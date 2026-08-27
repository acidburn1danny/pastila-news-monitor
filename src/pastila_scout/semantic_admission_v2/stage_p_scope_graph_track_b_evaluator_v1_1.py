"""Evaluation-only Track-B evaluator bound to the approved V1.3 diagnostic executor."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import MODEL_ID
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .stage_p_scope_graph_durable_executor_v1_3 import DurableScopeGraphStagePExecutorV1_3
from .stage_p_scope_graph_track_b_request_candidate_v1 import StagePScopeGraphTrackBRequestCandidateV1


APPROVED_TRACK_B_REQUEST_IDENTITY = "c6ab0e2f7721710af208c70ad96d31a412596b9ce69ee8f7f485caba5b620f08"
APPROVED_BASELINE_LANGUAGE_EXECUTOR_BINDING_IDENTITY = "aa01960320b1d98b2e7be7a7943bccc36f4c854662f75c660d20391267259b42"


class StagePScopeGraphTrackBEvaluatorV1_1:
    def __init__(self, *, project_root: Path, executor: DurableScopeGraphStagePExecutorV1_3,
                 timeout_seconds: float = 240.0) -> None:
        if type(executor) is not DurableScopeGraphStagePExecutorV1_3:
            raise TypeError("Track-B evaluator requires exact approved V1.3 diagnostic executor")
        self._executor = executor
        self._candidate = StagePScopeGraphTrackBRequestCandidateV1(
            project_root=project_root, timeout_seconds=timeout_seconds)
        if self._candidate.candidate_identity != APPROVED_TRACK_B_REQUEST_IDENTITY:
            raise RuntimeError("Track-B request candidate identity drift")
        for name in ("candidate_identity", "prompt_identity", "schema_identity", "constraint_identity",
                     "grammar_identity", "tokenizer_identity"):
            setattr(self, name, getattr(self._candidate, name))
        self.model_identity = MODEL_ID
        parts = ["STAGE_P_SCOPE_GRAPH_TRACK_B_EVALUATOR_V1_1", self.candidate_identity,
                 APPROVED_BASELINE_LANGUAGE_EXECUTOR_BINDING_IDENTITY, self.model_identity,
                 str(timeout_seconds)]
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
            raise RuntimeError("Track-B Stage P evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__ = ("StagePScopeGraphTrackBEvaluatorV1_1",)
