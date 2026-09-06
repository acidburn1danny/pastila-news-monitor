#!/usr/bin/env bash
set -euo pipefail

readonly ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
readonly REQUIRED_ANCESTOR="ca9e7027ad4472412d77291c3446dc1c3b1de026"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO="$(dirname -- "$SCRIPT_DIR")"
readonly PROBE="$REPO/src/pastila_scout/production_core_inference_resource_calibration_v1.py"

if [[ $# -ne 5 ]]; then
  echo "usage: $0 ROOTFS MODEL_REPO ADAPTER CANDIDATE RECEIPT" >&2
  exit 2
fi
readonly ROOTFS="$(realpath -e -- "$1")"
readonly MODEL_REPO="$(realpath -e -- "$2")"
readonly ADAPTER="$(realpath -e -- "$3")"
readonly CANDIDATE="$4"
readonly RECEIPT="$5"
case "$CANDIDATE" in
  pastila-editor-core-v1.1-experimental|pastila-editor-core-v1.2-experimental) ;;
  *) echo "invalid candidate" >&2; exit 2 ;;
esac
[[ ! -L "$1" && ! -L "$2" && ! -L "$3" && -f "$PROBE" && ! -L "$PROBE" ]] || {
  echo "noncanonical calibration input" >&2; exit 3;
}
readonly GIT_POINTER="$(sed -n 's/^gitdir: //p' "$REPO/.git")"
readonly GIT_DIR="$(wslpath -u "$GIT_POINTER")"
readonly HEAD_COMMIT="$(git --git-dir="$GIT_DIR" rev-parse HEAD)"
readonly HEAD_TREE="$(git --git-dir="$GIT_DIR" show -s --format=%T HEAD)"
git --git-dir="$GIT_DIR" merge-base --is-ancestor "$REQUIRED_ANCESTOR" "$HEAD_COMMIT" || {
  echo "calibration HEAD authority mismatch" >&2; exit 4;
}
readonly PROBE_SHA256="$(sha256sum "$PROBE" | cut -d' ' -f1)"
readonly LAUNCHER_SHA256="$(sha256sum "$0" | cut -d' ' -f1)"
[[ "$(git --git-dir="$GIT_DIR" show "$HEAD_COMMIT:src/pastila_scout/production_core_inference_resource_calibration_v1.py" | sha256sum | cut -d' ' -f1)" == "$PROBE_SHA256" ]] || exit 4
[[ "$(git --git-dir="$GIT_DIR" show "$HEAD_COMMIT:scripts/calibrate_production_core_inference_resources_v1.sh" | sha256sum | cut -d' ' -f1)" == "$LAUNCHER_SHA256" ]] || exit 4
readonly RECEIPT_PARENT="$(dirname -- "$RECEIPT")"
[[ "$(realpath -e -- "$RECEIPT_PARENT")" == "/home/pastila/.pastila-runtime/production-core-qualification-v1/inference-receipts" && ! -e "$RECEIPT" && ! -L "$RECEIPT" ]] || exit 4
readonly RECEIPT_TMP="$(mktemp -p "$RECEIPT_PARENT" .receipt.XXXXXXXX)"
[[ -f "$RECEIPT_TMP" && ! -L "$RECEIPT_TMP" ]] || exit 4
rootfs_identity() {
  tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$ROOTFS" -cf - . \
    | sha256sum | cut -d' ' -f1
}
readonly ROOTFS_BEFORE="$(rootfs_identity)"
[[ "$ROOTFS_BEFORE" == "$ROOTFS_SHA256" ]] || { echo "rootfs mismatch" >&2; exit 5; }

mounted=()
cleanup() {
  rm -f -- "$RECEIPT_TMP"
  local i
  for ((i=${#mounted[@]}-1; i>=0; i--)); do umount -l -- "${mounted[$i]}" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM
[[ "$(id -u)" == 0 ]] || { echo "launcher requires root" >&2; exit 5; }
unshare --mount --net --fork bash -s -- \
  "$ROOTFS" "$MODEL_REPO" "$ADAPTER" "$PROBE" "$CANDIDATE" "$HEAD_COMMIT" "$HEAD_TREE" \
  "$PROBE_SHA256" "$LAUNCHER_SHA256" "$ROOTFS_SHA256" >"$RECEIPT_TMP" <<'CHILD'
set -euo pipefail
ROOTFS="$1"; MODEL_REPO="$2"; ADAPTER="$3"; PROBE="$4"; CANDIDATE="$5"
HEAD_COMMIT="$6"; HEAD_TREE="$7"; PROBE_SHA256="$8"; LAUNCHER_SHA256="$9"; ROOTFS_SHA256="${10}"
mounted=()
cleanup() { local i; for ((i=${#mounted[@]}-1; i>=0; i--)); do umount -l -- "${mounted[$i]}" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
mount --bind "$ROOTFS" "$ROOTFS"; mounted+=("$ROOTFS")
mount -o remount,bind,ro "$ROOTFS"
for name in dev proc sys; do
  mount --rbind "/$name" "$ROOTFS/$name"; mounted+=("$ROOTFS/$name")
  mount --make-rslave "$ROOTFS/$name"
done
mount -t tmpfs -o size=64m,mode=1777 tmpfs "$ROOTFS/tmp"; mounted+=("$ROOTFS/tmp")
mkdir -p "$ROOTFS/tmp/model-repo" "$ROOTFS/tmp/adapter"
mount --bind "$MODEL_REPO" "$ROOTFS/tmp/model-repo"; mounted+=("$ROOTFS/tmp/model-repo")
mount -o remount,bind,ro "$ROOTFS/tmp/model-repo"
mount --bind "$ADAPTER" "$ROOTFS/tmp/adapter"; mounted+=("$ROOTFS/tmp/adapter")
mount -o remount,bind,ro "$ROOTFS/tmp/adapter"
install -m 0444 "$PROBE" "$ROOTFS/tmp/probe.py"
exec env -i CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 \
  PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 \
  TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib TRITON_CACHE_DIR=/tmp/triton-cache \
  CALIBRATION_COMMIT="$HEAD_COMMIT" CALIBRATION_TREE="$HEAD_TREE" \
  CALIBRATION_PROBE_SHA256="$PROBE_SHA256" CALIBRATION_LAUNCHER_SHA256="$LAUNCHER_SHA256" \
  CALIBRATION_ROOTFS_SHA256="$ROOTFS_SHA256" \
  /usr/sbin/chroot "$ROOTFS" /opt/production-core-runtime/bin/python -I /tmp/probe.py \
  /tmp/model-repo/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142 /tmp/adapter "$CANDIDATE"
CHILD
[[ "$(rootfs_identity)" == "$ROOTFS_BEFORE" ]] || { echo "rootfs mutated" >&2; exit 6; }
[[ "$(wc -l < "$RECEIPT_TMP")" -eq 2 ]] || { echo "invalid receipt framing" >&2; exit 7; }
readonly RECORDED_IDENTITY="$(sed -n '1p' "$RECEIPT_TMP" | tr -d '\n' | sha256sum | cut -d' ' -f1)"
[[ "$RECORDED_IDENTITY" == "$(sed -n '2p' "$RECEIPT_TMP")" ]] || { echo "receipt identity mismatch" >&2; exit 7; }
chmod 0444 "$RECEIPT_TMP"
mv -Tn -- "$RECEIPT_TMP" "$RECEIPT"
[[ ! -e "$RECEIPT_TMP" && -f "$RECEIPT" && ! -L "$RECEIPT" ]] || { echo "receipt publish collision" >&2; exit 7; }
sync -f "$RECEIPT"
sync -f "$RECEIPT_PARENT"
[[ "$(wc -l < "$RECEIPT")" -eq 2 ]] || { echo "published receipt framing mismatch" >&2; exit 7; }
[[ "$(sed -n '1p' "$RECEIPT" | tr -d '\n' | sha256sum | cut -d' ' -f1)" == "$RECORDED_IDENTITY" ]] || { echo "published receipt byte mismatch" >&2; exit 7; }
printf '%s\n' "$RECORDED_IDENTITY"
