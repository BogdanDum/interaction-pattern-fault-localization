from __future__ import annotations

import json
import random
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from rp_analysis.datasets import load_traces_from_manifest, tokens_for_trace_row
from rp_analysis.judge_run import find_occurrences, iter_jsonl
from rp_analysis.judge_study import (
    JUDGE_STUDY_DIR,
    PILOT_DEFAULT_N,
    PILOT_RANDOM_SEED,
    TOP_K,
    JudgeStudySpec,
    TraceTaskRecord,
    make_task_key,
    load_patterns_by_rank,
    load_top_patterns,
    study_output_dir,
    study_paths,
)
from rp_analysis.paths import repo_path, repo_relative, repo_root


def _select_pattern_for_trace(
    tokens: list[str],
    ranked_patterns: list[tuple[int, str]],
    *,
    pattern_mode: str,
) -> tuple[str, int] | None:
    """Pick the highest-ranked pattern present in a trace under the study's selection mode."""
    if pattern_mode == "fixed_ranks":
        for rank, pattern in ranked_patterns:
            if find_occurrences(tokens, pattern):
                return pattern, rank
        return None

    best: tuple[int, int, str] | None = None
    for rank, pattern in ranked_patterns:
        hits = find_occurrences(tokens, pattern)
        if not hits:
            continue
        key = (rank, min(hits))
        if best is None or key < (best[0], best[1]):
            best = (rank, min(hits), pattern)
    if best is None:
        return None
    return best[2], best[0]


def _judge_condition(spec: JudgeStudySpec) -> str:
    if spec.condition == "random":
        return "random_control"
    return "failing_candidate"


def _base_record_fields(
    row: pd.Series,
    mad_path: Path,
    outcome_fail: bool,
    spec: JudgeStudySpec,
    condition: str,
) -> dict[str, Any]:
    return {
        "trace_id": row.get("trace_id"),
        "mad_path": repo_relative(mad_path),
        "mad_relative_path": str(row.get("mad_relative_path", "")),
        "mas_name": str(row.get("mas_name", spec.framework)),
        "benchmark_name": str(row.get("benchmark_name", "")),
        "outcome_fail_any": outcome_fail,
        "condition": condition,
        "study_id": spec.study_id,
        "framework": spec.framework,
        "window_n": spec.effective_window_n(),
    }


def _tokens_for_trace_row(row: pd.Series, mad_path: Path, root: Path) -> list[str]:
    return tokens_for_trace_row(row, root)


def _tasks_for_trace_sbfl(
    row: pd.Series,
    ranked_patterns: list[tuple[int, str]],
    spec: JudgeStudySpec,
    root: Path,
) -> list[TraceTaskRecord]:
    """Build triggered or untriggered SBFL judge tasks for one trace from ranked patterns."""
    mad_path = repo_path(row["mad_path"], root)
    outcome_fail = bool(row["outcome_fail_any"])
    condition = _judge_condition(spec)
    base = _base_record_fields(row, mad_path, outcome_fail, spec, condition)

    tokens = _tokens_for_trace_row(row, mad_path, root)
    selected = _select_pattern_for_trace(
        tokens,
        ranked_patterns,
        pattern_mode=spec.pattern_mode,
    )

    if selected is None:
        return [
            TraceTaskRecord(
                **base,
                triggered=False,
                task_key=make_task_key(
                    base["mad_relative_path"], condition, None, None, spec.effective_window_n()
                ),
            )
        ]

    pattern, rank = selected
    hits = find_occurrences(tokens, pattern)
    if not hits:
        return [
            TraceTaskRecord(
                **base,
                triggered=False,
                task_key=make_task_key(
                    base["mad_relative_path"], condition, None, None, spec.effective_window_n()
                ),
            )
        ]
    start = min(hits)
    return [
        TraceTaskRecord(
            **base,
            triggered=True,
            pattern=pattern,
            pattern_rank=rank,
            occurrence_start=start,
            tokens=tokens,
            task_key=make_task_key(
                base["mad_relative_path"], condition, rank, start, spec.effective_window_n()
            ),
        )
    ]


def _triggered_failing_sbfl_tasks(tasks: list[TraceTaskRecord]) -> list[TraceTaskRecord]:
    return [rec for rec in tasks if rec.outcome_fail_any and rec.triggered]


def build_random_tasks_from_sbfl(
    sbfl_tasks: list[TraceTaskRecord],
    spec: JudgeStudySpec,
    root: Path | None = None,
) -> list[TraceTaskRecord]:
    """Pair each triggered failing SBFL run with one seeded random window of the same width."""
    root = root or repo_root()
    out: list[TraceTaskRecord] = []
    n = spec.effective_window_n()

    for rec in _triggered_failing_sbfl_tasks(sbfl_tasks):
        mad_path = repo_path(rec.mad_path, root)
        tokens = list(rec.tokens)
        path_seed = hash(rec.mad_relative_path) % (2**31)
        rng = random.Random(spec.seed + path_seed)
        max_start = len(tokens) - n
        late_start = max(0, (2 * len(tokens)) // 3)
        if late_start > max_start:
            late_start = max(0, len(tokens) // 2)
        if late_start > max_start:
            late_start = 0
        start = rng.randint(late_start, max_start)
        condition = "random_control"
        out.append(
            TraceTaskRecord(
                trace_id=rec.trace_id,
                mad_path=repo_relative(mad_path),
                mad_relative_path=rec.mad_relative_path,
                mas_name=rec.mas_name,
                benchmark_name=rec.benchmark_name,
                outcome_fail_any=True,
                triggered=True,
                pattern="RANDOM",
                pattern_rank=None,
                occurrence_start=start,
                condition=condition,
                study_id=spec.study_id,
                framework=spec.framework,
                window_n=n,
                tokens=tokens,
                task_key=make_task_key(rec.mad_relative_path, condition, None, start, n),
            )
        )
    return out


def apply_pilot_sample(
    tasks: list[TraceTaskRecord],
    *,
    pilot_n: int,
    seed: int = PILOT_RANDOM_SEED,
) -> list[TraceTaskRecord]:
    """Subsample triggered failing runs to a fixed pilot count using a reproducible seed."""
    triggered_failing_ids: list[Any] = []
    seen: set[Any] = set()
    for rec in tasks:
        if rec.outcome_fail_any and rec.triggered and rec.trace_id not in seen:
            seen.add(rec.trace_id)
            triggered_failing_ids.append(rec.trace_id)

    n_pick = min(int(pilot_n), len(triggered_failing_ids))
    rng = random.Random(seed)
    picked = set(rng.sample(triggered_failing_ids, n_pick))
    out: list[TraceTaskRecord] = []
    seen_pick: set[Any] = set()
    for rec in tasks:
        if rec.trace_id not in picked:
            continue
        if rec.trace_id in seen_pick:
            continue
        seen_pick.add(rec.trace_id)
        out.append(rec)
    return out


def build_study_tasks(
    spec: JudgeStudySpec,
    *,
    rankings_path: Path | None = None,
    artifacts_dir: Path | None = None,
    pair_from: Path | None = None,
    repo: Path | None = None,
    pilot: bool = False,
    pilot_n: int = PILOT_DEFAULT_N,
) -> list[TraceTaskRecord]:
    """Build judge task rows for an SBFL or random-control study from rankings and artifacts."""
    root = repo or repo_root()
    if spec.condition == "random":
        if pair_from is None:
            sbfl_spec = JudgeStudySpec(
                study_id=spec.study_id,
                framework=spec.framework,
                n=spec.n,
                condition="sbfl",
                pattern_mode=spec.pattern_mode,
                pattern_ranks=list(spec.pattern_ranks),
                top_k=spec.top_k,
                seed=spec.seed,
                judge_window_n=spec.judge_window_n,
            )
            pair_from = study_output_dir(sbfl_spec, root) / "tasks.jsonl"
        sbfl_tasks = read_tasks_jsonl(pair_from)
        tasks = build_random_tasks_from_sbfl(sbfl_tasks, spec, root)
        if pilot:
            tasks = apply_pilot_sample(tasks, pilot_n=pilot_n, seed=spec.seed)
        return tasks

    default_rankings, default_artifacts = study_paths(spec, root)
    rankings_path = rankings_path or default_rankings
    artifacts_dir = artifacts_dir or default_artifacts

    if spec.pattern_mode == "fixed_ranks":
        ranked_patterns = load_patterns_by_rank(rankings_path, spec.pattern_ranks)
    else:
        ranked_patterns = load_top_patterns(rankings_path, spec.top_k)

    traces = load_traces_from_manifest(artifacts_dir, root=root)
    traces["trace_id"] = traces["trace_id"].astype(int)
    tasks: list[TraceTaskRecord] = []
    for _, row in traces.iterrows():
        tasks.extend(_tasks_for_trace_sbfl(row, ranked_patterns, spec, root))

    if pilot:
        tasks = apply_pilot_sample(tasks, pilot_n=pilot_n, seed=spec.seed)
    return tasks


def build_trace_tasks(
    *,
    rankings_path: Path,
    artifacts_dir: Path,
    pilot: bool = False,
    pilot_n: int = PILOT_DEFAULT_N,
    repo: Path | None = None,
) -> list[TraceTaskRecord]:
    spec = JudgeStudySpec("cross_task", "MetaGPT", 4, top_k=TOP_K)
    return build_study_tasks(
        spec,
        rankings_path=rankings_path,
        artifacts_dir=artifacts_dir,
        repo=repo,
        pilot=pilot,
        pilot_n=pilot_n,
    )


def write_tasks_jsonl(tasks: Iterable[TraceTaskRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task.to_jsonable(), ensure_ascii=False) + "\n")


def read_tasks_jsonl(path: Path) -> list[TraceTaskRecord]:
    rows = list(iter_jsonl(path))
    records = []
    for row in rows:
        if "task_key" not in row:
            row["task_key"] = make_task_key(
                str(row.get("mad_relative_path", "")),
                row.get("condition", "failing_candidate"),
                row.get("pattern_rank"),
                row.get("occurrence_start"),
                row.get("window_n"),
            )
        records.append(TraceTaskRecord(**row))
    return records


def write_manifest(
    path: Path,
    spec: JudgeStudySpec,
    *,
    rankings_path: Path,
    artifacts_dir: Path | None,
    model: str,
    pilot: bool = False,
    pilot_n: int | None = None,
) -> None:
    manifest = {
        "spec": asdict(spec),
        "rankings_path": repo_relative(rankings_path),
        "artifacts_manifest_path": (
            repo_relative(artifacts_dir / "manifest.json") if artifacts_dir else None
        ),
        "model": model,
        "temperature": 0.0,
        "judge_study_dir": JUDGE_STUDY_DIR,
        "pilot": pilot,
        "pilot_n": pilot_n,
        "aggregation": "rank1_first_occurrence_single_phase_judge_w4",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def count_judgeable_tasks(tasks: list[TraceTaskRecord], *, failing_only: bool = False) -> int:
    n = 0
    for task in tasks:
        if not task.triggered:
            continue
        if failing_only and not task.outcome_fail_any:
            continue
        n += 1
    return n
