from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from rp_analysis.datasets import load_traces_from_manifest
from rp_analysis.paths import repo_root

PILOT_RANDOM_SEED = 42
PILOT_DEFAULT_N = 20
TOP_K = 4
JUDGE_STUDY_DIR = "rq4"

VOCAB_BATCH = "experiments/cross_task/runs/framework_pooled"


@dataclass
class JudgeStudySpec:
    study_id: str
    framework: str
    n: int
    condition: str = "sbfl"
    pattern_mode: str = "best_of_top_k"
    pattern_ranks: list[int] = field(default_factory=list)
    top_k: int = 4
    seed: int = 42
    failing_only: bool = True
    judge_window_n: int | None = None
    ranking_method: str = "sbfl"

    def effective_window_n(self) -> int:
        return int(self.judge_window_n) if self.judge_window_n is not None else int(self.n)

    def output_subdir(self) -> str:
        if (
            self.ranking_method == "markov"
            and self.condition == "sbfl"
            and self.pattern_mode == "fixed_ranks"
            and len(self.pattern_ranks) == 1
            and self.pattern_ranks[0] == 1
        ):
            return "markov"
        if (
            self.condition == "sbfl"
            and self.pattern_mode == "fixed_ranks"
            and len(self.pattern_ranks) == 1
        ):
            return f"rank{self.pattern_ranks[0]}"
        return self.condition

    def label(self) -> str:
        parts = [self.study_id, self.framework, f"n{self.n}", self.output_subdir()]
        return "/".join(parts)


@dataclass
class TraceTaskRecord:
    trace_id: Any
    mad_path: str
    mad_relative_path: str
    mas_name: str
    benchmark_name: str
    outcome_fail_any: bool
    triggered: bool
    pattern: str | None = None
    pattern_rank: int | None = None
    occurrence_start: int | None = None
    condition: str = "failing_candidate"
    pilot_role: str | None = None
    task_key: str | None = None
    study_id: str | None = None
    framework: str | None = None
    window_n: int | None = None
    tokens: list[str] | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


def make_task_key(
    mad_relative_path: str,
    condition: str,
    pattern_rank: int | None,
    occurrence_start: int | None,
    window_n: int | None = None,
) -> str:
    n_part = f":n{window_n}" if window_n is not None else ""
    if pattern_rank is not None and occurrence_start is not None:
        return f"{mad_relative_path}|{condition}:r{pattern_rank}:s{occurrence_start}{n_part}"
    return f"{mad_relative_path}|{condition}:none{n_part}"


def study_artifacts_dir(spec: JudgeStudySpec, root: Path | None = None) -> Path:
    root = root or repo_root()
    if spec.study_id == "same_task":
        return root / f"experiments/rq3/runs/n{spec.n}" / "artifacts"
    return root / VOCAB_BATCH / f"n{spec.n}" / spec.framework / "out" / "artifacts"


def study_paths(spec: JudgeStudySpec, root: Path | None = None) -> tuple[Path, Path]:
    root = root or repo_root()
    if spec.study_id == "same_task":
        base = root / f"experiments/rq3/runs/n{spec.n}"
        rankings = base / "runs/rankings__global.csv"
    else:
        base = root / VOCAB_BATCH / f"n{spec.n}" / spec.framework / "out"
        if spec.ranking_method == "markov":
            rankings = base / "runs/markov_pattern_rankings__global.csv"
        else:
            rankings = base / "runs/rankings__global.csv"
    return rankings, study_artifacts_dir(spec, root)


def study_output_dir(spec: JudgeStudySpec, root: Path | None = None, *, study_dir: str | None = None) -> Path:
    root = root or repo_root()
    base_name = study_dir or JUDGE_STUDY_DIR
    return root / "experiments" / base_name / "results" / spec.study_id / spec.framework / f"n{spec.n}" / spec.output_subdir()


def default_rankings_path(root: Path | None = None) -> Path:
    return study_paths(JudgeStudySpec("cross_task", "MetaGPT", 4), root)[0]


def load_study_traces(spec: JudgeStudySpec, root: Path | None = None) -> pd.DataFrame:
    _, artifacts_dir = study_paths(spec, root or repo_root())
    traces = load_traces_from_manifest(artifacts_dir, root=root)
    traces["trace_id"] = traces["trace_id"].astype(int)
    return traces


def default_output_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "experiments" / JUDGE_STUDY_DIR / "results"


def load_top_patterns(rankings_path: Path, top_k: int = TOP_K) -> list[tuple[int, str]]:
    df = pd.read_csv(rankings_path)
    df = df.sort_values("rank", ascending=True).head(int(top_k))
    return [(int(row["rank"]), str(row["pattern"])) for _, row in df.iterrows()]


def load_patterns_by_rank(rankings_path: Path, ranks: list[int]) -> list[tuple[int, str]]:
    df = pd.read_csv(rankings_path)
    df = df.sort_values("rank", ascending=True)
    rank_set = set(int(r) for r in ranks)
    out: list[tuple[int, str]] = []
    for _, row in df.iterrows():
        r = int(row["rank"])
        if r in rank_set:
            out.append((r, str(row["pattern"])))
    return sorted(out, key=lambda x: x[0])
