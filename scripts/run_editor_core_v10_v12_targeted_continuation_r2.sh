#!/usr/bin/env bash
set -euo pipefail
[[ $# == 8 && ${8:-} == --execute-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_CORE_R2_TRAINING_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; PARENT_CHECKPOINT="$(realpath -e -- "$3")"
PARENT="$(realpath -e -- "$PARENT_CHECKPOINT/adapter")"
CORPUS="$(realpath -e -- "$4")"; CONFIG="$(realpath -e -- "$5")"; OUTPUT="$(realpath -e -- "$6")"; WORKER="$(realpath -e -- "$7")"
SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
HELPER=/mnt/c/pf9/src/pastila_scout/production_core_wsl_driver_snapshot_v15.py
ZERO_STEP=/mnt/c/pf9/scripts/launch_editor_core_v10_v12_targeted_r2_zero_step.py
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_MODEL=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
EXPECTED_PARENT=50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4
EXPECTED_CHECKPOINT=00ee968941f8cba8ea47534d441c272c7a3120f9076953aa552f67e302a0ceef
EXPECTED_CORPUS=9c99425dc9c2ce1f69f2694177b8698892a8e1cc8ed67b5e7fe910d6e56ce072
EXPECTED_CONFIG=991e84f5063b6a27cc2311af5c5bde94b91b1bc5a27738d7d6596a12e9076fc6
EXPECTED_HELPER=7026fe0ea99d54d0fc6caefd5ac4b6c1119e488b1cdc96336ce14387b7ffb433
EXPECTED_ZERO_STEP=669ceb7f22f80b75e0220d30a995f445298ba198c0c2fb469d679367a276bda2
EXPECTED_WORKER=3797a73c3257a5ea4c113c1ca2eab378355e26bf84ee852438887b0d2f2f4320
sha256() { sha256sum -- "$1" | cut -d' ' -f1; }
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256 "$path")"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
checkpoint_identity() { python3 -B -c 'import hashlib,json,sys; p=sys.argv[1]; v=json.load(open(p,"rb")); i=v.pop("checkpoint_identity",None); c=json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":" )).encode(); assert i==hashlib.sha256(c).hexdigest() and v.get("model_sha256")==sys.argv[2] and v.get("optimizer_steps")==8; print(i)' "$1" "$EXPECTED_MODEL"; }
[[ $(sha256 "$ROOTFS_TAR") == "$EXPECTED_ROOTFS" && $(sha256 "$CORPUS") == "$EXPECTED_CORPUS" && $(sha256 "$CONFIG") == "$EXPECTED_CONFIG" ]] || exit 4
[[ $(sha256 "$HELPER") == "$EXPECTED_HELPER" && $(sha256 "$ZERO_STEP") == "$EXPECTED_ZERO_STEP" && $(sha256 "$WORKER") == "$EXPECTED_WORKER" ]] || exit 4
[[ $(flat_manifest "$MODEL") == "$EXPECTED_MODEL" && $(flat_manifest "$PARENT") == "$EXPECTED_PARENT" ]] || exit 4
[[ $(checkpoint_identity "$PARENT_CHECKPOINT/checkpoint.json") == "$EXPECTED_CHECKPOINT" ]] || exit 4
python3 -B "$HELPER" --root "$SNAPSHOT" >/dev/null
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]] || exit 4
WORK="$(mktemp -d /tmp/editor-targeted-r2-train.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"; child=""
cleanup() { [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOTFS" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$PARENT" "$CORPUS" "$CONFIG" "$OUTPUT" "$WORKER" "$SNAPSHOT" "$EXPECTED_MODEL" "$EXPECTED_PARENT" "$EXPECTED_CORPUS" "$EXPECTED_CONFIG" "$EXPECTED_ROOTFS" "$EXPECTED_WORKER" "$(sha256 "$0")" <<'CHILD' &
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
for pair in "$5:corpus.jsonl" "$6:config.json" "$8:worker.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$7" "$2/tmp/output"
[[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]] || exit 5
env -i CC=/usr/bin/gcc CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib TRAINING_EXECUTION_AUTHORIZED=1 MODEL_SHA256="${10}" PARENT_SHA256="${11}" CORPUS_SHA256="${12}" CONFIG_SHA256="${13}" ROOTFS_SHA256="${14}" WORKER_SHA256="${15}" LAUNCHER_SHA256="${16}" /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/worker.py /tmp/input/model /tmp/input/parent /tmp/input/authority/corpus.jsonl /tmp/input/authority/config.json /tmp/output
CHILD
child=$!; wait "$child"; child=""
