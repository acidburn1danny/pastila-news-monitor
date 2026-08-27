"""Zero-inference evaluator/runner interfaces for the approved V2 projector."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
from .stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1
from .stage_p_construction_obligation_token_projector_v1 import StagePConstructionObligationTokenProjectorV1
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


APPROVED_PROJECTOR_IDENTITY = "ab308048582a1a22afadb881110e7ba83f8ac0e15bc44c3f6379e71942397ce7"
APPROVED_TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
ENVELOPE_SCHEMA = "pastila-semantic-admission-v2-stage-p-projector-source-binding-envelope"
ENVELOPE_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class ProjectorSourceBindingEnvelopeV1:
    schema_name: str
    schema_version: str
    projector_identity: str
    tokenizer_identity: str
    decoder_identity: str
    candidate_utf8_base64: str
    candidate_sha256: str
    factual_authority_utf8_base64: str
    factual_authority_sha256: str
    context_identity: str

    def canonical_bytes(self) -> bytes:
        return (json.dumps({field: getattr(self, field) for field in self.__dataclass_fields__},
                           sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


@dataclass(frozen=True, slots=True)
class EvaluatorProjectorPreparationV1:
    rendered_prompt: str
    source_binding: ProjectorSourceBindingEnvelopeV1


class StagePConstructionObligationProjectorEvaluatorInterfaceV1:
    """Prepare prompt and a distinct immutable runner-side constraint envelope."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        from .stage_p_construction_obligation_request_candidate_v1 import (
            StagePConstructionObligationRequestCandidateV1,
        )
        self.request_candidate = StagePConstructionObligationRequestCandidateV1(
            project_root=project_root, timeout_seconds=timeout_seconds)

    def prepare(self, request: dict[str, object]) -> EvaluatorProjectorPreparationV1:
        if type(request) is not dict:
            raise ValueError("PROJECTOR_BINDING_REQUEST_INVALID")
        candidate_text = request.get("candidate"); authority_text = request.get("factual_summary")
        if type(candidate_text) is not str or not candidate_text:
            raise ValueError("PROJECTOR_BINDING_CANDIDATE_REQUIRED")
        if type(authority_text) is not str or not authority_text:
            raise ValueError("PROJECTOR_BINDING_FACTUAL_AUTHORITY_REQUIRED")
        candidate = ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data=candidate_text.encode("utf-8"))
        authority = ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data=authority_text.encode("utf-8"))
        context = SourceReferenceConstraintContextV1.bind(
            candidate=candidate, factual_authority=authority)
        envelope = ProjectorSourceBindingEnvelopeV1(
            ENVELOPE_SCHEMA, ENVELOPE_VERSION, APPROVED_PROJECTOR_IDENTITY,
            APPROVED_TOKENIZER_IDENTITY, DECODER_IDENTITY,
            base64.b64encode(candidate.data).decode("ascii"), candidate.sha256,
            base64.b64encode(authority.data).decode("ascii"), authority.sha256,
            context.binding_identity)
        return EvaluatorProjectorPreparationV1(
            self.request_candidate.render_prompt(request), envelope)


class StagePConstructionObligationProjectorRunnerInterfaceV1:
    """Reconstruct the request-bound context and candidate; performs no generation."""

    @staticmethod
    def bind(*, envelope: ProjectorSourceBindingEnvelopeV1,
             token_pieces: Mapping[int, str], eos_token_id: int,
             excluded_token_ids: Iterable[int]) -> StagePConstructionObligationTokenProjectorV1:
        if (envelope.schema_name != ENVELOPE_SCHEMA or envelope.schema_version != ENVELOPE_VERSION or
                envelope.projector_identity != APPROVED_PROJECTOR_IDENTITY or
                envelope.tokenizer_identity != APPROVED_TOKENIZER_IDENTITY or
                envelope.decoder_identity != DECODER_IDENTITY):
            raise ValueError("PROJECTOR_BINDING_IDENTITY_MISMATCH")
        try:
            candidate_bytes = base64.b64decode(envelope.candidate_utf8_base64, validate=True)
            authority_bytes = base64.b64decode(envelope.factual_authority_utf8_base64, validate=True)
        except Exception as error:
            raise ValueError("PROJECTOR_BINDING_BASE64_INVALID") from error
        if (hashlib.sha256(candidate_bytes).hexdigest() != envelope.candidate_sha256 or
                hashlib.sha256(authority_bytes).hexdigest() != envelope.factual_authority_sha256):
            raise ValueError("PROJECTOR_BINDING_SOURCE_HASH_MISMATCH")
        candidate = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE, data=candidate_bytes)
        authority = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.FACTUAL_AUTHORITY, data=authority_bytes)
        context = SourceReferenceConstraintContextV1.bind(candidate=candidate, factual_authority=authority)
        if context.binding_identity != envelope.context_identity:
            raise ValueError("PROJECTOR_BINDING_CONTEXT_IDENTITY_MISMATCH")
        controller = StagePConstructionObligationCharacterControllerV1(
            context=context, decoder_identity=DECODER_IDENTITY)
        return StagePConstructionObligationTokenProjectorV1(
            controller=controller, token_pieces=token_pieces, eos_token_id=eos_token_id,
            tokenizer_identity=APPROVED_TOKENIZER_IDENTITY, decoder_identity=DECODER_IDENTITY,
            excluded_token_ids=excluded_token_ids)


__all__ = (
    "EvaluatorProjectorPreparationV1", "ProjectorSourceBindingEnvelopeV1",
    "StagePConstructionObligationProjectorEvaluatorInterfaceV1",
    "StagePConstructionObligationProjectorRunnerInterfaceV1",
)
