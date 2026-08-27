from __future__ import annotations

import hashlib

import pytest

from pastila_scout.voice_deterministic_v2.core import (
    DeterministicVoiceValidationError,
    canonical_ir_bytes,
    render_governed_spans,
)
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    IRDispositionV1,
    IRSpanV1,
    MechanicIdV1,
    ProvenanceClassV1,
)


def _ir(*, expected_output_sha256: str) -> AcidCommentaryIRV1_1:
    return AcidCommentaryIRV1_1(
        proof_id="P1",
        source_record_id="synthetic:fact-atom",
        realization_program_id="SYNTHETIC_DETERMINISTIC_PROGRAM_V1",
        realization_program_sha256="0" * 64,
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        disposition=IRDispositionV1.REALIZE,
        spans=(
            IRSpanV1(
                text="Text determinist.",
                provenance_class=ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
                source_identity="synthetic:atom-1",
            ),
        ),
        repetition_signature="synthetic:no-history",
        expected_output_sha256=expected_output_sha256,
    )


def test_canonical_ir_and_rendering_are_byte_deterministic() -> None:
    expected = hashlib.sha256("Text determinist.".encode("utf-8")).hexdigest()
    ir = _ir(expected_output_sha256=expected)

    assert canonical_ir_bytes(ir) == canonical_ir_bytes(ir.model_copy())
    first = render_governed_spans(ir)
    second = render_governed_spans(ir)
    assert first == second
    assert first.commentary_bytes == "Text determinist.".encode("utf-8")
    assert first.output_sha256 == expected


def test_rendering_fails_closed_on_output_identity_drift() -> None:
    with pytest.raises(DeterministicVoiceValidationError, match="expected identity"):
        render_governed_spans(_ir(expected_output_sha256="0" * 64))
