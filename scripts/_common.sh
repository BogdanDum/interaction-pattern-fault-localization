#!/usr/bin/env bash
# Shared environment for all experiment scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/fault_localization:${PYTHONPATH:-}"
export MPLBACKEND="${MPLBACKEND:-Agg}"

PYTHON="${PYTHON:-python3}"
RP_ANALYSIS=( "${PYTHON}" -m rp_analysis.cli )
JUDGE_CLI=( "${PYTHON}" -m rp_analysis.judge_cli )

cd "${REPO_ROOT}"
