"""Receipt-preserving evaluator for Construction Obligation Projection V1."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import MODEL_ID
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .stage_p_constraint_failure_propagation_v1 import recover_constraint_liveness_v1
from .stage_p_construction_obligation_durable_executor_v1 import DurableConstructionObligationStagePExecutorV1
from .stage_p_construction_obligation_request_candidate_v1 import StagePConstructionObligationRequestCandidateV1
from .stage_p_scope_graph_durable_executor_v1_2 import StagePConstraintLivenessExecutionErrorV1


APPROVED_REQUEST_IDENTITY = "e1dbb1f70e9e5c83e23b5e29dbf868d1a3ad7c01ebd4d6d2c82aaa192bb00f31"
APPROVED_RUNNER_EXECUTOR_BINDING_IDENTITY = "689cfc7770e284b7364f143b05d2f0e6c6a5bc1a5c6358845fcea8f8d06ab930"
RECEIPT_PROPAGATION_CANDIDATE_IDENTITY = "aae3212858b87ae7e3876c497fb9b554d5c606426fa692d6df9f26982c9d7b08"


class StagePConstructionObligationEvaluatorV1:
    def __init__(self, *, project_root: Path, executor: DurableConstructionObligationStagePExecutorV1,
                 timeout_seconds: float = 240.0) -> None:
        if type(executor) is not DurableConstructionObligationStagePExecutorV1:
            raise TypeError("obligation evaluator requires exact approved durable executor")
        self._executor = executor
        self._candidate = StagePConstructionObligationRequestCandidateV1(
            project_root=project_root, timeout_seconds=timeout_seconds)
        if self._candidate.candidate_identity != APPROVED_REQUEST_IDENTITY:
            raise RuntimeError("obligation request candidate identity drift")
        for name in ("candidate_identity", "prompt_identity", "schema_identity", "constraint_identity",
                     "grammar_identity", "tokenizer_identity"):
            setattr(self, name, getattr(self._candidate, name))
        self.model_identity = MODEL_ID
        parts = ["STAGE_P_CONSTRUCTION_OBLIGATION_EVALUATOR_V1", self.candidate_identity,
                 APPROVED_RUNNER_EXECUTOR_BINDING_IDENTITY, RECEIPT_PROPAGATION_CANDIDATE_IDENTITY,
                 self.model_identity, str(timeout_seconds)]
        self.evaluator_identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        return self._candidate.render_prompt(request)

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        return self._candidate.build_authority(request, requested_at=requested_at)

    def __call__(self, request: dict[str, object]) -> str:
        result = self._executor.execute(self.build_authority(request, requested_at=datetime.now(UTC)))
        receipt = recover_constraint_liveness_v1(
            result=result, durable_lifecycle_root=self._executor._durable_root)
        if receipt is not None: raise StagePConstraintLivenessExecutionErrorV1(receipt)
        if (result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None or
                result.provider_result.status is not ProviderResultStatusV2.SUCCESS or
                len(result.provider_result.outputs) != 1 or
                result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("Construction Obligation Stage P evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__ = ("StagePConstructionObligationEvaluatorV1",)
