from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pastila_scout.voice_adjudication_v2 import (
    AuthorityTextV1,
    CandidateOwnerDispositionV1,
    FactAtomOwnerDecisionRebindProvenanceV1,
    OwnerDecisionRebindAuthorizationV1,
    PriorCandidateProvenanceClassV1,
    VoiceAdjudicationApplicationServiceV1,
    VoiceAdjudicationError,
    VoiceAdjudicationStoreV1,
    VoiceStoryAdjudicationStateV3,
)
from pastila_scout.voice_fact_atoms_v2 import TypedAuthorityFieldInputV2
from pastila_scout.voice_fact_atoms_v2.models import AuthorityClass, CandidateKind
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from tests.test_voice_production_materialization_v2 import _context

NOW = datetime(2026, 8, 24, tzinfo=UTC)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _started(tmp_path):
    binding, _, _, _, snapshot, _, _ = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    title = "18 ani"
    summary = "18 ani și George Smyth"
    rendered = "model-visible authority"
    authority = AuthorityTextV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=binding.event_authority_identity,
        source_identity="event-authority:1",
        text=rendered,
        text_sha256=_sha(rendered),
    )
    fields = tuple(
        TypedAuthorityFieldInputV2(
            authority_class=AuthorityClass.EVENT,
            authority_identity=binding.event_authority_identity,
            article_id=7,
            source_id="source",
            field_name=name,
            text=text,
            text_sha256=_sha(text),
        )
        for name, text in (("title", title), ("summary", summary))
    )
    store = VoiceAdjudicationStoreV1(tmp_path / "voice-root")
    service = VoiceAdjudicationApplicationServiceV1(store)
    state = service.begin_v2(
        binding=binding,
        story_position=1,
        authority_texts=(authority,),
        extraction_fields=fields,
        repetition_snapshot=snapshot,
    )
    return service, store, state


def _rebind(service, state, *, prior="candidate:old", target=None, rationale="Exact."):
    candidate = target or state.candidates[0]
    field_name = candidate.evidence.source_identity.rsplit(":", 1)[1]
    return service.rebind_fact_atom_owner_decision(
        state,
        prior_candidate_identity=prior,
        prior_candidate_provenance_class=(
            PriorCandidateProvenanceClassV1.NONCANONICAL_AD_HOC
        ),
        target_candidate_identity=candidate.candidate_id,
        expected_source_identity=candidate.evidence.source_identity,
        expected_field_name=field_name,
        expected_passage=candidate.evidence.passage,
        expected_start=candidate.evidence.start,
        expected_end=candidate.evidence.end,
        expected_candidate_kind=candidate.kind,
        disposition=CandidateOwnerDispositionV1.REJECT,
        decision_rationale=rationale,
        owner_authorization=(
            OwnerDecisionRebindAuthorizationV1.OWNER_AUTHORIZED_DECISION_REBIND
        ),
        adjudicator_identity="owner",
        adjudicated_at=NOW,
    )


def test_rebind_is_atomic_canonical_and_restart_safe(tmp_path):
    service, store, state = _started(tmp_path)
    rebound = _rebind(service, state, rationale="Byte-exact rationale.")
    assert isinstance(rebound, VoiceStoryAdjudicationStateV3)
    assert len(rebound.fact_atom_receipts) == 1
    assert len(rebound.fact_atom_rebind_provenance) == 1
    provenance = rebound.fact_atom_rebind_provenance[0]
    receipt = rebound.fact_atom_receipts[0]
    assert provenance.target_receipt_identity == receipt.receipt_identity
    assert (
        provenance.decision_rationale
        == receipt.decision_rationale
        == ("Byte-exact rationale.")
    )
    assert canonical_bytes(store.load(1)) == canonical_bytes(rebound)

    before = store.load(1)
    with pytest.raises(VoiceAdjudicationError, match="occurrence mismatch"):
        service.rebind_fact_atom_owner_decision(
            before,
            prior_candidate_identity="candidate:another-old",
            prior_candidate_provenance_class=(
                PriorCandidateProvenanceClassV1.NONCANONICAL_AD_HOC
            ),
            target_candidate_identity=before.candidates[1].candidate_id,
            expected_source_identity=before.candidates[1].evidence.source_identity,
            expected_field_name="summary",
            expected_passage="changed",
            expected_start=before.candidates[1].evidence.start,
            expected_end=before.candidates[1].evidence.end,
            expected_candidate_kind=CandidateKind.COMPLETE_QUANTITY,
            disposition=CandidateOwnerDispositionV1.REJECT,
            decision_rationale="Exact.",
            owner_authorization=(
                OwnerDecisionRebindAuthorizationV1.OWNER_AUTHORIZED_DECISION_REBIND
            ),
            adjudicator_identity="owner",
            adjudicated_at=NOW,
        )
    assert store.load(1) == before


def test_rebind_cardinality_and_integrity_fail_closed(tmp_path):
    service, _, state = _started(tmp_path)
    first = _rebind(service, state)
    with pytest.raises(VoiceAdjudicationError, match="one-to-one"):
        _rebind(service, first, target=first.candidates[1])
    with pytest.raises(VoiceAdjudicationError, match="one-to-one"):
        _rebind(
            service,
            first,
            prior="candidate:different-old",
            target=first.candidates[0],
        )

    provenance = first.fact_atom_rebind_provenance[0]
    with pytest.raises(ValidationError, match="identity mismatch"):
        VoiceStoryAdjudicationStateV3.model_validate(
            first.model_dump(mode="python")
            | {
                "fact_atom_rebind_provenance": (
                    provenance.model_copy(update={"decision_rationale": "Changed."}),
                )
            }
        )


def test_rebind_contract_unknown_version_and_required_fields_fail_closed(tmp_path):
    service, _, state = _started(tmp_path)
    provenance = _rebind(service, state).fact_atom_rebind_provenance[0]
    payload = provenance.model_dump(mode="python")
    with pytest.raises(ValidationError):
        FactAtomOwnerDecisionRebindProvenanceV1.model_validate(
            payload | {"schema_version": "999"}
        )
    payload.pop("owner_authorization")
    with pytest.raises(ValidationError):
        FactAtomOwnerDecisionRebindProvenanceV1.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("story_identity", "sha256:" + "9" * 64, "occurrence"),
        ("source_identity", "article:99:source:field:title", "missing"),
        ("field_name", "summary", "occurrence"),
        ("passage", "changed", "occurrence"),
        ("start", 1, "occurrence"),
        ("end", 5, "occurrence"),
        ("candidate_kind", CandidateKind.NAMED_ENTITY, "occurrence"),
        (
            "disposition",
            CandidateOwnerDispositionV1.REQUIRES_QUALIFICATION,
            "disagree",
        ),
        ("decision_rationale", "Changed.", "disagree"),
        ("target_receipt_identity", "sha256:" + "8" * 64, "missing"),
    ],
)
def test_rebind_link_mutations_fail_after_resealing(tmp_path, field, value, error):
    service, _, state = _started(tmp_path)
    rebound = _rebind(service, state)
    provenance = rebound.fact_atom_rebind_provenance[0].model_copy(
        update={field: value, "provenance_identity": "sha256:" + "0" * 64}
    )
    provenance = provenance.model_copy(
        update={"provenance_identity": canonical_identity(provenance)}
    )
    with pytest.raises(ValidationError, match=error):
        VoiceStoryAdjudicationStateV3.model_validate(
            rebound.model_dump(mode="python")
            | {"fact_atom_rebind_provenance": (provenance,)}
        )
