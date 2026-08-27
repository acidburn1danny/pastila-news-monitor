from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_provider_identity_v1 import MODEL_IDENTITY, STAGE_P_GRAMMAR_IDENTITY
from pastila_scout.semantic_admission_v2.stage_p_source_role_evaluator_v2 import StagePSourceRoleEvaluatorV2


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_source_role_evaluator_v2.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-prompt-v2-v4-binding-candidate.json"


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("source-role normalization invoked executor")


def test_source_role_identity_rebind_preserves_evaluator_identity_and_source_receipt() -> None:
    receipt = json.loads(ARTIFACT.read_bytes())
    evaluator = StagePSourceRoleEvaluatorV2(project_root=ROOT, executor=ForbiddenExecutor())
    binding = receipt["execution_binding"]
    assert evaluator.model_identity == binding["model_identity"] == MODEL_IDENTITY
    assert evaluator.grammar_identity == binding["grammar_identity"] == STAGE_P_GRAMMAR_IDENTITY
    assert evaluator.evaluator_identity == binding["evaluator_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == binding["evaluator_source_sha256"]


def test_authority_construction_is_exact_and_zero_call() -> None:
    executor = ForbiddenExecutor()
    evaluator = StagePSourceRoleEvaluatorV2(project_root=ROOT, executor=executor)
    request = {"factual_summary": "Autoritate sintetică exactă.", "candidate": "Comentariu sintetic exact."}
    prompt = evaluator.render_prompt(request)
    authority = evaluator.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    assert authority.request_intent.request_units[0].messages[0].content == prompt
    assert prompt == prompt.strip()
    assert len(authority.request_envelope.request_units) == 1
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert executor.calls == 0
    assert all(value is False for value in json.loads(ARTIFACT.read_bytes())["authority"].values())
