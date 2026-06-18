from __future__ import annotations

from pathlib import Path

from rp_analysis.paths import repo_root, repo_path

CROSS_TASK_FRAMEWORKS = ("AG2", "ChatDev", "HyperAgent", "MetaGPT")
CROSS_TASK_N = (2, 3, 4, 5)
SAME_TASK_FRAMEWORK = "HyperAgent"
SAME_TASK_N = (3, 4)

CROSS_TASK_POOLED = "experiments/cross_task/runs/framework_pooled"
CROSS_TASK_CONFIGS = "experiments/cross_task/configs"
SAME_TASK_RUNS = "experiments/rq3/runs"
SAME_TASK_CONFIGS = "experiments/rq3/configs"

JUDGE_RESULTS = "experiments/rq4/results"

FISHER_TOP_K_MAX = 20
JUDGE_TOP_K_MAX = 5
BOOTSTRAP_TOP_K_CHOICES = (1, 5, 10, 20, 30)


def validate_n(study: str, n: int) -> None:
    allowed = CROSS_TASK_N if study == "cross_task" else SAME_TASK_N
    if n not in allowed:
        raise ValueError(f"n must be one of {allowed} for study={study!r}, got {n}")


def validate_framework(study: str, framework: str) -> None:
    if study == "same_task":
        if framework != SAME_TASK_FRAMEWORK:
            raise ValueError(
                f"same_task only supports framework {SAME_TASK_FRAMEWORK!r}, got {framework!r}"
            )
        return
    if framework not in CROSS_TASK_FRAMEWORKS:
        raise ValueError(
            f"framework must be one of {CROSS_TASK_FRAMEWORKS}, got {framework!r}"
        )


def validate_top_k(
    top_k: int,
    *,
    purpose: str,
    max_patterns: int | None = None,
) -> None:
    if top_k < 1:
        raise ValueError(f"top-k must be >= 1 for {purpose}, got {top_k}")
    if purpose == "fisher" and top_k > FISHER_TOP_K_MAX:
        raise ValueError(f"fisher top-k must be <= {FISHER_TOP_K_MAX}, got {top_k}")
    if purpose == "judge" and top_k > JUDGE_TOP_K_MAX:
        raise ValueError(f"judge top-k must be <= {JUDGE_TOP_K_MAX}, got {top_k}")
    if purpose == "bootstrap" and top_k not in BOOTSTRAP_TOP_K_CHOICES:
        raise ValueError(
            f"bootstrap top-k should be one of {BOOTSTRAP_TOP_K_CHOICES}, got {top_k}"
        )
    if max_patterns is not None and top_k > max_patterns:
        raise ValueError(f"top-k {top_k} exceeds available patterns ({max_patterns})")


def cross_task_config_path(framework: str, n: int, root: Path | None = None) -> Path:
    validate_n("cross_task", n)
    validate_framework("cross_task", framework)
    base = repo_path(CROSS_TASK_CONFIGS, root)
    return base / f"n{n}" / framework / "config.json"


def cross_task_out_dir(framework: str, n: int, root: Path | None = None) -> Path:
    base = repo_path(CROSS_TASK_POOLED, root)
    return base / f"n{n}" / framework / "out"


def same_task_config_path(n: int, root: Path | None = None) -> Path:
    validate_n("same_task", n)
    base = repo_path(SAME_TASK_CONFIGS, root)
    return base / f"n{n}" / "config.json"


def same_task_out_dir(n: int, root: Path | None = None) -> Path:
    base = repo_path(SAME_TASK_RUNS, root)
    return base / f"n{n}"


def config_for(study: str, *, framework: str, n: int, root: Path | None = None) -> Path:
    if study == "cross_task":
        return cross_task_config_path(framework, n, root)
    validate_framework("same_task", framework)
    return same_task_config_path(n, root)


def out_dir_for(study: str, *, framework: str, n: int, root: Path | None = None) -> Path:
    if study == "cross_task":
        return cross_task_out_dir(framework, n, root)
    validate_framework("same_task", framework)
    return same_task_out_dir(n, root)


def judge_results_dir(root: Path | None = None) -> Path:
    return repo_path(JUDGE_RESULTS, root)


def repo() -> Path:
    return repo_root()
