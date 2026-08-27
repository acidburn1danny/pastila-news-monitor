"""Evaluation-only callable bound to the approved Scope Graph request candidate."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import MODEL_ID
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .stage_p_scope_graph_request_candidate_v1 import StagePScopeGraphRequestCandidateV1


class StagePScopeGraphEvaluatorV1:
    def __init__(self, *, project_root: Path, executor, timeout_seconds: float = 240.0) -> None:
        self._executor = executor
        self._candidate = StagePScopeGraphRequestCandidateV1(project_root=project_root, timeout_seconds=timeout_seconds)
        self.candidate_identity = self._candidate.candidate_identity
        self.prompt_identity = self._candidate.prompt_identity
        self.schema_identity = self._candidate.schema_identity
        self.grammar_identity = self._candidate.grammar_identity
        self.tokenizer_identity = self._candidate.tokenizer_identity
        self.model_identity = MODEL_ID

    def render_prompt(self, request):
        return self._candidate.render_prompt(request)

    def build_authority(self, request, *, requested_at: datetime):
        return self._candidate.build_authority(request, requested_at=requested_at)

    def __call__(self, request: dict[str, object]) -> str:
        authority = self.build_authority(request, requested_at=datetime.now(UTC))
        result = self._executor.execute(authority)
        if (result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None or
                result.provider_result.status is not ProviderResultStatusV2.SUCCESS or
                len(result.provider_result.outputs) != 1 or
                result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("Stage P scope-graph evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__ = ("StagePScopeGraphEvaluatorV1",)
