from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from rp_analysis.markov import fit_markov_model


def rank_patterns_by_markov_trace_contrast(
    traces_df: pd.DataFrame,
    X: sparse.csr_matrix,
    patterns: list[str],
    y: np.ndarray,
    *,
    n_markov: int,
    smoothing: float,
    min_tokens_per_trace: int = 1,
) -> pd.DataFrame:
    """Rank patterns by fail-vs-pass average Markov surprise delta weighted by support."""
    y = np.asarray(y).astype(int).ravel()
    pass_mask = y == 0

    train_seqs: list[list[str]] = []
    for i in np.flatnonzero(pass_mask):
        seq_list = [str(t) for t in traces_df["tokens"].iloc[i] if str(t)]
        if len(seq_list) >= min_tokens_per_trace:
            train_seqs.append(seq_list)

    model = fit_markov_model(train_seqs, n=int(n_markov), smoothing=float(smoothing))

    surprise: list[float] = []
    for i in range(len(traces_df)):
        seq_list = [str(t) for t in traces_df["tokens"].iloc[i] if str(t)]
        if len(seq_list) < min_tokens_per_trace:
            surprise.append(float("nan"))
        else:
            surprise.append(float(model.score_sequence(seq_list)["avg_neg_log_prob"]))
    s = np.asarray(surprise, dtype=np.float64)

    rows: list[dict[str, Any]] = []
    Xc = X.tocsr()
    for j, pat in enumerate(patterns):
        col = (Xc.getcol(j).toarray().ravel() > 0) & ~np.isnan(s)
        fail_i = (y == 1) & col
        pass_i = (y == 0) & col
        n_f = int(fail_i.sum())
        n_p = int(pass_i.sum())
        mf = float(np.nanmean(s[fail_i])) if n_f else float("nan")
        mp = float(np.nanmean(s[pass_i])) if n_p else float("nan")
        if np.isnan(mf) and np.isnan(mp):
            delta = 0.0
        elif np.isnan(mf):
            delta = -mp
        elif np.isnan(mp):
            delta = mf
        else:
            delta = mf - mp
        w = n_f + n_p
        weighted = float(delta * np.log1p(w)) if w else 0.0
        rows.append(
            {
                "pattern": pat,
                "fail_support": n_f,
                "pass_support": n_p,
                "mean_fail_surprise": mf,
                "mean_pass_surprise": mp,
                "surprise_delta": float(delta),
                "support_weighted_delta": weighted,
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["fail_support", "surprise_delta", "support_weighted_delta"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df
