#!/usr/bin/env bash
set -euo pipefail
unshare --mount --net --pid --ipc --uts --fork bash -c '
set -euo pipefail
mount --make-rprivate /
mount -t proc proc /proc
[[ "$$" == 1 ]]
[[ "$(awk -F: '\''NR>2 {gsub(/ /,"",$1); print $1}'\'' /proc/net/dev | sort -u | paste -sd, -)" == lo ]]
[[ "$(awk '\''NR>1 {n++} END {print n+0}'\'' /proc/net/route)" == 0 ]]
python3 - <<'\''PY'\''
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
'
