#!/usr/bin/env bash
set -euo pipefail

readonly AUTHORITY_ROOT="/home/pastila/.pastila-runtime/production-core-qualification-v1"
readonly ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "invalid runtime rootfs" >&2
  exit 2
fi
readonly ROOTFS="$1"
readonly ROOTFS_PARENT="$(dirname -- "$ROOTFS")"
readonly ROOTFS_NAME="$(basename -- "$ROOTFS")"
if [[ "$ROOTFS_PARENT" != "$AUTHORITY_ROOT" || ! "$ROOTFS_NAME" =~ ^materialized-[a-z0-9-]+$ ]]; then
  echo "invalid runtime rootfs" >&2
  exit 2
fi
if [[ ! -d "$ROOTFS" || -L "$ROOTFS" || "$(realpath -e -- "$ROOTFS")" != "$ROOTFS" ]]; then
  echo "invalid runtime rootfs resolution" >&2
  exit 2
fi
readonly PYTHON="/opt/production-core-runtime/bin/python"
readonly MODE="${2:-calibrate}"
case "$MODE" in
  calibrate) readonly ENTRY="/opt/qualification/production_core_synthetic_calibration_v1.py" ;;
  probe) readonly ENTRY="/opt/qualification/production_core_runtime_probe_v1.py" ;;
  *) echo "invalid offline runtime operation" >&2; exit 3 ;;
esac

exec unshare --net --mount --fork sh -c '
  set -eu
  mount --bind "$1" "$1"
  mount -o remount,bind,ro "$1"
  before="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$1" -cf - . | sha256sum | cut -d" " -f1)"
  if [ "$before" != "$5" ]; then
    echo "runtime rootfs identity mismatch" >&2
    exit 4
  fi
  mount --rbind /dev "$1/dev"
  mount -t proc proc "$1/proc"
  mount -t sysfs sysfs "$1/sys"
  mount -t tmpfs -o size=64m,mode=1777 tmpfs "$1/tmp"
  if find "$1/sys/class/net" -mindepth 1 -maxdepth 1 ! -name lo -print -quit | grep -q .; then
    echo "network namespace contains a non-loopback interface" >&2
    exit 5
  fi
  set +e
  if [ "$4" = calibrate ]; then
    env -i \
      CUBLAS_WORKSPACE_CONFIG=:4096:8 \
      CUDA_VISIBLE_DEVICES=0 \
      PYTHONHASHSEED=0 \
      TOKENIZERS_PARALLELISM=false \
      /usr/sbin/chroot "$1" "$2" -I "$3" --trials 20
    result=$?
  else
    env -i \
      CUBLAS_WORKSPACE_CONFIG=:4096:8 \
      CUDA_VISIBLE_DEVICES=0 \
      PYTHONHASHSEED=0 \
      TOKENIZERS_PARALLELISM=false \
      /usr/sbin/chroot "$1" "$2" -I "$3"
    result=$?
  fi
  set -e
  umount "$1/tmp"
  umount "$1/sys"
  umount "$1/proc"
  umount -R "$1/dev"
  after="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$1" -cf - . | sha256sum | cut -d" " -f1)"
  if [ "$after" != "$5" ]; then
    echo "runtime rootfs mutated during execution" >&2
    exit 6
  fi
  exit "$result"
' sh "$ROOTFS" "$PYTHON" "$ENTRY" "$MODE" "$ROOTFS_SHA256"
