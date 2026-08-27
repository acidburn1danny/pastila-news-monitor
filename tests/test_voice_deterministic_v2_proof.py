from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.voice_deterministic_v2 import (
    FROZEN_PROOF_CASES_V1,
    AcidCommentaryIRV1_1,
    BackgroundKindV1,
    CommentaryBackgroundAtomV1,
    DeterministicVoiceValidationError,
    IRSpanV1,
    ProvenanceClassV1,
    RenderOutcomeV1,
    build_frozen_realization_ir,
    build_p7_authority_abstention_ir,
    build_p8_repetition_abstention_ir,
    canonical_ir_bytes,
    render_deterministic_voice_v2,
)

EVIDENCE_ROOT = Path(
    "tests/fixtures/voice_deterministic_v2/frozen_proof_cases"
)


@pytest.mark.parametrize("proof_id", ("P1", "P2", "P3", "P4", "P5", "P6"))
def test_p1_p6_render_exact_frozen_owner_bytes_with_complete_provenance(
    proof_id: str,
) -> None:
    ir = build_frozen_realization_ir(proof_id, EVIDENCE_ROOT)
    result = render_deterministic_voice_v2(ir)
    case = FROZEN_PROOF_CASES_V1[proof_id]
    manifest = __import__("json").loads(
        (EVIDENCE_ROOT / proof_id / "manifest.json").read_text(encoding="utf-8")
    )
    expected = (EVIDENCE_ROOT / proof_id / manifest["target"]["path"]).read_bytes()

    assert result.outcome is RenderOutcomeV1.ACCEPTED
    assert result.commentary_bytes == expected
    assert result.output_sha256 == case.expected_output_sha256
    assert result.model_calls == result.provider_calls == 0
    assert result.provenance[0].start == 0
    assert result.provenance[-1].end == len(expected.decode("utf-8"))
    assert all(
        left.end == right.start
        for left, right in pairwise(result.provenance)
    )


def test_p3_fictional_roleplay_spans_are_identity_isolated() -> None:
    ir = build_frozen_realization_ir("P3", EVIDENCE_ROOT)
    actor_ids = {actor.fictional_actor_id for actor in ir.fictional_actors}

    assert actor_ids == {
        "P3-FRA-01-GENERIC-PROSECUTOR",
        "P3-FRA-02-GENERIC-PROSECUTOR",
    }
    assert all(
        actor.fictional_actor_id
        not in actor.identity_isolation_from_event_actor_ids
        for actor in ir.fictional_actors
    )
    assert any(span.fictional_actor_id for span in ir.spans)


def test_professional_domain_background_requires_exact_scope() -> None:
    with pytest.raises(ValidationError, match="professional-domain premise"):
        CommentaryBackgroundAtomV1(
            atom_id="PDP-1",
            background_kind=BackgroundKindV1.PROFESSIONAL_DOMAIN_PREMISE,
            exact_proposition="A scoped professional premise.",
            provenance_identity="receipt-1",
        )


def test_p7_authority_driven_abstention_emits_no_commentary() -> None:
    result = render_deterministic_voice_v2(build_p7_authority_abstention_ir())

    assert result.outcome is RenderOutcomeV1.ABSTAINED
    assert result.commentary_bytes == b""
    assert result.output_sha256 is None
    assert result.provenance == ()
    assert result.model_calls == result.provider_calls == 0


def test_p8_repetition_driven_abstention_requires_exhausted_signature() -> None:
    signature = FROZEN_PROOF_CASES_V1["P8"].repetition_signature
    with pytest.raises(ValueError, match="not exhausted"):
        build_p8_repetition_abstention_ir(exhausted_signatures=frozenset())

    result = render_deterministic_voice_v2(
        build_p8_repetition_abstention_ir(
            exhausted_signatures=frozenset({signature})
        )
    )
    assert result.outcome is RenderOutcomeV1.ABSTAINED
    assert result.commentary_bytes == b""
    assert result.model_calls == result.provider_calls == 0


def test_identical_ir_rerenders_and_reloads_byte_identically() -> None:
    original = build_frozen_realization_ir("P4", EVIDENCE_ROOT)
    serialized = canonical_ir_bytes(original)
    reloaded = AcidCommentaryIRV1_1.model_validate_json(serialized)
    first = render_deterministic_voice_v2(original)
    second = render_deterministic_voice_v2(original)
    after_restart = render_deterministic_voice_v2(reloaded)

    assert canonical_ir_bytes(reloaded) == serialized
    assert first == second == after_restart


def test_changed_owner_surface_fails_closed_on_output_identity() -> None:
    ir = build_frozen_realization_ir("P5", EVIDENCE_ROOT)
    changed = ir.spans[0].model_copy(update={"text": ir.spans[0].text + "!"})
    mutated = ir.model_copy(update={"spans": (changed, *ir.spans[1:])})

    with pytest.raises(DeterministicVoiceValidationError, match="owner target"):
        render_deterministic_voice_v2(mutated)


def test_unauthorized_callback_and_nonliteral_mapping_fail_closed() -> None:
    ir = build_frozen_realization_ir("P4", EVIDENCE_ROOT)
    callback_span = ir.spans[0].model_copy(update={"callback_id": "UNAPPROVED"})
    with pytest.raises(DeterministicVoiceValidationError, match="callback"):
        render_deterministic_voice_v2(
            ir.model_copy(update={"spans": (callback_span, *ir.spans[1:])})
        )

    mapping_index = next(
        index for index, span in enumerate(ir.spans) if span.nonliteral_mapping_id
    )
    spans = list(ir.spans)
    spans[mapping_index] = spans[mapping_index].model_copy(
        update={"nonliteral_mapping_id": "UNAPPROVED"}
    )
    with pytest.raises(DeterministicVoiceValidationError, match="mapping"):
        render_deterministic_voice_v2(ir.model_copy(update={"spans": tuple(spans)}))


def test_unknown_actor_mechanic_and_ir_version_fail_closed() -> None:
    ir = build_frozen_realization_ir("P3", EVIDENCE_ROOT)
    actor_span_index = next(
        index for index, span in enumerate(ir.spans) if span.fictional_actor_id
    )
    spans = list(ir.spans)
    spans[actor_span_index] = spans[actor_span_index].model_copy(
        update={"fictional_actor_id": "REAL-PROSECUTOR"}
    )
    with pytest.raises(ValidationError, match="unknown fictional actor"):
        AcidCommentaryIRV1_1.model_validate(
            ir.model_dump() | {"spans": [span.model_dump() for span in spans]}
        )

    payload = ir.model_dump(mode="json")
    payload["mechanic_id"] = "Q10"
    with pytest.raises(ValidationError):
        AcidCommentaryIRV1_1.model_validate(payload)
    payload["mechanic_id"] = ir.mechanic_id.value
    payload["schema_version"] = "ACID_COMMENTARY_IR_V2"
    with pytest.raises(ValidationError):
        AcidCommentaryIRV1_1.model_validate(payload)


def test_factual_span_requires_a_source_identity() -> None:
    with pytest.raises(ValidationError):
        IRSpanV1(
            text="fapt",
            provenance_class=ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
            source_identity="",
        )
