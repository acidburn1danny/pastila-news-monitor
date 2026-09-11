#!/usr/bin/env bash
set -euo pipefail
readonly ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
if [[ $# -ne 12 ]]; then echo "usage: launcher ROOTFS_TAR MODEL ADAPTER PROMPT BATCH OUTPUT CANDIDATE GENERATION_ID BATCH_SHA PROMPT_SHA RUNNER_SHA RUNNER" >&2; exit 2; fi
[[ "$(id -u)" == 0 ]] || { echo "root required" >&2; exit 3; }
for ordinal in 1 2 3 4 5 6; do [[ ! -L "${!ordinal}" ]] || exit 3; done
readonly ROOTFS_TAR="$(realpath -e -- "$1")" MODEL="$(realpath -e -- "$2")" ADAPTER="$(realpath -e -- "$3")"
readonly PROMPT="$(realpath -e -- "$4")" BATCH="$(realpath -e -- "$5")" OUTPUT="$(realpath -e -- "$6")"
readonly CANDIDATE="$7" GENERATION_ID="$8"
readonly EXPECTED_BATCH_SHA256="$9" EXPECTED_PROMPT_SHA256="${10}" EXPECTED_RUNNER_SHA256="${11}" RUNNER_INPUT="${12}"
[[ ! -L "$RUNNER_INPUT" && -f "$RUNNER_INPUT" ]] || exit 3
readonly RUNNER="$(realpath -e -- "$RUNNER_INPUT")"
case "$CANDIDATE" in pastila-editor-core-v1.1-json-successor-v2|pastila-editor-core-v1.2-json-successor) ;; *) exit 3;; esac
[[ -f "$ROOTFS_TAR" && -d "$MODEL" && -d "$ADAPTER" && -f "$PROMPT" && -f "$BATCH" && -d "$OUTPUT" ]] || exit 3
[[ -z "$(find "$OUTPUT" -mindepth 1 -print -quit)" && "$GENERATION_ID" =~ ^[0-9a-f]{64}$ && "$EXPECTED_BATCH_SHA256" =~ ^[0-9a-f]{64}$ && "$EXPECTED_PROMPT_SHA256" =~ ^[0-9a-f]{64}$ && "$EXPECTED_RUNNER_SHA256" =~ ^[0-9a-f]{64}$ ]] || exit 3
[[ -f "$RUNNER" && ! -L "$RUNNER" ]] || exit 3
readonly RUNNER_SHA256="$(sha256sum "$RUNNER" | cut -d' ' -f1)"
[[ "$RUNNER_SHA256" == "$EXPECTED_RUNNER_SHA256" ]] || exit 3
readonly PARENT_NETNS="$(readlink /proc/self/ns/net)" PARENT_PIDNS="$(readlink /proc/self/ns/pid)"
unshare --mount --net --pid --ipc --uts --fork bash -s -- \
  "$ROOTFS_TAR" "$MODEL" "$ADAPTER" "$PROMPT" "$BATCH" "$OUTPUT" "$RUNNER" \
  "$CANDIDATE" "$GENERATION_ID" "$EXPECTED_BATCH_SHA256" "$EXPECTED_PROMPT_SHA256" "$EXPECTED_RUNNER_SHA256" "$PARENT_NETNS" "$PARENT_PIDNS" <<'CHILD'
set -euo pipefail
ROOTFS_TAR="$1"; MODEL="$2"; ADAPTER="$3"; PROMPT="$4"; BATCH="$5"; OUTPUT="$6"
RUNNER="$7"; CANDIDATE="$8"; GENERATION_ID="$9"; BATCH_SHA256="${10}"; PROMPT_SHA256="${11}"; RUNNER_SHA256="${12}"
PARENT_NETNS="${13}"; PARENT_PIDNS="${14}"
ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
WORK="$(mktemp -d /tmp/pcq-rootfs.XXXXXXXX)"; ROOTFS="$WORK/rootfs"; mkdir "$ROOTFS"
mounted=()
cleanup() { local i; for ((i=${#mounted[@]}-1; i>=0; i--)); do umount -l -- "${mounted[$i]}" 2>/dev/null || true; done; rm -rf -- "$WORK"; }
trap cleanup EXIT INT TERM
snapshot_heartbeat() {
  local source="$1" heartbeat_fd
  exec {heartbeat_fd}<"$source" || return 1
  if ! heartbeat_snapshot_b64="$(base64 -w0 "/proc/self/fd/$heartbeat_fd")"; then exec {heartbeat_fd}<&-; return 1; fi
  exec {heartbeat_fd}<&-
  [[ "$heartbeat_snapshot_b64" =~ ^[A-Za-z0-9+/]*={0,2}$ ]]
}
[[ "$$" == 1 && "$(readlink /proc/self/ns/net)" != "$PARENT_NETNS" && "$(readlink /proc/self/ns/pid)" != "$PARENT_PIDNS" ]] || exit 4
exec {rootfs_fd}<"$ROOTFS_TAR"
[[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d' ' -f1)" == "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4" ]] || exit 4
tar -xf "/proc/self/fd/$rootfs_fd" -C "$ROOTFS"
[[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d' ' -f1)" == "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4" ]] || exit 4
[[ -z "$(find "$MODEL" "$ADAPTER" -type l -print -quit)" ]] || exit 4
MODEL_SNAPSHOT="$WORK/model-snapshot"; ADAPTER_SNAPSHOT="$WORK/adapter-snapshot"
cp -a --reflink=auto -- "$MODEL" "$MODEL_SNAPSHOT"
cp -a --reflink=auto -- "$ADAPTER" "$ADAPTER_SNAPSHOT"
exec {prompt_fd}<"$PROMPT"; exec {batch_fd}<"$BATCH"; exec {runner_fd}<"$RUNNER"
[[ "$(sha256sum "/proc/self/fd/$prompt_fd" | cut -d' ' -f1)" == "$PROMPT_SHA256" ]] || exit 4
[[ "$(sha256sum "/proc/self/fd/$batch_fd" | cut -d' ' -f1)" == "$BATCH_SHA256" ]] || exit 4
[[ "$(sha256sum "/proc/self/fd/$runner_fd" | cut -d' ' -f1)" == "$RUNNER_SHA256" ]] || exit 4
PROMPT_SNAPSHOT="$WORK/prompt.txt"; BATCH_SNAPSHOT="$WORK/batch.json"; RUNNER_SNAPSHOT="$WORK/runner.py"
cat "/proc/self/fd/$prompt_fd" > "$PROMPT_SNAPSHOT"; cat "/proc/self/fd/$batch_fd" > "$BATCH_SNAPSHOT"; cat "/proc/self/fd/$runner_fd" > "$RUNNER_SNAPSHOT"
mount -t proc proc "$ROOTFS/proc"; mounted+=("$ROOTFS/proc")
for name in dev sys; do mount --rbind "/$name" "$ROOTFS/$name"; mounted+=("$ROOTFS/$name"); mount --make-rslave "$ROOTFS/$name"; done
mount -t tmpfs -o size=64m,mode=1777 tmpfs "$ROOTFS/tmp"; mounted+=("$ROOTFS/tmp")
mkdir -p "$ROOTFS/tmp/input/model" "$ROOTFS/tmp/input/adapter" "$ROOTFS/tmp/input/authority" "$ROOTFS/tmp/output"
for target in prompt.txt batch.json runner.py; do
  install -m 000 /dev/null "$ROOTFS/tmp/input/authority/$target"
done
for source_target in "$MODEL_SNAPSHOT|$ROOTFS/tmp/input/model" "$ADAPTER_SNAPSHOT|$ROOTFS/tmp/input/adapter"; do source="${source_target%%|*}"; target="${source_target#*|}"; mount --bind "$source" "$target"; mounted+=("$target"); mount -o remount,bind,ro "$target"; done
for source_target in "$PROMPT_SNAPSHOT|$ROOTFS/tmp/input/authority/prompt.txt" "$BATCH_SNAPSHOT|$ROOTFS/tmp/input/authority/batch.json" "$RUNNER_SNAPSHOT|$ROOTFS/tmp/input/authority/runner.py"; do source="${source_target%%|*}"; target="${source_target#*|}"; mount --bind "$source" "$target"; mounted+=("$target"); mount -o remount,bind,ro "$target"; done
mount --bind "$OUTPUT" "$ROOTFS/tmp/output"; mounted+=("$ROOTFS/tmp/output")
interfaces="$(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -)"
route_rows="$(awk 'NR>1 {n++} END {print n+0}' /proc/net/route)"
[[ "$interfaces" == "lo" && "$route_rows" == 0 ]] || { echo "network isolation probe failed" >&2; exit 5; }
model_opts="$(findmnt -no OPTIONS --target "$ROOTFS/tmp/input/model")"; adapter_opts="$(findmnt -no OPTIONS --target "$ROOTFS/tmp/input/adapter")"
[[ ",$model_opts," == *,ro,* && ",$adapter_opts," == *,ro,* ]] || { echo "read-only mount probe failed" >&2; exit 5; }
mount_sha="$(sha256sum /proc/self/mountinfo | cut -d' ' -f1)"
printf '{"schema":"pastila-production-core-network-boundary-log","schema_version":1,"policy":"DENY_ALL_NEW_CHILD_NAMESPACE","observed_interfaces":["lo"],"observed_ipv4_route_rows":0,"namespace_init_pid":1,"network_namespace_differs_from_parent":true,"pid_namespace_differs_from_parent":true,"promotion_effect":false}' > "$OUTPUT/network-boundary.json"
printf '{"schema":"pastila-production-core-file-boundary-log","schema_version":1,"model_mount_read_only":true,"adapter_mount_read_only":true,"candidate_private_snapshots":true,"authority_inputs_from_open_descriptors":true,"private_rootfs_from_open_descriptor":true,"mountinfo_sha256":"%s","host_pid_namespace_reachable":false}' "$mount_sha" > "$OUTPUT/file-boundary.json"
env -i BATCH_SHA256="$BATCH_SHA256" PROMPT_SHA256="$PROMPT_SHA256" CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false TRANSFORMERS_OFFLINE=1 TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib TRITON_CACHE_DIR=/tmp/triton-cache QUALIFICATION_GENERATION_IDENTITY="$GENERATION_ID" ROOTFS_SHA256="$ROOTFS_SHA256" RUNNER_SHA256="$RUNNER_SHA256" /usr/sbin/chroot "$ROOTFS" /opt/production-core-runtime/bin/python -I /tmp/input/authority/runner.py /tmp/input/model /tmp/input/adapter /tmp/input/authority/prompt.txt /tmp/input/authority/batch.json "$CANDIDATE" &
runner_pid=$!; timed_out=false; invalid_heartbeat=false; last_heartbeat_identity=""; generation_allowance=600000000000; last_sequence=-1; last_completed=0; last_stage=INIT
read -r initial_uptime _ </proc/uptime; initial_whole="${initial_uptime%%.*}"; initial_frac="${initial_uptime#*.}000000000"; initial_now=$((10#$initial_whole * 1000000000 + 10#${initial_frac:0:9})); supervisor_deadline=$((initial_now + 600000000000))
while kill -0 "$runner_pid" 2>/dev/null; do
  read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9}))
  if snapshot_heartbeat "$OUTPUT/heartbeat.json"; then
    heartbeat_identity="$(printf %s "$heartbeat_snapshot_b64" | sha256sum | cut -d' ' -f1)"
    if [[ "$heartbeat_identity" != "$last_heartbeat_identity" ]]; then
      heartbeat_json="$(printf %s "$heartbeat_snapshot_b64" | base64 -d)"
      stage="$(sed -n 's/^{"stage":"\([A-Z_]*\)".*/\1/p' <<<"$heartbeat_json")"
      sequence="$(sed -n 's/.*"sequence":\([0-9][0-9]*\).*/\1/p' <<<"$heartbeat_json")"
      completed="$(sed -n 's/.*"completed_count":\([0-9][0-9]*\).*/\1/p' <<<"$heartbeat_json")"
      case_id="$(sed -n 's/.*"case_id":"\([A-Za-z0-9._:-]*\)".*/\1/p' <<<"$heartbeat_json")"
      observed="$(sed -n 's/.*"deadline_boottime_ns":\([0-9][0-9]*\)}$/\1/p' <<<"$heartbeat_json")"
      if [[ ! "$sequence" =~ ^[0-9]+$ || ! "$completed" =~ ^[0-9]+$ || ! "$observed" =~ ^[0-9]+$ ]] || (( observed < now || observed > now + 600000000000 )); then invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; fi
      case "$stage" in
        LOAD) [[ "$sequence" == 0 && "$completed" == 0 && -z "$case_id" ]] || { invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; }; expected="{\"stage\":\"LOAD\",\"sequence\":0,\"completed_count\":0,\"deadline_boottime_ns\":$observed}" ;;
        GENERATE)
          [[ -n "$case_id" && $sequence -ge 1 && $sequence -le 200 && $completed -eq $((sequence - 1)) ]] || { invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; }
          expected="{\"stage\":\"GENERATE\",\"sequence\":$sequence,\"completed_count\":$completed,\"case_id\":\"$case_id\",\"deadline_boottime_ns\":$observed}"
          if (( generation_allowance == 600000000000 )); then elapsed=$((now - initial_now)); (( elapsed < 600000000000 )) || { timed_out=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; }; generation_allowance=$((600000000000 - elapsed)); fi
          supervisor_deadline=$((now + generation_allowance)) ;;
        CASE_COMPLETE) [[ -n "$case_id" && $sequence -ge 1 && $sequence -le 200 && $completed -eq $sequence ]] || { invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; }; expected="{\"stage\":\"CASE_COMPLETE\",\"sequence\":$sequence,\"completed_count\":$completed,\"case_id\":\"$case_id\",\"deadline_boottime_ns\":$observed}" ;;
        BATCH_COMPLETE) [[ "$sequence" == 201 && "$completed" == 200 && -z "$case_id" ]] || { invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; }; expected="{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$observed}" ;;
        *) invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break ;;
      esac
      if ! cmp -s <(printf %s "$heartbeat_snapshot_b64" | base64 -d) <(printf %s "$expected") || (( sequence < last_sequence || completed < last_completed )) || { (( sequence == last_sequence )) && [[ "$last_stage" != GENERATE || "$stage" != CASE_COMPLETE ]]; }; then invalid_heartbeat=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; fi
      last_sequence=$sequence; last_completed=$completed; last_stage="$stage"
      last_heartbeat_identity="$heartbeat_identity"
    fi
  fi
  if (( now > supervisor_deadline )); then timed_out=true; kill -KILL "$runner_pid" 2>/dev/null || true; break; fi
  sleep 1
done
set +e; wait "$runner_pid"; status=$?; set -e
if [[ "$invalid_heartbeat" == true ]]; then printf '{"schema":"pastila-production-core-supervisor-failure","schema_version":2,"code":"INVALID_HEARTBEAT_AUTHORITY","ceiling_ns":600000000000,"watchdog_exit_code":125,"last_sequence":%s,"last_completed_count":%s,"last_stage":"%s"}' "$last_sequence" "$last_completed" "$last_stage" > "$OUTPUT/supervisor-failure.json"; exit 125; fi
if [[ "$timed_out" == true ]]; then printf '{"schema":"pastila-production-core-supervisor-failure","schema_version":2,"code":"INFERENCE_WALL_TIME_EXCEEDED","ceiling_ns":600000000000,"watchdog_exit_code":124,"last_sequence":%s,"last_completed_count":%s,"last_stage":"%s"}' "$last_sequence" "$last_completed" "$last_stage" > "$OUTPUT/supervisor-failure.json"; exit 124; fi
[[ "$status" -eq 0 ]] || exit "$status"
snapshot_heartbeat "$OUTPUT/heartbeat.json" || { printf '{"schema":"pastila-production-core-supervisor-failure","schema_version":2,"code":"INVALID_FINAL_HEARTBEAT_AUTHORITY","ceiling_ns":600000000000,"watchdog_exit_code":125,"last_sequence":%s,"last_completed_count":%s,"last_stage":"%s"}' "$last_sequence" "$last_completed" "$last_stage" > "$OUTPUT/supervisor-failure.json"; exit 125; }
final_heartbeat="$(printf %s "$heartbeat_snapshot_b64" | base64 -d)"
final_observed="$(sed -n 's/.*"deadline_boottime_ns":\([0-9][0-9]*\)}$/\1/p' <<<"$final_heartbeat")"
read -r final_uptime _ </proc/uptime; final_whole="${final_uptime%%.*}"; final_frac="${final_uptime#*.}000000000"; final_now=$((10#$final_whole * 1000000000 + 10#${final_frac:0:9}))
final_expected="{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$final_observed}"
if [[ ! "$final_observed" =~ ^[0-9]+$ ]] || ! cmp -s <(printf %s "$heartbeat_snapshot_b64" | base64 -d) <(printf %s "$final_expected") || (( final_observed < final_now || final_observed > final_now + 600000000000 || 201 < last_sequence || 200 < last_completed )); then printf '{"schema":"pastila-production-core-supervisor-failure","schema_version":2,"code":"INVALID_FINAL_HEARTBEAT_AUTHORITY","ceiling_ns":600000000000,"watchdog_exit_code":125,"last_sequence":%s,"last_completed_count":%s,"last_stage":"%s"}' "$last_sequence" "$last_completed" "$last_stage" > "$OUTPUT/supervisor-failure.json"; exit 125; fi
sync -f "$OUTPUT"
CHILD
