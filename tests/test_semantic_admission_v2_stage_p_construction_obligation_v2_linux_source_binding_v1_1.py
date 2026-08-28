from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    _policy,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    _observation,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_child_process_adapter_v1 import (
    FakeContext,
    FakeQueue,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    SYSTEM_PROMPT,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    _fixture,
)

import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_child_process_adapter_v1_1 as adapter
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_child_process_adapter_v1_1 import (
    LINUX_CHILD_PROCESS_ADAPTER_IDENTITY,
    build_linux_child_process_operations_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_composition_v1_1 import (
    LINUX_GENERATION_COMPOSITION_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_1 import (
    LinuxGenerationChildInvocationV1,
)


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _authority(raw_request, request):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.1.0",
        "authority_preload_identity": "54a5cfc079c0cde964328d9cd03033411b9b50c79b13683ad348ebfc0b93d0d1",
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
        "runner_request_sha256": hashlib.sha256(raw_request).hexdigest(),
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


def _inputs():
    raw_request, request = _fixture()
    raw_authority = _authority(raw_request, request)
    invocation = LinuxGenerationChildInvocationV1(
        raw_request, SYSTEM_PROMPT, json.loads(raw_authority)["authority_receipt_identity"])
    return raw_request, raw_authority, invocation


def test_process_construction_is_deferred_and_bound_to_v1_1_target() -> None:
    _, raw_authority, invocation = _inputs()
    context = FakeContext()
    operations = build_linux_child_process_operations_v1_1(
        raw_policy_receipt=_policy(), raw_authority_receipt=raw_authority,
        context_factory=lambda method: context)
    assert context.processes == []
    operations.start(invocation)
    assert len(context.processes) == 1
    assert context.processes[0].target is adapter._run_linux_generation_child_v1_1


def test_child_observes_before_prepare_and_propagates_exact_observation(monkeypatch) -> None:
    _, raw_authority, invocation = _inputs()
    trace = []
    request = SimpleNamespace(
        host_payload=b"host", host_payload_sha256=json.loads(raw_authority)["host_payload_sha256"],
        provider_request_id=json.loads(raw_authority)["provider_request_id"],
        source_context_identity=json.loads(raw_authority)["source_context_identity"])
    host = SimpleNamespace(rendered_prompt="rendered")
    prepared = SimpleNamespace(token_piece_bundle="pieces", operations="runtime")
    callback = SimpleNamespace(projector_preflight=SimpleNamespace(
        preflight=SimpleNamespace(request=request)))
    result = adapter.InjectedGenerationSupervisorResultV1(
        "EXECUTION_FAILURE", (), b"result", None, None, None, b"cleanup")
    monkeypatch.setattr(adapter, "parse_runner_request_v1", lambda **_: request)
    monkeypatch.setattr(adapter, "parse_construction_obligation_v2_host_wsl_payload_v1",
                        lambda **_: host)
    monkeypatch.setattr(adapter, "observe_linux_generation_preload_v1_1",
                        lambda **_: trace.append("observe") or _observation(15000))
    monkeypatch.setattr(adapter, "prepare_linux_runtime_operations_v1",
                        lambda **_: trace.append("prepare") or prepared)
    monkeypatch.setattr(adapter, "ConstructionObligationV2RunnerPreflightV1_1",
                        lambda *args: "base")
    monkeypatch.setattr(adapter, "bind_static_projector_preflight_v1_2",
                        lambda **_: "projector")
    monkeypatch.setattr(adapter, "bind_static_callback_preflight_v1_3",
                        lambda **_: callback)
    monkeypatch.setattr(adapter, "adapt_runtime_operations_v1_1",
                        lambda **_: "operations")
    monkeypatch.setattr(adapter, "supervise_injected_generation_v1_1",
                        lambda **kwargs: trace.append(("supervise", kwargs)) or result)
    queue = FakeQueue(maxsize=1)
    adapter._run_linux_generation_child_v1_1(
        invocation=invocation, raw_policy_receipt=_policy(),
        raw_authority_receipt=raw_authority, result_queue=queue)
    assert trace[:2] == ["observe", "prepare"]
    assert trace[-1][1]["preload_observation"].vram_free_mib == 15000
    assert queue.values == [result]


def test_new_source_identities_are_separate_and_import_is_nonexecuting() -> None:
    assert LINUX_CHILD_PROCESS_ADAPTER_IDENTITY == "e166f63ceafc21828c7191f57e43ffbfd2befa04fed6bcb12ee8b164432fc4be"
    assert LINUX_GENERATION_COMPOSITION_IDENTITY == "c52b5126add3f7975e3e630a618db81549dc74aeea2ab0b6756b6e0d8582e183"
    assert Path(__file__).exists()
