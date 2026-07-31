"""Structural and cross-contract Romanian conversational validation."""

import re

from pastila_scout.editor.communication import (
    DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
    CommunicationAssessment,
    communication_assessment_fingerprint,
    communication_engine_fingerprint,
    rhythm_fingerprint,
    validate_communication_assessment,
)
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA
from pastila_scout.editor.romanian_conversation.defaults import (
    CANONICAL_PRINCIPLE_TITLES,
    SUPPORTED_GUIDANCE_DIMENSIONS,
)
from pastila_scout.editor.romanian_conversation.fingerprint import engine_fingerprint
from pastila_scout.editor.romanian_conversation.models import (
    AuthenticityState,
    ConversationalReadiness,
    CorrectionIntegrationPoint,
    CorrectionScope,
    GuidanceScope,
    GuidanceStatus,
    PolicyModel,
    RomanianConversationalAssessment,
    RomanianConversationalEngine,
    SocialRegister,
)
from pastila_scout.editor.romanian_conversation.readiness import (
    determine_conversational_readiness,
)
from pastila_scout.editor.story import StoryArchitecturePlan, story_plan_fingerprint

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class RomanianConversationValidationError(ValueError):
    pass


def validate_romanian_conversational_engine(
    engine: RomanianConversationalEngine,
) -> RomanianConversationalEngine:
    errors: list[str] = []
    if not _SEMVER.fullmatch(engine.version):
        errors.append(
            "Romanian Conversational Engine version must use semantic versioning"
        )
    if engine.language != "Romanian" or engine.language_code != "ro-RO":
        errors.append("canonical language identity must be Romanian ro-RO")
    ids = [item.principle_id for item in engine.principles]
    orders = [item.order for item in engine.principles]
    if len(ids) != len(set(ids)) or len(orders) != len(set(orders)):
        errors.append(
            "Romanian conversational principle identifiers and order must be unique"
        )
    if len(engine.principles) != len(CANONICAL_PRINCIPLE_TITLES) or sorted(
        orders
    ) != list(range(1, 37)):
        errors.append("all 36 ordered canonical principles are required")
    for collection, attribute, label in (
        (engine.conversational_patterns, "pattern_id", "pattern"),
        (engine.canonical_reference_catalogue, "entry_id", "reference"),
        (engine.ai_likeness_indicators, "indicator_id", "AI-likeness indicator"),
        (engine.default_risk_definitions, "risk_id", "risk"),
    ):
        values = [getattr(item, attribute) for item in collection]
        if len(values) != len(set(values)):
            errors.append(f"duplicate {label} identifiers")
    if engine.register_policy.preferred_registers != (
        SocialRegister.NEUTRAL_CONVERSATIONAL,
        SocialRegister.POLISHED_CONVERSATIONAL,
        SocialRegister.INFORMAL_CONVERSATIONAL,
        SocialRegister.RESTRAINED_COLLOQUIAL,
    ):
        errors.append("canonical preferred register precedence changed")
    if set(engine.supported_guidance_dimensions) != set(SUPPORTED_GUIDANCE_DIMENSIONS):
        errors.append("unknown or missing profile guidance dimensions")
    communication = DEFAULT_SPOKEN_COMMUNICATION_ENGINE
    if (
        engine.rhythm_realization_policy.communication_rhythm_fingerprint
        != rhythm_fingerprint(communication.rhythm)
    ):
        errors.append("Romanian rhythm does not match Spoken Communication lineage")
    if (
        engine.teleprompter_realization_policy.communication_teleprompter_fingerprint
        != communication_engine_fingerprint(communication.teleprompter_cognition)
    ):
        errors.append(
            "Romanian teleprompter policy does not match communication lineage"
        )
    policies = [value for _, value in engine if isinstance(value, PolicyModel)]
    if any(
        policy.permits_generated_wording or policy.overrides_upstream
        for policy in policies
    ):
        errors.append(
            "Romanian policies cannot generate wording or override upstream contracts"
        )
    if any(
        indicator.claims_ai_authorship for indicator in engine.ai_likeness_indicators
    ):
        errors.append("AI-likeness indicators cannot claim AI authorship")
    if (
        engine.contains_generation_procedures
        or engine.implements_learning
        or engine.contains_unbounded_dictionary
    ):
        errors.append(
            "engine cannot generate, learn, or implement an unbounded dictionary"
        )
    if errors:
        raise RomanianConversationValidationError("; ".join(errors))
    return engine


def validate_correction_integration_point(
    point: CorrectionIntegrationPoint,
) -> CorrectionIntegrationPoint:
    errors = []
    if (
        point.correction_scope == CorrectionScope.PERMANENT_PROJECT_RULE
        and not point.explicit_permanence
    ):
        errors.append(
            "permanent project correction requires explicit editor permanence"
        )
    if any(
        (
            point.performs_learning,
            point.performs_persistence,
            point.mutates_canonical_engine,
            point.contains_generated_replacement_prose,
        )
    ):
        errors.append(
            "correction handoff cannot learn, persist, mutate canon, or generate replacement prose"
        )
    if errors:
        raise RomanianConversationValidationError("; ".join(errors))
    return point


def validate_romanian_conversational_assessment(
    assessment: RomanianConversationalAssessment,
    engine: RomanianConversationalEngine,
    communication_assessment: CommunicationAssessment,
    story_plan: StoryArchitecturePlan,
) -> RomanianConversationalAssessment:
    validate_romanian_conversational_engine(engine)
    validate_communication_assessment(
        communication_assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, story_plan
    )
    errors: list[str] = []
    if not _SEMVER.fullmatch(assessment.version):
        errors.append(
            "Romanian Conversational Assessment version must use semantic versioning"
        )
    if (
        assessment.engine_id,
        assessment.engine_version,
        assessment.engine_fingerprint,
    ) != (engine.conversational_engine_id, engine.version, engine_fingerprint(engine)):
        errors.append("Romanian Conversational Engine identity or fingerprint mismatch")
    if (
        assessment.communication_assessment_id,
        assessment.communication_assessment_fingerprint,
    ) != (
        communication_assessment.assessment_id,
        communication_assessment_fingerprint(communication_assessment),
    ):
        errors.append(
            "Spoken Communication Assessment identity or fingerprint mismatch"
        )
    if (
        assessment.story_architecture_plan_id != story_plan.architecture_id
        or assessment.story_architecture_plan_fingerprint
        != story_plan_fingerprint(story_plan)
    ):
        errors.append("Story Architecture Plan identity or fingerprint mismatch")
    philosophy = DEFAULT_EDITORIAL_PERSONA.philosophy
    expected_ids = (
        story_plan.persona_id,
        story_plan.philosophy_id,
        story_plan.voice_id,
        story_plan.audience_id,
        story_plan.decision_plan_id,
    )
    if (
        assessment.persona_id,
        assessment.philosophy_id,
        assessment.voice_id,
        assessment.audience_id,
        assessment.decision_plan_id,
    ) != expected_ids:
        errors.append("upstream editorial identity mismatch")
    if (
        assessment.persona_id != DEFAULT_EDITORIAL_PERSONA.persona_id
        or assessment.philosophy_id != philosophy.philosophy_id
    ):
        errors.append("Persona or Philosophy identity mismatch")
    if assessment.selected_register != assessment.register_assessment.selected_register:
        errors.append("selected register and Register Assessment disagree")
    register = assessment.register_assessment
    if (
        not all(
            (
                register.context_compatible,
                register.audience_compatible,
                register.persona_compatible,
                register.voice_compatible,
                register.severity_compatible,
                register.socially_credible,
                register.public_broadcast_suitable,
            )
        )
        and not register.requires_editor_review
    ):
        errors.append("incompatible register requires Editor-in-Chief review")
    if (
        assessment.authenticity_assessment.engine_fingerprint
        != assessment.engine_fingerprint
        or assessment.authenticity_assessment.communication_assessment_fingerprint
        != assessment.communication_assessment_fingerprint
    ):
        errors.append("Conversational Authenticity Assessment lineage mismatch")
    if (
        assessment.authenticity_assessment.authenticity_state
        == AuthenticityState.CONTEXT_DEPENDENT
        and assessment.readiness
        not in {
            ConversationalReadiness.REQUIRES_EDITOR_REVIEW,
            ConversationalReadiness.BLOCKED,
        }
    ):
        errors.append("context-dependent authenticity requires review")
    active = {GuidanceStatus.ESTABLISHED, GuidanceStatus.EXPLICIT_EDITOR_RULE}
    guidance_ids = [item.guidance_id for item in assessment.profile_guidance]
    if len(guidance_ids) != len(set(guidance_ids)):
        errors.append("duplicate profile guidance identifiers")
    for guidance in assessment.profile_guidance:
        if guidance.dimension not in SUPPORTED_GUIDANCE_DIMENSIONS:
            errors.append("unknown Romanian profile guidance dimension")
        if (
            guidance.status == GuidanceStatus.EXPLICIT_EDITOR_RULE
            and not guidance.editor_confirmed
        ):
            errors.append("explicit editor guidance requires confirmation")
        if guidance.status not in active and guidance.scope != GuidanceScope.LOCAL_ONLY:
            continue
        if (
            not guidance.fixed_boundary_compatible
            or guidance.attempts_upstream_override
        ):
            errors.append("profile guidance cannot override fixed boundaries")
    for indicator in assessment.ai_likeness_indicators:
        if indicator.claims_ai_authorship:
            errors.append("AI-likeness indicators cannot claim authorship")
    risks = [risk.risk_id for risk in assessment.risks]
    if len(risks) != len(set(risks)):
        errors.append("duplicate Romanian Conversational Risk identifiers")
    if any(risk.contains_replacement_wording for risk in assessment.risks):
        errors.append("risk mitigation cannot contain replacement wording")
    if (
        assessment.contains_generated_text
        or assessment.contains_replacement_language
        or assessment.modifies_upstream_contracts
    ):
        errors.append(
            "assessment cannot generate language or modify upstream contracts"
        )
    expected = determine_conversational_readiness(
        assessment, communication_assessment.readiness
    )
    if assessment.readiness != expected:
        errors.append(
            f"conversational readiness must be {expected.value}, not {assessment.readiness.value}"
        )
    if errors:
        raise RomanianConversationValidationError("; ".join(errors))
    return assessment
