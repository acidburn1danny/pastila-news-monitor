from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_durable_executor_v1 import (
    DEPENDENCY_IDENTITIES, RUNNER_RELATIVE, RUNNER_SHA256,
    DurableConstructionObligationStagePExecutorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_evaluator_v1 import (
    StagePConstructionObligationEvaluatorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_incremental_tracker_v1 import (
    StagePConstructionObligationIncrementalTrackerV1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_runner_executor_and_dependencies_are_exactly_bound(tmp_path):
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    executor = DurableConstructionObligationStagePExecutorV1(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    assert executor._max_output_tokens == 3200


def test_dependency_drift_fails_before_launch(monkeypatch, tmp_path):
    monkeypatch.setitem(DEPENDENCY_IDENTITIES, Path("missing-obligation-dependency.py"), "0" * 64)
    with pytest.raises(RuntimeError, match="dependency identity drift"):
        DurableConstructionObligationStagePExecutorV1(
            project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")


def test_evaluator_and_request_construct_without_execution(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(DurableConstructionObligationStagePExecutorV1, "execute",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    executor = DurableConstructionObligationStagePExecutorV1(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    evaluator = StagePConstructionObligationEvaluatorV1(project_root=ROOT, executor=executor)
    request = {"candidate": "Raport literal.", "factual_summary": "Raport literal."}
    authority = evaluator.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    assert "\n\n".join(message.content for message in unit.messages) == evaluator.render_prompt(request)
    assert evaluator.candidate_identity == "e1dbb1f70e9e5c83e23b5e29dbf868d1a3ad7c01ebd4d6d2c82aaa192bb00f31"
    assert evaluator.constraint_identity == "sha256:a5db3847530e1208fbc96f5a4af6e577b248ec2507c9045280b648420d0ad935"
    assert calls == []


def test_tracker_uses_incremental_then_rebuild_paths():
    tracker = StagePConstructionObligationIncrementalTrackerV1()
    decode = lambda ids: "".join(chr(item) for item in ids)
    first = tracker.state_for([ord("{")], decode)
    second = tracker.state_for([ord("{")], decode)
    assert first.path == second.path == "INCREMENTAL"
    rebuilt = tracker.state_for([], decode)
    assert rebuilt.path == "FULL_REBUILD"
