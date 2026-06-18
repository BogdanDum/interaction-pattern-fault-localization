from __future__ import annotations

import argparse
import json
from pathlib import Path

from rp_analysis import judge_metrics, orchestrator
from rp_analysis.judge_config import JUDGE_MODEL
from rp_analysis.bootstrap import run_bootstrap, run_significance_only
from rp_analysis.judge_cli import build_parser as judge_build_parser
from rp_analysis.judge_summarize import consolidate
from rp_analysis.orchestrator_config import load_config, resolve_config
from rp_analysis.study import (
    CROSS_TASK_FRAMEWORKS,
    CROSS_TASK_N,
    config_for,
    judge_results_dir,
    out_dir_for,
    validate_framework,
    validate_n,
    validate_top_k,
)


def _patch_config_for_run(
    config_path: Path,
    *,
    markov: bool | None,
    fisher_top_k: int | None,
) -> Path:
    cfg = load_config(config_path)
    if markov is not None:
        cfg.setdefault("markov_pattern", {})["enabled"] = bool(markov)
    if fisher_top_k is not None:
        validate_top_k(fisher_top_k, purpose="fisher")
        cfg.setdefault("sbfl", {})["fisher_max_patterns"] = int(fisher_top_k)
    if not cfg.get("experiment", {}).get("out_dir"):
        # resolved below via out_dir_override
        pass
    tmp = config_path.parent / ".config.runtime.json"
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return tmp


def cmd_run_experiment(args: argparse.Namespace) -> int:
    override = getattr(args, "out_dir", None)
    config_path = Path(args.config)
    runtime = config_path
    if args.fisher_top_k is not None or args.markov is not None:
        runtime = _patch_config_for_run(
            config_path,
            markov=args.markov,
            fisher_top_k=args.fisher_top_k,
        )
    rc = orchestrator.run_experiment(
        runtime,
        out_dir_override=Path(override) if override is not None else None,
    )
    if runtime != config_path and runtime.name == ".config.runtime.json":
        runtime.unlink(missing_ok=True)
    if args.export_top_k and override:
        _write_top_k_export(Path(override), int(args.export_top_k))
    elif args.export_top_k:
        cfg = resolve_config(load_config(config_path), config_path)
        _write_top_k_export(Path(cfg["experiment"]["out_dir"]), int(args.export_top_k))
    return rc


def _write_top_k_export(out_dir: Path, top_k: int) -> None:
    validate_top_k(top_k, purpose="export")
    runs = out_dir / "runs"
    for name in ("rankings__global.csv", "markov_pattern_rankings__global.csv"):
        src = runs / name
        if not src.is_file():
            continue
        import pandas as pd

        df = pd.read_csv(src)
        if "rank" in df.columns:
            df = df.sort_values("rank")
        else:
            df = df.sort_values("ochiai", ascending=False)
        dest = runs / f"{src.stem}__top{top_k}.csv"
        df.head(top_k).to_csv(dest, index=False)
        print(f"Wrote {dest}")


def cmd_rank(args: argparse.Namespace) -> int:
    validate_n(args.study, int(args.n))
    validate_framework(args.study, args.framework)
    config_path = config_for(args.study, framework=args.framework, n=int(args.n))
    if not config_path.is_file():
        raise SystemExit(f"Missing config: {config_path}")

    out_dir = out_dir_for(args.study, framework=args.framework, n=int(args.n))
    markov = args.markov
    if markov is None:
        markov = args.study == "cross_task"

    args.config = config_path
    args.out_dir = out_dir
    if args.fisher_top_k is None:
        args.fisher_top_k = 20
    args.markov = markov
    return cmd_run_experiment(args)


def cmd_rank_grid(args: argparse.Namespace) -> int:
    frameworks = list(CROSS_TASK_FRAMEWORKS) if args.study == "cross_task" else [args.framework]
    n_values = list(CROSS_TASK_N) if args.study == "cross_task" else [int(args.n)]
    if args.study == "cross_task" and args.framework:
        frameworks = [args.framework]
    if args.n is not None:
        n_values = [int(args.n)]

    rc = 0
    for fw in frameworks:
        for n in n_values:
            ns = argparse.Namespace(
                study=args.study,
                framework=fw,
                n=n,
                markov=args.markov,
                fisher_top_k=args.fisher_top_k or 20,
                export_top_k=args.export_top_k,
                config=None,
                out_dir=None,
            )
            print(f"\n== rank {args.study} / {fw} / n={n} ==")
            rc = max(rc, cmd_rank(ns))
    return rc


def cmd_significance(args: argparse.Namespace) -> int:
    rankings = Path(args.rankings)
    cfg = resolve_config(load_config(Path(args.config)), Path(args.config))
    df = run_significance_only(rankings, cfg["sbfl"])
    out = Path(args.out) if args.out else rankings
    df.to_csv(out, index=False)
    print(f"Wrote Fisher+BH columns -> {out}")
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    validate_top_k(int(args.top_k), purpose="bootstrap")
    if args.config:
        config_path = Path(args.config)
    else:
        if args.study is None or args.n is None:
            raise SystemExit("bootstrap requires --config or (--study and --n)")
        validate_n(args.study, int(args.n))
        framework = args.framework
        if args.study == "same_task":
            framework = "HyperAgent"
        validate_framework(args.study, framework)
        config_path = config_for(args.study, framework=framework, n=int(args.n))

    out_dir = Path(args.out_dir) if args.out_dir else None
    out_csv = run_bootstrap(
        config_path,
        B=int(args.bootstrap),
        seed=int(args.seed),
        top_k=int(args.top_k),
        out_dir=out_dir,
    )
    print(f"Bootstrap summary -> {out_csv}")
    return 0


def cmd_judge(args: argparse.Namespace) -> int:
    parser = judge_build_parser()
    judge_args = parser.parse_args(args.judge_argv)
    return int(judge_args.func(judge_args))


def cmd_judge_summarize(args: argparse.Namespace) -> int:
    base = Path(args.base) if args.base else judge_results_dir()
    errors = judge_metrics.validate_study_models(base, expected=JUDGE_MODEL)
    if errors:
        print(f"WARNING: {len(errors)} model mismatches (expected {JUDGE_MODEL})")
    df, report = consolidate(base, model=JUDGE_MODEL)
    out_csv = base / "summary.csv"
    out_md = base / "report.md"
    df.to_csv(out_csv, index=False)
    out_md.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {out_csv} and {out_md}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rp-analysis", description="Fault localization experiment CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rank", help="SBFL (+ RRF) and optional Markov rankings")
    r.add_argument("--study", choices=("cross_task", "same_task"), required=True)
    r.add_argument("--framework", default="MetaGPT")
    r.add_argument("--n", type=int, required=True)
    r.add_argument("--markov", action=argparse.BooleanOptionalAction, default=None)
    r.add_argument("--fisher-top-k", type=int, default=20, help="Fisher testing family size (1–20)")
    r.add_argument("--export-top-k", type=int, default=None, help="Also write top-k CSV slices")
    r.set_defaults(func=cmd_rank)

    g = sub.add_parser("rank-grid", help="Run rank over multiple framework×n cells")
    g.add_argument("--study", choices=("cross_task", "same_task"), default="cross_task")
    g.add_argument("--framework", default=None, help="Limit to one framework (cross-task)")
    g.add_argument("--n", type=int, default=None, help="Limit to one n")
    g.add_argument("--markov", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("--fisher-top-k", type=int, default=20)
    g.add_argument("--export-top-k", type=int, default=None)
    g.set_defaults(func=cmd_rank_grid)

    sig = sub.add_parser("significance", help="Re-apply Fisher + BH to an existing rankings CSV")
    sig.add_argument("--config", type=Path, required=True)
    sig.add_argument("--rankings", type=Path, required=True)
    sig.add_argument("--out", type=Path, default=None)
    sig.set_defaults(func=cmd_significance)

    b = sub.add_parser("bootstrap", help="Bootstrap rank-1 / top-k stability")
    b.add_argument("--study", choices=("cross_task", "same_task"), default=None)
    b.add_argument("--framework", default="MetaGPT")
    b.add_argument("--n", type=int, default=None)
    b.add_argument("--config", type=Path, default=None)
    b.add_argument("--bootstrap", type=int, default=100)
    b.add_argument("--seed", type=int, default=42)
    b.add_argument("--top-k", type=int, default=10)
    b.add_argument("--out-dir", type=Path, default=None)
    b.set_defaults(func=cmd_bootstrap)

    j = sub.add_parser("judge", help="LLM-as-a-judge (pass subcommand args after --)")
    j.add_argument("judge_argv", nargs=argparse.REMAINDER, help="e.g. all --study cross_task ...")
    j.set_defaults(func=cmd_judge)

    js = sub.add_parser("judge-summarize", help="Consolidate all judge result folders")
    js.add_argument("--base", type=Path, default=None)
    js.set_defaults(func=cmd_judge_summarize)

    legacy = sub.add_parser("run-experiment", help="Run from JSON config (legacy)")
    legacy.add_argument("--config", type=Path, required=True)
    legacy.add_argument("--out-dir", type=Path, default=None)
    legacy.add_argument("--markov", action=argparse.BooleanOptionalAction, default=None)
    legacy.add_argument("--fisher-top-k", type=int, default=None)
    legacy.add_argument("--export-top-k", type=int, default=None)
    legacy.set_defaults(func=cmd_run_experiment)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "judge" and args.judge_argv and args.judge_argv[0] == "--":
        args.judge_argv = args.judge_argv[1:]
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
