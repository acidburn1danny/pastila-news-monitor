from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pastila_scout.desktop_v1.views import _DesktopMainWindowV1
from pastila_scout.desktop_v1.voice_adjudication_actions import (
    VoiceDesktopAdjudicationActionV1,
    VoiceDesktopFactAtomInputV1,
)
from pastila_scout.desktop_v1.voice_adjudication_presentation import (
    present_voice_adjudication_v1,
)
from pastila_scout.desktop_v1.voice_adjudication_workflow import (
    VoiceDesktopAdjudicationCoordinatorV1,
)
from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    CandidateOwnerDispositionV1,
    VoiceAdjudicationError,
)
from pastila_scout.voice_fact_atoms_v2.models import AtomKind
from tests.voice_v2_synthetic_fixtures import started_adjudication_v2

NOW = datetime(2026, 8, 23, 14, tzinfo=UTC)


def test_daily_use_quantity_hides_schema_and_derives_safe_payload():
    payload = _DesktopMainWindowV1._daily_use_quantity(
        "peste 55.000 de dolari", "sprijinul acordat pentru fiecare copil"
    )
    assert payload == {
        "exact_surface": "peste 55.000 de dolari",
        "numeric_surface": "55.000",
        "approximation": "peste",
        "bound_semantics": "lower_bound",
        "unit_or_currency": "dolari",
        "subject_scope": "sprijinul acordat pentru fiecare copil",
    }
    assert _DesktopMainWindowV1._daily_use_quantity("55.000", "sprijin") is None


def _action(**values):
    return VoiceDesktopAdjudicationActionV1(
        event_id=1,
        owner_identity="desktop-owner",
        occurred_at=NOW,
        **values,
    )


def test_structured_fact_actions_partial_restart_and_terminal_finalization(tmp_path):
    service, store, state, _ = started_adjudication_v2(tmp_path)
    coordinator = VoiceDesktopAdjudicationCoordinatorV1(service)
    first = state.candidates[0]
    partial = coordinator.dispatch(
        _action(
            action="decide_fact",
            candidate_identity=first.candidate_id,
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
            atom_input=VoiceDesktopFactAtomInputV1(
                atom_id="owner-fact-1", atom_kind=AtomKind.EVENT_PROPOSITION
            ),
            governed_object_or_scope="owner-confirmed event proposition",
            decision_rationale="Owner accepted the proposition.",
        )
    )
    assert partial.lifecycle is AdjudicationLifecycleV1.FACT_ATOMS_PARTIAL
    assert store.load(1) == partial
    presentation = present_voice_adjudication_v1(store.load(1))
    assert presentation.title == "Adjudicare factuală în curs"
    assert presentation.candidates[0].exact_text == first.evidence.passage
    assert presentation.candidates[0].source_label == first.evidence.source_identity
    assert presentation.candidates[0].extraction_policy == (
        "voice-fact-candidate-extraction-v1"
    )
    assert presentation.candidates[0].disposition == "accept_typed_atom"

    with pytest.raises(VoiceAdjudicationError, match="terminal owner disposition"):
        coordinator.dispatch(_action(action="finalize_facts"))

    second = state.candidates[1]
    coordinator.dispatch(
        _action(
            action="decide_fact",
            candidate_identity=second.candidate_id,
            disposition=CandidateOwnerDispositionV1.REQUIRES_QUALIFICATION,
            governed_object_or_scope="qualification required",
            decision_rationale="Owner requires qualification.",
        )
    )
    with pytest.raises(VoiceAdjudicationError, match="terminal owner disposition"):
        coordinator.dispatch(_action(action="finalize_facts"))
    revised = coordinator.dispatch(
        _action(
            action="decide_fact",
            candidate_identity=second.candidate_id,
            disposition=CandidateOwnerDispositionV1.REJECT,
            supersession_reason="Owner resolved qualification by rejection.",
            decision_rationale="Owner rejected the qualified candidate.",
        )
    )
    assert revised.fact_atom_receipts[-1].prior_receipt_identity is not None

    decided = {item.candidate_identity for item in revised.fact_atom_receipts}
    for candidate in revised.candidates:
        if candidate.candidate_id not in decided:
            revised = coordinator.dispatch(
                _action(
                    action="decide_fact",
                    candidate_identity=candidate.candidate_id,
                    disposition=CandidateOwnerDispositionV1.REJECT,
                    decision_rationale="Owner rejected the residual candidate.",
                )
            )
    finalized = coordinator.dispatch(_action(action="finalize_facts"))
    assert finalized.lifecycle is AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED
    assert store.load(1).model_dump_json() == finalized.model_dump_json()


def test_no_claim_is_explicit_and_model_free(tmp_path):
    service, store, _state, _ = started_adjudication_v2(tmp_path)
    coordinator = VoiceDesktopAdjudicationCoordinatorV1(service)
    no_claim = coordinator.dispatch(
        _action(
            action="choose_no_claim",
            no_claim_reason="Owner found no safe editorial relationship.",
        )
    )
    assert no_claim.lifecycle is AdjudicationLifecycleV1.NO_CLAIM
    assert no_claim.eligibility.shortlist == ()
    assert present_voice_adjudication_v1(no_claim).title == "Fără construcție sigură"
    assert store.load(1) == no_claim
    assert service.model_calls == service.provider_calls == service.model_loads == 0


def test_action_contract_rejects_incomplete_or_naive_payloads():
    with pytest.raises(ValueError, match="typed fact acceptance"):
        _action(
            action="decide_fact",
            candidate_identity="candidate:1",
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
        )
    with pytest.raises(ValueError, match="NO CLAIM"):
        _action(action="choose_no_claim")
