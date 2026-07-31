"""Deterministic Audience Readiness precedence."""

from __future__ import annotations

from pastila_scout.editor.audience.models import (
    AudienceAssessment,
    AudienceReadiness,
    AudienceRiskSeverity,
    ContextBudgetLevel,
)
from pastila_scout.editor.decision.models import ProductionReadiness
from pastila_scout.editor.voice.models import HumorDensity


def determine_audience_readiness(
    assessment: AudienceAssessment, plan
) -> AudienceReadiness:
    """Derive readiness without predicting actual audience performance."""

    critical_or_blocking = any(
        risk.blocking or risk.severity == AudienceRiskSeverity.CRITICAL
        for risk in (*assessment.attention_risks, *assessment.trust_risks)
    )
    comprehension_block = (
        assessment.comprehension_assessment.missing_indispensable_context
        or assessment.comprehension_assessment.unresolved_central_factual_status
        or bool(assessment.comprehension_assessment.unresolved_reference_ids)
        or assessment.context_assessment.missing_indispensable_context
    )
    if (
        plan.production_readiness == ProductionReadiness.BLOCKED
        or critical_or_blocking
        or comprehension_block
        or assessment.blocking_issues
    ):
        return AudienceReadiness.BLOCKED
    guidance_conflict = any(
        item.contradictory_guidance_ids
        for item in assessment.calibration.established_profile_guidance
        if item.established and item.active
    )
    exceptional_unapproved = (
        assessment.context_assessment.budget_level == ContextBudgetLevel.EXCEPTIONAL
        and not assessment.requires_editor_in_chief_review
    )
    review_required = (
        plan.production_readiness == ProductionReadiness.REQUIRES_EDITOR_REVIEW
        or assessment.requires_editor_in_chief_review
        or any(
            risk.requires_editor_in_chief_review
            for risk in (*assessment.attention_risks, *assessment.trust_risks)
        )
        or any(
            item.requires_editor_in_chief_review
            for item in assessment.fatigue_assessments
        )
        or guidance_conflict
        or exceptional_unapproved
        or (
            assessment.emotional_calibration.tonal_seriousness.value == "grave"
            and assessment.emotional_calibration.unresolved_tonal_ambiguity
        )
    )
    if review_required:
        return AudienceReadiness.REQUIRES_EDITOR_REVIEW
    heavy_dense = (
        assessment.context_assessment.budget_level
        in {ContextBudgetLevel.HIGH, ContextBudgetLevel.EXCEPTIONAL}
        and assessment.calibration.voice_dimensions.humor_density == HumorDensity.DENSE
    )
    if (
        assessment.attention_risks
        or assessment.trust_risks
        or assessment.fatigue_assessments
        or assessment.advisory_issues
        or assessment.context_assessment.optional_context_excessive
        or heavy_dense
    ):
        return AudienceReadiness.READY_WITH_ADVISORIES
    return AudienceReadiness.READY
