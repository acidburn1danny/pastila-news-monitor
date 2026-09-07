#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
heartbeat="$work/heartbeat.json"; read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9}))
(printf '{"deadline_boottime_ns":%s}' "$((now + 100000000))" > "$heartbeat"; sleep 30) & child=$!
timed_out=false
while kill -0 "$child" 2>/dev/null; do
  deadline="$(sed -n 's/.*"deadline_boottime_ns":\([0-9][0-9]*\).*/\1/p' "$heartbeat")"; read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9}))
  if (( now > deadline )); then timed_out=true; kill -KILL "$child" 2>/dev/null || true; break; fi
  sleep 0.02
done
set +e; wait "$child" 2>/dev/null; status=$?; set -e
[[ "$timed_out" == true && "$status" -ne 0 ]]
# A child that never publishes a heartbeat is bounded by the supervisor's own deadline.
(sleep 30) & child=$!; read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9})); deadline=$((now + 100000000)); timed_out=false
while kill -0 "$child" 2>/dev/null; do read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9})); if (( now > deadline )); then timed_out=true; kill -KILL "$child" 2>/dev/null || true; break; fi; sleep 0.02; done
set +e; wait "$child" 2>/dev/null; status=$?; set -e; [[ "$timed_out" == true && "$status" -ne 0 ]]
# A child heartbeat is observation, never authority to extend the supervisor ceiling.
(sleep 30) & child=$!; read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9})); supervisor_deadline=$((now + 100000000)); printf '{"stage":"GENERATE","deadline_boottime_ns":%s}' "$((now + 700000000000))" > "$heartbeat"; invalid_heartbeat=false
while kill -0 "$child" 2>/dev/null; do read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}000000000"; now=$((10#$whole * 1000000000 + 10#${frac:0:9})); observed="$(sed -n 's/.*"deadline_boottime_ns":\([0-9][0-9]*\).*/\1/p' "$heartbeat")"; if [[ ! "$observed" =~ ^[0-9]+$ ]] || (( observed < now || observed > now + 600000000000 )); then invalid_heartbeat=true; kill -KILL "$child" 2>/dev/null || true; break; fi; if (( now > supervisor_deadline )); then kill -KILL "$child" 2>/dev/null || true; break; fi; sleep 0.02; done
set +e; wait "$child" 2>/dev/null; status=$?; set -e; [[ "$invalid_heartbeat" == true && "$status" -ne 0 ]]
printf first > "$work/a"; printf second > "$work/b"; ln -s "$work/a" "$work/current"
exec {snapshot_fd}<"$work/current"; ln -sfn "$work/b" "$work/current"
[[ "$(cat "/proc/self/fd/$snapshot_fd")" == first ]]

# Polling may legitimately miss CASE_COMPLETE; monotonic counters retain proof.
valid_progress() {
  local previous_sequence="$1" previous_completed="$2" previous_stage="$3" sequence="$4" completed="$5" stage="$6"
  (( sequence >= previous_sequence && completed >= previous_completed )) || return 1
  if (( sequence == previous_sequence )); then
    [[ "$previous_stage" == GENERATE && "$stage" == CASE_COMPLETE ]] || return 1
  fi
  case "$stage" in
    GENERATE) (( sequence >= 1 && sequence <= 200 && completed == sequence - 1 )) ;;
    CASE_COMPLETE) (( sequence >= 1 && sequence <= 200 && completed == sequence )) ;;
    BATCH_COMPLETE) (( sequence == 201 && completed == 200 )) ;;
    *) return 1 ;;
  esac
}
valid_progress 1 0 GENERATE 2 1 GENERATE
valid_progress 7 6 GENERATE 10 10 CASE_COMPLETE
! valid_progress 2 1 GENERATE 1 1 CASE_COMPLETE
! valid_progress 2 1 GENERATE 2 1 GENERATE
! valid_progress 2 1 GENERATE 4 1 GENERATE

valid_final() {
  local value="$1" now="$2" last_sequence="$3" last_completed="$4" observed expected
  observed="$(sed -n 's/.*"deadline_boottime_ns":\([0-9][0-9]*\)}$/\1/p' <<<"$value")"
  [[ "$observed" =~ ^[0-9]+$ ]] || return 1
  expected="{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$observed}"
  [[ "$value" == "$expected" ]] || return 1
  (( observed >= now && observed <= now + 600000000000 && 201 >= last_sequence && 200 >= last_completed ))
}
valid_final "{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$((now + 100000000))}" "$now" 200 200
! valid_final "{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$((now + 700000000000))}" "$now" 200 200
! valid_final "{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"extra\":true,\"deadline_boottime_ns\":$((now + 100000000))}" "$now" 200 200
! valid_final "{\"stage\":\"BATCH_COMPLETE\",\"sequence\":201,\"completed_count\":200,\"deadline_boottime_ns\":$((now + 100000000))}" "$now" 202 201

# Runner and supervisor parsers agree exactly on one frozen uptime sample.
uptime_sample="12345.67 890.12"
runner_sample="$(python3 -c 'import sys; u=sys.argv[1].split(maxsplit=1)[0]; w,sep,f=u.partition("."); assert sep and w.isascii() and w.isdigit(); c=(f+"00")[:2]; assert c.isascii() and c.isdigit(); print(int(w)*1_000_000_000+int(c)*10_000_000)' "$uptime_sample")"
read -r uptime _ <<<"$uptime_sample"; whole="${uptime%%.*}"; frac="${uptime#*.}00"; supervisor_sample=$((10#$whole * 1000000000 + 10#${frac:0:2} * 10000000))
[[ "$runner_sample" == "$supervisor_sample" && "$runner_sample" == 12345670000000 ]]
# Live sanity has no scheduler-latency assumption: the later read is conservative.
runner_now="$(python3 -c 'from pathlib import Path; u=Path("/proc/uptime").read_text("ascii").split(maxsplit=1)[0]; w,_,f=u.partition("."); print(int(w)*1_000_000_000+int((f+"00")[:2])*10_000_000)')"
read -r uptime _ </proc/uptime; whole="${uptime%%.*}"; frac="${uptime#*.}00"; supervisor_now=$((10#$whole * 1000000000 + 10#${frac:0:2} * 10000000))
(( runner_now % 10000000 == 0 && supervisor_now >= runner_now ))
runner_deadline=$((runner_now + 600000000000))
(( runner_deadline <= supervisor_now + 600000000000 ))
