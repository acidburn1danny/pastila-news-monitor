from __future__ import annotations

import sys

from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceWorkspaceStateV2,
    CanonicalVoiceWorkspaceStoreV2,
)
from pastila_scout.voice_repetition_v2 import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
    finalize_order_authority_v1,
)


def test_empty_workspace_round_trip_does_not_load_acceptance_authority(
    tmp_path,
) -> None:
    acceptance_was_loaded = (
        "pastila_scout.voice_repetition_v2.acceptance" in sys.modules
    )
    project = tmp_path / "episode.pastila"
    project.write_text("{}", encoding="utf-8")
    store = CanonicalVoiceWorkspaceStoreV2(
        project_path=project, project_identity="project:synthetic"
    )
    order = finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id="episode-synthetic",
            episode_ordinal=1,
            ordered_event_ids=(101,),
            publication_state=PublicationStateV1.UNPUBLISHED,
        )
    )
    state = CanonicalVoiceWorkspaceStateV2(
        project_identity="project:synthetic", order_authority=order
    )

    saved = store.save_workspace(state)
    assert store.load_workspace() == saved
    assert store.load_story(101) is None
    assert (
        "pastila_scout.voice_repetition_v2.acceptance" in sys.modules
    ) is acceptance_was_loaded
