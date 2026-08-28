"""Immutable source-only runtime-operations contract for generation V1."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


RUNTIME_OPERATIONS_CONTRACT_IDENTITY = "cc97c93651f42998a0cd921a0e32ae3a78a04e4fe5580d06395232496b3b0483"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
DEVICE_TRANSFER_POLICY = "CUDA_DEVICE_0_NON_BLOCKING_FALSE"
PROMPT_TOKEN_CEILING = 8192


@dataclass(frozen=True, slots=True)
class RuntimePromptBatchV1:
    input_token_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    prompt_token_count: int
    rendered_prompt_sha256: str
    tokenizer_identity: str
    decoder_identity: str
    batch_size: int
    device_transfer_policy: str


def validate_runtime_prompt_batch_v1(
    *, rendered_prompt: str, batch: RuntimePromptBatchV1,
) -> bytes:
    """Validate an explicit immutable text-only prompt batch."""
    if type(rendered_prompt) is not str or not rendered_prompt:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_RENDERED_PROMPT_REQUIRED")
    if type(batch) is not RuntimePromptBatchV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_PROMPT_BATCH_EXACT_TYPE_REQUIRED")
    prompt_sha256 = hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()
    exact = (
        batch.rendered_prompt_sha256 == prompt_sha256
        and batch.tokenizer_identity == TOKENIZER_IDENTITY
        and batch.decoder_identity == DECODER_IDENTITY
        and batch.batch_size == 1
        and batch.device_transfer_policy == DEVICE_TRANSFER_POLICY
        and type(batch.prompt_token_count) is int
        and batch.prompt_token_count == len(batch.input_token_ids)
        and 0 < batch.prompt_token_count <= PROMPT_TOKEN_CEILING
        and len(batch.attention_mask) == batch.prompt_token_count
        and all(type(item) is int and item >= 0 for item in batch.input_token_ids)
        and all(type(item) is int and item == 1 for item in batch.attention_mask)
    )
    if not exact:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_PROMPT_BATCH_MISMATCH")
    batch_value = {
        "input_token_ids": list(batch.input_token_ids),
        "attention_mask": list(batch.attention_mask),
        "prompt_token_count": batch.prompt_token_count,
        "rendered_prompt_sha256": batch.rendered_prompt_sha256,
        "tokenizer_identity": batch.tokenizer_identity,
        "decoder_identity": batch.decoder_identity,
        "batch_size": batch.batch_size,
        "device_transfer_policy": batch.device_transfer_policy,
    }
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-runtime-prompt-batch-receipt",
        "schema_version": "1.0.0",
        "runtime_operations_contract_identity": RUNTIME_OPERATIONS_CONTRACT_IDENTITY,
        "prompt_batch_sha256": hashlib.sha256(_canonical(batch_value)).hexdigest(),
        "rendered_prompt_sha256": prompt_sha256,
        "prompt_token_count": batch.prompt_token_count,
        "result": "RUNTIME_PROMPT_BATCH_VALIDATED_SOURCE_ONLY",
        "tokenizer_or_model_loaded": False,
        "generation_started": False,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "DECODER_IDENTITY", "DEVICE_TRANSFER_POLICY", "PROMPT_TOKEN_CEILING",
    "RUNTIME_OPERATIONS_CONTRACT_IDENTITY", "RuntimePromptBatchV1",
    "TOKENIZER_IDENTITY", "validate_runtime_prompt_batch_v1",
)
