"""Authoritative M6C.6A execution-planning service."""

from pastila_scout.editor.qa.corrective_action.models import (
    CONTRACT_VERSION as DECISION_CONTRACT_VERSION,
)
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionOutcome,
)

from .enums import (
    CorrectiveActionExecutionPlanDiagnosticCode,
    CorrectiveActionExecutionPlanningLifecycle,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanStage,
)
from .evaluation import (
    CorrectiveActionExecutionPlanEvaluator,
    SemanticPolicyConflictError,
    validate_policy_semantics,
)
from .models import (
    CONTRACT_VERSION,
    POLICY_VERSION,
    CorrectiveActionExecutionPlanDiagnostic,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanResult,
)
from .reporting import build_execution_plan_report
from .state import CorrectiveActionExecutionPlanningState, transition_planning_state
from .validation import (
    validate_decision_result,
    validate_execution_plan,
    validate_execution_plan_policy,
    validate_execution_plan_request,
)


class CorrectiveActionExecutionPlanService:
    """Validate and plan once without invoking any action executor."""

    def __init__(
        self, evaluator: CorrectiveActionExecutionPlanEvaluator | None = None
    ) -> None:
        self._evaluator = evaluator or CorrectiveActionExecutionPlanEvaluator()

    def plan(self, request: object) -> CorrectiveActionExecutionPlanResult:
        """Return one immutable plan or a deterministic operational failure."""

        state = _prepare_state(request)
        state = transition_planning_state(
            state, CorrectiveActionExecutionPlanningLifecycle.VALIDATING
        )
        failure = _validate_request_for_service(request)
        if failure is not None:
            outcome, code, stage, message = failure
            return _failure_result(state, request, outcome, code, stage, message)

        try:
            validate_policy_semantics(request)
        except SemanticPolicyConflictError:
            return _failure_result(
                state,
                request,
                CorrectiveActionExecutionPlanOutcome.FAILED_POLICY_VALIDATION,
                CorrectiveActionExecutionPlanDiagnosticCode.SEMANTIC_POLICY_CONFLICT,
                CorrectiveActionExecutionPlanStage.POLICY_VALIDATION,
                "Planning policy conflicts with fixed action semantics.",
            )

        state = transition_planning_state(
            state, CorrectiveActionExecutionPlanningLifecycle.PLANNING
        )
        try:
            plan = self._evaluator.evaluate(request)
        except Exception:  # noqa: BLE001 - sanitize at the public service boundary
            return _failure_result(
                state,
                request,
                CorrectiveActionExecutionPlanOutcome.FAILED_INTERNAL,
                CorrectiveActionExecutionPlanDiagnosticCode.INTERNAL_PLANNING_FAILURE,
                CorrectiveActionExecutionPlanStage.PLAN_VALIDATION,
                "Execution planning failed internally.",
            )
        try:
            validate_execution_plan(plan, request)
        except (TypeError, ValueError):
            return _failure_result(
                state,
                request,
                CorrectiveActionExecutionPlanOutcome.FAILED_INTEGRITY_VALIDATION,
                CorrectiveActionExecutionPlanDiagnosticCode.PLAN_FINGERPRINT_MISMATCH,
                CorrectiveActionExecutionPlanStage.PLAN_VALIDATION,
                "Execution-plan integrity validation failed.",
            )

        state = transition_planning_state(
            state,
            CorrectiveActionExecutionPlanningLifecycle.PLANNED,
            plan_fingerprint=plan.plan_fingerprint,
        )
        state = transition_planning_state(
            state,
            CorrectiveActionExecutionPlanningLifecycle.FINALIZED,
            operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
        )
        report = build_execution_plan_report(
            operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
            plan=plan,
            diagnostic=None,
            request_fingerprint=request.request_fingerprint,
            policy_fingerprint=request.planning_policy.policy_fingerprint,
            input_complete=True,
            decision_result_fingerprint=request.decision_result.result_fingerprint,
            final_lifecycle_phase=state.phase.value,
            lifecycle_revision=state.revision,
            state_fingerprint=state.state_fingerprint,
        )
        return CorrectiveActionExecutionPlanResult.build(
            operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
            plan=plan,
            diagnostic=None,
            report=report,
        )


def plan_corrective_action_execution(
    request: CorrectiveActionExecutionPlanRequest,
) -> CorrectiveActionExecutionPlanResult:
    """Delegate to the one authoritative planning service."""

    return CorrectiveActionExecutionPlanService().plan(request)


def _prepare_state(request: object) -> CorrectiveActionExecutionPlanningState:
    if isinstance(request, CorrectiveActionExecutionPlanRequest):
        return CorrectiveActionExecutionPlanningState.prepare(
            request_fingerprint=request.request_fingerprint,
            policy_fingerprint=request.planning_policy.policy_fingerprint,
            decision_result_fingerprint=request.decision_result.result_fingerprint,
        )
    return CorrectiveActionExecutionPlanningState.prepare(
        request_fingerprint=None,
        policy_fingerprint=None,
        decision_result_fingerprint=None,
    )


def _validate_request_for_service(request: object):
    if not isinstance(request, CorrectiveActionExecutionPlanRequest):
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT,
            CorrectiveActionExecutionPlanDiagnosticCode.INVALID_REQUEST,
            CorrectiveActionExecutionPlanStage.REQUEST_VALIDATION,
            "Execution-planning request is invalid.",
        )
    if request.contract_version != CONTRACT_VERSION:
        return _unsupported_request_failure()
    if request.planning_policy.policy_version != POLICY_VERSION:
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_UNSUPPORTED_CONTRACT,
            CorrectiveActionExecutionPlanDiagnosticCode.UNSUPPORTED_POLICY_VERSION,
            CorrectiveActionExecutionPlanStage.POLICY_VALIDATION,
            "Execution-planning policy version is unsupported.",
        )
    if request.decision_result.descriptor.contract_version != DECISION_CONTRACT_VERSION:
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_UNSUPPORTED_CONTRACT,
            CorrectiveActionExecutionPlanDiagnosticCode.UNSUPPORTED_DECISION_CONTRACT_VERSION,
            CorrectiveActionExecutionPlanStage.UPSTREAM_VALIDATION,
            "Corrective-action decision contract version is unsupported.",
        )
    try:
        validate_execution_plan_policy(request.planning_policy)
    except (TypeError, ValueError):
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_INTEGRITY_VALIDATION,
            CorrectiveActionExecutionPlanDiagnosticCode.POLICY_FINGERPRINT_MISMATCH,
            CorrectiveActionExecutionPlanStage.POLICY_VALIDATION,
            "Execution-planning policy integrity validation failed.",
        )
    try:
        validate_decision_result(request.decision_result)
    except (TypeError, ValueError):
        if (
            request.decision_result.operational_outcome
            is not CorrectiveActionDecisionOutcome.COMPLETED
        ):
            return (
                CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT,
                CorrectiveActionExecutionPlanDiagnosticCode.INVALID_DECISION_RESULT,
                CorrectiveActionExecutionPlanStage.UPSTREAM_VALIDATION,
                "Corrective-action decision did not complete.",
            )
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_INTEGRITY_VALIDATION,
            CorrectiveActionExecutionPlanDiagnosticCode.INVALID_DECISION_RESULT,
            CorrectiveActionExecutionPlanStage.UPSTREAM_VALIDATION,
            "Corrective-action decision result is invalid.",
        )
    try:
        validate_execution_plan_request(request)
    except (TypeError, ValueError):
        return (
            CorrectiveActionExecutionPlanOutcome.FAILED_INTEGRITY_VALIDATION,
            CorrectiveActionExecutionPlanDiagnosticCode.REQUEST_FINGERPRINT_MISMATCH,
            CorrectiveActionExecutionPlanStage.REQUEST_VALIDATION,
            "Execution-planning request integrity validation failed.",
        )
    return None


def _unsupported_request_failure():
    return (
        CorrectiveActionExecutionPlanOutcome.FAILED_UNSUPPORTED_CONTRACT,
        CorrectiveActionExecutionPlanDiagnosticCode.INVALID_REQUEST,
        CorrectiveActionExecutionPlanStage.REQUEST_VALIDATION,
        "Execution-planning request version is unsupported.",
    )


def _failure_result(
    state,
    request,
    outcome,
    code,
    stage,
    message,
) -> CorrectiveActionExecutionPlanResult:
    state = transition_planning_state(
        state,
        CorrectiveActionExecutionPlanningLifecycle.FAILED,
        operational_outcome=outcome,
        diagnostic_code=code,
    )
    diagnostic = CorrectiveActionExecutionPlanDiagnostic.build(
        code=code, safe_message=message, stage=stage
    )
    valid_request = isinstance(request, CorrectiveActionExecutionPlanRequest)
    report = build_execution_plan_report(
        operational_outcome=outcome,
        plan=None,
        diagnostic=diagnostic,
        request_fingerprint=(request.request_fingerprint if valid_request else None),
        policy_fingerprint=(
            request.planning_policy.policy_fingerprint if valid_request else None
        ),
        input_complete=False,
        decision_result_fingerprint=(
            request.decision_result.result_fingerprint if valid_request else None
        ),
        final_lifecycle_phase=state.phase.value,
        lifecycle_revision=state.revision,
        state_fingerprint=state.state_fingerprint,
    )
    return CorrectiveActionExecutionPlanResult.build(
        operational_outcome=outcome,
        plan=None,
        diagnostic=diagnostic,
        report=report,
    )
