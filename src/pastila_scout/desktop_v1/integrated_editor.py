"""Projection from daily desktop state into the existing Editor V1 request."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.contracts.identity import (
    assign_scout_input_identity,
    verify_scout_input_identity,
)
from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_selection_profile,
)
from pastila_scout.editor_application_v1 import (
    EditorApplicationGenerationConfigurationV1,
    EditorApplicationRequestV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
)
from pastila_scout.editor_core_identities_v1 import (
    CORE_V1_1_MODEL_ID,
    CORE_V1_2_MODEL_ID,
)
from pastila_scout.editor.generation.semantic_draft_v2 import PastilaEditorSemanticDraftV2
from pastila_scout.editor_application_v1 import load_editor_operational_result_v1
from pastila_scout.expression_retrieval_v1.usage import load_committed_usage_receipts_v1
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1


def _selected_scout_input_v1(*, project: object, event_id: int):
    if type(event_id) is not int or event_id <= 0:
        raise ValueError("Invalid selected Editor event")
    source = project.scout_input
    verify_scout_input_identity(source)
    matches = tuple(
        event for event in source.ranked_events if event.event_id == event_id
    )
    if len(matches) != 1:
        raise ValueError("Selected Editor event is unavailable")
    selected = matches[0].model_copy(update={"rank": 1})
    data = source.model_dump(mode="json")
    data["ranked_events"] = [selected.model_dump(mode="json")]
    data["event_counts"]["reported"] = 1
    return assign_scout_input_identity(data), selected


def _integrated_editor_request_v1(
    *,
    project: object,
    settings: object,
    event_id: int | None = None,
    provider_override: str | None = None,
    model_override: str | None = None,
    governed_factual_material: bool = False,
) -> EditorApplicationRequestV1:
    if event_id is None:
        source, selected = project.scout_input, project.candidate
        event_id = selected.event_id
    else:
        source, selected = _selected_scout_input_v1(project=project, event_id=event_id)
    model = model_override or settings.editor_default_model
    if governed_factual_material:
        if model != CORE_V1_2_MODEL_ID:
            raise ValueError("Governed commentary requires PastilaAcida Core V1.2")
        source, selected = _governed_summary_source_v1(
            project=project,
            source=source,
            selected=selected,
            event_id=event_id,
        )
    provider = ProviderChoiceV1(
        "ollama"
        if model in {CORE_V1_1_MODEL_ID, CORE_V1_2_MODEL_ID}
        else (provider_override or settings.editor_provider)
    )
    output_directory = settings.editor_output_directory
    if output_directory is None:
        raise ValueError("Editor output is unavailable")
    reference = f"editor-desktop-v1:{uuid.uuid4().hex}"
    destination = Path(output_directory) / f"editor-{event_id}-{uuid.uuid4().hex}.json"
    generation = EditorApplicationGenerationConfigurationV1(
        "editor-application-generation-config-v1",
        provider,
        model,
        None,
        0.25,
        1.0,
        2000,
        None,
        True,
        settings.editor_timeout_seconds,
    )
    context = sample_episode_context().model_copy(
        update={
            "mandatory_event_ids": (event_id,),
            "avoid_recent_event_ids": (),
            "previous_episode_reference": None,
            "extensions": {
                "pastila.expression_usage_receipts_v1": tuple(
                    receipt.model_dump(mode="python")
                    for receipt in load_committed_usage_receipts_v1(
                        (material.output_path, material.payload_sha256)
                        for material in getattr(project, "editor_materials", ())
                        if material.event_id != event_id
                    )
                )
            },
        }
    )
    base_profile = sample_selection_profile()
    selected_category = selected.categories[0]
    profile = base_profile.model_copy(
        update={
            "category_constraints": {
                selected_category: next(
                    iter(base_profile.category_constraints.values())
                )
            },
            "minimum_source_diversity": max(
                1, len({item.source_id for item in selected.source_provenance})
            ),
        }
    )
    return EditorApplicationRequestV1(
        source,
        profile,
        context,
        generation,
        EditorOutputDestinationV1(destination, EditorOverwritePolicyV1.FAIL_IF_EXISTS),
        datetime.now(UTC),
        reference,
        CancellationTokenV2(cancellation_requested=False),
    )


def _governed_summary_source_v1(*, project, source, selected, event_id: int):
    """Bind commentary generation to the already-persisted factual authority."""

    materials = tuple(
        item for item in getattr(project, "editor_materials", ()) if item.event_id == event_id
    )
    if len(materials) != 1:
        raise ValueError("Governed Editor factual material is unavailable")
    material = materials[0]
    result = load_editor_operational_result_v1(
        path=Path(material.output_path), payload_sha256=material.payload_sha256
    )
    if type(result.draft) is not PastilaEditorSemanticDraftV2:
        raise ValueError("Governed Editor factual material is not Semantic Draft V2")
    stories = tuple(item for item in result.draft.stories if item.event_id == event_id)
    if len(stories) != 1:
        raise ValueError("Governed Editor factual story is unavailable")
    governed = stories[0].factual_summary.text
    selected = selected.model_copy(update={"canonical_summary": governed})
    data = source.model_dump(mode="json")
    data["ranked_events"] = [selected.model_dump(mode="json")]
    return assign_scout_input_identity(data), selected


__all__: tuple[str, ...] = ()
