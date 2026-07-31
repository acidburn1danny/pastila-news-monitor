"""Lossless handoff of pipeline outcomes into frozen M6C.5A execution state."""

from pastila_scout.editor.qa.models import ReviewerFailure
from pastila_scout.editor.qa.state import EditorialQAState


def build_m6c5a_execution_state(result, plan):
    """Return unaggregated M6C.5A state from accepted operational outcomes."""

    units = {item.execution_id: item for item in plan.execution_units}
    state = EditorialQAState()
    for outcome in result.execution_outcomes:
        unit = units[outcome.execution_id]
        if outcome.review_result is not None:
            state = state.accept_result(unit.manifest_item_id, outcome.review_result)
        elif outcome.status.value == "failed":
            state = state.accept_failure(
                ReviewerFailure(
                    manifest_item_id=unit.manifest_item_id,
                    reviewer_id=unit.reviewer_id,
                    required=unit.required,
                    code=outcome.failure_code,
                    message="Reviewer pipeline execution failed.",
                )
            )
    return state
