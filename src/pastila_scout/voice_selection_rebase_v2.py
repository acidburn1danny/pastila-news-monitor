"""Governed rebasing of unchanged owner choices onto fresh repetition state."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
)
from pastila_scout.expression_catalog_v2.eligibility import _sealed as expression_sealed
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoiceWorkspaceStoreV2,
)
from pastila_scout.voice_eligibility_v2 import evaluate_voice_eligibility_v1
from pastila_scout.voice_eligibility_v2.models import (
    MechanicEligibilityClaimV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2.models import VoiceFactAtomBundleV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from pastila_scout.voice_repetition_v2 import derive_repetition_snapshot_v1
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    VoiceRepetitionLedgerV1,
)
from pastila_scout.voice_repetition_v2.persistence import atomic_write

SHA = r"^sha256:[0-9a-f]{64}$"
ZERO = "sha256:" + "0" * 64


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SelectionReceiptRebaseV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-selection-receipt-rebase"] = (
        "pastilaacida-voice-selection-receipt-rebase"
    )
    schema_version: Literal["1"] = "1"
    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA)
    ledger_identity: str = Field(pattern=SHA)
    prior_snapshot_identity: str = Field(pattern=SHA)
    fresh_snapshot_identity: str = Field(pattern=SHA)
    prior_program_receipt_identity: str = Field(pattern=SHA)
    rebased_program_receipt: VoiceOwnerSelectionReceiptV1
    prior_expression_receipt_identity: str | None = Field(default=None, pattern=SHA)
    rebased_expression_receipt: ExpressionOwnerSelectionReceiptV1 | None = None
    program_eligibility: VoiceEligibilityResultV1
    expression_eligibility: ExpressionEligibilityResultV1 | None = None
    decision_semantically_identical: Literal[True] = True
    non_repetition_inputs_identical: Literal[True] = True
    rebase_identity: str = Field(default=ZERO, pattern=SHA)


class ExplicitNoneReceiptRebaseV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-explicit-none-receipt-rebase"] = (
        "pastilaacida-voice-explicit-none-receipt-rebase"
    )
    schema_version: Literal["1"] = "1"
    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA)
    ledger_identity: str = Field(pattern=SHA)
    prior_receipt_identity: str = Field(pattern=SHA)
    prior_snapshot_identity: str = Field(pattern=SHA)
    fresh_snapshot_identity: str = Field(pattern=SHA)
    fresh_eligibility: VoiceEligibilityResultV1
    rebased_receipt: VoiceOwnerSelectionReceiptV1
    decision_semantically_identical: Literal[True] = True
    rebase_identity: str = Field(default=ZERO, pattern=SHA)


class SelectionRebaseIntegrityError(ValueError):
    pass


ExpressionReevaluator = Callable[
    [VoiceEligibilityResultV1, VoiceRepetitionSnapshotV1],
    ExpressionEligibilityResultV1,
]


def _finish(value: SelectionReceiptRebaseV1) -> SelectionReceiptRebaseV1:
    return value.model_copy(
        update={
            "rebase_identity": canonical_identity(
                value.model_dump(mode="json", exclude={"rebase_identity"})
            )
        }
    )


def rebase_explicit_none_receipt_v1(
    *,
    event_id: int,
    semantic_draft_revision_identity: str,
    ledger_identity: str,
    prior_receipt: VoiceOwnerSelectionReceiptV1,
    fresh_snapshot: VoiceRepetitionSnapshotV1,
    fresh_eligibility: VoiceEligibilityResultV1,
) -> ExplicitNoneReceiptRebaseV1:
    if (
        prior_receipt.selection_kind is not SelectionKindV1.NONE
        or prior_receipt.selected_candidate_id is not None
        or prior_receipt.shortlist_candidate_ids
        or fresh_eligibility.shortlist
    ):
        raise SelectionRebaseIntegrityError(
            "explicit NONE rebase requires unchanged empty eligibility"
        )
    receipt = EditorDeterministicVoiceApplicationServiceV2.select_program(
        result=fresh_eligibility,
        snapshot=fresh_snapshot,
        candidate_identity=None,
        owner_identity=prior_receipt.selector_identity,
        selected_at=prior_receipt.selected_at,
    )
    provisional = ExplicitNoneReceiptRebaseV1(
        event_id=event_id,
        semantic_draft_revision_identity=semantic_draft_revision_identity,
        ledger_identity=ledger_identity,
        prior_receipt_identity=prior_receipt.receipt_identity,
        prior_snapshot_identity=prior_receipt.repetition_snapshot_identity,
        fresh_snapshot_identity=fresh_snapshot.snapshot_identity,
        fresh_eligibility=fresh_eligibility,
        rebased_receipt=receipt,
    )
    return provisional.model_copy(
        update={
            "rebase_identity": canonical_identity(
                provisional.model_dump(mode="json", exclude={"rebase_identity"})
            )
        }
    )


def rebase_owner_selection_receipts_v1(
    *,
    event_id: int,
    semantic_draft_revision_identity: str,
    bundle: VoiceFactAtomBundleV1,
    claims: tuple[MechanicEligibilityClaimV1, ...],
    prior_eligibility: VoiceEligibilityResultV1,
    prior_program_receipt: VoiceOwnerSelectionReceiptV1,
    prior_expression_eligibility: ExpressionEligibilityResultV1 | None,
    prior_expression_receipt: ExpressionOwnerSelectionReceiptV1 | None,
    ledger: VoiceRepetitionLedgerV1,
    order_authority: EpisodeOrderAuthorityV1,
    expression_reevaluator: ExpressionReevaluator | None = None,
) -> SelectionReceiptRebaseV1:
    """Rebind the exact same owner choice; never choose an alternative."""

    if prior_program_receipt.selection_kind is not SelectionKindV1.PROGRAM:
        raise SelectionRebaseIntegrityError("only an explicit program can be rebased")
    old_candidate = next(
        (
            item
            for item in prior_eligibility.shortlist
            if item.candidate_id == prior_program_receipt.selected_candidate_id
        ),
        None,
    )
    if old_candidate is None:
        raise SelectionRebaseIntegrityError("prior program receipt is not reproducible")
    envelope = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order_authority, event_id=event_id
    )
    fresh = envelope.snapshot
    eligibility = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=claims,
        repetition_snapshot=fresh,
        requested_program_ids=(old_candidate.program_id,),
    )
    candidate = next(
        (
            item
            for item in eligibility.shortlist
            if item.program_id == old_candidate.program_id
        ),
        None,
    )
    if candidate is None:
        raise SelectionRebaseIntegrityError("owner-selected program became ineligible")
    if (
        candidate.mechanic_id != old_candidate.mechanic_id
        or candidate.cadence_signature != old_candidate.cadence_signature
        or candidate.surface_ids != old_candidate.surface_ids
        or candidate.repetition_signature != old_candidate.repetition_signature
    ):
        raise SelectionRebaseIntegrityError("owner-selected program semantics changed")
    program_receipt = EditorDeterministicVoiceApplicationServiceV2.select_program(
        result=eligibility,
        snapshot=fresh,
        candidate_identity=candidate.candidate_id,
        owner_identity=prior_program_receipt.selector_identity,
        selected_at=prior_program_receipt.selected_at,
    )

    expression_result = None
    expression_receipt = None
    if (prior_expression_eligibility is None) != (prior_expression_receipt is None):
        raise SelectionRebaseIntegrityError("prior expression tuple is incomplete")
    if prior_expression_receipt is not None:
        if expression_reevaluator is None:
            if prior_expression_eligibility.shortlist:
                raise SelectionRebaseIntegrityError(
                    "expression eligibility requires governed reevaluation"
                )
            provisional = prior_expression_eligibility.model_copy(
                update={
                    "program_eligibility_result_identity": eligibility.result_identity,
                    "repetition_snapshot_identity": fresh.snapshot_identity,
                    "result_identity": ZERO,
                }
            )
            expression_result = provisional.model_copy(
                update={
                    "result_identity": expression_sealed(provisional, "result_identity")
                }
            )
        else:
            expression_result = expression_reevaluator(eligibility, fresh)
        prior_kind = prior_expression_receipt.selection_kind
        prior_selected = prior_expression_receipt.selected_candidate_id
        selected = None
        if prior_kind is ExpressionSelectionKindV1.EXPRESSION:
            old_expression = next(
                item
                for item in prior_expression_eligibility.shortlist
                if item.candidate_id == prior_selected
            )
            match = next(
                (
                    item
                    for item in expression_result.shortlist
                    if item.expression_id == old_expression.expression_id
                    and item.surface_id == old_expression.surface_id
                    and item.relationship == old_expression.relationship
                ),
                None,
            )
            if match is None:
                raise SelectionRebaseIntegrityError(
                    "owner-selected expression became ineligible or changed"
                )
            selected = match.candidate_id
        elif prior_selected is not None:
            raise SelectionRebaseIntegrityError("Fără expresie changed meaning")
        expression_receipt = (
            EditorDeterministicVoiceApplicationServiceV2.select_expression(
                result=expression_result,
                snapshot=fresh,
                candidate_identity=selected,
                owner_identity=prior_expression_receipt.selector_identity,
                selected_at=prior_expression_receipt.selected_at,
            )
        )
        if expression_receipt.selection_kind is not prior_kind:
            raise SelectionRebaseIntegrityError("expression selection kind changed")

    return _finish(
        SelectionReceiptRebaseV1(
            event_id=event_id,
            semantic_draft_revision_identity=semantic_draft_revision_identity,
            ledger_identity=ledger.ledger_identity,
            prior_snapshot_identity=prior_program_receipt.repetition_snapshot_identity,
            fresh_snapshot_identity=fresh.snapshot_identity,
            prior_program_receipt_identity=prior_program_receipt.receipt_identity,
            rebased_program_receipt=program_receipt,
            prior_expression_receipt_identity=(
                None
                if prior_expression_receipt is None
                else prior_expression_receipt.receipt_identity
            ),
            rebased_expression_receipt=expression_receipt,
            program_eligibility=eligibility,
            expression_eligibility=expression_result,
        )
    )


def persist_selection_rebase_v1(root: Path, rebase: SelectionReceiptRebaseV1) -> Path:
    if _finish(rebase).rebase_identity != rebase.rebase_identity:
        raise SelectionRebaseIntegrityError("selection rebase identity mismatch")
    path = (
        root
        / "selection-rebases"
        / f"{rebase.rebase_identity.removeprefix('sha256:')}.json"
    )
    if path.exists() and path.read_bytes() != canonical_bytes(rebase):
        raise SelectionRebaseIntegrityError("selection rebase identity collision")
    atomic_write(path, canonical_bytes(rebase))
    return path


def rebase_canonical_story_selection_v1(
    *, store: CanonicalVoiceWorkspaceStoreV2, event_id: int
) -> SelectionReceiptRebaseV1:
    state = store.load_story(event_id)
    if state is None or state.program_selection is None:
        raise SelectionRebaseIntegrityError("selected canonical story is required")
    rebase = rebase_owner_selection_receipts_v1(
        event_id=event_id,
        semantic_draft_revision_identity=state.binding.semantic_draft_revision_identity,
        bundle=state.fact_atom_bundle,
        claims=state.mechanic_claims,
        prior_eligibility=state.program_eligibility,
        prior_program_receipt=state.program_selection,
        prior_expression_eligibility=state.expression_eligibility,
        prior_expression_receipt=state.expression_selection,
        ledger=store.acceptance_store.current_ledger(),
        order_authority=state.order_authority,
    )
    persist_selection_rebase_v1(store.root, rebase)
    fresh_snapshot = derive_repetition_snapshot_v1(
        ledger=store.acceptance_store.current_ledger(),
        order_authority=state.order_authority,
        event_id=event_id,
    ).snapshot
    updated = state.model_copy(
        update={
            "lifecycle": CanonicalVoiceLifecycleV2.EXPRESSION_SELECTED_OR_NONE,
            "repetition_snapshot": fresh_snapshot,
            "program_eligibility": rebase.program_eligibility,
            "program_selection": rebase.rebased_program_receipt,
            "expression_eligibility": rebase.expression_eligibility,
            "expression_selection": rebase.rebased_expression_receipt,
            "execution_request": None,
            "preview": None,
            "prior_state_identity": state.state_identity,
            "state_identity": ZERO,
        }
    )
    store.save_story(updated)
    return rebase


__all__ = [
    "ExplicitNoneReceiptRebaseV1",
    "SelectionRebaseIntegrityError",
    "SelectionReceiptRebaseV1",
    "persist_selection_rebase_v1",
    "rebase_canonical_story_selection_v1",
    "rebase_explicit_none_receipt_v1",
    "rebase_owner_selection_receipts_v1",
]
