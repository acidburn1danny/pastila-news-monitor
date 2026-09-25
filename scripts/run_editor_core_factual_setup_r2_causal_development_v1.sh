#!/usr/bin/env bash
set -euo pipefail
[[ $# == 9 && ${9:-} == --inference-authorized && $(id -u) == 0 ]] || exit 2
ROOTFS=$(realpath -e -- "$1"); MODEL=$(realpath -e -- "$2"); R2=$(realpath -e -- "$3"); CANDIDATES=$(realpath -e -- "$4"); REQUESTS=$(realpath -e -- "$5"); MANIFEST=$(realpath -e -- "$6"); OUTPUT=$(realpath -e -- "$7"); WORKER=$(realpath -e -- "$8")
[[ -d $OUTPUT && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]] || exit 3
WORK=$(mktemp -d /tmp/editor-causal-development.XXXXXXXX); ROOT=$WORK/root; mkdir "$ROOT"; child=""
cleanup(){ [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOT" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS" "$ROOT" "$MODEL" "$R2" "$CANDIDATES" "$REQUESTS" "$MANIFEST" "$OUTPUT" "$WORKER" /root/pf9-v15-wsl-drivers-snapshot <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"; mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"; mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mount --bind "${10}" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/r2" "$2/tmp/input/candidates" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"; mount --bind "$4" "$2/tmp/input/r2"; mount -o remount,bind,ro "$2/tmp/input/r2"; mount --bind "$5" "$2/tmp/input/candidates"; mount -o remount,bind,ro "$2/tmp/input/candidates"
for pair in "$6:requests.jsonl" "$7:candidates.json" "$9:worker.py" /mnt/c/pf9/scripts/editor_core_bridge_json_constraint_v3.py:editor_core_bridge_json_constraint_v3.py /mnt/c/pf9/scripts/evaluate_editor_core_factual_setup_benchmark_v1.py:evaluate_editor_core_factual_setup_benchmark_v1.py; do src=${pair%%:*}; name=${pair#*:}; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$8" "$2/tmp/output"; [[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]]
env -i EDITOR_CAUSAL_DEVELOPMENT_AUTHORIZED=1 CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/worker.py --model /tmp/input/model --requests /tmp/input/authority/requests.jsonl --candidates /tmp/input/authority/candidates.json --output /tmp/output
CHILD
child=$!; wait "$child"; child=""
