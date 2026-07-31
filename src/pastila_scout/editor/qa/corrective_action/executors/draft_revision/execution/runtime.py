"""M6C.6D Part 3A production Draft Revision executor."""

# The executor is the approved outer capability exception boundary.
# ruff: noqa: BLE001

from typing import Protocol

from pastila_scout.editor.generation.revision import (
    ControlledRevisionInvocation,
    ControlledRevisionResult,
    RevisionResultStatus,
    revision_fingerprint,
    validate_controlled_revision_invocation,
    validate_controlled_revision_result,
)
from pastila_scout.editor.qa.models import canonical_json

from ..preparation_models import (
    DraftRevisionPreparationOutcome,
    DraftRevisionPreparationPhase,
    DraftRevisionPreparationResult,
    DraftRevisionPreparationStatus,
)
from .models import (
    DraftRevisionExecutionDiagnostic,
    DraftRevisionExecutionDiagnosticCode,
    DraftRevisionExecutionLifecycle,
    DraftRevisionExecutionOutcome,
    DraftRevisionExecutionPhase,
    DraftRevisionExecutionReport,
    DraftRevisionExecutionResult,
    DraftRevisionExecutionStatus,
)


class ControlledRevisionService(Protocol):
    def execute(
        self, invocation: ControlledRevisionInvocation
    ) -> ControlledRevisionResult: ...


class PreparationResultValidator(Protocol):
    def __call__(self, value: DraftRevisionPreparationResult) -> None: ...


class InvocationValidator(Protocol):
    def __call__(self, value: ControlledRevisionInvocation) -> None: ...


class ControlledResultValidator(Protocol):
    def __call__(
        self,
        value: ControlledRevisionResult,
        *,
        invocation: ControlledRevisionInvocation | None = None,
        gateway_result=None,
    ) -> None: ...


class ExecutionResultValidator(Protocol):
    def __call__(self, value: DraftRevisionExecutionResult) -> None: ...


class ControlledRevisionInvocationFactory:
    """Sole owner of invocation construction from the exact prepared request."""

    def create(
        self, preparation_result: DraftRevisionPreparationResult
    ) -> ControlledRevisionInvocation:
        return ControlledRevisionInvocation.build(
            request=preparation_result.generation_request
        )


class DraftRevisionExecutionLifecycleFactory:
    """Sole owner of deterministic executor terminal lifecycles."""

    def success(self) -> DraftRevisionExecutionLifecycle:
        return DraftRevisionExecutionLifecycle.build(
            tuple(DraftRevisionExecutionPhase)[:7]
        )

    def failure(self, reached: int) -> DraftRevisionExecutionLifecycle:
        normal = tuple(DraftRevisionExecutionPhase)[:7]
        return DraftRevisionExecutionLifecycle.build(
            (*normal[:reached], DraftRevisionExecutionPhase.FAILED)
        )


class DraftRevisionExecutionResultFactory:
    """Sole owner of executor success and sanitized failure mapping."""

    def __init__(self, lifecycle_factory: DraftRevisionExecutionLifecycleFactory):
        self.lifecycle_factory = lifecycle_factory

    def success(
        self,
        preparation: DraftRevisionPreparationResult,
        invocation: ControlledRevisionInvocation,
        controlled_result: ControlledRevisionResult,
    ) -> DraftRevisionExecutionResult:
        try:
            return DraftRevisionExecutionResult.build(
                status=DraftRevisionExecutionStatus.SUCCESS,
                outcome=DraftRevisionExecutionOutcome.COMPLETED,
                preparation_result=preparation,
                controlled_revision_invocation=invocation,
                controlled_revision_result=controlled_result,
                revised_draft=controlled_result.revised_draft,
                lifecycle=self.lifecycle_factory.success(),
                input_preparation_fingerprint=preparation.preparation_fingerprint,
            )
        except Exception:
            return self.failure(
                preparation_fingerprint=preparation.preparation_fingerprint,
                preparation=preparation,
                invocation=invocation,
                controlled_result=controlled_result,
                outcome=DraftRevisionExecutionOutcome.INTERNAL_FAILURE,
                code=DraftRevisionExecutionDiagnosticCode.INTERNAL_DRAFT_REVISION_EXECUTION_FAILURE,
                reached=5,
            )

    def failure(
        self,
        *,
        preparation_fingerprint: str,
        outcome: DraftRevisionExecutionOutcome,
        code: DraftRevisionExecutionDiagnosticCode,
        reached: int,
        preparation: DraftRevisionPreparationResult | None = None,
        invocation: ControlledRevisionInvocation | None = None,
        controlled_result: ControlledRevisionResult | None = None,
        nested_code: str | None = None,
    ) -> DraftRevisionExecutionResult:
        return DraftRevisionExecutionResult.build(
            status=DraftRevisionExecutionStatus.FAILED,
            outcome=outcome,
            preparation_result=preparation,
            controlled_revision_invocation=invocation,
            controlled_revision_result=controlled_result,
            revised_draft=None,
            diagnostic=DraftRevisionExecutionDiagnostic.build(
                code=code,
                safe_message="Draft revision execution failed.",
                controlled_revision_diagnostic_code=nested_code,
            ),
            lifecycle=self.lifecycle_factory.failure(reached),
            input_preparation_fingerprint=preparation_fingerprint,
        )


class DraftRevisionExecutor:
    """The only M6C.6D Part 3A production execution entry point."""

    def __init__(
        self,
        *,
        controlled_revision_service: ControlledRevisionService,
        preparation_result_validator: PreparationResultValidator,
        invocation_factory: ControlledRevisionInvocationFactory,
        invocation_validator: InvocationValidator,
        controlled_revision_result_validator: ControlledResultValidator,
        execution_result_factory: DraftRevisionExecutionResultFactory,
        execution_result_validator: ExecutionResultValidator,
    ):
        self.controlled_revision_service = controlled_revision_service
        self.preparation_result_validator = preparation_result_validator
        self.invocation_factory = invocation_factory
        self.invocation_validator = invocation_validator
        self.controlled_revision_result_validator = controlled_revision_result_validator
        self.execution_result_factory = execution_result_factory
        self.execution_result_validator = execution_result_validator

    def execute(
        self, preparation_result: DraftRevisionPreparationResult
    ) -> DraftRevisionExecutionResult:
        preparation_fp = getattr(
            preparation_result, "preparation_fingerprint", "sha256:" + "0" * 64
        )
        try:
            self.preparation_result_validator(preparation_result)
        except Exception:
            return self._failure(
                preparation_fingerprint=preparation_fp,
                outcome=DraftRevisionExecutionOutcome.INVALID_PREPARATION,
                code=DraftRevisionExecutionDiagnosticCode.INVALID_DRAFT_REVISION_PREPARATION,
                reached=1,
            )
        if (
            preparation_result.outcome is not DraftRevisionPreparationOutcome.PREPARED
            or preparation_result.status is not DraftRevisionPreparationStatus.PREPARED
            or preparation_result.lifecycle.phases[-1]
            is not DraftRevisionPreparationPhase.PREPARED
            or preparation_result.generation_request is None
        ):
            return self._failure(
                preparation_fingerprint=preparation_fp,
                outcome=DraftRevisionExecutionOutcome.PREPARATION_NOT_EXECUTABLE,
                code=DraftRevisionExecutionDiagnosticCode.DRAFT_REVISION_PREPARATION_NOT_EXECUTABLE,
                reached=1,
            )
        try:
            invocation = self.invocation_factory.create(preparation_result)
            self.invocation_validator(invocation)
        except Exception:
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                outcome=DraftRevisionExecutionOutcome.INVALID_INVOCATION,
                code=DraftRevisionExecutionDiagnosticCode.CONTROLLED_REVISION_INVOCATION_INVALID,
                reached=2,
            )
        try:
            controlled_result = self.controlled_revision_service.execute(invocation)
        except Exception:
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                invocation=invocation,
                outcome=DraftRevisionExecutionOutcome.CONTROLLED_REVISION_FAILED,
                code=DraftRevisionExecutionDiagnosticCode.CONTROLLED_REVISION_EXECUTION_FAILED,
                reached=4,
            )
        if not isinstance(controlled_result, ControlledRevisionResult):
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                invocation=invocation,
                outcome=DraftRevisionExecutionOutcome.INVALID_CONTROLLED_REVISION_RESULT,
                code=DraftRevisionExecutionDiagnosticCode.INVALID_CONTROLLED_REVISION_RESULT,
                reached=4,
            )
        try:
            self.controlled_revision_result_validator(
                controlled_result, invocation=invocation
            )
        except Exception as exc:
            lineage = "lineage" in str(exc).casefold()
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                invocation=invocation,
                outcome=(
                    DraftRevisionExecutionOutcome.LINEAGE_MISMATCH
                    if lineage
                    else DraftRevisionExecutionOutcome.INVALID_CONTROLLED_REVISION_RESULT
                ),
                code=(
                    DraftRevisionExecutionDiagnosticCode.DRAFT_REVISION_EXECUTION_LINEAGE_MISMATCH
                    if lineage
                    else DraftRevisionExecutionDiagnosticCode.INVALID_CONTROLLED_REVISION_RESULT
                ),
                reached=4,
            )
        if not self._lineage_valid(preparation_result, invocation, controlled_result):
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                invocation=invocation,
                controlled_result=controlled_result,
                outcome=DraftRevisionExecutionOutcome.LINEAGE_MISMATCH,
                code=DraftRevisionExecutionDiagnosticCode.DRAFT_REVISION_EXECUTION_LINEAGE_MISMATCH,
                reached=5,
            )
        if controlled_result.status is not RevisionResultStatus.SUCCESS:
            return self._failure(
                preparation_fingerprint=preparation_fp,
                preparation=preparation_result,
                invocation=invocation,
                controlled_result=controlled_result,
                outcome=DraftRevisionExecutionOutcome.CONTROLLED_REVISION_FAILED,
                code=DraftRevisionExecutionDiagnosticCode.CONTROLLED_REVISION_EXECUTION_FAILED,
                reached=5,
                nested_code=(
                    controlled_result.diagnostic.code.value
                    if controlled_result.diagnostic
                    else None
                ),
            )
        result = self.execution_result_factory.success(
            preparation_result, invocation, controlled_result
        )
        self.execution_result_validator(result)
        return result

    def _failure(self, **values):
        result = self.execution_result_factory.failure(**values)
        self.execution_result_validator(result)
        return result

    @staticmethod
    def _lineage_valid(preparation, invocation, result):
        request = preparation.generation_request
        return (
            invocation.request is request
            and result.revision_request_fingerprint
            == request.revision_request_fingerprint
            and result.invocation_fingerprint == invocation.invocation_fingerprint
            and result.source_draft_fingerprint
            == revision_fingerprint(request.source_draft)
            and result.preservation_fingerprint
            == request.preservation_requirements.preservation_fingerprint
            and result.output_contract_fingerprint
            == request.expected_output_contract.output_contract_fingerprint
            and request.planning_input_fingerprint
            == preparation.executor_request.planning_input.input_fingerprint
            and request.executor_request_fingerprint
            == preparation.executor_request.request_fingerprint
        )


def validate_draft_revision_execution_result(
    value: DraftRevisionExecutionResult,
) -> None:
    if not isinstance(value, DraftRevisionExecutionResult):
        raise TypeError("invalid draft-revision execution result")
    value.invariants()
    if value.controlled_revision_invocation:
        validate_controlled_revision_invocation(value.controlled_revision_invocation)
    if value.controlled_revision_result:
        validate_controlled_revision_result(
            value.controlled_revision_result,
            invocation=value.controlled_revision_invocation,
        )


def build_draft_revision_execution_report(
    result: DraftRevisionExecutionResult,
) -> DraftRevisionExecutionReport:
    preparation = result.preparation_result
    request = preparation.generation_request if preparation else None
    controlled = result.controlled_revision_result
    diagnostic = result.diagnostic
    return DraftRevisionExecutionReport.build(
        capability="draft_revision",
        action="request_revision",
        status=result.status,
        outcome=result.outcome,
        target_count=len(request.revision_targets) if request else 0,
        diagnostic_code=diagnostic.code if diagnostic else None,
        controlled_revision_diagnostic_code=(
            diagnostic.controlled_revision_diagnostic_code if diagnostic else None
        ),
        lifecycle=tuple(item.value for item in result.lifecycle.phases),
        executor_request_fingerprint=(
            preparation.executor_request.request_fingerprint if preparation else None
        ),
        planning_input_fingerprint=(
            preparation.executor_request.planning_input.input_fingerprint
            if preparation
            else None
        ),
        preparation_fingerprint=result.input_preparation_fingerprint,
        revision_request_fingerprint=(
            request.revision_request_fingerprint if request else None
        ),
        invocation_fingerprint=(
            result.controlled_revision_invocation.invocation_fingerprint
            if result.controlled_revision_invocation
            else None
        ),
        controlled_revision_result_fingerprint=(
            controlled.result_fingerprint if controlled else None
        ),
        source_draft_fingerprint=(
            controlled.source_draft_fingerprint if controlled else None
        ),
        preservation_fingerprint=(
            controlled.preservation_fingerprint if controlled else None
        ),
        output_contract_fingerprint=(
            controlled.output_contract_fingerprint if controlled else None
        ),
        execution_fingerprint=result.execution_fingerprint,
    )


def serialize_draft_revision_execution_report(
    report: DraftRevisionExecutionReport,
) -> str:
    return canonical_json(report)
