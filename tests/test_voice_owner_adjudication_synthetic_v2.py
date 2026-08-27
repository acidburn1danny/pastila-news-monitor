from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    AuthorityTextV1,
    CandidateOwnerDispositionV1,
    VoiceAdjudicationApplicationServiceV1,
    VoiceAdjudicationStoreV1,
)
from pastila_scout.voice_eligibility_v2.engine import finalize_repetition_snapshot
from pastila_scout.voice_eligibility_v2.models import VoiceRepetitionSnapshotV1
from pastila_scout.voice_fact_atoms_v2.models import AuthorityClass
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1


ZERO = "sha256:" + "0" * 64
NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)


def test_owner_rejection_is_canonical_persistent_and_zero_model(tmp_path) -> None:
    authority_identity = "event-authority:synthetic"
    text = "Proiectul costă aproximativ 37.000 de euro. Cauza nu este cunoscută."
    binding = VoiceStoryBindingV1(
        story_material_reference="story:synthetic",
        semantic_draft_revision_identity="sha256:" + "1" * 64,
        event_id=101,
        factual_summary_sha256="sha256:" + hashlib.sha256(text.encode()).hexdigest(),
        event_authority_identity=authority_identity,
    )
    authority = AuthorityTextV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=authority_identity,
        source_identity="synthetic:event:101",
        text=text,
        text_sha256="sha256:" + hashlib.sha256(text.encode()).hexdigest(),
    )
    snapshot = finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=1,
            current_story_position=1,
            uses=(),
            snapshot_identity=ZERO,
        )
    )
    store = VoiceAdjudicationStoreV1(tmp_path / "voice")
    service = VoiceAdjudicationApplicationServiceV1(store)
    state = service.begin(
        binding=binding,
        story_position=1,
        authority_texts=(authority,),
        repetition_snapshot=snapshot,
    )
    assert state.lifecycle is AdjudicationLifecycleV1.CANDIDATES_EXTRACTED
    assert state.candidates

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

    assert store.load(101) == rejected
    assert rejected.fact_atom_receipts[-1].decision_rationale
    assert service.model_calls == service.provider_calls == service.model_loads == 0
