"""Deterministic Spoken Communication assessment readiness."""

from pastila_scout.editor.communication.models import (
    CommunicationAssessment,
    CommunicationReadiness,
    CommunicationRiskSeverity,
)


def determine_communication_readiness(
    assessment: CommunicationAssessment,
) -> CommunicationReadiness:
    """Derive readiness using strict blocker, review, advisory precedence."""

    if assessment.blocking_issues or any(
        risk.blocking or risk.severity == CommunicationRiskSeverity.CRITICAL
        for risk in assessment.risks
    ):
        return CommunicationReadiness.BLOCKED
    if assessment.requires_editor_in_chief_review or any(
        risk.requires_editor_in_chief_review for risk in assessment.risks
    ):
        return CommunicationReadiness.REQUIRES_EDITOR_REVIEW
    if assessment.advisory_issues or assessment.risks:
        return CommunicationReadiness.READY_WITH_ADVISORIES
    return CommunicationReadiness.READY
