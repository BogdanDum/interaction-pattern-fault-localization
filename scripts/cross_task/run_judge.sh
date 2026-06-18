#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

BASE="${REPO_ROOT}/experiments/rq4/results"
STUDY_DIR="rq4"
TEMPERATURE=0
DELAY=0.5
WINDOW_N=4
FULL=0
FRAMEWORK=""
N=""
CONDITION="sbfl"

usage() {
  cat <<EOF
Usage: $0 [--full] [--framework FW] [--n N] [--condition sbfl|random]

Run RQ4 LLM-as-a-judge for cross-task conditions (requires DEEPSEEK_API_KEY in .env).

  --full        Run all paper cross-task judge cells + consolidated report
  --framework   Framework for a single cell (default MetaGPT)
  --n           N-gram size for a single cell (default 4)
  --condition   sbfl = SBFL rank-1 (default); random = random baseline
  default       MetaGPT n=4 rank-1 only (smoke test)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=1; shift ;;
    --framework) shift; FRAMEWORK="$1"; shift ;;
    --n) shift; N="$1"; shift ;;
    --condition) shift; CONDITION="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -n "$CONDITION" && "$CONDITION" != "sbfl" && "$CONDITION" != "random" ]]; then
  echo "Invalid --condition: $CONDITION (use sbfl or random)" >&2
  exit 2
fi

mkdir -p "$BASE"
COMMON=(
  --study-dir "$STUDY_DIR"
  --temperature "$TEMPERATURE"
  --delay "$DELAY"
  --pattern-mode fixed_ranks
  --judge-window-n "$WINDOW_N"
  --pattern-ranks 1
  --top-k 1
)
RANK1=(--ranking-method sbfl)

run_sbfl() {
  local fw="$1" n="$2"
  echo "=== cross_task / $fw / n$n / SBFL rank-1 ==="
  "${JUDGE_CLI[@]}" all \
    --study cross_task --framework "$fw" --n "$n" --condition sbfl \
    "${RANK1[@]}" "${COMMON[@]}" --no-resume
}

run_random() {
  local fw="$1" n="$2" pair_from="$3"
  echo "=== cross_task / $fw / n$n / random ==="
  "${JUDGE_CLI[@]}" all \
    --study cross_task --framework "$fw" --n "$n" --condition random \
    "${RANK1[@]}" --pair-from "$pair_from" \
    "${COMMON[@]}" --no-resume
}

if [[ "$FULL" -eq 1 ]]; then
  run_sbfl MetaGPT 4
  MG4="$BASE/cross_task/MetaGPT/n4/rank1"
  run_sbfl MetaGPT 3
  MG3="$BASE/cross_task/MetaGPT/n3/rank1"
  run_random MetaGPT 3 "$MG3/tasks.jsonl"
  run_sbfl MetaGPT 2
  MG2="$BASE/cross_task/MetaGPT/n2/rank1"
  run_random MetaGPT 2 "$MG2/tasks.jsonl"
  run_random MetaGPT 4 "$MG4/tasks.jsonl"

  run_sbfl AG2 4
  AG4="$BASE/cross_task/AG2/n4/rank1"
  run_random AG2 4 "$AG4/tasks.jsonl"

  run_sbfl HyperAgent 4
  HA4="$BASE/cross_task/HyperAgent/n4/rank1"
  run_random HyperAgent 4 "$HA4/tasks.jsonl"
  run_sbfl HyperAgent 3
  HA3="$BASE/cross_task/HyperAgent/n3/rank1"
  run_random HyperAgent 3 "$HA3/tasks.jsonl"
  run_sbfl HyperAgent 2

  "${RP_ANALYSIS[@]}" judge-summarize --base "$BASE"
else
  FW="${FRAMEWORK:-MetaGPT}"
  NVAL="${N:-4}"
  if [[ "$CONDITION" == "random" ]]; then
    PAIR_FROM="$BASE/cross_task/$FW/n$NVAL/rank1/tasks.jsonl"
    if [[ ! -f "$PAIR_FROM" ]]; then
      echo "Missing $PAIR_FROM — run rank-1 first." >&2
      exit 1
    fi
    run_random "$FW" "$NVAL" "$PAIR_FROM"
  else
    run_sbfl "$FW" "$NVAL"
  fi
  echo "Done (single cell). Use --full for all cross-task judge conditions."
fi

echo "Results under $BASE"
