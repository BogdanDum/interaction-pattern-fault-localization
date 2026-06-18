from __future__ import annotations

import numpy as np
from scipy import sparse

from rp_analysis.ngrams import format_ngram, normalized_ngram_for_export


def _normalized_pattern(pattern: str, *, mas_name: str, n: int) -> str:
    parts = [t.strip() for t in str(pattern).split(" :: ") if t.strip()]
    if len(parts) != n:
        return str(pattern)
    return format_ngram(
        normalized_ngram_for_export(tuple(parts), mas_name=mas_name, n=n)
    )


def collapse_pattern_columns(
    patterns: list[str],
    X: sparse.csr_matrix,
    *,
    mas_name: str,
    n: int,
) -> tuple[list[str], sparse.csr_matrix]:
    if not patterns or X.shape[1] == 0:
        return patterns, X
    groups: dict[str, list[int]] = {}
    for j, pat in enumerate(patterns):
        key = _normalized_pattern(pat, mas_name=mas_name, n=n)
        groups.setdefault(key, []).append(j)
    new_patterns = sorted(groups.keys())
    if len(new_patterns) == len(patterns):
        return patterns, X
    old_to_new = {key: i for i, key in enumerate(new_patterns)}
    rows, cols, data = [], [], []
    Xc = X.tocsc()
    for key, indices in groups.items():
        col = Xc[:, indices].sum(axis=1)
        nz = col.nonzero()
        if len(nz[0]) == 0:
            continue
        jnew = old_to_new[key]
        for r in np.asarray(nz[0]).ravel():
            rows.append(int(r))
            cols.append(jnew)
            data.append(1 if int(col[r, 0]) > 0 else 0)
    X_new = sparse.csr_matrix(
        (data, (rows, cols)),
        shape=(X.shape[0], len(new_patterns)),
        dtype=np.int8,
    )
    return new_patterns, X_new
