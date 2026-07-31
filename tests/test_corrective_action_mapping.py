"""Exhaustive M6C.5F Part 2 mapping tests against frozen status enums."""

import pytest
from test_editorial_review_integration import _generation_case

from pastila_scout.editor.qa import ApprovalStatus
from pastila_scout.editor.qa.corrective_action import (
    CorrectiveAction,
    CorrectiveActionDecisionPolicy,
    CorrectiveActionDecisionReason,
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionService,
    build_standard_corrective_action_decision_policy,
)
from pastila_scout.editor.qa.corrective_action.evaluation import (
    EDITORIAL_STATUS_VALUES,
    M6C5D_STATUS_VALUES,
    M6C5E_STATUS_VALUES,
)
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionLifecycle,
    CorrectiveActionDecisionPhase,
    CorrectiveActionDecisionTraceType,
)
from pastila_scout.editor.qa.corrective_action.state import DecisionRuntimeState
from pastila_scout.editor.qa.integration import (
    EditorialReviewIntegrationPolicy,
    EditorialReviewIntegrationRequest,
    IntegrationStatus,
    build_standard_editorial_review_integration_service,
)
from pastila_scout.editor.qa.integration.models import (
    EditorialReviewIntegrationReport,
    EditorialReviewIntegrationResult,
)
from pastila_scout.editor.qa.models import EditorialApprovalDecision, fingerprint
from pastila_scout.editor.qa.orchestration import OrchestrationStatus
from pastila_scout.editor.qa.orchestration.models import (
    EditorialReviewOrchestrationReport,
    EditorialReviewOrchestrationResult,
)


def _completed():
    generator, invocation = _generation_case()
    return build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))


def _decide(integration, policy=None):
    policy = policy or build_standard_corrective_action_decision_policy()
    return CorrectiveActionDecisionService().decide(
        CorrectiveActionDecisionRequest.build(integration, policy)
    )


def _with_status(integration, status):
    review = integration.review_result
    editorial = review.editorial_result
    decision_values = editorial.decision.model_dump(
        mode="python", exclude={"decision_fingerprint"}
    )
    decision_values["status"] = status
    decision = EditorialApprovalDecision(
        **decision_values, decision_fingerprint=fingerprint(decision_values)
    )
    editorial = editorial.model_copy(update={"decision": decision})
    report_values = review.report.model_dump(
        mode="python", exclude={"report_fingerprint"}
    )
    report_values["editorial_status"] = status.value
    review_report = EditorialReviewOrchestrationReport(
        **report_values, report_fingerprint=fingerprint(report_values)
    )
    review_values = review.model_dump(
        mode="python", exclude={"result_fingerprint", "editorial_result", "report"}
    )
    review = EditorialReviewOrchestrationResult.build(
        **review_values, editorial_result=editorial, report=review_report
    )
    integration_report_values = integration.report.model_dump(
        mode="python", exclude={"report_fingerprint"}
    )
    integration_report_values.update(
        editorial_status=status.value,
        review_result_fingerprint=review.result_fingerprint,
    )
    integration_report = EditorialReviewIntegrationReport(
        **integration_report_values,
        report_fingerprint=fingerprint(integration_report_values),
    )
    integration_values = integration.model_dump(
        mode="python", exclude={"result_fingerprint", "review_result", "report"}
    )
    return EditorialReviewIntegrationResult.build(
        **integration_values, review_result=review, report=integration_report
    )


@pytest.mark.parametrize(
    ("status", "action", "reason", "policy_applied"),
    (
        (
            ApprovalStatus.APPROVED,
            CorrectiveAction.CONTINUE_WORKFLOW,
            CorrectiveActionDecisionReason.EDITORIAL_APPROVED,
            False,
        ),
        (
            ApprovalStatus.APPROVED_WITH_WARNINGS,
            CorrectiveAction.CONTINUE_WORKFLOW,
            CorrectiveActionDecisionReason.EDITORIAL_APPROVED,
            False,
        ),
        (
            ApprovalStatus.REQUIRES_REGENERATION,
            CorrectiveAction.REQUEST_REGENERATION,
            CorrectiveActionDecisionReason.EDITORIAL_REGENERATION_REQUIRED,
            False,
        ),
        (
            ApprovalStatus.REQUIRES_HUMAN_REVIEW,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveActionDecisionReason.EDITORIAL_HUMAN_REVIEW_REQUIRED,
            False,
        ),
        (
            ApprovalStatus.REJECTED,
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
            True,
        ),
        (
            ApprovalStatus.PENDING,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveActionDecisionReason.UPSTREAM_INCOMPLETE,
            True,
        ),
    ),
)
def test_every_editorial_status_has_intentional_mapping(
    status, action, reason, policy_applied
):
    result = _decide(_with_status(_completed(), status))
    assert result.decision.action is action
    assert result.decision.reason is reason
    assert result.decision.policy_applied is policy_applied


def test_rejection_policy_override_and_validation() -> None:
    integration = _with_status(_completed(), ApprovalStatus.REJECTED)
    policy = CorrectiveActionDecisionPolicy.build(
        rejected_action=CorrectiveAction.REQUEST_MANUAL_REVIEW
    )
    assert _decide(integration, policy).decision.action is (
        CorrectiveAction.REQUEST_MANUAL_REVIEW
    )
    with pytest.raises(ValueError):
        CorrectiveActionDecisionPolicy.build(
            rejected_action=CorrectiveAction.REQUEST_REGENERATION
        )


@pytest.mark.parametrize(
    "action",
    (
        CorrectiveAction.REQUEST_MANUAL_REVIEW,
        CorrectiveAction.HALT_WORKFLOW,
        CorrectiveAction.NO_ACTION,
    ),
)
def test_review_disabled_is_policy_controlled_and_never_approved(action) -> None:
    generator, invocation = _generation_case()
    integration = build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(
        EditorialReviewIntegrationRequest(
            generation=invocation,
            integration_policy=EditorialReviewIntegrationPolicy(
                require_review_after_generation=False
            ),
        )
    )
    policy = CorrectiveActionDecisionPolicy.build(review_disabled_action=action)
    result = _decide(integration, policy)
    assert result.decision.action is action
    assert result.decision.reason is CorrectiveActionDecisionReason.REVIEW_DISABLED
    assert result.decision.source_editorial_status is None


def test_status_inventory_is_exhaustive_against_frozen_enums() -> None:
    assert M6C5E_STATUS_VALUES == {item.value for item in IntegrationStatus}
    assert M6C5D_STATUS_VALUES == {item.value for item in OrchestrationStatus}
    assert EDITORIAL_STATUS_VALUES == {item.value for item in ApprovalStatus}


def test_runtime_state_is_immutable_revisioned_and_terminal() -> None:
    prepared = DecisionRuntimeState.prepared()
    validating = prepared.advance(
        CorrectiveActionDecisionLifecycle.VALIDATING,
        CorrectiveActionDecisionTraceType.REQUEST_RECEIVED,
        CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
    )
    failed = validating.advance(
        CorrectiveActionDecisionLifecycle.FAILED,
        CorrectiveActionDecisionTraceType.FAILED,
        CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
    )
    assert prepared.revision == 0 and validating.revision == 1
    assert failed.revision == 2 and len(failed.trace) == 2
    with pytest.raises(ValueError):
        failed.advance(
            CorrectiveActionDecisionLifecycle.FINALIZED,
            CorrectiveActionDecisionTraceType.FINALIZED,
            CorrectiveActionDecisionPhase.FINALIZATION,
        )
    with pytest.raises(ValueError):
        prepared.advance(
            CorrectiveActionDecisionLifecycle.FINALIZED,
            CorrectiveActionDecisionTraceType.FINALIZED,
            CorrectiveActionDecisionPhase.FINALIZATION,
        )
