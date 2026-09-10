#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
[[ $# -eq 2 && ( "$2" == file || "$2" == flat-dir ) && ! -L "$1" ]] || exit 2
resolved="$(realpath -e -- "$1")"
physical="$(printf '%s|' "$resolved"; stat -Lc '%d:%i' -- "$resolved")"
if [[ "$2" == file ]]; then
  [[ -f "$resolved" ]] || exit 3
  content="$(sha256sum -- "$resolved" | cut -d' ' -f1)"
else
  [[ -d "$resolved" && -z "$(find "$resolved" -mindepth 1 -maxdepth 1 \( -type l -o ! -type f \) -print -quit)" ]] || exit 3
  content="$({ while IFS= read -r -d '' path; do name="${path##*/}"; size="$(stat -Lc %s -- "$path")"; digest="$(sha256sum -- "$path" | cut -d' ' -f1)"; printf '%s\0' "$name"; printf '%016x' "$size" | xxd -r -p; printf '%s' "$digest" | xxd -r -p; done < <(find "$resolved" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z); } | sha256sum | cut -d' ' -f1)"
fi
printf '{"physical_identity":"%s","content_identity":"%s"}' "$physical" "$content"
