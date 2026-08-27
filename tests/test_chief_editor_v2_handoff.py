from __future__ import annotations

from datetime import UTC, datetime

import pytest
from test_active_project_v1 import _additional_event, _database
from test_editor_operational_execution_v1 import execute_fake, observation
from test_editor_operational_semantic_v2_persistence import _semantic_output

from pastila_scout.active_project_v1 import ActiveProjectStoreV1, ChiefEditorItemV1
from pastila_scout.chief_editor_v2_handoff import (
    create_chief_editor_v2_story_reference,
    render_resolved_chief_editor_v2_story,
    resolve_chief_editor_v2_story_reference,
    voice_sidecar_path_for_material,
)
from pastila_scout.desktop_v1.entrypoint import _publish_chief_editor
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryExecutionProvenanceV2,
    AcidCommentaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
)
from pastila_scout.editor_application_v1 import EditorOperationalResultSerializerV1
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.voice_workflow_v2 import (
    AcceptedCommentaryBindingV1,
    PersistedVoiceAttemptOutcomeV1,
    PublicCommentaryStateV1,
    VoiceAttemptRecordV1,
    VoiceStoryBindingV1,
    VoiceValidationResultV1,
    VoiceWorkflowSidecarStoreV1,
    VoiceWorkflowSidecarV1,
    semantic_draft_revision_identity,
    sha256_identity,
)

NOW = datetime(2026, 8, 22, 8, 0, tzinfo=UTC)


def _operational(monkeypatch, *, summary_text=None, commentary=None, event_id=2566):
    output = _semantic_output()
    draft = output.draft
    story = draft.stories[0]
    if event_id != story.event_id:
        story = story.model_copy(update={"event_id": event_id})
    if summary_text is not None:
        story = story.model_copy(
            update={
                "factual_summary": story.factual_summary.model_copy(
                    update={"text": summary_text}
                )
            }
        )
    if commentary is not None:
        story = story.model_copy(
            update={
                "acid_commentary": commentary,
                "acid_commentary_status": "present",
            }
        )
    rebuilt = PastilaEditorSemanticDraftV2.assemble(
        episode_id=draft.episode_id,
        mode=(
            SemanticDraftModeV2.CORE_PLUS_VOICE
            if commentary is not None
            else SemanticDraftModeV2.CORE_ONLY
        ),
        stories=(story,),
        provenance_references=draft.provenance_references,
        generation_receipts=draft.generation_receipts,
    )
    output = output.model_copy(update={"draft": rebuilt})
    result, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=output,
    )
    return result


def _persist(monkeypatch, path, *, summary_text=None, commentary=None, event_id=2566):
    result = _operational(
        monkeypatch,
        summary_text=summary_text,
        commentary=commentary,
        event_id=event_id,
    )
    serialized = EditorOperationalResultSerializerV1().serialize(result=result)
    path.write_bytes(serialized.payload)
    return result.draft, serialized.payload_sha256


def test_exact_v2_revision_handoff_persists_and_resolves_after_restart(
    monkeypatch, tmp_path
):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    _additional_event(database, 2566, "Material V2")
    material_path = tmp_path / "editor-v2.json"
    draft, payload_sha256 = _persist(monkeypatch, material_path)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    store.handoff(event_id=2566)
    store.mark_editor_item_running(event_id=2566)
    project = store.record_editor_output_for_event(
        event_id=2566,
        output_path=material_path,
        payload_sha256=payload_sha256,
    )

    reference = project.chief_editor_items[0].v2_story_reference
    assert reference is not None
    assert reference.semantic_draft_revision_identity == (
        semantic_draft_revision_identity(draft)
    )
    assert reference.story_position == 1
    assert reference.commentary_state is PublicCommentaryStateV1.UNAVAILABLE
    saved = store.save_chief_editor(
        title="Episod V2",
        items=(
            ChiefEditorItemV1(
                project.chief_editor_items[0].material_reference,
                "Actualitate",
                "Intenție editorială, nu tranziție acceptată.",
            ),
        ),
    )
    assert saved.chief_editor_items[0].v2_story_reference == reference
    assert saved.chief_editor_items[0].note == (
        "Intenție editorială, nu tranziție acceptată."
    )
    restarted = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    ).load()
    assert restarted is not None
    assert restarted.chief_editor_items[0].v2_story_reference == reference
    resolved = resolve_chief_editor_v2_story_reference(reference)
    assert resolved.factual_summary_text == draft.stories[0].factual_summary.text
    assert "Comentariu acid\nIndisponibil" in (
        render_resolved_chief_editor_v2_story(resolved)
    )
    published = {}

    class View:
        def publish_chief_editor(self, **kwargs):
            published.update(kwargs)

    _publish_chief_editor(View(), restarted)
    assert published["v2_presentations"] == (
        (
            reference.material_reference,
            render_resolved_chief_editor_v2_story(resolved),
        ),
    )


def test_newer_material_does_not_rebind_existing_chief_editor_item(
    monkeypatch, tmp_path
):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    _additional_event(database, 2566, "Material V2")
    first_path = tmp_path / "first.json"
    first_draft, first_sha = _persist(monkeypatch, first_path)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    store.handoff(event_id=2566)
    store.mark_editor_item_running(event_id=2566)
    first = store.record_editor_output_for_event(
        event_id=2566, output_path=first_path, payload_sha256=first_sha
    )
    frozen_reference = first.chief_editor_items[0].v2_story_reference

    second_path = tmp_path / "second.json"
    _, second_sha = _persist(
        monkeypatch,
        second_path,
        summary_text="Autoritatea locală a confirmat o măsură nouă.",
    )
    second = store.record_editor_output(
        output_path=second_path, payload_sha256=second_sha
    )
    assert second.editor_materials[0].output_path == str(second_path)
    assert second.chief_editor_items[0].v2_story_reference == frozen_reference
    assert (
        resolve_chief_editor_v2_story_reference(frozen_reference).factual_summary_text
        == first_draft.stories[0].factual_summary.text
    )


def test_mismatched_reference_fails_closed(monkeypatch, tmp_path):
    path = tmp_path / "material.json"
    _, payload_sha256 = _persist(monkeypatch, path)
    reference = create_chief_editor_v2_story_reference(
        material_reference="editor-material-v1:event:2566",
        event_id=2566,
        output_path=path,
        payload_sha256=payload_sha256,
    )
    assert reference is not None
    corrupted = reference.model_copy(
        update={"factual_summary_identity": "sha256:" + "0" * 64}
    )
    with pytest.raises(ValueError, match="no longer matches"):
        resolve_chief_editor_v2_story_reference(corrupted)


def test_generated_commentary_survives_handoff_byte_exact(monkeypatch, tmp_path):
    commentary = AcidCommentaryV2(
        text="Text acid exact, fără rescriere.",
        voice_model_identity="voice-package:v2",
        factual_boundary_receipt="voice-boundary:pass",
    )
    path = tmp_path / "generated.json"
    draft, payload_sha256 = _persist(monkeypatch, path, commentary=commentary)
    story = draft.stories[0]
    runtime_identity = sha256_identity("runtime")
    binding = VoiceStoryBindingV1(
        story_material_reference="editor-material-v1:event:2566",
        semantic_draft_revision_identity=semantic_draft_revision_identity(draft),
        event_id=2566,
        factual_summary_sha256=sha256_identity(story.factual_summary.text),
        event_authority_identity=story.factual_summary.authority_bundle_identity,
        runtime_input_identity=runtime_identity,
    )
    attempt = VoiceAttemptRecordV1(
        attempt_identity=sha256_identity("attempt"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.GENERATED,
        runtime_input_identity=runtime_identity,
        voice_model_package_identity="voice-package:v2",
        validation_result=VoiceValidationResultV1.PASSED,
        output_sha256=sha256_identity(commentary.text),
        started_at=NOW,
        completed_at=NOW,
    )
    accepted = AcceptedCommentaryBindingV1(
        attempt_identity=attempt.attempt_identity,
        attempt_ordinal=1,
        acid_commentary_identity=sha256_identity("commentary-record"),
        output_sha256=sha256_identity(commentary.text),
        voice_model_package_identity="voice-package:v2",
        factual_boundary_validation_receipt="voice-boundary:pass",
        accepted_at=NOW,
    )
    sidecar = VoiceWorkflowSidecarV1(
        binding=binding,
        commentary_state=PublicCommentaryStateV1.GENERATED,
        attempts=(attempt,),
        accepted_commentary=accepted,
        created_at=NOW,
        updated_at=NOW,
    )
    VoiceWorkflowSidecarStoreV1(voice_sidecar_path_for_material(path)).save(
        sidecar, draft=draft
    )
    reference = create_chief_editor_v2_story_reference(
        material_reference=binding.story_material_reference,
        event_id=2566,
        output_path=path,
        payload_sha256=payload_sha256,
    )
    assert reference is not None
    resolved = resolve_chief_editor_v2_story_reference(reference)
    assert resolved.acid_commentary_text == commentary.text
    assert render_resolved_chief_editor_v2_story(resolved).endswith(commentary.text)


def test_explicit_voice_revision_promotion_rebinds_exactly_and_fails_stale(
    monkeypatch, tmp_path
):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    _additional_event(database, 2566, "Material V2")
    core_path = tmp_path / "core.json"
    _, core_sha = _persist(monkeypatch, core_path)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    store.handoff(event_id=2566)
    store.mark_editor_item_running(event_id=2566)
    project = store.record_editor_output_for_event(
        event_id=2566, output_path=core_path, payload_sha256=core_sha
    )
    original = project.chief_editor_items[0].v2_story_reference
    assert original is not None

    commentary = AcidCommentaryV2(
        text="Comentariu determinist exact.",
        factual_boundary_receipt="sha256:" + "2" * 64,
        execution_provenance=AcidCommentaryExecutionProvenanceV2(
            backend_kind="deterministic_renderer",
            backend_identity="pastilaacida-voice:deterministic-renderer:v2",
            canonical_ir_identity="sha256:" + "3" * 64,
            character_provenance_identity="sha256:" + "4" * 64,
            acceptance_transaction_identity="sha256:" + "5" * 64,
            model_calls=0,
            provider_calls=0,
            model_loads=0,
        ),
    )
    accepted_path = tmp_path / "accepted.json"
    _, accepted_sha = _persist(monkeypatch, accepted_path, commentary=commentary)
    promoted = store.promote_editor_v2_revision(
        event_id=2566,
        expected_reference=original,
        output_path=accepted_path,
        payload_sha256=accepted_sha,
    )
    accepted_reference = promoted.chief_editor_items[0].v2_story_reference
    assert accepted_reference is not None
    assert accepted_reference.acid_commentary_identity == sha256_identity(
        commentary.text
    )
    assert (
        resolve_chief_editor_v2_story_reference(accepted_reference).acid_commentary_text
        == commentary.text
    )
    assert (
        store.promote_editor_v2_revision(
            event_id=2566,
            expected_reference=original,
            output_path=accepted_path,
            payload_sha256=accepted_sha,
        )
        .chief_editor_items[0]
        .v2_story_reference
        == accepted_reference
    )
    with pytest.raises(ValueError, match="învechită"):
        store.promote_editor_v2_revision(
            event_id=2566,
            expected_reference=original,
            output_path=core_path,
            payload_sha256=core_sha,
        )
    restarted = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    ).load()
    assert restarted is not None
    assert restarted.chief_editor_items[0].v2_story_reference == accepted_reference
    removed = store.promote_editor_v2_revision(
        event_id=2566,
        expected_reference=accepted_reference,
        output_path=core_path,
        payload_sha256=core_sha,
    )
    removed_reference = removed.chief_editor_items[0].v2_story_reference
    assert removed_reference is not None
    assert removed_reference.acid_commentary_identity is None
    assert (
        resolve_chief_editor_v2_story_reference(removed_reference).acid_commentary_text
        is None
    )
