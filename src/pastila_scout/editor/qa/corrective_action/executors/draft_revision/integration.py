"""Authoritative Draft Revision integration into the v2 execution runtime."""

from typing import Protocol

from pastila_scout.editor.qa.corrective_action.execution_dispatch.input_transport import (
    CorrectiveActionExecutorRequestV2,
)
from pastila_scout.editor.qa.corrective_action.execution_dispatch.v2_runtime import (
    CorrectiveActionExecutionPhaseV2,
    CorrectiveActionExecutionResponse,
    CorrectiveActionExecutionResponseStatus,
)

from .execution import (
    DraftRevisionExecutionResult,
    DraftRevisionExecutionStatus,
    validate_draft_revision_execution_result,
)
from .preparation_models import (
    DraftRevisionPreparationOutcome,
    DraftRevisionPreparationResult,
)


class PreparationService(Protocol):
    def prepare(
        self, request: CorrectiveActionExecutorRequestV2
    ) -> DraftRevisionPreparationResult: ...


class RevisionExecutor(Protocol):
    def execute(
        self, preparation: DraftRevisionPreparationResult
    ) -> DraftRevisionExecutionResult: ...


class DraftRevisionCorrectiveActionExecutor:
    """Orchestrate the two frozen boundaries once and map their outcomes."""

    def __init__(
        self, preparation_service: PreparationService, executor: RevisionExecutor
    ):
        self.preparation_service = preparation_service
        self.executor = executor

    def execute(
        self, request: CorrectiveActionExecutorRequestV2
    ) -> CorrectiveActionExecutionResponse:
        base = (
            CorrectiveActionExecutionPhaseV2.CREATED,
            CorrectiveActionExecutionPhaseV2.REQUEST_VALIDATED,
            CorrectiveActionExecutionPhaseV2.CAPABILITY_RESOLVED,
            CorrectiveActionExecutionPhaseV2.PREPARING,
        )
        try:
            preparation = self.preparation_service.prepare(request)
        except Exception:  # noqa: BLE001 - sanitized integration boundary
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_PREPARATION_FAILED,
                "capability_preparation_failed",
                (*base, CorrectiveActionExecutionPhaseV2.FAILED),
            )
        if not isinstance(preparation, DraftRevisionPreparationResult):
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_PREPARATION_FAILED,
                "invalid_preparation_result",
                (*base, CorrectiveActionExecutionPhaseV2.FAILED),
            )
        try:
            preparation.invariants()
        except (TypeError, ValueError):
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_PREPARATION_FAILED,
                "invalid_preparation_result",
                (*base, CorrectiveActionExecutionPhaseV2.FAILED),
            )
        if preparation.executor_request is not request:
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_PREPARATION_FAILED,
                "preparation_request_identity_mismatch",
                (*base, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
            )
        if preparation.outcome is not DraftRevisionPreparationOutcome.PREPARED:
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_NOT_EXECUTABLE,
                "capability_not_executable",
                (*base, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
            )
        prepared = (
            *base,
            CorrectiveActionExecutionPhaseV2.PREPARED,
            CorrectiveActionExecutionPhaseV2.EXECUTING,
        )
        try:
            execution = self.executor.execute(preparation)
        except Exception:  # noqa: BLE001 - sanitized integration boundary
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_EXECUTION_FAILED,
                "capability_execution_failed",
                (*prepared, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
            )
        if not isinstance(execution, DraftRevisionExecutionResult):
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.INVALID_CAPABILITY_EXECUTION_RESULT,
                "invalid_capability_execution_result",
                (*prepared, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
            )
        try:
            validate_draft_revision_execution_result(execution)
            if execution.preparation_result is not preparation:
                raise ValueError("execution preparation identity mismatch")
        except (TypeError, ValueError):
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.INVALID_CAPABILITY_EXECUTION_RESULT,
                "invalid_capability_execution_result",
                (*prepared, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
            )
        lifecycle = (
            *prepared,
            CorrectiveActionExecutionPhaseV2.EXECUTED,
            CorrectiveActionExecutionPhaseV2.RESULT_VALIDATED,
        )
        if execution.status is not DraftRevisionExecutionStatus.SUCCESS:
            return self._failure(
                request,
                CorrectiveActionExecutionResponseStatus.CAPABILITY_EXECUTION_FAILED,
                "capability_execution_failed",
                (*lifecycle, CorrectiveActionExecutionPhaseV2.FAILED),
                preparation_fingerprint=preparation.preparation_fingerprint,
                execution_fingerprint=execution.execution_fingerprint,
                capability_result=execution,
            )
        return CorrectiveActionExecutionResponse.build(
            request=request,
            capability=request.planning_input.required_capability,
            action=request.planning_input.corrective_action,
            status=CorrectiveActionExecutionResponseStatus.SUCCESS,
            lifecycle=(*lifecycle, CorrectiveActionExecutionPhaseV2.COMPLETED),
            preparation_fingerprint=preparation.preparation_fingerprint,
            execution_fingerprint=execution.execution_fingerprint,
            capability_result=execution,
        )

    @staticmethod
    def _failure(request, status, code, lifecycle, **values):
        return CorrectiveActionExecutionResponse.build(
            request=request,
            capability=request.planning_input.required_capability,
            action=request.planning_input.corrective_action,
            status=status,
            lifecycle=lifecycle,
            diagnostic_code=code,
            **values,
        )
