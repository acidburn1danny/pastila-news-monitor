from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_3 import (
    DurableScopeGraphStagePExecutorV1_3,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_track_b_evaluator_v1_1 import (
    APPROVED_TRACK_B_REQUEST_IDENTITY,
    StagePScopeGraphTrackBEvaluatorV1_1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence/stage-p-request.json"


def _bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("execution forbidden during zero-inference rebinding")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    executor = DurableScopeGraphStagePExecutorV1_3(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    return StagePScopeGraphTrackBEvaluatorV1_1(project_root=ROOT, executor=executor), calls


def test_exact_rebinding_constructs_without_execution(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    assert evaluator.candidate_identity == APPROVED_TRACK_B_REQUEST_IDENTITY
    assert len(evaluator.evaluator_identity) == 64
    assert calls == []


def test_request_render_and_application_authority_are_preserved(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    request = json.loads(CASE.read_text("utf-8"))
    authority = evaluator.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    rendered = evaluator.render_prompt(request)
    assert "\n\n".join(message.content for message in authority.request_envelope.request_units[0].messages) == rendered
    assert request["candidate"] in rendered and request["factual_summary"] in rendered
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert calls == []


def test_old_or_nonexact_executor_is_rejected():
    with pytest.raises(TypeError, match="exact approved V1.3"):
        StagePScopeGraphTrackBEvaluatorV1_1(project_root=ROOT, executor=object())


def test_case01_remains_unexecuted(tmp_path, monkeypatch):
    evaluator, calls = _bound(tmp_path, monkeypatch)
    assert callable(evaluator) and calls == []
