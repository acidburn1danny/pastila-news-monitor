"""Validation and byte-deterministic realization for the bounded Voice proof."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise

from pastila_scout.voice_deterministic_v2.core import (
    DeterministicVoiceValidationError,
)
from pastila_scout.voice_deterministic_v2.library import (
    APPROVED_CALLBACK_IDS_V1,
    APPROVED_NONLITERAL_MAPPING_IDS_V1,
    FROZEN_PROOF_CASES_V1,
)
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    DeterministicVoiceResultV1,
    IRDispositionV1,
    ProductionAcidCommentaryIRV1_1,
    ProvenanceClassV1,
    RenderedProvenanceSpanV1,
    RenderOutcomeV1,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_ir_bytes(ir: AcidCommentaryIRV1_1) -> bytes:
    payload = ir.model_dump(mode="json")
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _render_spans(
    ir, *, mismatch_message: str = "rendered bytes differ from expected identity"
) -> DeterministicVoiceResultV1:
    ir_identity = _sha256(canonical_ir_bytes(ir))
    output_parts: list[str] = []
    provenance: list[RenderedProvenanceSpanV1] = []
    cursor = 0
    for span in ir.spans:
        output_parts.append(span.text)
        end = cursor + len(span.text)
        provenance.append(
            RenderedProvenanceSpanV1(
                start=cursor,
                end=end,
                provenance_class=span.provenance_class,
                source_identity=span.source_identity,
                fictional_actor_id=span.fictional_actor_id,
                nonliteral_mapping_id=span.nonliteral_mapping_id,
                callback_id=span.callback_id,
                expression_binding=span.expression_binding,
            )
        )
        cursor = end
    output_bytes = "".join(output_parts).encode("utf-8")
    output_sha256 = _sha256(output_bytes)
    if output_sha256 != ir.expected_output_sha256:
        raise DeterministicVoiceValidationError(mismatch_message)
    if not provenance or provenance[0].start != 0 or provenance[-1].end != cursor:
        raise DeterministicVoiceValidationError("incomplete provenance coverage")
    if any(left.end != right.start for left, right in pairwise(provenance)):
        raise DeterministicVoiceValidationError("overlapping or uncovered provenance")
    result_payload = f"{ir_identity}:accepted:{output_sha256}".encode()
    return DeterministicVoiceResultV1(
        outcome=RenderOutcomeV1.ACCEPTED,
        commentary_bytes=output_bytes,
        output_sha256=output_sha256,
        provenance=tuple(provenance),
        ir_identity=ir_identity,
        result_identity=_sha256(result_payload),
    )


def _validate_against_library(ir: AcidCommentaryIRV1_1) -> None:
    case = FROZEN_PROOF_CASES_V1.get(ir.proof_id)
    if case is None:
        raise DeterministicVoiceValidationError("unknown proof case")
    if (
        ir.source_record_id != case.source_record_id
        or ir.mechanic_id is not case.mechanic_id
        or ir.realization_program_id != case.realization_program_id
        or ir.repetition_signature != case.repetition_signature
    ):
        raise DeterministicVoiceValidationError(
            "proof binding does not match allowlist"
        )
    if case.realization_program_sha256 and (
        ir.realization_program_sha256 != case.realization_program_sha256
    ):
        raise DeterministicVoiceValidationError("realization program identity mismatch")

    expression_spans = tuple(
        span
        for span in ir.spans
        if span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
    )
    if case.expected_output_sha256:
        if ir.disposition is not IRDispositionV1.REALIZE:
            raise DeterministicVoiceValidationError("accepted proof case must realize")
        if (
            not expression_spans
            and ir.expected_output_sha256 != case.expected_output_sha256
        ):
            raise DeterministicVoiceValidationError("owner target identity mismatch")
        if expression_spans:
            base_text = "".join(span.text for span in ir.spans[: ir.base_span_count])
            if (
                ir.base_output_sha256 != case.expected_output_sha256
                or _sha256(base_text.encode("utf-8")) != case.expected_output_sha256
            ):
                raise DeterministicVoiceValidationError(
                    "integrated expression base differs from owner target"
                )
    elif (
        ir.disposition is not IRDispositionV1.ABSTAIN
        or ir.abstention_reason is not case.expected_abstention_reason
    ):
        raise DeterministicVoiceValidationError("abstention reason mismatch")

    actor_ids = {actor.fictional_actor_id for actor in ir.fictional_actors}
    for span in ir.spans:
        if span.callback_id and span.callback_id not in APPROVED_CALLBACK_IDS_V1:
            raise DeterministicVoiceValidationError("unauthorized callback")
        if (
            span.nonliteral_mapping_id
            and span.nonliteral_mapping_id not in APPROVED_NONLITERAL_MAPPING_IDS_V1
        ):
            raise DeterministicVoiceValidationError("unauthorized nonliteral mapping")
        if span.fictional_actor_id and span.fictional_actor_id not in actor_ids:
            raise DeterministicVoiceValidationError("fictional actor leakage")


def _render_deterministic_voice_v2(
    ir: AcidCommentaryIRV1_1, *, expression_context_validated: bool
) -> DeterministicVoiceResultV1:
    if (
        any(
            span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
            for span in ir.spans
        )
        and not expression_context_validated
    ):
        raise DeterministicVoiceValidationError(
            "expression span requires governed integration validation"
        )

    _validate_against_library(ir)
    ir_identity = _sha256(canonical_ir_bytes(ir))

    if ir.disposition is IRDispositionV1.ABSTAIN:
        result_payload = f"{ir_identity}:abstain:{ir.abstention_reason.value}".encode()
        return DeterministicVoiceResultV1(
            outcome=RenderOutcomeV1.ABSTAINED,
            abstention_reason=ir.abstention_reason,
            ir_identity=ir_identity,
            result_identity=_sha256(result_payload),
        )

    return _render_spans(ir, mismatch_message="rendered bytes differ from owner target")


def render_production_deterministic_voice_v2(
    ir: ProductionAcidCommentaryIRV1_1,
) -> DeterministicVoiceResultV1:
    """Validate reusable production authority and render without proof fixtures."""

    from pastila_scout.voice_deterministic_v2.production import (
        PRODUCTION_SURFACE_BY_ID_V1,
        _program_sha,
    )
    from pastila_scout.voice_eligibility_v2.library import PROGRAM_BY_ID_V1

    spec = PROGRAM_BY_ID_V1.get(ir.realization_program_id)
    if spec is None or spec.mechanic_id is not ir.mechanic_id:
        raise DeterministicVoiceValidationError("unknown production program")
    if ir.realization_program_sha256 != _program_sha(spec.program_id):
        raise DeterministicVoiceValidationError("production program identity mismatch")
    authorized_sources = set(spec.surface_ids) | {
        "FORMAT_DOUBLE_NEWLINE_V1",
        *(atom_id for _, ids in ir.atom_role_bindings for atom_id in ids),
    }
    for span in ir.spans:
        if span.source_identity not in authorized_sources:
            raise DeterministicVoiceValidationError(
                "unknown production surface/operator"
            )
        surface = PRODUCTION_SURFACE_BY_ID_V1.get(span.source_identity)
        if surface is not None and (
            surface.retired
            or spec.program_id not in surface.permitted_programs
            or surface.text != span.text
            or surface.provenance_class is not span.provenance_class
        ):
            raise DeterministicVoiceValidationError(
                "production surface authority mismatch"
            )
        if span.source_identity == "FORMAT_DOUBLE_NEWLINE_V1" and (
            span.text != "\n\n"
            or span.provenance_class
            is not ProvenanceClassV1.DETERMINISTIC_FORMATTING_OR_OPERATOR
        ):
            raise DeterministicVoiceValidationError("malformed formatting provenance")
    return _render_spans(ir)


def render_deterministic_voice_v2(
    ir: AcidCommentaryIRV1_1,
) -> DeterministicVoiceResultV1:
    """Render a frozen base proof or return a prose-free abstention."""

    return _render_deterministic_voice_v2(ir, expression_context_validated=False)


__all__ = [
    "DeterministicVoiceValidationError",
    "canonical_ir_bytes",
    "render_deterministic_voice_v2",
    "render_production_deterministic_voice_v2",
]
