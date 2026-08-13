"""Projection from daily desktop state into the existing Editor V1 request."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

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
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1


def _integrated_editor_request_v1(*, project: object, settings: object) -> EditorApplicationRequestV1:
    provider = ProviderChoiceV1(settings.editor_provider)
    model = settings.ollama_model if provider is ProviderChoiceV1.OLLAMA else settings.editor_model
    output_directory = settings.editor_output_directory
    if output_directory is None:
        raise ValueError("Editor output is unavailable")
    reference = f"editor-desktop-v1:{uuid.uuid4().hex}"
    destination = Path(output_directory) / f"editor-{project.candidate.event_id}-{uuid.uuid4().hex}.json"
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
            "mandatory_event_ids": (project.candidate.event_id,),
            "avoid_recent_event_ids": (),
            "previous_episode_reference": None,
        }
    )
    profile = sample_selection_profile().model_copy(
        update={
            "minimum_source_diversity": max(1, project.candidate.source_count),
        }
    )
    return EditorApplicationRequestV1(
        project.scout_input,
        profile,
        context,
        generation,
        EditorOutputDestinationV1(destination, EditorOverwritePolicyV1.FAIL_IF_EXISTS),
        datetime.now(UTC),
        reference,
        CancellationTokenV2(cancellation_requested=False),
    )


__all__: tuple[str, ...] = ()
