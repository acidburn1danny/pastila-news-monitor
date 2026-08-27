"""Proof-neutral package boundary with lazy proof compatibility exports."""

from __future__ import annotations

from .core import DeterministicVoiceValidationError, canonical_ir_bytes
from .models import (
    AbstentionReasonV1,
    AcidCommentaryIRV1_1,
    BackgroundKindV1,
    CommentaryBackgroundAtomV1,
    DeterministicVoiceResultV1,
    ExpressionSpanBindingV1,
    FictionalRoleplayActorV1,
    IRDispositionV1,
    IRSpanV1,
    MechanicIdV1,
    ProductionAcidCommentaryIRV1_1,
    ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1,
    ProvenanceClassV1,
    RenderOutcomeV1,
)

_PROOF_LIBRARY_EXPORTS = {
    "APPROVED_CALLBACK_IDS_V1",
    "APPROVED_NONLITERAL_MAPPING_IDS_V1",
    "EVIDENCE_ONLY_STRUCTURE_IDS_V1",
    "FROZEN_PROOF_CASES_V1",
}
_PROOF_BUILDER_EXPORTS = {
    "build_frozen_realization_ir",
    "build_p7_authority_abstention_ir",
    "build_p8_repetition_abstention_ir",
}


def __getattr__(name: str):
    if name in _PROOF_LIBRARY_EXPORTS:
        from . import library

        return getattr(library, name)
    if name in _PROOF_BUILDER_EXPORTS:
        from . import proof

        return getattr(proof, name)
    if name == "render_deterministic_voice_v2":
        from .renderer import render_deterministic_voice_v2

        return render_deterministic_voice_v2
    if name == "render_production_deterministic_voice_v2":
        from .production_renderer import render_production_deterministic_voice_v2

        return render_production_deterministic_voice_v2
    raise AttributeError(name)


__all__ = [
    "APPROVED_CALLBACK_IDS_V1",
    "APPROVED_NONLITERAL_MAPPING_IDS_V1",
    "EVIDENCE_ONLY_STRUCTURE_IDS_V1",
    "FROZEN_PROOF_CASES_V1",
    "AbstentionReasonV1",
    "AcidCommentaryIRV1_1",
    "BackgroundKindV1",
    "CommentaryBackgroundAtomV1",
    "DeterministicVoiceResultV1",
    "DeterministicVoiceValidationError",
    "ExpressionSpanBindingV1",
    "FictionalRoleplayActorV1",
    "IRDispositionV1",
    "IRSpanV1",
    "MechanicIdV1",
    "ProductionAcidCommentaryIRV1_1",
    "ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1",
    "ProvenanceClassV1",
    "RenderOutcomeV1",
    "build_frozen_realization_ir",
    "build_p7_authority_abstention_ir",
    "build_p8_repetition_abstention_ir",
    "canonical_ir_bytes",
    "render_deterministic_voice_v2",
    "render_production_deterministic_voice_v2",
]
