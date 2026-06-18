from __future__ import annotations

from typing import Iterable

JOINER = " :: "

_METAGPT_LOOP_ANCHOR = (
    "VERIFY_FAIL",
    "INFORM",
    "VERIFY_FAIL",
    "INFORM",
)


def iter_ngrams(sequence: list[str], n: int) -> Iterable[tuple[str, ...]]:
    if len(sequence) < n:
        return
    for i in range(len(sequence) - n + 1):
        yield tuple(sequence[i : i + n])


def _metagpt_verify_provide_key(g: tuple[str, ...]) -> tuple[str, ...] | None:
    vf, prov = "VERIFY_FAIL", "INFORM"
    if vf in g and prov in g:
        return _METAGPT_LOOP_ANCHOR
    return None


def normalized_ngram_for_export(
    g: tuple[str, ...],
    *,
    mas_name: str = "",
    n: int = 4,
) -> tuple[str, ...]:
    if len(g) != n:
        return g
    fw = (mas_name or "").lower()
    if fw == "metagpt" and n == 4:
        key = _metagpt_verify_provide_key(g)
        if key is not None:
            return key
    if fw == "hyperagent" and n == 4:
        err, plan, act = "ERROR", "PLAN", "ACT"
        vf, vp = "VERIFY_FAIL", "VERIFY_PASS"
        if err in g and plan in g and act in g and (vf in g or vp in g):
            return (err, plan, act, vf)

    if "REQUEST" in g and len(set(g)) == len(g):
        priority = {
            "REQUEST": 0,
            "PLAN": 1,
            "ACT": 2,
            "INFORM": 3,
            "VERIFY_PASS": 4,
            "VERIFY_FAIL": 5,
            "ERROR": 6,
            "TERMINATE": 7,
        }
        return tuple(sorted(g, key=lambda t: priority.get(t, 999)))
    return g


def ngram_presence_set(
    sequence: list[str],
    n: int,
    *,
    mas_name: str = "",
    normalize: bool = False,
) -> set[tuple[str, ...]]:
    raw = set(iter_ngrams(sequence, n))
    if not normalize:
        return raw
    return {normalized_ngram_for_export(g, mas_name=mas_name, n=n) for g in raw}


def format_ngram(g: tuple[str, ...], joiner: str = JOINER) -> str:
    return joiner.join(g)
