#!/usr/bin/env bash
set -euo pipefail

readonly TOKENIZER_SHA256="2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"

if [[ ${1:-} != --inside ]]; then
  if [[ $# -ne 2 ]]; then
    exit 2
  fi
  exec unshare --mount --fork "$0" --inside "$1" "$2"
fi
if [[ $# -ne 3 ]]; then
  exit 2
fi
readonly SOURCE_STORE="$2"
readonly LAUNCHER="$3"
readonly TEMP_ROOT="$(mktemp -d /tmp/pastila-tokenizer-launcher-test.XXXXXX)"
case "$TEMP_ROOT" in /tmp/pastila-tokenizer-launcher-test.*) ;; *) exit 99 ;; esac

cleanup() {
  local cleanup_error=0
  local target
  set +e
  for target in \
    "$TEMP_ROOT/store/tokenizer-materialized-a" \
    "$TEMP_ROOT/store/objects/sha256/$TOKENIZER_SHA256.tar" \
    "$TEMP_ROOT/store"; do
    if mountpoint -q -- "$target"; then
      umount -- "$target" || cleanup_error=1
    fi
  done
  for target in \
    "$TEMP_ROOT/store/tokenizer-materialized-a" \
    "$TEMP_ROOT/store/objects/sha256/$TOKENIZER_SHA256.tar" \
    "$TEMP_ROOT/store"; do
    if mountpoint -q -- "$target"; then
      printf 'refusing cleanup with active mount: %s\n' "$target" >&2
      return 97
    fi
  done
  remaining_mounts="$(findmnt -rn -o TARGET | awk -v root="$TEMP_ROOT" \
    '$0 == root || index($0, root "/") == 1 { print }')"
  if [[ -n "$remaining_mounts" ]]; then
    printf 'refusing cleanup with unexpected mount(s):\n%s\n' "$remaining_mounts" >&2
    return 97
  fi
  if [[ "$TEMP_ROOT" != /tmp/pastila-tokenizer-launcher-test.* || \
        ! -d "$TEMP_ROOT" || -L "$TEMP_ROOT" ]]; then
    printf 'refusing cleanup of invalid temporary root\n' >&2
    return 98
  fi
  rm -rf -- "$TEMP_ROOT" || cleanup_error=1
  if [[ -e "$TEMP_ROOT" ]]; then
    printf 'temporary-root cleanup incomplete\n' >&2
    return 99
  fi
  return "$cleanup_error"
}
on_exit() {
  local operation_status=$?
  local cleanup_status=0
  trap - EXIT INT TERM
  cleanup || cleanup_status=$?
  if [[ $operation_status -ne 0 ]]; then
    exit "$operation_status"
  fi
  exit "$cleanup_status"
}
on_signal() {
  local signal_status="$1"
  trap - INT TERM
  exit "$signal_status"
}
trap on_exit EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

mkdir "$TEMP_ROOT/store"
mount --bind "$SOURCE_STORE" "$TEMP_ROOT/store"

set +e
"$LAUNCHER" "$TEMP_ROOT/store" tokenizer-materialized-a fixed >/dev/null
relocated=$?
"$LAUNCHER" "$TEMP_ROOT/store/../store" tokenizer-materialized-a fixed >/dev/null 2>&1
noncanonical=$?
ln -s "$TEMP_ROOT/store" "$TEMP_ROOT/store-link"
"$LAUNCHER" "$TEMP_ROOT/store-link" tokenizer-materialized-a fixed >/dev/null 2>&1
symlink_store=$?

printf bad >"$TEMP_ROOT/bad-object"
mount --bind "$TEMP_ROOT/bad-object" "$TEMP_ROOT/store/objects/sha256/$TOKENIZER_SHA256.tar"
"$LAUNCHER" "$TEMP_ROOT/store" tokenizer-materialized-a fixed >/dev/null 2>&1
bad_object=$?
umount "$TEMP_ROOT/store/objects/sha256/$TOKENIZER_SHA256.tar"

mkdir "$TEMP_ROOT/bad-tokenizer"
for name in chat_template.jinja config.json tokenizer.json tokenizer_config.json; do
  printf substituted >"$TEMP_ROOT/bad-tokenizer/$name"
done
mount --bind "$TEMP_ROOT/bad-tokenizer" "$TEMP_ROOT/store/tokenizer-materialized-a"
"$LAUNCHER" "$TEMP_ROOT/store" tokenizer-materialized-a fixed >/dev/null 2>&1
bad_tokenizer=$?
umount "$TEMP_ROOT/store/tokenizer-materialized-a"
set -e

test "$relocated" -eq 0
test "$noncanonical" -ne 0
test "$symlink_store" -ne 0
test "$bad_object" -ne 0
test "$bad_tokenizer" -ne 0
printf 'RELOCATED_AND_SUBSTITUTION_EXECUTABLE_PASS\n'
