"""Minimal deterministic Editorial QA orchestration skeleton."""

from pastila_scout.editor.qa.aggregation import ApprovalPolicyEngine, FindingAggregator
from pastila_scout.editor.qa.manifest import EditorialReviewManifest, ReviewerPlan
from pastila_scout.editor.qa.models import (
    EditorialQAResult,
    EditorialQATrace,
    EditorialReviewRequest,
    QATraceRecord,
    ReviewerFailure,
    ReviewExecutionStatus,
    TraceEventType,
    fingerprint,
)
from pastila_scout.editor.qa.state import EditorialQAState
from pastila_scout.editor.qa.validation import (
    ReviewerResultValidationError,
    draft_component_ids,
    validate_review_result,
)


class EditorialQAError(RuntimeError):
    pass


class EditorialQAOrchestrator:
    """Execute independent reviewers, aggregate, and decide without rewriting."""

    def __init__(self, reviewers, *, approval_policy=None):
        self.reviewers = tuple(sorted(reviewers, key=lambda item: item.reviewer_id))
        if len({item.reviewer_id for item in self.reviewers}) != len(self.reviewers):
            raise EditorialQAError("reviewer IDs must be unique")
        self.approval_policy = approval_policy

    def review(self, draft, *, required_reviewer_ids=()):
        required = frozenset(required_reviewer_ids)
        known_components = draft_component_ids(draft)
        plans = tuple(
            ReviewerPlan(
                reviewer_id=reviewer.reviewer_id,
                reviewer_version=reviewer.reviewer_version,
                capabilities=reviewer.capabilities,
                target_component_ids=known_components,
                required=(not required or reviewer.reviewer_id in required),
            )
            for reviewer in self.reviewers
        )
        manifest = EditorialReviewManifest.build(plans)
        reviewer_map = {item.reviewer_id: item for item in self.reviewers}
        state = EditorialQAState()
        trace = [
            _trace(
                1,
                TraceEventType.MANIFEST_CREATED,
                state,
                state,
                message="manifest_created",
            )
        ]
        sequence = 2
        for item in manifest.items:
            if item.operation != "review":
                continue
            reviewer = reviewer_map[item.reviewer_id]
            request = EditorialReviewRequest(
                review_id="review:"
                + fingerprint(
                    {
                        "manifest_item_id": item.manifest_item_id,
                        "draft": fingerprint(draft),
                    }
                ),
                reviewer_id=item.reviewer_id,
                episode_draft=draft,
                scope=item.scope,
                component_ids=item.target_component_ids,
            )
            trace.append(
                _trace(
                    sequence,
                    TraceEventType.REVIEW_STARTED,
                    state,
                    state,
                    item=item,
                    message="review_started",
                )
            )
            sequence += 1
            before = state
            try:
                result = reviewer.review(request)
                validate_review_result(request, result)
                if result.status in {
                    ReviewExecutionStatus.FAILED,
                    ReviewExecutionStatus.SKIPPED,
                }:
                    raise ReviewerResultValidationError(
                        "reviewer returned non-completed status"
                    )
                state = state.accept_result(item.manifest_item_id, result)
                trace.append(
                    _trace(
                        sequence,
                        TraceEventType.RESULT_VALIDATED,
                        before,
                        before,
                        item=item,
                        result=result,
                        message="result_validated",
                    )
                )
                sequence += 1
                trace.append(
                    _trace(
                        sequence,
                        TraceEventType.REVIEW_COMPLETED,
                        before,
                        state,
                        item=item,
                        result=result,
                        message="review_completed",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - reviewer isolation boundary
                failure = ReviewerFailure(
                    manifest_item_id=item.manifest_item_id,
                    reviewer_id=item.reviewer_id,
                    required=item.required,
                    code=f"reviewer_failure.{type(exc).__name__}",
                    message="Reviewer execution or structural validation failed.",
                )
                state = state.accept_failure(failure)
                trace.append(
                    _trace(
                        sequence,
                        TraceEventType.REVIEW_FAILED,
                        before,
                        state,
                        item=item,
                        message=failure.code,
                    )
                )
            sequence += 1
        report = FindingAggregator().aggregate(
            draft=draft, manifest=manifest, state=state
        )
        before = state
        state = state.accept_aggregation()
        trace.append(
            _trace(
                sequence,
                TraceEventType.FINDINGS_AGGREGATED,
                before,
                state,
                message="findings_aggregated",
                findings=tuple(item.finding_id for item in report.findings),
            )
        )
        sequence += 1
        decision = ApprovalPolicyEngine().decide(report, self.approval_policy)
        before = state
        state = state.accept_approval(decision.status)
        trace.append(
            _trace(
                sequence,
                TraceEventType.APPROVAL_DECIDED,
                before,
                state,
                message="approval_decided",
            )
        )
        return EditorialQAResult(
            report=report,
            decision=decision,
            manifest=manifest,
            state=state,
            trace=EditorialQATrace(records=tuple(trace)),
        )


def _trace(
    sequence, event, before, after, *, item=None, result=None, message, findings=()
):
    return QATraceRecord(
        sequence_number=sequence,
        event_type=event,
        manifest_item_id=item.manifest_item_id if item else None,
        reviewer_id=item.reviewer_id if item else None,
        state_revision_before=before.revision,
        state_revision_after=after.revision,
        result_fingerprint=result.review_fingerprint if result else None,
        finding_ids=findings
        or (tuple(item.finding_id for item in result.findings) if result else ()),
        message_code=message,
    )
