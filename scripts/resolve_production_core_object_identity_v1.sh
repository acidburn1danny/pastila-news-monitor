#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && ! -L "$1" ]] || exit 2
readonly resolved="$(realpath -e -- "$1")"
printf '%s|' "$resolved"
stat -Lc '%d:%i' -- "$resolved"
