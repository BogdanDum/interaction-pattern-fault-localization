from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from rp_analysis import judge_prompt
from rp_analysis.judge_config import JUDGE_MODEL
from rp_analysis.judge_run import iter_jsonl
from rp_analysis.judge_study import JudgeStudySpec
from rp_analysis.judge_tasks import read_tasks_jsonl


def aggregate_trace_verdicts(
    results: list[dict[str, Any]],
    *,
    condition: str | None = None,
) -> list[dict[str, Any]]:
    """Roll occurrence-level judge rows up to one verdict per failing run."""
    filtered = [
        r
        for r in results
        if r.get("verdict") and r.get("outcome_fail_any")
        and (condition is None or r.get("condition") == condition)
    ]
    by_run: dict[str, list[dict[str, Any]]] = {}
    for row in filtered:
        run_id = str(row.get("mad_relative_path") or "")
        by_run.setdefault(run_id, []).append(row)

    trace_rows: list[dict[str, Any]] = []
    for run_id, rows in sorted(by_run.items(), key=lambda x: str(x[0])):
        trace_id = rows[0].get("trace_id")
        any_caused = any(judge_prompt.verdict_caused(r.get("verdict")) for r in rows)
        trace_verdict = "caused" if any_caused else "not_caused"
        caused_rows = [r for r in rows if judge_prompt.verdict_caused(r.get("verdict"))]
        representative = caused_rows[0] if caused_rows else rows[0]
        trace_rows.append(
            {
                "trace_id": trace_id,
                "condition": rows[0].get("condition"),
                "pattern": rows[0].get("pattern"),
                "pattern_rank": rows[0].get("pattern_rank"),
                "n_occurrences_judged": len(rows),
                "trace_verdict": trace_verdict,
                "any_hit": any_caused,
                "failure_summary": representative.get("failure_summary"),
                "justification": representative.get("justification"),
                "root_cause_span": representative.get("root_cause_span"),
                "root_cause_reason": representative.get("root_cause_reason"),
                "mad_relative_path": rows[0].get("mad_relative_path"),
                "model": rows[0].get("model"),
            }
        )
    return trace_rows


def trace_verdict_stats(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(trace_rows)
    if n == 0:
        return {
            "n_traces": 0,
            "caused_pct": 0.0,
            "not_caused_pct": 0.0,
            "counts": {},
        }
    counts: dict[str, int] = {}
    for r in trace_rows:
        v = str(r.get("trace_verdict", "unknown"))
        counts[v] = counts.get(v, 0) + 1
    return {
        "n_traces": n,
        "caused_pct": counts.get("caused", 0) / n,
        "not_caused_pct": counts.get("not_caused", 0) / n,
        "counts": counts,
    }


def _verdict_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "caused_pct": 0.0,
            "not_caused_pct": 0.0,
            "counts": {},
        }
    counts: dict[str, int] = {}
    for r in rows:
        v = str(r.get("verdict", "unknown"))
        counts[v] = counts.get(v, 0) + 1
    return {
        "n": n,
        "caused_pct": counts.get("caused", 0) / n,
        "not_caused_pct": counts.get("not_caused", 0) / n,
        "counts": counts,
    }


def summarize_trace_judge(
    tasks_path: Path,
    results_path: Path,
    *,
    out_csv: Path,
    out_report: Path,
    out_trace_csv: Path | None = None,
    run_tag: str | None = None,
    spec: JudgeStudySpec | None = None,
    model: str = JUDGE_MODEL,
) -> dict[str, Any]:
    """Write CSV summaries and a markdown report from task and result JSONL files."""
    tasks = read_tasks_jsonl(tasks_path)
    results = list(iter_jsonl(results_path)) if results_path.exists() else []

    judged = [r for r in results if r.get("verdict") and r.get("outcome_fail_any")]
    failing_tasks = [t for t in tasks if t.outcome_fail_any]
    triggered_failing_runs = [t for t in failing_tasks if t.triggered]
    n_failing_runs = len(failing_tasks)
    n_triggered_runs = len(triggered_failing_runs)

    trigger_rate = n_triggered_runs / n_failing_runs if n_failing_runs else 0.0
    occ_stats = _verdict_stats(judged)
    trace_rows = aggregate_trace_verdicts(judged)
    trace_stats = trace_verdict_stats(trace_rows)

    summary_rows = []
    distances: list[int] = []
    for r in judged:
        dist = r.get("localization_distance")
        if dist is not None:
            distances.append(int(dist))
        summary_rows.append(
            {
                "trace_id": r.get("trace_id"),
                "condition": r.get("condition"),
                "pattern": r.get("pattern"),
                "pattern_rank": r.get("pattern_rank"),
                "occurrence_start": r.get("occurrence_start"),
                "window_n": r.get("window_n"),
                "verdict": r.get("verdict"),
                "localization_distance": dist,
                "origin_start_in_window": r.get("origin_start_in_window"),
                "failure_summary": r.get("failure_summary"),
                "root_cause_span": r.get("root_cause_span"),
                "root_cause_reason": r.get("root_cause_reason"),
                "justification": r.get("justification"),
                "mad_relative_path": r.get("mad_relative_path"),
                "model": r.get("model"),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(out_csv, index=False)

    trace_csv_path = out_trace_csv or out_csv.parent / "trace_summary.csv"
    pd.DataFrame(trace_rows).to_csv(trace_csv_path, index=False)

    title = spec.label() if spec else "trace judge"
    tag_note = f" run_tag={run_tag}" if run_tag else ""
    report_lines = [
        f"# Judge report: {title}",
        "",
        f"Config: {model}, temperature=0, failing traces only.{tag_note}",
        "",
        "Metric definitions (per-run):",
        "- **Ranking**: first occurrence of rank-k failure-associated pattern.",
        "- **Random baseline**: one random fixed-length window per triggered failing run.",
        "- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.",
        "- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).",
        f"- **Judge window width**: {spec.effective_window_n() if spec else 'n'} tokens.",
        "",
        "## Coverage",
        f"- Task rows: {len(tasks)} ({len(failing_tasks)} failing-task rows)",
        f"- Failing runs: {n_failing_runs}",
        f"- Triggered runs: {n_triggered_runs}",
        f"- Occurrence-level judge calls: {occ_stats['n']}",
        f"- Run-level units: {trace_stats['n_traces']}",
        "",
        "## Run-level metrics (primary)",
        f"- Trigger rate (failing runs): {trigger_rate:.1%}",
        f"- **Caused | triggered**: {occ_stats['caused_pct']:.1%} "
        f"({occ_stats['counts'].get('caused', 0)}/{occ_stats['n']})",
        f"- Run caused rate (any-hit): {trace_stats['caused_pct']:.1%}",
        f"- Not caused rate: {trace_stats['not_caused_pct']:.1%}",
    ]
    if distances:
        mean_d = sum(distances) / len(distances)
        report_lines.append(f"- Mean localization distance: {mean_d:.2f}")
    report_lines.extend(
        [
            "",
            "## Occurrence-level verdict breakdown",
        ]
    )
    for verdict, count in sorted(occ_stats["counts"].items()):
        pct = count / occ_stats["n"] if occ_stats["n"] else 0
        report_lines.append(f"- {verdict}: {count} ({pct:.1%})")

    caused_examples = [r for r in trace_rows if r.get("trace_verdict") == "caused"][:3]
    if caused_examples:
        report_lines.extend(["", "## Example justifications (trace caused)"])
        for r in caused_examples:
            report_lines.append(f"- trace_id={r.get('trace_id')}: {r.get('justification', '')}")

    out_report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "study": title,
        "n_tasks": len(tasks),
        "n_failing": len(failing_tasks),
        "n_triggered_failing": n_triggered_runs,
        "n_failing_runs": n_failing_runs,
        "trigger_rate": trigger_rate,
        "n_occurrence_judged": occ_stats["n"],
        "n_judged": trace_stats["n_traces"],
        "caused_pct": trace_stats["caused_pct"],
        "not_caused_pct": trace_stats["not_caused_pct"],
        "occurrence_caused_pct": occ_stats["caused_pct"],
        "mean_localization_distance": sum(distances) / len(distances) if distances else None,
        "verdict_counts": trace_stats["counts"],
        "occurrence_verdict_counts": occ_stats["counts"],
    }

_trace_verdict_stats = trace_verdict_stats
