"""Non-executing V1.2.1 generation-authority identity admission.

This successor changes only source-binding identities. Capacity and execution
policy remain exactly those of V1.1; importing the module grants no authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    AUTHORITY_CONTRACT_V1_IDENTITY,
    PACKAGE_IDENTITIES,
    POLICY_GATE_IDENTITY,
    WSL_PROFILE_IDENTITY,
    GenerationPreloadObservationV1_1,
)
from .stage_p_construction_obligation_v2_generation_v1_2_1_identity_contract import (
    COMPOSITION_IDENTITY as LINUX_GENERATION_COMPOSITION_IDENTITY,
    HOST_EXECUTOR_IDENTITY as GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
    RUNNER_IDENTITY as LINUX_GENERATION_RUNNER_IDENTITY,
    SUPERVISOR_IDENTITY,
    WORKER_IDENTITY,
    WSL_BINDING_IDENTITY as GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
)

AUTHORITY_PRELOAD_IDENTITY_FIELDS = (
    "construction-obligation-v2-generation-authority-preload-v1.2.1",
    "composition:" + LINUX_GENERATION_COMPOSITION_IDENTITY,
    "runner:" + LINUX_GENERATION_RUNNER_IDENTITY,
    "wsl-binding:" + GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
    "host-executor:" + GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
    "policy:v1.1-byte-equivalent",
)
AUTHORITY_PRELOAD_IDENTITY = hashlib.sha256(
    "\n".join(AUTHORITY_PRELOAD_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class GenerationAuthorityV1_2:
    owner_authority_identity: str
    host_payload_sha256: str
    runner_request_sha256: str
    provider_request_id: str
    source_context_identity: str
    packet_plan_identity: str
    command_plan_identity: str
    required_free_vram_mib: int
    authority_receipt_identity: str


def validate_generation_preload_v1_2_1(
    *, authority: GenerationAuthorityV1_2,
    observed: GenerationPreloadObservationV1_1,
) -> bytes:
    """Preserve the exact V1.1 capacity policy under V1.2.1 authority identity."""
    if type(authority) is not GenerationAuthorityV1_2:
        raise TypeError("GENERATION_AUTHORITY_V1_2_EXACT_TYPE_REQUIRED")
    if type(observed) is not GenerationPreloadObservationV1_1:
        raise TypeError("GENERATION_PRELOAD_V1_1_EXACT_TYPE_REQUIRED")
    expected = GenerationPreloadObservationV1_1(
        PACKAGE_IDENTITIES,
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        "NVIDIA GeForce RTX 5080", 16303, observed.vram_free_mib, "12.0", 0,
        "NF4_4BIT", True, "BF16",
    )
    if observed != expected or type(observed.vram_free_mib) is not int:
        raise ValueError("GENERATION_PRELOAD_V1_2_ENVIRONMENT_MISMATCH")
    if observed.vram_free_mib < authority.required_free_vram_mib:
        raise ValueError("GENERATION_PRELOAD_V1_2_INSUFFICIENT_FREE_VRAM")
    observation = asdict(observed)
    observation["package_identities"] = list(observed.package_identities)
    value = {
        "schema_name": "pastila-semantic-admission-v2-generation-preload-admission",
        "schema_version": "1.2.1",
        "authority_preload_identity": AUTHORITY_PRELOAD_IDENTITY,
        "authority_receipt_identity": authority.authority_receipt_identity,
        "observation_sha256": hashlib.sha256(_canonical(observation)).hexdigest(),
        "admission": "MODEL_LOAD_START_ADMITTED", "model_load_started": False,
        "generation_started": False, "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical({
        key: item for key, item in value.items() if key != "receipt_identity"
    })).hexdigest()
    return _canonical(value)


def parse_generation_authority_v1_2_1(
    *, raw_receipt: bytes, expected_host_payload_sha256: str,
    expected_runner_request_sha256: str, expected_provider_request_id: str,
    expected_source_context_identity: str,
    expected_packet_plan_identity: str | None = None,
    expected_command_plan_identity: str | None = None,
) -> GenerationAuthorityV1_2:
    try:
        value = json.loads(raw_receipt.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("GENERATION_AUTHORITY_V1_2_JSON_INVALID") from exc
    required = {
        "schema_name", "schema_version", "authority_preload_identity",
        "authority_contract_v1_identity", "policy_gate_identity",
        "supervisor_identity", "worker_identity", "composition_identity",
        "runner_identity", "wsl_binding_identity", "host_executor_identity",
        "wsl_profile_identity", "owner_authority_identity", "host_payload_sha256",
        "runner_request_sha256", "provider_request_id", "source_context_identity",
        "packet_plan_identity", "command_plan_identity",
        "required_free_vram_mib", "attempt_ceiling", "operation",
        "model_load_authorized", "generation_authorized", "prompt_token_ceiling",
        "output_token_ceiling", "retry_authorized", "fallback_authorized",
        "repair_authorized", "selection_authorized", "stage_c_authorized",
        "authority_receipt_identity",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("GENERATION_AUTHORITY_V1_2_SHAPE_MISMATCH")
    expected_fixed = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.2.1", "authority_preload_identity": AUTHORITY_PRELOAD_IDENTITY,
        "authority_contract_v1_identity": AUTHORITY_CONTRACT_V1_IDENTITY,
        "policy_gate_identity": POLICY_GATE_IDENTITY, "supervisor_identity": SUPERVISOR_IDENTITY,
        "worker_identity": WORKER_IDENTITY, "composition_identity": LINUX_GENERATION_COMPOSITION_IDENTITY,
        "runner_identity": LINUX_GENERATION_RUNNER_IDENTITY,
        "wsl_binding_identity": GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        "host_executor_identity": GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
        "wsl_profile_identity": WSL_PROFILE_IDENTITY, "required_free_vram_mib": 14000,
        "attempt_ceiling": 1, "operation": "GENERATE_ONCE_STAGE_P_ONLY",
        "model_load_authorized": True, "generation_authorized": True,
        "prompt_token_ceiling": 8192, "output_token_ceiling": 3200,
        "retry_authorized": False, "fallback_authorized": False,
        "repair_authorized": False, "selection_authorized": False,
        "stage_c_authorized": False,
    }
    if any(value[key] != item for key, item in expected_fixed.items()):
        raise ValueError("GENERATION_AUTHORITY_V1_2_POLICY_OR_IDENTITY_MISMATCH")
    bound = {
        "host_payload_sha256": expected_host_payload_sha256,
        "runner_request_sha256": expected_runner_request_sha256,
        "provider_request_id": expected_provider_request_id,
        "source_context_identity": expected_source_context_identity,
    }
    if any(value[key] != item for key, item in bound.items()):
        raise ValueError("GENERATION_AUTHORITY_V1_2_REQUEST_BINDING_MISMATCH")
    if (expected_packet_plan_identity is not None
            and value["packet_plan_identity"] != expected_packet_plan_identity):
        raise ValueError("GENERATION_AUTHORITY_V1_2_PACKET_PLAN_MISMATCH")
    if (expected_command_plan_identity is not None
            and value["command_plan_identity"] != expected_command_plan_identity):
        raise ValueError("GENERATION_AUTHORITY_V1_2_COMMAND_PLAN_MISMATCH")
    if any(type(value[key]) is not str or not value[key] for key in (
            "owner_authority_identity", *bound, "packet_plan_identity",
            "command_plan_identity")):
        raise ValueError("GENERATION_AUTHORITY_V1_2_BINDING_INVALID")
    if any(len(value[key]) != 64 or any(c not in "0123456789abcdef" for c in value[key])
           for key in ("packet_plan_identity", "command_plan_identity")):
        raise ValueError("GENERATION_AUTHORITY_V1_2_PLAN_IDENTITY_INVALID")
    body = {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    identity = hashlib.sha256(_canonical(body)).hexdigest()
    if value["authority_receipt_identity"] != identity or raw_receipt != _canonical(value):
        raise ValueError("GENERATION_AUTHORITY_V1_2_SEAL_MISMATCH")
    return GenerationAuthorityV1_2(
        value["owner_authority_identity"], value["host_payload_sha256"],
        value["runner_request_sha256"], value["provider_request_id"],
        value["source_context_identity"], value["packet_plan_identity"],
        value["command_plan_identity"], value["required_free_vram_mib"], identity,
    )


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "AUTHORITY_PRELOAD_IDENTITY", "AUTHORITY_PRELOAD_IDENTITY_FIELDS",
    "GenerationAuthorityV1_2", "GenerationPreloadObservationV1_1",
    "PACKAGE_IDENTITIES", "parse_generation_authority_v1_2_1",
    "validate_generation_preload_v1_2_1",
)
