#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

N=""
B=100
SEED=42
TOP_K=10
OUT_DIR="${REPO_ROOT}/experiments/rq3/results/bootstrap"

usage() {
  cat <<EOF
Usage: $0 [--n N] [--bootstrap B] [--seed S] [--top-k K] [--out-dir DIR]

Bootstrap rank-1 stability for same-task SBFL (default n∈{3,4}).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n) shift; N="$1"; shift ;;
    --bootstrap) shift; B="$1"; shift ;;
    --seed) shift; SEED="$1"; shift ;;
    --top-k) shift; TOP_K="$1"; shift ;;
    --out-dir) shift; OUT_DIR="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

run_one() {
  local n="$1"
  echo "== Bootstrap same_task / HyperAgent / n=${n} =="
  "${RP_ANALYSIS[@]}" bootstrap \
    --study same_task --framework HyperAgent --n "$n" \
    --bootstrap "$B" --seed "$SEED" --top-k "$TOP_K" \
    --out-dir "$OUT_DIR"
}

if [[ -n "$N" ]]; then
  run_one "$N"
else
  for n in 3 4; do
    run_one "$n"
  done
fi
