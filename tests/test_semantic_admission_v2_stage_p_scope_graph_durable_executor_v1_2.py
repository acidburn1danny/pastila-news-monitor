from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_2 import (
    DEPENDENCY_IDENTITIES,
    RUNNER_RELATIVE,
    RUNNER_SHA256,
    DurableScopeGraphStagePExecutorV1_2,
    read_constraint_liveness_failure_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _detail():
    return {"code": "CONSTRAINT_LIVENESS_FAILURE", "decoded_utf8_bytes": 1045,
            "decoded_sha256": "d" * 64, "dfa_mode": "CHOICE", "dfa_next_step": "COVERAGE_END",
            "entry_count": 1}


def test_runner_and_dependency_identities_are_exact():
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_liveness_exception_is_parsed_as_a_distinct_hashed_receipt(tmp_path):
    events = AppendOnlyLifecycleV1(tmp_path, actor="runner")
    events.emit("RUNNER_EXCEPTION", exception_type="StagePConstraintLivenessErrorV1",
                exception_message=json.dumps(_detail(), sort_keys=True, separators=(",", ":")))
    receipt = read_constraint_liveness_failure_v1(tmp_path)
    assert receipt is not None
    assert receipt.as_json_value() == _detail()


def test_transport_exception_is_not_misclassified_as_liveness(tmp_path):
    events = AppendOnlyLifecycleV1(tmp_path, actor="runner")
    events.emit("RUNNER_EXCEPTION", exception_type="OSError", exception_message="transport")
    assert read_constraint_liveness_failure_v1(tmp_path) is None


def test_malformed_liveness_receipt_fails_closed(tmp_path):
    events = AppendOnlyLifecycleV1(tmp_path, actor="runner")
    detail = _detail(); detail["decoded_sha256"] = "short"
    events.emit("RUNNER_EXCEPTION", exception_type="StagePConstraintLivenessErrorV1",
                exception_message=json.dumps(detail))
    with pytest.raises(ValueError, match="CONSTRAINT_LIVENESS_RECEIPT_INVALID"):
        read_constraint_liveness_failure_v1(tmp_path)


def test_executor_construction_verifies_binding_without_launch(tmp_path, monkeypatch):
    called = False
    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess launch forbidden")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    executor = DurableScopeGraphStagePExecutorV1_2(project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    assert executor is not None and called is False


def test_executor_source_persists_distinct_host_classification():
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_2.py").read_text("utf-8")
    assert 'events.emit("HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED", **value)' in source
    assert 'trace["failure_classification"] = value' in source
    assert "StagePConstraintLivenessExecutionErrorV1(liveness)" in source
