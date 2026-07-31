"""The single authoritative generic execution dispatcher."""

from dataclasses import dataclass

from .bindings import CorrectiveActionExecutorBindings
from .eligibility import (
    DispatchEligibilityEvaluator,
    DispatchEligibilityResult,
    DispatchEligibilityStatus,
)
from .enums import (
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionDispatchOutcome,
    CorrectiveActionExecutionDispatchStatus,
    CorrectiveActionExecutorOutcome,
)
from .models import (
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchResult,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
)
from .reporting import build_execution_dispatch_report
from .resolution import (
    CapabilityResolutionResult,
    CapabilityResolutionStatus,
    CapabilityResolver,
)
from .state import (
    CorrectiveActionExecutionDispatchPhase,
    CorrectiveActionExecutionDispatchState,
    transition_dispatch_state,
)
from .validation import validate_executor_request, validate_executor_result


@dataclass(frozen=True, slots=True)
class DispatchRuntimeResult:
    """Private orchestration result retained by workflow composition."""

    result: CorrectiveActionExecutionDispatchResult
    state: CorrectiveActionExecutionDispatchState
    eligibility: DispatchEligibilityResult | None
    resolution: CapabilityResolutionResult | None


class CorrectiveActionExecutionDispatcher:
    """Evaluate, resolve, and invoke at most one generic executor exactly once."""

    def __init__(
        self,
        bindings: CorrectiveActionExecutorBindings,
        eligibility_evaluator: DispatchEligibilityEvaluator | None = None,
        capability_resolver: CapabilityResolver | None = None,
    ) -> None:
        self._bindings = bindings
        self._eligibility = eligibility_evaluator or DispatchEligibilityEvaluator()
        self._resolver = capability_resolver or CapabilityResolver()

    def dispatch(
        self,
        request: CorrectiveActionExecutionDispatchRequest,
        state: CorrectiveActionExecutionDispatchState,
    ) -> DispatchRuntimeResult:
        """Run the authoritative orchestration from eligibility onward."""

        eligibility = self._eligibility.evaluate(
            request.planning_result, request.policy, request.execution_context
        )
        if eligibility.status is not DispatchEligibilityStatus.ELIGIBLE:
            return self._ineligible(request, state, eligibility)

        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.RESOLVING
        )
        resolution = self._resolver.resolve(
            request.planning_result, self._bindings.registry
        )
        if resolution.status is not CapabilityResolutionStatus.EXACT_MATCH:
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            code = (
                CorrectiveActionExecutionDispatchDiagnosticCode.AMBIGUOUS_EXECUTOR_MATCH
                if resolution.status is CapabilityResolutionStatus.AMBIGUOUS_MATCH
                else CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_NOT_FOUND
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_CAPABILITY_RESOLUTION,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                diagnostic=_diagnostic(code, "Executor resolution failed."),
            )
            return DispatchRuntimeResult(result, state, eligibility, resolution)

        descriptor = resolution.descriptor
        binding = self._bindings.binding_for(descriptor)
        if binding is None:
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_EXECUTOR_CONTRACT,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                descriptor=descriptor,
                diagnostic=_diagnostic(
                    CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_DESCRIPTOR_INVALID,
                    "Executor binding validation failed.",
                ),
            )
            return DispatchRuntimeResult(result, state, eligibility, resolution)

        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.BUILDING_EXECUTOR_REQUEST
        )
        try:
            executor_request = CorrectiveActionExecutorRequest.build(
                planning_result=request.planning_result,
                plan=request.planning_result.plan,
                executor_descriptor=descriptor,
                execution_context=request.execution_context,
            )
            validate_executor_request(executor_request)
        except (TypeError, ValueError):
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_EXECUTOR_CONTRACT,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                descriptor=descriptor,
                diagnostic=_diagnostic(
                    CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_REQUEST_INVALID,
                    "Executor request validation failed.",
                ),
            )
            return DispatchRuntimeResult(result, state, eligibility, resolution)

        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.INVOKING_EXECUTOR
        )
        try:
            executor_result = binding.executor.execute(executor_request)
        except Exception:  # noqa: BLE001 - sanitize the sole invocation boundary
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_EXECUTOR_CONTRACT,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                descriptor=descriptor,
                executor_request=executor_request,
                diagnostic=_diagnostic(
                    CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
                    "Executor invocation failed.",
                ),
            )
            return DispatchRuntimeResult(result, state, eligibility, resolution)

        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.VALIDATING_EXECUTOR_RESULT
        )
        try:
            validate_executor_result(executor_result)
            if executor_result.request is not executor_request:
                raise ValueError("executor result request identity mismatch")
            if executor_result.executor_descriptor is not descriptor:
                raise ValueError("executor result descriptor identity mismatch")
        except (TypeError, ValueError):
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_EXECUTOR_CONTRACT,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                descriptor=descriptor,
                executor_request=executor_request,
                diagnostic=_diagnostic(
                    CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_RESULT_INVALID,
                    "Executor result validation failed.",
                ),
            )
            return DispatchRuntimeResult(result, state, eligibility, resolution)

        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.DISPATCHED
        )
        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.FINALIZED
        )
        status = (
            CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED
            if executor_result.operational_outcome
            is CorrectiveActionExecutorOutcome.COMPLETED
            else CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED
        )
        result = _dispatch_result(
            request,
            CorrectiveActionExecutionDispatchOutcome.COMPLETED,
            status,
            descriptor=descriptor,
            executor_request=executor_request,
            executor_result=executor_result,
        )
        return DispatchRuntimeResult(result, state, eligibility, resolution)

    def _ineligible(self, request, state, eligibility):
        if eligibility.status is DispatchEligibilityStatus.NOT_EXECUTABLE:
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FINALIZED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.COMPLETED,
                CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
            )
        elif eligibility.status is DispatchEligibilityStatus.AUTHORIZATION_REQUIRED:
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FINALIZED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.COMPLETED,
                CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION,
                diagnostic=eligibility.diagnostic,
            )
        else:
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            outcome = (
                CorrectiveActionExecutionDispatchOutcome.FAILED_INTEGRITY_VALIDATION
                if eligibility.status is DispatchEligibilityStatus.INTEGRITY_FAILURE
                else CorrectiveActionExecutionDispatchOutcome.FAILED_NOT_DISPATCHABLE
            )
            result = _dispatch_result(
                request,
                outcome,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                diagnostic=eligibility.diagnostic,
            )
        return DispatchRuntimeResult(result, state, eligibility, None)


def _diagnostic(code, message):
    return CorrectiveActionExecutionDispatchDiagnostic.build(
        code=code,
        category=(
            CorrectiveActionExecutionDispatchDiagnosticCategory.EXECUTOR
            if "executor" in code.value
            else CorrectiveActionExecutionDispatchDiagnosticCategory.RESOLUTION
        ),
        safe_message=message,
    )


def _dispatch_result(
    request,
    outcome,
    status,
    *,
    descriptor: CorrectiveActionExecutorDescriptor | None = None,
    executor_request: CorrectiveActionExecutorRequest | None = None,
    executor_result: CorrectiveActionExecutorResult | None = None,
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic | None = None,
):
    report = build_execution_dispatch_report(
        request=request,
        operational_outcome=outcome,
        dispatch_status=status,
        executor_descriptor=descriptor,
        executor_request=executor_request,
        executor_result=executor_result,
        diagnostic=diagnostic,
    )
    return CorrectiveActionExecutionDispatchResult.build(
        request=request,
        operational_outcome=outcome,
        dispatch_status=status,
        executor_descriptor=descriptor,
        executor_request=executor_request,
        executor_result=executor_result,
        diagnostic=diagnostic,
        report=report,
    )
