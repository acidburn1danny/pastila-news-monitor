"""Pure injected-result evaluator for the frozen Construction-Obligation V2 lineage."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2,
    SourceProjectionReceiptV1,
    build_source_projection_receipt_v1,
    canonical_projection_receipt_bytes_v1,
)
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY,
    ENVELOPE_SCHEMA_NAME,
    ENVELOPE_SCHEMA_VERSION,
    PROJECTOR_FREEZE_IDENTITY,
    TOKENIZER_IDENTITY,
    ConstructionObligationV2ProjectorSourceBindingV1,
    _decode_bound_source,
)
from .immutable_source_span_reference_v1 import SourceRoleV1
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


STATIC_PROJECTOR_BINDING_IDENTITY = "9993395df612550e221efd2c4419a9f87f7382ef184d6e3d66b931340cd767f3"
EVALUATION_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-static-evaluation"
EVALUATION_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2StaticEvaluationV1:
    schema_name: str
    schema_version: str
    static_projector_binding_identity: str
    projector_freeze_identity: str
    source_context_identity: str
    raw_result_sha256: str
    ledger: ConstructionObligationLedgerV2
    source_projection_receipt: SourceProjectionReceiptV1
    evaluation_identity: str


def evaluate_injected_construction_obligation_v2_result_v1(
    *, raw_result: bytes,
    source_binding: ConstructionObligationV2ProjectorSourceBindingV1,
) -> ConstructionObligationV2StaticEvaluationV1:
    """Validate injected bytes and build the existing deterministic projection receipt."""
    if type(raw_result) is not bytes or not raw_result:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_INJECTED_RESULT_BYTES_REQUIRED")
    if type(source_binding) is not ConstructionObligationV2ProjectorSourceBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_EXACT_TYPE_REQUIRED")
    if (source_binding.schema_name != ENVELOPE_SCHEMA_NAME or
            source_binding.schema_version != ENVELOPE_SCHEMA_VERSION or
            source_binding.projector_freeze_identity != PROJECTOR_FREEZE_IDENTITY or
            source_binding.tokenizer_identity != TOKENIZER_IDENTITY or
            source_binding.decoder_identity != DECODER_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_IDENTITY_MISMATCH")
    candidate = _decode_bound_source(
        source_binding.candidate_utf8_base64, source_binding.candidate_sha256,
        SourceRoleV1.CANDIDATE)
    authority = _decode_bound_source(
        source_binding.factual_authority_utf8_base64,
        source_binding.factual_authority_sha256, SourceRoleV1.FACTUAL_AUTHORITY)
    context = SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority)
    if context.binding_identity != source_binding.source_context_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SOURCE_CONTEXT_IDENTITY_MISMATCH")
    ledger = ConstructionObligationLedgerV2.model_validate_json(raw_result, strict=True)
    receipt = build_source_projection_receipt_v1(
        raw_response=raw_result, ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    raw_sha256 = hashlib.sha256(raw_result).hexdigest()
    receipt_sha256 = hashlib.sha256(
        canonical_projection_receipt_bytes_v1(receipt)).hexdigest()
    identity_fields = (
        EVALUATION_SCHEMA_NAME, EVALUATION_SCHEMA_VERSION,
        STATIC_PROJECTOR_BINDING_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
        context.binding_identity, raw_sha256, receipt_sha256)
    evaluation_identity = hashlib.sha256("\n".join(identity_fields).encode()).hexdigest()
    return ConstructionObligationV2StaticEvaluationV1(
        EVALUATION_SCHEMA_NAME, EVALUATION_SCHEMA_VERSION,
        STATIC_PROJECTOR_BINDING_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
        context.binding_identity, raw_sha256, ledger, receipt, evaluation_identity)


__all__ = (
    "ConstructionObligationV2StaticEvaluationV1",
    "STATIC_PROJECTOR_BINDING_IDENTITY",
    "evaluate_injected_construction_obligation_v2_result_v1",
)
