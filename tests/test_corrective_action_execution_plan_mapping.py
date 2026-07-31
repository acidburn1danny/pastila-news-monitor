"""Authoritative M6C.6A Part 2 action-to-plan mapping tests."""

import pytest
from test_corrective_action_decision_contracts import _completed_integration

from pastila_scout.editor.qa.corrective_action import (
    CorrectiveAction,
    CorrectiveActionDecision,
    CorrectiveActionDecisionReason,
    CorrectiveActionDecisionReport,
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionResult,
    CorrectiveActionDecisionService,
    build_standard_corrective_action_decision_policy,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanService,
    CorrectiveActionExecutionPlanType,
    build_standard_corrective_action_execution_plan_policy,
)

_REASONS = {
    CorrectiveAction.CONTINUE_WORKFLOW: (
        CorrectiveActionDecisionReason.EDITORIAL_APPROVED
    ),
    CorrectiveAction.REQUEST_REVISION: (
        CorrectiveActionDecisionReason.EDITORIAL_REVISION_REQUIRED
    ),
    CorrectiveAction.REQUEST_REGENERATION: (
        CorrectiveActionDecisionReason.EDITORIAL_REGENERATION_REQUIRED
    ),
    CorrectiveAction.REQUEST_MANUAL_REVIEW: (
        CorrectiveActionDecisionReason.EDITORIAL_HUMAN_REVIEW_REQUIRED
    ),
    CorrectiveAction.HALT_WORKFLOW: (CorrectiveActionDecisionReason.EDITORIAL_REJECTED),
    CorrectiveAction.NO_ACTION: CorrectiveActionDecisionReason.REVIEW_DISABLED,
}


def _decision_result(action: CorrectiveAction):
    decision_request = CorrectiveActionDecisionRequest.build(
        _completed_integration(),
        build_standard_corrective_action_decision_policy(),
    )
    base = CorrectiveActionDecisionService().decide(decision_request)
    reason = _REASONS[action]
    policy_applied = reason in {
        CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
        CorrectiveActionDecisionReason.REVIEW_DISABLED,
    }
    decision = CorrectiveActionDecision.build(
        action=action,
        reason=reason,
        source_integration_fingerprint=base.integration_result.result_fingerprint,
        source_editorial_status=base.decision.source_editorial_status,
        policy_fingerprint=base.decision.policy_fingerprint,
        policy_applied=policy_applied,
        decision_rule_id=f"test.{action.value}",
    )
    report_values = base.report.model_dump(
        exclude={"report_fingerprint"}, mode="python"
    )
    report_values.update(
        requested_action=action,
        decision_reason=reason,
        decision_fingerprint=decision.decision_fingerprint,
    )
    report = CorrectiveActionDecisionReport.build(**report_values)
    return CorrectiveActionDecisionResult.build(
        descriptor=base.descriptor,
        request_fingerprint=base.request_fingerprint,
        integration_result=base.integration_result,
        operational_outcome=base.operational_outcome,
        decision=decision,
        lifecycle=base.lifecycle,
        diagnostics=base.diagnostics,
        trace=base.trace,
        completeness=base.completeness,
        report=report,
    )


def _planning_request(action: CorrectiveAction, **policy_values):
    decision_result = _decision_result(action)
    policy = build_standard_corrective_action_execution_plan_policy()
    if policy_values:
        policy = policy.build(**policy_values)
    return CorrectiveActionExecutionPlanRequest.build(decision_result, policy)


@pytest.mark.parametrize(
    ("action", "plan_type", "mode", "capability"),
    (
        (
            CorrectiveAction.CONTINUE_WORKFLOW,
            CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION,
            CorrectiveActionExecutionMode.NON_EXECUTABLE,
            CorrectiveActionExecutionCapability.NONE,
        ),
        (
            CorrectiveAction.REQUEST_REVISION,
            CorrectiveActionExecutionPlanType.REVISE_DRAFT,
            CorrectiveActionExecutionMode.HUMAN_GATED,
            CorrectiveActionExecutionCapability.DRAFT_REVISION,
        ),
        (
            CorrectiveAction.REQUEST_REGENERATION,
            CorrectiveActionExecutionPlanType.REGENERATE_DRAFT,
            CorrectiveActionExecutionMode.HUMAN_GATED,
            CorrectiveActionExecutionCapability.DRAFT_REGENERATION,
        ),
        (
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveActionExecutionPlanType.CREATE_MANUAL_REVIEW_REQUEST,
            CorrectiveActionExecutionMode.HUMAN_GATED,
            CorrectiveActionExecutionCapability.MANUAL_REVIEW_ROUTING,
        ),
        (
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionExecutionPlanType.BLOCK_AUTOMATIC_CONTINUATION,
            CorrectiveActionExecutionMode.NON_EXECUTABLE,
            CorrectiveActionExecutionCapability.WORKFLOW_CONTINUATION_BLOCK,
        ),
        (
            CorrectiveAction.NO_ACTION,
            CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION,
            CorrectiveActionExecutionMode.NON_EXECUTABLE,
            CorrectiveActionExecutionCapability.NONE,
        ),
    ),
)
def test_authoritative_mapping_matrix(action, plan_type, mode, capability) -> None:
    request = _planning_request(action)
    result = CorrectiveActionExecutionPlanService().plan(request)
    plan = result.plan
    assert result.operational_outcome is CorrectiveActionExecutionPlanOutcome.COMPLETED
    assert plan.plan_type is plan_type
    assert plan.execution_mode is mode
    assert plan.required_capability is capability
    assert plan.source_action is action
    assert plan.source_reason is _REASONS[action]
    assert plan.decision_result is request.decision_result
    assert result.plan is plan
    assert plan.automatic_execution_allowed is (
        mode is CorrectiveActionExecutionMode.AUTOMATIC
    )
    assert plan.human_authorization_required is (
        mode is CorrectiveActionExecutionMode.HUMAN_GATED
    )
    assert plan.plan_fingerprint.startswith("sha256:")


@pytest.mark.parametrize(
    ("action", "policy_values", "expected_mode"),
    (
        (
            CorrectiveAction.REQUEST_REVISION,
            {"revision_requires_human_authorization": False},
            CorrectiveActionExecutionMode.AUTOMATIC,
        ),
        (
            CorrectiveAction.REQUEST_REVISION,
            {"revision_requires_human_authorization": True},
            CorrectiveActionExecutionMode.HUMAN_GATED,
        ),
        (
            CorrectiveAction.REQUEST_REGENERATION,
            {"regeneration_automatic_allowed": True},
            CorrectiveActionExecutionMode.AUTOMATIC,
        ),
        (
            CorrectiveAction.REQUEST_REGENERATION,
            {"regeneration_automatic_allowed": False},
            CorrectiveActionExecutionMode.HUMAN_GATED,
        ),
        (
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            {"manual_review_requires_human_authorization": False},
            CorrectiveActionExecutionMode.AUTOMATIC,
        ),
        (
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            {"manual_review_requires_human_authorization": True},
            CorrectiveActionExecutionMode.HUMAN_GATED,
        ),
    ),
)
def test_policy_controls_only_execution_mode(
    action, policy_values, expected_mode
) -> None:
    result = CorrectiveActionExecutionPlanService().plan(
        _planning_request(action, **policy_values)
    )
    assert result.plan.execution_mode is expected_mode
    assert result.plan.source_action is action


@pytest.mark.parametrize(
    "policy_values",
    (
        {"halt_is_non_executable": False},
        {"unify_continue_and_no_action_plan_type": False},
    ),
)
def test_semantic_policy_conflicts_fail_without_fallback_plan(policy_values) -> None:
    result = CorrectiveActionExecutionPlanService().plan(
        _planning_request(CorrectiveAction.HALT_WORKFLOW, **policy_values)
    )
    assert result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.FAILED_POLICY_VALIDATION
    )
    assert result.plan is None
    assert result.diagnostic.code.value == "semantic_policy_conflict"


def test_precondition_matrix_is_typed_and_action_specific() -> None:
    revision = (
        CorrectiveActionExecutionPlanService()
        .plan(_planning_request(CorrectiveAction.REQUEST_REVISION))
        .plan.preconditions
    )
    regeneration = (
        CorrectiveActionExecutionPlanService()
        .plan(_planning_request(CorrectiveAction.REQUEST_REGENERATION))
        .plan.preconditions
    )
    manual = (
        CorrectiveActionExecutionPlanService()
        .plan(_planning_request(CorrectiveAction.REQUEST_MANUAL_REVIEW))
        .plan.preconditions
    )
    assert revision.requires_original_draft
    assert regeneration.requires_generation_context
    assert manual.requires_manual_review_destination
    assert all(
        item.requires_executor_capability for item in (revision, regeneration, manual)
    )
