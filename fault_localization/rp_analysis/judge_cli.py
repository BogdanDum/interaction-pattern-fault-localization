from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from rp_analysis.judge_config import JUDGE_MODEL
from rp_analysis.judge_report import summarize_trace_judge
from rp_analysis.judge_run import iter_jsonl
from rp_analysis.judge_runner import run_trace_judge
from rp_analysis.judge_study import (
    PILOT_DEFAULT_N,
    JudgeStudySpec,
    default_output_dir,
    default_rankings_path,
    study_output_dir,
    study_paths,
)
from rp_analysis.judge_tasks import (
    build_study_tasks,
    build_trace_tasks,
    count_judgeable_tasks,
    read_tasks_jsonl,
    write_manifest,
    write_tasks_jsonl,
)
from rp_analysis.paths import repo_root

_ENV_FILE = ".env"


def _repo() -> Path:
    return repo_root()


def _env_path() -> Path:
    candidate = Path(_ENV_FILE)
    if candidate.is_absolute():
        return candidate
    return _repo() / candidate


def _load_env() -> None:
    env_path = _env_path()
    if env_path.is_file():
        load_dotenv(env_path)
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    if env_path.is_file():
        raw = env_path.read_text(encoding="utf-8").strip()
        if raw and not raw.startswith("#") and "=" not in raw:
            os.environ["DEEPSEEK_API_KEY"] = raw


def _api_key() -> str:
    _load_env()
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise SystemExit(f"Missing API key. Set DEEPSEEK_API_KEY in {_ENV_FILE}")
    return key


def _parse_ranks(text: str | None) -> list[int]:
    if not text:
        return []
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def _build_spec(args: argparse.Namespace) -> JudgeStudySpec:
    pattern_mode = args.pattern_mode
    ranks = _parse_ranks(args.pattern_ranks)
    if ranks and pattern_mode == "best_of_top_k":
        pattern_mode = "fixed_ranks"
    return JudgeStudySpec(
        study_id=args.study,
        framework=args.framework,
        n=int(args.n),
        condition=args.condition,
        pattern_mode=pattern_mode,
        pattern_ranks=ranks,
        top_k=int(args.top_k),
        seed=int(args.seed),
        failing_only=True,
        judge_window_n=int(args.judge_window_n) if args.judge_window_n is not None else None,
        ranking_method=str(getattr(args, "ranking_method", "sbfl")),
    )


def _out_dir(args: argparse.Namespace, spec: JudgeStudySpec) -> Path:
    if args.out_dir:
        return Path(args.out_dir)
    if args.pilot and not args.study:
        return default_output_dir(_repo())
    return study_output_dir(spec, _repo(), study_dir=args.study_dir)


def cmd_build_tasks(args: argparse.Namespace) -> int:
    root = _repo()
    spec = _build_spec(args)
    out_dir = _out_dir(args, spec)
    pilot_n = int(args.pilot_n)

    if args.pilot and args.rankings and args.artifacts_dir:
        tasks = build_trace_tasks(
            rankings_path=Path(args.rankings),
            artifacts_dir=Path(args.artifacts_dir),
            pilot=True,
            pilot_n=pilot_n,
            repo=root,
        )
    else:
        rankings, artifacts = study_paths(spec, root)
        pair_from = Path(args.pair_from) if args.pair_from else None
        tasks = build_study_tasks(
            spec,
            rankings_path=Path(args.rankings) if args.rankings else rankings,
            artifacts_dir=Path(args.artifacts_dir) if args.artifacts_dir else artifacts,
            pair_from=pair_from,
            repo=root,
            pilot=args.pilot,
            pilot_n=pilot_n,
        )

    tasks_path = out_dir / "tasks.jsonl"
    write_tasks_jsonl(tasks, tasks_path)
    triggered = sum(1 for t in tasks if t.triggered)
    unique_traces = len({t.trace_id for t in tasks if t.triggered})
    if not args.pilot:
        rankings_p, artifacts_p = study_paths(spec, root)
        write_manifest(
            out_dir / "manifest.json",
            spec,
            rankings_path=Path(args.rankings) if args.rankings else rankings_p,
            artifacts_dir=None if spec.condition == "random" else (
                Path(args.artifacts_dir) if args.artifacts_dir else artifacts_p
            ),
            model=JUDGE_MODEL,
            pilot=False,
        )
    print(f"Wrote {len(tasks)} tasks ({triggered} triggered rows, {unique_traces} unique traces) -> {tasks_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    spec = _build_spec(args)
    out_dir = _out_dir(args, spec)
    tasks_path = out_dir / "tasks.jsonl"
    results_path = out_dir / "results.jsonl"

    tasks = read_tasks_jsonl(tasks_path)
    failing_only = spec.failing_only and not args.pilot if args.failing_only is None else args.failing_only
    expected = count_judgeable_tasks(tasks, failing_only=failing_only)

    if args.skip_if_results and results_path.exists():
        n_existing = sum(1 for _ in iter_jsonl(results_path))
        if n_existing >= expected and expected > 0:
            print(f"Skip run: {n_existing}/{expected} results already exist -> {results_path}")
            return 0

    n = run_trace_judge(
        tasks,
        out_jsonl=results_path,
        api_key=_api_key(),
        temperature=float(args.temperature),
        delay_s=float(args.delay),
        resume=not args.no_resume,
        failing_only=failing_only,
        spec=spec,
    )
    print(f"Judge calls completed: {n} -> {results_path}")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    spec = _build_spec(args)
    out_dir = _out_dir(args, spec)
    summary = summarize_trace_judge(
        out_dir / "tasks.jsonl",
        out_dir / "results.jsonl",
        out_csv=out_dir / "summary.csv",
        out_report=out_dir / "report.md",
        out_trace_csv=out_dir / "trace_summary.csv",
        run_tag=args.run_tag,
        spec=spec,
        model=JUDGE_MODEL,
    )
    print(
        f"Summary [{summary['study']}]: n_traces={summary['n_judged']} "
        f"caused={summary['caused_pct']:.1%} "
        f"(occurrence_calls={summary['n_occurrence_judged']})"
    )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _repo()
    spec = JudgeStudySpec("cross_task", "MetaGPT", 4, condition="sbfl", top_k=4)
    out_dir = study_output_dir(spec, root)
    out_dir.mkdir(parents=True, exist_ok=True)

    legacy = root / "experiments" / "rq4" / "results" / "metagpt_trace_judge"
    for name in ("full_tasks.jsonl", "full_results.jsonl", "full_summary.csv", "full_report.md"):
        src = legacy / name
        if not src.exists():
            continue
        dst_name = name.replace("full_", "")
        shutil.copy2(src, out_dir / dst_name)

    rankings, artifacts = study_paths(spec, root)
    write_manifest(
        out_dir / "manifest.json",
        spec,
        rankings_path=rankings,
        artifacts_dir=artifacts,
        model=JUDGE_MODEL,
    )
    print(f"Ingested legacy MetaGPT n4 sbfl results -> {out_dir}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    cmd_build_tasks(args)
    cmd_run(args)
    cmd_summarize(args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Trace-level LLM judge experiments (v2)")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--study", choices=("cross_task", "same_task"), default="cross_task")
    common.add_argument("--framework", default="MetaGPT")
    common.add_argument("--n", type=int, default=4)
    common.add_argument("--condition", choices=("sbfl", "random"), default="sbfl")
    common.add_argument("--pattern-mode", choices=("best_of_top_k", "fixed_ranks"), default="best_of_top_k")
    common.add_argument("--pattern-ranks", default=None, help="Comma-separated ranks, e.g. 1,3")
    common.add_argument("--top-k", type=int, default=4)
    common.add_argument("--seed", type=int, default=42)
    common.add_argument("--out-dir", type=Path, default=None)
    common.add_argument("--study-dir", default="rq4", help="Subfolder under results/")
    common.add_argument(
        "--ranking-method",
        choices=("sbfl", "markov"),
        default="sbfl",
        help="Ranking source for pattern selection (cross-task only for markov)",
    )
    common.add_argument(
        "--judge-window-n",
        type=int,
        default=None,
        help="Fixed highlight width (tokens); default = pattern n",
    )
    common.add_argument("--pilot", action="store_true")
    common.add_argument("--pilot-n", type=int, default=PILOT_DEFAULT_N)
    common.add_argument("--run-tag", default=None)
    common.add_argument("--temperature", type=float, default=0.0)
    common.add_argument("--delay", type=float, default=0.5)
    common.add_argument("--no-resume", action="store_true")
    common.add_argument("--failing-only", action=argparse.BooleanOptionalAction, default=None)
    common.add_argument("--skip-if-results", action="store_true")

    b = sub.add_parser("build-tasks", parents=[common], help="Build judge tasks")
    b.add_argument("--rankings", type=Path, default=None)
    b.add_argument("--artifacts-dir", type=Path, default=None)
    b.add_argument("--pair-from", type=Path, default=None, help="SBFL tasks.jsonl for random baseline")
    b.set_defaults(func=cmd_build_tasks)

    r = sub.add_parser("run", parents=[common], help="Run judge API calls")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("summarize", parents=[common], help="Summarize results")
    s.set_defaults(func=cmd_summarize)

    sub.add_parser("ingest-legacy-metagpt", help="Copy existing MetaGPT n4 sbfl results").set_defaults(func=cmd_ingest)

    a = sub.add_parser("all", parents=[common], help="build-tasks + run + summarize")
    a.add_argument("--rankings", type=Path, default=None)
    a.add_argument("--artifacts-dir", type=Path, default=None)
    a.add_argument("--pair-from", type=Path, default=None)
    a.set_defaults(func=cmd_all)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
