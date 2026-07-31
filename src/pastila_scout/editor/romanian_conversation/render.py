"""Deterministic Romanian conversational policy rendering."""

from pydantic import BaseModel

from pastila_scout.editor.communication import CommunicationAssessment
from pastila_scout.editor.romanian_conversation.models import (
    RomanianConversationalAssessment,
    RomanianConversationalEngine,
)
from pastila_scout.editor.romanian_conversation.validator import (
    validate_romanian_conversational_assessment,
    validate_romanian_conversational_engine,
)
from pastila_scout.editor.story import StoryArchitecturePlan


def _model_lines(model: BaseModel) -> list[str]:
    lines = []
    for key, value in model.model_dump(mode="json").items():
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value) or "None"
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return lines


def render_romanian_conversational_engine(engine: RomanianConversationalEngine) -> str:
    validate_romanian_conversational_engine(engine)
    lines = [
        "[Romanian Conversational Engine]",
        "",
        "Identity",
        f"{engine.conversational_engine_id} {engine.version}",
        f"{engine.title} | {engine.language_code} | {engine.primary_medium}",
        "",
        "Canonical Assumptions",
        *(f"- {item}" for item in engine.canonical_assumptions),
        "",
        "Canonical Principles",
        *(
            f"{item.order}. {item.title}"
            for item in sorted(engine.principles, key=lambda item: item.order)
        ),
        "",
        "Register Hierarchy",
        *(
            f"- preferred: {item.value}"
            for item in engine.register_policy.preferred_registers
        ),
    ]
    sections = (
        ("Conversational Authenticity", engine.authenticity_model),
        ("Syntax", engine.syntax_policy),
        ("Word Order", engine.word_order_policy),
        ("Ellipsis", engine.ellipsis_policy),
        ("Fragments", engine.fragment_policy),
        ("Repetition", engine.repetition_policy),
        ("Connectors", engine.connector_policy),
        ("Lexical Naturalness", engine.lexical_naturalness_policy),
        ("Colloquial Language", engine.colloquial_policy),
        ("Slang", engine.slang_policy),
        ("Jargon", engine.jargon_policy),
        ("Translated Constructions", engine.translated_construction_policy),
        ("Press Language", engine.press_language_policy),
        ("Bureaucratic Language", engine.bureaucratic_language_policy),
        ("Academic Language", engine.academic_language_policy),
        ("Legal Precision", engine.legal_precision_policy),
        ("Entity References", engine.entity_reference_policy),
        ("Demonstratives", engine.demonstrative_policy),
        ("Emphasis", engine.emphasis_policy),
        ("Romanian Rhythm", engine.rhythm_realization_policy),
        ("Conversational Repair", engine.repair_policy),
        ("Satire Integration", engine.satire_integration_policy),
        ("Sensitivity", engine.sensitivity_policy),
        ("Teleprompter Realization", engine.teleprompter_realization_policy),
    )
    for title, model in sections:
        lines.extend(("", title, *_model_lines(model)))
    lines.extend(
        (
            "",
            "Conversational Patterns",
            *(
                f"- {item.order}: {item.pattern_id}"
                for item in engine.conversational_patterns
            ),
        )
    )
    lines.extend(
        (
            "",
            "Canonical Reference Catalogue",
            *(
                f"- {item.entry_id}: {item.normalized_expression}"
                for item in sorted(
                    engine.canonical_reference_catalogue, key=lambda item: item.entry_id
                )
            ),
        )
    )
    lines.extend(
        (
            "",
            "AI-Likeness Indicators",
            *(
                f"- {item.indicator_id}"
                for item in sorted(
                    engine.ai_likeness_indicators, key=lambda item: item.indicator_id
                )
            ),
        )
    )
    lines.extend(
        (
            "",
            "Correction Integration Points",
            *(f"- {item}" for item in engine.correction_integration_points),
        )
    )
    lines.extend(
        (
            "",
            "Profile Guidance",
            *(f"- {item}" for item in engine.supported_guidance_dimensions),
        )
    )
    lines.extend(
        (
            "",
            "Fixed Boundaries",
            *(f"- {item}" for item in engine.fixed_boundaries),
            "",
            "Editor-in-Chief Authority",
            engine.editor_authority,
        )
    )
    return "\n".join(lines) + "\n"


def render_romanian_conversational_assessment(
    assessment: RomanianConversationalAssessment,
    engine: RomanianConversationalEngine,
    communication_assessment: CommunicationAssessment,
    story_plan: StoryArchitecturePlan,
) -> str:
    validate_romanian_conversational_assessment(
        assessment, engine, communication_assessment, story_plan
    )
    lines = [
        "[Romanian Conversational Assessment]",
        f"Identity: {assessment.assessment_id} {assessment.version}",
        f"Readiness: {assessment.readiness.value}",
        f"Engine: {assessment.engine_id} {assessment.engine_fingerprint}",
        f"Communication Assessment: {assessment.communication_assessment_id}",
        f"Story Architecture: {assessment.story_architecture_plan_id}",
        f"Authenticity: {assessment.authenticity_assessment.authenticity_state.value}",
        f"Register: {assessment.selected_register.value}",
        "Risks:",
        *(
            f"- {item.risk_id}: {item.risk_type} [{item.severity.value}]"
            for item in sorted(assessment.risks, key=lambda item: item.risk_id)
        ),
        "Advisories:",
        *(f"- {item}" for item in sorted(assessment.advisories)),
        "Review Reasons:",
        *(f"- {item}" for item in sorted(assessment.review_reasons)),
        "Profile Guidance:",
        *(
            f"- {item.guidance_id}: {item.dimension}"
            for item in sorted(
                assessment.profile_guidance, key=lambda item: item.guidance_id
            )
        ),
    ]
    return "\n".join(lines) + "\n"
