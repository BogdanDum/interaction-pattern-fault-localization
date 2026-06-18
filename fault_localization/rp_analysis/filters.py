from __future__ import annotations

import numpy as np
from scipy import sparse


def pattern_support(X: sparse.csr_matrix) -> np.ndarray:
    return np.asarray(X.sum(axis=0)).ravel().astype(int)


def pattern_fail_pass_support(
    X: sparse.csr_matrix, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y).astype(bool)
    fail_mask = y
    pass_mask = ~y

    Xf = X[fail_mask]
    Xp = X[pass_mask]

    fail_sup = np.asarray(Xf.sum(axis=0)).ravel().astype(int)
    pass_sup = np.asarray(Xp.sum(axis=0)).ravel().astype(int)
    return fail_sup, pass_sup


def filter_pattern_indices(
    X: sparse.csr_matrix,
    y: np.ndarray,
    *,
    min_support_total: int = 1,
    min_support_fail: int = 0,
    min_support_pass: int = 0,
    max_prevalence: float = 1.0,
    patterns: list[str],
) -> np.ndarray:
    """Return pattern column indices that pass minimum-support and max-prevalence filters."""
    n_traces = X.shape[0]
    if n_traces == 0:
        return np.array([], dtype=int)

    total = pattern_support(X)
    fail_sup, pass_sup = pattern_fail_pass_support(X, y)
    prevalence = total / float(n_traces)

    mask = np.ones(len(patterns), dtype=bool)
    mask &= total >= min_support_total
    mask &= fail_sup >= min_support_fail
    mask &= pass_sup >= min_support_pass
    mask &= prevalence <= max_prevalence

    return np.nonzero(mask)[0]
