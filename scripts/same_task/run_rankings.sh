#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

N=""
FISHER_K=20
EXPORT_K=""

usage() {
  cat <<EOF
Usage: $0 [--n N] [--fisher-top-k K] [--export-top-k K]

SBFL rankings for HyperAgent same-task (psf__requests-1142).
Markov is disabled. Default: n∈{3,4} when --n omitted.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n) shift; N="$1"; shift ;;
    --fisher-top-k) shift; FISHER_K="$1"; shift ;;
    --export-top-k) shift; EXPORT_K="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

ARGS=(--study same_task --framework HyperAgent --no-markov --fisher-top-k "$FISHER_K")
[[ -n "$EXPORT_K" ]] && ARGS+=(--export-top-k "$EXPORT_K")

if [[ -n "$N" ]]; then
  echo "== Same-task rank: HyperAgent n=${N} =="
  "${RP_ANALYSIS[@]}" rank "${ARGS[@]}" --n "$N"
else
  for n in 3 4; do
    echo "== Same-task rank: HyperAgent n=${n} =="
    "${RP_ANALYSIS[@]}" rank "${ARGS[@]}" --n "$n"
  done
fi
