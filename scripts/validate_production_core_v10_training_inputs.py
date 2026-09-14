"""Fail-closed, zero-model validation of V10 training inputs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import (
    GENERATION_POLICY,
    canonical,
    contract_identity,
    render_training_messages,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v10": (
        "pastila-editor-core-v1.1-json-successor",
        ROOT / ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
    ),
    "pastila-editor-core-v1.2-json-successor-v10": (
        "pastila-editor-core-v1.2-json-successor",
        ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
    ),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate(corpus: Path, config_path: Path) -> dict[str, object]:
    if corpus.is_symlink() or config_path.is_symlink():
        raise ValueError("symlink input rejected")
    corpus_raw = corpus.read_bytes()
    config = json.loads(config_path.read_bytes())
    candidate = config.get("candidate")
    if config.get("schema_version") != 4 or config.get("status") != "FROZEN_PRETRAINING_ZERO_EXECUTION":
        raise ValueError("V10 config boundary mismatch")
    if config.get("training_execution_profile") != "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS":
        raise ValueError("training execution profile mismatch")
    if config.get("performance_freeze_identity") != "d418ac661108e44237d3be7bbbda8e0ae9b4d0a5a918d95a47594095d055cfff":
        raise ValueError("performance freeze identity mismatch")
    if config.get("execution_contract_identity") != contract_identity():
        raise ValueError("execution contract identity mismatch")
    ceiling = GENERATION_POLICY["maximum_training_sequence_tokens"]
    if config.get("max_sequence_tokens") != ceiling or ceiling != 3072:
        raise ValueError("training ceiling mismatch")
    if config.get("training_corpus_sha256") != sha(corpus_raw):
        raise ValueError("training corpus identity mismatch")
    prompt_authority = PROMPTS.get(candidate)
    if prompt_authority is None:
        raise ValueError("candidate prompt authority mismatch")
    contract_candidate, prompt_path = prompt_authority
    if prompt_path.is_symlink():
        raise ValueError("candidate prompt authority mismatch")
    editorial = prompt_path.read_bytes()
    rows = [json.loads(line) for line in corpus_raw.splitlines()]
    if len(rows) != 480:
        raise ValueError("training corpus cardinality mismatch")
    for row in rows:
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            raise ValueError("training message shape mismatch")
        projected = list(render_training_messages(
            candidate=contract_candidate,
            editorial_prompt=editorial,
            user_prompt=messages[1].get("content"),
        ))
        if messages[:2] != projected:
            raise ValueError("training renderer divergence")
        target = messages[2]
        if tuple(target) != ("role", "content") or target["role"] != "assistant":
            raise ValueError("training target shape mismatch")
        raw_target = target["content"]
        if not isinstance(raw_target, str) or canonical(json.loads(raw_target)).decode() != raw_target:
            raise ValueError("training target is not canonical JSON")
    return {
        "candidate": candidate,
        "execution_contract_identity": contract_identity(),
        "maximum_training_sequence_tokens": ceiling,
        "rows": len(rows),
        "training_corpus_sha256": sha(corpus_raw),
        "model_loaded": False,
        "training_performed": False,
    }


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validator CORPUS CONFIG")
    print(json.dumps(validate(Path(sys.argv[1]), Path(sys.argv[2])), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
