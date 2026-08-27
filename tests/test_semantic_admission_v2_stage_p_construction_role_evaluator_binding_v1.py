from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_role_durable_executor_v1 import (
    DurableConstructionRoleStagePExecutorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_evaluator_v1 import (
    StagePConstructionRoleEvaluatorV1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_evaluator_binds_exact_executor_and_candidate_without_execution(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(DurableConstructionRoleStagePExecutorV1, "execute",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    executor = DurableConstructionRoleStagePExecutorV1(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    evaluator = StagePConstructionRoleEvaluatorV1(project_root=ROOT, executor=executor)
    request = {"candidate": "Raport literal.", "factual_summary": "Raport literal."}
    authority = evaluator.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    assert "\n\n".join(message.content for message in unit.messages) == evaluator.render_prompt(request)
    assert evaluator.candidate_identity == "46633da94538451e04643adf4f291bc30033749d8768e36c8a6be5eb13621734"
    assert evaluator.model_identity == "pastila-editor-core-v1.2-experimental"
    assert calls == []
