"""Static source/context binding for the frozen Construction-Obligation V2 projector."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
from .stage_p_construction_obligation_character_controller_v1 import (
    StagePConstructionObligationCharacterControllerV1,
)
from .stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePConstructionObligationV2TokenProjectorV1,
)
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
EOS_TOKEN_ID = 2
EXCLUDED_TOKEN_IDS = (0, 1, 11)
ENVELOPE_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-projector-source-binding"
ENVELOPE_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2ProjectorSourceBindingV1:
    schema_name: str
    schema_version: str
    projector_freeze_identity: str
    tokenizer_identity: str
    decoder_identity: str
    candidate_utf8_base64: str
    candidate_sha256: str
    factual_authority_utf8_base64: str
    factual_authority_sha256: str
    source_context_identity: str

    def canonical_bytes(self) -> bytes:
        value = {name: getattr(self, name) for name in self.__dataclass_fields__}
        return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                           separators=(",", ":"), allow_nan=False) + "\n").encode()


def prepare_construction_obligation_v2_projector_binding_v1(
    *, candidate_utf8: bytes, factual_authority_utf8: bytes,
) -> ConstructionObligationV2ProjectorSourceBindingV1:
    candidate = _bind_source(candidate_utf8, SourceRoleV1.CANDIDATE)
    authority = _bind_source(factual_authority_utf8, SourceRoleV1.FACTUAL_AUTHORITY)
    context = SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority)
    return ConstructionObligationV2ProjectorSourceBindingV1(
        ENVELOPE_SCHEMA_NAME, ENVELOPE_SCHEMA_VERSION, PROJECTOR_FREEZE_IDENTITY,
        TOKENIZER_IDENTITY, DECODER_IDENTITY,
        base64.b64encode(candidate.data).decode("ascii"), candidate.sha256,
        base64.b64encode(authority.data).decode("ascii"), authority.sha256,
        context.binding_identity)


def bind_construction_obligation_v2_projector_v1(
    *, envelope: ConstructionObligationV2ProjectorSourceBindingV1,
    token_pieces: Mapping[int, str],
) -> StagePConstructionObligationV2TokenProjectorV1:
    if type(envelope) is not ConstructionObligationV2ProjectorSourceBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_EXACT_TYPE_REQUIRED")
    if (envelope.schema_name != ENVELOPE_SCHEMA_NAME or
            envelope.schema_version != ENVELOPE_SCHEMA_VERSION or
            envelope.projector_freeze_identity != PROJECTOR_FREEZE_IDENTITY or
            envelope.tokenizer_identity != TOKENIZER_IDENTITY or
            envelope.decoder_identity != DECODER_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_IDENTITY_MISMATCH")
    candidate = _decode_bound_source(
        envelope.candidate_utf8_base64, envelope.candidate_sha256,
        SourceRoleV1.CANDIDATE)
    authority = _decode_bound_source(
        envelope.factual_authority_utf8_base64, envelope.factual_authority_sha256,
        SourceRoleV1.FACTUAL_AUTHORITY)
    context = SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority)
    if context.binding_identity != envelope.source_context_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SOURCE_CONTEXT_IDENTITY_MISMATCH")
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity=DECODER_IDENTITY)
    return StagePConstructionObligationV2TokenProjectorV1(
        controller=controller, token_pieces=token_pieces,
        eos_token_id=EOS_TOKEN_ID, tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,
        request_context_identity=context.binding_identity,
        excluded_token_ids=EXCLUDED_TOKEN_IDS)


def _bind_source(data: bytes, role: SourceRoleV1) -> ImmutableUtf8SourceV1:
    if type(data) is not bytes or not data:
        raise ValueError(f"{role.value}_UTF8_BYTES_REQUIRED")
    data.decode("utf-8", errors="strict")
    return ImmutableUtf8SourceV1.bind(role=role, data=data)


def _decode_bound_source(value: str, expected_sha256: str,
                         role: SourceRoleV1) -> ImmutableUtf8SourceV1:
    try:
        data = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{role.value}_SOURCE_BASE64_INVALID") from exc
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"{role.value}_SOURCE_HASH_MISMATCH")
    return _bind_source(data, role)


__all__ = (
    "ConstructionObligationV2ProjectorSourceBindingV1", "DECODER_IDENTITY",
    "EOS_TOKEN_ID", "EXCLUDED_TOKEN_IDS", "PROJECTOR_FREEZE_IDENTITY",
    "TOKENIZER_IDENTITY", "bind_construction_obligation_v2_projector_v1",
    "prepare_construction_obligation_v2_projector_binding_v1",
)
