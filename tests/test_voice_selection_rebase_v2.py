from datetime import UTC, datetime

import pytest

import pastila_scout.voice_selection_rebase_v2 as subject
from pastila_scout.expression_catalog_v2.eligibility import _sealed as expression_sealed
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
)
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.engine import (
    _sealed,
    finalize_selection_receipt,
)
from pastila_scout.voice_eligibility_v2.models import (
    ProgramCandidateV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
)
from pastila_scout.voice_fact_atoms_v2.models import VoiceFactAtomBundleV1
from pastila_scout.voice_repetition_v2 import (
    derive_repetition_snapshot_v1,
    finalize_ledger_v1,
    finalize_order_authority_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
    VoiceRepetitionLedgerV1,
)

ZERO = "sha256:" + "0" * 64
SHA = "sha256:" + "1" * 64
NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _order():
    return finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id="episode",
            episode_ordinal=1,
            ordered_event_ids=(1, 2),
            publication_state=PublicationStateV1.UNPUBLISHED,
        )
    )


def _ledger():
    return finalize_ledger_v1(VoiceRepetitionLedgerV1())


def _result(snapshot, candidate_id=SHA):
    candidate = ProgramCandidateV1(
        candidate_id=candidate_id,
        program_id="NEL_DELAYED_QUANTITY_REVEAL_V1",
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        cadence_signature="cadence",
        surface_ids=("surface",),
        repetition_signature="signature",
    )
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity=SHA,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        mechanic_outcomes=(),
        program_outcomes=(),
        shortlist=(candidate,),
        result_identity=ZERO,
    )
    return provisional.model_copy(
        update={"result_identity": _sealed(provisional, "result_identity")}
    )


def _receipt(result, snapshot):
    provisional = VoiceOwnerSelectionReceiptV1(
        fact_atom_bundle_identity=SHA,
        eligibility_result_identity=result.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        shortlist_candidate_ids=(result.shortlist[0].candidate_id,),
        selection_kind=SelectionKindV1.PROGRAM,
        selected_candidate_id=result.shortlist[0].candidate_id,
        selector_identity="owner",
        selected_at=NOW,
        receipt_identity=ZERO,
    )
    return finalize_selection_receipt(provisional, result=result, snapshot=snapshot)


def _empty_expression(result, snapshot):
    provisional = ExpressionEligibilityResultV1(
        fact_atom_bundle_identity=SHA,
        program_eligibility_result_identity=result.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        outcomes=(),
        shortlist=(),
    )
    return provisional.model_copy(
        update={"result_identity": expression_sealed(provisional, "result_identity")}
    )


def test_same_program_rebases_to_fresh_snapshot_and_preserves_lineage(
    monkeypatch, tmp_path
):
    ledger = _ledger()
    order = _order()
    old_snapshot = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=2
    ).snapshot
    old_result = _result(old_snapshot)
    old_receipt = _receipt(old_result, old_snapshot)
    monkeypatch.setattr(
        subject,
        "evaluate_voice_eligibility_v1",
        lambda **kw: _result(kw["repetition_snapshot"], "sha256:" + "2" * 64),
    )
    rebase = subject.rebase_owner_selection_receipts_v1(
        event_id=2,
        semantic_draft_revision_identity=SHA,
        bundle=VoiceFactAtomBundleV1.model_construct(bundle_identity=SHA),
        claims=(),
        prior_eligibility=old_result,
        prior_program_receipt=old_receipt,
        prior_expression_eligibility=None,
        prior_expression_receipt=None,
        ledger=ledger,
        order_authority=order,
    )
    assert rebase.prior_program_receipt_identity == old_receipt.receipt_identity
    assert (
        rebase.rebased_program_receipt.receipt_identity != old_receipt.receipt_identity
    )
    assert rebase.rebased_program_receipt.selected_candidate_id == "sha256:" + "2" * 64
    path = subject.persist_selection_rebase_v1(tmp_path, rebase)
    assert path.read_bytes()
    assert subject.persist_selection_rebase_v1(tmp_path, rebase) == path


def test_rebase_fails_closed_when_program_is_no_longer_eligible(monkeypatch):
    ledger = _ledger()
    order = _order()
    snapshot = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=2
    ).snapshot
    old_result = _result(snapshot)
    empty = old_result.model_copy(update={"shortlist": (), "result_identity": ZERO})
    empty = empty.model_copy(
        update={"result_identity": _sealed(empty, "result_identity")}
    )
    monkeypatch.setattr(subject, "evaluate_voice_eligibility_v1", lambda **kw: empty)
    with pytest.raises(
        subject.SelectionRebaseIntegrityError, match="became ineligible"
    ):
        subject.rebase_owner_selection_receipts_v1(
            event_id=2,
            semantic_draft_revision_identity=SHA,
            bundle=VoiceFactAtomBundleV1.model_construct(bundle_identity=SHA),
            claims=(),
            prior_eligibility=old_result,
            prior_program_receipt=_receipt(old_result, snapshot),
            prior_expression_eligibility=None,
            prior_expression_receipt=None,
            ledger=ledger,
            order_authority=order,
        )


def test_none_expression_cannot_silently_become_expression(monkeypatch):
    ledger = _ledger()
    order = _order()
    snapshot = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=2
    ).snapshot
    result = _result(snapshot)
    expression = _empty_expression(result, snapshot)
    monkeypatch.setattr(
        subject,
        "evaluate_voice_eligibility_v1",
        lambda **kw: _result(kw["repetition_snapshot"]),
    )
    # An incomplete expression tuple cannot be treated as Fără expresie.
    with pytest.raises(subject.SelectionRebaseIntegrityError, match="incomplete"):
        subject.rebase_owner_selection_receipts_v1(
            event_id=2,
            semantic_draft_revision_identity=SHA,
            bundle=VoiceFactAtomBundleV1.model_construct(bundle_identity=SHA),
            claims=(),
            prior_eligibility=result,
            prior_program_receipt=_receipt(result, snapshot),
            prior_expression_eligibility=expression,
            prior_expression_receipt=None,
            ledger=ledger,
            order_authority=order,
        )


def test_explicit_none_rebases_only_when_both_shortlists_are_empty():
    ledger = _ledger()
    order = _order()
    snapshot = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=2
    ).snapshot
    selected = _result(snapshot)
    empty = selected.model_copy(update={"shortlist": (), "result_identity": ZERO})
    empty = empty.model_copy(
        update={"result_identity": _sealed(empty, "result_identity")}
    )
    prior = subject.EditorDeterministicVoiceApplicationServiceV2.select_program(
        result=empty,
        snapshot=snapshot,
        candidate_identity=None,
        owner_identity="owner",
        selected_at=NOW,
    )
    rebased = subject.rebase_explicit_none_receipt_v1(
        event_id=2,
        semantic_draft_revision_identity=SHA,
        ledger_identity=ledger.ledger_identity,
        prior_receipt=prior,
        fresh_snapshot=snapshot,
        fresh_eligibility=empty,
    )
    assert rebased.rebased_receipt.selection_kind is SelectionKindV1.NONE
    with pytest.raises(
        subject.SelectionRebaseIntegrityError, match="empty eligibility"
    ):
        subject.rebase_explicit_none_receipt_v1(
            event_id=2,
            semantic_draft_revision_identity=SHA,
            ledger_identity=ledger.ledger_identity,
            prior_receipt=prior,
            fresh_snapshot=snapshot,
            fresh_eligibility=selected,
        )
