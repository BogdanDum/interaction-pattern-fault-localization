from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from rp_analysis import judge_prompt
from rp_analysis.judge_run import iter_jsonl

from rp_analysis.judge_config import EXPECTED_MODEL, JUDGE_BASE_URL, JUDGE_MODEL


def _occurrence_rank_key(row: dict[str, Any]) -> tuple[int, int, int]:
    caused = 1 if judge_prompt.verdict_caused(row.get("verdict")) else 0
    dist = row.get("localization_distance")
    if dist is None:
        dist_score = 0
    else:
        dist_score = -int(dist)
    origin = 1 if row.get("origin_start_in_window") is True else 0
    return (caused, dist_score, origin)


def aggregate_occurrence_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    distances: list[int] = []
    for row in rows:
        dist = row.get("localization_distance")
        if dist is not None:
            distances.append(int(dist))
    n = len(rows)
    verdict_caused_n = sum(1 for row in rows if judge_prompt.verdict_caused(row.get("verdict")))
    return {
        "n": n,
        "verdict_caused_n": verdict_caused_n,
        "verdict_caused_pct": verdict_caused_n / n if n else 0.0,
        "mean_localization_distance": sum(distances) / len(distances) if distances else None,
    }


def trace_key(row: dict[str, Any]) -> tuple[Any, Any]:
    return (row.get("trace_id"), row.get("mad_relative_path"))


def run_key(row: dict[str, Any]) -> str:
    return str(row.get("mad_relative_path") or "")


def dedupe_best_per_trace(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in rows:
        key = trace_key(row)
        prev = best.get(key)
        if prev is None or _occurrence_rank_key(row) > _occurrence_rank_key(prev):
            best[key] = row
    return [best[k] for k in sorted(best, key=lambda x: (str(x[0]), str(x[1] or "")))]


def failing_run_keys_from_tasks(tasks: list[dict[str, Any]]) -> set[str]:
    return {run_key(t) for t in tasks if t.get("outcome_fail_any")}


def triggered_run_keys_from_tasks(tasks: list[dict[str, Any]]) -> set[str]:
    return {
        run_key(t)
        for t in tasks
        if t.get("outcome_fail_any") and t.get("triggered")
    }


def trigger_rate_from_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    failing = [t for t in tasks if t.get("outcome_fail_any")]
    unique_failing = failing_run_keys_from_tasks(failing)
    triggered = triggered_run_keys_from_tasks(failing)
    n_unique = len(unique_failing)
    return {
        "n_failing_runs": n_unique,
        "n_triggered_runs": len(triggered),
        "n_failing_unique_traces": n_unique,
        "n_triggered_unique_traces": len(triggered),
        "trigger_rate": len(triggered) / n_unique if n_unique else 0.0,
    }


def triggered_trace_ids_from_tasks(tasks: list[dict[str, Any]]) -> set[str]:
    return triggered_run_keys_from_tasks(tasks)


def unique_triggered_keys_from_tasks(tasks: list[dict[str, Any]]) -> set[tuple[Any, Any]]:
    return {
        (t.get("trace_id"), t.get("mad_relative_path"))
        for t in tasks
        if t.get("outcome_fail_any") and t.get("triggered")
    }


def load_judged_results(path: Path) -> list[dict[str, Any]]:
    return [
        r
        for r in iter_jsonl(path)
        if r.get("verdict") and r.get("outcome_fail_any")
    ]


def load_tasks(path: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def core_and_marginal_sets(
    tasks_by_n: dict[int, list[dict[str, Any]]],
) -> tuple[set[str], set[str]]:
    t2 = triggered_run_keys_from_tasks(tasks_by_n.get(2, []))
    t3 = triggered_run_keys_from_tasks(tasks_by_n.get(3, []))
    t4 = triggered_run_keys_from_tasks(tasks_by_n.get(4, []))
    core = t3 | t4
    marginal = t2 - core
    return core, marginal


def filter_results_by_trace_ids(
    rows: list[dict[str, Any]],
    trace_ids: set[Any],
) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("trace_id") in trace_ids]


def filter_results_by_keys(
    rows: list[dict[str, Any]],
    keys: set[tuple[Any, Any]],
) -> list[dict[str, Any]]:
    return [r for r in rows if trace_key(r) in keys]


def metrics_for_condition(
    results: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    trace_ids: set[Any] | None = None,
    keys: set[tuple[Any, Any]] | None = None,
) -> dict[str, Any]:
    """Compute caused rate, localization distance, and trigger stats for a task subset."""
    rows = list(results)
    if keys is not None:
        rows = filter_results_by_keys(rows, keys)
    elif trace_ids is not None:
        rows = filter_results_by_trace_ids(rows, trace_ids)
    occ = aggregate_occurrence_stats(rows)
    deduped = dedupe_best_per_trace(rows)
    trig = trigger_rate_from_tasks(tasks)
    if trace_ids is not None:
        failing = [t for t in tasks if t.get("outcome_fail_any")]
        unique_failing = failing_run_keys_from_tasks(failing)
        triggered_in_set = trace_ids & triggered_run_keys_from_tasks(tasks)
        trig = {
            "n_failing_runs": len(unique_failing),
            "n_triggered_runs": len(triggered_in_set),
            "n_failing_unique_traces": len(unique_failing),
            "n_triggered_unique_traces": len(triggered_in_set),
            "trigger_rate": len(triggered_in_set) / len(trace_ids) if trace_ids else 0.0,
        }
    return {
        **occ,
        "n_trace_deduped": len(deduped),
        **trig,
    }


def paired_n_sensitivity(
    results_by_n: dict[int, list[dict[str, Any]]],
    tasks_by_n: dict[int, list[dict[str, Any]]],
) -> pd.DataFrame:
    """Tabulate judge metrics across window sizes for all triggered, core, and marginal sets."""
    core, marginal = core_and_marginal_sets(tasks_by_n)
    rows = []
    for n in sorted(results_by_n):
        tasks = tasks_by_n.get(n, [])
        results = results_by_n[n]
        for label, trace_ids in (
            ("all_triggered", None),
            ("core_C", core),
            ("marginal_M", marginal),
        ):
            if label == "all_triggered":
                m = metrics_for_condition(results, tasks)
            else:
                m = metrics_for_condition(results, tasks, trace_ids=trace_ids)
            rows.append(
                {
                    "n": n,
                    "subset": label,
                    "n_occurrences": m["n"],
                    "n_trace_deduped": m["n_trace_deduped"],
                    "trigger_rate": m["trigger_rate"],
                    "caused_n": m["verdict_caused_n"],
                    "caused_triggered": (
                        f"{m['verdict_caused_n']}/{m['n']}" if m["n"] else None
                    ),
                    "caused_pct": round(m["verdict_caused_pct"] * 100, 1),
                    "mean_localization_distance": (
                        round(m["mean_localization_distance"], 2)
                        if m.get("mean_localization_distance") is not None
                        else None
                    ),
                }
            )
    return pd.DataFrame(rows)


def paired_per_trace_table(
    results_by_n: dict[int, list[dict[str, Any]]],
    tasks_by_n: dict[int, list[dict[str, Any]]],
) -> pd.DataFrame:
    """Align per-trace best verdicts across n=2,3,4 for traces in the core triggered set."""
    core, _ = core_and_marginal_sets(tasks_by_n)
    keys: set[tuple[Any, Any]] = set()
    for n in (2, 3, 4):
        for t in tasks_by_n.get(n, []):
            if t.get("trace_id") in core and t.get("triggered"):
                keys.add(trace_key(t))

    rows = []
    for key in sorted(keys, key=lambda x: (str(x[0]), str(x[1] or ""))):
        trace_id, mad_rel = key
        row: dict[str, Any] = {"trace_id": trace_id, "mad_relative_path": mad_rel}
        for n in (2, 3, 4):
            results = results_by_n.get(n, [])
            matched = [r for r in results if trace_key(r) == key]
            if not matched:
                row[f"n{n}_verdict"] = None
                row[f"n{n}_distance"] = None
                continue
            best = dedupe_best_per_trace(matched)[0]
            row[f"n{n}_verdict"] = best.get("verdict")
            row[f"n{n}_distance"] = best.get("localization_distance")
        rows.append(row)
    return pd.DataFrame(rows)


def validate_model_in_jsonl(path: Path, *, expected: str = EXPECTED_MODEL) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return errors
    for i, row in enumerate(iter_jsonl(path)):
        model = row.get("model")
        if model and model != expected:
            errors.append(f"{path}:{i + 1} model={model!r} expected {expected!r}")
    return errors


def validate_study_models(base: Path, *, expected: str = EXPECTED_MODEL) -> list[str]:
    errors: list[str] = []
    for name in ("results.jsonl",):
        for p in base.rglob(name):
            errors.extend(validate_model_in_jsonl(p, expected=expected))
    return errors
