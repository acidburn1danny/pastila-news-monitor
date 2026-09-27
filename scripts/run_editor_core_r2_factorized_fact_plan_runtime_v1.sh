#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "--zero-step-only" ]]; then echo 'real execution authority absent' >&2; exit 64; fi
shift
exec python3 -B "$(dirname "$0")/preflight_editor_core_r2_factorized_fact_plan_runtime_v1.py" "$@"
