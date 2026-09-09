#!/usr/bin/env bash
set -euo pipefail

readonly STORE=/home/pastila/.pastila-runtime/production-core-qualification-v1
readonly ROOTFS_SHA256=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
readonly TOKENIZER_SHA256=2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c
readonly TOKENIZER_SIZE=17295360
if [[ $# -ne 1 || ! "$1" =~ ^[AB]$ ]]; then
  echo "usage: launcher A|B" >&2
  exit 2
fi
readonly MATERIALIZATION="$1"
readonly ROOTFS_TAR="$STORE/objects/sha256/$ROOTFS_SHA256-$MATERIALIZATION.tar"
readonly TOKENIZER="$STORE/tokenizer-materialized-${MATERIALIZATION,,}"
readonly MODEL="$STORE/execution-materialization-$MATERIALIZATION/model"
readonly TOKENIZER_OBJECT="$STORE/objects/sha256/$TOKENIZER_SHA256.tar"
readonly REPOSITORY=/mnt/c/pf9
readonly PROBE="$REPOSITORY/scripts/probe_production_core_candidate_prompt_input_envelope_v1.py"
readonly LAUNCHER_SHA256="$(sha256sum "$0" | cut -d' ' -f1)"
readonly PROBE_SHA256="$(sha256sum "$PROBE" | cut -d' ' -f1)"
readonly PARENT_NET_NAMESPACE="$(readlink /proc/self/ns/net)"
readonly REPOSITORY_SNAPSHOT="$(mktemp -d /tmp/pcq-prompt-source.XXXXXXXX)"
trap 'rm -rf -- "$REPOSITORY_SNAPSHOT"' EXIT INT TERM
mkdir -p "$REPOSITORY_SNAPSHOT/docs/artifacts" "$REPOSITORY_SNAPSHOT/scripts"
cp -a -- "$REPOSITORY/src" "$REPOSITORY_SNAPSHOT/"
cp --no-dereference "$REPOSITORY/docs/artifacts/production-core-qualification-corpus-v1.json" \
  "$REPOSITORY_SNAPSHOT/docs/artifacts/"
cp -a -- \
  "$REPOSITORY/.experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence" \
  "$REPOSITORY/.experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence" \
  "$REPOSITORY_SNAPSHOT/"
cp --no-dereference "$PROBE" "$REPOSITORY_SNAPSHOT/scripts/"

for path in "$STORE" "$TOKENIZER" "$MODEL"; do
  [[ -d "$path" && ! -L "$path" && "$(realpath -e "$path")" = "$path" ]] || {
    echo "runtime authority resolution invalid" >&2; exit 3;
  }
done
[[ -f "$ROOTFS_TAR" && ! -L "$ROOTFS_TAR" ]] || {
  echo "rootfs object invalid" >&2; exit 3;
}
[[ "$(sha256sum "$ROOTFS_TAR" | cut -d' ' -f1)" = "$ROOTFS_SHA256" ]] || {
  echo "rootfs identity mismatch" >&2; exit 4;
}
[[ -f "$TOKENIZER_OBJECT" && ! -L "$TOKENIZER_OBJECT" ]] || {
  echo "tokenizer object invalid" >&2; exit 3;
}
[[ "$(wc -c < "$TOKENIZER_OBJECT")" -eq "$TOKENIZER_SIZE" ]] || exit 4
[[ "$(sha256sum "$TOKENIZER_OBJECT" | cut -d' ' -f1)" = "$TOKENIZER_SHA256" ]] || exit 4
for source in "$TOKENIZER" "$MODEL"; do
  reconstructed="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
    -C "$source" -cf - chat_template.jinja config.json tokenizer.json tokenizer_config.json | sha256sum | cut -d' ' -f1)"
  [[ "$reconstructed" = "$TOKENIZER_SHA256" ]] || {
    echo "runner/probe tokenizer equivalence mismatch" >&2; exit 4;
  }
done
readonly EFFECTIVE_FILES=(chat_template.jinja config.json special_tokens_map.json tokenizer.json tokenizer_config.json)
for source in "$STORE/execution-materialization-A/model" "$STORE/execution-materialization-B/model"; do
  [[ -f "$source/special_tokens_map.json" && ! -L "$source/special_tokens_map.json" ]] || {
    echo "effective tokenizer closure invalid" >&2; exit 3;
  }
done
readonly EFFECTIVE_TOKENIZER_SHA256="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
  -C "$MODEL" -cf - "${EFFECTIVE_FILES[@]}" | sha256sum | cut -d' ' -f1)"
readonly OTHER_MODEL="$STORE/execution-materialization-$([[ "$MATERIALIZATION" = A ]] && echo B || echo A)/model"
readonly OTHER_EFFECTIVE_SHA256="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
  -C "$OTHER_MODEL" -cf - "${EFFECTIVE_FILES[@]}" | sha256sum | cut -d' ' -f1)"
[[ "$EFFECTIVE_TOKENIZER_SHA256" = "$OTHER_EFFECTIVE_SHA256" ]] || {
  echo "effective runner tokenizer closures differ" >&2; exit 4;
}
readonly DISTINCT_A="$(stat -Lc '%d:%i' "$STORE/execution-materialization-A/model")"
readonly DISTINCT_B="$(stat -Lc '%d:%i' "$STORE/execution-materialization-B/model")"
[[ "$DISTINCT_A" != "$DISTINCT_B" ]] || { echo "materializations alias" >&2; exit 4; }

exec unshare --net --fork bash -c '
  set -euo pipefail
  rootfs_tar="$1"; model="$2"; repository="$3"; materialization="$4"
  rootfs_sha="$5"; tokenizer_sha="$6"; effective_tokenizer_sha="$7"; launcher_sha="$8"; probe_sha="$9"; parent_netns="${10}"
  child_netns="$(readlink /proc/self/ns/net)"
  [[ "$child_netns" != "$parent_netns" ]] || { echo "network namespace not isolated" >&2; exit 7; }
  work="$(mktemp -d /tmp/pcq-prompt-probe.XXXXXXXX)"
  root="$work/rootfs"
  mkdir "$root"
  cleanup() {
    rm -rf -- "$work" "$repository"
  }
  trap cleanup EXIT INT TERM
  exec {rootfs_fd}<"$rootfs_tar"
  [[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d" " -f1)" = "$rootfs_sha" ]]
  tar -xf "/proc/self/fd/$rootfs_fd" -C "$root"
  [[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d" " -f1)" = "$rootfs_sha" ]]
  mkdir -p "$root/dev"
  mknod -m 0666 "$root/dev/null" c 1 3
  mknod -m 0444 "$root/dev/urandom" c 1 9
  mkdir -p "$root/tmp/tokenizer" "$root/tmp/repo/docs/artifacts" "$root/tmp/repo/scripts"
  cp --no-dereference \
    "$model/chat_template.jinja" \
    "$model/config.json" \
    "$model/special_tokens_map.json" \
    "$model/tokenizer.json" \
    "$model/tokenizer_config.json" \
    "$root/tmp/tokenizer/"
  cp -a -- "$repository/." "$root/tmp/repo/"
  receipt="$(env -i \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONPATH=/tmp/repo/src \
    LC_ALL=C.UTF-8 \
    EXPECTED_NETWORK_INTERFACES=lo \
    CUDA_VISIBLE_DEVICES= \
    /usr/sbin/chroot "$root" \
    /opt/production-core-runtime/bin/python -I \
    /tmp/repo/scripts/probe_production_core_candidate_prompt_input_envelope_v1.py \
    /tmp/repo /tmp/tokenizer "$materialization" "$rootfs_sha" "$tokenizer_sha" \
    "$effective_tokenizer_sha" \
    "$launcher_sha" "$probe_sha")"
  receipt_path="/tmp/production-core-prompt-envelope-$materialization.json"
  printf "%s\n" "$receipt" > "$receipt_path"
  printf "%s\n" "$receipt"
  after="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu \
    -C "$root/tmp/tokenizer" -cf - chat_template.jinja config.json special_tokens_map.json tokenizer.json tokenizer_config.json | sha256sum | cut -d" " -f1)"
  [[ "$after" = "$effective_tokenizer_sha" ]] || { echo "tokenizer snapshot changed" >&2; exit 4; }
' sh "$ROOTFS_TAR" "$MODEL" "$REPOSITORY_SNAPSHOT" "$MATERIALIZATION" "$ROOTFS_SHA256" \
  "$TOKENIZER_SHA256" "$EFFECTIVE_TOKENIZER_SHA256" "$LAUNCHER_SHA256" "$PROBE_SHA256" \
  "$PARENT_NET_NAMESPACE"
