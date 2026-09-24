#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 && $1 == --comparison-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_SETUP_COMPARISON_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOT=/root/pf9-editor-factual-setup-benchmark-v1-v2
[[ ! -e $ROOT ]] || exit 4
mkdir -p "$ROOT/r1" "$ROOT/r2"
COMMON=(/root/pf9-v12-recovery-replay-20260917/rootfs/inference-rootfs.tar
        /root/pf9-v12-recovery-replay-20260917/models/A)
REQUESTS=/mnt/c/pf9/docs/artifacts/editor-core-factual-setup-benchmark-v1-requests.jsonl
WORKER=/mnt/c/pf9/scripts/evaluate_editor_core_factual_setup_benchmark_v1.py
ROUTE=/mnt/c/pf9/scripts/run_editor_core_factual_setup_benchmark_v1.sh
EDITOR_SETUP_OWNER_AUTHORIZED=1 bash "$ROUTE" "${COMMON[@]}" \
  /root/pf9-editor-core-v10-v12-targeted-r1-output/checkpoint-000008/adapter \
  "$REQUESTS" "$ROOT/r1" blind-candidate-x "$WORKER" --inference-authorized
EDITOR_SETUP_OWNER_AUTHORIZED=1 bash "$ROUTE" "${COMMON[@]}" \
  /root/pf9-editor-core-v10-v12-targeted-r2-output/checkpoint-000009/adapter \
  "$REQUESTS" "$ROOT/r2" blind-candidate-y "$WORKER" --inference-authorized
