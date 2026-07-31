"""Authoritative pure M6C.6C Part 2 preparation orchestration."""

from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutorRequest,
    validate_executor_request,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.integration.models import ControlledGenerationInvocation
from pastila_scout.editor.qa.models import fingerprint

from .descriptor import build_draft_regeneration_executor_descriptor
from .enums import (
    DraftRegenerationDiagnosticCategory,
    DraftRegenerationDiagnosticCode,
    DraftRegenerationPreconditionStatus,
    DraftRegenerationPreparationOutcome,
    DraftRegenerationPreparationPhase,
    DraftRegenerationPreparationStatus,
)
from .factory import (
    DraftRegenerationInputResolver,
    construct_draft_regeneration_request,
)
from .generation_boundary import (
    ControlledGenerationRequest,
    ControlledGenerationRequestProjector,
)
from .models import DraftRegenerationDiagnostic, DraftRegenerationRequest
from .policy import DraftRegenerationPolicy
from .preconditions import (
    DraftRegenerationPreconditionEvaluation,
    DraftRegenerationPreconditionEvaluator,
)
from .state import DraftRegenerationPreparationState
from .validation import (
    validate_draft_regeneration_policy,
    validate_draft_regeneration_request,
)

PREPARATION_RESULT_VERSION = "1"


class DraftRegenerationPreparationResult(FrozenModel):
    result_version: str = PREPARATION_RESULT_VERSION
    executor_request: CorrectiveActionExecutorRequest
    operational_outcome: DraftRegenerationPreparationOutcome
    status: DraftRegenerationPreparationStatus
    regeneration_request: DraftRegenerationRequest | None
    precondition_evaluation: DraftRegenerationPreconditionEvaluation | None
    controlled_generation_request: ControlledGenerationRequest | None
    diagnostic: DraftRegenerationDiagnostic | None
    terminal_state: DraftRegenerationPreparationState
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("result_version", PREPARATION_RESULT_VERSION)
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        prepared = self.status is DraftRegenerationPreparationStatus.PREPARED
        if prepared != (
            self.operational_outcome is DraftRegenerationPreparationOutcome.COMPLETED
        ):
            raise ValueError("preparation outcome and status are inconsistent")
        if prepared:
            if (
                None
                in (
                    self.regeneration_request,
                    self.precondition_evaluation,
                    self.controlled_generation_request,
                )
                or self.diagnostic is not None
            ):
                raise ValueError("prepared result shape is inconsistent")
            if (
                self.terminal_state.phase
                is not DraftRegenerationPreparationPhase.PREPARED
            ):
                raise ValueError("prepared result requires terminal PREPARED state")
            if self.precondition_evaluation.request is not self.regeneration_request:
                raise ValueError("preparation does not preserve request identity")
        elif (
            self.diagnostic is None
            or self.terminal_state.phase is not DraftRegenerationPreparationPhase.FAILED
        ):
            raise ValueError("failed result shape is inconsistent")
        if self.result_fingerprint != fingerprint(
            _result_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("preparation-result fingerprint is inconsistent")
        return self


class DraftRegenerationRequestFactory:
    """Prepare a Controlled Generation request exactly once without invoking it."""

    def __init__(
        self,
        input_resolver: DraftRegenerationInputResolver,
        *,
        projector=None,
        precondition_evaluator=None
    ):
        self._resolver = input_resolver
        self._projector = projector or ControlledGenerationRequestProjector()
        self._evaluator = (
            precondition_evaluator or DraftRegenerationPreconditionEvaluator()
        )

    def prepare(
        self,
        executor_request: CorrectiveActionExecutorRequest,
        policy: DraftRegenerationPolicy,
    ) -> DraftRegenerationPreparationResult:
        state = DraftRegenerationPreparationState.initial(
            executor_request.request_fingerprint
        )
        state = state.transition(
            DraftRegenerationPreparationPhase.VALIDATING_EXECUTOR_REQUEST
        )
        try:
            failure = _validate_authority(executor_request)
            if failure:
                return _failed(executor_request, failure[0], failure[1], state)
            try:
                validate_draft_regeneration_policy(policy)
            except (TypeError, ValueError):
                return _failed(
                    executor_request,
                    DraftRegenerationPreparationOutcome.FAILED_POLICY_VALIDATION,
                    DraftRegenerationDiagnosticCode.INVALID_REGENERATION_POLICY,
                    state,
                )
            state = state.transition(DraftRegenerationPreparationPhase.RESOLVING_INPUT)
            try:
                resolved = self._resolver.resolve(executor_request)
            except (TypeError, ValueError):
                return _failed(
                    executor_request,
                    DraftRegenerationPreparationOutcome.FAILED_INPUT_RESOLUTION,
                    DraftRegenerationDiagnosticCode.REGENERATION_INPUT_RESOLUTION_FAILED,
                    state,
                )
            state = state.transition(
                DraftRegenerationPreparationPhase.BUILDING_REGENERATION_REQUEST,
                regeneration_input_fingerprint=resolved.input_fingerprint,
            )
            try:
                request = construct_draft_regeneration_request(
                    executor_request, policy, resolved
                )
                validate_draft_regeneration_request(request)
            except (TypeError, ValueError):
                return _failed(
                    executor_request,
                    DraftRegenerationPreparationOutcome.FAILED_INTEGRITY,
                    DraftRegenerationDiagnosticCode.INVALID_REGENERATION_REQUEST,
                    state,
                )
            state = state.transition(
                DraftRegenerationPreparationPhase.PROJECTING_GENERATION_REQUEST,
                regeneration_request_fingerprint=request.request_fingerprint,
            )
            try:
                generation_request = self._projector.project(request)
            except (TypeError, ValueError):
                return _failed(
                    executor_request,
                    DraftRegenerationPreparationOutcome.FAILED_CONTROLLED_GENERATION_REQUEST,
                    DraftRegenerationDiagnosticCode.CONTROLLED_GENERATION_REQUEST_PROJECTION_FAILED,
                    state,
                    request=request,
                )
            state = state.transition(
                DraftRegenerationPreparationPhase.EVALUATING_PRECONDITIONS,
                controlled_generation_request_fingerprint=generation_request.invocation_fingerprint,
            )
            evaluation = self._evaluator.evaluate(request, generation_request)
            if (
                evaluation.overall_status
                is not DraftRegenerationPreconditionStatus.SATISFIED
            ):
                return _failed(
                    executor_request,
                    DraftRegenerationPreparationOutcome.FAILED_PRECONDITION,
                    DraftRegenerationDiagnosticCode.PRECONDITION_NOT_SATISFIED,
                    state,
                    request=request,
                    evaluation=evaluation,
                )
            state = state.transition(
                DraftRegenerationPreparationPhase.PREPARED,
                precondition_evaluation_fingerprint=evaluation.evaluation_fingerprint,
                preparation_outcome=DraftRegenerationPreparationOutcome.COMPLETED,
            )
            return DraftRegenerationPreparationResult.build(
                executor_request=executor_request,
                operational_outcome=DraftRegenerationPreparationOutcome.COMPLETED,
                status=DraftRegenerationPreparationStatus.PREPARED,
                regeneration_request=request,
                precondition_evaluation=evaluation,
                controlled_generation_request=generation_request,
                diagnostic=None,
                terminal_state=state,
            )
        except Exception:  # noqa: BLE001 - public boundary must sanitize unknown faults
            return _failed(
                executor_request,
                DraftRegenerationPreparationOutcome.FAILED_INTERNAL,
                DraftRegenerationDiagnosticCode.REGENERATION_INTERNAL_FAILURE,
                state,
            )


def _validate_authority(request):
    try:
        validate_executor_request(request)
    except (TypeError, ValueError):
        return (
            DraftRegenerationPreparationOutcome.FAILED_INVALID_EXECUTOR_REQUEST,
            DraftRegenerationDiagnosticCode.INVALID_EXECUTOR_REQUEST,
        )
    plan = request.plan
    if plan.plan_type is not CorrectiveActionExecutionPlanType.REGENERATE_DRAFT:
        return (
            DraftRegenerationPreparationOutcome.FAILED_PLAN_MISMATCH,
            DraftRegenerationDiagnosticCode.PLAN_TYPE_NOT_REGENERATE_DRAFT,
        )
    if (
        plan.required_capability
        is not CorrectiveActionExecutionCapability.DRAFT_REGENERATION
    ):
        return (
            DraftRegenerationPreparationOutcome.FAILED_CAPABILITY_MISMATCH,
            DraftRegenerationDiagnosticCode.CAPABILITY_NOT_DRAFT_REGENERATION,
        )
    if request.executor_descriptor != build_draft_regeneration_executor_descriptor():
        return (
            DraftRegenerationPreparationOutcome.FAILED_INVALID_EXECUTOR_REQUEST,
            DraftRegenerationDiagnosticCode.INVALID_EXECUTOR_REQUEST,
        )
    if plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE:
        return (
            DraftRegenerationPreparationOutcome.FAILED_EXECUTION_MODE,
            DraftRegenerationDiagnosticCode.EXECUTION_MODE_NOT_SUPPORTED,
        )
    auth = request.execution_context.authorization_state
    if (
        plan.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
        and auth is not CorrectiveActionAuthorizationState.GRANTED
    ):
        return DraftRegenerationPreparationOutcome.FAILED_AUTHORIZATION, (
            DraftRegenerationDiagnosticCode.AUTHORIZATION_DENIED
            if auth is CorrectiveActionAuthorizationState.DENIED
            else DraftRegenerationDiagnosticCode.AUTHORIZATION_REQUIRED
        )
    return None


def _failed(executor_request, outcome, code, state, *, request=None, evaluation=None):
    diagnostic = DraftRegenerationDiagnostic.build(
        code=code,
        category=_category(code),
        safe_message="Regeneration preparation could not be completed.",
    )
    state = state.transition(
        DraftRegenerationPreparationPhase.FAILED,
        preparation_outcome=outcome,
        diagnostic_code=code.value,
        precondition_evaluation_fingerprint=(
            evaluation.evaluation_fingerprint if evaluation else None
        ),
    )
    return DraftRegenerationPreparationResult.build(
        executor_request=executor_request,
        operational_outcome=outcome,
        status=DraftRegenerationPreparationStatus.FAILED,
        regeneration_request=request,
        precondition_evaluation=evaluation,
        controlled_generation_request=None,
        diagnostic=diagnostic,
        terminal_state=state,
    )


def _category(code):
    if code in {
        DraftRegenerationDiagnosticCode.AUTHORIZATION_DENIED,
        DraftRegenerationDiagnosticCode.AUTHORIZATION_REQUIRED,
    }:
        return DraftRegenerationDiagnosticCategory.AUTHORIZATION
    if code in {
        DraftRegenerationDiagnosticCode.PLAN_TYPE_NOT_REGENERATE_DRAFT,
        DraftRegenerationDiagnosticCode.CAPABILITY_NOT_DRAFT_REGENERATION,
    }:
        return DraftRegenerationDiagnosticCategory.PLAN
    if code in {DraftRegenerationDiagnosticCode.REGENERATION_INPUT_RESOLUTION_FAILED}:
        return DraftRegenerationDiagnosticCategory.INPUT
    if code is DraftRegenerationDiagnosticCode.PRECONDITION_NOT_SATISFIED:
        return DraftRegenerationDiagnosticCategory.PRECONDITION
    return DraftRegenerationDiagnosticCategory.VALIDATION


def _result_identity(values):
    def field(obj, name):
        if isinstance(obj, dict) and name == "invocation_fingerprint":
            return ControlledGenerationInvocation.model_validate(
                obj
            ).invocation_fingerprint
        return obj.get(name) if isinstance(obj, dict) else getattr(obj, name)

    return {
        "result_version": values["result_version"],
        "executor_request_fingerprint": field(
            values["executor_request"], "request_fingerprint"
        ),
        "operational_outcome": values["operational_outcome"],
        "status": values["status"],
        "regeneration_request_fingerprint": (
            field(values["regeneration_request"], "request_fingerprint")
            if values.get("regeneration_request")
            else None
        ),
        "controlled_generation_request_fingerprint": (
            field(values["controlled_generation_request"], "invocation_fingerprint")
            if values.get("controlled_generation_request")
            else None
        ),
        "precondition_evaluation_fingerprint": (
            field(values["precondition_evaluation"], "evaluation_fingerprint")
            if values.get("precondition_evaluation")
            else None
        ),
        "diagnostic_code": (
            field(values["diagnostic"], "code") if values.get("diagnostic") else None
        ),
        "terminal_state_fingerprint": field(
            values["terminal_state"], "state_fingerprint"
        ),
    }
