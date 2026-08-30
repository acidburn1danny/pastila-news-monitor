"""Pure canonical request renderer for Construction-Obligation V2 Stage P."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    parse_construction_obligation_v2_static_payload_v1,
)
from .immutable_source_span_reference_v1 import SourceRoleV1
from .stage_p_construction_obligation_v2_projector_binding_v1 import _decode_bound_source
from .stage_p_construction_obligation_semantic_completeness_v1 import (
    SemanticCompletenessPolicyV1, semantic_completeness_policy_contract_v1,
)


DESIGN_IDENTITY = "93f5005c74dd9f4d553c2a193e924e891d1e29a78d5dc793766b840d30e892cc"
PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
STATIC_PAYLOAD_IDENTITY = "d55694074ea2023b0e93e06be9e260c11495cdc9fdbc23181c85e36c9921f7cd"
V2_SCHEMA_IDENTITY = "sha256:1a4d0dbac3dd56d9b18de678b0044143473c916eaad1f68451b97e7928a50838"
PROMPT_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-prompt-v1.txt")
PROMPT_SHA256 = "33a6e62acf0f9ee9636dea1da3b9c62a345ecab61b835b2f86466d71526be0a2"
DATA_BEGIN = b"BEGIN_CANONICAL_CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD"
DATA_END = b"END_CANONICAL_CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD"
POLICY_BEGIN = b"BEGIN_CANONICAL_SEMANTIC_COMPLETENESS_POLICY"
POLICY_END = b"END_CANONICAL_SEMANTIC_COMPLETENESS_POLICY"
MAX_RENDERED_UTF8_BYTES = 192_000
REQUEST_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-rendered-request"
REQUEST_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2RenderedRequestV1:
    schema_name: str
    schema_version: str
    design_identity: str
    projector_freeze_identity: str
    static_payload_identity: str
    v2_schema_identity: str
    prompt_sha256: str
    static_payload_sha256: str
    rendered_prompt_sha256: str
    rendered_prompt_utf8_bytes: int
    request_identity: str
    rendered_prompt: str


class ConstructionObligationV2RequestRendererV1:
    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        prompt_bytes = (self.project_root / PROMPT_RELATIVE).read_bytes()
        if hashlib.sha256(prompt_bytes).hexdigest() != PROMPT_SHA256:
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_PROMPT_IDENTITY_DRIFT")
        if not prompt_bytes.endswith(b"\n"):
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_PROMPT_FINAL_NEWLINE_REQUIRED")
        self._prompt_bytes = prompt_bytes

    def render(self, *, canonical_static_payload: bytes) -> ConstructionObligationV2RenderedRequestV1:
        parsed = parse_construction_obligation_v2_static_payload_v1(
            raw_payload=canonical_static_payload)
        if any(delimiter in canonical_static_payload for delimiter in (
                DATA_BEGIN, DATA_END, POLICY_BEGIN, POLICY_END)):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DATA_DELIMITER_COLLISION")
        candidate = _decode_bound_source(
            parsed.source_binding.candidate_utf8_base64,
            parsed.source_binding.candidate_sha256, SourceRoleV1.CANDIDATE)
        authority = _decode_bound_source(
            parsed.source_binding.factual_authority_utf8_base64,
            parsed.source_binding.factual_authority_sha256,
            SourceRoleV1.FACTUAL_AUTHORITY)
        policy = SemanticCompletenessPolicyV1.bind(
            candidate=candidate, factual_authority=authority)
        policy_bytes = (json.dumps(
            semantic_completeness_policy_contract_v1(policy), ensure_ascii=True,
            sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        rendered = (self._prompt_bytes + b"\n" + POLICY_BEGIN + b"\n" +
                    policy_bytes + POLICY_END + b"\n" + DATA_BEGIN + b"\n" +
                    canonical_static_payload + DATA_END)
        if len(rendered) > MAX_RENDERED_UTF8_BYTES:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_TOO_LARGE")
        rendered_text = rendered.decode("utf-8", errors="strict")
        payload_sha256 = hashlib.sha256(canonical_static_payload).hexdigest()
        rendered_sha256 = hashlib.sha256(rendered).hexdigest()
        identity_fields = (
            REQUEST_SCHEMA_NAME, REQUEST_SCHEMA_VERSION, DESIGN_IDENTITY,
            PROJECTOR_FREEZE_IDENTITY, STATIC_PAYLOAD_IDENTITY,
            V2_SCHEMA_IDENTITY, PROMPT_SHA256, payload_sha256, rendered_sha256)
        request_identity = hashlib.sha256("\n".join(identity_fields).encode()).hexdigest()
        return ConstructionObligationV2RenderedRequestV1(
            REQUEST_SCHEMA_NAME, REQUEST_SCHEMA_VERSION, DESIGN_IDENTITY,
            PROJECTOR_FREEZE_IDENTITY, STATIC_PAYLOAD_IDENTITY,
            V2_SCHEMA_IDENTITY, PROMPT_SHA256, payload_sha256, rendered_sha256,
            len(rendered), request_identity, rendered_text)


__all__ = (
    "ConstructionObligationV2RenderedRequestV1",
    "ConstructionObligationV2RequestRendererV1", "DATA_BEGIN", "DATA_END",
    "POLICY_BEGIN", "POLICY_END", "PROMPT_RELATIVE", "PROMPT_SHA256",
)
