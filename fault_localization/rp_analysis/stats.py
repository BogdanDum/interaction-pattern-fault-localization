from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact


def _fail_rate(e_f: np.ndarray, n_f: np.ndarray) -> np.ndarray:
    denom = e_f + n_f
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(e_f, denom, where=denom > 0)
    return np.where(denom > 0, out, 0.0)


def _pass_rate(e_p: np.ndarray, n_p: np.ndarray) -> np.ndarray:
    denom = e_p + n_p
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(e_p, denom, where=denom > 0)
    return np.where(denom > 0, out, 0.0)


def is_higher_in_positives(
    e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray
) -> np.ndarray:
    """True where pattern prevalence is higher in y=1 (positive) traces than y=0"""
    return _fail_rate(e_f, n_f) > _pass_rate(e_p, n_p)


def fail_minus_pass_rate_delta(
    e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray
) -> np.ndarray:
    """fail_rate - pass_rate per pattern (for testing-family prefilter)"""
    return _fail_rate(e_f, n_f) - _pass_rate(e_p, n_p)


def fisher_p_values_two_sided(
    e_f: np.ndarray, e_p: np.ndarray, n_f: np.ndarray, n_p: np.ndarray
) -> np.ndarray:
    """Per-pattern two-sided Fisher exact p-values"""
    pvals = np.ones_like(e_f, dtype=np.float64)
    for i in range(len(e_f)):
        table = [[e_f[i], e_p[i]], [n_f[i], n_p[i]]]
        _, p = fisher_exact(table, alternative="two-sided")
        pvals[i] = float(p)
    return pvals


def fisher_p_values_greater(
    e_f: np.ndarray,
    e_p: np.ndarray,
    n_f: np.ndarray,
    n_p: np.ndarray,
    *,
    require_higher_in_positives: bool = True,
) -> np.ndarray:
    """One-sided Fisher (greater): pattern more frequent in positives than negatives"""
    pvals = np.ones_like(e_f, dtype=np.float64)
    higher = is_higher_in_positives(e_f, e_p, n_f, n_p)
    for i in range(len(e_f)):
        if require_higher_in_positives and not higher[i]:
            pvals[i] = 1.0
            continue
        table = [[e_f[i], e_p[i]], [n_f[i], n_p[i]]]
        _, p = fisher_exact(table, alternative="greater")
        pvals[i] = float(p)
    return pvals


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """Return BH-adjusted q-values (Benjamini–Hochberg adjusted p-values)"""
    p = np.asarray(p_values, dtype=np.float64)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p)
    sorted_p = p[order]
    ranks = np.arange(1, m + 1, dtype=np.float64)
    temp = sorted_p * m / ranks
    temp = np.minimum.accumulate(temp[::-1])[::-1]
    temp = np.minimum(temp, 1.0)
    qvals = np.empty_like(temp)
    qvals[order] = temp
    return qvals


def _select_fisher_testing_positions(
    out: pd.DataFrame,
    e_f: np.ndarray,
    e_p: np.ndarray,
    n_f: np.ndarray,
    n_p: np.ndarray,
    *,
    score_col: str,
    max_patterns: int | None,
    min_rate_delta: float,
    higher_in_positives_only: bool,
) -> np.ndarray:
    """Row indices for the Fisher/BH testing family (pre-specified subset)"""
    n = len(out)
    if n == 0:
        return np.array([], dtype=int)

    higher = is_higher_in_positives(e_f, e_p, n_f, n_p)
    delta = fail_minus_pass_rate_delta(e_f, e_p, n_f, n_p)
    order = np.argsort(-out[score_col].to_numpy(dtype=np.float64))

    selected: list[int] = []
    k_cap = int(max_patterns) if max_patterns is not None and int(max_patterns) > 0 else n
    for pos in order:
        if higher_in_positives_only and not higher[pos]:
            continue
        if float(min_rate_delta) > 0.0 and delta[pos] < float(min_rate_delta):
            continue
        selected.append(int(pos))
        if len(selected) >= k_cap:
            break
    return np.asarray(selected, dtype=int)


def attach_fisher_fdr(
    df: pd.DataFrame,
    *,
    q: float = 0.05,
    direction: str = "greater",
    require_higher_in_positives: bool = True,
    max_patterns: int | None = 20,
    score_col: str = "ochiai",
    min_rate_delta: float = 0.10,
    higher_in_positives_only: bool = True,
    nominal_p: float = 0.05,
    high_effect_ochiai: float = 0.50,
    high_effect_delta: float = 0.15,
) -> pd.DataFrame:
    """
    Attach Fisher p-values and BH-FDR q-values.
    """
    out = df.copy()
    e_f = out["e_f"].to_numpy(dtype=np.float64)
    e_p = out["e_p"].to_numpy(dtype=np.float64)
    n_f = out["n_f"].to_numpy(dtype=np.float64)
    n_p = out["n_p"].to_numpy(dtype=np.float64)
    n = len(out)

    higher = is_higher_in_positives(e_f, e_p, n_f, n_p)
    delta = fail_minus_pass_rate_delta(e_f, e_p, n_f, n_p)
    out["higher_in_positives"] = higher
    out["fail_pass_rate_delta"] = delta
    out["fisher_tested"] = False
    out["p_value"] = np.nan
    out["q_value"] = np.nan
    out["reject_bh"] = False
    out["evidence_level"] = "untested"

    if n == 0:
        return out

    test_pos = _select_fisher_testing_positions(
        out,
        e_f,
        e_p,
        n_f,
        n_p,
        score_col=score_col,
        max_patterns=max_patterns,
        min_rate_delta=min_rate_delta,
        higher_in_positives_only=higher_in_positives_only,
    )
    if test_pos.size == 0:
        return out

    if direction == "two_sided":
        p_test = fisher_p_values_two_sided(
            e_f[test_pos], e_p[test_pos], n_f[test_pos], n_p[test_pos]
        )
    else:
        p_test = fisher_p_values_greater(
            e_f[test_pos],
            e_p[test_pos],
            n_f[test_pos],
            n_p[test_pos],
            require_higher_in_positives=require_higher_in_positives,
        )

    q_test = benjamini_hochberg(p_test)
    out.loc[out.index[test_pos], "fisher_tested"] = True
    out.loc[out.index[test_pos], "p_value"] = p_test
    out.loc[out.index[test_pos], "q_value"] = q_test
    out.loc[out.index[test_pos], "reject_bh"] = q_test <= float(q)
    out["evidence_level"] = classify_evidence_levels(
        out,
        primary_q=float(q),
        nominal_p=float(nominal_p),
        high_effect_ochiai=float(high_effect_ochiai),
        high_effect_delta=float(high_effect_delta),
    )
    return out


def classify_evidence_levels(
    df: pd.DataFrame,
    *,
    primary_q: float = 0.05,
    nominal_p: float = 0.05,
    high_effect_ochiai: float = 0.50,
    high_effect_delta: float = 0.15,
) -> pd.Series:
    """
    Categorize pattern evidence without changing the underlying statistical test.
    """
    if df.empty:
        return pd.Series(dtype=object)

    tested = df.get("fisher_tested", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    higher = df.get("higher_in_positives", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    p_value = pd.to_numeric(df.get("p_value", pd.Series(np.nan, index=df.index)), errors="coerce")
    q_value = pd.to_numeric(df.get("q_value", pd.Series(np.nan, index=df.index)), errors="coerce")
    ochiai_score = pd.to_numeric(df.get("ochiai", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
    rate_delta = pd.to_numeric(
        df.get("fail_pass_rate_delta", pd.Series(0.0, index=df.index)), errors="coerce"
    ).fillna(0.0)

    high_effect = higher & (ochiai_score >= high_effect_ochiai) & (rate_delta >= high_effect_delta)
    nominal = tested & higher & (p_value <= nominal_p)
    primary_bh = tested & (q_value <= primary_q)

    levels = pd.Series("untested", index=df.index, dtype=object)
    levels.loc[tested] = "tested_not_significant"
    levels.loc[high_effect] = "high_effect"
    levels.loc[nominal] = "nominal_higher_in_positives"
    levels.loc[nominal & high_effect] = "nominal_high_effect"
    levels.loc[primary_bh] = "bh_significant"
    return levels
