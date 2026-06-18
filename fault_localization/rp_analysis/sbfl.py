from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse


def compute_contingency_sparse(X: sparse.csr_matrix, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = np.asarray(y).astype(np.float64).reshape(-1, 1)
    one_y = 1.0 - y
    e_f = np.asarray(X.transpose() @ y).ravel()
    e_p = np.asarray(X.transpose() @ one_y).ravel()
    fail_count = float(y.sum())
    pass_count = float(one_y.sum())
    n_f = fail_count - e_f
    n_p = pass_count - e_p
    return e_f, e_p, n_f, n_p


def contingency_per_column_dense(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = y.astype(np.float64)
    one_minus_y = 1.0 - y
    present_f = X.T @ y
    present_p = X.T @ one_minus_y
    fail_count = float(np.sum(y))
    pass_count = float(np.sum(one_minus_y))
    e_f = np.asarray(present_f).ravel()
    e_p = np.asarray(present_p).ravel()
    n_f = fail_count - e_f
    n_p = pass_count - e_p
    return e_f, e_p, n_f, n_p


def ochiai(e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray) -> np.ndarray:
    denom = np.sqrt((e_f + n_f) * (e_f + e_p))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(e_f, denom, where=denom > 0)
    out = np.where(denom > 0, out, 0.0)
    return out


def tarantula(e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray) -> np.ndarray:
    fail_pres = np.divide(e_f, e_f + n_f, out=np.zeros_like(e_f), where=(e_f + n_f) > 0)
    pass_pres = np.divide(e_p, e_p + n_p, out=np.zeros_like(e_p), where=(e_p + n_p) > 0)
    denom = fail_pres + pass_pres
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(fail_pres, denom, where=denom > 0)
    return np.where(denom > 0, out, 0.0)


def dstar(e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray, star: float = 2.0) -> np.ndarray:
    denom = e_p + n_f
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(np.power(e_f, star), denom, where=denom > 0)
    return np.where(denom > 0, out, 0.0)


def jaccard(e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray) -> np.ndarray:
    denom = e_f + n_f + e_p
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(e_f, denom, where=denom > 0)
    return np.where(denom > 0, out, 0.0)


def op2(e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray) -> np.ndarray:
    denom = e_p + n_p + 1.0
    return e_f - (e_p / denom)


def scores_dataframe(
    pattern_names: list[str],
    e_f: np.ndarray,
    e_p: np.ndarray,
    n_f: np.ndarray,
    n_p: np.ndarray,
    *,
    label_name: str,
) -> pd.DataFrame:
    """Assemble Ochiai, Tarantula, D*, Jaccard, and OP2 scores into one rankings DataFrame."""
    df = pd.DataFrame(
        {
            "pattern": pattern_names,
            "label": label_name,
            "e_f": e_f,
            "e_p": e_p,
            "n_f": n_f,
            "n_p": n_p,
            "ochiai": ochiai(e_f, e_p, n_f, n_p),
            "tarantula": tarantula(e_f, e_p, n_f, n_p),
            "dstar": dstar(e_f, e_p, n_f, n_p),
            "jaccard": jaccard(e_f, e_p, n_f, n_p),
            "op2": op2(e_f, e_p, n_f, n_p),
        }
    )
    return df


def reciprocal_rank_fusion(
    df: pd.DataFrame,
    score_cols: list[str],
    *,
    k_rrf: int = 60,
    out_col: str = "rrf_score",
) -> pd.DataFrame:
    out = df.copy()
    acc = np.zeros(len(out), dtype=np.float64)
    for col in score_cols:
        ranks = out[col].rank(ascending=False, method="average")
        acc += 1.0 / (k_rrf + ranks.to_numpy())
    out[out_col] = acc
    return out
