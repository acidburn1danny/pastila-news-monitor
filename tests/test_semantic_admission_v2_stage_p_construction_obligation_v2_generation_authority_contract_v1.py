from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_contract_v1 import (
    AUTHORITY_CONTRACT_IDENTITY,
    parse_generation_authority_v1,
)


ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-authority-contract-v1.json")
CANDIDATE = "1" * 64
HOST = "2" * 64
REQUEST = "request-v1"
CONTEXT = "3" * 64


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _receipt():
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.0.0",
        "authority_contract_identity": AUTHORITY_CONTRACT_IDENTITY,
        "policy_gate_identity": "7a6e3629275e80d61b0af20d88393b158f2ac1154d6e9017f5bf3489f5d6b7d4",
        "runner_protocol_identity": "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf",
        "projector_freeze_identity": "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587",
        "compatibility_receipt_identity": "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f",
        "generation_candidate_identity": CANDIDATE,
        "owner_authority_identity": "synthetic-owner-v1",
        "host_payload_sha256": HOST,
        "provider_request_id": REQUEST,
        "source_context_identity": CONTEXT,
        "required_free_vram_mib": 14000,
        "attempt_ceiling": 1,
        "operation": "GENERATE_ONCE_STAGE_P_ONLY",
        "model_load_authorized": True,
        "generation_authorized": True,
        "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200,
        "retry_authorized": False,
        "fallback_authorized": False,
        "repair_authorized": False,
        "selection_authorized": False,
        "stage_c_authorized": False,
        "authority_receipt_identity": "",
    }
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    )).hexdigest()
    return value


def _parse(value):
    return parse_generation_authority_v1(
        raw_receipt=_canonical(value),
        expected_generation_candidate_identity=CANDIDATE,
        expected_host_payload_sha256=HOST,
        expected_provider_request_id=REQUEST,
        expected_source_context_identity=CONTEXT,
    )


def test_exact_synthetic_future_receipt_parses_without_issuing_authority() -> None:
    receipt = _receipt()
    parsed = _parse(receipt)
    assert parsed.generation_candidate_identity == CANDIDATE
    assert parsed.required_free_vram_mib == 14000
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    assert artifact["receipt_status"] == "UNISSUED"
    assert artifact["authority"]["authority_receipt_issued"] is False


@pytest.mark.parametrize("field", [
    "policy_gate_identity", "runner_protocol_identity", "projector_freeze_identity",
    "compatibility_receipt_identity", "attempt_ceiling", "operation",
    "model_load_authorized", "generation_authorized", "prompt_token_ceiling",
    "output_token_ceiling", "retry_authorized", "fallback_authorized",
    "repair_authorized", "selection_authorized", "stage_c_authorized",
    "generation_candidate_identity", "host_payload_sha256", "provider_request_id",
    "source_context_identity",
])
def test_every_policy_or_request_binding_mutation_fails_closed(field) -> None:
    value = deepcopy(_receipt())
    current = value[field]
    value[field] = not current if type(current) is bool else current + 1 if type(current) is int else current + "x"
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    )).hexdigest()
    with pytest.raises(ValueError):
        _parse(value)


def test_noncanonical_unsealed_and_malformed_receipts_fail_closed() -> None:
    value = _receipt()
    value["authority_receipt_identity"] = "0" * 64
    with pytest.raises(ValueError, match="SEAL_MISMATCH"):
        _parse(value)
    with pytest.raises(ValueError):
        parse_generation_authority_v1(
            raw_receipt=b"{}\n", expected_generation_candidate_identity=CANDIDATE,
            expected_host_payload_sha256=HOST, expected_provider_request_id=REQUEST,
            expected_source_context_identity=CONTEXT,
        )


def test_contract_artifact_identity_and_no_runtime_authority() -> None:
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == AUTHORITY_CONTRACT_IDENTITY
    assert artifact["canonical_identity"] == AUTHORITY_CONTRACT_IDENTITY
    assert artifact["authority"]["contract_normalization"] is True
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "contract_normalization")
