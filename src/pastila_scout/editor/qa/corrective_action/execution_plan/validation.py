"""Pure fail-closed validators for M6C.6A public contracts."""

from pydantic import ValidationError

from pastila_scout.editor.qa.corrective_action.models import (
    CONTRACT_VERSION as DECISION_CONTRACT_VERSION,
)
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionOutcome,
    CorrectiveActionDecisionResult,
)

from .models import (
    CONTRACT_VERSION,
    POLICY_VERSION,
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanPolicy,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanResult,
)


def validate_execution_plan_policy(
    policy: CorrectiveActionExecutionPlanPolicy,
) -> None:
    """Validate supported policy identity without side effects."""

    if not isinstance(policy, CorrectiveActionExecutionPlanPolicy):
        raise TypeError("invalid execution-plan policy")
    if policy.policy_version != POLICY_VERSION:
        raise ValueError("unsupported execution-plan policy version")
    _revalidate(CorrectiveActionExecutionPlanPolicy, policy)


def validate_decision_result(result: CorrectiveActionDecisionResult) -> None:
    """Validate frozen upstream integrity, not editorial correctness."""

    if not isinstance(result, CorrectiveActionDecisionResult):
        raise TypeError("invalid corrective-action decision result")
    if result.descriptor.contract_version != DECISION_CONTRACT_VERSION:
        raise ValueError("unsupported corrective-action decision contract version")
    _revalidate(CorrectiveActionDecisionResult, result)
    if result.operational_outcome is not CorrectiveActionDecisionOutcome.COMPLETED:
        raise ValueError("corrective-action decision did not complete")
    if result.decision is None:
        raise ValueError("completed corrective-action result has no decision")


def validate_execution_plan_request(
    request: CorrectiveActionExecutionPlanRequest,
) -> None:
    """Validate request, policy, upstream result, and fingerprint lineage."""

    if not isinstance(request, CorrectiveActionExecutionPlanRequest):
        raise TypeError("invalid execution-plan request")
    if request.contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported execution-plan request version")
    _revalidate(CorrectiveActionExecutionPlanRequest, request)
    validate_execution_plan_policy(request.planning_policy)
    validate_decision_result(request.decision_result)


def validate_execution_plan(
    plan: CorrectiveActionExecutionPlan,
    request: CorrectiveActionExecutionPlanRequest | None = None,
) -> None:
    """Validate plan consistency and optional request lineage."""

    if not isinstance(plan, CorrectiveActionExecutionPlan):
        raise TypeError("invalid corrective-action execution plan")
    if plan.contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported execution-plan contract version")
    _revalidate(CorrectiveActionExecutionPlan, plan)
    validate_decision_result(plan.decision_result)
    if request is not None:
        validate_execution_plan_request(request)
        if plan.decision_result is not request.decision_result:
            raise ValueError("plan does not preserve request decision identity")
        if plan.request_fingerprint != request.request_fingerprint:
            raise ValueError("plan request fingerprint is inconsistent")
        if plan.policy_fingerprint != request.planning_policy.policy_fingerprint:
            raise ValueError("plan policy fingerprint is inconsistent")


def validate_execution_plan_result(
    result: CorrectiveActionExecutionPlanResult,
) -> None:
    """Validate operational/plan separation and all present contracts."""

    if not isinstance(result, CorrectiveActionExecutionPlanResult):
        raise TypeError("invalid execution-plan result")
    if result.contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported execution-plan result version")
    _revalidate(CorrectiveActionExecutionPlanResult, result)
    if result.plan is not None:
        validate_execution_plan(result.plan)


def _revalidate(model_type, value) -> None:
    try:
        model_type.model_validate(value.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(f"{model_type.__name__} integrity validation failed") from exc
