#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"

CONFIG=""
RANKINGS=""
OUT=""

usage() {
  cat <<EOF
Usage: $0 --config PATH --rankings PATH [--out PATH]

Re-apply Fisher exact test + Benjamini–Hochberg FDR to an existing rankings CSV.
Normally Fisher+BH run automatically during run_rankings.sh; use this to refresh
significance columns without recomputing SBFL scores.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) shift; CONFIG="$1"; shift ;;
    --rankings) shift; RANKINGS="$1"; shift ;;
    --out) shift; OUT="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "$CONFIG" && -n "$RANKINGS" ]] || { usage; exit 2; }

SIG=(--config "$CONFIG" --rankings "$RANKINGS")
[[ -n "$OUT" ]] && SIG+=(--out "$OUT")
"${RP_ANALYSIS[@]}" significance "${SIG[@]}"
