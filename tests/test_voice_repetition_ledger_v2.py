from __future__ import annotations

import sys

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_bytes
from pastila_scout.voice_repetition_v2 import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
    VoiceRepetitionLedgerV1,
    derive_repetition_snapshot_v1,
    finalize_ledger_v1,
    finalize_order_authority_v1,
)
from pastila_scout.voice_repetition_v2.persistence import atomic_write, load_ledger


def test_empty_ledger_snapshot_and_persistence_are_canonical(tmp_path) -> None:
    assert "pastila_scout.voice_repetition_v2.acceptance" not in sys.modules
    assert "pastila_scout.voice_repetition_v2.lifecycle" not in sys.modules

    ledger = finalize_ledger_v1(VoiceRepetitionLedgerV1())
    order = finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id="episode-synthetic",
            episode_ordinal=1,
            ordered_event_ids=(101,),
            publication_state=PublicationStateV1.UNPUBLISHED,
        )
    )
    envelope = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=101
    )

    assert envelope.snapshot.uses == ()
    assert envelope.snapshot.current_story_position == 1
    assert envelope.exact_surface_identities == ()

    path = tmp_path / "ledger.json"
    atomic_write(path, canonical_bytes(ledger))
    assert load_ledger(path) == ledger
