"""Evaluation-only evaluator for the approved Creative Target candidate."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import MODEL_ID
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .stage_p_creative_target_durable_executor_v1 import DurableCreativeTargetStagePExecutorV1
from .stage_p_creative_target_request_candidate_v1 import StagePCreativeTargetRequestCandidateV1


APPROVED_REQUEST_CANDIDATE_IDENTITY = "79b27bb6d7e35dfa9153cafb724e82d5689973b49605a9ea09a4b6462f01d9cc"
APPROVED_RUNNER_EXECUTOR_BINDING_IDENTITY = "c1fcd8ae5a9e95f08f09f6cc5f2d7c90c63eeebd7148b706885282514b35fa56"


class StagePCreativeTargetEvaluatorV1:
    def __init__(self, *, project_root: Path, executor: DurableCreativeTargetStagePExecutorV1,
                 timeout_seconds: float = 240.0) -> None:
        if type(executor) is not DurableCreativeTargetStagePExecutorV1:
            raise TypeError("Creative Target evaluator requires exact approved durable executor")
        self._executor = executor
        self._candidate = StagePCreativeTargetRequestCandidateV1(
            project_root=project_root, timeout_seconds=timeout_seconds)
        if self._candidate.candidate_identity != APPROVED_REQUEST_CANDIDATE_IDENTITY:
            raise RuntimeError("Creative Target request candidate identity drift")
        for name in ("candidate_identity", "prompt_identity", "schema_identity", "constraint_identity",
                     "grammar_identity", "tokenizer_identity"):
            setattr(self, name, getattr(self._candidate, name))
        self.model_identity = MODEL_ID
        parts = ["STAGE_P_CREATIVE_TARGET_EVALUATOR_V1", self.candidate_identity,
                 APPROVED_RUNNER_EXECUTOR_BINDING_IDENTITY, self.model_identity, str(timeout_seconds)]
        self.evaluator_identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        return self._candidate.render_prompt(request)

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        return self._candidate.build_authority(request, requested_at=requested_at)

    def __call__(self, request: dict[str, object]) -> str:
        result = self._executor.execute(self.build_authority(request, requested_at=datetime.now(UTC)))
        if (result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None or
                result.provider_result.status is not ProviderResultStatusV2.SUCCESS or
                len(result.provider_result.outputs) != 1 or
                result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("Creative Target Stage P evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__ = ("StagePCreativeTargetEvaluatorV1",)
