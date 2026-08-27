from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_provider_identity_v1 import (
    MODEL_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_evaluator_v1 import (
    StagePRoleCoherenceEvaluatorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_evaluator_v2 import (
    StagePRoleCoherenceEvaluatorV2,
)


ROOT = Path(__file__).resolve().parents[1]
REQUEST = {"factual_summary": "Fapt verificabil.", "candidate": "Text candidat."}


class ForbiddenExecutor:
    def execute(self, _authority):  # pragma: no cover - invocation is the failure
        raise AssertionError("static evaluator verification must not execute")


def test_role_coherence_v1_static_binding_is_provider_neutral() -> None:
    evaluator = StagePRoleCoherenceEvaluatorV1(
        project_root=ROOT, executor=ForbiddenExecutor()
    )

    assert evaluator.model_identity == MODEL_IDENTITY
    assert evaluator.render_prompt(REQUEST)
    authority = evaluator.build_authority(
        REQUEST, requested_at=datetime(2026, 8, 27, tzinfo=UTC)
    )
    assert authority.context.request_id.startswith("application-request-v1:")
    assert authority.timeout_policy.timeout_seconds == 240.0


def test_role_coherence_v2_static_binding_is_provider_neutral() -> None:
    evaluator = StagePRoleCoherenceEvaluatorV2(
        project_root=ROOT, executor=ForbiddenExecutor()
    )

    assert evaluator.model_identity == MODEL_IDENTITY
    assert evaluator.render_prompt(REQUEST)
    authority = evaluator.build_authority(
        REQUEST, requested_at=datetime(2026, 8, 27, tzinfo=UTC)
    )
    assert authority.context.request_id.startswith("application-request-v1:")
    assert authority.timeout_policy.timeout_seconds == 240.0
