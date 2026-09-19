"""Tokenizer-only length/EOS audit for the targeted continuation round."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer

PREFIX = "editor-core-v10-v12-targeted-continuation-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def ids(value: object) -> list[int]:
    if hasattr(value, "get") and value.get("input_ids") is not None:
        value = value.get("input_ids")
    values = getattr(value, "ids", value)
    if isinstance(values, (list, tuple)) and len(values) == 1 and hasattr(values[0], "ids"):
        values = values[0].ids
    if not isinstance(values, (list, tuple)) or not all(type(item) is int for item in values):
        raise ValueError("tokenizer output shape mismatch")
    return list(values)


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def audit(model: Path, artifacts: Path) -> dict:
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    training = load(artifacts / f"{PREFIX}-training.jsonl")
    holdout = load(artifacts / f"{PREFIX}-holdout-requests.jsonl")
    keys = {row["example_id"]: row for row in load(artifacts / f"{PREFIX}-holdout-answer-key.jsonl")}
    manifest = json.loads((artifacts / f"{PREFIX}-manifest.json").read_bytes())
    observed = {"training": [], "holdout_input": [], "holdout_expected_sequence": []}
    for row in training:
        prefix = ids(tokenizer.apply_chat_template(row["messages"][:2], tokenize=True, add_generation_prompt=True))
        full = ids(tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=False))
        if not full or full[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in full[len(prefix):-1]:
            raise ValueError(f"EOS closure mismatch: {row['example_id']}: eos={tokenizer.eos_token_id}:tail={full[-8:]}:prefix={len(prefix)}:full={len(full)}")
        observed["training"].append(len(full))
    for row in holdout:
        prefix = ids(tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True))
        target = keys[row["example_id"]]["assistant_target"]
        full_messages = row["messages"] + [{"role": "assistant", "content": target}]
        full = ids(tokenizer.apply_chat_template(full_messages, tokenize=True, add_generation_prompt=False))
        if not full or full[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in full[len(prefix):-1]:
            raise ValueError(f"holdout EOS closure mismatch: {row['example_id']}")
        observed["holdout_input"].append(len(prefix))
        observed["holdout_expected_sequence"].append(len(full))
    result = {
        "schema": "pastila-editor-core-targeted-continuation-token-audit",
        "schema_version": 1,
        "status": "PASS_TOKENIZER_ONLY_ZERO_MODEL_LOAD_ZERO_TRAINING",
        "tokenizer_sha256": "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c",
        "dataset_manifest_identity": manifest["manifest_identity"],
        "training_corpus_sha256": manifest["artifacts"]["training"]["sha256"],
        "holdout_requests_sha256": manifest["artifacts"]["holdout-requests"]["sha256"],
        "holdout_answer_key_sha256": manifest["artifacts"]["holdout-answer-key"]["sha256"],
        "training_rows": len(training),
        "holdout_rows": len(holdout),
        "maximum_training_sequence_tokens": max(observed["training"]),
        "maximum_holdout_input_tokens": max(observed["holdout_input"]),
        "maximum_holdout_expected_sequence_tokens": max(observed["holdout_expected_sequence"]),
        "configured_ceiling": 3072,
        "all_sequences_within_ceiling": max(observed["training"] + observed["holdout_expected_sequence"]) <= 3072,
        "terminal_eos_verified": True,
        "model_loaded": False,
        "inference_performed": False,
        "training_performed": False,
    }
    if not result["all_sequences_within_ceiling"]:
        raise ValueError("token ceiling exceeded")
    return {**result, "audit_identity": sha(canonical(result))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("artifacts", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.model, args.artifacts), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
