from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse


def vocabulary_from_traces(ngram_lists: list[list[str]]) -> list[str]:
    vocab: set[str] = set()
    for ng in ngram_lists:
        for p in ng:
            if p:
                vocab.add(str(p))
    return sorted(vocab)


def build_sparse_matrix(traces_df: pd.DataFrame, patterns: list[str]) -> sparse.csr_matrix:
    """Build a binary trace-by-pattern CSR matrix from per-trace n-gram presence lists."""
    if traces_df.empty or not patterns:
        return sparse.csr_matrix((len(traces_df), max(len(patterns), 0)), dtype=np.int8)

    pattern_to_idx = {p: i for i, p in enumerate(patterns)}
    n_rows = len(traces_df)
    n_cols = len(patterns)

    rows: list[int] = []
    cols: list[int] = []
    data: list[int] = []

    for i, ngrams in enumerate(traces_df["ngram_presence"].tolist()):
        seen: set[int] = set()
        for g in ngrams:
            p = str(g)
            j = pattern_to_idx.get(p)
            if j is None or j in seen:
                continue
            seen.add(j)
            rows.append(i)
            cols.append(j)
            data.append(1)

    return sparse.csr_matrix((data, (rows, cols)), shape=(n_rows, n_cols), dtype=np.int8)


def save_artifacts(
    out_dir: Path,
    traces_df: pd.DataFrame,
    patterns: list[str],
    *,
    manifest: dict[str, Any] | None = None,
) -> None:
    """Persist traces CSV, pattern vocabulary, and experiment manifest under artifacts/."""
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df_save = traces_df.drop(columns=["ngram_presence", "stats"], errors="ignore")
    df_save.to_csv(out_dir / "traces.csv", index=False)

    with open(out_dir / "patterns.json", "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2)
        f.write("\n")

    meta: dict[str, Any] = {
        "n_traces": int(len(traces_df)),
        "n_patterns": int(len(patterns)),
        "matrix_shape": [len(traces_df), len(patterns)],
    }
    if manifest:
        meta.update(manifest)
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
