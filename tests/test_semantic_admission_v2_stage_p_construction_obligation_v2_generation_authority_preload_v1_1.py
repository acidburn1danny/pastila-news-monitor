from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    AUTHORITY_PRELOAD_IDENTITY,
    GenerationPreloadObservationV1_1,
    admit_generation_start_v1_1,
    parse_generation_authority_v1_1,
    validate_generation_preload_v1_1,
)

ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-authority-preload-v1-1.json")
HOST, RUNNER, CONTEXT = "1" * 64, "2" * 64, "3" * 64


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _receipt():
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.1.0", "authority_preload_identity": AUTHORITY_PRELOAD_IDENTITY,
        "authority_contract_v1_identity": "d37a8a7ad5f0fed905654e74cb6111570b1abf19ac0629a3b3eee5ed5fa84844",
        "policy_gate_identity": "7a6e3629275e80d61b0af20d88393b158f2ac1154d6e9017f5bf3489f5d6b7d4",
        "supervisor_identity": "ce43ed32836005bcd471da40f9003e3d9ba66e090e57fbf66cdf77d0c8b95391",
        "worker_identity": "8f2b6e445375d2295583ee3eeec6c643dec57bb5f711bdcf2b12abf310e03489",
        "composition_identity": "c52b5126add3f7975e3e630a618db81549dc74aeea2ab0b6756b6e0d8582e183",
        "runner_identity": "ed9303593dea53b9375913e3cb1640cdb11f2e347299435532f7e3935bf755da",
        "wsl_binding_identity": "c7a09557517e2a762d1d60738bc2c073be458533769bd0a968f25930fe3b6843",
        "host_executor_identity": "7749b2b075c7db788927130505edbaafa1c7cfbd398b1132b01b396f94d97942",
        "wsl_profile_identity": "71f66b8bf20b3decb31cfe65d3d94720f9fd1d2c6500c9ef259197cbf94bc7f4",
        "owner_authority_identity": "synthetic-owner", "host_payload_sha256": HOST,
        "runner_request_sha256": RUNNER, "provider_request_id": "synthetic-request",
        "source_context_identity": CONTEXT, "required_free_vram_mib": 14000,
        "attempt_ceiling": 1, "operation": "GENERATE_ONCE_STAGE_P_ONLY",
        "model_load_authorized": True, "generation_authorized": True,
        "prompt_token_ceiling": 8192, "output_token_ceiling": 3200,
        "retry_authorized": False, "fallback_authorized": False,
        "repair_authorized": False, "selection_authorized": False,
        "stage_c_authorized": False, "authority_receipt_identity": "",
    }
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {k: v for k, v in value.items() if k != "authority_receipt_identity"})).hexdigest()
    return value


def _parse(value=None):
    return parse_generation_authority_v1_1(
        raw_receipt=_canonical(value or _receipt()), expected_host_payload_sha256=HOST,
        expected_runner_request_sha256=RUNNER, expected_provider_request_id="synthetic-request",
        expected_source_context_identity=CONTEXT,
    )


def _observation(free=14000):
    return GenerationPreloadObservationV1_1(
        ("transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
         "accelerate==1.14.0", "bitsandbytes==0.50.1"),
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        "NVIDIA GeForce RTX 5080", 16303, free, "12.0", 0, "NF4_4BIT", True, "BF16")


def test_dual_role_receipt_and_preload_admission_are_canonical() -> None:
    authority = _parse()
    receipt = json.loads(validate_generation_preload_v1_1(
        authority=authority, observed=_observation()))
    assert receipt["admission"] == "MODEL_LOAD_START_ADMITTED"
    assert receipt["model_load_started"] is False


@pytest.mark.parametrize("field", ["supervisor_identity", "worker_identity", "composition_identity",
                                    "runner_identity", "wsl_binding_identity", "host_executor_identity",
                                    "wsl_profile_identity", "required_free_vram_mib"])
def test_every_remediated_binding_mutation_fails_closed(field) -> None:
    value = deepcopy(_receipt())
    value[field] = value[field] + "x" if isinstance(value[field], str) else 13999
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {k: v for k, v in value.items() if k != "authority_receipt_identity"})).hexdigest()
    with pytest.raises(ValueError, match="POLICY_OR_BINDING_MISMATCH"):
        _parse(value)


def test_free_vram_and_environment_fail_before_start_callback() -> None:
    calls = []
    with pytest.raises(ValueError, match="INSUFFICIENT_FREE_VRAM"):
        admit_generation_start_v1_1(
            authority=_parse(), observed=_observation(13999), start=lambda: calls.append(True))
    assert calls == []
    bad = deepcopy(_observation())
    object.__setattr__(bad, "cuda_device", 1)
    with pytest.raises(ValueError, match="ENVIRONMENT_MISMATCH"):
        admit_generation_start_v1_1(
            authority=_parse(), observed=bad, start=lambda: calls.append(True))
    assert calls == []


def test_valid_admission_precedes_exactly_one_injected_start() -> None:
    calls = []
    admission, result = admit_generation_start_v1_1(
        authority=_parse(), observed=_observation(15000),
        start=lambda: calls.append("started") or "result")
    assert json.loads(admission)["model_load_started"] is False
    assert result == "result" and calls == ["started"]


def test_freeze_identity_and_no_execution_authority() -> None:
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == AUTHORITY_PRELOAD_IDENTITY
    assert artifact["canonical_identity"] == AUTHORITY_PRELOAD_IDENTITY
    assert not any(artifact["authority"].values())
