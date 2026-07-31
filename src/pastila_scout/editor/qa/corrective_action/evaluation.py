"""Single authoritative M6C.5F corrective-action evaluator."""

from dataclasses import dataclass

from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveAction,
    CorrectiveActionDecisionReason,
)
from pastila_scout.editor.qa.integration import IntegrationStatus

M6C5E_STATUS_VALUES = frozenset(item.value for item in IntegrationStatus)
M6C5D_STATUS_VALUES = frozenset(
    {
        "completed",
        "completed_with_limited_review",
        "completed_without_editorial_outcome",
        "failed_before_pipeline",
        "failed_after_pipeline",
        "failed_during_editorial_handoff",
    }
)
M6C5D_FAILURE_VALUES = frozenset(
    {
        "failed_before_pipeline",
        "failed_after_pipeline",
        "failed_during_editorial_handoff",
    }
)
EDITORIAL_STATUS_VALUES = frozenset(
    {
        "pending",
        "approved",
        "approved_with_warnings",
        "requires_regeneration",
        "requires_human_review",
        "rejected",
    }
)


@dataclass(frozen=True)
class DecisionEvaluation:
    action: CorrectiveAction
    reason: CorrectiveActionDecisionReason
    source_editorial_status: str | None
    policy_applied: bool
    decision_rule_id: str


class InvalidUpstreamStateError(ValueError):
    """The frozen result is valid structurally but inconsistent for decisioning."""


class UnsupportedUpstreamStatusError(ValueError):
    """An upstream status is unknown to this contract version."""


def evaluate_decision(integration_result, policy) -> DecisionEvaluation:
    """Classify one validated M6C.5E result without inspecting findings."""

    _validate_public_consistency(integration_result)
    status = integration_result.status
    if status is IntegrationStatus.FAILED_DURING_GENERATION:
        return _evaluation(
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionDecisionReason.UPSTREAM_GENERATION_FAILED,
            rule="integration.failed_during_generation",
        )
    if status is IntegrationStatus.FAILED_BEFORE_REVIEW:
        return _evaluation(
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionDecisionReason.UPSTREAM_DRAFT_INVALID,
            rule="integration.failed_before_review",
        )
    if status is IntegrationStatus.FAILED_DURING_REVIEW:
        return _evaluation(
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionDecisionReason.UPSTREAM_REVIEW_FAILED,
            rule="integration.failed_during_review",
        )
    if status is IntegrationStatus.COMPLETED_WITHOUT_REVIEW:
        return _evaluation(
            policy.review_disabled_action,
            CorrectiveActionDecisionReason.REVIEW_DISABLED,
            policy_applied=True,
            rule="policy.review_disabled_action",
        )
    if status is not IntegrationStatus.COMPLETED:
        raise UnsupportedUpstreamStatusError("unsupported M6C.5E status")

    review_result = integration_result.review_result
    if review_result is None:
        raise InvalidUpstreamStateError("completed integration has no review result")
    review_status = review_result.status.value
    if review_status not in M6C5D_STATUS_VALUES:
        raise UnsupportedUpstreamStatusError("unsupported M6C.5D status")
    if review_status in M6C5D_FAILURE_VALUES:
        raise InvalidUpstreamStateError("completed integration contains failed review")
    editorial_result = review_result.editorial_result
    if editorial_result is None:
        return _evaluation(
            policy.missing_editorial_action,
            CorrectiveActionDecisionReason.EDITORIAL_OUTCOME_ABSENT,
            policy_applied=True,
            rule="policy.missing_editorial_action",
        )
    editorial_status = editorial_result.decision.status.value
    if editorial_status not in EDITORIAL_STATUS_VALUES:
        raise UnsupportedUpstreamStatusError("unsupported editorial status")
    if editorial_status in {"approved", "approved_with_warnings"}:
        return _evaluation(
            CorrectiveAction.CONTINUE_WORKFLOW,
            CorrectiveActionDecisionReason.EDITORIAL_APPROVED,
            editorial_status=editorial_status,
            rule=f"editorial.{editorial_status}",
        )
    if editorial_status == "requires_regeneration":
        return _evaluation(
            CorrectiveAction.REQUEST_REGENERATION,
            CorrectiveActionDecisionReason.EDITORIAL_REGENERATION_REQUIRED,
            editorial_status=editorial_status,
            rule="editorial.requires_regeneration",
        )
    if editorial_status == "requires_human_review":
        return _evaluation(
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveActionDecisionReason.EDITORIAL_HUMAN_REVIEW_REQUIRED,
            editorial_status=editorial_status,
            rule="editorial.requires_human_review",
        )
    if editorial_status == "rejected":
        return _evaluation(
            policy.rejected_action,
            CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
            editorial_status=editorial_status,
            policy_applied=True,
            rule="policy.rejected_action",
        )
    if editorial_status == "pending":
        return _evaluation(
            policy.missing_editorial_action,
            CorrectiveActionDecisionReason.UPSTREAM_INCOMPLETE,
            editorial_status=editorial_status,
            policy_applied=True,
            rule="policy.missing_editorial_action.pending",
        )
    raise UnsupportedUpstreamStatusError("unsupported editorial status")


def _validate_public_consistency(result) -> None:
    if result.integration_version != "1.0.0":
        raise UnsupportedUpstreamStatusError("unsupported M6C.5E version")
    if result.status.value not in M6C5E_STATUS_VALUES:
        raise UnsupportedUpstreamStatusError("unsupported M6C.5E status")
    report = result.report
    if report.integration_status is not result.status:
        raise InvalidUpstreamStateError("integration report status mismatch")
    if report.review_performed != report.completeness.review_invoked:
        raise InvalidUpstreamStateError("review invocation metadata mismatch")
    if result.status is IntegrationStatus.COMPLETED:
        if result.review_result is None or not report.completeness.review_completed:
            raise InvalidUpstreamStateError("completed integration is incomplete")
    elif result.status is IntegrationStatus.COMPLETED_WITHOUT_REVIEW:
        if result.review_result is not None or report.review_performed:
            raise InvalidUpstreamStateError("no-review integration contains review")
    elif result.status is IntegrationStatus.FAILED_DURING_GENERATION:
        if result.review_result is not None:
            raise InvalidUpstreamStateError("generation failure contains review")
    elif result.status is IntegrationStatus.FAILED_BEFORE_REVIEW:
        if result.generation_result is None or result.review_result is not None:
            raise InvalidUpstreamStateError("before-review failure is inconsistent")
    elif result.status is IntegrationStatus.FAILED_DURING_REVIEW and (
        result.generation_result is None or result.draft_fingerprint is None
    ):
        raise InvalidUpstreamStateError("review failure lacks generated draft")


def _evaluation(
    action,
    reason,
    *,
    editorial_status=None,
    policy_applied=False,
    rule,
):
    return DecisionEvaluation(
        action=action,
        reason=reason,
        source_editorial_status=editorial_status,
        policy_applied=policy_applied,
        decision_rule_id=rule,
    )
