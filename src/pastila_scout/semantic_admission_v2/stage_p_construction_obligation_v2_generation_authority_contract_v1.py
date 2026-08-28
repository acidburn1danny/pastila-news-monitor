"""Unissued one-shot generation authority contract for Construction-Obligation V2."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


AUTHORITY_CONTRACT_IDENTITY = "d37a8a7ad5f0fed905654e74cb6111570b1abf19ac0629a3b3eee5ed5fa84844"
POLICY_GATE_IDENTITY = "7a6e3629275e80d61b0af20d88393b158f2ac1154d6e9017f5bf3489f5d6b7d4"
RUNNER_PROTOCOL_IDENTITY = "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf"
PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
COMPATIBILITY_RECEIPT_IDENTITY = "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f"


@dataclass(frozen=True, slots=True)
class GenerationAuthorityV1:
    generation_candidate_identity: str
    owner_authority_identity: str
    host_payload_sha256: str
    provider_request_id: str
    source_context_identity: str
    required_free_vram_mib: int
    authority_receipt_identity: str


def parse_generation_authority_v1(
    *, raw_receipt: bytes, expected_generation_candidate_identity: str,
    expected_host_payload_sha256: str, expected_provider_request_id: str,
    expected_source_context_identity: str,
) -> GenerationAuthorityV1:
    """Validate an explicitly issued future receipt; this module issues none."""
    value = _object(raw_receipt)
    required = {
        "schema_name", "schema_version", "authority_contract_identity",
        "policy_gate_identity", "runner_protocol_identity", "projector_freeze_identity",
        "compatibility_receipt_identity", "generation_candidate_identity",
        "owner_authority_identity", "host_payload_sha256", "provider_request_id",
        "source_context_identity", "required_free_vram_mib", "attempt_ceiling",
        "operation", "model_load_authorized", "generation_authorized",
        "prompt_token_ceiling", "output_token_ceiling", "retry_authorized",
        "fallback_authorized", "repair_authorized", "selection_authorized",
        "stage_c_authorized", "authority_receipt_identity",
    }
    if set(value) != required:
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_SHAPE_MISMATCH")
    fixed = (
        value["schema_name"], value["schema_version"],
        value["authority_contract_identity"], value["policy_gate_identity"],
        value["runner_protocol_identity"], value["projector_freeze_identity"],
        value["compatibility_receipt_identity"], value["attempt_ceiling"],
        value["operation"], value["model_load_authorized"],
        value["generation_authorized"], value["prompt_token_ceiling"],
        value["output_token_ceiling"], value["retry_authorized"],
        value["fallback_authorized"], value["repair_authorized"],
        value["selection_authorized"], value["stage_c_authorized"],
    )
    expected = (
        "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "1.0.0", AUTHORITY_CONTRACT_IDENTITY, POLICY_GATE_IDENTITY,
        RUNNER_PROTOCOL_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
        COMPATIBILITY_RECEIPT_IDENTITY, 1, "GENERATE_ONCE_STAGE_P_ONLY",
        True, True, 8192, 3200, False, False, False, False, False,
    )
    bound = (
        value["generation_candidate_identity"], value["host_payload_sha256"],
        value["provider_request_id"], value["source_context_identity"],
    )
    expected_bound = (
        expected_generation_candidate_identity, expected_host_payload_sha256,
        expected_provider_request_id, expected_source_context_identity,
    )
    if fixed != expected or bound != expected_bound:
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_POLICY_OR_BINDING_MISMATCH")
    if any(type(item) is not str or not item for item in (
        value["owner_authority_identity"], *bound)):
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_BINDING_INVALID")
    if any(len(item) != 64 or any(char not in "0123456789abcdef" for char in item)
           for item in (value["host_payload_sha256"], value["source_context_identity"])):
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_HASH_INVALID")
    if type(value["required_free_vram_mib"]) is not int or value["required_free_vram_mib"] <= 0:
        raise ValueError("GENERATION_AUTHORITY_CAPACITY_INVALID")
    identity = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    )).hexdigest()
    if value["authority_receipt_identity"] != identity or raw_receipt != _canonical(value):
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_SEAL_MISMATCH")
    return GenerationAuthorityV1(
        value["generation_candidate_identity"], value["owner_authority_identity"],
        value["host_payload_sha256"], value["provider_request_id"],
        value["source_context_identity"], value["required_free_vram_mib"], identity,
    )


def _object(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes or not raw:
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_JSON_INVALID") from exc
    if type(value) is not dict:
        raise ValueError("GENERATION_AUTHORITY_RECEIPT_SHAPE_INVALID")
    return value


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "AUTHORITY_CONTRACT_IDENTITY", "GenerationAuthorityV1",
    "parse_generation_authority_v1",
)
