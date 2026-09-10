#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 8 ]]; then echo "usage: launcher ROOTFS MODEL PREDECESSOR CORPUS CONFIG OUTPUT TRAINER MODE" >&2; exit 2; fi
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; PREDECESSOR="$(realpath -e -- "$3")"
CORPUS="$(realpath -e -- "$4")"; CONFIG="$(realpath -e -- "$5")"; OUTPUT="$(realpath -m -- "$6")"; TRAINER="$(realpath -e -- "$7")"
MODE="$8"; [[ "$MODE" == SMOKE || "$MODE" == FULL ]] || exit 3
[[ "$(id -u)" == 0 && -f "$ROOTFS_TAR" && -d "$MODEL" && -d "$PREDECESSOR" && -f "$CORPUS" && -f "$CONFIG" && -f "$TRAINER" ]] || exit 3
mkdir -p "$OUTPUT"; [[ -z "$(find "$OUTPUT" -mindepth 1 -print -quit)" ]] || exit 3
ROOTFS_SHA="$(sha256sum "$ROOTFS_TAR" | cut -d' ' -f1)"; [[ "$ROOTFS_SHA" == 9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826 ]] || exit 3
CORPUS_SHA="$(sha256sum "$CORPUS" | cut -d' ' -f1)"; CONFIG_SHA="$(sha256sum "$CONFIG" | cut -d' ' -f1)"
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256sum -- "$path" | cut -d' ' -f1)"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
[[ -z "$(find "$MODEL" "$PREDECESSOR" -mindepth 1 -maxdepth 1 \( -type l -o ! -type f \) -print -quit)" ]] || exit 3
MODEL_SHA="$(flat_manifest "$MODEL")"; PREDECESSOR_SHA="$(flat_manifest "$PREDECESSOR")"; LAUNCHER_SHA="$(sha256sum "$(realpath -e -- "$0")" | cut -d' ' -f1)"; TRAINER_SHA="$(sha256sum "$TRAINER" | cut -d' ' -f1)"
WORK="$(mktemp -d /tmp/pcs-train.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"; mounted=()
cleanup() { local i; for ((i=${#mounted[@]}-1; i>=0; i--)); do umount -l -- "${mounted[$i]}" 2>/dev/null || true; done; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
unshare --mount --net --pid --ipc --uts --fork bash -c '
set -euo pipefail
tar -xf "$1" -C "$2"
mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"
mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/predecessor" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
mount --bind "$4" "$2/tmp/input/predecessor"; mount -o remount,bind,ro "$2/tmp/input/predecessor"
for pair in "$5:corpus.jsonl" "$6:config.json" "$8:trainer.py"; do source="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$source" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$7" "$2/tmp/output"
for target in "$2" "$2/tmp/input/model" "$2/tmp/input/predecessor" "$2/tmp/input/authority/corpus.jsonl" "$2/tmp/input/authority/config.json" "$2/tmp/input/authority/trainer.py"; do
  options="$(findmnt -n -o OPTIONS --target "$target")"
  [[ ",$options," == *,ro,* ]] || exit 5
done
options="$(findmnt -n -o OPTIONS --target "$2/tmp/output")"; [[ ",$options," != *,ro,* ]] || exit 5
[[ "$(awk -F: '\''NR>2 {gsub(/ /,"",$1); print $1}'\'' /proc/net/dev | sort -u | paste -sd, -)" == lo ]] || exit 5
env -i CC=/usr/bin/gcc CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRAINING_MODE="${12}" TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib CORPUS_SHA256="$9" CONFIG_SHA256="${10}" PREDECESSOR_SHA256="${11}" MODEL_SHA256="${13}" ROOTFS_SHA256="${14}" LAUNCHER_SHA256="${15}" TRAINER_SHA256="${16}" AUTHORITY_MOUNTS_READ_ONLY=1 OUTPUT_MOUNT_WRITABLE=1 /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I /tmp/input/authority/trainer.py /tmp/input/model /tmp/input/predecessor /tmp/input/authority/corpus.jsonl /tmp/input/authority/config.json /tmp/output
' bash "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$PREDECESSOR" "$CORPUS" "$CONFIG" "$OUTPUT" "$TRAINER" "$CORPUS_SHA" "$CONFIG_SHA" "$PREDECESSOR_SHA" "$MODE" "$MODEL_SHA" "$ROOTFS_SHA" "$LAUNCHER_SHA" "$TRAINER_SHA"
