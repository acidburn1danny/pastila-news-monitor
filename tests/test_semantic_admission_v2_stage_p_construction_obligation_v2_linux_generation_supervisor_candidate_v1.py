from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_contract_v1 import (
    AUTHORITY_CONTRACT_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    POLICY_GATE_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1 import (
    supervise_injected_generation_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    InjectedCompatibleGenerationResourceV1, InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    SUPERVISOR_CANDIDATE_IDENTITY, InjectedChildProcessOperationsV1,
    InjectedDurableSinkV1, supervise_linux_generation_candidate_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import (
    PROJECTOR_FREEZE_IDENTITY,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-linux-generation-supervisor-candidate-v1.json"
SYSTEM_PROMPT = (ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt").read_text("utf-8")
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (  # noqa: E402
    COMPATIBILITY, _policy, _terminal_fixture,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import _fixture  # noqa: E402


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _authority(request):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.0.0", "authority_contract_identity": AUTHORITY_CONTRACT_IDENTITY,
        "policy_gate_identity": POLICY_GATE_IDENTITY,
        "runner_protocol_identity": "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf",
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "compatibility_receipt_identity": "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f",
        "generation_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
        "owner_authority_identity": "synthetic-supervisor-test",
        "host_payload_sha256": request.host_payload_sha256,
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


def _child_result():
    bound, text, generated = _terminal_fixture()
    return supervise_injected_generation_v1(
        raw_policy_receipt=_policy(),
        raw_authority_receipt=_worker_authority(bound),
        callback_preflight=bound, rendered_prompt="child prompt",
        operations=InjectedGenerationOperationsV1(
            lambda _: (1, 2),
            lambda: InjectedCompatibleGenerationResourceV1(
                object(), COMPATIBILITY.read_bytes()),
            lambda resource, prompt, maximum, allowed: (
                allowed((*prompt, *generated)) and
                InjectedGenerationOutputV1(text.encode(), (*generated, 2), True)
            ), lambda _: None))


def _worker_authority(bound):
    from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import _authority
    return _authority(bound)


@dataclass
class Handle:
    result: object
    alive: bool = False
    exit_code: int | None = 0


def _process(calls, result, *, initially_alive=False, survive_terminate=False):
    handle = Handle(result, initially_alive, None if initially_alive else 0)
    def start(invocation): calls.append(("start", invocation)); return handle
    def join(value, timeout): calls.append(("join", timeout))
    def terminate(value):
        calls.append("terminate")
        if not survive_terminate: value.alive = False; value.exit_code = -15
    def kill(value): calls.append("kill"); value.alive = False; value.exit_code = -9
    return InjectedChildProcessOperationsV1(
        start, join, lambda value: value.alive, terminate, kill,
        lambda value: value.exit_code, lambda value: value.result)


def test_success_starts_once_and_persists_exact_durable_bundle() -> None:
    raw, request = _fixture(); calls = []; persisted = {}
    outcome = supervise_linux_generation_candidate_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(request),
        raw_runner_request=raw, system_prompt=SYSTEM_PROMPT, timeout_seconds=900.0,
        child_operations=_process(calls, _child_result()),
        durable_sink=InjectedDurableSinkV1(
            lambda label, value: persisted.setdefault(label, value)))
    assert outcome.status == "TERMINAL_OUTPUT"
    assert len([item for item in calls if isinstance(item, tuple) and item[0] == "start"]) == 1
    assert "raw-output.bin" in persisted and "raw-partial-output.bin" not in persisted
    assert {"adapter-compatibility-receipt.json", "runner-result.json",
            "cleanup-receipt-v1-1.json", "result-envelope-v1-1.json",
            "supervisor-receipt.json"}.issubset(persisted)
    envelope = json.loads(persisted["result-envelope-v1-1.json"])
    assert envelope["partial_output_semantic_authority"] is False
    receipt = json.loads(outcome.supervisor_receipt)
    assert receipt["retry_count"] == 0 and receipt["timed_out"] is False


@pytest.mark.parametrize("mutation", ["policy", "authority", "request", "prompt", "timeout"])
def test_all_prestart_mismatches_fail_before_child_start(mutation) -> None:
    raw, request = _fixture(); calls = []
    values = {
        "raw_policy_receipt": _policy(), "raw_authority_receipt": _authority(request),
        "raw_runner_request": raw, "system_prompt": SYSTEM_PROMPT,
        "timeout_seconds": 900.0,
    }
    if mutation == "policy": values["raw_policy_receipt"] += b"x"
    elif mutation == "authority": values["raw_authority_receipt"] = b"{}\n"
    elif mutation == "request": values["raw_runner_request"] = b"{}\n"
    elif mutation == "prompt": values["system_prompt"] += "x"
    else: values["timeout_seconds"] = 0.0
    with pytest.raises((ValueError, TypeError)):
        supervise_linux_generation_candidate_v1(
            **values, child_operations=_process(calls, _child_result()),
            durable_sink=InjectedDurableSinkV1(lambda label, value: None))
    assert calls == []


@pytest.mark.parametrize("survive_terminate,expected", [(False, "TERMINATED"), (True, "KILLED")])
def test_timeout_terminates_then_kills_if_required_and_persists_failure(
    survive_terminate, expected,
) -> None:
    raw, request = _fixture(); calls = []; persisted = {}
    outcome = supervise_linux_generation_candidate_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(request),
        raw_runner_request=raw, system_prompt=SYSTEM_PROMPT, timeout_seconds=5.0,
        child_operations=_process(calls, None, initially_alive=True,
                                  survive_terminate=survive_terminate),
        durable_sink=InjectedDurableSinkV1(
            lambda label, value: persisted.setdefault(label, value)))
    receipt = json.loads(outcome.supervisor_receipt)
    assert outcome.status == "EXECUTION_FAILURE"
    assert receipt["timed_out"] is True and receipt["termination"] == expected
    assert calls.count("terminate") == 1
    assert calls.count("kill") == (1 if survive_terminate else 0)
    assert json.loads(persisted["runner-result.json"])["status"] == "EXECUTION_FAILURE"
    assert json.loads(persisted["cleanup-receipt-v1-1.json"])["cleanup_status"] == "CLEANUP_FAILED"


def test_persistence_failure_is_not_retried() -> None:
    raw, request = _fixture(); calls = []
    def persist(label, value): calls.append(label); raise OSError("synthetic")
    with pytest.raises(RuntimeError, match="DURABLE_PERSISTENCE_FAILED"):
        supervise_linux_generation_candidate_v1(
            raw_policy_receipt=_policy(), raw_authority_receipt=_authority(request),
            raw_runner_request=raw, system_prompt=SYSTEM_PROMPT,
            timeout_seconds=900.0, child_operations=_process([], _child_result()),
            durable_sink=InjectedDurableSinkV1(persist))
    assert len(calls) == 1


def test_identity_artifact_and_source_have_no_process_or_launch_surface() -> None:
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    ordered = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(ordered).encode()).hexdigest() == SUPERVISOR_CANDIDATE_IDENTITY
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "source_candidate_normalization")
    source = SOURCE.read_text("utf-8")
    assert all(term not in source for term in (
        "multiprocessing", "subprocess", "Popen", "wsl.exe", "from_pretrained",
        ".generate(", "if __name__", "build_invocation", ".execute(",
        "write_text", "write_bytes", "open(",
    ))
