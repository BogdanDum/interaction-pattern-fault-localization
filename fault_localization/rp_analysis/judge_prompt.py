from __future__ import annotations

import json
import re
from typing import Any

VERDICTS = frozenset({"caused", "not_caused"})

_TOKEN_LEGEND = (
    "Token legend (action vocabulary):\n"
    "- REQUEST: initial task specification\n"
    "- PLAN: architectural decomposition, role routing, phase handoff, or "
    "phase transition signaling a new coordination stage\n"
    "- ACT: code generation, tests, or tool execution\n"
    "- VERIFY_FAIL: reviewer critique, failed test, or validation rejection\n"
    "- VERIFY_PASS: successful validation or test pass\n"
    "- INFORM: status updates or discussion without repair\n"
    "- ERROR: explicit error signal or exception\n"
    "- TERMINATE: explicit completion signal\n"
)


def format_events_table(events: list[dict[str, Any]], highlight_range: tuple[int, int] | None = None) -> str:
    lines = []
    for e in events:
        idx = int(e.get("index"))
        action = e.get("action")
        preview = str(e.get("text_preview", ""))
        line = f"[{idx}] action={action}\n    text: {preview}"
        if highlight_range is not None:
            lo, hi = highlight_range
            if lo <= idx <= hi:
                line = "<<< " + line + " >>>"
        lines.append(line)
    return "\n".join(lines)


def window_context_line(
    *,
    condition: str | None = None,
    pattern_rank: int | None = None,
) -> str:
    """Return the judge prompt sentence describing how this window was chosen."""
    if condition == "random_control":
        return (
            "This window is a randomly selected fixed-length slice from the same failing trace."
        )
    if pattern_rank is not None and pattern_rank > 1:
        return (
            f"This window is the first occurrence of the rank-{pattern_rank} "
            "failure-associated pattern in this trace."
        )
    return (
        "This window is the first occurrence of the top-ranked failure-associated "
        "pattern in this trace."
    )


def build_trace_judge_prompt(
    *,
    trajectory_excerpt: str,
    events_table: str,
    pattern_tokens: list[str] | None = None,
    condition: str | None = None,
    pattern_rank: int | None = None,
    **_: Any,
) -> str:
    """RQ4 failure-window judge prompt (paper Appendix C.2)"""
    pattern_string = " :: ".join(pattern_tokens) if pattern_tokens else "RANDOM"
    ctx = window_context_line(condition=condition, pattern_rank=pattern_rank)
    schema = {
        "failure_summary": "one sentence: how this run failed overall",
        "verdict": "<caused|not_caused>",
        "justification": (
            "2-3 sentences in action-type terms: what interaction the window shows, and "
            "whether it contains the initiating fault and why"
        ),
    }
    return (
        "You are an expert analyst of multi-agent LLM systems. You are given a trace "
        "from a run that FAILED.\n\n"
        f"{_TOKEN_LEGEND}\n"
        "Localization under evaluation:\n"
        f"- Interaction pattern: {pattern_string}\n"
        "- Window: a fixed-length contiguous slice of the trace, highlighted with <<< >>> below.\n"
        f"- {ctx}\n\n"
        "Task:\n"
        "Decide whether this highlighted interaction caused the failure.\n\n"
        "Initiating fault:\n"
        "The initiating fault is the earliest point in the run where a concrete mistake "
        "or harmful decision puts the execution on the path to failure (but-for: without "
        "it, the run would not have failed in the way it did). Use the full trace to "
        "locate it, then decide whether that fault falls inside the highlighted window.\n\n"
        "Verdict rubric (your answer is final):\n"
        "- **caused**: the highlighted window contains the initiating fault that started "
        "this failure.\n"
        "- **not_caused**: the initiating fault is not in this window (it lies earlier or "
        "outside the highlighted slice).\n\n"
        "Rules:\n"
        "- Use the full trace for context, but judge only the highlighted <<< >>> window.\n"
        "- If the same token sequence appears elsewhere in the trace, ignore those occurrences.\n"
        "- The window is a fixed-length slice, not a minimal span.\n\n"
        "Justification style:\n"
        "- Describe the highlighted window as a short action-token sequence using types "
        "from the legend (e.g. PLAN:ACT:VERIFY_FAIL).\n"
        '- Do not cite bare index numbers.\n'
        "- Write at most 2-3 sentences: what interaction the window shows, and whether "
        "it contains the initiating fault and why.\n\n"
        "--- Trajectory excerpt ---\n"
        f"{trajectory_excerpt}\n\n"
        "--- Chronological labeled events ---\n"
        "(Highlighted window marked with <<< >>>.)\n"
        f"{events_table}\n\n"
        "Respond with JSON ONLY, keys exactly:\n"
        f"{json.dumps(schema, indent=2)}"
    )


def normalize_verdict(raw: Any) -> str | None:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    return v if v in VERDICTS else None


def verdict_caused(verdict: str | None) -> bool:
    return str(verdict or "").strip().lower() == "caused"


def verdict_useful(verdict: str | None) -> bool:
    return verdict_caused(verdict)


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, count=1)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_judge_json(text: str) -> dict[str, Any]:
    data = json.loads(_strip_json_fences(text))
    verdict = normalize_verdict(data.get("verdict"))
    if verdict is not None:
        data["verdict"] = verdict
    return data


def finalize_judge_verdict(
    parsed: dict[str, Any],
    highlight_range: tuple[int, int],
) -> dict[str, Any]:
    judge_verdict = normalize_verdict(parsed.get("verdict"))
    final = judge_verdict if judge_verdict is not None else "not_caused"
    parsed["highlight_range"] = list(highlight_range)
    parsed["verdict_judge"] = judge_verdict
    parsed["verdict"] = final
    parsed["overlap_hit"] = final == "caused"
    return parsed
