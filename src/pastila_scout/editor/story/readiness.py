"""Deterministic Story Architecture readiness precedence."""

from pastila_scout.editor.audience.models import AudienceReadiness
from pastila_scout.editor.decision.models import ProductionReadiness, RiskSeverity
from pastila_scout.editor.story.models import (
    StoryArchitectureReadiness,
)


def determine_story_readiness(plan, decision_plan, audience_assessment):
    if (
        decision_plan.production_readiness == ProductionReadiness.BLOCKED
        or audience_assessment.audience_readiness == AudienceReadiness.BLOCKED
        or plan.blocking_issues
        or plan.unresolved_dependencies
        or plan.primary_spine_count != 1
        or not plan.primary_core_represented
        or any(
            r.blocking_status or r.severity == RiskSeverity.CRITICAL
            for r in plan.architecture_risks
        )
    ):
        return StoryArchitectureReadiness.BLOCKED
    review = (
        decision_plan.production_readiness == ProductionReadiness.REQUIRES_EDITOR_REVIEW
        or audience_assessment.audience_readiness
        == AudienceReadiness.REQUIRES_EDITOR_REVIEW
        or plan.requires_editor_in_chief_review
        or plan.selected_pattern.requires_editor_in_chief_review
        or plan.opening_plan.requires_editor_in_chief_review
        or plan.payoff_plan.requires_editor_in_chief_review
        or any(x.requires_editor_in_chief_review for x in plan.story_units)
        or any(x.requires_editor_in_chief_review for x in plan.transitions)
        or any(x.review_conditions for x in plan.context_placements)
        or any(x.requires_editor_in_chief_review for x in plan.consequence_plans)
        or any(x.requires_editor_in_chief_review for x in plan.satire_placements)
        or any(x.requires_editor_in_chief_review for x in plan.secondary_angles)
        or any(x.requires_editor_in_chief_review for x in plan.architecture_risks)
        or any(
            x.contradictory_guidance_ids
            for x in plan.profile_guidance
            if x.established and x.active
        )
    )
    if review:
        return StoryArchitectureReadiness.REQUIRES_EDITOR_REVIEW
    if plan.architecture_risks or plan.advisory_issues:
        return StoryArchitectureReadiness.READY_WITH_ADVISORIES
    return StoryArchitectureReadiness.READY
