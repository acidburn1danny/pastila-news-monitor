"""Single authoritative M6C.6A action-to-plan evaluator."""

from pastila_scout.editor.qa.corrective_action.models import CorrectiveAction

from .enums import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanType,
)
from .models import (
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanRequest,
    _canonical_preconditions,
)


class SemanticPolicyConflictError(ValueError):
    """Raised when policy attempts to contradict fixed planning semantics."""


def validate_policy_semantics(request: CorrectiveActionExecutionPlanRequest) -> None:
    """Reject policy choices that would alter the authoritative fixed mapping."""

    policy = request.planning_policy
    if not policy.halt_is_non_executable:
        raise SemanticPolicyConflictError("halt must remain non-executable")
    if not policy.unify_continue_and_no_action_plan_type:
        raise SemanticPolicyConflictError(
            "continue and no-action must retain the fixed shared plan type"
        )


class CorrectiveActionExecutionPlanEvaluator:
    """Map a validated authoritative action to exactly one immutable plan."""

    def evaluate(
        self, request: CorrectiveActionExecutionPlanRequest
    ) -> CorrectiveActionExecutionPlan:
        """Evaluate one request without dispatching or executing its plan."""

        decision = request.decision_result.decision
        if decision is None:
            raise ValueError("validated request has no authoritative decision")
        plan_type = _plan_type(decision.action)
        execution_mode = _execution_mode(decision.action, request)
        capability = _required_capability(plan_type)
        preconditions = _canonical_preconditions(plan_type, execution_mode)
        return CorrectiveActionExecutionPlan.build(
            plan_type=plan_type,
            execution_mode=execution_mode,
            required_capability=capability,
            source_action=decision.action,
            source_reason=decision.reason,
            preconditions=preconditions,
            decision_result=request.decision_result,
            policy_fingerprint=request.planning_policy.policy_fingerprint,
            request_fingerprint=request.request_fingerprint,
        )


def _plan_type(action: CorrectiveAction) -> CorrectiveActionExecutionPlanType:
    mapping = {
        CorrectiveAction.CONTINUE_WORKFLOW: (
            CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION
        ),
        CorrectiveAction.REQUEST_REVISION: (
            CorrectiveActionExecutionPlanType.REVISE_DRAFT
        ),
        CorrectiveAction.REQUEST_REGENERATION: (
            CorrectiveActionExecutionPlanType.REGENERATE_DRAFT
        ),
        CorrectiveAction.REQUEST_MANUAL_REVIEW: (
            CorrectiveActionExecutionPlanType.CREATE_MANUAL_REVIEW_REQUEST
        ),
        CorrectiveAction.HALT_WORKFLOW: (
            CorrectiveActionExecutionPlanType.BLOCK_AUTOMATIC_CONTINUATION
        ),
        CorrectiveAction.NO_ACTION: (
            CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION
        ),
    }
    try:
        return mapping[action]
    except KeyError as exc:
        raise ValueError("unsupported corrective action") from exc


def _execution_mode(
    action: CorrectiveAction, request: CorrectiveActionExecutionPlanRequest
) -> CorrectiveActionExecutionMode:
    policy = request.planning_policy
    if action in {
        CorrectiveAction.CONTINUE_WORKFLOW,
        CorrectiveAction.NO_ACTION,
        CorrectiveAction.HALT_WORKFLOW,
    }:
        return CorrectiveActionExecutionMode.NON_EXECUTABLE
    if action is CorrectiveAction.REQUEST_REVISION:
        human_gated = policy.revision_requires_human_authorization
    elif action is CorrectiveAction.REQUEST_REGENERATION:
        human_gated = not policy.regeneration_automatic_allowed
    else:
        human_gated = policy.manual_review_requires_human_authorization
    return (
        CorrectiveActionExecutionMode.HUMAN_GATED
        if human_gated
        else CorrectiveActionExecutionMode.AUTOMATIC
    )


def _required_capability(
    plan_type: CorrectiveActionExecutionPlanType,
) -> CorrectiveActionExecutionCapability:
    return {
        CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION: (
            CorrectiveActionExecutionCapability.NONE
        ),
        CorrectiveActionExecutionPlanType.REVISE_DRAFT: (
            CorrectiveActionExecutionCapability.DRAFT_REVISION
        ),
        CorrectiveActionExecutionPlanType.REGENERATE_DRAFT: (
            CorrectiveActionExecutionCapability.DRAFT_REGENERATION
        ),
        CorrectiveActionExecutionPlanType.CREATE_MANUAL_REVIEW_REQUEST: (
            CorrectiveActionExecutionCapability.MANUAL_REVIEW_ROUTING
        ),
        CorrectiveActionExecutionPlanType.BLOCK_AUTOMATIC_CONTINUATION: (
            CorrectiveActionExecutionCapability.WORKFLOW_CONTINUATION_BLOCK
        ),
    }[plan_type]
