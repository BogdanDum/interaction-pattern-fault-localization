from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from rp_analysis import judge_metrics, judge_prompt
from rp_analysis.judge_report import aggregate_trace_verdicts, _trace_verdict_stats
from rp_analysis.judge_run import iter_jsonl
from rp_analysis.paths import repo_root
from rp_analysis.study import JUDGE_RESULTS

STUDY_LABELS = {
    ("cross_task", "MetaGPT", "n4", "markov"): "MetaGPT cross-task Markov rank-1 (n=4)",
    ("cross_task", "MetaGPT", "n4", "rank1"): "MetaGPT cross-task rank-1 (n=4)",
    ("cross_task", "MetaGPT", "n4", "random"): "MetaGPT cross-task random (n=4)",
    ("cross_task", "MetaGPT", "n3", "rank1"): "MetaGPT cross-task rank-1 (n=3)",
    ("cross_task", "MetaGPT", "n3", "random"): "MetaGPT cross-task random (n=3)",
    ("cross_task", "MetaGPT", "n2", "rank1"): "MetaGPT cross-task rank-1 (n=2)",
    ("cross_task", "MetaGPT", "n2", "random"): "MetaGPT cross-task random (n=2)",
    ("cross_task", "MetaGPT", "n5", "rank1"): "MetaGPT cross-task rank-1 (n=5)",
    ("cross_task", "HyperAgent", "n4", "rank1"): "HyperAgent cross-task rank-1 (n=4)",
    ("cross_task", "HyperAgent", "n4", "random"): "HyperAgent cross-task random (n=4)",
    ("cross_task", "HyperAgent", "n3", "rank1"): "HyperAgent cross-task rank-1 (n=3)",
    ("cross_task", "HyperAgent", "n2", "rank1"): "HyperAgent cross-task rank-1 (n=2)",
    ("cross_task", "HyperAgent", "n5", "rank1"): "HyperAgent cross-task rank-1 (n=5)",
    ("cross_task", "HyperAgent", "n4", "sbfl"): "HyperAgent cross-task top-3 (n=4)",
    ("same_task", "HyperAgent", "n4", "rank1"): "HyperAgent RQ3 same-task rank-1 (n=4)",
    ("same_task", "HyperAgent", "n4", "random"): "HyperAgent RQ3 same-task random (n=4)",
    ("same_task", "HyperAgent", "n3", "rank1"): "HyperAgent RQ3 same-task rank-1 (n=3)",
    ("same_task", "HyperAgent", "n4", "sbfl"): "HyperAgent RQ3 same-task top-3 (n=4)",
    ("cross_task", "AG2", "n4", "rank1"): "AG2 cross-task rank-1 (n=4)",
    ("cross_task", "AG2", "n4", "random"): "AG2 cross-task random (n=4)",
}

from rp_analysis.judge_config import JUDGE_MODEL


def _parse_study_dir(path: Path) -> tuple[str, str, str, str] | None:
    parts = path.parts
    for study_id in ("cross_task", "same_task"):
        try:
            idx = parts.index(study_id)
            framework = parts[idx + 1]
            n_part = parts[idx + 2]
            subdir = parts[idx + 3]
            return study_id, framework, n_part, subdir
        except (ValueError, IndexError):
            continue
    return None


def _mean_localization_distance(summary_csv: Path) -> float | None:
    if not summary_csv.exists():
        return None
    df = pd.read_csv(summary_csv)
    if "localization_distance" not in df.columns:
        return None
    vals = df["localization_distance"].dropna()
    if vals.empty:
        return None
    return float(vals.mean())


def _judge_metrics_from_results(
    results_path: Path,
    tasks_path: Path,
    *,
    trace_ids: set | None = None,
) -> dict[str, float | None]:
    if not results_path.exists():
        return {}
    results = judge_metrics.load_judged_results(results_path)
    tasks = judge_metrics.load_tasks(tasks_path) if tasks_path.exists() else []
    m = judge_metrics.metrics_for_condition(results, tasks, trace_ids=trace_ids)
    out = {
        "trigger_rate": round(m["trigger_rate"] * 100, 1),
        "occurrence_caused_pct": round(m["verdict_caused_pct"] * 100, 1),
        "occurrence_caused_n": m.get("verdict_caused_n"),
        "n_occurrences_judged": m.get("n"),
    }
    if trace_ids is not None:
        out["subset_n_traces"] = len(trace_ids)
    return out


def _load_row(path: Path) -> dict | None:
    key = _parse_study_dir(path.parent)
    if key is None:
        return None
    study_id, framework, n_part, subdir = key
    if subdir == "rank2":
        return None
    label = STUDY_LABELS.get(key, f"{study_id}/{framework}/{n_part}/{subdir}")

    trace_summary_path = path.parent / "trace_summary.csv"
    summary_path = path.parent / "summary.csv"
    results_path = path.parent / "results.jsonl"
    tasks_path = path.parent / "tasks.jsonl"
    if trace_summary_path.exists():
        df = pd.read_csv(trace_summary_path)
        stats = _trace_verdict_stats(df.to_dict("records"))
    elif results_path.exists():
        rows = [r for r in iter_jsonl(results_path) if r.get("verdict") and r.get("outcome_fail_any")]
        trace_rows = aggregate_trace_verdicts(rows)
        stats = _trace_verdict_stats(trace_rows)
    else:
        return None

    if stats["n_traces"] == 0:
        return None

    n_occ = 0
    if results_path.exists():
        n_occ = sum(1 for r in iter_jsonl(results_path) if r.get("verdict") and r.get("outcome_fail_any"))

    mean_dist = _mean_localization_distance(summary_path)
    judge_metrics_extra = _judge_metrics_from_results(results_path, tasks_path)

    n_failing_runs = None
    n_triggered_runs = None
    if tasks_path.exists():
        tasks = judge_metrics.load_tasks(tasks_path)
        trig = judge_metrics.trigger_rate_from_tasks(tasks)
        n_failing_runs = trig.get("n_failing_runs")
        n_triggered_runs = trig.get("n_triggered_runs")

    occ_rows = (
        [r for r in iter_jsonl(results_path) if r.get("verdict") and r.get("outcome_fail_any")]
        if results_path.exists()
        else []
    )
    occ_caused_n = sum(1 for r in occ_rows if judge_prompt.verdict_caused(r.get("verdict")))
    n_occ_judged = len(occ_rows)
    caused_triggered = f"{occ_caused_n}/{n_occ_judged}" if n_occ_judged else None
    occurrence_caused_pct = round(occ_caused_n / n_occ_judged * 100, 1) if n_occ_judged else None

    caused_n = stats["counts"].get("caused", 0)
    n_judged = stats["n_traces"]
    return {
        "label": label,
        "study_id": study_id,
        "framework": framework,
        "n": int(n_part.replace("n", "")),
        "condition": subdir,
        "n_traces": n_judged,
        "n_failing_runs": n_failing_runs,
        "n_triggered_runs": n_triggered_runs,
        "n_occurrence_calls": n_occ,
        "caused_pct": occurrence_caused_pct if occurrence_caused_pct is not None else round(stats["caused_pct"] * 100, 1),
        "not_caused_pct": round(stats["not_caused_pct"] * 100, 1),
        "caused_n": occ_caused_n if n_occ_judged else caused_n,
        "not_caused_n": stats["counts"].get("not_caused", 0),
        "caused_triggered": caused_triggered,
        "mean_localization_distance": round(mean_dist, 2) if mean_dist is not None else None,
        **judge_metrics_extra,
    }


def consolidate(base: Path, *, model: str = JUDGE_MODEL) -> tuple[pd.DataFrame, str]:
    rows = []
    seen_dirs: set[Path] = set()
    for summary in sorted(base.rglob("trace_summary.csv")):
        if summary.parent in seen_dirs:
            continue
        seen_dirs.add(summary.parent)
        row = _load_row(summary)
        if row:
            rows.append(row)
    if not rows:
        for summary in sorted(base.rglob("summary.csv")):
            parent = summary.parent
            if parent in seen_dirs:
                continue
            seen_dirs.add(parent)
            row = _load_row(summary)
            if row:
                rows.append(row)

    if not rows:
        raise SystemExit(f"No judge results found under {base}")

    df = pd.DataFrame(rows)
    order = {v: i for i, v in enumerate(STUDY_LABELS.values())}
    df["_ord"] = df["label"].map(lambda x: order.get(x, 999))
    df = df.sort_values("_ord").drop(columns=["_ord"])

    if "rq4" in str(base):
        version = "v6"
    elif "judge_study_v5" in str(base):
        version = "v5"
    elif "judge_study_v4" in str(base):
        version = "v4"
    elif "judge_study_v3" in str(base):
        version = "v3"
    else:
        version = "v2"
    report_lines = [
        f"# LLM Judge — Full Consolidated Report ({version})",
        "",
        f"Model: {model}, temperature=0. Judge window width = 4.",
        "",
        "Metrics:",
    ]
    if version == "v6":
        report_lines.extend(
            [
                "- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).",
                "- **Caused | triggered** (headline): judge `caused` / triggered failing windows",
                "- **Trigger rate**: failing runs where rank-1 pattern appears",
                "- **Judge rubric**: single-phase; highlighted window contains initiating fault",
            ]
        )
    elif version in ("v4", "v5"):
        rubric = (
            "single-phase: highlighted interaction contains initiating fault"
            if version == "v5"
            else "window contains failure origin (two-phase)"
        )
        report_lines.extend(
            [
                "- **Caused | triggered** (headline): judge `caused` / triggered failing windows",
                "- **Trigger rate**: failing traces where pattern fires",
                f"- **Judge rubric (v5)**: {rubric}" if version == "v5" else "",
            ]
        )
        report_lines = [line for line in report_lines if line]
    if version == "v6":
        master_header = (
            "| Label | Study | n | Cond | Failing runs | Triggered | Trigger rate | "
            "Caused | triggered | Mean dist |"
        )
        master_sep = (
            "|-------|-------|---|------|--------------|-----------|--------------|"
            "-----------------|-----------|"
        )
    else:
        master_header = (
            "| Label | Study | n | Cond | N judged | Trigger | Occ caused | Mean dist |"
        )
        master_sep = "|-------|-------|---|------|----------|---------|------------|-----------|"
    report_lines.extend(
        [
            "",
            "## Master table (all conditions)",
            "",
            master_header,
            master_sep,
        ]
    )
    for _, r in df.iterrows():
        occ_val = r.get("caused_pct", "—")
        dist = r.get("mean_localization_distance")
        dist_s = f"{dist}" if dist is not None and pd.notna(dist) else "—"
        if version == "v6":
            fail_r = r.get("n_failing_runs")
            trig_r = r.get("n_triggered_runs")
            fail_s = int(fail_r) if fail_r is not None and pd.notna(fail_r) else "—"
            trig_s = int(trig_r) if trig_r is not None and pd.notna(trig_r) else "—"
            ct = r.get("caused_triggered", "—")
            report_lines.append(
                f"| {r['label']} | {r['study_id']} | {int(r['n'])} | {r['condition']} | "
                f"{fail_s} | {trig_s} | {r.get('trigger_rate', '—')}% | "
                f"{ct} ({occ_val}%) | {dist_s} |"
            )
        else:
            report_lines.append(
                f"| {r['label']} | {r['study_id']} | {int(r['n'])} | {r['condition']} | "
                f"{int(r['n_traces'])} | {r.get('trigger_rate', '—')}% | "
                f"{occ_val}% | {dist_s} |"
            )

    def _section(title: str, subset: pd.DataFrame) -> None:
        if subset.empty:
            return
        report_lines.extend(["", f"## {title}", ""])
        if version == "v6":
            report_lines.append(
                "| Label | Failing | Triggered | Trigger | Caused | triggered | Mean dist |"
            )
            report_lines.append(
                "|-------|---------|-----------|---------|-----------------|-----------|"
            )
            for _, r in subset.iterrows():
                dist = r.get("mean_localization_distance")
                dist_s = f"{dist}" if dist is not None and pd.notna(dist) else "—"
                report_lines.append(
                    f"| {r['label']} | {r.get('n_failing_runs', '—')} | {r.get('n_triggered_runs', '—')} | "
                    f"{r.get('trigger_rate', '—')}% | {r.get('caused_triggered', '—')} ({r['caused_pct']}%) | "
                    f"{dist_s} |"
                )
        elif version in ("v4", "v5"):
            report_lines.append(
                "| Label | Trigger | Occ caused | Mean dist |"
            )
            report_lines.append(
                "|-------|---------|------------|-----------|"
            )
            for _, r in subset.iterrows():
                dist = r.get("mean_localization_distance")
                dist_s = f"{dist}" if dist is not None and pd.notna(dist) else "—"
                report_lines.append(
                    f"| {r['label']} | {r.get('trigger_rate', '—')}% | "
                    f"{r['caused_pct']}% | {dist_s} |"
                )

    metagpt_ct = df[(df["study_id"] == "cross_task") & (df["framework"] == "MetaGPT")]
    _section("MetaGPT cross-task — rank-1 n-sensitivity", metagpt_ct[metagpt_ct["condition"] == "rank1"])
    _section(
        "MetaGPT cross-task — random baselines (paired)",
        metagpt_ct[metagpt_ct["condition"] == "random"],
    )

    ha_ct = df[(df["study_id"] == "cross_task") & (df["framework"] == "HyperAgent")]
    _section("HyperAgent cross-task (MAST pooled)", ha_ct[ha_ct["condition"].isin(["rank1", "random"])])

    ha_rq3 = df[(df["study_id"] == "same_task") & (df["framework"] == "HyperAgent")]
    _section("HyperAgent RQ3 same-task", ha_rq3[ha_rq3["condition"].isin(["rank1", "random"])])

    n5 = df[df["n"] == 5]
    if not n5.empty:
        report_lines.extend(["", "## Appendix: n=5", ""])
        for _, r in n5.iterrows():
            report_lines.append(
                f"- {r['label']}: caused/triggered={r['caused_pct']}%"
            )

    mg4 = metagpt_ct[(metagpt_ct["condition"] == "rank1") & (metagpt_ct["n"] == 4)]
    mrand4 = metagpt_ct[(metagpt_ct["condition"] == "random") & (metagpt_ct["n"] == 4)]
    if not mg4.empty and not mrand4.empty:
        report_lines.extend(
            [
                "",
                "## Key findings",
                "",
                f"- MetaGPT cross-task headline (SBFL rank-1): caused/triggered n=4 "
                f"{mg4.iloc[0].get('caused_triggered')} ({mg4.iloc[0].get('caused_pct')}%) vs random "
                f"{mrand4.iloc[0].get('caused_triggered')} ({mrand4.iloc[0].get('caused_pct')}%) (paired).",
            ]
        )
    rq3_r1 = ha_rq3[(ha_rq3["condition"] == "rank1") & (ha_rq3["n"] == 4)]
    rq3_rand = ha_rq3[(ha_rq3["condition"] == "random") & (ha_rq3["n"] == 4)]
    if not rq3_r1.empty:
        report_lines.append(
            f"- HyperAgent RQ3 rank-1 n=4: caused/triggered "
            f"{rq3_r1.iloc[0].get('caused_triggered')} ({rq3_r1.iloc[0]['caused_pct']}%)."
        )
    if not rq3_rand.empty:
        report_lines.append(
            f"- HyperAgent RQ3 random n=4: caused/triggered "
            f"{rq3_rand.iloc[0].get('caused_triggered')} ({rq3_rand.iloc[0].get('caused_pct')}%)."
        )

    return df, "\n".join(report_lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate judge study results")
    parser.add_argument(
        "--base",
        type=Path,
        default=repo_root() / JUDGE_RESULTS,
    )
    args = parser.parse_args()

    errors = judge_metrics.validate_study_models(args.base, expected=JUDGE_MODEL)
    if errors:
        print(f"WARNING: {len(errors)} model mismatches (expected {JUDGE_MODEL})", file=sys.stderr)

    df, report = consolidate(args.base, model=JUDGE_MODEL)
    out_csv = args.base / "summary.csv"
    out_md = args.base / "report.md"
    df.to_csv(out_csv, index=False)
    out_md.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {out_csv} and {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
