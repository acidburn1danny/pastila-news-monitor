#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
printf descriptor-sentinel > "$work/source"
exec {snapshot_fd}<"$work/source"
unshare --mount --net --pid --ipc --uts --fork bash -s -- "$snapshot_fd" <<'CHILD'
set -euo pipefail
snapshot_fd="$1"
[[ "$(cat "/proc/self/fd/$snapshot_fd")" == descriptor-sentinel ]]
mount --make-rprivate /
fixture_root="$(mktemp -d)"
mkdir -p "$fixture_root/input/authority"
install -m 000 /dev/null "$fixture_root/input/authority/prompt.txt"
mount --bind "/proc/self/fd/$snapshot_fd" "$fixture_root/input/authority/prompt.txt"
[[ "$(cat "$fixture_root/input/authority/prompt.txt")" == descriptor-sentinel ]]
umount "$fixture_root/input/authority/prompt.txt"
rm -rf -- "$fixture_root"
mount -t proc proc /proc
[[ "$$" == 1 ]]
[[ "$(awk -F: 'NR>2 {gsub(/ /,"",$1); print $1}' /proc/net/dev | sort -u | paste -sd, -)" == lo ]]
[[ "$(awk 'NR>1 {n++} END {print n+0}' /proc/net/route)" == 0 ]]
python3 - <<'PY'
import socket
s = socket.socket()
s.settimeout(0.1)
try:
    s.connect(("1.1.1.1", 443))
except OSError:
    pass
else:
    raise SystemExit("network unexpectedly reachable")
finally:
    s.close()
PY
CHILD
