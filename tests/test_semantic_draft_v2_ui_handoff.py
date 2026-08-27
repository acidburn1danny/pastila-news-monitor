from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_editor_operational_semantic_v2_persistence import _v2_operational
from test_semantic_draft_v2 import _story

from pastila_scout.active_project_v1 import ChiefEditorItemV1, EditorMaterialV1
from pastila_scout.desktop_v1.editor_material_presentation_v2 import (
    load_editor_material_presentation_v2,
    project_editor_material_presentation_v2,
    render_editor_material_presentation_v2,
)
from pastila_scout.desktop_v1.entrypoint import (
    _publish_chief_editor,
    _publish_editor_worklist,
)
from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.generation.semantic_draft_v2 import (
    CrossStoryTransitionV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
)
from pastila_scout.editor_application_v1 import EditorOperationalResultSerializerV1


def _single_v2() -> PastilaEditorSemanticDraftV2:
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="single",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(_story(10, 1),),
    )


def test_v2_single_story_ui_has_factual_summary_and_unavailable_commentary_only():
    projection = project_editor_material_presentation_v2(
        event_id=10, draft=_single_v2()
    )
    assert projection.schema_label == "Semantic Draft V2"
    assert tuple(item.label for item in projection.components) == (
        "Rezumat factual",
        "Comentariu acid: indisponibil",
    )
    assert projection.components[0].text == "Fapt confirmat pentru 10."
    assert projection.components[1].availability == "unavailable"
    assert projection.components[1].text == (
        "Nu este selectat încă un model Voice valid."
    )
    rendered = render_editor_material_presentation_v2(projection)
    assert "OPENING" not in rendered and "CLOSING" not in rendered
    assert "Introducere episod" not in rendered and "Monolog final" not in rendered


def test_v2_multi_story_ui_preserves_order_and_only_present_transition():
    stories = (_story(10, 1), _story(20, 2), _story(30, 3))
    transition = CrossStoryTransitionV2(
        transition_id="10-20",
        from_event_id=10,
        to_event_id=20,
        text="Trecem de la primul subiect la al doilea.",
        source_story_fingerprints=("sha256:10", "sha256:20"),
        validation_receipt="sha256:transition",
    )
    draft = PastilaEditorSemanticDraftV2.assemble(
        episode_id="multi",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=stories,
        transitions=(transition,),
    )
    projection = project_editor_material_presentation_v2(event_id=10, draft=draft)
    labels = tuple(item.label for item in projection.components)
    assert labels == (
        "Rezumat factual",
        "Comentariu acid: indisponibil",
        "Tranziție între știri",
        "Rezumat factual",
        "Comentariu acid: indisponibil",
        "Rezumat factual",
        "Comentariu acid: indisponibil",
    )
    assert projection.components[2].text == transition.text
    assert labels.count("Tranziție între știri") == 1


def test_persisted_v2_restart_reconstructs_identical_native_ui(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    result = _v2_operational(monkeypatch)
    serialized = EditorOperationalResultSerializerV1().serialize(result=result)
    path = tmp_path / "material-v2.json"
    path.write_bytes(serialized.payload)
    material = EditorMaterialV1(
        reference="editor-material-v1:event:2566",
        event_id=2566,
        title="Titlu",
        summary="Rezumat",
        output_path=str(path),
        payload_sha256=serialized.payload_sha256,
    )
    first = load_editor_material_presentation_v2(material=material)
    second = load_editor_material_presentation_v2(material=replace(material))
    assert first == second
    assert first.schema_label == "Semantic Draft V2"
    assert ChiefEditorItemV1(material.reference).material_reference == material.reference
    assert type(result.draft) is PastilaEditorSemanticDraftV2

    class View:
        def publish_editor_worklist(self, *, items):
            self.worklist = items

        def publish_editor_material_presentations(self, *, items):
            self.presentations = items

        def publish_chief_editor(self, **values):
            self.chief = values

    view = View()
    project = SimpleNamespace(
        latest_handoff_event_ids=(2566,),
        editor_worklist=(
            SimpleNamespace(
                event_id=2566, status=SimpleNamespace(value="completed")
            ),
        ),
        scout_input=SimpleNamespace(
            ranked_events=(
                SimpleNamespace(event_id=2566, canonical_title="Titlu"),
            )
        ),
        editor_materials=(material,),
        chief_editor_items=(ChiefEditorItemV1(material.reference),),
        chief_editor_title="Episod",
        title="Episod",
    )
    _publish_editor_worklist(view, project)
    _publish_chief_editor(view, project)
    assert view.presentations == (first,)
    assert view.chief["available"] == ((material.reference, material.title),)
    assert view.chief["items"][0][0] == material.reference


def test_historical_v1_ui_text_is_unchanged_and_not_projected_to_v2():
    draft = EpisodeDraft(
        episode_id="legacy",
        opening="OPENING istoric",
        stories=(),
        transitions=(),
        closing="CLOSING istoric",
        cta=None,
        assembled_text="OPENING istoric\n\nCLOSING istoric",
        teleprompter_text="OPENING istoric\n\nCLOSING istoric",
    )
    projection = project_editor_material_presentation_v2(event_id=7, draft=draft)
    assert projection.schema_label == "V1 (istoric)"
    assert projection.components == ()
    assert render_editor_material_presentation_v2(projection) == draft.assembled_text
    assert type(draft) is EpisodeDraft
