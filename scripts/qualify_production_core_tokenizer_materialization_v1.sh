#!/usr/bin/env bash
set -euo pipefail

readonly ROOTFS_SHA256="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
readonly TOKENIZER_SHA256="2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
readonly TOKENIZER_SIZE=17295360
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(realpath -e -- "$SCRIPT_DIR/..")"
readonly PROBE="$REPO_ROOT/src/pastila_scout/production_core_tokenizer_materialization_probe_v1.py"
readonly PROBE_SHA256="1ef4fd391872b14714e5b6fd3b9fcdc887b447822f57e30dd82e36c86326bb95"
readonly CORPUS="$REPO_ROOT/docs/artifacts/production-core-tokenizer-regex-comparison-corpus-v1.json"
readonly CORPUS_SHA256="42d071e047bc7ea3a9cc2d1b7c2c22f74d8db4355a976c51cb727ee3dd0ecd78"
readonly DEFAULT_STDERR_SHA256="4425935b0a695ecb79d5d3b975e8b3fbd73594c24ae6deb1bb235491faae873d"
readonly DEFAULT_STDERR_SIZE=348
readonly PYTHON="/opt/production-core-runtime/bin/python"

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "invalid tokenizer materialization" >&2
  exit 2
fi
readonly STORE_INPUT="$1"
readonly MATERIALIZATION="$2"
readonly MODE="$3"
if [[ ! "$MATERIALIZATION" =~ ^tokenizer-materialized-[ab]$ ]] || \
   [[ "$MODE" = fixed && $# -ne 3 ]] || \
   [[ "$MODE" = frozen-default && ( $# -ne 4 || "$4" != comparison-only ) ]] || \
   [[ ! "$MODE" =~ ^(frozen-default|fixed)$ ]]; then
  echo "invalid tokenizer materialization" >&2
  exit 2
fi
if [[ ! -d "$STORE_INPUT" || -L "$STORE_INPUT" ]]; then
  echo "invalid object store resolution" >&2
  exit 2
fi
readonly OBJECT_STORE_ROOT="$(realpath -e -- "$STORE_INPUT")"
if [[ "$OBJECT_STORE_ROOT" != "$STORE_INPUT" || "$OBJECT_STORE_ROOT" = / || "$OBJECT_STORE_ROOT" = "$REPO_ROOT" ]]; then
  echo "invalid object store resolution" >&2
  exit 2
fi
readonly ROOTFS="$OBJECT_STORE_ROOT/materialized-c"
readonly TOKENIZER="$OBJECT_STORE_ROOT/$MATERIALIZATION"
readonly TOKENIZER_OBJECT="$OBJECT_STORE_ROOT/objects/sha256/$TOKENIZER_SHA256.tar"
if [[ ! -d "$ROOTFS" || -L "$ROOTFS" || "$(realpath -e -- "$ROOTFS")" != "$ROOTFS" ]] || \
   [[ ! -d "$TOKENIZER" || -L "$TOKENIZER" || "$(realpath -e -- "$TOKENIZER")" != "$TOKENIZER" ]] || \
   [[ ! -f "$TOKENIZER_OBJECT" || -L "$TOKENIZER_OBJECT" || "$(realpath -e -- "$TOKENIZER_OBJECT")" != "$TOKENIZER_OBJECT" ]]; then
  echo "invalid tokenizer materialization resolution" >&2
  exit 2
fi
case "$ROOTFS" in "$OBJECT_STORE_ROOT"/*) ;; *) echo "rootfs escaped object store" >&2; exit 2 ;; esac
case "$TOKENIZER" in "$OBJECT_STORE_ROOT"/*) ;; *) echo "tokenizer escaped object store" >&2; exit 2 ;; esac
case "$TOKENIZER_OBJECT" in "$OBJECT_STORE_ROOT"/objects/sha256/*) ;; *) echo "object escaped store" >&2; exit 2 ;; esac
if [[ "$(wc -c < "$TOKENIZER_OBJECT")" -ne "$TOKENIZER_SIZE" ]] || \
   [[ "$(sha256sum "$TOKENIZER_OBJECT" | cut -d' ' -f1)" != "$TOKENIZER_SHA256" ]]; then
  echo "content-addressed tokenizer object mismatch" >&2
  exit 4
fi
if [[ ! -f "$PROBE" || -L "$PROBE" ]]; then
  echo "invalid tokenizer probe" >&2
  exit 3
fi
if [[ "$(sha256sum "$PROBE" | cut -d' ' -f1)" != "$PROBE_SHA256" ]]; then
  echo "tokenizer probe identity mismatch" >&2
  exit 3
fi
if [[ ! -f "$CORPUS" || -L "$CORPUS" || "$(sha256sum "$CORPUS" | cut -d' ' -f1)" != "$CORPUS_SHA256" ]]; then
  echo "comparison corpus identity mismatch" >&2
  exit 3
fi
readonly RECONSTRUCTED="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
  -C "$TOKENIZER" -cf - chat_template.jinja config.json tokenizer.json tokenizer_config.json | sha256sum | cut -d' ' -f1)"
if [[ "$RECONSTRUCTED" != "$TOKENIZER_SHA256" ]]; then
  echo "tokenizer materialization identity mismatch" >&2
  exit 4
fi

exec unshare --net --mount --fork sh -c '
  set -eu
  mount --bind "$1" "$1"
  mount -o remount,bind,ro "$1"
  before="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$1" -cf - . | sha256sum | cut -d" " -f1)"
  if [ "$before" != "$6" ]; then
    echo "runtime rootfs identity mismatch" >&2
    exit 5
  fi
  mount --rbind /dev "$1/dev"
  mount -t proc proc "$1/proc"
  mount -t sysfs sysfs "$1/sys"
  if find "$1/sys/class/net" -mindepth 1 -maxdepth 1 ! -name lo -print -quit | grep -q .; then
    echo "network namespace contains a non-loopback interface" >&2
    exit 7
  fi
  mount -t tmpfs -o size=64m,mode=1777 tmpfs "$1/tmp"
  mkdir "$1/tmp/tokenizer"
  for name in chat_template.jinja config.json tokenizer.json tokenizer_config.json; do
    cp --no-dereference -- "$2/$name" "$1/tmp/tokenizer/$name"
  done
  if find "$1/tmp/tokenizer" -type l -print -quit | grep -q .; then
    echo "tokenizer snapshot contains a symlink" >&2
    exit 4
  fi
  snapshot="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
    -C "$1/tmp/tokenizer" -cf - chat_template.jinja config.json tokenizer.json tokenizer_config.json | sha256sum | cut -d" " -f1)"
  if [ "$snapshot" != "$5" ]; then
    echo "tokenizer snapshot identity mismatch" >&2
    exit 4
  fi
  mount --bind "$1/tmp/tokenizer" "$1/tmp/tokenizer"
  mount -o remount,bind,ro "$1/tmp/tokenizer"
  cp --no-dereference -- "$3" "$1/tmp/probe.py"
  if [ "$(sha256sum "$1/tmp/probe.py" | cut -d" " -f1)" != "$7" ]; then
    echo "mounted tokenizer probe identity mismatch" >&2
    exit 3
  fi
  mount --bind "$1/tmp/probe.py" "$1/tmp/probe.py"
  mount -o remount,bind,ro "$1/tmp/probe.py"
  cp --no-dereference -- "$8" "$1/tmp/corpus.json"
  if [ "$(sha256sum "$1/tmp/corpus.json" | cut -d" " -f1)" != "$9" ]; then
    echo "mounted comparison corpus identity mismatch" >&2
    exit 3
  fi
  mount --bind "$1/tmp/corpus.json" "$1/tmp/corpus.json"
  mount -o remount,bind,ro "$1/tmp/corpus.json"
  set +e
  env -i HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false LC_ALL=C.UTF-8 \
    /usr/sbin/chroot "$1" "$4" -I /tmp/probe.py /tmp/tokenizer /tmp/corpus.json "${10}" \
    >"$1/tmp/probe.stdout" 2>"$1/tmp/probe.stderr"
  result=$?
  set -e
  if [ "${10}" = fixed ] && [ -s "$1/tmp/probe.stderr" ]; then
    echo "qualification tokenizer emitted stderr" >&2
    cat "$1/tmp/probe.stderr" >&2
    result=8
  elif [ "${10}" = frozen-default ] && \
       { [ "$(wc -c < "$1/tmp/probe.stderr")" -ne "${12}" ] || \
         [ "$(sha256sum "$1/tmp/probe.stderr" | cut -d" " -f1)" != "${11}" ]; }; then
    echo "comparison-only tokenizer stderr identity mismatch" >&2
    result=9
  elif [ "${10}" = frozen-default ]; then
    cat "$1/tmp/probe.stderr" >&2
  fi
  cat "$1/tmp/probe.stdout"
  umount "$1/tmp/corpus.json"
  umount "$1/tmp/probe.py"
  umount "$1/tmp/tokenizer"
  umount "$1/tmp"
  umount "$1/sys"
  umount "$1/proc"
  umount -R "$1/dev"
  after="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$1" -cf - . | sha256sum | cut -d" " -f1)"
  if [ "$after" != "$6" ]; then
    echo "runtime rootfs mutated during tokenizer probe" >&2
    exit 6
  fi
  exit "$result"
' sh "$ROOTFS" "$TOKENIZER" "$PROBE" "$PYTHON" "$TOKENIZER_SHA256" "$ROOTFS_SHA256" "$PROBE_SHA256" "$CORPUS" "$CORPUS_SHA256" "$MODE" "$DEFAULT_STDERR_SHA256" "$DEFAULT_STDERR_SIZE"
