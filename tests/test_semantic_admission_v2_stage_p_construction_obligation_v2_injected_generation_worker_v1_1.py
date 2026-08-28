from __future__ import annotations

import hashlib
import json

import pytest
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    COMPATIBILITY,
    _policy,
    _terminal_fixture,
)

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    AUTHORITY_PRELOAD_IDENTITY,
    GenerationPreloadObservationV1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
    execute_injected_generation_worker_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    EOS_TOKEN_ID,
)

RUNNER_REQUEST_SHA256 = "4" * 64


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _authority(bound):
    request = bound.projector_preflight.preflight.request
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
        "owner_authority_identity": "synthetic-owner", "host_payload_sha256": request.host_payload_sha256,
        "runner_request_sha256": RUNNER_REQUEST_SHA256,
        "provider_request_id": request.provider_request_id,
        "source_context_identity": request.source_context_identity,
        "required_free_vram_mib": 14000, "attempt_ceiling": 1,
        "operation": "GENERATE_ONCE_STAGE_P_ONLY", "model_load_authorized": True,
        "generation_authorized": True, "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200, "retry_authorized": False,
        "fallback_authorized": False, "repair_authorized": False,
        "selection_authorized": False, "stage_c_authorized": False,
        "authority_receipt_identity": "",
    }
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def _observation(free):
    return GenerationPreloadObservationV1_1(
        ("transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
         "accelerate==1.14.0", "bitsandbytes==0.50.1"),
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        "NVIDIA GeForce RTX 5080", 16303, free, "12.0", 0, "NF4_4BIT", True, "BF16")


def test_capacity_failure_precedes_tokenize_event_and_model_load() -> None:
    bound, _, _ = _terminal_fixture()
    calls = []
    with pytest.raises(ValueError, match="INSUFFICIENT_FREE_VRAM"):
        execute_injected_generation_worker_v1_1(
            raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
            expected_runner_request_sha256=RUNNER_REQUEST_SHA256,
            preload_observation=_observation(13999), callback_preflight=bound,
            rendered_prompt="synthetic", operations=InjectedGenerationOperationsV1(
                lambda _: calls.append("tokenize"), lambda: calls.append("load"),
                lambda *args: calls.append("generate"), lambda _: calls.append("cleanup")))
    assert calls == []


def test_valid_preload_allows_exactly_one_injected_load_and_generation() -> None:
    bound, text, generated = _terminal_fixture()
    calls = []

    def generate(resource, prompt_ids, maximum, allowed):
        calls.append("generate")
        assert allowed((*prompt_ids, *generated)) == (EOS_TOKEN_ID,)
        return InjectedGenerationOutputV1(text.encode(), (*generated, EOS_TOKEN_ID), True)

    resource = object()
    result = execute_injected_generation_worker_v1_1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        expected_runner_request_sha256=RUNNER_REQUEST_SHA256,
        preload_observation=_observation(15000), callback_preflight=bound,
        rendered_prompt="synthetic", operations=InjectedGenerationOperationsV1(
            lambda _: (1, 2),
            lambda: calls.append("load") or InjectedCompatibleGenerationResourceV1(
                resource, COMPATIBILITY.read_bytes()),
            generate, lambda _: calls.append("cleanup")))
    assert result.status == "TERMINAL_OUTPUT"
    assert calls == ["load", "generate", "cleanup"]
    assert json.loads(result.events[0])["event"] == "MODEL_LOAD_STARTED"
