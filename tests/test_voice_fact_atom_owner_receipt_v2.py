from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pastila_scout.voice_adjudication_v2 import (
    CandidateOwnerDispositionV1,
    FactAtomOwnerReceiptV1,
    FactAtomOwnerReceiptV2,
    VoiceAdjudicationError,
)
from pastila_scout.voice_adjudication_v2.models import (
    ZERO,
    VoiceStoryAdjudicationStateV1,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity
from tests.test_voice_owner_adjudication_v2 import _started

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _seal(receipt):
    return receipt.model_copy(update={"receipt_identity": canonical_identity(receipt)})


def _v1():
    return _seal(
        FactAtomOwnerReceiptV1(
            semantic_draft_revision_identity=SHA_A,
            event_authority_identity="event-authority:1",
            candidate_identity="candidate:1",
            exact_source_span_sha256=SHA_B,
            disposition=CandidateOwnerDispositionV1.REJECT,
            adjudicator_identity="owner",
            adjudicated_at=NOW,
        )
    )


def _v2(rationale="Not promoted as an independent governed atom."):
    return _seal(
        FactAtomOwnerReceiptV2(
            semantic_draft_revision_identity=SHA_A,
            event_authority_identity="event-authority:1",
            candidate_identity="candidate:1",
            exact_source_span_sha256=SHA_B,
            disposition=CandidateOwnerDispositionV1.REJECT,
            adjudicator_identity="owner",
            adjudicated_at=NOW,
            decision_rationale=rationale,
        )
    )


def test_v1_round_trip_and_identity_are_unchanged():
    receipt = _v1()
    raw = receipt.model_dump_json()
    loaded = FactAtomOwnerReceiptV1.model_validate_json(raw)
    assert loaded == receipt
    assert loaded.schema_version == "1"
    assert "decision_rationale" not in loaded.model_dump()
    assert loaded.receipt_identity == receipt.receipt_identity


def test_v2_round_trip_rationale_identity_and_empty_rejection():
    receipt = _v2()
    loaded = FactAtomOwnerReceiptV2.model_validate_json(receipt.model_dump_json())
    assert loaded == receipt
    mutated = _v2("A different owner rationale.")
    assert mutated.receipt_identity != receipt.receipt_identity
    with pytest.raises(ValidationError, match="non-empty rationale"):
        _v2("   ")


def test_state_union_loads_v1_and_v2_and_rejects_unknown_version(tmp_path):
    _service, _store, state, _text = _started(tmp_path)
    for receipt in (_v1(), _v2()):
        loaded = VoiceStoryAdjudicationStateV1.model_validate(
            state.model_copy(update={"fact_atom_receipts": (receipt,)}).model_dump()
        )
        assert loaded.fact_atom_receipts[0] == receipt
    payload = state.model_dump(mode="json")
    payload["fact_atom_receipts"] = [
        {**_v2().model_dump(mode="json"), "schema_version": "999"}
    ]
    with pytest.raises(ValidationError):
        VoiceStoryAdjudicationStateV1.model_validate(payload)


def test_duplicate_active_terminal_receipts_fail_closed(tmp_path):
    service, _store, state, _text = _started(tmp_path)
    candidate = state.candidates[0]
    first = _seal(
        _v2().model_copy(
            update={
                "candidate_identity": candidate.candidate_id,
                "receipt_identity": ZERO,
            }
        )
    )
    second = _seal(
        first.model_copy(
            update={
                "decision_rationale": "Second active decision.",
                "receipt_identity": ZERO,
            }
        )
    )
    duplicate = state.model_copy(update={"fact_atom_receipts": (first, second)})
    with pytest.raises(VoiceAdjudicationError, match="duplicate active"):
        service.finalize_fact_atoms(duplicate)
