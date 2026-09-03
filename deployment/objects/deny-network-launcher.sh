#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 5 || "$1" != "--launcher-sha256" || "$3" != "--expected-sha256" ]]; then
  echo "closed launcher arguments" >&2
  exit 64
fi
launcher_expected="$2"
expected="$4"
shift 4
executable="$1"
shift

[[ "$launcher_expected" =~ ^[0-9a-f]{64}$ && "$expected" =~ ^[0-9a-f]{64}$ ]] || exit 65
launcher_resolved="$(/usr/bin/realpath --canonicalize-existing "${BASH_SOURCE[0]}")"
launcher_actual="$(/usr/bin/sha256sum --binary "$launcher_resolved" | /usr/bin/cut -d' ' -f1)"
[[ "$launcher_actual" == "$launcher_expected" ]] || exit 69
[[ -f "$executable" && ! -L "$executable" ]] || exit 66
actual="$(/usr/bin/sha256sum --binary "$executable" | /usr/bin/cut -d' ' -f1)"
[[ "$actual" == "$expected" ]] || exit 67
resolved="$(/usr/bin/realpath --canonicalize-existing "$executable")"
[[ "$resolved" == "$executable" ]] || exit 68

# A new user namespace supplies CAP_SYS_ADMIN only inside the namespace; the
# paired network namespace starts with no usable interface.  The child gets a
# closed environment and cannot inherit proxy, credential, preload, or config
# channels from the caller.
exec /usr/bin/unshare --user --map-root-user --net -- \
  /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent SSL_CERT_FILE=/dev/null \
  "$executable" "$@"
