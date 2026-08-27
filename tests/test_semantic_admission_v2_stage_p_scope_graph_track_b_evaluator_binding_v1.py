from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_2 import (
    DurableScopeGraphStagePExecutorV1_2,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_track_b_evaluator_v1 import (
    APPROVED_TRACK_B_REQUEST_IDENTITY,
    StagePScopeGraphTrackBEvaluatorV1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence/stage-p-request.json"


def _bound(tmp_path, monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("execution forbidden in zero-inference binding")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    executor = DurableScopeGraphStagePExecutorV1_2(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    evaluator = StagePScopeGraphTrackBEvaluatorV1(project_root=ROOT, executor=executor)
    return evaluator, calls


def test_exact_evaluator_executor_binding_constructs_without_execution(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    assert evaluator.candidate_identity == APPROVED_TRACK_B_REQUEST_IDENTITY
    assert len(evaluator.evaluator_identity) == 64
    assert calls == []


def test_bound_request_preserves_exact_prompt_and_authority(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    request = json.loads(CASE.read_text("utf-8"))
    authority = evaluator.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    assert "\n\n".join(message.content for message in unit.messages) == evaluator.render_prompt(request)
    assert request["candidate"] in evaluator.render_prompt(request)
    assert request["factual_summary"] in evaluator.render_prompt(request)
    assert calls == []


def test_evaluator_rejects_any_nonexact_executor():
    with pytest.raises(TypeError, match="exact Track-A executor"):
        StagePScopeGraphTrackBEvaluatorV1(project_root=ROOT, executor=object())


def test_case01_is_not_called_by_binding(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    assert callable(evaluator)
    assert calls == []
