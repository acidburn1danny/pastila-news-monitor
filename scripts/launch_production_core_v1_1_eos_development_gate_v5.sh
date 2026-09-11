#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 7 ]]; then echo "usage: launcher ROOTFS MODEL ADAPTER PROBES OUTPUT RUNNER MATERIALIZATION" >&2; exit 2; fi
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; ADAPTER="$(realpath -e -- "$3")"
PROBES="$(realpath -e -- "$4")"; OUTPUT="$(realpath -m -- "$5")"; RUNNER="$(realpath -e -- "$6")"; LABEL="$7"
[[ "$(id -u)" == 0 && "$LABEL" =~ ^(A|B)$ ]] || exit 3
mkdir -p "$OUTPUT"; [[ -z "$(find "$OUTPUT" -mindepth 1 -print -quit)" ]] || exit 3
[[ "$(sha256sum "$ROOTFS_TAR" | cut -d' ' -f1)" == 9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826 ]] || exit 3
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256sum -- "$path" | cut -d' ' -f1)"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
[[ -z "$(find "$MODEL" "$ADAPTER" -mindepth 1 -maxdepth 1 \( -type l -o ! -type f \) -print -quit)" ]] || exit 3
MODEL_SHA="$(flat_manifest "$MODEL")"; ADAPTER_SHA="$(flat_manifest "$ADAPTER")"; DEVELOPMENT_SHA="$(sha256sum "$PROBES" | cut -d' ' -f1)"
WORK="$(mktemp -d /tmp/pcs-dev-v5.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"
cleanup() { umount -l -- "$ROOTFS/tmp/output" "$ROOTFS/tmp/input/authority/runner.py" "$ROOTFS/tmp/input/authority/probes.jsonl" "$ROOTFS/tmp/input/adapter" "$ROOTFS/tmp/input/model" "$ROOTFS/sys" "$ROOTFS/dev" "$ROOTFS/proc" "$ROOTFS" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
unshare --mount --net --pid --ipc --uts --fork bash -c '
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mkdir -p "$2/tmp/input/model" "$2/tmp/input/adapter" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
mount --bind "$4" "$2/tmp/input/adapter"; mount -o remount,bind,ro "$2/tmp/input/adapter"
for pair in "$5:probes.jsonl" "$7:runner.py"; do source="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$source" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$6" "$2/tmp/output"
for target in "$2" "$2/tmp/input/model" "$2/tmp/input/adapter" "$2/tmp/input/authority/probes.jsonl" "$2/tmp/input/authority/runner.py"; do options="$(findmnt -n -o OPTIONS --target "$target")"; [[ ",$options," == *,ro,* ]] || exit 5; done
options="$(findmnt -n -o OPTIONS --target "$2/tmp/output")"; [[ ",$options," != *,ro,* ]] || exit 5
[[ "$(awk -F: '\''NR>2 {gsub(/ /,"",$1); print $1}'\'' /proc/net/dev | sort -u | paste -sd, -)" == lo ]] || exit 5
env -i ADAPTER_SHA256="$9" CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 DEVELOPMENT_SHA256="${10}" HF_HUB_OFFLINE=1 MODEL_SHA256="$8" PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I /tmp/input/authority/runner.py /tmp/input/model /tmp/input/adapter /tmp/input/authority/probes.jsonl /tmp/output "${11}"
' bash "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$ADAPTER" "$PROBES" "$OUTPUT" "$RUNNER" "$MODEL_SHA" "$ADAPTER_SHA" "$DEVELOPMENT_SHA" "$LABEL"
