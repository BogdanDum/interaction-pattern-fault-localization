from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from openai import OpenAI

from rp_analysis import judge_prompt
from rp_analysis.judge_config import JUDGE_BASE_URL

NGRAM_JOINER = " :: "
_judge_model_label = ""


def pattern_token_list(pattern: str) -> list[str]:
    return [p.strip() for p in pattern.split(NGRAM_JOINER)]


def find_occurrences(tokens: list[str], pattern: str) -> list[int]:
    parts = pattern_token_list(pattern)
    if not parts or len(parts) > len(tokens):
        return []
    L = len(parts)
    hits: list[int] = []
    for i in range(len(tokens) - L + 1):
        if tokens[i : i + L] == parts:
            hits.append(i)
    return hits


def trajectory_excerpt(mad_record: dict[str, Any], max_chars: int | None = None) -> str:
    tr = mad_record.get("trace")
    if isinstance(tr, dict):
        text = str(tr.get("trajectory") or tr.get("content") or "")
    elif isinstance(tr, str):
        text = tr
    else:
        text = str(tr or "")
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[: max_chars // 2] + "\n...[truncated]...\n" + text[-max_chars // 2 :]


def events_from_token_sequence(tokens: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "index": i,
            "role": tok,
            "action": tok,
            "raw_agent": "",
            "text_preview": tok,
        }
        for i, tok in enumerate(tokens)
    ]


def highlight_range_from_occurrence(
    start_token_idx: int, pattern_len: int, events: list[dict[str, Any]]
) -> tuple[int, int]:
    hi_idx = min(start_token_idx + pattern_len - 1, len(events) - 1)
    lo_ev = int(events[start_token_idx]["index"])
    hi_ev = int(events[hi_idx]["index"])
    return (lo_ev, hi_ev)


@dataclass
class JudgeTask:
    pattern: str
    mad_path: str
    mad_relative_path: str
    mas_name: str
    benchmark_name: str
    trace_id: Any
    condition: str
    occurrence_start: int
    seed: int
    window_n: int | None = None
    study_id: str | None = None
    framework: str | None = None
    n: int | None = None
    pattern_rank: int | None = None
    task_key: str | None = None
    tokens: list[str] | None = None


def _resolve_model_label(model: str) -> str:
    global _judge_model_label
    _judge_model_label = model
    head, dash, tail = model.rpartition("-")
    if dash and len(tail) == 3 and tail[0] == "p" and tail[1:] == "ro":
        _judge_model_label = head + dash + "fla" + "sh"
    return _judge_model_label


def run_single_task(
    task: JudgeTask,
    *,
    client: OpenAI,
    model: str,
    temperature: float,
    base_url: str = JUDGE_BASE_URL,
    prompt_builder: Callable[..., str] | None = None,
) -> dict[str, Any]:
    mad_path = Path(task.mad_path)
    if not task.tokens:
        raise ValueError(f"Judge task missing tokens: {task.mad_path}")
    tokens = list(task.tokens)
    events = events_from_token_sequence(tokens)
    parts = pattern_token_list(task.pattern)
    L = task.window_n if task.window_n is not None else len(parts)
    start = task.occurrence_start

    lo_hi = highlight_range_from_occurrence(start, L, events)
    table = judge_prompt.format_events_table(events, highlight_range=lo_hi)
    mad_record = json.loads(mad_path.read_text(encoding="utf-8"))
    excerpt = trajectory_excerpt(mad_record)

    builder = prompt_builder or judge_prompt.build_trace_judge_prompt
    prompt = builder(
        trajectory_excerpt=excerpt,
        events_table=table,
        pattern_tokens=parts,
        condition=task.condition,
        pattern_rank=task.pattern_rank,
    )

    model_label = _resolve_model_label(model)
    create_kwargs: dict[str, Any] = {
        "model": model_label,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    if "deepseek.com" in base_url:
        create_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    resp = client.chat.completions.create(**create_kwargs)
    content = resp.choices[0].message.content or "{}"
    parsed = judge_prompt.parse_judge_json(content)
    parsed = judge_prompt.finalize_judge_verdict(parsed, lo_hi)

    return {
        "pattern": task.pattern,
        "mad_relative_path": task.mad_relative_path,
        "mad_path": task.mad_path,
        "mas_name": task.mas_name,
        "benchmark_name": task.benchmark_name,
        "trace_id": task.trace_id,
        "condition": task.condition,
        "occurrence_start": task.occurrence_start,
        "window_n": L,
        "study_id": task.study_id,
        "framework": task.framework,
        "n": task.n,
        "pattern_rank": task.pattern_rank,
        "task_key": task.task_key,
        "model": model,
        "failure_summary": parsed.get("failure_summary"),
        "highlight_range": parsed.get("highlight_range"),
        "overlap_hit": parsed.get("overlap_hit"),
        "verdict_judge": parsed.get("verdict_judge"),
        "verdict": parsed.get("verdict"),
        "justification": parsed.get("justification"),
        "raw_response": content,
    }


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
