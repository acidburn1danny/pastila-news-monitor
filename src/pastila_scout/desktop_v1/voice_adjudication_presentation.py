"""Natural-language Editor projection of governed owner adjudication state."""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    VoiceStoryAdjudicationStateV1,
)


@dataclass(frozen=True, slots=True)
class VoiceFactCandidatePresentationV1:
    candidate_identity: str
    exact_text: str
    source_label: str
    extraction_policy: str
    candidate_kind: str = "exact_span"
    disposition: str = "undecided"
    review_message: str = (
        "Acest text este doar un candidat extras. Devine fapt utilizabil numai "
        "după confirmarea explicită a editorului."
    )


@dataclass(frozen=True, slots=True)
class VoiceAdjudicationPresentationV1:
    event_id: int
    title: str
    message: str
    candidates: tuple[VoiceFactCandidatePresentationV1, ...] = ()
    can_review_facts: bool = False
    can_review_mechanics: bool = False
    can_choose_no_claim: bool = True
    fact_finalization_enabled: bool = False
    claim_finalization_enabled: bool = False
    mechanic_choices: tuple[str, ...] = ()


def present_voice_adjudication_v1(
    state: VoiceStoryAdjudicationStateV1,
) -> VoiceAdjudicationPresentationV1:
    source_labels = {
        item.source_identity: item.source_identity for item in state.authority_texts
    }
    extraction_fields = getattr(state, "extraction_fields", ())
    source_labels.update(
        {
            item.source_identity: (
                f"{item.source_id.replace('-', ' ').title()} · "
                f"{'titlu' if item.field_name == 'title' else 'rezumat'}"
            )
            for item in extraction_fields
        }
    )
    latest = {item.candidate_identity: item for item in state.fact_atom_receipts}
    candidates = tuple(
        VoiceFactCandidatePresentationV1(
            candidate_identity=item.candidate_id,
            exact_text=item.evidence.passage,
            source_label=source_labels[item.evidence.source_identity],
            extraction_policy=state.fact_atom_bundle.extraction_policy_version,
            candidate_kind=item.kind.value,
            disposition=(
                "undecided"
                if item.candidate_id not in latest
                else latest[item.candidate_id].disposition.value
            ),
        )
        for item in state.candidates
    )
    if state.lifecycle is AdjudicationLifecycleV1.STALE:
        return VoiceAdjudicationPresentationV1(
            event_id=state.binding.event_id,
            title="Adjudicare învechită — reevaluare necesară",
            message="Materialul sau autoritatea factuală s-a schimbat.",
            can_choose_no_claim=False,
        )
    if state.lifecycle is AdjudicationLifecycleV1.NO_CLAIM:
        return VoiceAdjudicationPresentationV1(
            event_id=state.binding.event_id,
            title="Fără construcție sigură",
            message="Editorul a decis că nu există o construcție sigură.",
        )
    fact_final = state.lifecycle in {
        AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED,
        AdjudicationLifecycleV1.MECHANIC_CLAIMS_PARTIAL,
        AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED,
    }
    terminal = all(
        item.candidate_id in latest
        and latest[item.candidate_id].disposition.value
        in {"accept_typed_atom", "reject"}
        for item in state.candidates
    )
    return VoiceAdjudicationPresentationV1(
        event_id=state.binding.event_id,
        title=(
            "Construcție editorială confirmată"
            if state.lifecycle is AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED
            else "Faptele sunt finalizate"
            if state.lifecycle is AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED
            else "Confirmarea construcției editoriale este necesară"
            if state.lifecycle is AdjudicationLifecycleV1.MECHANIC_CLAIMS_PARTIAL
            else (
                "Adjudicare factuală în curs"
                if state.fact_atom_receipts
                else "Adjudicare factuală necesară"
            )
        ),
        message=(
            "Nicio construcție nu este obligatorie. Confirmă numai relațiile "
            "susținute de materialul acceptat."
            if fact_final
            else "Confirmă sau respinge fiecare suprafață; extragerea nu înseamnă aprobare."
        ),
        candidates=candidates,
        can_review_facts=not fact_final,
        can_review_mechanics=fact_final,
        fact_finalization_enabled=not fact_final and terminal,
        claim_finalization_enabled=bool(state.mechanic_claims),
        mechanic_choices=(
            (
                "numeric_expectation_ladder",
                "fictional_intake_or_interface",
                "uncertainty_sandwiched_fiction",
            )
            if fact_final
            else ()
        ),
    )


__all__ = [
    "VoiceAdjudicationPresentationV1",
    "VoiceFactCandidatePresentationV1",
    "present_voice_adjudication_v1",
]
