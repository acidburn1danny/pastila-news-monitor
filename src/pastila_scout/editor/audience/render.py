"""Deterministic renderers for audience configuration and assessments."""

from __future__ import annotations

from collections.abc import Iterable

from pastila_scout.editor.audience.models import (
    AudienceAssessment,
    AudienceCalibration,
    AudienceModel,
)
from pastila_scout.editor.audience.validator import (
    validate_audience_assessment,
    validate_audience_model,
)
from pastila_scout.editor.decision.models import EditorialDecisionPlan


def _bullets(values: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in sorted(values)]


def render_audience_model(model: AudienceModel) -> str:
    validate_audience_model(model)
    cognitive = model.cognitive_profile
    lines = [
        "[Audience Model]",
        "",
        "Audience Identity",
        f"Audience ID: {model.audience_id}",
        f"Version: {model.version}",
        f"Title: {model.title}",
        f"Project: {model.project}",
        f"Jurisdiction: {model.jurisdiction}",
        "",
        "Primary Medium",
        model.primary_medium,
        "",
        "Audience Assumptions",
        *_bullets(model.audience_assumptions),
        "",
        "Canonical Principles",
    ]
    for item in sorted(model.principles, key=lambda item: item.order):
        lines.extend((f"{item.order}. {item.title}", item.statement))
    lines.extend(
        (
            "",
            "Knowledge Model",
            f"Default prior knowledge: {model.knowledge_profile.default_prior_knowledge.value}",
            *_bullets(model.knowledge_profile.prohibited_assumptions),
            "",
            "Cognitive Model",
            f"Information density: {cognitive.preferred_information_density.value}",
            f"Context load: {cognitive.maximum_recommended_context_load.value}",
            f"Entity load: {cognitive.maximum_recommended_entity_load.value}",
            f"Numeric load: {cognitive.maximum_recommended_numeric_load.value}",
            "",
            "Context Policy",
            "Context must be proportionate and directly support comprehension.",
            "",
            "Attention Policy",
            *_bullets(model.attention_policy),
            "",
            "Trust Policy",
            *_bullets(model.trust_profile.foundations),
            "",
            "Emotional Reception",
            *_bullets(model.default_emotional_policy),
            "",
            "Fatigue Policy",
            *_bullets(model.fatigue_policy),
            "",
            "Relationship with Editorial Profile",
            "Only established, evidence-linked findings may tune non-fixed calibration.",
            "",
            "Editor-in-Chief Authority",
            "The Editor-in-Chief determines the final audience production standard.",
            "",
            "Fixed Boundaries",
            *_bullets(model.fixed_boundaries),
        )
    )
    return "\n".join(lines) + "\n"


def render_calibration(calibration: AudienceCalibration) -> str:
    return (
        "[Audience Calibration]\n"
        f"Audience: {calibration.audience_id} {calibration.audience_version}\n"
        f"Prior knowledge: {calibration.prior_knowledge.value}\n"
        f"Context budget: {calibration.context_budget.budget_level.value}\n"
        f"Information density: {calibration.cognitive_profile.preferred_information_density.value}\n"
        f"Primary emotion: {calibration.intended_emotional_response.primary_intended_response.value}\n"
    )


def render_audience_assessment(
    assessment: AudienceAssessment,
    plan: EditorialDecisionPlan,
    model: AudienceModel,
) -> str:
    validate_audience_assessment(assessment, plan, model)
    material = {item.material_id: item for item in plan.source_material}
    lines = [
        "[Audience Assessment]",
        "",
        "Assessment Identity",
        f"Assessment ID: {assessment.assessment_id}",
        f"Decision Plan: {assessment.decision_plan_id}",
        "",
        "Audience Readiness",
        assessment.audience_readiness.value,
        "",
        "Audience Calibration",
        render_calibration(assessment.calibration).rstrip(),
        "",
        "Comprehension Assessment",
        assessment.comprehension_assessment.summary,
        "",
        "Context Assessment",
        assessment.context_assessment.justification,
        *[
            f"- {item}: {material[item].content}"
            for item in sorted(
                assessment.context_assessment.required_context_material_ids
            )
            if item in material
        ],
        "",
        "Attention Risks",
        *[
            f"- {item.risk_id}: {item.explanation}"
            for item in sorted(assessment.attention_risks, key=lambda x: x.risk_id)
        ],
        "",
        "Trust Risks",
        *[
            f"- {item.risk_id}: {item.explanation}"
            for item in sorted(assessment.trust_risks, key=lambda x: x.risk_id)
        ],
        "",
        "Fatigue Assessment",
        *[
            f"- {item.fatigue_id}: {item.explanation}"
            for item in sorted(
                assessment.fatigue_assessments, key=lambda x: x.fatigue_id
            )
        ],
        "",
        "Emotional Calibration",
        assessment.emotional_calibration.primary_intended_response.value,
        "",
        "Unresolved Audience Questions",
        *_bullets(assessment.unresolved_audience_questions),
        "",
        "Blocking Issues",
        *_bullets(assessment.blocking_issues),
        "",
        "Advisory Issues",
        *_bullets(assessment.advisory_issues),
        "",
        "Editor-in-Chief Review",
        "Required" if assessment.requires_editor_in_chief_review else "Not required",
    ]
    return "\n".join(lines) + "\n"
