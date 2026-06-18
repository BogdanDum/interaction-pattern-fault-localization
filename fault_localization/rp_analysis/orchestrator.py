from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rp_analysis import stats as mast_stats
from rp_analysis.datasets import (
    apply_post_filters,
    build_traces_table,
    collect_export_paths,
    filter_export_paths,
)
from rp_analysis.filters import filter_pattern_indices
from rp_analysis.matrix import build_sparse_matrix, save_artifacts, vocabulary_from_traces
from rp_analysis.orchestrator_config import fisher_kwargs, load_config, resolve_config
from rp_analysis.paths import config_for_disk, repo_relative
from rp_analysis.sbfl import (
    compute_contingency_sparse,
    reciprocal_rank_fusion,
    scores_dataframe,
)

SCORE_COLS = ("ochiai", "tarantula", "dstar", "jaccard", "op2")
GLOBAL_LABEL_ID = "global"


@dataclass
class LabelSpec:
    label_id: str
    y: np.ndarray
    description: str


def enumerate_labels(traces_df: pd.DataFrame, labels_cfg: dict[str, Any]) -> list[LabelSpec]:
    del labels_cfg
    y = traces_df["outcome_fail_any"].astype(int).to_numpy()
    return [LabelSpec(GLOBAL_LABEL_ID, y, "outcome_fail_any")]


def stage_build_artifacts(
    cfg: dict[str, Any],
    out_dir: Path,
    log_fp,
) -> tuple[pd.DataFrame, Any, list[str]]:
    """Load tokenized exports, apply filters, and write sparse trace-pattern artifacts."""
    tok = cfg["tokenization"]
    pop = cfg["population"]

    paths = filter_export_paths(
        collect_export_paths(Path(tok["export_root"]), int(tok["n"])),
        Path(tok["export_root"]),
        int(tok["n"]),
        include_set=pop["include_set"],
        mas_names=pop["mas_names"] or None,
        benchmark_names=pop["benchmark_names"] or None,
    )

    traces_df = build_traces_table(paths, Path(tok["mad_root"]), n=int(tok["n"]))
    n_pre = len(traces_df)
    traces_df = apply_post_filters(
        traces_df,
        llm_names=pop["llm_names"] or None,
        benchmark_names=pop["benchmark_names"] or None,
        min_event_count=int(pop["min_event_count"] or 0),
        max_traces=pop["max_traces"],
        sample_seed=int(pop["sample_seed"] or 42),
    )

    patterns = vocabulary_from_traces(traces_df["ngram_presence"].tolist())
    X = build_sparse_matrix(traces_df, patterns)
    if patterns:
        from rp_analysis.pattern_collapse import collapse_pattern_columns

        mas = str(traces_df["mas_name"].iloc[0])
        patterns, X = collapse_pattern_columns(
            patterns, X, mas_name=mas, n=int(tok["n"])
        )

    manifest = {
        "export_root": repo_relative(tok["export_root"]),
        "mad_root": repo_relative(tok["mad_root"]),
        "n": int(tok["n"]),
        "n_export_files": len(paths),
        "n_traces_after_path_filter": n_pre,
        "n_traces_final": int(len(traces_df)),
        "filters": pop,
    }
    save_artifacts(out_dir / "artifacts", traces_df, patterns, manifest=manifest)

    print(
        f"[build] traces={len(traces_df)} (pre-post={n_pre}) patterns={len(patterns)}",
        file=log_fp,
    )
    return traces_df, X, patterns


def stage_score_label(
    cfg: dict[str, Any],
    traces_df: pd.DataFrame,
    X,
    patterns: list[str],
    spec: LabelSpec,
    out_dir: Path,
    log_fp,
) -> Path | None:
    """Score filtered patterns with SBFL, Fisher/FDR, and optional Markov contrast ranking."""
    sb = cfg["sbfl"]
    flt = sb["filters"]
    y = np.asarray(spec.y, dtype=np.float64)

    keep_idx = filter_pattern_indices(
        X,
        y,
        min_support_total=int(flt["min_support_total"]),
        min_support_fail=int(flt["min_support_fail"]),
        min_support_pass=int(flt["min_support_pass"]),
        max_prevalence=float(flt["max_prevalence"]),
        patterns=patterns,
    )
    if keep_idx.size == 0:
        print(f"[score:{spec.label_id}] no patterns survived filters", file=log_fp)
        return None

    pat_sub = [patterns[i] for i in keep_idx]
    X_sub = X[:, keep_idx]

    e_f, e_p, n_f, n_p = compute_contingency_sparse(X_sub, y)
    df = scores_dataframe(pat_sub, e_f, e_p, n_f, n_p, label_name=spec.label_id)
    df = reciprocal_rank_fusion(df, list(SCORE_COLS))
    df["rank_rrf"] = df["rrf_score"].rank(ascending=False, method="average").astype(int)
    df = df.sort_values("ochiai", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    if bool(sb["fisher"]):
        df = mast_stats.attach_fisher_fdr(df, **fisher_kwargs(sb))

    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"rankings__{GLOBAL_LABEL_ID}.csv"
    df.to_csv(out_path, index=False)

    mpc = cfg.get("markov_pattern") or {}
    if bool(mpc["enabled"]):
        from rp_analysis.markov_patterns import rank_patterns_by_markov_trace_contrast

        tok = cfg["tokenization"]
        df_mp = rank_patterns_by_markov_trace_contrast(
            traces_df,
            X_sub,
            pat_sub,
            y.astype(int),
            n_markov=int(mpc["n"] or tok["n"]),
            smoothing=float(mpc["smoothing"]),
            min_tokens_per_trace=int(mpc["min_tokens_per_trace"]),
        )
        mp_path = runs_dir / f"markov_pattern_rankings__{GLOBAL_LABEL_ID}.csv"
        df_mp.to_csv(mp_path, index=False)
        print(f"[score:{spec.label_id}] markov_pattern -> {mp_path.name}", file=log_fp)

    n_pos = int(np.sum(y))
    n_neg = int(len(y) - n_pos)
    n_tested = int(df["fisher_tested"].sum()) if "fisher_tested" in df.columns else 0
    n_reject = int(df["reject_bh"].sum()) if "reject_bh" in df.columns else 0
    manifest = {
        "label_id": spec.label_id,
        "description": spec.description,
        "n_positive": n_pos,
        "n_negative": n_neg,
        "n_patterns_after_filter": int(len(df)),
        "n_fisher_tested": n_tested,
        "n_reject_bh": n_reject,
        "reject_bh_rate_among_tested": (n_reject / n_tested) if n_tested else None,
    }
    out_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[score:{spec.label_id}] pos={n_pos} neg={n_neg} kept={len(df)} -> {out_path.name}",
        file=log_fp,
    )
    return out_path


def run_experiment(config_path: Path, *, out_dir_override: Path | None = None) -> int:
    """Run the full build-then-score experiment pipeline from a resolved config file."""
    cfg_raw = load_config(config_path)
    cfg = resolve_config(cfg_raw, config_path)

    if out_dir_override is not None:
        cfg.setdefault("experiment", {})["out_dir"] = str(out_dir_override.resolve())

    out_dir = Path(cfg["experiment"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "config.resolved.json").write_text(
        json.dumps(config_for_disk(cfg), indent=2) + "\n",
        encoding="utf-8",
    )

    log_path = out_dir / "log.txt"
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(log_path, "w", encoding="utf-8") as log_fp:
        print(f"# experiment {cfg['experiment']['name']} started {started}", file=log_fp)
        traces_df, X, patterns = stage_build_artifacts(cfg, out_dir, log_fp)
        specs: list[LabelSpec] = []
        for label_block in cfg["labels"]:
            specs.extend(enumerate_labels(traces_df, label_block))

        for spec in specs:
            stage_score_label(cfg, traces_df, X, patterns, spec, out_dir, log_fp)

    print(f"experiment '{cfg['experiment']['name']}' finished -> {out_dir}")
    return 0
