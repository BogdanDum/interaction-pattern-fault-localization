from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from rp_analysis import judge_prompt
from rp_analysis.judge_config import JUDGE_BASE_URL, JUDGE_MODEL
from rp_analysis.judge_run import JudgeTask, append_jsonl, iter_jsonl, run_single_task
from rp_analysis.judge_study import JudgeStudySpec, TraceTaskRecord, make_task_key


def _task_to_judge_task(task: TraceTaskRecord) -> JudgeTask:
    pattern = task.pattern or "RANDOM"
    return JudgeTask(
        pattern=pattern,
        mad_path=task.mad_path,
        mad_relative_path=task.mad_relative_path,
        mas_name=task.mas_name,
        benchmark_name=task.benchmark_name,
        trace_id=task.trace_id,
        condition=task.condition,
        occurrence_start=int(task.occurrence_start),
        seed=0,
        window_n=task.window_n,
        study_id=task.study_id,
        framework=task.framework,
        n=task.window_n,
        pattern_rank=task.pattern_rank,
        task_key=task.task_key,
        tokens=task.tokens,
    )


def _result_task_key(row: dict[str, Any]) -> str:
    if row.get("task_key"):
        return str(row["task_key"])
    return make_task_key(
        str(row.get("mad_relative_path", "")),
        row.get("condition", "failing_candidate"),
        row.get("pattern_rank"),
        row.get("occurrence_start"),
        row.get("window_n"),
    )


def run_trace_judge(
    tasks: list[TraceTaskRecord],
    *,
    out_jsonl: Path,
    model: str = JUDGE_MODEL,
    base_url: str = JUDGE_BASE_URL,
    api_key: str,
    temperature: float = 0.0,
    delay_s: float = 0.5,
    resume: bool = True,
    failing_only: bool = False,
    spec: JudgeStudySpec | None = None,
) -> int:
    """Call the LLM judge for each triggered task, with resume and retry on API failures."""
    del spec
    client = OpenAI(api_key=api_key, base_url=base_url)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    if not resume:
        out_jsonl.write_text("", encoding="utf-8")
    done_keys: set[str] = set()
    if resume and out_jsonl.exists():
        for row in iter_jsonl(out_jsonl):
            done_keys.add(_result_task_key(row))

    n_calls = 0
    for task in tasks:
        if not task.triggered:
            continue
        if failing_only and not task.outcome_fail_any:
            continue
        key = task.task_key or make_task_key(
            task.mad_relative_path,
            task.condition,
            task.pattern_rank,
            task.occurrence_start,
            task.window_n,
        )
        if key in done_keys:
            continue
        judge_task = _task_to_judge_task(task)
        row: dict[str, Any] | None = None
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                row = run_single_task(
                    judge_task,
                    client=client,
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                    prompt_builder=judge_prompt.build_trace_judge_prompt,
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(1.0)
        if row is None:
            row = {
                "pattern": task.pattern,
                "mad_relative_path": task.mad_relative_path,
                "mad_path": task.mad_path,
                "mas_name": task.mas_name,
                "benchmark_name": task.benchmark_name,
                "trace_id": task.trace_id,
                "condition": task.condition,
                "occurrence_start": task.occurrence_start,
                "window_n": task.window_n,
                "study_id": task.study_id,
                "framework": task.framework,
                "pattern_rank": task.pattern_rank,
                "task_key": key,
                "model": model,
                "error": str(last_exc),
                "verdict": None,
            }
        row["task_key"] = key
        row["pattern_rank"] = task.pattern_rank
        row["pilot_role"] = task.pilot_role
        row["outcome_fail_any"] = task.outcome_fail_any
        row["useful"] = judge_prompt.verdict_caused(row.get("verdict"))
        append_jsonl(out_jsonl, row)
        n_calls += 1
        if delay_s > 0:
            time.sleep(delay_s)
    return n_calls
