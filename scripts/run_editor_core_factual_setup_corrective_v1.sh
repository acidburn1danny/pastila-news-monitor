#!/usr/bin/env bash
set -euo pipefail
[[ $# == 8 && ${8:-} == --execute-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_FACTUAL_SETUP_CORRECTIVE_V1_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; PARENT_CHECKPOINT="$(realpath -e -- "$3")"
PARENT="$(realpath -e -- "$PARENT_CHECKPOINT/adapter")"; CORPUS="$(realpath -e -- "$4")"; CONFIG="$(realpath -e -- "$5")"
OUTPUT="$(realpath -e -- "$6")"; WORKER="$(realpath -e -- "$7")"
REPOSITORY=/mnt/c/pf9
MANIFEST=$REPOSITORY/docs/artifacts/editor-core-factual-setup-corrective-v1-manifest.json
ZERO_STEP=$REPOSITORY/scripts/launch_editor_core_factual_setup_corrective_v1_zero_step.py
SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
EXPECTED_SOURCE_COMMIT=5a5537ff9eb076a289b8fde6b306c38c11085899
EXPECTED_SOURCE_TREE=dff0bcc0af869726ec70b528d5b7f96116e4d7ea
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_MODEL=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
EXPECTED_PARENT=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02
EXPECTED_CHECKPOINT=96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be
EXPECTED_MANIFEST_IDENTITY=50b387a0025025f5daac68cd65ab5570a731f9bb0db2a82c023921829e806a88
EXPECTED_CONFIG_IDENTITY=2b813d0485a3d3e186e4b5a4c88139af83d8d54fb25e759cee0921ee94da230b
EXPECTED_CORPUS=56c3e13cf79f24882c09b4b73403fa05c1ba628d48c58b822b09f440d848f606
EXPECTED_CONFIG_FILE=49e03990128dd97c746df5a9158796b60a4863d22e41ca7c50b0daae6ac507b4
EXPECTED_MANIFEST_FILE=6543deed5641f1f10de6acc00d18dc5d8541ad39996701f9e4241e2fc6f24e40
EXPECTED_ZERO_STEP=04323716cb5b7ea1caaf973098ff246183520081d39a4bf88dc52990fc1a4f15
EXPECTED_WORKER=16d5f6bdaae5126d8953c9529423f9dd30d55a48d3e8e6a43c1337971fc77004
sha256() { sha256sum -- "$1" | cut -d' ' -f1; }
flat_manifest() { { while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256 "$path")"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1; }
json_identity() { python3 -B -c 'import hashlib,json,sys; v=json.load(open(sys.argv[1],"rb")); key=sys.argv[2]; expected=sys.argv[3]; got=v.pop(key,None); raw=json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode(); assert got==expected==hashlib.sha256(raw).hexdigest()' "$1" "$2" "$3"; }
checkpoint_identity() { python3 -B -c 'import hashlib,json,sys; v=json.load(open(sys.argv[1],"rb")); got=v.pop("checkpoint_identity",None); raw=json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode(); assert got==sys.argv[2]==hashlib.sha256(raw).hexdigest() and v.get("optimizer_steps")==9' "$1" "$EXPECTED_CHECKPOINT"; }
GIT=(git -c "safe.directory=$REPOSITORY" -C "$REPOSITORY")
[[ $("${GIT[@]}" rev-parse "$EXPECTED_SOURCE_COMMIT^{tree}") == "$EXPECTED_SOURCE_TREE" ]] || exit 4
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_SOURCE_COMMIT" HEAD || exit 4
[[ $("${GIT[@]}" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}') == origin/successor/core-v2-v12-runner-binding-remediation ]] || exit 4
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_SOURCE_COMMIT" '@{upstream}' || exit 4
[[ $(sha256 "$CORPUS") == "$EXPECTED_CORPUS" && $(sha256 "$CONFIG") == "$EXPECTED_CONFIG_FILE" && $(sha256 "$MANIFEST") == "$EXPECTED_MANIFEST_FILE" ]] || exit 4
[[ $(sha256 "$ZERO_STEP") == "$EXPECTED_ZERO_STEP" && $(sha256 "$WORKER") == "$EXPECTED_WORKER" && $(sha256 "$ROOTFS_TAR") == "$EXPECTED_ROOTFS" ]] || exit 4
json_identity "$CONFIG" config_identity "$EXPECTED_CONFIG_IDENTITY"; json_identity "$MANIFEST" manifest_identity "$EXPECTED_MANIFEST_IDENTITY"
[[ $(flat_manifest "$MODEL") == "$EXPECTED_MODEL" && $(flat_manifest "$PARENT") == "$EXPECTED_PARENT" ]] || exit 4
checkpoint_identity "$PARENT_CHECKPOINT/checkpoint.json"
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]] || exit 4
python3 -B "$ZERO_STEP" --parent-checkpoint "$PARENT_CHECKPOINT" --output "$OUTPUT" >/dev/null
WORK="$(mktemp -d /tmp/editor-factual-corrective-v1.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"; child=""
cleanup() { [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOTFS" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOTFS" "$MODEL" "$PARENT" "$CORPUS" "$CONFIG" "$OUTPUT" "$WORKER" "$SNAPSHOT" "$EXPECTED_MODEL" "$EXPECTED_PARENT" "$EXPECTED_CORPUS" "$EXPECTED_CONFIG_IDENTITY" "$EXPECTED_MANIFEST_IDENTITY" "$EXPECTED_ROOTFS" "$EXPECTED_WORKER" "$(sha256 "$0")" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"
mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"; mount --bind "$9" "$2/usr/lib/wsl/drivers"; mount -o remount,bind,ro "$2/usr/lib/wsl/drivers"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/parent" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"; mount --bind "$4" "$2/tmp/input/parent"; mount -o remount,bind,ro "$2/tmp/input/parent"
for pair in "$5:corpus.jsonl" "$6:config.json" "$8:worker.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$7" "$2/tmp/output"; [[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]] || exit 5
env -i CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_CACHE_DIR=/tmp/triton-cache TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib TRAINING_EXECUTION_AUTHORIZED=1 MODEL_SHA256="${10}" PARENT_SHA256="${11}" CORPUS_SHA256="${12}" CONFIG_IDENTITY="${13}" MANIFEST_IDENTITY="${14}" ROOTFS_SHA256="${15}" WORKER_SHA256="${16}" LAUNCHER_SHA256="${17}" /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -I -B /tmp/input/authority/worker.py /tmp/input/model /tmp/input/parent /tmp/input/authority/corpus.jsonl /tmp/input/authority/config.json /tmp/output
CHILD
child=$!; wait "$child"; child=""
