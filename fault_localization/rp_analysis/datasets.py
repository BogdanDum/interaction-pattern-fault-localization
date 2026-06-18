from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from rp_analysis.ngrams import format_ngram, normalized_ngram_for_export

from rp_analysis.paths import repo_path, repo_relative

FAILURE_CODE_RE = re.compile(r"^\d+\.\d+$")

KNOWN_SETS = ("full_set")
TOKEN_EXPORT_SUBDIR = "vocab"
NGRAM_JOINER = " :: "


def taxonomy_sort_key(code: str) -> tuple[int, int]:
    major, minor = code.split(".", 1)
    return int(major), int(minor)


def export_ngram_dir(export_root: Path, n: int) -> Path:
    return export_root.resolve() / TOKEN_EXPORT_SUBDIR / f"n{n}"


def collect_export_paths(export_root: Path, n: int) -> list[Path]:
    sub = export_ngram_dir(export_root, n)
    if not sub.is_dir():
        raise FileNotFoundError(f"Missing export directory: {sub}")
    return sorted(sub.rglob("*.json"))


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mast_annotation_to_columns(mast_annotation: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for k, v in mast_annotation.items():
        key = str(k).strip()
        if FAILURE_CODE_RE.match(key):
            out[f"mast_{key}"] = int(v)
    return out


def outcome_fail_any(mast_annotation: dict[str, Any]) -> bool:
    cols = mast_annotation_to_columns(mast_annotation)
    return any(v != 0 for v in cols.values())


def discover_mast_code_columns(
    sample_paths: list[Path], mad_root: Path, limit: int | None = 200
) -> list[str]:
    """Discover MAST failure-code column names by scanning MAD annotations in export samples."""
    keys: set[str] = set()
    subset = sample_paths if limit is None else sample_paths[:limit]
    for p in subset:
        exp = load_json(p)
        rel = exp.get("mad_path") or exp.get("mad_relative_path")
        if not rel:
            continue
        mad_path = mad_root / str(rel)
        if not mad_path.is_file():
            continue
        rec = load_json(mad_path)
        ann = rec.get("mast_annotation") or {}
        keys.update(str(k).strip() for k in ann.keys() if FAILURE_CODE_RE.match(str(k).strip()))
    return sorted(keys, key=taxonomy_sort_key)


def normalize_mast_code(c: str) -> str:
    c = str(c).strip()
    if c.startswith("mast_"):
        c = c[len("mast_") :]
    return c


def set_from_relative(rel: str) -> str:
    parts = Path(str(rel)).parts
    if parts and parts[0] in KNOWN_SETS:
        return parts[0]
    return ""


def filter_export_paths(
    export_paths: list[Path],
    export_root: Path,
    n: int,
    *,
    include_set: str | None = None,
    mas_names: list[str] | None = None,
    benchmark_names: list[str] | None = None,
) -> list[Path]:
    del benchmark_names
    base = export_ngram_dir(export_root, n).resolve()
    inc = (include_set or "").strip().lower()
    if inc in ("", "both", "all"):
        inc = ""
    mas_set = set(mas_names) if mas_names else None

    out: list[Path] = []
    for p in export_paths:
        rel = p.resolve().relative_to(base)
        parts = rel.parts
        if len(parts) < 2:
            continue
        path_set, path_mas = parts[0], parts[1]
        if inc and path_set != inc:
            continue
        if mas_set is not None and path_mas not in mas_set:
            continue
        out.append(p)
    return out


def apply_post_filters(
    df: pd.DataFrame,
    *,
    llm_names: list[str] | None = None,
    benchmark_names: list[str] | None = None,
    min_event_count: int = 0,
    max_traces: int | None = None,
    sample_seed: int = 42,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if llm_names:
        out = out[out["llm_name"].isin(llm_names)]
    if benchmark_names:
        out = out[out["benchmark_name"].isin(benchmark_names)]
    if min_event_count and int(min_event_count) > 0:
        out = out[out["event_count"] >= int(min_event_count)]
    if max_traces and int(max_traces) > 0 and len(out) > int(max_traces):
        out = out.sample(n=int(max_traces), random_state=int(sample_seed))
    return out.reset_index(drop=True)


def _normalize_ngram_presence(
    presence: list,
    *,
    mas_name: str,
    n: int,
) -> list[str]:
    """Merge action-token export n-grams to normalized keys."""
    seen: set[str] = set()
    for p in presence:
        parts = [t.strip() for t in str(p).split(" :: ") if t.strip()]
        if len(parts) != n:
            seen.add(str(p))
            continue
        c = format_ngram(
            normalized_ngram_for_export(tuple(parts), mas_name=str(mas_name or ""), n=n)
        )
        seen.add(c)
    return sorted(seen)


def build_traces_table(
    export_paths: list[Path],
    mad_root: Path,
    *,
    n: int,
    mast_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Assemble one row per tokenized export with metadata, labels, and normalized n-gram presence."""
    mad_root = mad_root.resolve()
    rows: list[dict[str, Any]] = []

    if mast_columns is None:
        mast_columns = discover_mast_code_columns(export_paths, mad_root)
        if not mast_columns:
            mast_columns = discover_mast_code_columns(export_paths, mad_root, limit=None)
    mast_codes = [normalize_mast_code(c) for c in mast_columns]

    for exp_path in export_paths:
        exp = load_json(exp_path)
        rel = exp.get("mad_path") or exp.get("mad_relative_path")
        mad_path = mad_root / str(rel)
        rec = load_json(mad_path)
        ann = rec.get("mast_annotation") or {}
        mast_flat = mast_annotation_to_columns(ann)
        stats = exp.get("stats") or {}

        row: dict[str, Any] = {
            "export_path": repo_relative(exp_path),
            "mad_path": repo_relative(mad_path),
            "mad_relative_path": str(rel),
            "set_name": set_from_relative(str(rel)),
            "n": int(n),
            "mas_name": exp.get("mas_name") or rec.get("mas_name"),
            "benchmark_name": exp.get("benchmark_name") or rec.get("benchmark_name"),
            "llm_name": exp.get("llm_name") if exp.get("llm_name") is not None else rec.get("llm_name"),
            "trace_id": exp.get("trace_id") if exp.get("trace_id") is not None else rec.get("trace_id"),
            "outcome_fail_any": outcome_fail_any(ann),
            "ngram_presence": _normalize_ngram_presence(
                exp.get("ngram_presence") or [],
                mas_name=str(exp.get("mas_name") or rec.get("mas_name") or ""),
                n=int(n),
            ),
            "tokens": exp.get("tokens"),
            "stats": stats,
            "event_count": int(stats.get("event_count", 0) or 0),
        }

        for mk in mast_codes:
            col = f"mast_{mk}"
            row[col] = int(mast_flat.get(col, 0))

        rows.append(row)

    return pd.DataFrame(rows)


def load_traces_from_manifest(
    artifacts_dir: Path,
    *,
    root: Path | None = None,
) -> pd.DataFrame:
    """Rebuild the trace table from manifest json and tokenized exports."""
    base = artifacts_dir.resolve()
    manifest_path = base / "manifest.json" if base.is_dir() else base
    if manifest_path.is_dir():
        manifest_path = manifest_path / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    export_root = repo_path(str(manifest["export_root"]), root)
    mad_root = repo_path(str(manifest["mad_root"]), root)
    n = int(manifest["n"])
    pop = manifest.get("filters") or {}

    paths = filter_export_paths(
        collect_export_paths(export_root, n),
        export_root,
        n,
        include_set=pop.get("include_set"),
        mas_names=pop.get("mas_names") or None,
        benchmark_names=pop.get("benchmark_names") or None,
    )
    traces_df = build_traces_table(paths, mad_root, n=n)
    traces_df = apply_post_filters(
        traces_df,
        llm_names=pop.get("llm_names") or None,
        benchmark_names=pop.get("benchmark_names") or None,
        min_event_count=int(pop.get("min_event_count", 0) or 0),
        max_traces=pop.get("max_traces"),
        sample_seed=int(pop.get("sample_seed", 42) or 42),
    )
    return traces_df


def tokens_for_trace_row(row: pd.Series, root: Path | None = None) -> list[str]:
    raw = row.get("tokens")
    if isinstance(raw, list) and raw:
        return [str(t) for t in raw]
    export_path = row.get("export_path")
    if export_path:
        exp = load_json(repo_path(str(export_path), root))
        tokens = exp.get("tokens")
        if isinstance(tokens, list) and tokens:
            return [str(t) for t in tokens]
    mad_rel = row.get("mad_relative_path") or row.get("mad_path")
    raise ValueError(f"No tokens for trace {mad_rel}")
