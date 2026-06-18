from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rp_analysis.datasets import collect_export_paths, load_json
from rp_analysis.paths import repo_path

SBFL_FILTER_DEFAULTS: dict[str, Any] = {
    "min_support_total": 5,
    "min_support_fail": 3,
    "min_support_pass": 0,
    "max_prevalence": 0.75,
}

SBFL_DEFAULTS: dict[str, Any] = {
    "fisher": True,
    "fdr_alpha": 0.05,
    "fisher_direction": "greater",
    "fisher_require_higher_in_positives": True,
    "fisher_higher_in_positives_only": True,
    "fisher_min_rate_delta": 0.10,
    "fisher_max_patterns": 20,
    "fisher_score_col": "ochiai",
    "nominal_p_alpha": 0.05,
    "high_effect_ochiai": 0.50,
    "high_effect_delta": 0.15,
}

MARKOV_PATTERN_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "n": None,
    "smoothing": 1.0,
    "min_tokens_per_trace": 1,
}

POPULATION_DEFAULTS: dict[str, Any] = {
    "include_set": "both",
    "mas_names": [],
    "benchmark_names": [],
    "llm_names": [],
    "min_event_count": 0,
    "max_traces": None,
    "sample_seed": 42,
}


def load_config(config_path: Path) -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def normalize_labels_blocks(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return [{}]
    if isinstance(raw, dict):
        return [dict(raw)]
    return [dict(item) for item in raw]


def _apply_defaults(section: dict[str, Any], defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        section.setdefault(key, value)


def _normalize_fisher_max_patterns(sb: dict[str, Any]) -> int | None:
    max_pat = sb.get("fisher_max_patterns")
    if max_pat is None:
        return None
    max_pat = int(max_pat)
    return None if max_pat <= 0 else max_pat


def fisher_kwargs(sb: dict[str, Any]) -> dict[str, Any]:
    return {
        "q": float(sb["fdr_alpha"]),
        "direction": str(sb["fisher_direction"]),
        "require_higher_in_positives": bool(sb["fisher_require_higher_in_positives"]),
        "max_patterns": _normalize_fisher_max_patterns(sb),
        "score_col": str(sb["fisher_score_col"]),
        "min_rate_delta": float(sb["fisher_min_rate_delta"]),
        "higher_in_positives_only": bool(sb["fisher_higher_in_positives_only"]),
        "nominal_p": float(sb["nominal_p_alpha"]),
        "high_effect_ochiai": float(sb["high_effect_ochiai"]),
        "high_effect_delta": float(sb["high_effect_delta"]),
    }


def resolve_config(cfg: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """Normalize experiment config paths, defaults, and label blocks after loading from disk."""
    out = json.loads(json.dumps(cfg))

    exp = out.setdefault("experiment", {})
    name = exp.get("name") or config_path.stem
    exp["name"] = name
    exp_out = exp.get("out_dir") or f"out/{name}"
    exp["out_dir"] = str(repo_path(exp_out))

    tok = out.setdefault("tokenization", {})
    tok["export_root"] = str(repo_path(tok["export_root"]))
    tok["mad_root"] = str(repo_path(tok["mad_root"]))
    tok.setdefault("n", 3)

    probe_paths = collect_export_paths(Path(tok["export_root"]), int(tok["n"]))
    if probe_paths:
        sample = load_json(probe_paths[0])
        st0 = sample.get("stats") or {}
        if "segmentation" in st0:
            tok.setdefault("segmentation", st0["segmentation"])
        if "hyperagent_inner_agent" in st0:
            tok.setdefault("hyperagent_inner_agent", st0["hyperagent_inner_agent"])

    pop = out.setdefault("population", {})
    _apply_defaults(pop, POPULATION_DEFAULTS)

    label_blocks = normalize_labels_blocks(out.get("labels"))
    for lab in label_blocks:
        lab.setdefault("mode", "global")
    out["labels"] = label_blocks

    sb = out.setdefault("sbfl", {})
    _apply_defaults(sb.setdefault("filters", {}), SBFL_FILTER_DEFAULTS)
    _apply_defaults(sb, SBFL_DEFAULTS)

    mp = out.setdefault("markov_pattern", {})
    _apply_defaults(mp, MARKOV_PATTERN_DEFAULTS)

    return out
