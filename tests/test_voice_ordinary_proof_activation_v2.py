from datetime import UTC, datetime

import pytest

from pastila_scout.voice_eligibility_v2.models import (
    SelectionKindV1,
    VoiceOwnerSelectionReceiptV1,
)
from pastila_scout.voice_executor_v2 import (
    OrdinaryStoryProofActivationEntryV1,
    OrdinaryStoryProofAuthorityAmendmentV1,
    VoiceOrdinaryStoryProofOnlyAuthorityV1,
    finalize_ordinary_story_proof_amendment_v1,
    finalize_ordinary_story_proof_authority_v1,
    reject_as_production_authority,
    verify_ordinary_story_proof_authority_v1,
)

IDENTITY = "sha256:" + "1" * 64
HEX = "2" * 64


def _authority():
    return finalize_ordinary_story_proof_authority_v1(
        VoiceOrdinaryStoryProofOnlyAuthorityV1(
            corpus_ledger_sha256=HEX,
            corpus_manifest_sha256=HEX,
            renderer_identity="pastilaacida-voice:deterministic-renderer:v2",
            entries=(
                OrdinaryStoryProofActivationEntryV1(
                    event_id=1,
                    semantic_draft_revision_identity=IDENTITY,
                    story_state_identity=IDENTITY,
                    adjudication_state_identity=IDENTITY,
                    fact_atom_bundle_identity=IDENTITY,
                ),
            ),
        )
    )


def test_ordinary_story_proof_authority_is_deterministic_and_nonproduction():
    authority = _authority()
    assert verify_ordinary_story_proof_authority_v1(authority) == authority
    assert authority.proof_only is True
    assert authority.production_eligible is False
    with pytest.raises(TypeError, match="not production authority"):
        reject_as_production_authority(authority)


def test_ordinary_story_proof_authority_fails_closed_on_tampering():
    authority = _authority().model_copy(update={"corpus_ledger_sha256": "3" * 64})
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_ordinary_story_proof_authority_v1(authority)


def test_partial_program_tuple_is_rejected():
    with pytest.raises(ValueError, match="program tuple"):
        OrdinaryStoryProofActivationEntryV1(
            event_id=1,
            semantic_draft_revision_identity=IDENTITY,
            story_state_identity=IDENTITY,
            adjudication_state_identity=IDENTITY,
            fact_atom_bundle_identity=IDENTITY,
            program_id="NEL_EXAMPLE",
        )


def test_explicit_none_amendment_is_proof_only():
    receipt = VoiceOwnerSelectionReceiptV1(
        fact_atom_bundle_identity=IDENTITY,
        eligibility_result_identity=IDENTITY,
        repetition_snapshot_identity=IDENTITY,
        shortlist_candidate_ids=(),
        selection_kind=SelectionKindV1.NONE,
        selector_identity="owner",
        selected_at=datetime(2026, 8, 23, tzinfo=UTC),
        receipt_identity=IDENTITY,
    )
    amendment = finalize_ordinary_story_proof_amendment_v1(
        OrdinaryStoryProofAuthorityAmendmentV1(
            parent_authority_identity=IDENTITY,
            event_id=1,
            semantic_draft_revision_identity=IDENTITY,
            ledger_identity=IDENTITY,
            fresh_snapshot_identity=IDENTITY,
            superseded_program_receipt_identity=IDENTITY,
            replacement_program_receipt=receipt,
        )
    )
    assert amendment.production_eligible is False
    with pytest.raises(TypeError, match="not production authority"):
        reject_as_production_authority(amendment)
