#!/usr/bin/env bash
set -euo pipefail
[[ $# == 7 && ${7:-} == --preflight-only && $(id -u) == 0 ]] || exit 2
REPO=/mnt/c/pf9
ROOTFS_TAR="$(realpath -e -- "$1")"
TOKENIZER="$(realpath -e -- "$2")"
PAIRS="$(realpath -e -- "$3")"
RETENTION="$(realpath -e -- "$4")"
PREFLIGHT="$(realpath -e -- "$5")"
WORKER="$(realpath -e -- "$6")"
EXPECTED_COMMIT=eadbddf23da3408f8cfb8233823f4f8fd974519f
EXPECTED_TREE=e07eb052f78d2d634dcd4f5482fb84508f585a2d
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
EXPECTED_TOKENIZER=d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135
EXPECTED_PAIRS=a986105db31a02a6cc16dfab0821666a58f58685a83f50cead7c25bd5a536cc1
EXPECTED_RETENTION=6f3599e17010e0a7154f8f85019a9b4f55a4db897da87f4d1c35c435c15d5b7f
GIT=(git -c "safe.directory=$REPO" -C "$REPO")
[[ $("${GIT[@]}" rev-parse "$EXPECTED_COMMIT^{tree}") == "$EXPECTED_TREE" ]]
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_COMMIT" '@{upstream}'
[[ $(sha256sum "$ROOTFS_TAR"|cut -d' ' -f1) == "$EXPECTED_ROOTFS" ]]
[[ $(sha256sum "$TOKENIZER/tokenizer.json"|cut -d' ' -f1) == "$EXPECTED_TOKENIZER" ]]
[[ $(sha256sum "$PAIRS"|cut -d' ' -f1) == "$EXPECTED_PAIRS" ]]
[[ $(sha256sum "$RETENTION"|cut -d' ' -f1) == "$EXPECTED_RETENTION" ]]
WORK="$(mktemp -d /tmp/editor-anchored-runtime.XXXXXXXX)"; ROOT="$WORK/root"; OUTPUT="$WORK/output"; mkdir "$ROOT" "$OUTPUT"; child=""
cleanup(){ [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOT" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOT" "$TOKENIZER" "$PAIRS" "$RETENTION" "$PREFLIGHT" "$WORKER" "$OUTPUT" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"; mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"
mkdir -p "$2/tmp/input/tokenizer" "$2/tmp/input/authority" "$2/tmp/output"
mount --bind "$3" "$2/tmp/input/tokenizer"; mount -o remount,bind,ro "$2/tmp/input/tokenizer"
for pair in "$4:pairs.jsonl" "$5:retention.jsonl" "$6:preflight.py" "$7:editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$8" "$2/tmp/output"
[[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]]
env -i HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 PYTHONPATH=/tmp/input/authority /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -B /tmp/input/authority/preflight.py --model /tmp/input/tokenizer --pairs /tmp/input/authority/pairs.jsonl --retention /tmp/input/authority/retention.jsonl --output /tmp/output
CHILD
child=$!; wait "$child"; child=""
