from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pastila_scout.voice_deterministic_v2 import MechanicIdV1
from pastila_scout.voice_eligibility_v2 import (
    ZERO_IDENTITY,
    AtomRoleBindingV1,
    EligibilityStatusV1,
    MechanicEligibilityClaimV1,
    OptionalEnrichmentExtensionV1,
    RepetitionUseV1,
    SelectionKindV1,
    UnknownVoiceEligibilityStateVersionError,
    VoiceEligibilityIntegrityError,
    VoiceEligibilityStateStoreV1,
    VoiceEligibilityStateV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
    finalize_repetition_snapshot,
    finalize_selection_receipt,
    finalize_state_identity,
)
from pastila_scout.voice_fact_atoms_v2 import (
    AtomKind,
    AuthorityClass,
    AuthorityPassageV1,
    CandidateKind,
    CompleteQuantityV1,
    FactAtomV1,
    SurfaceCandidateV1,
    VoiceFactAtomBundleV1,
    finalize_bundle_identity,
)

SHA = "sha256:" + "1" * 64


def _candidate(candidate_id: str, text: str) -> SurfaceCandidateV1:
    evidence = AuthorityPassageV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=SHA,
        source_identity="event-source",
        passage=text,
        start=0,
        end=len(text),
    )
    provisional = SurfaceCandidateV1(
        candidate_id=candidate_id,
        kind=CandidateKind.EXACT_SPAN,
        evidence=evidence,
        normalized_key=text.casefold(),
        extraction_receipt_identity=SHA,
    )
    return provisional


def _bundle() -> VoiceFactAtomBundleV1:
    candidates = (
        _candidate("c-prop", "Proiectul este un coteț mobil."),
        _candidate("c-q1", "aproximativ 37.000 de euro"),
        _candidate("c-q2", "83 de beneficiari"),
        _candidate("c-unknown", "motivul nu este cunoscut"),
    )
    atoms = (
        FactAtomV1(
            atom_id="prop",
            kind=AtomKind.EVENT_PROPOSITION,
            proposition="Proiectul este un coteț mobil.",
            authority_class=AuthorityClass.EVENT,
            evidence=(candidates[0].evidence,),
            candidate_ids=("c-prop",),
        ),
        FactAtomV1(
            atom_id="q1",
            kind=AtomKind.COMPLETE_QUANTITY,
            proposition="aproximativ 37.000 de euro",
            authority_class=AuthorityClass.EVENT,
            evidence=(candidates[1].evidence,),
            candidate_ids=("c-q1",),
            quantity=CompleteQuantityV1(
                exact_surface="aproximativ 37.000 de euro",
                numeric_surface="37.000",
                approximation="aproximativ",
                bound_semantics="approximate",
                unit_or_currency="euro",
                subject_scope="proiect",
            ),
        ),
        FactAtomV1(
            atom_id="q2",
            kind=AtomKind.COMPLETE_QUANTITY,
            proposition="83 de beneficiari",
            authority_class=AuthorityClass.EVENT,
            evidence=(candidates[2].evidence,),
            candidate_ids=("c-q2",),
            quantity=CompleteQuantityV1(
                exact_surface="83 de beneficiari",
                numeric_surface="83",
                bound_semantics="exact",
                unit_or_currency="beneficiari",
                subject_scope="persoane",
            ),
        ),
        FactAtomV1(
            atom_id="unknown",
            kind=AtomKind.UNCERTAINTY_STATUS,
            proposition="motivul nu este cunoscut",
            authority_class=AuthorityClass.EVENT,
            evidence=(candidates[3].evidence,),
            candidate_ids=("c-unknown",),
            qualification_target_atom_ids=("prop",),
        ),
    )
    return finalize_bundle_identity(
        VoiceFactAtomBundleV1(
            revision=1,
            semantic_draft_revision_identity=SHA,
            event_id=7,
            story_position=1,
            factual_summary_identity=SHA,
            event_authority_identity=SHA,
            candidates=candidates,
            atoms=atoms,
            adjudication_receipt_identities=(SHA,),
            bundle_identity=ZERO_IDENTITY,
        )
    )


NUMERIC_BOUNDARIES = tuple(
    sorted(
        {
            "axes_remain_separate",
            "fiction_is_not_real_benchmark",
            "no_arithmetic_conversion_ratio_or_average",
            "no_causality_equivalence_or_derived_value",
            "no_normative_quantity_judgment",
            "no_real_physical_display_claim",
            "no_value_judgment",
            "preserve_approximation_attribution_period_denominator_scope",
        }
    )
)


def _claim(
    bundle,
    mechanic=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
    *,
    boundaries=NUMERIC_BOUNDARIES,
    atom_ids=("prop", "q1", "q2"),
):
    provisional = MechanicEligibilityClaimV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        mechanic_id=mechanic,
        atom_roles=(AtomRoleBindingV1(role="governed_atoms", atom_ids=atom_ids),),
        satisfied_boundary_codes=boundaries,
        adjudication_receipt_identity=SHA,
        claim_identity=ZERO_IDENTITY,
    )
    return finalize_claim_identity(provisional)


def _snapshot(*uses, episode=3, position=2):
    return finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=episode,
            current_story_position=position,
            uses=uses,
            snapshot_identity=ZERO_IDENTITY,
        )
    )


def _numeric_result(bundle=None, snapshot=None):
    bundle = bundle or _bundle()
    snapshot = snapshot or _snapshot()
    return (
        bundle,
        snapshot,
        evaluate_voice_eligibility_v1(
            bundle=bundle,
            claims=(_claim(bundle),),
            repetition_snapshot=snapshot,
        ),
    )


def test_mechanic_and_program_eligibility_are_typed_and_fail_closed():
    bundle, _, result = _numeric_result()
    mechanic = {item.subject_id: item for item in result.mechanic_outcomes}
    assert (
        mechanic["NUMERIC_EXPECTATION_LADDER_V1"].status is EligibilityStatusV1.ELIGIBLE
    )
    assert (
        mechanic["FICTIONAL_INTAKE_OR_INTERFACE_V1"].status
        is EligibilityStatusV1.INELIGIBLE
    )
    assert [item.program_id for item in result.shortlist] == sorted(
        item.program_id for item in result.shortlist
    )
    assert len(result.shortlist) == 4

    weak = _claim(bundle, atom_ids=("prop",))
    blocked = evaluate_voice_eligibility_v1(
        bundle=bundle, claims=(weak,), repetition_snapshot=_snapshot()
    )
    assert not blocked.shortlist
    assert any(
        item.reason_codes == ("required_numeric_and_event_atoms_missing",)
        for item in blocked.mechanic_outcomes
    )


def test_program_frozen_boundaries_and_unknown_ids_fail_closed():
    bundle = _bundle()
    claim = _claim(bundle, boundaries=())
    result = evaluate_voice_eligibility_v1(
        bundle=bundle, claims=(claim,), repetition_snapshot=_snapshot()
    )
    assert not result.shortlist
    assert all(
        "frozen_boundary_claim_requirement" in item.reason_codes
        for item in result.program_outcomes
        if item.subject_id.startswith("NEL_")
    )
    with pytest.raises(
        VoiceEligibilityIntegrityError, match="unknown reusable program"
    ):
        evaluate_voice_eligibility_v1(
            bundle=bundle,
            claims=(_claim(bundle),),
            repetition_snapshot=_snapshot(),
            requested_program_ids=("UNKNOWN_PROGRAM_V9",),
        )
    with pytest.raises(ValidationError):
        MechanicEligibilityClaimV1.model_validate(
            _claim(bundle).model_dump(mode="json") | {"mechanic_id": "UNKNOWN_V9"}
        )


def test_unclaimed_atoms_and_duplicate_role_atoms_cannot_satisfy_programs():
    bundle = _bundle()
    one_quantity = _claim(bundle, atom_ids=("prop", "q1"))
    result = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(one_quantity,),
        repetition_snapshot=_snapshot(),
        requested_program_ids=("NEL_TWO_AXIS_QUANTITY_CONTRAST_V1",),
    )
    assert not result.shortlist
    assert "complete_quantity_requirement" in result.program_outcomes[0].reason_codes

    with pytest.raises(ValidationError, match="multiple mechanic roles"):
        MechanicEligibilityClaimV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
            atom_roles=(
                AtomRoleBindingV1(role="first", atom_ids=("q1",)),
                AtomRoleBindingV1(role="second", atom_ids=("q1",)),
            ),
            adjudication_receipt_identity=SHA,
            claim_identity=ZERO_IDENTITY,
        )


def test_stale_bundle_claim_and_missing_history_fail_closed():
    bundle = _bundle()
    stale = finalize_claim_identity(
        _claim(bundle).model_copy(
            update={"fact_atom_bundle_identity": SHA, "claim_identity": ZERO_IDENTITY}
        )
    )
    with pytest.raises(VoiceEligibilityIntegrityError, match="stale"):
        evaluate_voice_eligibility_v1(
            bundle=bundle, claims=(stale,), repetition_snapshot=_snapshot()
        )
    with pytest.raises(ValidationError):
        VoiceRepetitionSnapshotV1.model_validate(
            {
                "current_episode_ordinal": 1,
                "current_story_position": 1,
                "history_complete": False,
                "snapshot_identity": ZERO_IDENTITY,
            }
        )


def test_repetition_adjacency_and_cross_episode_cooldown_block():
    bundle = _bundle()
    baseline = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(_claim(bundle),),
        repetition_snapshot=_snapshot(),
        requested_program_ids=("NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",),
    )
    chosen = baseline.shortlist[0]
    prior = RepetitionUseV1(
        episode_ordinal=3,
        story_position=1,
        mechanic_id=chosen.mechanic_id,
        program_id="another-program",
        cadence_signature="another-cadence",
        surface_ids=(),
    )
    adjacent = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(_claim(bundle),),
        repetition_snapshot=_snapshot(prior),
        requested_program_ids=(chosen.program_id,),
    )
    assert not adjacent.shortlist
    assert "adjacent_mechanic_block" in adjacent.program_outcomes[0].reason_codes

    old = prior.model_copy(
        update={
            "episode_ordinal": 2,
            "surface_ids": chosen.surface_ids,
            "mechanic_id": MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        }
    )
    cooldown = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(_claim(bundle),),
        repetition_snapshot=_snapshot(old),
        requested_program_ids=(chosen.program_id,),
    )
    assert not cooldown.shortlist
    assert "surface_cross_episode_cooldown" in cooldown.program_outcomes[0].reason_codes


def test_explicit_program_and_none_selection_are_bound_to_shortlist():
    bundle, snapshot, result = _numeric_result()
    common = {
        "fact_atom_bundle_identity": bundle.bundle_identity,
        "eligibility_result_identity": result.result_identity,
        "repetition_snapshot_identity": snapshot.snapshot_identity,
        "shortlist_candidate_ids": tuple(
            item.candidate_id for item in result.shortlist
        ),
        "selector_identity": "owner",
        "selected_at": datetime(2026, 8, 22, tzinfo=UTC),
        "receipt_identity": ZERO_IDENTITY,
    }
    selected = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(
            **common,
            selection_kind=SelectionKindV1.PROGRAM,
            selected_candidate_id=result.shortlist[0].candidate_id,
        ),
        result=result,
        snapshot=snapshot,
    )
    omitted = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(**common, selection_kind=SelectionKindV1.NONE),
        result=result,
        snapshot=snapshot,
    )
    assert selected.selected_candidate_id == result.shortlist[0].candidate_id
    assert omitted.selection_kind is SelectionKindV1.NONE
    with pytest.raises(ValidationError, match="not in the frozen shortlist"):
        VoiceOwnerSelectionReceiptV1(
            **common,
            selection_kind=SelectionKindV1.PROGRAM,
            selected_candidate_id=SHA,
        )


def test_inactive_enrichment_cannot_carry_or_emit_expression_behavior():
    _, _, result = _numeric_result()
    assert result.enrichment == OptionalEnrichmentExtensionV1()
    assert not result.enrichment.candidates
    assert result.enrichment.emitted_surface is None
    with pytest.raises(ValidationError, match="cannot carry behavior"):
        OptionalEnrichmentExtensionV1(candidates=({"expression": "anything"},))


def test_state_round_trip_is_canonical_and_unknown_version_fails(tmp_path):
    bundle, snapshot, result = _numeric_result()
    receipt = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            eligibility_result_identity=result.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=tuple(x.candidate_id for x in result.shortlist),
            selection_kind=SelectionKindV1.NONE,
            selector_identity="owner",
            selected_at=datetime(2026, 8, 22, tzinfo=UTC),
            receipt_identity=ZERO_IDENTITY,
        ),
        result=result,
        snapshot=snapshot,
    )
    state = finalize_state_identity(
        VoiceEligibilityStateV1(
            repetition_snapshot=snapshot,
            eligibility_result=result,
            selection_receipt=receipt,
        )
    )
    store = VoiceEligibilityStateStoreV1(tmp_path / "eligibility.json")
    first_identity = store.save(state)
    assert store.load() == state
    assert store.save(store.load()) == first_identity

    payload = state.model_dump(mode="json") | {"schema_version": "2"}
    (tmp_path / "eligibility.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UnknownVoiceEligibilityStateVersionError):
        store.load()


def test_selection_cannot_reinterpret_legacy_expression_receipts():
    fields = VoiceOwnerSelectionReceiptV1.model_fields
    assert "usage_receipts" not in fields
    assert "expression_usage_receipt" not in fields
