#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

FRAMEWORK=""
N=""
B=100
SEED=42
TOP_K=10
OUT_DIR=""

usage() {
  cat <<EOF
Usage: $0 [--framework FW] [--n N] [--bootstrap B] [--seed S] [--top-k K] [--out-dir DIR]

Bootstrap rank-1 / top-k stability (default B=100, seed=42, top-k=10).
Omit --framework/--n to run all primary cells (frameworks × n∈{3,4}).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --framework) shift; FRAMEWORK="$1"; shift ;;
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
  local fw="$1" n="$2"
  local args=(--study cross_task --framework "$fw" --n "$n" --bootstrap "$B" --seed "$SEED" --top-k "$TOP_K")
  [[ -n "$OUT_DIR" ]] && args+=(--out-dir "$OUT_DIR")
  echo "== Bootstrap cross_task / ${fw} / n=${n} =="
  "${RP_ANALYSIS[@]}" bootstrap "${args[@]}"
}

if [[ -n "$FRAMEWORK" && -n "$N" ]]; then
  run_one "$FRAMEWORK" "$N"
elif [[ -z "$FRAMEWORK" && -z "$N" ]]; then
  for fw in AG2 ChatDev HyperAgent MetaGPT; do
    for n in 3 4; do
      run_one "$fw" "$n"
    done
  done
else
  echo "Provide both --framework and --n, or neither for batch." >&2
  exit 2
fi
