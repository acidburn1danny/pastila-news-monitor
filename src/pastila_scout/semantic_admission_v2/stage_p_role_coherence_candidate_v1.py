"""Zero-inference construction candidate for Stage P role coherence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_role_coherence_contract_v1 import RoleCoherentLedgerV1
from .stage_p_role_coherence_prompt_v1 import StagePRoleCoherencePromptContractV1
from .stage_p_provider_identity_v1 import MODEL_IDENTITY


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class StagePRoleCoherenceCandidateV1:
    """Construct identity-bound requests; intentionally has no execution method."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self._contract = StagePRoleCoherencePromptContractV1(project_root)
        self._timeout = timeout_seconds
        self.prompt_identity = self._contract.prompt_identity
        self.schema_identity = "sha256:" + hashlib.sha256(_canonical_json(RoleCoherentLedgerV1.model_json_schema())).hexdigest()
        constraint = project_root.resolve(strict=True) / "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_constraint_v1.py"
        self.constraint_source_identity = "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest()
        self.grammar_identity = "sha256:" + hashlib.sha256(
            f"{self.schema_identity}\n{self.constraint_source_identity}".encode("utf-8")
        ).hexdigest()
        self.model_identity = MODEL_IDENTITY
        self.candidate_identity = hashlib.sha256(
            f"P_ROLE_COHERENCE_V1\n{self.prompt_identity}\n{self.schema_identity}\n{self.grammar_identity}\n{MODEL_IDENTITY}".encode("utf-8")
        ).hexdigest()

    def render_prompt(self, request: dict[str, object]) -> str:
        summary, candidate = request.get("factual_summary"), request.get("candidate")
        if type(summary) is not str or type(candidate) is not str:
            raise ValueError("Stage P role-coherence source text invalid")
        return self._contract.render(factual_summary=summary, candidate=candidate)

    def build_authority(self, request: dict[str, object], *, requested_at: datetime):
        prompt = self.render_prompt(request)
        prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        application = ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA,
            prompt,
            f"semantic-admission-v2:stage-p-role-coherence-v1:{prompt_sha[:24]}",
            requested_at,
            TimeoutPolicyV2(timeout_seconds=self._timeout),
            CancellationTokenV2(cancellation_requested=False),
        )
        return ApplicationRequestAuthorityV1().build(application)


__all__ = ("StagePRoleCoherenceCandidateV1",)
