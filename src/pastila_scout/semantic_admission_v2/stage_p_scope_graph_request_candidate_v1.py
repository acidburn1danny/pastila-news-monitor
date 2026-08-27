"""Zero-inference, identity-bound application-request candidate for Scope Graph V1."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_scope_graph_contract_v1 import ScopeGraphLedgerV1
from .stage_p_scope_graph_prompt_v1 import StagePScopeGraphPromptContractV1


APPROVED_PROMPT_CANDIDATE_IDENTITY = "030da4350e6228edc3bd3a7c4da56fc05a8619d9bb996f775f34989bcfa307f6"
APPROVED_SCHEMA_IDENTITY = "sha256:be5dd5a7ec69f4340ed79a18c782db9070207c8b16927fa7f6c8ff7b58e66c29"
APPROVED_GRAMMAR_IDENTITY = "sha256:95d16d95cef7163dbad0e149c7607400e531f8a086c92d6aa41209783d4edc59"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class StagePScopeGraphRequestCandidateV1:
    """Construct provider-neutral request authority; intentionally cannot execute it."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._root = project_root.resolve(strict=True)
        self._prompt = StagePScopeGraphPromptContractV1(self._root)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("Stage P scope-graph timeout invalid")
        self.timeout_seconds = timeout_seconds
        self.prompt_identity = self._prompt.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(_canonical(ScopeGraphLedgerV1.model_json_schema())).hexdigest()
        constraint = self._root / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1.py"
        constraint_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{constraint_identity}".encode()).hexdigest()
        self.tokenizer_identity = APPROVED_TOKENIZER_IDENTITY
        if self.schema_identity != APPROVED_SCHEMA_IDENTITY or self.grammar_identity != APPROVED_GRAMMAR_IDENTITY:
            raise RuntimeError("Stage P scope-graph approved dependency identity drift")
        self.candidate_identity = hashlib.sha256(
            ("STAGE_P_SCOPE_GRAPH_REQUEST_V1\n" + APPROVED_PROMPT_CANDIDATE_IDENTITY + "\n" +
             self.prompt_identity + "\n" + self.schema_identity + "\n" + self.grammar_identity + "\n" +
             self.tokenizer_identity + "\n" + str(self.timeout_seconds)).encode()).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        if type(request) is not dict:
            raise ValueError("Stage P scope-graph request source invalid")
        return self._prompt.render(factual_summary=request.get("factual_summary"), candidate=request.get("candidate"))

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request)
        prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA,
            prompt,
            f"semantic-admission-v2:stage-p-scope-graph-v1:{prompt_sha[:24]}",
            requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False),
        )
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePScopeGraphRequestCandidateV1",)
