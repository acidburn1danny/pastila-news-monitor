from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from pastila_scout.desktop_v1.voice_adjudication_presentation import (
    present_voice_adjudication_v1,
)
from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    AuthorityTextV1,
    CandidateOwnerDispositionV1,
    VoiceAdjudicationApplicationServiceV1,
    VoiceAdjudicationError,
    VoiceAdjudicationStoreV1,
)
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.models import AtomRoleBindingV1
from pastila_scout.voice_fact_atoms_v2.models import (
    AtomKind,
    AuthorityClass,
    CandidateKind,
    CompleteQuantityV1,
    FactAtomV1,
)
from tests.test_voice_production_materialization_v2 import _context

NOW = datetime(2026, 8, 23, 12, tzinfo=UTC)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _started(tmp_path):
    binding, _, _, _, snapshot, _, _ = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    text = "Proiectul costă aproximativ 37.000 de euro. Cauza nu este cunoscută."
    authority = AuthorityTextV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=binding.event_authority_identity,
        source_identity="event-authority:1",
        text=text,
        text_sha256=_sha(text),
    )
    store = VoiceAdjudicationStoreV1(tmp_path / "voice-root")
    service = VoiceAdjudicationApplicationServiceV1(store)
    state = service.begin(
        binding=binding,
        story_position=1,
        authority_texts=(authority,),
        repetition_snapshot=snapshot,
    )
    return service, store, state, text


def _exact(service, state, text, surface, kind):
    start = text.index(surface)
    return service.add_exact_candidate(
        state,
        source_identity="event-authority:1",
        start=start,
        end=start + len(surface),
        kind=kind,
    )


def _atom(state, surface, atom_id, kind, *, quantity=None, targets=()):
    candidate = next(
        item for item in state.candidates if item.evidence.passage == surface
    )
    return candidate, FactAtomV1(
        atom_id=atom_id,
        kind=kind,
        proposition=surface,
        authority_class=AuthorityClass.EVENT,
        evidence=(candidate.evidence,),
        candidate_ids=(candidate.candidate_id,),
        quantity=quantity,
        qualification_target_atom_ids=targets,
    )


def test_extraction_never_promotes_and_owner_can_reject(tmp_path):
    service, store, state, _ = _started(tmp_path)
    assert state.lifecycle is AdjudicationLifecycleV1.CANDIDATES_EXTRACTED
    assert state.candidates
    assert state.fact_atom_bundle.atoms == ()
    assert all(item.requires_semantic_adjudication for item in state.candidates)

    candidate = state.candidates[0]
    rejected = service.decide_fact_atom(
        state,
        candidate_identity=candidate.candidate_id,
        disposition=CandidateOwnerDispositionV1.REJECT,
        atom=None,
        adjudicator_identity="owner",
        adjudicated_at=NOW,
        decision_rationale="Owner rejected this extracted candidate.",
    )
    assert rejected.fact_atom_bundle.atoms == ()
    assert store.load(1) == rejected
    assert service.model_calls == service.provider_calls == service.model_loads == 0
    presentation = present_voice_adjudication_v1(rejected)
    assert presentation.can_review_facts
    assert "extragerea nu înseamnă aprobare" in presentation.message

    composition = compose_voice_v2_production(
        project_path=(tmp_path / "active-project.json").resolve(),
        project_identity="project-1",
    )
    assert composition.adjudication_store is not None
    assert composition.adjudication_application is not None


def test_explicit_atoms_claim_revision_and_restart(tmp_path):
    service, store, state, text = _started(tmp_path)
    proposition = "Proiectul costă aproximativ 37.000 de euro."
    quantity_surface = "aproximativ 37.000 de euro"
    uncertainty = "Cauza nu este cunoscută."
    state = _exact(service, state, text, proposition, CandidateKind.EXACT_SPAN)
    state = _exact(
        service, state, text, quantity_surface, CandidateKind.COMPLETE_QUANTITY
    )
    state = _exact(service, state, text, uncertainty, CandidateKind.UNCERTAINTY_MARKER)

    candidate, proposition_atom = _atom(
        state, proposition, "event-proposition", AtomKind.EVENT_PROPOSITION
    )
    state = service.decide_fact_atom(
        state,
        candidate_identity=candidate.candidate_id,
        disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
        atom=proposition_atom,
        governed_object_or_scope="project cost",
        actor_or_subject_atom_ids=("event-proposition",),
        chronology_atom_ids=("event-proposition",),
        attribution_atom_ids=("event-proposition",),
        adjudicator_identity="owner",
        adjudicated_at=NOW,
        decision_rationale="Owner accepted the exact event proposition.",
    )
    candidate, quantity_atom = _atom(
        state,
        quantity_surface,
        "complete-quantity",
        AtomKind.COMPLETE_QUANTITY,
        quantity=CompleteQuantityV1(
            exact_surface=quantity_surface,
            numeric_surface="37.000",
            approximation="aproximativ",
            bound_semantics="approximate",
            unit_or_currency="euro",
            subject_scope="project cost",
        ),
    )
    state = service.decide_fact_atom(
        state,
        candidate_identity=candidate.candidate_id,
        disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
        atom=quantity_atom,
        governed_object_or_scope="project cost",
        adjudicator_identity="owner",
        adjudicated_at=NOW,
        decision_rationale="Owner accepted the complete quantity.",
    )
    candidate, uncertainty_atom = _atom(
        state,
        uncertainty,
        "uncertainty",
        AtomKind.UNCERTAINTY_STATUS,
        targets=("event-proposition",),
    )
    state = service.decide_fact_atom(
        state,
        candidate_identity=candidate.candidate_id,
        disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
        atom=uncertainty_atom,
        uncertainty_target_atom_ids=("event-proposition",),
        adjudicator_identity="owner",
        adjudicated_at=NOW,
        decision_rationale="Owner accepted the uncertainty boundary.",
    )
    decided = {item.candidate_identity for item in state.fact_atom_receipts}
    for remaining in state.candidates:
        if remaining.candidate_id not in decided:
            state = service.decide_fact_atom(
                state,
                candidate_identity=remaining.candidate_id,
                disposition=CandidateOwnerDispositionV1.REJECT,
                atom=None,
                adjudicator_identity="owner",
                adjudicated_at=NOW,
                decision_rationale="Owner rejected this residual candidate.",
            )
    state = service.finalize_fact_atoms(state)
    claim_state = service.adjudicate_mechanic_claim(
        state,
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        atom_roles=(
            AtomRoleBindingV1(
                role="complete_quantity", atom_ids=("complete-quantity",)
            ),
            AtomRoleBindingV1(role="quantity_object", atom_ids=("event-proposition",)),
        ),
        satisfied_boundary_codes=(
            "no_value_judgment",
            "preserve_approximation_attribution_period_denominator_scope",
        ),
        adjudicator_identity="owner",
        adjudicated_at=NOW,
    )
    finalized = service.finalize_claims(claim_state)
    assert finalized.lifecycle is AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED
    assert finalized.eligibility is not None
    assert finalized.eligibility.shortlist
    assert store.load(1) == finalized
    assert store.load(1).model_dump_json() == finalized.model_dump_json()

    with pytest.raises(VoiceAdjudicationError, match="exact source span"):
        service.decide_fact_atom(
            finalized,
            candidate_identity=candidate.candidate_id,
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
            atom=uncertainty_atom.model_copy(update={"proposition": "Parafrază."}),
            adjudicator_identity="owner",
            adjudicated_at=NOW,
            decision_rationale="Invalid paraphrase must fail.",
            supersession_reason="revision",
        )

    revised = service.decide_fact_atom(
        finalized,
        candidate_identity=candidate.candidate_id,
        disposition=CandidateOwnerDispositionV1.REJECT,
        atom=None,
        adjudicator_identity="owner",
        adjudicated_at=NOW,
        decision_rationale="Owner rejected the previously accepted boundary.",
        supersession_reason="owner rejected boundary",
    )
    assert revised.mechanic_claims == () and revised.eligibility is None
    assert revised.fact_atom_receipts[-1].prior_receipt_identity is not None


def test_no_claim_and_stale_are_safe_persisted_outcomes(tmp_path):
    service, store, state, _ = _started(tmp_path)
    with pytest.raises(VoiceAdjudicationError, match="not finalized"):
        service.adjudicate_mechanic_claim(
            state,
            mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
            atom_roles=(AtomRoleBindingV1(role="quantity", atom_ids=("missing",)),),
            satisfied_boundary_codes=(),
            adjudicator_identity="owner",
            adjudicated_at=NOW,
        )
    no_claim = service.choose_no_claim(state, reason="Nicio construcție sigură.")
    assert no_claim.lifecycle is AdjudicationLifecycleV1.NO_CLAIM
    assert no_claim.eligibility is not None
    assert no_claim.eligibility.shortlist == ()
    assert store.load(1) == no_claim

    stale = service.mark_stale(no_claim, reason="semantic_draft_revision_changed")
    assert stale.lifecycle is AdjudicationLifecycleV1.STALE
    assert stale.eligibility is None
    assert store.load(1) == stale


def test_story_change_marks_stale_but_repetition_only_rebuilds_downstream(tmp_path):
    service, _, state, _ = _started(tmp_path)
    changed_binding = state.binding.model_copy(
        update={"semantic_draft_revision_identity": "sha256:" + "9" * 64}
    )
    stale = service.load_for_story(
        binding=changed_binding,
        authority_texts=state.authority_texts,
        repetition_snapshot=state.repetition_snapshot,
    )
    assert stale.lifecycle is AdjudicationLifecycleV1.STALE
    assert stale.stale_reason == "story_revision_or_binding_changed"
