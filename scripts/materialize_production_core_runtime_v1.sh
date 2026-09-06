#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_FREEZE="d5885027194ade26a8dec3ac13ccecd3ae6f6b9d"
readonly EXPECTED_FREEZE_TREE="f8d14d3d99570a24b379d01e8789158bde786a6d"
readonly EXPECTED_PROFILE_SHA256="92bafd61be5f43fea48bf1e88b35eb694ab26d8a09b420243770ea37d46e8274"
readonly ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
readonly AUTHORITY_ROOT="/home/pastila/.pastila-runtime/production-core-qualification-v1"
readonly SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPOSITORY="$(dirname -- "$SCRIPT_DIRECTORY")"

if [[ $# -ne 1 ]]; then
  echo "invalid materialization target" >&2
  exit 2
fi
readonly TARGET="$1"
readonly TARGET_PARENT="$(dirname -- "$TARGET")"
readonly TARGET_NAME="$(basename -- "$TARGET")"
if [[ "$TARGET_PARENT" != "$AUTHORITY_ROOT" || ! "$TARGET_NAME" =~ ^materialized-[a-z0-9-]+$ ]]; then
  echo "invalid materialization target" >&2
  exit 2
fi
if [[ -e "$TARGET" || -L "$TARGET" ]]; then
  echo "materialization target already exists" >&2
  exit 3
fi
if [[ -L "$AUTHORITY_ROOT" || "$(realpath -e -- "$AUTHORITY_ROOT")" != "$AUTHORITY_ROOT" ]]; then
  echo "runtime authority root is not canonical" >&2
  exit 3
fi
readonly GIT_POINTER="$(sed -n 's/^gitdir: //p' "$REPOSITORY/.git")"
if [[ -z "$GIT_POINTER" ]]; then
  echo "worktree Git authority unavailable" >&2
  exit 4
fi
readonly GIT_DIRECTORY="$(wslpath -u "$GIT_POINTER")"
if [[ "$(git --git-dir="$GIT_DIRECTORY" cat-file -t "$EXPECTED_FREEZE")" != commit ]] \
  || [[ "$(git --git-dir="$GIT_DIRECTORY" show -s --format=%T "$EXPECTED_FREEZE")" != "$EXPECTED_FREEZE_TREE" ]] \
  || [[ "$(git --git-dir="$GIT_DIRECTORY" show "$EXPECTED_FREEZE:docs/artifacts/production-core-execution-profile-proposal-v1.json" | sha256sum | cut -d' ' -f1)" != "$EXPECTED_PROFILE_SHA256" ]]; then
  echo "freeze authority mismatch" >&2
  exit 4
fi
readonly ROOTFS_OBJECT="$AUTHORITY_ROOT/objects/sha256/$ROOTFS_SHA256.tar"
if [[ ! -f "$ROOTFS_OBJECT" || -L "$ROOTFS_OBJECT" ]]; then
  echo "content-addressed rootfs object unavailable" >&2
  exit 5
fi
exec 3<"$ROOTFS_OBJECT"
if [[ "$(sha256sum /proc/self/fd/3 | cut -d' ' -f1)" != "$ROOTFS_SHA256" ]]; then
  echo "content-addressed rootfs object mismatch" >&2
  exit 6
fi

readonly STAGING="$AUTHORITY_ROOT/.materializing-$(basename -- "$TARGET")-$$"
if [[ -e "$STAGING" ]]; then
  echo "materialization staging collision" >&2
  exit 6
fi
cleanup() {
  rm -rf --one-file-system -- "$STAGING"
}
trap cleanup EXIT INT TERM
mkdir -m 0700 -- "$STAGING"
tar -C "$STAGING" -xf /proc/self/fd/3

# Canonical identity ignores mutable ownership and timestamps while binding every
# path, mode, symlink target, and byte in deterministic path order.
readonly MATERIALIZED_SHA256="$(
  tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
    -C "$STAGING" -cf - . | sha256sum | cut -d' ' -f1
)"
if [[ "$MATERIALIZED_SHA256" != "$ROOTFS_SHA256" ]]; then
  echo "materialized rootfs identity mismatch" >&2
  exit 7
fi
if [[ "$(sha256sum /proc/self/fd/3 | cut -d' ' -f1)" != "$ROOTFS_SHA256" ]]; then
  echo "content-addressed rootfs object changed during consumption" >&2
  exit 7
fi
mv -T -- "$STAGING" "$TARGET"
trap - EXIT INT TERM
printf '%s\n' "$MATERIALIZED_SHA256"
