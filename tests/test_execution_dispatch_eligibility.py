"""M6C.6B Part 2 authoritative dispatch eligibility tests."""

import pytest
from test_corrective_action_execution_dispatch_contracts import (
    _context,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionDispatchPolicy,
    DispatchEligibilityEvaluator,
    DispatchEligibilityStatus,
    build_dispatch_eligibility_report,
    build_standard_corrective_action_execution_dispatch_policy,
    render_dispatch_eligibility_report,
    serialize_dispatch_eligibility_report,
    validate_dispatch_eligibility_result,
)


def _evaluate(plan_result, authorization, policy=None):
    return DispatchEligibilityEvaluator().evaluate(
        plan_result,
        policy or build_standard_corrective_action_execution_dispatch_policy(),
        _context(authorization),
    )


def test_automatic_plan_is_eligible_without_authorization() -> None:
    plan_result = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    result = _evaluate(plan_result, CorrectiveActionAuthorizationState.NOT_REQUIRED)
    assert result.status is DispatchEligibilityStatus.ELIGIBLE
    assert result.plan_result is plan_result
    assert result.diagnostic is None
    validate_dispatch_eligibility_result(result)


def test_human_gated_plan_requires_then_accepts_authorization() -> None:
    plan_result = _planning_result(CorrectiveAction.REQUEST_REGENERATION)
    waiting = _evaluate(
        plan_result, CorrectiveActionAuthorizationState.REQUIRED_NOT_GRANTED
    )
    granted = _evaluate(plan_result, CorrectiveActionAuthorizationState.GRANTED)
    denied = _evaluate(plan_result, CorrectiveActionAuthorizationState.DENIED)
    assert waiting.status is DispatchEligibilityStatus.AUTHORIZATION_REQUIRED
    assert granted.status is DispatchEligibilityStatus.ELIGIBLE
    assert denied.status is DispatchEligibilityStatus.POLICY_BLOCKED


def test_non_executable_plan_is_not_dispatchable_but_remains_valid() -> None:
    result = _evaluate(
        _planning_result(CorrectiveAction.CONTINUE_WORKFLOW),
        CorrectiveActionAuthorizationState.NOT_REQUIRED,
    )
    assert result.status is DispatchEligibilityStatus.NOT_EXECUTABLE
    assert result.diagnostic.code.value == "plan_not_dispatchable"


def test_policy_can_block_without_reinterpreting_plan() -> None:
    plan_result = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    policy = CorrectiveActionExecutionDispatchPolicy.build(
        allow_automatic_dispatch=False
    )
    result = _evaluate(
        plan_result,
        CorrectiveActionAuthorizationState.NOT_REQUIRED,
        policy,
    )
    assert result.status is DispatchEligibilityStatus.POLICY_BLOCKED
    assert result.plan_result is plan_result
    assert result.required_capability is plan_result.plan.required_capability


def test_invalid_policy_context_and_fingerprints_fail_closed() -> None:
    plan_result = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    policy = build_standard_corrective_action_execution_dispatch_policy()
    bad_policy = policy.model_copy(update={"policy_fingerprint": "sha256:bad"})
    bad_context = _context().model_copy(update={"context_fingerprint": "sha256:bad"})
    bad_plan = plan_result.model_copy(update={"result_fingerprint": "sha256:bad"})
    evaluator = DispatchEligibilityEvaluator()
    assert (
        evaluator.evaluate(plan_result, bad_policy, _context()).status
        is DispatchEligibilityStatus.INTEGRITY_FAILURE
    )
    assert (
        evaluator.evaluate(plan_result, policy, bad_context).status
        is DispatchEligibilityStatus.INTEGRITY_FAILURE
    )
    assert (
        evaluator.evaluate(bad_plan, policy, _context()).status
        is DispatchEligibilityStatus.INTEGRITY_FAILURE
    )


def test_eligibility_is_deterministic_and_reports_are_safe() -> None:
    plan_result = _planning_result(CorrectiveAction.REQUEST_REGENERATION)
    first = _evaluate(plan_result, CorrectiveActionAuthorizationState.GRANTED)
    second = _evaluate(plan_result, CorrectiveActionAuthorizationState.GRANTED)
    assert first == second
    report = build_dispatch_eligibility_report(first)
    serialized = serialize_dispatch_eligibility_report(report)
    rendered = render_dispatch_eligibility_report(report)
    assert serialized == serialize_dispatch_eligibility_report(report)
    assert first.eligibility_fingerprint in serialized
    assert "provider" not in serialized and "finding" not in serialized
    assert "Eligibility: eligible" in rendered


def test_unknown_eligibility_status_is_rejected() -> None:
    result = _evaluate(
        _planning_result(CorrectiveAction.CONTINUE_WORKFLOW),
        CorrectiveActionAuthorizationState.NOT_REQUIRED,
    )
    values = result.model_dump()
    values["status"] = "maybe"
    with pytest.raises(ValueError):
        type(result).model_validate(values)
