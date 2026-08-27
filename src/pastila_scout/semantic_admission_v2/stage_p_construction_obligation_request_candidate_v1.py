"""Zero-inference request identity for Construction Obligation Projection V1."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_construction_role_contract_v1 import ConstructionRoleLedgerV1
from .stage_p_construction_role_prompt_v1 import StagePConstructionRolePromptContractV1


APPROVED_DFA_CANDIDATE_IDENTITY = "ba5e7096afda282b09be2e7e9bd83b2d46ef50904a07ba0b8783cad02a5a314f"
APPROVED_PROMPT_IDENTITY = "sha256:2fe034826fb19b28c4686fd4640325fd31a1f739140322b5a83412515f62e6bd"
APPROVED_SCHEMA_IDENTITY = "sha256:1b9e2a289aaade5e79c1be2f81000103dd7787b068576b9d8923789a237c6854"
APPROVED_CONSTRAINT_IDENTITY = "sha256:a5db3847530e1208fbc96f5a4af6e577b248ec2507c9045280b648420d0ad935"
APPROVED_GRAMMAR_IDENTITY = "sha256:340daf4cb25aadd9fa759cb16b7e388529c4a79caf79a1a18a407b8cab4037cc"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
APPROVED_REQUEST_IDENTITY_240 = "e1dbb1f70e9e5c83e23b5e29dbf868d1a3ad7c01ebd4d6d2c82aaa192bb00f31"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


class StagePConstructionObligationRequestCandidateV1:
    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._root = project_root.resolve(strict=True)
        self._prompt = StagePConstructionRolePromptContractV1(self._root)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("construction-obligation timeout invalid")
        self.timeout_seconds = timeout_seconds
        self.prompt_identity = self._prompt.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(
            _canonical(ConstructionRoleLedgerV1.model_json_schema())).hexdigest()
        constraint = self._root / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_constraint_v1.py"
        self.constraint_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{self.constraint_identity}".encode()).hexdigest()
        self.tokenizer_identity = APPROVED_TOKENIZER_IDENTITY
        observed = (self.prompt_identity, self.schema_identity, self.constraint_identity, self.grammar_identity)
        approved = (APPROVED_PROMPT_IDENTITY, APPROVED_SCHEMA_IDENTITY,
                    APPROVED_CONSTRAINT_IDENTITY, APPROVED_GRAMMAR_IDENTITY)
        if observed != approved:
            raise RuntimeError("construction-obligation approved dependency identity drift")
        parts = ["STAGE_P_CONSTRUCTION_OBLIGATION_REQUEST_V1", APPROVED_DFA_CANDIDATE_IDENTITY,
                 self.prompt_identity, self.schema_identity, self.constraint_identity,
                 self.grammar_identity, self.tokenizer_identity, str(self.timeout_seconds)]
        self.candidate_identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()
        if timeout_seconds == 240.0 and self.candidate_identity != APPROVED_REQUEST_IDENTITY_240:
            raise RuntimeError("construction-obligation request identity drift")

    def render_prompt(self, request: dict[str, object]) -> str:
        if type(request) is not dict: raise ValueError("construction-obligation request invalid")
        return self._prompt.render(factual_summary=request.get("factual_summary"),
                                   candidate=request.get("candidate"))

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request); prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:stage-p-construction-obligation-v1:{prompt_sha[:24]}", requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePConstructionObligationRequestCandidateV1",)
