#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 2 && "$1" =~ ^[AB]$ ]] || { echo "usage: launcher A|B REPOSITORY" >&2; exit 2; }
readonly MATERIALIZATION="$1"
readonly REPOSITORY="$2"
readonly STORE=/home/pastila/.pastila-runtime/production-core-qualification-v1
readonly ROOTFS_SHA=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
readonly TOKENIZER_SHA=2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c
readonly EFFECTIVE_TOKENIZER_SHA=7a2235fbe0a3c0caf083a14fb7c9150828927dfb0dc8808abef4568b93bfff7d
readonly ROOTFS="$STORE/objects/sha256/$ROOTFS_SHA-$MATERIALIZATION.tar"
readonly MODEL="$STORE/execution-materialization-$MATERIALIZATION/model"
readonly SNAPSHOT="$(mktemp -d /tmp/pcq-v2-input.XXXXXXXX)"
trap 'rm -rf -- "$SNAPSHOT"' EXIT INT TERM
[[ -d "$REPOSITORY" && ! -L "$REPOSITORY" ]] || exit 3
[[ -f "$ROOTFS" && ! -L "$ROOTFS" && "$(sha256sum "$ROOTFS" | cut -d' ' -f1)" = "$ROOTFS_SHA" ]] || exit 4
for source in "$STORE/execution-materialization-A/model" "$STORE/execution-materialization-B/model"; do
  [[ -d "$source" && ! -L "$source" ]] || exit 3
  for name in chat_template.jinja config.json special_tokens_map.json tokenizer.json tokenizer_config.json; do
    [[ -f "$source/$name" && ! -L "$source/$name" ]] || exit 3
  done
  actual="$(tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu -C "$source" -cf - chat_template.jinja config.json special_tokens_map.json tokenizer.json tokenizer_config.json | sha256sum | cut -d' ' -f1)"
  [[ "$actual" = "$EFFECTIVE_TOKENIZER_SHA" ]] || { echo "effective tokenizer mismatch" >&2; exit 4; }
done
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu -C "$MODEL" -cf "$SNAPSHOT/tokenizer.tar" chat_template.jinja config.json special_tokens_map.json tokenizer.json tokenizer_config.json
snapshot_tokenizer_sha="$(sha256sum "$SNAPSHOT/tokenizer.tar" | cut -d' ' -f1)"
[[ "$snapshot_tokenizer_sha" = "$EFFECTIVE_TOKENIZER_SHA" ]] || exit 4
mkdir -p "$SNAPSHOT/repo/docs/artifacts" "$SNAPSHOT/repo/scripts"
cp --no-dereference "$REPOSITORY/docs/artifacts/production-core-candidate-request-manifest-v2.json" "$SNAPSHOT/repo/docs/artifacts/"
cp --no-dereference "$REPOSITORY/scripts/probe_production_core_candidate_prompt_input_envelope_v2.py" "$SNAPSHOT/repo/scripts/"
cp -a -- "$REPOSITORY/.experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence" "$SNAPSHOT/repo/"
cp -a -- "$REPOSITORY/.experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence" "$SNAPSHOT/repo/"
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --format=gnu -C "$SNAPSHOT/repo" -cf "$SNAPSHOT/repo.tar" .
readonly REPO_SNAPSHOT_SHA="$(sha256sum "$SNAPSHOT/repo.tar" | cut -d' ' -f1)"
readonly RUNTIME_SHA="$(printf '%s\0%s\0%s\0%s' "$ROOTFS_SHA" "$TOKENIZER_SHA" "$EFFECTIVE_TOKENIZER_SHA" "$REPO_SNAPSHOT_SHA" | sha256sum | cut -d' ' -f1)"
readonly LAUNCHER_SHA="$(sha256sum "$0" | cut -d' ' -f1)"
readonly PROBE_SHA="$(sha256sum "$SNAPSHOT/repo/scripts/probe_production_core_candidate_prompt_input_envelope_v2.py" | cut -d' ' -f1)"
readonly PARENT_NETNS="$(readlink /proc/self/ns/net)"
exec unshare --net --fork bash -c '
  set -euo pipefail
  rootfs="$1"; snapshot="$2"; materialization="$3"; runtime_sha="$4"; parent="$5"; expected_rootfs="$6"; expected_repo="$7"; launcher_sha="$8"; probe_sha="$9"
  [[ "$(readlink /proc/self/ns/net)" != "$parent" ]] || exit 7
  work="$(mktemp -d /tmp/pcq-v2-root.XXXXXXXX)"; root="$work/root"; mkdir "$root"
  trap '\''rm -rf -- "$work" "$snapshot"'\'' EXIT INT TERM
  exec {rootfs_fd}<"$rootfs"
  [[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d" " -f1)" = "$expected_rootfs" ]] || exit 4
  tar -xf "/proc/self/fd/$rootfs_fd" -C "$root"
  [[ "$(sha256sum "/proc/self/fd/$rootfs_fd" | cut -d" " -f1)" = "$expected_rootfs" ]] || exit 4
  mkdir -p "$root/dev" "$root/tmp/tokenizer" "$root/tmp/repo"
  mknod -m 0666 "$root/dev/null" c 1 3; mknod -m 0444 "$root/dev/urandom" c 1 9
  exec {tokenizer_fd}<"$snapshot/tokenizer.tar"
  [[ "$(sha256sum "/proc/self/fd/$tokenizer_fd" | cut -d" " -f1)" = "7a2235fbe0a3c0caf083a14fb7c9150828927dfb0dc8808abef4568b93bfff7d" ]] || exit 4
  tar -xf "/proc/self/fd/$tokenizer_fd" -C "$root/tmp/tokenizer"
  [[ "$(sha256sum "/proc/self/fd/$tokenizer_fd" | cut -d" " -f1)" = "7a2235fbe0a3c0caf083a14fb7c9150828927dfb0dc8808abef4568b93bfff7d" ]] || exit 4
  exec {repo_fd}<"$snapshot/repo.tar"
  [[ "$(sha256sum "/proc/self/fd/$repo_fd" | cut -d" " -f1)" = "$expected_repo" ]] || exit 4
  tar -xf "/proc/self/fd/$repo_fd" -C "$root/tmp/repo"
  [[ "$(sha256sum "/proc/self/fd/$repo_fd" | cut -d" " -f1)" = "$expected_repo" ]] || exit 4
  env -i HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false LC_ALL=C.UTF-8 EXPECTED_NETWORK_INTERFACES=lo CUDA_VISIBLE_DEVICES= \
    /usr/sbin/chroot "$root" /opt/production-core-runtime/bin/python -I \
    /tmp/repo/scripts/probe_production_core_candidate_prompt_input_envelope_v2.py \
    /tmp/repo /tmp/tokenizer "$materialization" "$runtime_sha" "$expected_repo" "$launcher_sha" "$probe_sha"
' sh "$ROOTFS" "$SNAPSHOT" "$MATERIALIZATION" "$RUNTIME_SHA" "$PARENT_NETNS" "$ROOTFS_SHA" "$REPO_SNAPSHOT_SHA" "$LAUNCHER_SHA" "$PROBE_SHA"
