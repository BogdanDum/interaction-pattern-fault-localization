from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rp_analysis import orchestrator
from rp_analysis.filters import filter_pattern_indices
from rp_analysis.matrix import build_sparse_matrix
from rp_analysis.orchestrator import SCORE_COLS
from rp_analysis.orchestrator_config import fisher_kwargs, load_config, resolve_config
from rp_analysis.paths import repo_relative
from rp_analysis.sbfl import compute_contingency_sparse, reciprocal_rank_fusion, scores_dataframe
from rp_analysis.stats import attach_fisher_fdr


def _load_experiment_frames(
    config_path: Path,
) -> tuple[dict[str, Any], pd.DataFrame, Any, list[str], np.ndarray]:
    cfg_raw = load_config(config_path)
    cfg = resolve_config(cfg_raw, config_path)
    out_dir = Path(cfg["experiment"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "log.txt", "w", encoding="utf-8") as log_fp:
        traces_df, X, patterns = orchestrator.stage_build_artifacts(cfg, out_dir, log_fp)

    y = traces_df["outcome_fail_any"].astype(int).to_numpy()
    return cfg, traces_df, X, patterns, y


def _rank_patterns_on_sample(
    traces_df: pd.DataFrame,
    patterns: list[str],
    y: np.ndarray,
    *,
    sbfl_cfg: dict[str, Any],
    top_k: int,
) -> tuple[str | None, str | None, set[str], set[str]]:
    X = build_sparse_matrix(traces_df, patterns)
    flt = sbfl_cfg["filters"]
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
        return None, None, set(), set()

    pat_sub = [patterns[i] for i in keep_idx]
    X_sub = X[:, keep_idx]
    e_f, e_p, n_f, n_p = compute_contingency_sparse(X_sub, y)
    df = scores_dataframe(pat_sub, e_f, e_p, n_f, n_p, label_name="global")
    df = reciprocal_rank_fusion(df, list(SCORE_COLS))
    df = df.sort_values("ochiai", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    df = df.sort_values("rrf_score", ascending=False).reset_index(drop=True)
    df["rank_rrf"] = df.index + 1

    by_ochiai = df.sort_values("ochiai", ascending=False).reset_index(drop=True)
    by_rrf = df.sort_values("rrf_score", ascending=False).reset_index(drop=True)
    rank1_ochiai = str(by_ochiai.iloc[0]["pattern"]) if len(by_ochiai) else None
    rank1_rrf = str(by_rrf.iloc[0]["pattern"]) if len(by_rrf) else None
    top_ochiai = set(by_ochiai.head(top_k)["pattern"].astype(str))
    top_rrf = set(by_rrf.head(top_k)["pattern"].astype(str))
    return rank1_ochiai, rank1_rrf, top_ochiai, top_rrf


def run_bootstrap(
    config_path: Path,
    *,
    B: int = 100,
    seed: int = 42,
    top_k: int = 10,
    out_dir: Path | None = None,
) -> Path:
    cfg, traces_df, _X, patterns, y = _load_experiment_frames(config_path)
    sbfl_cfg = cfg["sbfl"]
    n_traces = len(traces_df)

    full_rank1_path = Path(cfg["experiment"]["out_dir"]) / "runs" / "rankings__global.csv"
    if full_rank1_path.is_file():
        full_df = pd.read_csv(full_rank1_path)
        ref_pattern = str(full_df.sort_values("rank").iloc[0]["pattern"])
    else:
        ref_ochiai, _, _, _ = _rank_patterns_on_sample(
            traces_df, patterns, y, sbfl_cfg=sbfl_cfg, top_k=top_k
        )
        ref_pattern = ref_ochiai or ""

    rng = np.random.default_rng(int(seed))
    rank1_ochiai_counts: dict[str, int] = {}
    rank1_rrf_counts: dict[str, int] = {}
    in_top_ochiai: dict[str, int] = {ref_pattern: 0}
    in_top_rrf: dict[str, int] = {ref_pattern: 0}

    for _ in range(int(B)):
        idx = rng.integers(0, n_traces, size=n_traces)
        sample_df = traces_df.iloc[idx].reset_index(drop=True)
        y_b = sample_df["outcome_fail_any"].astype(int).to_numpy()
        r1_o, r1_r, top_o, top_r = _rank_patterns_on_sample(
            sample_df, patterns, y_b, sbfl_cfg=sbfl_cfg, top_k=top_k
        )
        if r1_o:
            rank1_ochiai_counts[r1_o] = rank1_ochiai_counts.get(r1_o, 0) + 1
        if r1_r:
            rank1_rrf_counts[r1_r] = rank1_rrf_counts.get(r1_r, 0) + 1
        if ref_pattern in top_o:
            in_top_ochiai[ref_pattern] += 1
        if ref_pattern in top_r:
            in_top_rrf[ref_pattern] += 1

    rows = [
        {
            "pattern": ref_pattern,
            "bootstrap": int(B),
            "in_top_k_freq_ochiai": in_top_ochiai.get(ref_pattern, 0),
            "freq_ochiai": in_top_ochiai.get(ref_pattern, 0) / float(B),
            "in_top_k_freq_rrf": in_top_rrf.get(ref_pattern, 0),
            "freq_rrf": in_top_rrf.get(ref_pattern, 0) / float(B),
            "in_top_k_freq": in_top_ochiai.get(ref_pattern, 0),
            "freq": rank1_ochiai_counts.get(ref_pattern, 0) / float(B),
            "rank1_freq_ochiai": rank1_ochiai_counts.get(ref_pattern, 0) / float(B),
            "rank1_freq_rrf": rank1_rrf_counts.get(ref_pattern, 0) / float(B),
            "top_k": int(top_k),
            "seed": int(seed),
        }
    ]
    summary = pd.DataFrame(rows)

    if out_dir is None:
        exp_out = Path(cfg["experiment"]["out_dir"])
        out_dir = exp_out.parent.parent / "results" / "bootstrap"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    label = cfg["labels"][0].get("mode", "global") if cfg.get("labels") else "global"
    n_val = int(cfg["tokenization"]["n"])
    out_csv = out_dir / f"bootstrap__n{n_val}__{label}.csv"
    summary.to_csv(out_csv, index=False)

    meta = {
        "config": repo_relative(config_path),
        "B": int(B),
        "seed": int(seed),
        "top_k": int(top_k),
        "reference_rank1_pattern": ref_pattern,
        "n_traces": n_traces,
    }
    out_csv.with_suffix(".manifest.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return out_csv


def run_significance_only(rankings_csv: Path, sbfl_cfg: dict[str, Any]) -> pd.DataFrame:
    """Re-attach Fisher + BH columns to an existing rankings CSV (contingency cols required)."""
    df = pd.read_csv(rankings_csv)
    required = {"e_f", "e_p", "n_f", "n_p", "ochiai"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"rankings CSV missing columns for significance: {sorted(missing)}")
    return attach_fisher_fdr(df, **fisher_kwargs(sbfl_cfg))
