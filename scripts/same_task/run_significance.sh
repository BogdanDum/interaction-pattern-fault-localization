#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_common.sh"
exec "$(dirname "$0")/../cross_task/run_significance.sh" "$@"
