#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

BASE="${REPO_ROOT}/experiments/rq4/results"
STUDY_DIR="rq4"
FULL=0

usage() {
  cat <<EOF
Usage: $0 [--full]

RQ4 judge for HyperAgent same-task (requires DEEPSEEK_API_KEY in .env).

  --full   n∈{3,4} rank-1 + random baselines + consolidated report
  default  n=4 rank-1 only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

mkdir -p "$BASE"
COMMON=(
  --study-dir "$STUDY_DIR"
  --temperature 0
  --delay 0.5
  --pattern-mode fixed_ranks
  --judge-window-n 4
  --pattern-ranks 1
  --top-k 1
  --ranking-method sbfl
)

run_sbfl() {
  local n="$1"
  echo "=== same_task / HyperAgent / n$n / SBFL rank-1 ==="
  "${JUDGE_CLI[@]}" all \
    --study same_task --framework HyperAgent --n "$n" --condition sbfl \
    "${COMMON[@]}" --no-resume
}

run_random() {
  local n="$1" pair_from="$2"
  echo "=== same_task / HyperAgent / n$n / random ==="
  "${JUDGE_CLI[@]}" all \
    --study same_task --framework HyperAgent --n "$n" --condition random \
    --pair-from "$pair_from" "${COMMON[@]}" --no-resume
}

if [[ "$FULL" -eq 1 ]]; then
  run_sbfl 4
  RQ4="$BASE/same_task/HyperAgent/n4/rank1"
  run_random 4 "$RQ4/tasks.jsonl"
  run_sbfl 3
  RQ3="$BASE/same_task/HyperAgent/n3/rank1"
  run_random 3 "$RQ3/tasks.jsonl"
  "${RP_ANALYSIS[@]}" judge-summarize --base "$BASE"
else
  run_sbfl 4
fi

echo "Results under $BASE"
