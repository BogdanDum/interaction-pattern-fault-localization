#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

FRAMEWORK=""
N=""
MARKOV=""
FISHER_K=20
EXPORT_K=""

usage() {
  cat <<EOF
Usage: $0 [--framework FW] [--n N] [--no-markov] [--fisher-top-k K] [--export-top-k K]

Run SBFL (+ RRF + Fisher/BH) and Markov rankings for one cross-task cell,
or the full 4×4 grid when --framework and --n are omitted.

  --fisher-top-k K   Fisher testing family size (1–20, default 20)
  --export-top-k K   Also write top-K CSV slices under runs/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --framework) shift; FRAMEWORK="$1"; shift ;;
    --n) shift; N="$1"; shift ;;
    --markov) MARKOV="--markov"; shift ;;
    --no-markov) MARKOV="--no-markov"; shift ;;
    --fisher-top-k) shift; FISHER_K="$1"; shift ;;
    --export-top-k) shift; EXPORT_K="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

ARGS=(--study cross_task --fisher-top-k "$FISHER_K")
[[ -n "$MARKOV" ]] && ARGS+=("$MARKOV")
[[ -n "$EXPORT_K" ]] && ARGS+=(--export-top-k "$EXPORT_K")

if [[ -n "$FRAMEWORK" && -n "$N" ]]; then
  echo "== Cross-task rank: ${FRAMEWORK} n=${N} =="
  "${RP_ANALYSIS[@]}" rank "${ARGS[@]}" --framework "$FRAMEWORK" --n "$N"
elif [[ -z "$FRAMEWORK" && -z "$N" ]]; then
  echo "== Cross-task rank grid (4 frameworks × n∈{2,3,4,5}) =="
  GRID=(--study cross_task --fisher-top-k "$FISHER_K")
  [[ -n "$MARKOV" ]] && GRID+=("$MARKOV")
  [[ -n "$EXPORT_K" ]] && GRID+=(--export-top-k "$EXPORT_K")
  "${RP_ANALYSIS[@]}" rank-grid "${GRID[@]}"
else
  echo "Provide both --framework and --n, or neither for full grid." >&2
  exit 2
fi
