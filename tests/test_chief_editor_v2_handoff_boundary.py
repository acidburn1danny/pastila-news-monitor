from pastila_scout.chief_editor_v2_handoff import (
    ChiefEditorV2StoryReferenceV1,
    ResolvedChiefEditorV2StoryV1,
    render_resolved_chief_editor_v2_story,
)
from pastila_scout.voice_workflow_v2 import PublicCommentaryStateV1


def _reference(state: PublicCommentaryStateV1):
    digest = "sha256:" + "0" * 64
    return ChiefEditorV2StoryReferenceV1(
        material_reference="editor-material-v1:event:1",
        material_output_path="material.json",
        material_payload_sha256="payload",
        semantic_draft_revision_identity=digest,
        event_id=1,
        story_position=1,
        story_revision_identity=digest,
        factual_summary_identity=digest,
        commentary_state=state,
        event_authority_identity="authority-v1",
    )


def test_handoff_renders_exact_authored_content():
    resolved = ResolvedChiefEditorV2StoryV1(
        reference=_reference(PublicCommentaryStateV1.GENERATED),
        factual_summary_text="Exact summary.",
        acid_commentary_text="Exact commentary.",
    )

    assert render_resolved_chief_editor_v2_story(resolved) == (
        "Rezumat factual\nExact summary.\nComentariu acid\nExact commentary."
    )


def test_handoff_preserves_truthful_absent_commentary_state():
    resolved = ResolvedChiefEditorV2StoryV1(
        reference=_reference(PublicCommentaryStateV1.UNGENERATED),
        factual_summary_text="Exact summary.",
        acid_commentary_text=None,
    )

    assert render_resolved_chief_editor_v2_story(resolved).endswith("Negenerat")
