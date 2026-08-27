"""Evaluation-only callable bound to Role Coherence V2."""
from __future__ import annotations

from datetime import UTC,datetime
from pathlib import Path

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2,ProviderResultStatusV2

from .stage_p_role_coherence_candidate_v2 import StagePRoleCoherenceCandidateV2


class StagePRoleCoherenceEvaluatorV2:
    def __init__(self,*,project_root:Path,executor,timeout_seconds:float=240.0)->None:
        self._executor=executor;self._candidate=StagePRoleCoherenceCandidateV2(project_root=project_root,timeout_seconds=timeout_seconds)
        for name in ("candidate_identity","prompt_identity","schema_identity","constraint_identity","grammar_identity","model_identity"):
            setattr(self,name,getattr(self._candidate,name))
    def render_prompt(self,request): return self._candidate.render_prompt(request)
    def build_authority(self,request,*,requested_at): return self._candidate.build_authority(request,requested_at=requested_at)
    def __call__(self,request):
        result=self._executor.execute(self.build_authority(request,requested_at=datetime.now(UTC)))
        if(result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None
           or result.provider_result.status is not ProviderResultStatusV2.SUCCESS or len(result.provider_result.outputs)!=1
           or result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("Stage P role-coherence V2 evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__=("StagePRoleCoherenceEvaluatorV2",)
