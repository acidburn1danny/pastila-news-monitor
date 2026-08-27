from __future__ import annotations

from datetime import timedelta

from test_editor_voice_application_v2 import NOW, _draft, _request, _sha

from pastila_scout.desktop_v1.editor_material_presentation_v2 import (
    project_editor_material_presentation_v2,
    render_editor_material_presentation_v2,
)
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryV2,
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.editor_voice_application_v2 import (
    EditorVoiceApplicationOutcomeV1,
    EditorVoiceApplicationResultV1,
    EditorVoiceApplicationServiceV1,
    UnavailableVoiceExecutorV1,
)
from pastila_scout.voice_workflow_v2 import (
    AcceptedCommentaryBindingV1,
    PersistedVoiceAttemptOutcomeV1,
    PublicCommentaryStateV1,
    VoiceAttemptRecordV1,
    VoiceValidationResultV1,
    VoiceWorkflowSidecarStoreV1,
    VoiceWorkflowSidecarV1,
    sha256_identity,
)


def _component(draft, result):
    projection = project_editor_material_presentation_v2(
        event_id=77, draft=draft, voice_results={77: result}
    )
    assert projection.components[0].label == "Rezumat factual"
    assert projection.components[0].text == draft.stories[0].factual_summary.text
    return projection.components[1], render_editor_material_presentation_v2(projection)


def test_unavailable_ui_comes_from_application_service_without_execution(tmp_path):
    draft = _draft()
    request = _request(draft).model_copy(update={"runtime_input_identity": None})
    service = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: NOW
    )
    result = service.inspect(
        request, store=VoiceWorkflowSidecarStoreV1(tmp_path / "missing.json")
    )

    component, rendered = _component(draft, result)
    assert component.label == "Comentariu acid: indisponibil"
    assert component.text == "Nu este selectat încă un model Voice valid."
    assert not component.generation_enabled and not component.retry_enabled
    assert "OPENING" not in rendered and "CLOSING" not in rendered


def test_ungenerated_and_failed_controls_follow_application_result():
    draft = _draft()
    binding = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: NOW
    ).prepare_binding(_request(draft))
    ungenerated = EditorVoiceApplicationResultV1(
        outcome=EditorVoiceApplicationOutcomeV1.UNGENERATED,
        commentary_state=PublicCommentaryStateV1.UNGENERATED,
        generation_possible=True,
        binding=binding,
        executor_identity="future-voice-executor:v1",
    )
    component, rendered = _component(draft, ungenerated)
    assert component.label == "Comentariu acid: negenerat"
    assert component.text == ""
    assert component.generation_enabled and not component.retry_enabled
    assert rendered.endswith("Comentariu acid: negenerat")

    failed = EditorVoiceApplicationResultV1(
        outcome=EditorVoiceApplicationOutcomeV1.FAILED,
        commentary_state=PublicCommentaryStateV1.FAILED,
        generation_possible=True,
        binding=binding,
        executor_identity="future-voice-executor:v1",
        safe_failure_code="factual_boundary_failed",
    )
    component, _ = _component(draft, failed)
    assert component.label == "Comentariu acid: eșuat"
    assert "factual_boundary_failed" in component.text
    assert component.retry_enabled and not component.generation_enabled


def test_invalid_binding_hides_stale_commentary():
    commentary = AcidCommentaryV2(
        text="Text care nu trebuie afișat fără legătura validă.",
        voice_model_identity="voice-package:v2",
        factual_boundary_receipt="voice-boundary:pass",
    )
    draft = _draft(commentary)
    invalid = EditorVoiceApplicationResultV1(
        outcome=EditorVoiceApplicationOutcomeV1.INVALID_BINDING,
        commentary_state=None,
        generation_possible=False,
        safe_failure_code="voice_story_binding_invalid",
    )

    component, rendered = _component(draft, invalid)
    assert component.label == "Comentariu acid: eroare de integritate"
    assert commentary.text not in rendered
    assert "nu este validă" in component.text


def test_generated_commentary_reloads_from_exact_persisted_sidecar(tmp_path):
    commentary = AcidCommentaryV2(
        text="Raportul e gata. Misterul și-a încheiat programul.",
        voice_model_identity="voice-package:accepted",
        factual_boundary_receipt="voice-boundary:pass",
    )
    persisted_draft_path = tmp_path / "semantic-draft-v2.json"
    persisted_draft_path.write_text(
        _draft(commentary).model_dump_json(), encoding="utf-8"
    )
    draft = PastilaEditorSemanticDraftV2.model_validate_json(
        persisted_draft_path.read_text(encoding="utf-8")
    )
    request = _request(draft)
    service = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: NOW
    )
    binding = service.prepare_binding(request)
    attempt = VoiceAttemptRecordV1(
        attempt_identity=_sha("persisted-generated-attempt"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.GENERATED,
        runtime_input_identity=request.runtime_input_identity,
        voice_model_package_identity="voice-package:accepted",
        validation_result=VoiceValidationResultV1.PASSED,
        output_sha256=sha256_identity(commentary.text),
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
    )
    accepted = AcceptedCommentaryBindingV1(
        attempt_identity=attempt.attempt_identity,
        attempt_ordinal=1,
        acid_commentary_identity=_sha("persisted-commentary"),
        output_sha256=sha256_identity(commentary.text),
        voice_model_package_identity="voice-package:accepted",
        factual_boundary_validation_receipt="voice-boundary:pass",
        accepted_at=NOW + timedelta(seconds=1),
    )
    sidecar = VoiceWorkflowSidecarV1(
        binding=binding,
        commentary_state=PublicCommentaryStateV1.GENERATED,
        attempts=(attempt,),
        accepted_commentary=accepted,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
    )
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")
    store.save(sidecar, draft=draft)

    first = service.inspect(request, store=store)
    reloaded_draft = PastilaEditorSemanticDraftV2.model_validate_json(
        persisted_draft_path.read_text(encoding="utf-8")
    )
    second = service.inspect(_request(reloaded_draft), store=store)
    assert first == second
    component, rendered = _component(reloaded_draft, second)
    assert component.label == "Comentariu acid: generat"
    assert component.text == commentary.text
    assert commentary.text in rendered
