"""Structural validation of reviewer results against an immutable draft request."""

from pastila_scout.editor.qa.models import ReviewExecutionStatus, ReviewScope


class ReviewerResultValidationError(ValueError):
    pass


def draft_component_ids(draft):
    values = ["opening"]
    for position, _story in enumerate(draft.stories, 1):
        values.append(f"story-{position:02d}")
    for position, _transition in enumerate(draft.transitions, 1):
        values.append(f"transition-{position:02d}-{position + 1:02d}")
    values.append("closing")
    if draft.cta is not None:
        values.append("cta")
    values.append("teleprompter")
    return tuple(values)


def validate_review_result(request, result):
    if result.reviewer_id != request.reviewer_id:
        raise ReviewerResultValidationError("reviewer identity mismatch")
    known = set(draft_component_ids(request.episode_draft))
    if not set(result.reviewed_component_ids) <= known:
        raise ReviewerResultValidationError(
            "result contains unknown reviewed component"
        )
    if set(result.reviewed_component_ids) != set(request.component_ids):
        raise ReviewerResultValidationError("reviewed components do not match request")
    finding_ids = {item.finding_id for item in result.findings}
    for finding in result.findings:
        if finding.reviewer_id != result.reviewer_id:
            raise ReviewerResultValidationError("finding reviewer identity mismatch")
        location = finding.location
        if (
            location.component_type is not ReviewScope.EPISODE
            and location.component_id not in known
        ):
            raise ReviewerResultValidationError(
                "finding location references unknown component"
            )
        if (
            location.component_type is ReviewScope.STORY
            and location.story_position is not None
            and location.component_id != f"story-{location.story_position:02d}"
        ):
            raise ReviewerResultValidationError(
                "story position and component ID disagree"
            )
        if location.component_type is ReviewScope.TRANSITION:
            expected_transition = (
                f"transition-{location.transition_from_story_position:02d}-"
                f"{location.transition_to_story_position:02d}"
            )
            if location.component_id != expected_transition:
                raise ReviewerResultValidationError(
                    "transition positions and component ID disagree"
                )
        if not set(finding.related_finding_ids) <= finding_ids:
            raise ReviewerResultValidationError(
                "related finding ID is absent from result"
            )
        if (
            request.scope is not ReviewScope.EPISODE
            and finding.scope is not request.scope
        ):
            raise ReviewerResultValidationError("finding scope exceeds requested scope")
    if result.status is ReviewExecutionStatus.COMPLETED and result.warnings:
        raise ReviewerResultValidationError(
            "completed result with warnings must use warning status"
        )
    return result
