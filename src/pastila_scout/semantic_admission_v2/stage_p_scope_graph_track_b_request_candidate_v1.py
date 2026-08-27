"""Zero-inference application-request candidate for Track-B semantic scope selection."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_scope_graph_contract_v1_1 import ScopeGraphLedgerV1_1
from .stage_p_scope_graph_track_b_prompt_v1 import StagePScopeGraphTrackBPromptContractV1


APPROVED_TRACK_B_DESIGN_IDENTITY = "021690adb065887b6bd5c388a4beb5288629963a12fe7b09b94984a5f69dc05d"
APPROVED_TRACK_A_DURABLE_BINDING_IDENTITY = "4830238a46d1ecf25defcb00e5b7e75128c8a9fd9aff19cf14ab63037605bf2a"
APPROVED_PROMPT_IDENTITY = "sha256:35081f4840bce62317842cca75c42c143a62e04688867cbc1ae64b2e0db75cfc"
APPROVED_SCHEMA_IDENTITY = "sha256:a61f16046045ca015dd2001393ab58e7ab7c94f50cbfc49f7df959bd45b3338c"
APPROVED_CONSTRAINT_IDENTITY = "sha256:e928d3ba6fcc8590afe89ded92500437ff8086d14430dba3e4fe983efaf3cb18"
APPROVED_GRAMMAR_IDENTITY = "sha256:3c7914c3ac0316b4596754ca4011c1fad728539232d7d524fac92b8689861e3d"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class StagePScopeGraphTrackBRequestCandidateV1:
    """Construct an identity-bound request; intentionally has no execution method."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._root = project_root.resolve(strict=True)
        self._prompt = StagePScopeGraphTrackBPromptContractV1(self._root)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("Track-B timeout invalid")
        self.timeout_seconds = timeout_seconds
        self.prompt_identity = self._prompt.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(_canonical(ScopeGraphLedgerV1_1.model_json_schema())).hexdigest()
        constraint = self._root / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1_2.py"
        self.constraint_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{self.constraint_identity}".encode()).hexdigest()
        self.tokenizer_identity = APPROVED_TOKENIZER_IDENTITY
        observed = (self.prompt_identity, self.schema_identity, self.constraint_identity, self.grammar_identity)
        approved = (APPROVED_PROMPT_IDENTITY, APPROVED_SCHEMA_IDENTITY,
                    APPROVED_CONSTRAINT_IDENTITY, APPROVED_GRAMMAR_IDENTITY)
        if observed != approved:
            raise RuntimeError("Track-B approved dependency identity drift")
        parts = ["STAGE_P_SCOPE_GRAPH_TRACK_B_REQUEST_V1", APPROVED_TRACK_B_DESIGN_IDENTITY,
                 APPROVED_TRACK_A_DURABLE_BINDING_IDENTITY, self.prompt_identity, self.schema_identity,
                 self.constraint_identity, self.grammar_identity, self.tokenizer_identity,
                 str(self.timeout_seconds)]
        self.candidate_identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        if type(request) is not dict:
            raise ValueError("Track-B request source invalid")
        return self._prompt.render(factual_summary=request.get("factual_summary"), candidate=request.get("candidate"))

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request)
        prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:stage-p-scope-graph-track-b-v1:{prompt_sha[:24]}", requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePScopeGraphTrackBRequestCandidateV1",)
