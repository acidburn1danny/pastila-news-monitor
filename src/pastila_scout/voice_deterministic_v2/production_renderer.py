"""Production-only deterministic renderer with no proof dependencies."""

from __future__ import annotations

from pastila_scout.voice_eligibility_v2.library import PROGRAM_BY_ID_V1

from .core import DeterministicVoiceValidationError, render_governed_spans
from .models import ProductionAcidCommentaryIRV1_1, ProvenanceClassV1
from .production import PRODUCTION_SURFACE_BY_ID_V1, _program_sha


def render_production_deterministic_voice_v2(
    ir: ProductionAcidCommentaryIRV1_1,
):
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
    return render_governed_spans(ir)


__all__ = ["render_production_deterministic_voice_v2"]
