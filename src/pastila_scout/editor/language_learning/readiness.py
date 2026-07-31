from pastila_scout.editor.language_learning.models import (
    LearningReadiness,
    LearningSession,
)


def determine_learning_readiness(session: LearningSession) -> LearningReadiness:
    dependency_states = (
        {item.readiness for item in session.compatibility.dependencies}
        if session.compatibility
        else set()
    )
    if LearningReadiness.BLOCKED in dependency_states:
        return LearningReadiness.BLOCKED
    if session.blocking_issues:
        return LearningReadiness.BLOCKED
    if LearningReadiness.REQUIRES_EDITOR_REVIEW in dependency_states:
        return LearningReadiness.REQUIRES_EDITOR_REVIEW
    if session.review_issues:
        return LearningReadiness.REQUIRES_EDITOR_REVIEW
    if LearningReadiness.READY_WITH_ADVISORIES in dependency_states:
        return LearningReadiness.READY_WITH_ADVISORIES
    if session.advisory_issues:
        return LearningReadiness.READY_WITH_ADVISORIES
    return LearningReadiness.READY
