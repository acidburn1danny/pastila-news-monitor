#!/usr/bin/env bash
set -euo pipefail
[[ $# == 8 && ${8:-} == --preflight-only && $(id -u) == 0 ]] || exit 2
REPO=/mnt/c/pf9; ROOTFS_TAR="$(realpath -e -- "$1")"; MODEL="$(realpath -e -- "$2")"; CORPUS="$(realpath -e -- "$3")"; CHALLENGER="$(realpath -e -- "$4")"; OUTPUT="$(realpath -e -- "$5")"; PREFLIGHT="$(realpath -e -- "$6")"; WORKER="$(realpath -e -- "$7")"
EXPECTED_COMMIT=67946ad7375d7631ea184b974667e08de6db3292
EXPECTED_TREE=20eec3317677ccbab4efdf0b6a936a61c3aedf6e
EXPECTED_CHALLENGER=a6c90d629cea87d6f16b122199e3c319ad4d1a78ae6b25855d5bce8aa3020a3e
EXPECTED_CORPUS=56c3e13cf79f24882c09b4b73403fa05c1ba628d48c58b822b09f440d848f606
EXPECTED_ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
GIT=(git -c "safe.directory=$REPO" -C "$REPO")
[[ $("${GIT[@]}" rev-parse "$EXPECTED_COMMIT^{tree}") == "$EXPECTED_TREE" ]]
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD
"${GIT[@]}" merge-base --is-ancestor "$EXPECTED_COMMIT" '@{upstream}'
[[ $(sha256sum "$CHALLENGER"|cut -d' ' -f1) == "$EXPECTED_CHALLENGER" && $(sha256sum "$CORPUS"|cut -d' ' -f1) == "$EXPECTED_CORPUS" && $(sha256sum "$ROOTFS_TAR"|cut -d' ' -f1) == "$EXPECTED_ROOTFS" ]]
[[ $(findmnt -n -o FSTYPE --target "$OUTPUT") == ext4 && ! -L $OUTPUT && -z $(find "$OUTPUT" -mindepth 1 -print -quit) ]]
WORK="$(mktemp -d /tmp/editor-causal-runtime.XXXXXXXX)"; ROOT="$WORK/root"; mkdir "$ROOT"; child=""
cleanup(){ [[ -n $child ]] && kill -KILL -- "-$child" 2>/dev/null || true; umount -R "$ROOT" 2>/dev/null || true; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
setsid unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork bash -s -- "$ROOTFS_TAR" "$ROOT" "$MODEL" "$CORPUS" "$CHALLENGER" "$OUTPUT" "$PREFLIGHT" "$WORKER" <<'CHILD' &
set -euo pipefail
tar -xf "$1" -C "$2"; mount --bind "$2" "$2"; mount -o remount,bind,ro "$2"; mount -t proc proc "$2/proc"
mount --rbind /dev "$2/dev"; mount --make-rslave "$2/dev"; mount --rbind /sys "$2/sys"; mount --make-rslave "$2/sys"; mount -t tmpfs -o size=256m,mode=1777 tmpfs "$2/tmp"
mkdir -p "$2/tmp/input/model" "$2/tmp/input/authority" "$2/tmp/output"; mount --bind "$3" "$2/tmp/input/model"; mount -o remount,bind,ro "$2/tmp/input/model"
for pair in "$4:corpus.jsonl" "$5:challenger.jsonl" "$7:preflight.py" "$8:worker.py"; do src="${pair%%:*}"; name="${pair#*:}"; touch "$2/tmp/input/authority/$name"; mount --bind "$src" "$2/tmp/input/authority/$name"; mount -o remount,bind,ro "$2/tmp/input/authority/$name"; done
mount --bind "$6" "$2/tmp/output"; [[ $(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -) == lo ]]
env -i HF_HUB_OFFLINE=1 PATH=/usr/bin:/bin PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 PYTHONPATH=/tmp/input/authority /usr/sbin/chroot "$2" /opt/production-core-runtime/bin/python -B /tmp/input/authority/preflight.py --model /tmp/input/model --corpus /tmp/input/authority/corpus.jsonl --challenger /tmp/input/authority/challenger.jsonl --output /tmp/output
CHILD
child=$!; wait "$child"; child=""
