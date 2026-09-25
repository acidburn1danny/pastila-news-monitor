#!/usr/bin/env bash
set -euo pipefail
[[ $# == 15 && ${15:-} == --execute-authorized && $(id -u) == 0 ]] || exit 2
[[ ${EDITOR_CAUSAL_DIAGNOSTIC_OWNER_AUTHORIZED:-0} == 1 ]] || exit 3
ROOTFS="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; CHECKPOINT="$(realpath -e -- "$3")"; PARENT="$(realpath -e -- "$CHECKPOINT/adapter")"; CORPUS="$(realpath -e -- "$4")"; SIGNAL="$(realpath -e -- "$5")"; DEVELOPMENT="$(realpath -e -- "$6")"; OUTPUT="$(realpath -e -- "$7")"; WORKER="$(realpath -e -- "$8")"; VERIFIER="$(realpath -e -- "$9")"; ARM="${10}"; SEED="${11}"; PREFLIGHT_ROUTE="$(realpath -e -- "${12}")"; PREFLIGHT="$(realpath -e -- "${13}")"; CHALLENGER="$(realpath -e -- "${14}")"
REPO=/mnt/c/pf9; SNAPSHOT=/root/pf9-v15-wsl-drivers-snapshot
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_MODEL=f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39
EXPECTED_PARENT=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02
EXPECTED_CHECKPOINT=96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be
EXPECTED_CORPUS=56c3e13cf79f24882c09b4b73403fa05c1ba628d48c58b822b09f440d848f606
EXPECTED_DEVELOPMENT=436adcaf59392c852965501a1b1ed8068c991619e8f3de9e2cd92047f80ae51f
EXPECTED_T0_SIGNAL=3b79faf08d33a555e706b2e8f21d667cdff4891cb72ec60abe5599223e0f5181
EXPECTED_T1_SIGNAL=a6c90d629cea87d6f16b122199e3c319ad4d1a78ae6b25855d5bce8aa3020a3e
flat_manifest(){ { while IFS= read -r -d '' p; do n="${p##*/}"; z="$(stat -Lc %s -- "$p")"; h="$(sha256sum -- "$p"|cut -d' ' -f1)"; printf '%s\0' "$n"; printf '%016x' "$z"|xxd -r -p; printf '%s' "$h"|xxd -r -p; done < <(find "$1" -mindepth 1 -maxdepth 1 -type f -print0|sort -z); }|sha256sum|cut -d' ' -f1; }
PYTHONPATH="$REPO/scripts" python3 -B "$VERIFIER" --arm "$ARM" --seed "$SEED" >/dev/null
[[ $(sha256sum "$ROOTFS"|cut -d' ' -f1) == "$EXPECTED_ROOTFS" && $(flat_manifest "$MODEL") == "$EXPECTED_MODEL" && $(flat_manifest "$PARENT") == "$EXPECTED_PARENT" && $(sha256sum "$CORPUS"|cut -d' ' -f1) == "$EXPECTED_CORPUS" && $(sha256sum "$DEVELOPMENT"|cut -d' ' -f1) == "$EXPECTED_DEVELOPMENT" ]]
if [[ $ARM == T0_* ]]; then EXPECTED_SIGNAL=$EXPECTED_T0_SIGNAL; else EXPECTED_SIGNAL=$EXPECTED_T1_SIGNAL; fi
[[ $(sha256sum "$SIGNAL"|cut -d' ' -f1) == "$EXPECTED_SIGNAL" ]]
python3 -B -c 'import hashlib,json,sys; p=json.load(open(sys.argv[1],"rb")); got=p.pop("checkpoint_identity",None); raw=json.dumps(p,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode(); assert got==sys.argv[2]==hashlib.sha256(raw).hexdigest() and p["optimizer_steps"]==9' "$CHECKPOINT/checkpoint.json" "$EXPECTED_CHECKPOINT"
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
