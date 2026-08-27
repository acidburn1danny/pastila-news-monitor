"""Zero-inference request candidate bound to role-conditioned grammar V2."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1,ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2,TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_role_coherence_prompt_v1 import StagePRoleCoherencePromptContractV1
from .stage_p_provider_identity_v1 import MODEL_IDENTITY


SCHEMA_IDENTITY="sha256:a47603e257ee5e315b77993891f0079e30e6c63a150b6b04e6889a98a4613ac9"
CONSTRAINT_IDENTITY="sha256:5011b85a8b8bc12b871ceb0c8c1ba74cd453b5e4c6ff5f9ece2ace56704502fa"
GRAMMAR_IDENTITY="sha256:0d55e1d47054251c380901d9c8ac4f4be4f76355c3fc1a9fbc80cc16387f2429"
CANDIDATE_IDENTITY="0f51ac154a178ae65bc208969f53f3e4a7a2438950c170cb2e700247db68b3e3"


class StagePRoleCoherenceCandidateV2:
    def __init__(self,*,project_root:Path,timeout_seconds:float=240.0)->None:
        self._contract=StagePRoleCoherencePromptContractV1(project_root);self._timeout=timeout_seconds
        self.prompt_identity=self._contract.prompt_identity;self.schema_identity=SCHEMA_IDENTITY
        self.constraint_identity=CONSTRAINT_IDENTITY;self.grammar_identity=GRAMMAR_IDENTITY
        self.model_identity=MODEL_IDENTITY;self.candidate_identity=CANDIDATE_IDENTITY

    def render_prompt(self,request):
        summary,candidate=request.get("factual_summary"),request.get("candidate")
        if type(summary) is not str or type(candidate) is not str: raise ValueError("role-coherence V2 source invalid")
        return self._contract.render(factual_summary=summary,candidate=candidate)

    def build_authority(self,request,*,requested_at:datetime):
        prompt=self.render_prompt(request);digest=hashlib.sha256(prompt.encode()).hexdigest()
        application=ApplicationProviderRequestV1(ProviderChoiceV1.OLLAMA,prompt,
            f"semantic-admission-v2:stage-p-role-coherence-v2:{digest[:24]}",requested_at,
            TimeoutPolicyV2(timeout_seconds=self._timeout),CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)


__all__=("StagePRoleCoherenceCandidateV2",)
