"""One-reviewer invocation and validation boundary."""

from pastila_scout.editor.qa.models import (
    EditorialReviewRequest,
    ReviewExecutionStatus,
    fingerprint,
)
from pastila_scout.editor.qa.pipeline.models import (
    PipelineDiagnostic,
    PipelineDiagnosticPhase,
    PipelineDiagnosticSeverity,
    ReviewerExecutionOutcome,
    ReviewerExecutionStatus,
)
from pastila_scout.editor.qa.validation import validate_review_result


class ReviewerExecutor:
    def execute(self, *, unit, pipeline_request, reviewer):
        request = EditorialReviewRequest(
            review_id="review:"
            + fingerprint(
                {
                    "execution": unit.execution_id,
                    "draft": fingerprint(pipeline_request.episode_draft),
                }
            ),
            reviewer_id=unit.reviewer_id,
            episode_draft=pipeline_request.episode_draft,
            scope=unit.scope,
            component_ids=unit.target_component_ids,
        )
        try:
            result = reviewer.review(request)
        except Exception:  # noqa: BLE001 - reviewer invocation boundary
            return _failure(unit, "REVIEWER_INVOCATION_EXCEPTION")
        try:
            validate_review_result(request, result)
            if result.reviewer_version != unit.reviewer_version:
                raise ValueError("version mismatch")
            if result.status is ReviewExecutionStatus.SKIPPED:
                return ReviewerExecutionOutcome.build(
                    execution_id=unit.execution_id,
                    reviewer_id=unit.reviewer_id,
                    required=unit.required,
                    status=ReviewerExecutionStatus.SKIPPED,
                    skip_code="REVIEWER_SELF_SKIPPED",
                )
            if result.status is ReviewExecutionStatus.FAILED:
                raise ValueError("reviewer returned failure status")
            return ReviewerExecutionOutcome.build(
                execution_id=unit.execution_id,
                reviewer_id=unit.reviewer_id,
                required=unit.required,
                status=ReviewerExecutionStatus.COMPLETED,
                review_result=result,
            )
        except Exception:  # noqa: BLE001 - result validation boundary
            return _failure(unit, "INVALID_REVIEW_RESULT")


def _failure(unit, code):
    diagnostic = PipelineDiagnostic.build(
        code=code,
        severity=PipelineDiagnosticSeverity.ERROR,
        phase=PipelineDiagnosticPhase.EXECUTION,
        execution_id=unit.execution_id,
        reviewer_id=unit.reviewer_id,
    )
    return ReviewerExecutionOutcome.build(
        execution_id=unit.execution_id,
        reviewer_id=unit.reviewer_id,
        required=unit.required,
        status=ReviewerExecutionStatus.FAILED,
        failure_code=code,
        diagnostics=(diagnostic,),
    )
