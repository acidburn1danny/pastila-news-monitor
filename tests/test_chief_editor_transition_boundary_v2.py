from datetime import UTC, datetime

from pastila_scout.chief_editor_transition_v2 import (
    ChiefEditorTransitionWorkflowSidecarV1,
    ChiefEditorTransitionWorkflowStoreV1,
)


def test_empty_transition_sidecar_round_trips_deterministically(tmp_path):
    now = datetime(2026, 8, 27, tzinfo=UTC)
    sidecar = ChiefEditorTransitionWorkflowSidecarV1(
        ordered_chief_story_identities=("historical-v1:editor-material-v1:event:1",),
        created_at=now,
        updated_at=now,
    )
    store = ChiefEditorTransitionWorkflowStoreV1(tmp_path / "transitions.json")

    first_identity = store.save(sidecar)
    reloaded = store.load()

    assert reloaded == sidecar
    assert store.save(reloaded) == first_identity
