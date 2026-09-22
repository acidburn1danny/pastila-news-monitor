#!/usr/bin/env bash
set -euo pipefail

# Consuming route. This file is never invoked by fixture smoke or zero-step.
[[ $# == 9 && $9 == --execute-authorized && $(id -u) == 0 ]] || exit 2
[[ ${BRIDGE_A1A2_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
[[ $5 == A1 || $5 == A2 ]] || exit 4
[[ $6 == 271828 || $6 == 314159 || $6 == 161803 ]] || exit 4

REPO="$(realpath -e -- "$(dirname -- "${BASH_SOURCE[0]}")/..")"
GIT=(git -c "safe.directory=$REPO" -C "$REPO")
BRANCH=successor/core-v2-v12-runner-binding-remediation
HEAD="$("${GIT[@]}" rev-parse HEAD)"
[[ "$("${GIT[@]}" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}')" == "origin/$BRANCH" ]] || exit 4
[[ "$("${GIT[@]}" rev-parse "origin/$BRANCH")" == "$HEAD" ]] || exit 4
[[ "$("${GIT[@]}" ls-remote --heads origin "$BRANCH" | cut -f1)" == "$HEAD" ]] || exit 4
"${GIT[@]}" merge-base --is-ancestor 94880823ac060539f21b1df4b8374b04a484ad78 "$HEAD" || exit 4

for relative in \
  scripts/run_editor_core_bridge_causal_pilot.sh \
  scripts/train_editor_core_bridge_causal_pilot.py \
  scripts/project_editor_core_bridge_causal_runs.py \
  scripts/launch_editor_core_bridge_causal_zero_step.py \
  scripts/audit_editor_core_bridge_development_causal_pilot.py \
  scripts/audit_editor_core_bridge_a1_a2_fixture_gate.py \
  docs/artifacts/editor-core-editorial-bridge-development-causal-pilot-v1.json; do
  cmp -s <("${GIT[@]}" show "$HEAD:$relative") "$REPO/$relative" || exit 4
done

ROOTFS="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"
CHECKPOINT="$(realpath -e -- "$3")"; PARENT="$(realpath -e -- "$CHECKPOINT/adapter")"
OUTPUTS="$(realpath -e -- "$4")"; ARM="$5"; SEED="$6"
WORKER="$(realpath -e -- "$7")"
[[ "$WORKER" == "$REPO/scripts/train_editor_core_bridge_causal_pilot.py" ]] || exit 4
SLUG="${ARM,,}-seed-$SEED"; OUTPUT="$(realpath -e -- "$OUTPUTS/$SLUG")"
SNAPSHOT="$(realpath -e -- "$8")"
SHA() { sha256sum -- "$1" | cut -d' ' -f1; }

# This checks all six separate empty ext4 targets, published Bridge ancestry,
# model, R2 parent, rootfs, driver snapshot, tokenizer and source bindings.
python3 -B "$REPO/scripts/launch_editor_core_bridge_causal_zero_step.py" \
  --model "$MODEL" --parent-checkpoint "$CHECKPOINT" --rootfs "$ROOTFS" \
  --driver-snapshot "$SNAPSHOT" --outputs "$OUTPUTS" --target-slug "$SLUG" >/dev/null

WORK="$(mktemp -d /tmp/editor-bridge-a1a2.XXXXXXXX)"; ROOT="$WORK/rootfs"; mkdir "$ROOT"
child=""
cleanup() { [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOT" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
python3 -B "$REPO/scripts/project_editor_core_bridge_causal_runs.py" \
  --arm "$ARM" --seed "$SEED" --corpus-output "$WORK/corpus.jsonl" --spec-output "$WORK/spec.json"
CORPUS_SHA="$(SHA "$WORK/corpus.jsonl")"; SPEC_SHA="$(SHA "$WORK/spec.json")"
SPEC_ID="$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1],"rb"))["run_spec_identity"])' "$WORK/spec.json")"
WORKER_SHA="$(SHA "$WORKER")"; LAUNCHER_SHA="$(SHA "$REPO/scripts/run_editor_core_bridge_causal_pilot.sh")"
MODEL_SHA=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
PARENT_SHA=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02
ROOTFS_SHA=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
[[ "$(SHA "$ROOTFS")" == "$ROOTFS_SHA" ]] || exit 4

setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- \
  "$ROOTFS" "$ROOT" "$MODEL" "$PARENT" "$WORK/corpus.jsonl" "$WORK/spec.json" \
  "$OUTPUT" "$WORKER" "$SNAPSHOT" "$MODEL_SHA" "$PARENT_SHA" "$CORPUS_SHA" \
  "$SPEC_SHA" "$ROOTFS_SHA" "$WORKER_SHA" "$LAUNCHER_SHA" "$SPEC_ID" "$SLUG" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"
mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"
mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"
mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"
mount --bind "$9" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/parent" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
mount --bind "$4" "$2/tmp/input/parent"; mount -o remount,bind,ro "$2/tmp/input/parent"
for pair in "$5:corpus.jsonl" "$6:spec.json" "$8:worker.py"; do
  src="${pair%%:*}"; name="${pair#*:}"
  touch "$2/tmp/input/authority/$name"
  mount --bind "$src" "$2/tmp/input/authority/$name"
  mount -o remount,bind,ro "$2/tmp/input/authority/$name"
done
mount --bind "$7" "$2/tmp/output"
[[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]] || exit 5
env -i CC=/usr/bin/gcc CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 \
  HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false \
  TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib \
  TRAINING_EXECUTION_AUTHORIZED=1 MODEL_SHA256="${10}" PARENT_SHA256="${11}" \
  CORPUS_SHA256="${12}" CONFIG_SHA256="${13}" ROOTFS_SHA256="${14}" \
  WORKER_SHA256="${15}" LAUNCHER_SHA256="${16}" RUN_SPEC_IDENTITY="${17}" \
  OUTPUT_SLUG="${18}" /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B \
  /tmp/input/authority/worker.py /tmp/input/model /tmp/input/parent \
  /tmp/input/authority/corpus.jsonl /tmp/input/authority/spec.json /tmp/output
CHILD
child=$!; wait "$child"; child=""
