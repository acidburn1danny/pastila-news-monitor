"""Deterministic Romanian conversational readiness."""

from pastila_scout.editor.communication import CommunicationReadiness
from pastila_scout.editor.romanian_conversation.models import (
    AuthenticityState,
    ConversationalReadiness,
    FindingSeverity,
    GuidanceStatus,
    RomanianConversationalAssessment,
    SocialRegister,
)


def determine_conversational_readiness(
    assessment: RomanianConversationalAssessment,
    upstream_readiness: CommunicationReadiness,
) -> ConversationalReadiness:
    if (
        upstream_readiness == CommunicationReadiness.BLOCKED
        or assessment.dependencies
        or any(
            risk.blocking or risk.severity == FindingSeverity.CRITICAL
            for risk in assessment.risks
        )
        or assessment.authenticity_assessment.authenticity_state
        == AuthenticityState.BLOCKED
    ):
        return ConversationalReadiness.BLOCKED
    active_guidance = [
        item
        for item in assessment.profile_guidance
        if item.status
        in {GuidanceStatus.ESTABLISHED, GuidanceStatus.EXPLICIT_EDITOR_RULE}
    ]
    if (
        upstream_readiness == CommunicationReadiness.REQUIRES_EDITOR_REVIEW
        or assessment.review_reasons
        or assessment.register_assessment.requires_editor_review
        or assessment.selected_register == SocialRegister.STREET_INFLUENCED
        or assessment.authenticity_assessment.authenticity_state
        in {
            AuthenticityState.CONTEXT_DEPENDENT,
            AuthenticityState.REQUIRES_EDITOR_REVIEW,
        }
        or any(
            risk.requires_editor_review or risk.severity == FindingSeverity.HIGH
            for risk in assessment.risks
        )
        or len({(item.dimension, item.value) for item in active_guidance})
        < len(active_guidance)
    ):
        return ConversationalReadiness.REQUIRES_EDITOR_REVIEW
    if assessment.advisories or assessment.risks or assessment.ai_likeness_indicators:
        return ConversationalReadiness.READY_WITH_ADVISORIES
    return ConversationalReadiness.READY
