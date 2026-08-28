"""Source-only generation policy gate for Construction-Obligation V2.

This module validates policy values only.  It has no runtime imports, model
construction, tokenizer loading, transport, or generation call site.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


POLICY_GATE_IDENTITY = "7a6e3629275e80d61b0af20d88393b158f2ac1154d6e9017f5bf3489f5d6b7d4"
MODEL_LOAD_POLICY_GATE_IDENTITY = "9410ef484986fc14534334ebf6a6912d381e2882b8fca948de4b215b2e7a8931"
IMMUTABLE_MANIFEST_IDENTITY = "bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9"
ADAPTER_COMPATIBILITY_GATE_IDENTITY = "66b89ee1b4d8f9832b86a59c9b83c07f8a2c0c3e1a9f25494ad50ed7c4b2ccdd"
ADAPTER_COMPATIBILITY_RECEIPT_IDENTITY = "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f"
HOST_PAYLOAD_CONTRACT_IDENTITY = "1dc94cda37c270fda49bca7b430bbad4970b3afadf2d0e348cfc3479161e1a49"
RUNNER_PROTOCOL_IDENTITY = "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf"
RUNNER_CODEC_IDENTITY = "09de75b7ecc52dedde19bf1f773c52ecf5a0a9da72da30a28113778b3867398f"
RUNNER_IDENTITIES = (
    "4f2c2b790b1e6f843e81fba418935f629867cf179fda3f548caac9f1306d03c2",
    "7a8ad4379362debbbf72425d3c2328bc9bed778b45fe083a42d47f8407428b52",
    "83074527007e585be686caac6a6951df000e3de0052ff104e45bdc529ce44908",
    "f21bc27ccdbd1941783e2cfc893eede389e5a56207342a97d7fafc66b4506f91",
    "a4f958ac8b793da4e5c9d2d91145b8d49c2ca8624d209e9aed0670eced35f678",
)
PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
LOCAL_MODEL_IDENTITY = "pastila-editor-core-v1.2-experimental"
PROVIDER_REQUEST_BINDING_IDENTITY = "02ab80de6c994bede334dc87faaa20a30302d445a8ac162494428789df1b6cc5"
PROVIDER_DESCRIPTOR_IDENTITY = (
    "scout:provider-descriptor-v2:"
    "72aec3ff060fbedee82a8264c15e2033f07bd99ea84cdb0152c637cf4aa0f159"
)


@dataclass(frozen=True, slots=True)
class ObservedGenerationExecutionPolicyV1:
    model_load_policy_gate_identity: str
    immutable_manifest_identity: str
    adapter_compatibility_gate_identity: str
    adapter_compatibility_receipt_identity: str
    host_payload_contract_identity: str
    runner_protocol_identity: str
    runner_codec_identity: str
    runner_identities: tuple[str, ...]
    projector_freeze_identity: str
    tokenizer_identity: str
    decoder_identity: str
    local_model_identity: str
    local_execution_mode: str
    provider_request_binding_identity: str
    provider_descriptor_identity: str
    provider_role: str
    provider_execution_authorized: bool
    prompt_token_ceiling: int
    output_token_ceiling: int
    batch_size: int
    do_sample: bool
    num_beams: int
    repetition_penalty: float
    use_cache: bool
    attempt_ceiling: int
    retry_count: int
    fallback_enabled: bool
    repair_enabled: bool
    selection_enabled: bool
    prompt_tokens_validated_before_generation: bool
    compatibility_receipt_required_before_generation: bool
    durable_raw_output_required: bool
    durable_lifecycle_required: bool
    durable_result_required: bool
    cleanup_receipt_required: bool
    partial_output_semantic_authority: bool
    stage_c_authorized: bool


def canonical_observed_generation_execution_policy_v1() -> ObservedGenerationExecutionPolicyV1:
    return ObservedGenerationExecutionPolicyV1(
        MODEL_LOAD_POLICY_GATE_IDENTITY,
        IMMUTABLE_MANIFEST_IDENTITY,
        ADAPTER_COMPATIBILITY_GATE_IDENTITY,
        ADAPTER_COMPATIBILITY_RECEIPT_IDENTITY,
        HOST_PAYLOAD_CONTRACT_IDENTITY,
        RUNNER_PROTOCOL_IDENTITY,
        RUNNER_CODEC_IDENTITY,
        RUNNER_IDENTITIES,
        PROJECTOR_FREEZE_IDENTITY,
        TOKENIZER_IDENTITY,
        DECODER_IDENTITY,
        LOCAL_MODEL_IDENTITY,
        "LOCAL_MODEL_DIRECT_EXECUTION",
        PROVIDER_REQUEST_BINDING_IDENTITY,
        PROVIDER_DESCRIPTOR_IDENTITY,
        "REQUEST_PROVENANCE_ONLY",
        False,
        8192,
        3200,
        1,
        False,
        1,
        1.0,
        True,
        1,
        0,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    )


def validate_generation_execution_policy_gate_v1(
    *, observed: ObservedGenerationExecutionPolicyV1,
) -> bytes:
    """Return a deterministic non-authorizing policy receipt."""
    if type(observed) is not ObservedGenerationExecutionPolicyV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_EXACT_TYPE_REQUIRED")
    if observed != canonical_observed_generation_execution_policy_v1():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_MISMATCH")
    value_observed = asdict(observed)
    value_observed["runner_identities"] = list(observed.runner_identities)
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-policy-gate-receipt",
        "schema_version": "1.0.0",
        "policy_gate_identity": POLICY_GATE_IDENTITY,
        "observed_policy_sha256": hashlib.sha256(_canonical(value_observed)).hexdigest(),
        "execution_reconciliation": "LOCAL_MODEL_EXECUTION_OLLAMA_REQUEST_PROVENANCE_ONLY",
        "result": "POLICY_VALIDATED_SOURCE_ONLY",
        "generation_started": False,
        "generation_authorized": False,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(
        _canonical({key: item for key, item in value.items() if key != "receipt_identity"})
    ).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "ObservedGenerationExecutionPolicyV1",
    "POLICY_GATE_IDENTITY",
    "canonical_observed_generation_execution_policy_v1",
    "validate_generation_execution_policy_gate_v1",
)
