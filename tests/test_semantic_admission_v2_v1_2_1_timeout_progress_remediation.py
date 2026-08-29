from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 as worker,
)
from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 as supervisor,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    parse_runner_request_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-exact-operations-bound"
COMPATIBILITY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-adapter-compatibility-validation-receipt-v1.json"
MODULES = (
    ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1.py",
    ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1.py",
    ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2_1.py",
    ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1.py",
)


def _progress():
    request = parse_runner_request_v1(
        raw_request=(PACKET / "runner-request.json").read_bytes())
    previous = None
    events = []
    for sequence, (event, detail) in enumerate((
        ("MODEL_LOAD_STARTED", {}),
        ("MODEL_LOAD_COMPLETED", {"compatibility_receipt_identity": worker.COMPATIBILITY_RECEIPT_IDENTITY}),
        ("GENERATION_STARTED", {"output_token_ceiling": 3200}),
    )):
        raw = worker._event(request.provider_request_id, sequence, event, detail, previous)
        previous = json.loads(raw)["event_identity"]
        events.append(("lifecycle", raw))
    events.insert(2, ("compatibility", COMPATIBILITY.read_bytes()))
    return request, tuple(events)


def test_timeout_preserves_observed_progress_and_chains_terminal_failure():
    request, progress = _progress()
    artifacts = dict(supervisor._reconcile_artifacts(
        request=request,
        child_result=None,
        failure_code="CHILD_TIMEOUT_TERMINATED",
        child_progress=progress,
    ))
    assert "adapter-compatibility-receipt.json" in artifacts
    assert [json.loads(artifacts[f"lifecycle-{index:05d}-{name}.json"])["event"] for index, name in (
        (1, "model_load_started"),
        (2, "model_load_completed"),
        (3, "generation_started"),
        (4, "execution-failed"),
    )] == ["MODEL_LOAD_STARTED", "MODEL_LOAD_COMPLETED", "GENERATION_STARTED", "EXECUTION_FAILED"]
    terminal = json.loads(artifacts["lifecycle-00004-execution-failed.json"])
    started = json.loads(artifacts["lifecycle-00003-generation_started.json"])
    assert terminal["sequence"] == 3
    assert terminal["previous_event_identity"] == started["event_identity"]
    assert terminal["failure_code"] == "CHILD_TIMEOUT_TERMINATED"
    assert json.loads(artifacts["cleanup-receipt-v1-1.json"])["cleanup_status"] == "CLEANUP_FAILED"


def test_progress_and_compatibility_mutations_fail_closed():
    request, progress = _progress()
    mutated = bytearray(progress[0][1]); mutated[-2] ^= 1
    with pytest.raises(ValueError, match="CHILD_PROGRESS"):
        supervisor._reconcile_artifacts(
            request=request, child_result=None, failure_code="CHILD_TIMEOUT_TERMINATED",
            child_progress=(("lifecycle", bytes(mutated)), *progress[1:]))
    with pytest.raises(ValueError, match="COMPATIBILITY"):
        supervisor._reconcile_artifacts(
            request=request, child_result=None, failure_code="CHILD_TIMEOUT_TERMINATED",
            child_progress=((*progress[:-1], ("compatibility", b"{}\n"))))


def test_timeout_remediation_import_surface_is_zero_execution():
    forbidden_calls = {"execute", "generate", "from_pretrained", "Popen", "run"}
    for path in MODULES:
        tree = ast.parse(path.read_text("utf-8"))
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        assert not (calls & forbidden_calls)
    assert not (PACKET.parent.parent / ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-v1-2-1-timeout-progress-bound-evidence").exists()
