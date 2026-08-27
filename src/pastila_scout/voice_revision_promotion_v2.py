"""Promote canonical accepted Voice revisions into exact Chief Editor handoff."""

from __future__ import annotations

from pathlib import Path

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.chief_editor_v2_handoff import (
    resolve_chief_editor_v2_story_reference,
)
from pastila_scout.editor_application_v1 import (
    EditorOperationalResultSerializerV1,
    load_editor_operational_result_v1,
)
from pastila_scout.editor_operational_execution_v1 import replace_completed_draft_v1
from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoicePersistenceError,
    CanonicalVoiceStoryStateV2,
)
from pastila_scout.voice_repetition_v2.persistence import atomic_write
from pastila_scout.voice_workflow_v2 import semantic_draft_revision_identity


class AcceptedVoiceRevisionPromoterV2:
    """Materialize and select one already-authoritative authored revision."""

    def __init__(self, *, project_store: ActiveProjectStoreV1, root: Path):
        self.project_store = project_store
        self.root = root

    def promote(
        self,
        state: CanonicalVoiceStoryStateV2,
        *,
        expected_source_revision_identity: str,
    ) -> None:
        if state.lifecycle not in {
            CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY,
            CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY,
        }:
            raise CanonicalVoicePersistenceError(
                "nonterminal Voice revision cannot be promoted"
            )
        # Promotion is part of the live desktop process, not startup recovery.
        # Do not reset an Editor item's RUNNING state while observing the project.
        runtime_loader = getattr(
            self.project_store, "load_runtime_state", self.project_store.load
        )
        project = runtime_loader()
        if project is None:
            raise CanonicalVoicePersistenceError("active project is unavailable")
        event_id = state.binding.event_id
        material_reference = f"editor-material-v1:event:{event_id}"
        material = next(
            (item for item in project.editor_materials if item.reference == material_reference),
            None,
        )
        item = next(
            (
                item
                for item in project.chief_editor_items
                if item.material_reference == material_reference
            ),
            None,
        )
        if (
            material is None
            or item is None
            or item.v2_story_reference is None
            or material.output_path is None
            or material.payload_sha256 is None
        ):
            raise CanonicalVoicePersistenceError("current Editor revision is unavailable")
        current_reference = item.v2_story_reference
        resolved = resolve_chief_editor_v2_story_reference(current_reference)
        target_revision = semantic_draft_revision_identity(state.authored_draft)
        target_story = next(
            item for item in state.authored_draft.stories if item.event_id == event_id
        )
        target_commentary = (
            None if target_story.acid_commentary is None else target_story.acid_commentary.text
        )
        if current_reference.semantic_draft_revision_identity == target_revision:
            if resolved.acid_commentary_text != target_commentary:
                raise CanonicalVoicePersistenceError("promoted revision content mismatch")
            return
        if (
            current_reference.semantic_draft_revision_identity
            != expected_source_revision_identity
        ):
            raise CanonicalVoicePersistenceError("current Editor revision is stale")
        result = load_editor_operational_result_v1(
            path=Path(material.output_path), payload_sha256=material.payload_sha256
        )
        derived = replace_completed_draft_v1(result, state.authored_draft)
        serialized = EditorOperationalResultSerializerV1().serialize(result=derived)
        revision = target_revision.removeprefix("sha256:")
        path = (
            self.root
            / "promoted-editor-materials"
            / str(event_id)
            / f"{revision}.json"
        )
        if path.exists() and path.read_bytes() != serialized.payload:
            raise CanonicalVoicePersistenceError("promoted revision identity collision")
        atomic_write(path, serialized.payload)
        try:
            self.project_store.promote_editor_v2_revision(
                event_id=event_id,
                expected_reference=current_reference,
                output_path=path,
                payload_sha256=serialized.payload_sha256,
            )
        except ValueError as exc:
            raise CanonicalVoicePersistenceError(
                "Chief Editor revision promotion failed"
            ) from exc


__all__ = ["AcceptedVoiceRevisionPromoterV2"]
