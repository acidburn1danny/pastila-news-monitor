"""Evaluation-only Stage P evaluator bound to the V2 source-role prompt."""
from __future__ import annotations

import hashlib
from datetime import UTC,datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1,ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2,ExecutionOutcomeV2,TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderFinishReasonV2,ProviderResultStatusV2

from .stage_p_source_role_prompt_v2 import StagePSourceRolePromptContractV2
from .stage_p_provider_identity_v1 import MODEL_IDENTITY,STAGE_P_GRAMMAR_IDENTITY


class StagePSourceRoleEvaluatorV2:
    def __init__(self,*,project_root:Path,executor,timeout_seconds:float=240.0)->None:
        self._executor=executor;self._timeout=timeout_seconds;self._contract=StagePSourceRolePromptContractV2(project_root)
        self.prompt_identity=self._contract.prompt_identity;self.grammar_identity=STAGE_P_GRAMMAR_IDENTITY
        self.model_identity=MODEL_IDENTITY
        self.evaluator_identity=hashlib.sha256(f"P_SOURCE_ROLE_V2\n{self.prompt_identity}\n{self.grammar_identity}\n{MODEL_IDENTITY}".encode()).hexdigest()

    def render_prompt(self,request:dict[str,object])->str:
        summary,candidate=request.get("factual_summary"),request.get("candidate")
        if type(summary) is not str or type(candidate) is not str: raise ValueError("Stage P V2 source text invalid")
        return self._contract.render(factual_summary=summary,candidate=candidate)

    def build_authority(self,request:dict[str,object],*,requested_at:datetime):
        prompt=self.render_prompt(request);prompt_sha=hashlib.sha256(prompt.encode()).hexdigest()
        application=ApplicationProviderRequestV1(ProviderChoiceV1.OLLAMA,prompt,f"semantic-admission-v2:stage-p-source-role-v2:{prompt_sha[:24]}",
            requested_at,TimeoutPolicyV2(timeout_seconds=self._timeout),CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)

    def __call__(self,request:dict[str,object])->str:
        authority=self.build_authority(request,requested_at=datetime.now(UTC));result=self._executor.execute(authority)
        if(result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None
            or result.provider_result.status is not ProviderResultStatusV2.SUCCESS or len(result.provider_result.outputs)!=1
            or result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("Stage P source-role V2 evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__=("StagePSourceRoleEvaluatorV2",)
