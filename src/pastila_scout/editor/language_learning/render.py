"""Deterministic reference-only learning renderers."""

import json

from pydantic import BaseModel

from pastila_scout.editor.language_learning.fingerprint import canonical_semantics
from pastila_scout.editor.language_learning.models import *


def render_artifact(artifact: BaseModel) -> str:
    """Return canonical UTF-8-safe JSON, excluding runtime timestamp provenance."""
    payload = canonical_semantics(artifact)
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def render_edit_graph(graph: LanguageEditGraph) -> str:
    return (
        "\n".join(
            [
                "[Language Edit Graph]",
                f"Graph: {graph.graph_id}",
                f"Source: {graph.source_reference}",
                f"Target: {graph.target_reference}",
                *(
                    f"{i}. {x.operation_id} | {x.operation_type.value} | {x.affected_dimension} | {x.intent_reference}"
                    for i, x in enumerate(graph.ordered_operations, 1)
                ),
            ]
        )
        + "\n"
    )


def render_profile(profile: EditorialLanguageProfile) -> str:
    return (
        "\n".join(
            [
                "[Editorial Language Profile]",
                f"Profile: {profile.profile_id} {profile.profile_version}",
                f"Editor: {profile.editor_identity}",
                f"Maturity: {profile.profile_maturity.state}",
                f"Confidence: {profile.profile_confidence.state.value}",
                "Active Preferences:",
                *(
                    f"- {x.preference_id}"
                    for x in sorted(
                        profile.active_preferences, key=lambda x: x.preference_id
                    )
                ),
                "Conflicts:",
                *(
                    f"- {x.conflict_id}"
                    for x in sorted(profile.conflicts, key=lambda x: x.conflict_id)
                ),
            ]
        )
        + "\n"
    )


def render_guidance(projection: GuidanceProjection) -> str:
    return (
        "\n".join(
            [
                "[Guidance Projection]",
                f"Projection: {projection.projection_id}",
                *(
                    f"- {x.guidance_id} | {x.source_preference_id} | {x.confidence.state.value} | {x.scope.value}"
                    for x in sorted(projection.guidance, key=lambda x: x.guidance_id)
                ),
            ]
        )
        + "\n"
    )


def render_explanation(explanation: LearningExplanation) -> str:
    lines = ["[Learning Explanation]", f"Explanation: {explanation.explanation_id}"]
    for key, value in explanation.model_dump(mode="json").items():
        if key != "explanation_id":
            lines.append(
                f"- {key}: {', '.join(value) if isinstance(value,list) else value}"
            )
    return "\n".join(lines) + "\n"
