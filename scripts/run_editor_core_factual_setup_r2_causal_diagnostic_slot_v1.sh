#!/usr/bin/env bash
set -euo pipefail
[[ $# == 15 && ${15:-} == --execute-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_CAUSAL_DIAGNOSTIC_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; CHECKPOINT="$(realpath -e -- "$3")"; PARENT="$(realpath -e -- "$CHECKPOINT/adapter")"; CORPUS="$(realpath -e -- "$4")"; SIGNAL="$(realpath -e -- "$5")"; DEVELOPMENT="$(realpath -e -- "$6")"; OUTPUT="$(realpath -e -- "$7")"; WORKER="$(realpath -e -- "$8")"; VERIFIER="$(realpath -e -- "$9")"; ARM="${10}"; SEED="${11}"; PREFLIGHT_ROUTE="$(realpath -e -- "${12}")"; PREFLIGHT="$(realpath -e -- "${13}")"; CHALLENGER="$(realpath -e -- "${14}")"
REPO=/mnt/c/pf9; SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
PYTHONPATH="$REPO/scripts" python3 -B "$VERIFIER" --arm "$ARM" --seed "$SEED" >/dev/null
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]]
bash "$PREFLIGHT_ROUTE" "$ROOTFS" "$MODEL" "$CORPUS" "$CHALLENGER" "$OUTPUT" "$PREFLIGHT" "$WORKER" --preflight-only >/dev/null
WORK="$(mktemp -d /tmp/editor-causal-slot.XXXXXXXX)"; ROOT="$WORK/root"; child=""
mkdir "$ROOT"; cleanup(){ [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOT" 2>/dev/null || true; rm -rf -- "$WORK"; }; trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS" "$ROOT" "$MODEL" "$PARENT" "$CORPUS" "$SIGNAL" "$DEVELOPMENT" "$OUTPUT" "$WORKER" "$SNAPSHOT" "$ARM" "$SEED" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"; mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"; mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mount --bind "${10}" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/parent" "$2/tmp/input/authority" "$2/tmp/output"; mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"; mount --bind "$4" "$2/tmp/input/parent"; mount -o remount,bind,ro "$2/tmp/input/parent"
for pair in "$5:corpus.jsonl" "$6:signal.jsonl" "$7:development.jsonl" "$9:worker.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$8" "$2/tmp/output"; [[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]]
env -i CAUSAL_DIAGNOSTIC_REAL_RUN_AUTHORIZED=1 CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/worker.py /tmp/input/model /tmp/input/parent /tmp/input/authority/corpus.jsonl /tmp/input/authority/signal.jsonl /tmp/input/authority/development.jsonl /tmp/output "${11}" "${12}"
CHILD
child=$!; wait "$child"; child=""
