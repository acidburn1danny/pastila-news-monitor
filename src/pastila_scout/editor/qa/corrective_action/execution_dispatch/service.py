"""Public validation and lifecycle boundary for execution dispatch."""

from .bindings import CorrectiveActionExecutorBindings, validate_executor_bindings
from .dispatcher import (
    CorrectiveActionExecutionDispatcher,
    DispatchRuntimeResult,
    _diagnostic,
    _dispatch_result,
)
from .enums import (
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionDispatchOutcome,
    CorrectiveActionExecutionDispatchStatus,
)
from .models import (
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchResult,
)
from .state import (
    CorrectiveActionExecutionDispatchPhase,
    CorrectiveActionExecutionDispatchState,
    transition_dispatch_state,
)
from .validation import validate_execution_dispatch_request


class CorrectiveActionExecutionDispatchService:
    """Own public validation/lifecycle and delegate semantics once."""

    def __init__(
        self,
        bindings: CorrectiveActionExecutorBindings,
        dispatcher: CorrectiveActionExecutionDispatcher | None = None,
    ) -> None:
        validate_executor_bindings(bindings)
        self._bindings = bindings
        self._dispatcher = dispatcher or CorrectiveActionExecutionDispatcher(bindings)

    def dispatch_runtime(
        self, request: CorrectiveActionExecutionDispatchRequest
    ) -> DispatchRuntimeResult:
        """Validate once, initialize lifecycle, and invoke the dispatcher once."""

        validate_execution_dispatch_request(request)
        state = CorrectiveActionExecutionDispatchState.prepared(
            request.request_fingerprint
        )
        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.VALIDATING
        )
        validate_executor_bindings(self._bindings)
        state = transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.EVALUATING_ELIGIBILITY
        )
        try:
            return self._dispatcher.dispatch(request, state)
        except Exception:  # noqa: BLE001 - sanitize the public dispatch boundary
            state = transition_dispatch_state(
                state, CorrectiveActionExecutionDispatchPhase.FAILED
            )
            result = _dispatch_result(
                request,
                CorrectiveActionExecutionDispatchOutcome.FAILED_INTERNAL,
                CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
                diagnostic=_diagnostic(
                    CorrectiveActionExecutionDispatchDiagnosticCode.DISPATCH_INTERNAL_FAILURE,
                    "Dispatch failed internally.",
                ),
            )
            return DispatchRuntimeResult(result, state, None, None)

    def dispatch(
        self, request: CorrectiveActionExecutionDispatchRequest
    ) -> CorrectiveActionExecutionDispatchResult:
        """Return the authoritative immutable dispatch result."""

        return self.dispatch_runtime(request).result


def build_standard_corrective_action_execution_dispatch_service(
    bindings: CorrectiveActionExecutorBindings,
) -> CorrectiveActionExecutionDispatchService:
    """Build the standard dispatcher explicitly, without discovery or globals."""

    return CorrectiveActionExecutionDispatchService(bindings)
