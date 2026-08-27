"""Zero-inference application-request candidate for creative-target decomposition."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_creative_target_contract_v1 import CreativeTargetLedgerV1
from .stage_p_creative_target_prompt_v1 import StagePCreativeTargetPromptContractV1


APPROVED_DESIGN_IDENTITY = "efac1d65039546bd50dfa5079be9ae5d5e11e36ba731ab76ea4cac1e4b8ceda3"
APPROVED_PROMPT_IDENTITY = "sha256:a7a1fb35b356889b8465d767c5111f3b1b9aed2a449417a2089f694ba73a8824"
APPROVED_SCHEMA_IDENTITY = "sha256:3dccbf050677900fed11899295ed5724f638270116b72ebcda26a26255586569"
APPROVED_CONSTRAINT_IDENTITY = "sha256:e64ab5b70479399f13e9ce9ba299d61dfbd044276109ff7ff98f1e2b29078380"
APPROVED_GRAMMAR_IDENTITY = "sha256:d81f9588383bf93e46a1c57a5e5ab9b284af38d13e43223f7a29a656f1415adf"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class StagePCreativeTargetRequestCandidateV1:
    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._root = project_root.resolve(strict=True)
        self._prompt = StagePCreativeTargetPromptContractV1(self._root)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("creative-target timeout invalid")
        self.timeout_seconds = timeout_seconds
        self.prompt_identity = self._prompt.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(_canonical(CreativeTargetLedgerV1.model_json_schema())).hexdigest()
        constraint = self._root / "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_constraint_v1.py"
        self.constraint_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{self.constraint_identity}".encode()).hexdigest()
        self.tokenizer_identity = APPROVED_TOKENIZER_IDENTITY
        observed = (self.prompt_identity, self.schema_identity, self.constraint_identity, self.grammar_identity)
        approved = (APPROVED_PROMPT_IDENTITY, APPROVED_SCHEMA_IDENTITY,
                    APPROVED_CONSTRAINT_IDENTITY, APPROVED_GRAMMAR_IDENTITY)
        if observed != approved:
            raise RuntimeError("creative-target approved dependency identity drift")
        parts = ["STAGE_P_CREATIVE_TARGET_REQUEST_V1", APPROVED_DESIGN_IDENTITY,
                 self.prompt_identity, self.schema_identity, self.constraint_identity,
                 self.grammar_identity, self.tokenizer_identity, str(self.timeout_seconds)]
        self.candidate_identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        if type(request) is not dict:
            raise ValueError("creative-target request source invalid")
        return self._prompt.render(factual_summary=request.get("factual_summary"), candidate=request.get("candidate"))

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request)
        prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:stage-p-creative-target-v1:{prompt_sha[:24]}", requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePCreativeTargetRequestCandidateV1",)
