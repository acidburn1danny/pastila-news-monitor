"""Zero-inference identity-bound application-request candidate for Scope Graph V1.1."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_scope_graph_contract_v1_1 import ScopeGraphLedgerV1_1
from .stage_p_scope_graph_prompt_v1_1 import StagePScopeGraphPromptContractV1_1


APPROVED_TOKENIZER_CANDIDATE_IDENTITY = "fc32a8d1bc40df96bb3a4921f993d7ebfbc31570b3c306f28e4046d5e028f1f2"
APPROVED_SCHEMA_IDENTITY = "sha256:a61f16046045ca015dd2001393ab58e7ab7c94f50cbfc49f7df959bd45b3338c"
APPROVED_GRAMMAR_IDENTITY = "sha256:28539234a7c6a7815fbf47d506855a3d17cd236b5a8c7d3a37fd2c3abc7cb393"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class StagePScopeGraphRequestCandidateV1_1:
    """Construct provider-neutral request authority; intentionally cannot execute it."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._root = project_root.resolve(strict=True)
        self._prompt = StagePScopeGraphPromptContractV1_1(self._root)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("Stage P scope-graph V1.1 timeout invalid")
        self.timeout_seconds = timeout_seconds
        self.prompt_identity = self._prompt.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(_canonical(ScopeGraphLedgerV1_1.model_json_schema())).hexdigest()
        constraint = self._root / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1_1.py"
        constraint_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{constraint_identity}".encode()).hexdigest()
        self.tokenizer_identity = APPROVED_TOKENIZER_IDENTITY
        if self.schema_identity != APPROVED_SCHEMA_IDENTITY or self.grammar_identity != APPROVED_GRAMMAR_IDENTITY:
            raise RuntimeError("Stage P scope-graph V1.1 approved dependency identity drift")
        self.candidate_identity = hashlib.sha256(
            ("STAGE_P_SCOPE_GRAPH_REQUEST_V1_1\n" + APPROVED_TOKENIZER_CANDIDATE_IDENTITY + "\n" +
             self.prompt_identity + "\n" + self.schema_identity + "\n" + self.grammar_identity + "\n" +
             self.tokenizer_identity + "\n" + str(self.timeout_seconds)).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        if type(request) is not dict:
            raise ValueError("Stage P scope-graph V1.1 request source invalid")
        return self._prompt.render(factual_summary=request.get("factual_summary"), candidate=request.get("candidate"))

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request)
        prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:stage-p-scope-graph-v1-1:{prompt_sha[:24]}", requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False))
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePScopeGraphRequestCandidateV1_1",)
