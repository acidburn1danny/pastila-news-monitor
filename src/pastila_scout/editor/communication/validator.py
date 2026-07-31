"""Validation for language-neutral Spoken Communication contracts."""

import re

from pastila_scout.editor.communication.defaults import (
    CANONICAL_COMMUNICATION_PRINCIPLES,
    SUPPORTED_PROFILE_DIMENSIONS,
)
from pastila_scout.editor.communication.models import (
    CommunicationAssessment,
    SpokenCommunicationEngine,
)
from pastila_scout.editor.communication.readiness import (
    determine_communication_readiness,
)
from pastila_scout.editor.story import StoryArchitecturePlan, story_plan_fingerprint

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class CommunicationValidationError(ValueError):
    """Raised when a communication contract violates fixed boundaries."""


def validate_spoken_communication_engine(
    engine: SpokenCommunicationEngine,
) -> SpokenCommunicationEngine:
    """Validate canonical identity, completeness, and language-neutral boundaries."""

    errors: list[str] = []
    if not _SEMVER.fullmatch(engine.version):
        errors.append(
            "Spoken Communication Engine version must use semantic versioning"
        )
    identifiers = [principle.principle_id for principle in engine.principles]
    orders = [principle.order for principle in engine.principles]
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate communication principle identifiers")
    if len(orders) != len(set(orders)):
        errors.append("communication principle order must be unique")
    if set(identifiers) != {
        identifier for identifier, _ in CANONICAL_COMMUNICATION_PRINCIPLES
    }:
        errors.append("all canonical communication principles are required")
    if sorted(orders) != list(range(1, len(engine.principles) + 1)):
        errors.append("communication principle order must be explicit and contiguous")
    if engine.language != "language-neutral":
        errors.append("Spoken Communication Engine must remain language-neutral")
    if set(engine.supported_profile_dimensions) != set(SUPPORTED_PROFILE_DIMENSIONS):
        errors.append("profile integration points are incomplete or unknown")
    if engine.working_memory.claims_neuroscientific_precision:
        errors.append(
            "working-memory capacities are editorial heuristics, not neuroscience"
        )
    if (
        engine.payoff_timing.maximum_setup_units
        < engine.payoff_timing.minimum_setup_units
    ):
        errors.append("maximum payoff setup cannot be lower than minimum setup")
    if not engine.rhythm.serves_comprehension:
        errors.append("communication rhythm must serve comprehension")
    if engine.pauses.defines_punctuation:
        errors.append("communication pauses cannot define punctuation")
    if engine.attention.predicts_listener_behavior:
        errors.append("attention policy cannot predict listener behavior")
    if engine.transitions.contains_transition_wording:
        errors.append("communication transitions cannot contain generated wording")
    if engine.emotion_timing.contains_emotional_wording:
        errors.append("emotion timing cannot contain generated wording")
    if engine.teleprompter_cognition.contains_formatting_rules:
        errors.append("teleprompter cognition cannot define rendering or formatting")
    if any(
        (
            engine.contains_generated_language,
            engine.contains_language_specific_rules,
            engine.contains_generation_procedures,
            engine.implements_learning,
        )
    ):
        errors.append(
            "communication policy cannot generate language, specialize by language, or learn"
        )
    if errors:
        raise CommunicationValidationError("; ".join(errors))
    return engine


def validate_communication_assessment(
    assessment: CommunicationAssessment,
    engine: SpokenCommunicationEngine,
    story_plan: StoryArchitecturePlan,
) -> CommunicationAssessment:
    """Validate an assessment against canonical engine and Story Plan lineage."""

    validate_spoken_communication_engine(engine)
    errors: list[str] = []
    if not _SEMVER.fullmatch(assessment.version):
        errors.append("Communication Assessment version must use semantic versioning")
    if (
        assessment.communication_engine_id != engine.communication_engine_id
        or assessment.communication_engine_version != engine.version
    ):
        errors.append("Spoken Communication Engine identity mismatch")
    if (
        assessment.story_architecture_id != story_plan.architecture_id
        or assessment.story_architecture_version != story_plan.version
    ):
        errors.append("Story Architecture identity mismatch")
    if assessment.story_plan_fingerprint != story_plan_fingerprint(story_plan):
        errors.append("Story Architecture Plan fingerprint mismatch")
    risk_ids = [risk.risk_id for risk in assessment.risks]
    guidance_ids = [guidance.guidance_id for guidance in assessment.profile_guidance]
    if len(risk_ids) != len(set(risk_ids)):
        errors.append("duplicate Communication Risk identifiers")
    if len(guidance_ids) != len(set(guidance_ids)):
        errors.append("duplicate Communication Profile Guidance identifiers")
    for guidance in assessment.profile_guidance:
        if not guidance.established:
            errors.append("emerging profile findings cannot tune communication policy")
        if not set(guidance.tuning_dimensions).issubset(SUPPORTED_PROFILE_DIMENSIONS):
            errors.append(
                "Communication Profile Guidance uses an unknown tuning dimension"
            )
        if not guidance.fixed_boundary_compatible or any(
            (
                guidance.changes_story_architecture,
                guidance.changes_factual_content,
                guidance.overrides_voice,
                guidance.overrides_audience,
                guidance.overrides_persona_or_philosophy,
                guidance.implements_learning,
            )
        ):
            errors.append("Communication Profile Guidance overrides fixed boundaries")
    if any(
        (
            assessment.modifies_story_architecture,
            assessment.modifies_upstream_contracts,
            assessment.contains_generated_language,
            assessment.contains_generated_dialogue,
            assessment.contains_generated_transition,
            assessment.contains_generated_joke,
            assessment.contains_generated_hook,
            assessment.contains_generated_punchline,
            assessment.contains_language_specific_behavior,
            assessment.contains_teleprompter_formatting,
        )
    ):
        errors.append(
            "Communication Assessment cannot mutate, generate, or specialize language"
        )
    expected = determine_communication_readiness(assessment)
    if assessment.readiness != expected:
        errors.append(
            f"communication readiness must be {expected.value}, not {assessment.readiness.value}"
        )
    if errors:
        raise CommunicationValidationError("; ".join(errors))
    return assessment
