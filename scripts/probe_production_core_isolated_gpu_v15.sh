#!/usr/bin/env bash
# No model, adapter, schedule, candidate, or attempt is accepted by this probe.
set -euo pipefail
[[ ($# == 1 || $# == 2 || $# == 5) && $(id -u) == 0 && ! -L $1 ]] || exit 2
ROOTFS_TAR="$(realpath -e -- "$1")"
MODE="${2:-canonical}"
[[ $MODE == canonical || $MODE == diagnostic-host-wsl-lib || $MODE == diagnostic-host-wsl-drivers || $MODE == diagnostic-host-wsl-all || $MODE == diagnostic-host-network || $MODE == production-snapshot ]] || exit 2
DRIVER_ROOT="${3:-}"; HELPER="${4:-}"; HELPER_SHA256="${5:-}"
if [[ $MODE == production-snapshot ]]; then
  [[ $# == 5 && ! -L $DRIVER_ROOT && ! -L $HELPER && $HELPER_SHA256 =~ ^[0-9a-f]{64}$ ]] || exit 2
  DRIVER_ROOT="$(realpath -e -- "$DRIVER_ROOT")"; HELPER="$(realpath -e -- "$HELPER")"
  [[ $(sha256sum "$HELPER" | cut -d' ' -f1) == "$HELPER_SHA256" ]] || exit 3
  python3 -B "$HELPER" --root "$DRIVER_ROOT" >/dev/null || exit 3
fi
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
[[ -f $ROOTFS_TAR && $(sha256sum "$ROOTFS_TAR" | cut -d' ' -f1) == "$EXPECTED_ROOTFS" ]] || exit 3
PARENT_NETNS="$(readlink /proc/self/ns/net)"
PARENT_PIDNS="$(readlink /proc/self/ns/pid)"
namespace_args=(--mount --net --pid --ipc --uts --fork)
if [[ $MODE == diagnostic-host-network ]]; then namespace_args=(--mount --pid --ipc --uts --fork); fi
unshare "${namespace_args[@]}" bash -s -- "$ROOTFS_TAR" "$PARENT_NETNS" "$PARENT_PIDNS" "$MODE" "$DRIVER_ROOT" "$HELPER" "$HELPER_SHA256" <<'CHILD'
set -euo pipefail
ROOTFS_TAR="$1"; PARENT_NETNS="$2"; PARENT_PIDNS="$3"; MODE="$4"
DRIVER_ROOT="$5"; HELPER="$6"; HELPER_SHA256="$7"
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
NETWORK_ISOLATED=false
if [[ $MODE != diagnostic-host-network ]]; then NETWORK_ISOLATED=true; fi
[[ $$ == 1 && $(readlink /proc/self/ns/pid) != "$PARENT_PIDNS" ]] || exit 4
if [[ $NETWORK_ISOLATED == true ]]; then
  [[ $(readlink /proc/self/ns/net) != "$PARENT_NETNS" ]] || exit 4
else
  [[ $(readlink /proc/self/ns/net) == "$PARENT_NETNS" ]] || exit 4
fi
WORK="$(mktemp -d /tmp/pcq-v15-probe.XXXXXXXX)"
ROOTFS="$WORK/rootfs"
mkdir "$ROOTFS"
mounted=()
cleanup() {
  local i
  for ((i=${#mounted[@]}-1; i>=0; i--)); do umount -l -- "${mounted[$i]}" 2>/dev/null || true; done
  rm -rf -- "$WORK"
}
trap cleanup EXIT INT TERM
exec {rootfs_fd}<"$ROOTFS_TAR"
[[ $(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d' ' -f1) == "$EXPECTED_ROOTFS" ]] || exit 4
tar -xf "/proc/self/fd/$rootfs_fd" -C "$ROOTFS"
[[ $(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d' ' -f1) == "$EXPECTED_ROOTFS" ]] || exit 4
if [[ $MODE == diagnostic-host-wsl-lib || $MODE == diagnostic-host-wsl-all ]]; then
  mount --bind /usr/lib/wsl/lib "$ROOTFS/usr/lib/wsl/lib"
  mounted+=("$ROOTFS/usr/lib/wsl/lib")
  mount -o remount,bind,ro "$ROOTFS/usr/lib/wsl/lib"
fi
if [[ $MODE == diagnostic-host-wsl-drivers || $MODE == diagnostic-host-wsl-all ]]; then
  mount --bind /usr/lib/wsl/drivers "$ROOTFS/usr/lib/wsl/drivers"
  mounted+=("$ROOTFS/usr/lib/wsl/drivers")
  mount -o remount,bind,ro "$ROOTFS/usr/lib/wsl/drivers"
fi
if [[ $MODE == production-snapshot ]]; then
  exec {helper_fd}<"$HELPER"
  [[ $(sha256sum "/proc/self/fd/$helper_fd" | cut -d' ' -f1) == "$HELPER_SHA256" ]] || exit 4
  cp "/proc/self/fd/$helper_fd" "$WORK/manifest.py"
  python3 -B "$WORK/manifest.py" --root "$DRIVER_ROOT" >/dev/null || exit 4
  mount --bind "$DRIVER_ROOT" "$ROOTFS/usr/lib/wsl/drivers"
  mounted+=("$ROOTFS/usr/lib/wsl/drivers")
  mount -o remount,bind,ro "$ROOTFS/usr/lib/wsl/drivers"
  driver_opts="$(findmnt -no OPTIONS --target "$ROOTFS/usr/lib/wsl/drivers")"
  [[ ",$driver_opts," == *,ro,* ]] || exit 5
  python3 -B "$WORK/manifest.py" --root "$ROOTFS/usr/lib/wsl/drivers" >/dev/null || exit 4
fi
mount -t proc proc "$ROOTFS/proc"; mounted+=("$ROOTFS/proc")
for name in dev sys; do
  mount --rbind "/$name" "$ROOTFS/$name"
  mounted+=("$ROOTFS/$name")
  mount --make-rslave "$ROOTFS/$name"
done
mount -t tmpfs -o size=64m,mode=1777 tmpfs "$ROOTFS/tmp"; mounted+=("$ROOTFS/tmp")
interfaces="$(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -)"
routes="$(awk 'NR>1 {n++} END {print n+0}' /proc/net/route)"
if [[ $NETWORK_ISOLATED == true ]]; then [[ $interfaces == lo && $routes == 0 ]] || exit 5; fi
env -i CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib TRITON_CACHE_DIR=/tmp/triton-cache WSL_LIB_SOURCE="$MODE" NETWORK_ISOLATED="$NETWORK_ISOLATED" \
  /usr/sbin/chroot "$ROOTFS" /opt/production-core-runtime/bin/python -I -B -c '
import ctypes
import json
import os
import bitsandbytes, peft, torch, transformers
cuda_available = bool(torch.cuda.is_available())
try:
    torch.cuda.init()
except Exception as error:
    torch_cuda_init_error = type(error).__name__ + ": " + str(error)
else:
    torch_cuda_init_error = None
try:
    cuda = ctypes.CDLL("/usr/lib/wsl/lib/libcuda.so.1")
except OSError:
    libcuda_load, cu_init_result, cu_device_count = "FAIL", None, None
else:
    libcuda_load = "PASS"
    cu_init_result = int(cuda.cuInit(0))
    count = ctypes.c_int()
    cu_device_count = int(count.value) if cu_init_result == 0 and cuda.cuDeviceGetCount(ctypes.byref(count)) == 0 else None
print(json.dumps({
    "schema": "pastila-production-core-v15-isolated-gpu-probe",
    "wsl_lib_source": os.environ["WSL_LIB_SOURCE"],
    "rootfs_sha256": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
    "versions": {"bitsandbytes": bitsandbytes.__version__, "peft": peft.__version__, "torch": torch.__version__, "transformers": transformers.__version__},
    "cuda_available": cuda_available,
    "device_dxg": os.path.exists("/dev/dxg"),
    "libcuda_load": libcuda_load,
    "cu_init_result": cu_init_result,
    "cu_device_count": cu_device_count,
    "torch_cuda_init_error": torch_cuda_init_error,
    "network_isolated": os.environ["NETWORK_ISOLATED"] == "true",
    "pid_isolated": True,
}, sort_keys=True, separators=(",", ":")))'
CHILD
