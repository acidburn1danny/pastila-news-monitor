"""Native Editor material projections for historical V1 and semantic V2 UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.editor_application_v1 import load_editor_operational_result_v1
from pastila_scout.editor_voice_application_v2 import (
    EditorVoiceApplicationOutcomeV1,
    EditorVoiceApplicationResultV1,
    EditorVoiceApplicationServiceV1,
    UnavailableVoiceExecutorV1,
)


@dataclass(frozen=True, slots=True)
class EditorMaterialComponentPresentationV2:
    label: str
    text: str
    availability: str = "present"
    generation_enabled: bool = False
    retry_enabled: bool = False


@dataclass(frozen=True, slots=True)
class EditorMaterialPresentationV2:
    event_id: int
    schema_label: str
    components: tuple[EditorMaterialComponentPresentationV2, ...]
    assembled_text: str


def voice_workflow_sidecar_path_v1(material_path: Path) -> Path:
    return material_path.with_suffix(material_path.suffix + ".voice-workflow-v1.json")


def load_editor_material_presentation_v2(
    *,
    material,
    voice_application: EditorVoiceApplicationServiceV1 | None = None,
) -> EditorMaterialPresentationV2:
    if not material.output_path or not material.payload_sha256:
        raise ValueError("Editor material artifact is unavailable")
    material_path = Path(material.output_path)
    result = load_editor_operational_result_v1(
        path=material_path, payload_sha256=material.payload_sha256
    )
    if result.draft is None:
        raise ValueError("Editor material draft is unavailable")
    voice_results = None
    if type(result.draft) is PastilaEditorSemanticDraftV2:
        application = voice_application or EditorVoiceApplicationServiceV1(
            executor=UnavailableVoiceExecutorV1(), clock=lambda: datetime.now(UTC)
        )
        voice_results = {
            material.event_id: application.inspect_persisted_story(
                draft=result.draft,
                story_material_reference=material.reference,
                event_id=material.event_id,
                sidecar_path=voice_workflow_sidecar_path_v1(material_path),
            )
        }
    return project_editor_material_presentation_v2(
        event_id=material.event_id,
        draft=result.draft,
        voice_results=voice_results,
    )


def project_editor_material_presentation_v2(
    *,
    event_id: int,
    draft: EpisodeDraft | PastilaEditorSemanticDraftV2,
    voice_results: dict[int, EditorVoiceApplicationResultV1] | None = None,
) -> EditorMaterialPresentationV2:
    """Project UI content without changing or compatibility-projecting the draft."""

    if type(event_id) is not int or event_id <= 0:
        raise ValueError("Invalid Editor event identity")
    if type(draft) is EpisodeDraft:
        return EditorMaterialPresentationV2(
            event_id=event_id,
            schema_label="V1 (istoric)",
            components=(),
            assembled_text=draft.assembled_text,
        )
    if type(draft) is not PastilaEditorSemanticDraftV2:
        raise ValueError("Unsupported Editor draft schema")

    components: list[EditorMaterialComponentPresentationV2] = []
    if draft.intro is not None:
        components.append(
            EditorMaterialComponentPresentationV2(
                "Introducere episod", draft.intro.text
            )
        )
    for index, story in enumerate(draft.stories):
        components.append(
            EditorMaterialComponentPresentationV2(
                "Rezumat factual", story.factual_summary.text
            )
        )
        voice_result = (
            None if voice_results is None else voice_results.get(story.event_id)
        )
        if voice_result is None:
            voice_result = _unpersisted_voice_result(
                draft=draft, event_id=story.event_id
            )
        components.append(
            _voice_component_presentation(story=story, result=voice_result)
        )
        if index + 1 < len(draft.stories):
            next_story = draft.stories[index + 1]
            transition = next(
                (
                    item
                    for item in draft.transitions
                    if item.from_event_id == story.event_id
                    and item.to_event_id == next_story.event_id
                ),
                None,
            )
            if transition is not None:
                components.append(
                    EditorMaterialComponentPresentationV2(
                        "Tranziție între știri", transition.text
                    )
                )
    if draft.final_monologue is not None:
        components.append(
            EditorMaterialComponentPresentationV2(
                "Monolog final", draft.final_monologue.text
            )
        )
    return EditorMaterialPresentationV2(
        event_id=event_id,
        schema_label="Semantic Draft V2",
        components=tuple(components),
        assembled_text=draft.assembled_text,
    )


def render_editor_material_presentation_v2(
    value: EditorMaterialPresentationV2,
) -> str:
    if type(value) is not EditorMaterialPresentationV2:
        raise ValueError("Invalid Editor material presentation")
    if value.schema_label == "V1 (istoric)":
        return value.assembled_text
    sections = [f"Format: {value.schema_label}"]
    sections.extend(
        (f"{component.label}\n{component.text}" if component.text else component.label)
        for component in value.components
    )
    return "\n\n".join(sections)


def _unpersisted_voice_result(
    *, draft: PastilaEditorSemanticDraftV2, event_id: int
) -> EditorVoiceApplicationResultV1:
    application = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: datetime.now(UTC)
    )
    return application.inspect_persisted_story(
        draft=draft,
        story_material_reference=f"editor-material-v2:event:{event_id}:unpersisted",
        event_id=event_id,
        sidecar_path=None,
    )


def _voice_component_presentation(
    *, story, result: EditorVoiceApplicationResultV1
) -> EditorMaterialComponentPresentationV2:
    if (
        story.acid_commentary is not None
        and story.acid_commentary.execution_provenance is not None
        and story.acid_commentary.execution_provenance.backend_kind == "model"
    ):
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: generat de modelul local",
            story.acid_commentary.text,
            "generated",
        )
    if (
        story.acid_commentary is not None
        and story.acid_commentary.execution_provenance is not None
        and story.acid_commentary.execution_provenance.backend_kind
        == "deterministic_renderer"
    ):
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: generat determinist",
            story.acid_commentary.text,
            "generated",
        )
    if (
        story.acid_commentary is None
        and story.acid_commentary_status == "absent_owner_removed"
    ):
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: eliminat de editor",
            "Comentariul a fost eliminat explicit; rezumatul factual rămâne neschimbat.",
            "owner_removed",
        )
    outcome = result.outcome
    if outcome is EditorVoiceApplicationOutcomeV1.GENERATED:
        if story.acid_commentary is not None:
            return EditorMaterialComponentPresentationV2(
                "Comentariu acid: generat",
                story.acid_commentary.text,
                "generated",
            )
        outcome = EditorVoiceApplicationOutcomeV1.INVALID_BINDING
    if outcome is EditorVoiceApplicationOutcomeV1.UNAVAILABLE:
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: indisponibil",
            "Nu este selectat încă un model Voice valid.",
            "unavailable",
        )
    if outcome is EditorVoiceApplicationOutcomeV1.UNGENERATED:
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: negenerat",
            "",
            "ungenerated",
            generation_enabled=result.generation_possible,
        )
    if outcome is EditorVoiceApplicationOutcomeV1.FAILED:
        detail = result.safe_failure_code or "voice_execution_failed"
        return EditorMaterialComponentPresentationV2(
            "Comentariu acid: eșuat",
            f"Generarea comentariului a eșuat în siguranță ({detail}).",
            "failed",
            retry_enabled=result.generation_possible,
        )
    return EditorMaterialComponentPresentationV2(
        "Comentariu acid: eroare de integritate",
        "Legătura dintre comentariu și materialul factual nu este validă.",
        "invalid_binding",
    )


__all__ = (
    "EditorMaterialComponentPresentationV2",
    "EditorMaterialPresentationV2",
    "load_editor_material_presentation_v2",
    "project_editor_material_presentation_v2",
    "render_editor_material_presentation_v2",
    "voice_workflow_sidecar_path_v1",
)
