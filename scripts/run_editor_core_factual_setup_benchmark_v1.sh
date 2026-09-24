#!/usr/bin/env bash
set -euo pipefail
[[ $# == 8 && ${8:-} == --inference-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_SETUP_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; ADAPTER="$(realpath -e -- "$3")"
REQUESTS="$(realpath -e -- "$4")"; OUTPUT="$(realpath -e -- "$5")"; CANDIDATE="$6"; WORKER="$(realpath -e -- "$7")"
REPOSITORY=/mnt/c/pf9; SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
CONSTRAINT="$REPOSITORY/scripts/editor_core_bridge_json_constraint_v3.py"
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_MODEL=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
EXPECTED_REQUESTS=436adcaf59392c852965501a1b1ed8068c991619e8f3de9e2cd92047f80ae51f
EXPECTED_WORKER=77d562f0c3b688b9b6697b11426f7d12f9af9ffe446829c162d235af7b8c2be3
EXPECTED_CONSTRAINT=5c98158062dcf19d484a641b456b509bdcca1e5d21eba14754977bbd6a36ba6c
case "$CANDIDATE" in
  blind-candidate-x) EXPECTED_ADAPTER=50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4 ;;
  blind-candidate-y) EXPECTED_ADAPTER=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02 ;;
  *) exit 4 ;;
esac
sha256() { sha256sum -- "$1" | cut -d' ' -f1; }
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256 "$path")"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
[[ $(sha256 "$ROOTFS_TAR") == "$EXPECTED_ROOTFS" && $(flat_manifest "$MODEL") == "$EXPECTED_MODEL" ]] || exit 4
[[ $(flat_manifest "$ADAPTER") == "$EXPECTED_ADAPTER" && $(sha256 "$REQUESTS") == "$EXPECTED_REQUESTS" ]] || exit 4
[[ $(sha256 "$WORKER") == "$EXPECTED_WORKER" && $(sha256 "$CONSTRAINT") == "$EXPECTED_CONSTRAINT" ]] || exit 4
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]] || exit 4
[[ -d $SNAPSHOT && ! -L $SNAPSHOT && $(findmnt -n -o FSTYPE --target "$SNAPSHOT") == ext4 ]] || exit 4
WORK="$(mktemp -d /tmp/editor-factual-setup-v1.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"; child=""
cleanup() { [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOTFS" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$ADAPTER" "$REQUESTS" "$OUTPUT" "$WORKER" "$CANDIDATE" "$SNAPSHOT" "$EXPECTED_MODEL" "$EXPECTED_ADAPTER" "$EXPECTED_REQUESTS" "$EXPECTED_WORKER" "$CONSTRAINT" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"
mount -t proc proc "$2/proc"; mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mount --bind "$9" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/adapter" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
mount --bind "$4" "$2/tmp/input/adapter"; mount -o remount,bind,ro "$2/tmp/input/adapter"
for pair in "$5:requests.jsonl" "$7:worker.py" "${14}:editor_core_bridge_json_constraint_v3.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$6" "$2/tmp/output"
[[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]] || exit 5
env -i CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 EDITOR_SETUP_INFERENCE_AUTHORIZED=1 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib MODEL_SHA256="${10}" ADAPTER_SHA256="${11}" REQUESTS_SHA256="${12}" WORKER_SHA256="${13}" /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/worker.py /tmp/input/model /tmp/input/adapter /tmp/input/authority/requests.jsonl /tmp/output "$8"
CHILD
child=$!; wait "$child"; child=""
