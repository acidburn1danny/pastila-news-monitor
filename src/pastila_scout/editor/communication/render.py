"""Deterministic reference-only Spoken Communication renderers."""

from collections.abc import Iterable

from pydantic import BaseModel

from pastila_scout.editor.communication.models import (
    CommunicationAssessment,
    CommunicationFlowModel,
    SpokenCommunicationEngine,
)
from pastila_scout.editor.communication.validator import (
    validate_communication_assessment,
    validate_spoken_communication_engine,
)
from pastila_scout.editor.story import StoryArchitecturePlan


def _humanize(name: str) -> str:
    return name.replace("_", " ").title()


def _model_lines(model: BaseModel) -> list[str]:
    lines: list[str] = []
    for name, value in model.model_dump(mode="json").items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value) or "None"
        else:
            rendered = str(value)
        lines.append(f"- {_humanize(name)}: {rendered}")
    return lines


def _section(title: str, values: Iterable[str]) -> list[str]:
    return ["", title, *values]


def render_spoken_communication_engine(
    engine: SpokenCommunicationEngine,
) -> str:
    """Render every canonical policy section in stable order."""

    validate_spoken_communication_engine(engine)
    lines = [
        "[Spoken Communication Engine]",
        *_section(
            "Identity",
            (
                f"{engine.communication_engine_id} {engine.version}",
                f"{engine.title} | {engine.language} | {engine.medium}",
            ),
        ),
        *_section("Purpose", (engine.purpose,)),
        *_section(
            "Core Assumptions", (f"- {item}" for item in engine.core_assumptions)
        ),
        *_section(
            "Canonical Principles",
            (
                f"{item.order}. {item.title}"
                for item in sorted(engine.principles, key=lambda item: item.order)
            ),
        ),
    ]
    sections = (
        ("Working Memory", engine.working_memory),
        ("Communication Flow", engine.communication_flow),
        ("Rhythm", engine.rhythm),
        ("Pauses", engine.pauses),
        ("Attention", engine.attention),
        ("Orientation", engine.orientation),
        ("Reference Continuity", engine.references),
        ("Communication Continuity", engine.continuity),
        ("Transitions", engine.transitions),
        ("Payoff Timing", engine.payoff_timing),
        ("Emotion Timing", engine.emotion_timing),
        ("Teleprompter Cognition", engine.teleprompter_cognition),
    )
    for title, model in sections:
        lines.extend(_section(title, _model_lines(model)))
    lines.extend(
        _section(
            "Profile Integration",
            (f"- {item}" for item in engine.supported_profile_dimensions),
        )
    )
    lines.extend(
        _section("Editor-in-Chief Authority", (engine.editor_in_chief_authority,))
    )
    lines.extend(
        _section("Fixed Boundaries", (f"- {item}" for item in engine.fixed_boundaries))
    )
    return "\n".join(lines) + "\n"


def render_working_memory(engine: SpokenCommunicationEngine) -> str:
    """Render the canonical working-memory heuristic model."""

    validate_spoken_communication_engine(engine)
    return "\n".join(["[Working Memory]", *_model_lines(engine.working_memory)]) + "\n"


def render_communication_flow(flow: CommunicationFlowModel) -> str:
    """Render dependency-flow policies without realizing wording."""

    return "\n".join(["[Communication Flow]", *_model_lines(flow)]) + "\n"


def render_rhythm(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Rhythm]", *_model_lines(engine.rhythm)]) + "\n"


def render_attention(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Attention]", *_model_lines(engine.attention)]) + "\n"


def render_orientation(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Orientation]", *_model_lines(engine.orientation)]) + "\n"


def render_continuity(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Continuity]", *_model_lines(engine.continuity)]) + "\n"


def render_transitions(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Transitions]", *_model_lines(engine.transitions)]) + "\n"


def render_pauses(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Pauses]", *_model_lines(engine.pauses)]) + "\n"


def render_emotion_timing(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return "\n".join(["[Emotion Timing]", *_model_lines(engine.emotion_timing)]) + "\n"


def render_teleprompter_cognition(engine: SpokenCommunicationEngine) -> str:
    validate_spoken_communication_engine(engine)
    return (
        "\n".join(
            ["[Teleprompter Cognition]", *_model_lines(engine.teleprompter_cognition)]
        )
        + "\n"
    )


def render_communication_assessment(
    assessment: CommunicationAssessment,
    engine: SpokenCommunicationEngine,
    story_plan: StoryArchitecturePlan,
) -> str:
    """Render assessment lineage, readiness, findings, and guidance."""

    validate_communication_assessment(assessment, engine, story_plan)
    lines = [
        "[Communication Assessment]",
        f"Identity: {assessment.assessment_id} {assessment.version}",
        f"Readiness: {assessment.readiness.value}",
        f"Engine: {assessment.communication_engine_id} {assessment.communication_engine_version}",
        f"Story Architecture: {assessment.story_architecture_id} {assessment.story_architecture_version}",
        f"Story Plan Fingerprint: {assessment.story_plan_fingerprint}",
        "Communication Risks:",
        *(
            f"- {risk.risk_id}: {risk.risk_type.value} [{risk.severity.value}]"
            for risk in sorted(assessment.risks, key=lambda risk: risk.risk_id)
        ),
        "Profile Guidance:",
        *(
            f"- {item.guidance_id}: {', '.join(sorted(item.tuning_dimensions))}"
            for item in sorted(
                assessment.profile_guidance, key=lambda item: item.guidance_id
            )
        ),
        "Blocking Issues:",
        *(f"- {item}" for item in sorted(assessment.blocking_issues)),
        "Advisory Issues:",
        *(f"- {item}" for item in sorted(assessment.advisory_issues)),
        f"Editor-in-Chief Review: {'Required' if assessment.requires_editor_in_chief_review else 'Not required'}",
        f"Summary: {assessment.summary}",
    ]
    return "\n".join(lines) + "\n"
