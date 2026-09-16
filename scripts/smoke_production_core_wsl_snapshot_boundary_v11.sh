#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 2 && "$(id -u)" == 0 ]] || exit 2
for ordinal in 1 2; do [[ ! -L "${!ordinal}" ]] || exit 3; done
MODEL="$(realpath -e -- "$1")"; ADAPTER="$(realpath -e -- "$2")"
[[ -d "$MODEL" && -d "$ADAPTER" ]] || exit 3
[[ -z "$(find "$MODEL" "$ADAPTER" -type l -print -quit)" ]] || exit 3
[[ -z "$(find "$MODEL" "$ADAPTER" \( -type f -o -type d \) -perm /222 -print -quit)" ]] || exit 3
MODEL_PHYSICAL="$(stat -Lc '%d:%i' -- "$MODEL")"; ADAPTER_PHYSICAL="$(stat -Lc '%d:%i' -- "$ADAPTER")"
unshare --mount --pid --fork bash -s -- "$MODEL" "$ADAPTER" "$MODEL_PHYSICAL" "$ADAPTER_PHYSICAL" <<'CHILD'
set -euo pipefail
MODEL="$1"; ADAPTER="$2"; MODEL_PHYSICAL="$3"; ADAPTER_PHYSICAL="$4"
mount --make-rprivate /
WORK="$(mktemp -d /tmp/pcq-v11-snapshot-smoke.XXXXXXXX)"
MODEL_SNAPSHOT="$WORK/model"; ADAPTER_SNAPSHOT="$WORK/adapter"; mkdir "$MODEL_SNAPSHOT" "$ADAPTER_SNAPSHOT"
mounted=()
cleanup(){ local i; for ((i=${#mounted[@]}-1;i>=0;i--));do umount -l -- "${mounted[$i]}" 2>/dev/null||true;done;rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
for source_target in "$MODEL|$MODEL_SNAPSHOT" "$ADAPTER|$ADAPTER_SNAPSHOT"; do
 source="${source_target%%|*}"; target="${source_target#*|}"
 mount --bind "$source" "$target"; mounted+=("$target"); mount -o remount,bind,ro "$target"
done
[[ "$(stat -Lc '%d:%i' -- "$MODEL_SNAPSHOT")" == "$MODEL_PHYSICAL" ]]
[[ "$(stat -Lc '%d:%i' -- "$ADAPTER_SNAPSHOT")" == "$ADAPTER_PHYSICAL" ]]
for target in "$MODEL_SNAPSHOT" "$ADAPTER_SNAPSHOT"; do
 opts="$(findmnt -no OPTIONS --target "$target")"; [[ ",$opts," == *,ro,* ]]
 if touch "$target/.v11-write-probe" 2>/dev/null; then exit 5; fi
done
printf '{"schema":"pastila-production-core-v11-wsl-snapshot-boundary-smoke","schema_version":1,"result":"PASS","snapshot_strategy":"PRIVATE_READ_ONLY_BIND_MOUNT","model_physical_identity":"%s","adapter_physical_identity":"%s","source_writable_entries":0,"snapshot_writable":false,"qualification_rows":0,"candidate_execution":0,"attempt_consumption":0}\n' "$MODEL_PHYSICAL" "$ADAPTER_PHYSICAL"
CHILD
