"""Deterministic eligibility and repetition filtering without prose generation."""

from __future__ import annotations

from collections import Counter

from pastila_scout.voice_fact_atoms_v2 import AtomKind, VoiceFactAtomBundleV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    bundle_payload_identity,
    canonical_identity,
)

from .library import PROGRAM_BY_ID_V1, PROGRAM_SPECS_V1, REUSABLE_MECHANICS_V1
from .models import (
    ZERO_IDENTITY,
    EligibilityOutcomeV1,
    EligibilityStatusV1,
    MechanicEligibilityClaimV1,
    OptionalEnrichmentExtensionV1,
    ProgramCandidateV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)

BOUNDARY_KINDS = frozenset(
    {
        AtomKind.ALLEGATION_STATUS,
        AtomKind.UNCERTAINTY_STATUS,
        AtomKind.CAUSAL_BOUNDARY,
        AtomKind.NEGATIVE_BOUNDARY,
    }
)


class VoiceEligibilityIntegrityError(ValueError):
    pass


def _sealed(value, field: str):
    return canonical_identity(value.model_copy(update={field: ZERO_IDENTITY}))


def finalize_claim_identity(claim: MechanicEligibilityClaimV1):
    return claim.model_copy(update={"claim_identity": _sealed(claim, "claim_identity")})


def finalize_repetition_snapshot(snapshot: VoiceRepetitionSnapshotV1):
    return snapshot.model_copy(
        update={"snapshot_identity": _sealed(snapshot, "snapshot_identity")}
    )


def _validate_inputs(bundle, claims, snapshot):
    if bundle.bundle_identity != bundle_payload_identity(bundle):
        raise VoiceEligibilityIntegrityError("fact-atom bundle identity mismatch")
    if snapshot.snapshot_identity != _sealed(snapshot, "snapshot_identity"):
        raise VoiceEligibilityIntegrityError("repetition snapshot identity mismatch")
    atom_ids = {item.atom_id for item in bundle.atoms}
    for claim in claims:
        if claim.claim_identity != _sealed(claim, "claim_identity"):
            raise VoiceEligibilityIntegrityError("mechanic claim identity mismatch")
        if claim.fact_atom_bundle_identity != bundle.bundle_identity:
            raise VoiceEligibilityIntegrityError(
                "stale mechanic claim fact-atom bundle"
            )
        if claim.mechanic_id not in REUSABLE_MECHANICS_V1:
            raise VoiceEligibilityIntegrityError("unknown reusable mechanic")
        referenced = {atom for role in claim.atom_roles for atom in role.atom_ids}
        if not referenced <= atom_ids:
            raise VoiceEligibilityIntegrityError(
                "mechanic claim references unknown atom"
            )


def _mechanic_reasons(bundle, claim):
    atoms = {item.atom_id: item for item in bundle.atoms}
    claimed = [atoms[item] for role in claim.atom_roles for item in role.atom_ids]
    kinds = Counter(item.kind for item in claimed)
    if claim.mechanic_id.value == "NUMERIC_EXPECTATION_LADDER_V1":
        if (
            kinds[AtomKind.COMPLETE_QUANTITY] < 1
            or kinds[AtomKind.EVENT_PROPOSITION] < 1
        ):
            return ("required_numeric_and_event_atoms_missing",)
    elif claim.mechanic_id.value == "FICTIONAL_INTAKE_OR_INTERFACE_V1":
        if kinds[AtomKind.EVENT_PROPOSITION] < 2:
            return ("two_event_propositions_required",)
    elif claim.mechanic_id.value == "UNCERTAINTY_SANDWICHED_FICTION_V1" and (
        kinds[AtomKind.EVENT_PROPOSITION] < 1
        or not any(item.kind in BOUNDARY_KINDS for item in claimed)
    ):
        return ("event_anchor_and_exact_boundary_required",)
    return ()


def _repetition_reasons(spec, snapshot):
    current = [
        u
        for u in snapshot.uses
        if u.episode_ordinal == snapshot.current_episode_ordinal
    ]
    if (
        sum(u.program_id == spec.program_id for u in current)
        >= spec.episode_use_ceiling
    ):
        return ("program_episode_ceiling",)
    if sum(u.mechanic_id == spec.mechanic_id for u in current) >= 2:
        return ("mechanic_episode_ceiling",)
    previous = [
        u for u in current if u.story_position == snapshot.current_story_position - 1
    ]
    if previous and previous[-1].mechanic_id == spec.mechanic_id:
        return ("adjacent_mechanic_block",)
    if any(u.cadence_signature == spec.cadence_signature for u in current):
        return ("cadence_episode_block",)
    if any(set(u.surface_ids) & set(spec.surface_ids) for u in current):
        return ("surface_episode_block",)
    recent = [
        u
        for u in snapshot.uses
        if u.episode_ordinal < snapshot.current_episode_ordinal
        and snapshot.current_episode_ordinal - u.episode_ordinal <= 2
    ]
    if any(set(u.surface_ids) & set(spec.surface_ids) for u in recent):
        return ("surface_cross_episode_cooldown",)
    return ()


def evaluate_voice_eligibility_v1(
    *,
    bundle: VoiceFactAtomBundleV1,
    claims: tuple[MechanicEligibilityClaimV1, ...],
    repetition_snapshot: VoiceRepetitionSnapshotV1,
    requested_program_ids: tuple[str, ...] | None = None,
) -> VoiceEligibilityResultV1:
    _validate_inputs(bundle, claims, repetition_snapshot)
    if requested_program_ids is not None:
        if len(requested_program_ids) != len(set(requested_program_ids)):
            raise VoiceEligibilityIntegrityError("duplicate requested program")
        unknown = set(requested_program_ids) - PROGRAM_BY_ID_V1.keys()
        if unknown:
            raise VoiceEligibilityIntegrityError("unknown reusable program")
    by_mechanic = {item.mechanic_id: item for item in claims}
    if len(by_mechanic) != len(claims):
        raise VoiceEligibilityIntegrityError("duplicate mechanic claim")
    mechanic_outcomes = []
    eligible_mechanics = set()
    for mechanic in sorted(REUSABLE_MECHANICS_V1, key=lambda item: item.value):
        claim = by_mechanic.get(mechanic)
        reasons = (
            ("missing_explicit_adjudicated_claim",)
            if claim is None
            else _mechanic_reasons(bundle, claim)
        )
        status = (
            EligibilityStatusV1.INELIGIBLE if reasons else EligibilityStatusV1.ELIGIBLE
        )
        if status is EligibilityStatusV1.ELIGIBLE:
            eligible_mechanics.add(mechanic)
        mechanic_outcomes.append(
            EligibilityOutcomeV1(
                subject_id=mechanic.value,
                status=status,
                reason_codes=reasons or ("typed_claim_and_atoms_satisfied",),
            )
        )
    program_outcomes = []
    candidates = []
    atoms_by_id = {item.atom_id: item for item in bundle.atoms}
    specs = (
        PROGRAM_SPECS_V1
        if requested_program_ids is None
        else tuple(PROGRAM_BY_ID_V1[item] for item in requested_program_ids)
    )
    for spec in sorted(specs, key=lambda item: item.program_id):
        reasons = []
        claim = by_mechanic.get(spec.mechanic_id)
        claimed_atoms = (
            tuple(
                atoms_by_id[atom_id]
                for role in claim.atom_roles
                for atom_id in role.atom_ids
            )
            if claim is not None
            else ()
        )
        if spec.mechanic_id not in eligible_mechanics or claim is None:
            reasons.append("parent_mechanic_ineligible")
        if (
            sum(a.kind is AtomKind.EVENT_PROPOSITION for a in claimed_atoms)
            < spec.minimum_event_propositions
        ):
            reasons.append("event_proposition_requirement")
        if (
            sum(a.kind is AtomKind.COMPLETE_QUANTITY for a in claimed_atoms)
            < spec.minimum_complete_quantities
        ):
            reasons.append("complete_quantity_requirement")
        if spec.requires_boundary_atom and not any(
            a.kind in BOUNDARY_KINDS for a in claimed_atoms
        ):
            reasons.append("boundary_atom_requirement")
        if claim is not None and not set(spec.required_boundary_codes) <= set(
            claim.satisfied_boundary_codes
        ):
            reasons.append("frozen_boundary_claim_requirement")
        reasons.extend(_repetition_reasons(spec, repetition_snapshot))
        reasons = sorted(set(reasons))
        status = (
            EligibilityStatusV1.INELIGIBLE if reasons else EligibilityStatusV1.ELIGIBLE
        )
        program_outcomes.append(
            EligibilityOutcomeV1(
                subject_id=spec.program_id,
                status=status,
                reason_codes=tuple(reasons) or ("all_typed_gates_satisfied",),
            )
        )
        if status is EligibilityStatusV1.ELIGIBLE:
            payload = f"{bundle.bundle_identity}|{repetition_snapshot.snapshot_identity}|{spec.program_id}"
            candidate_id = canonical_identity(payload)
            candidates.append(
                ProgramCandidateV1(
                    candidate_id=candidate_id,
                    program_id=spec.program_id,
                    mechanic_id=spec.mechanic_id,
                    cadence_signature=spec.cadence_signature,
                    surface_ids=spec.surface_ids,
                    repetition_signature=f"{spec.mechanic_id.value}/{spec.program_id}/{spec.cadence_signature}",
                )
            )
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        repetition_snapshot_identity=repetition_snapshot.snapshot_identity,
        mechanic_outcomes=tuple(mechanic_outcomes),
        program_outcomes=tuple(program_outcomes),
        shortlist=tuple(candidates),
        enrichment=OptionalEnrichmentExtensionV1(),
        result_identity=ZERO_IDENTITY,
    )
    return provisional.model_copy(
        update={"result_identity": _sealed(provisional, "result_identity")}
    )


def finalize_selection_receipt(
    receipt: VoiceOwnerSelectionReceiptV1,
    *,
    result: VoiceEligibilityResultV1,
    snapshot: VoiceRepetitionSnapshotV1,
) -> VoiceOwnerSelectionReceiptV1:
    if result.result_identity != _sealed(result, "result_identity"):
        raise VoiceEligibilityIntegrityError("eligibility result identity mismatch")
    if snapshot.snapshot_identity != result.repetition_snapshot_identity:
        raise VoiceEligibilityIntegrityError("selection repetition snapshot mismatch")
    expected = tuple(item.candidate_id for item in result.shortlist)
    if receipt.shortlist_candidate_ids != expected:
        raise VoiceEligibilityIntegrityError("selection shortlist mismatch")
    if (
        receipt.fact_atom_bundle_identity != result.fact_atom_bundle_identity
        or receipt.eligibility_result_identity != result.result_identity
        or receipt.repetition_snapshot_identity != snapshot.snapshot_identity
    ):
        raise VoiceEligibilityIntegrityError("selection binding mismatch")
    return receipt.model_copy(
        update={"receipt_identity": _sealed(receipt, "receipt_identity")}
    )


__all__ = [
    "VoiceEligibilityIntegrityError",
    "evaluate_voice_eligibility_v1",
    "finalize_claim_identity",
    "finalize_repetition_snapshot",
    "finalize_selection_receipt",
]
