from pastila_scout.desktop_v1.editor_material_presentation_v2 import (
    EditorMaterialComponentPresentationV2,
    EditorMaterialPresentationV2,
    render_editor_material_presentation_v2,
)


def test_semantic_v2_presentation_renders_explicit_component_labels():
    presentation = EditorMaterialPresentationV2(
        event_id=7,
        schema_label="Semantic Draft V2",
        components=(
            EditorMaterialComponentPresentationV2(
                label="Rezumat factual", text="Text factual exact."
            ),
            EditorMaterialComponentPresentationV2(
                label="Comentariu acid: indisponibil",
                text="Nu este selectat încă un model Voice valid.",
                availability="unavailable",
            ),
        ),
        assembled_text="Text factual exact.",
    )

    assert render_editor_material_presentation_v2(presentation) == (
        "Format: Semantic Draft V2\n\n"
        "Rezumat factual\nText factual exact.\n\n"
        "Comentariu acid: indisponibil\n"
        "Nu este selectat încă un model Voice valid."
    )


def test_historical_v1_presentation_remains_byte_exact():
    presentation = EditorMaterialPresentationV2(
        event_id=7,
        schema_label="V1 (istoric)",
        components=(),
        assembled_text="Text istoric exact.",
    )

    assert render_editor_material_presentation_v2(presentation) == "Text istoric exact."
