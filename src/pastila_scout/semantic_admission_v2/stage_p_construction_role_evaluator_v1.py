"""Evaluation-only evaluator for the approved Construction Role Audit candidate."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import MODEL_ID
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .stage_p_construction_role_durable_executor_v1 import DurableConstructionRoleStagePExecutorV1
from .stage_p_construction_role_request_candidate_v1 import StagePConstructionRoleRequestCandidateV1


APPROVED_REQUEST_CANDIDATE_IDENTITY = "46633da94538451e04643adf4f291bc30033749d8768e36c8a6be5eb13621734"
APPROVED_RUNNER_EXECUTOR_BINDING_IDENTITY = "142e61df3c38c88011c2437f2c430c59263e74cb258e43d535ee2ebad552c72c"


class StagePConstructionRoleEvaluatorV1:
    def __init__(self, *, project_root: Path, executor: DurableConstructionRoleStagePExecutorV1,
                 timeout_seconds: float = 240.0) -> None:
        if type(executor) is not DurableConstructionRoleStagePExecutorV1:
            raise TypeError("Construction Role evaluator requires exact approved durable executor")
        self._executor = executor
        self._candidate = StagePConstructionRoleRequestCandidateV1(
            project_root=project_root, timeout_seconds=timeout_seconds)
        if self._candidate.candidate_identity != APPROVED_REQUEST_CANDIDATE_IDENTITY:
            raise RuntimeError("Construction Role request candidate identity drift")
        for name in ("candidate_identity", "prompt_identity", "schema_identity", "constraint_identity",
                     "grammar_identity", "tokenizer_identity"):
            setattr(self, name, getattr(self._candidate, name))
        self.model_identity = MODEL_ID
        parts = ["STAGE_P_CONSTRUCTION_ROLE_EVALUATOR_V1", self.candidate_identity,
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
            raise RuntimeError("Construction Role Stage P evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__ = ("StagePConstructionRoleEvaluatorV1",)
