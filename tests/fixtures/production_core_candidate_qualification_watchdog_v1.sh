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
[[ "$(cat "/proc/$$/fd/$snapshot_fd")" == first ]]
