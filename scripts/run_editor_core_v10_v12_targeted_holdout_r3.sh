#!/usr/bin/env bash
set -euo pipefail
[[ $# == 8 && ${8:-} == --evaluate-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_CORE_R3_EVALUATION_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; ADAPTER="$(realpath -e -- "$3")"
REQUESTS="$(realpath -e -- "$4")"; OUTPUT="$(realpath -e -- "$5")"; RUNNER="$(realpath -e -- "$6")"; CANDIDATE="$7"
SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
REPOSITORY=/mnt/c/pf9
EXPECTED_PARENT_COMMIT=ba5220431a28ac8a83e0671a07be83ba990cda49
EXPECTED_PARENT_TREE=b12df340ff4b1543248d793ff55bcaf68527040b
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_MODEL=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
EXPECTED_REQUESTS=dc0bc9168c83d9a1711fb24e73170a8f838cce343b4312c7f2288cd9a48d59a6
EXPECTED_RUNNER=411f0d9daae90fc90433bbdb89728953536cdec74dde05692abf8bb8a3e7b878
case "$CANDIDATE" in
  r2-step-9) EXPECTED_ADAPTER=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02 ;;
  r3-step-6) EXPECTED_ADAPTER=eaa142cb58c2b795e75ce1b57746950e6fcd3026bc5dd2ac8d55c210c5ce6a00 ;;
  *) exit 4 ;;
esac
sha256() { sha256sum -- "$1" | cut -d' ' -f1; }
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256 "$path")"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
GIT=(git -c "safe.directory=$REPOSITORY" -C "$REPOSITORY")
[[ $("${GIT[@]}" rev-parse HEAD^) == "$EXPECTED_PARENT_COMMIT" && $("${GIT[@]}" rev-parse HEAD^^{tree}) == "$EXPECTED_PARENT_TREE" ]] || exit 4
[[ $(sha256 "$ROOTFS_TAR") == "$EXPECTED_ROOTFS" && $(sha256 "$REQUESTS") == "$EXPECTED_REQUESTS" && $(sha256 "$RUNNER") == "$EXPECTED_RUNNER" ]] || exit 4
[[ $(flat_manifest "$MODEL") == "$EXPECTED_MODEL" && $(flat_manifest "$ADAPTER") == "$EXPECTED_ADAPTER" ]] || exit 4
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]] || exit 4
[[ -d $SNAPSHOT && ! -L $SNAPSHOT && $(findmnt -n -o FSTYPE --target "$SNAPSHOT") == ext4 ]] || exit 4
WORK="$(mktemp -d /tmp/editor-targeted-r3-eval.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"; child=""
cleanup() { [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOTFS" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$ADAPTER" "$REQUESTS" "$OUTPUT" "$RUNNER" "$CANDIDATE" "$SNAPSHOT" "$EXPECTED_MODEL" "$EXPECTED_ADAPTER" "$EXPECTED_REQUESTS" "$EXPECTED_RUNNER" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"
mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"
mount -t proc proc "$2/proc"; mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mount --bind "$9" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/adapter" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
mount --bind "$4" "$2/tmp/input/adapter"; mount -o remount,bind,ro "$2/tmp/input/adapter"
for pair in "$5:requests.jsonl" "$7:runner.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$6" "$2/tmp/output"
[[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]] || exit 5
env -i CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 EVALUATION_EXECUTION_AUTHORIZED=1 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib MODEL_SHA256="${10}" ADAPTER_SHA256="${11}" REQUESTS_SHA256="${12}" RUNNER_SHA256="${13}" /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/runner.py /tmp/input/model /tmp/input/adapter /tmp/input/authority/requests.jsonl /tmp/output "$8"
CHILD
child=$!; wait "$child"; child=""
