"""Canonical non-executing payload for the frozen V2 projector and static evaluator."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Mapping

from .immutable_source_span_reference_v1 import SourceRoleV1
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY,
    PROJECTOR_FREEZE_IDENTITY,
    TOKENIZER_IDENTITY,
    ConstructionObligationV2ProjectorSourceBindingV1,
    _decode_bound_source,
    bind_construction_obligation_v2_projector_v1,
)
from .stage_p_construction_obligation_v2_static_evaluator_v1 import (
    ConstructionObligationV2StaticEvaluationV1,
    evaluate_injected_construction_obligation_v2_result_v1,
)
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


STATIC_PROJECTOR_BINDING_IDENTITY = "9993395df612550e221efd2c4419a9f87f7382ef184d6e3d66b931340cd767f3"
STATIC_EVALUATOR_IDENTITY = "ffb7316fd0dfd783d93337345208fb912ccb7bd6accd5065dd065ce937617d4c"
PAYLOAD_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-static-payload"
PAYLOAD_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2StaticPayloadV1:
    source_binding: ConstructionObligationV2ProjectorSourceBindingV1
    payload_sha256: str

    def bind_projector(self, *, token_pieces: Mapping[int, str]):
        return bind_construction_obligation_v2_projector_v1(
            envelope=self.source_binding, token_pieces=token_pieces)

    def evaluate_injected_result(
        self, *, raw_result: bytes,
    ) -> ConstructionObligationV2StaticEvaluationV1:
        return evaluate_injected_construction_obligation_v2_result_v1(
            raw_result=raw_result, source_binding=self.source_binding)


def build_construction_obligation_v2_static_payload_v1(
    *, source_binding: ConstructionObligationV2ProjectorSourceBindingV1,
) -> bytes:
    _validate_source_binding(source_binding)
    source_value = {field.name: getattr(source_binding, field.name)
                    for field in fields(source_binding)}
    value = {
        "schema_name": PAYLOAD_SCHEMA_NAME,
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "static_projector_binding_identity": STATIC_PROJECTOR_BINDING_IDENTITY,
        "static_evaluator_identity": STATIC_EVALUATOR_IDENTITY,
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "tokenizer_identity": TOKENIZER_IDENTITY,
        "decoder_identity": DECODER_IDENTITY,
        "source_binding": source_value,
    }
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def parse_construction_obligation_v2_static_payload_v1(
    *, raw_payload: bytes,
) -> ConstructionObligationV2StaticPayloadV1:
    if type(raw_payload) is not bytes or not raw_payload:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_BYTES_REQUIRED")
    try:
        value = json.loads(raw_payload.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_JSON_INVALID") from exc
    required = {
        "schema_name", "schema_version", "static_projector_binding_identity",
        "static_evaluator_identity", "projector_freeze_identity",
        "tokenizer_identity", "decoder_identity", "source_binding"}
    if type(value) is not dict or set(value) != required:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_SHAPE_INVALID")
    if (value["schema_name"] != PAYLOAD_SCHEMA_NAME or
            value["schema_version"] != PAYLOAD_SCHEMA_VERSION or
            value["static_projector_binding_identity"] != STATIC_PROJECTOR_BINDING_IDENTITY or
            value["static_evaluator_identity"] != STATIC_EVALUATOR_IDENTITY or
            value["projector_freeze_identity"] != PROJECTOR_FREEZE_IDENTITY or
            value["tokenizer_identity"] != TOKENIZER_IDENTITY or
            value["decoder_identity"] != DECODER_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_IDENTITY_MISMATCH")
    names = {field.name for field in fields(ConstructionObligationV2ProjectorSourceBindingV1)}
    if type(value["source_binding"]) is not dict or set(value["source_binding"]) != names:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_SOURCE_SHAPE_INVALID")
    try:
        binding = ConstructionObligationV2ProjectorSourceBindingV1(**value["source_binding"])
    except (TypeError, ValueError) as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_SOURCE_INVALID") from exc
    _validate_source_binding(binding)
    canonical = build_construction_obligation_v2_static_payload_v1(source_binding=binding)
    if raw_payload != canonical:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_NOT_CANONICAL")
    return ConstructionObligationV2StaticPayloadV1(
        binding, hashlib.sha256(raw_payload).hexdigest())


def _validate_source_binding(
    binding: ConstructionObligationV2ProjectorSourceBindingV1,
) -> None:
    if type(binding) is not ConstructionObligationV2ProjectorSourceBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_EXACT_TYPE_REQUIRED")
    if (binding.projector_freeze_identity != PROJECTOR_FREEZE_IDENTITY or
            binding.tokenizer_identity != TOKENIZER_IDENTITY or
            binding.decoder_identity != DECODER_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_SOURCE_IDENTITY_MISMATCH")
    candidate = _decode_bound_source(
        binding.candidate_utf8_base64, binding.candidate_sha256,
        SourceRoleV1.CANDIDATE)
    authority = _decode_bound_source(
        binding.factual_authority_utf8_base64,
        binding.factual_authority_sha256, SourceRoleV1.FACTUAL_AUTHORITY)
    context = SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority)
    if context.binding_identity != binding.source_context_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_CONTEXT_IDENTITY_MISMATCH")


__all__ = (
    "ConstructionObligationV2StaticPayloadV1", "STATIC_EVALUATOR_IDENTITY",
    "STATIC_PROJECTOR_BINDING_IDENTITY",
    "build_construction_obligation_v2_static_payload_v1",
    "parse_construction_obligation_v2_static_payload_v1",
)
