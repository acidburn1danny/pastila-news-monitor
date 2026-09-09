#!/usr/bin/env bash
set -euo pipefail

readonly SOURCE_STORE=/home/pastila/.pastila-runtime/production-core-qualification-v1
readonly SOURCE_LAUNCHER=/mnt/c/pf9/scripts/probe_production_core_candidate_prompt_input_envelope_v1.sh
readonly ROOTFS=274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4
readonly TOKENIZER=2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c
readonly WORK="$(mktemp -d /tmp/pcq-prompt-negative.XXXXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT

make_store() {
  local store="$1" materialization name
  mkdir -p "$store/objects/sha256"
  ln "$SOURCE_STORE/objects/sha256/$TOKENIZER.tar" "$store/objects/sha256/$TOKENIZER.tar"
  for materialization in A B; do
    ln "$SOURCE_STORE/objects/sha256/$ROOTFS-$materialization.tar" \
      "$store/objects/sha256/$ROOTFS-$materialization.tar"
    mkdir -p "$store/execution-materialization-$materialization/model"
    mkdir -p "$store/tokenizer-materialized-${materialization,,}"
    for name in chat_template.jinja config.json tokenizer.json tokenizer_config.json; do
      cp "$SOURCE_STORE/execution-materialization-$materialization/model/$name" \
        "$store/execution-materialization-$materialization/model/$name"
      cp "$SOURCE_STORE/tokenizer-materialized-${materialization,,}/$name" \
        "$store/tokenizer-materialized-${materialization,,}/$name"
    done
    cp "$SOURCE_STORE/execution-materialization-$materialization/model/special_tokens_map.json" \
      "$store/execution-materialization-$materialization/model/special_tokens_map.json"
  done
  sed "s|readonly STORE=.*|readonly STORE=$store|" "$SOURCE_LAUNCHER" > "$store/launcher.sh"
}

store="$WORK/tokenizer-substitution"
make_store "$store"
printf x >> "$store/tokenizer-materialized-a/tokenizer_config.json"
if bash "$store/launcher.sh" A >/dev/null 2>&1; then
  echo "tokenizer substitution accepted" >&2
  exit 1
fi

store="$WORK/special-token-substitution"
make_store "$store"
printf x >> "$store/execution-materialization-A/model/special_tokens_map.json"
if bash "$store/launcher.sh" A >/dev/null 2>&1; then
  echo "special-token substitution accepted" >&2
  exit 1
fi

store="$WORK/rootfs-substitution"
make_store "$store"
rm "$store/objects/sha256/$ROOTFS-A.tar"
printf substituted > "$store/objects/sha256/$ROOTFS-A.tar"
if bash "$store/launcher.sh" A >/dev/null 2>&1; then
  echo "rootfs substitution accepted" >&2
  exit 1
fi

echo PROMPT_INPUT_ENVELOPE_NEGATIVE_PASS
