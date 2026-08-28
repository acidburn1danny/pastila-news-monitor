from __future__ import annotations

import hashlib
import json

import pytest

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_authority_preload_v1_2 as authority


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _receipt():
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.2.0", "authority_preload_identity": authority.AUTHORITY_PRELOAD_IDENTITY,
        "authority_contract_v1_identity": authority.AUTHORITY_CONTRACT_V1_IDENTITY,
        "policy_gate_identity": authority.POLICY_GATE_IDENTITY,
        "supervisor_identity": authority.SUPERVISOR_IDENTITY,
        "worker_identity": authority.WORKER_IDENTITY,
        "composition_identity": authority.LINUX_GENERATION_COMPOSITION_IDENTITY,
        "runner_identity": authority.LINUX_GENERATION_RUNNER_IDENTITY,
        "wsl_binding_identity": authority.GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        "host_executor_identity": authority.GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
        "wsl_profile_identity": authority.WSL_PROFILE_IDENTITY,
        "owner_authority_identity": "owner:test", "host_payload_sha256": "a" * 64,
        "runner_request_sha256": "b" * 64, "provider_request_id": "request",
        "source_context_identity": "c" * 64, "required_free_vram_mib": 14000,
        "attempt_ceiling": 1, "operation": "GENERATE_ONCE_STAGE_P_ONLY",
        "model_load_authorized": True, "generation_authorized": True,
        "prompt_token_ceiling": 8192, "output_token_ceiling": 3200,
        "retry_authorized": False, "fallback_authorized": False,
        "repair_authorized": False, "selection_authorized": False,
        "stage_c_authorized": False, "authority_receipt_identity": "",
    }
    value["authority_receipt_identity"] = hashlib.sha256(_canonical({k: v for k, v in value.items() if k != "authority_receipt_identity"})).hexdigest()
    return value


def test_v1_2_receipt_binds_exact_source_chain():
    value = _receipt()
    parsed = authority.parse_generation_authority_v1_2(
        raw_receipt=_canonical(value), expected_host_payload_sha256="a" * 64,
        expected_runner_request_sha256="b" * 64, expected_provider_request_id="request",
        expected_source_context_identity="c" * 64,
    )
    assert parsed.authority_receipt_identity == value["authority_receipt_identity"]


@pytest.mark.parametrize("field", ["composition_identity", "runner_identity", "wsl_binding_identity", "host_executor_identity"])
def test_rejects_each_legacy_or_mutated_source_identity(field):
    value = _receipt(); value[field] = "0" * 64
    value["authority_receipt_identity"] = hashlib.sha256(_canonical({k: v for k, v in value.items() if k != "authority_receipt_identity"})).hexdigest()
    with pytest.raises(ValueError, match="POLICY_OR_IDENTITY"):
        authority.parse_generation_authority_v1_2(
            raw_receipt=_canonical(value), expected_host_payload_sha256="a" * 64,
            expected_runner_request_sha256="b" * 64, expected_provider_request_id="request",
            expected_source_context_identity="c" * 64,
        )


def test_identity_derivation_is_deterministic():
    assert authority.AUTHORITY_PRELOAD_IDENTITY == hashlib.sha256(
        "\n".join(authority.AUTHORITY_PRELOAD_IDENTITY_FIELDS).encode()
    ).hexdigest()
