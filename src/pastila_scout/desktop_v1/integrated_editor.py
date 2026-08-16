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
    *, project: object, settings: object, event_id: int | None = None
) -> EditorApplicationRequestV1:
    if event_id is None:
        event_id = project.candidate.event_id
        source, selected = project.scout_input, project.candidate
    else:
        source, selected = _selected_scout_input_v1(project=project, event_id=event_id)
    provider = ProviderChoiceV1(settings.editor_provider)
    model = (
        settings.ollama_model
        if provider is ProviderChoiceV1.OLLAMA
        else settings.editor_model
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
    profile = sample_selection_profile().model_copy(
        update={
            "minimum_source_diversity": max(1, selected.source_count),
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


__all__: tuple[str, ...] = ()
