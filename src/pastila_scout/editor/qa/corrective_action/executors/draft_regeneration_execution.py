"""Provider-neutral production draft-regeneration executor."""

from enum import StrEnum

from pydantic import model_validator

from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    FrozenModel,
)
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
    CorrectiveActionOutputReference,
    validate_executor_request,
)
from pastila_scout.editor.qa.models import fingerprint

from .draft_regeneration.descriptor import build_draft_regeneration_executor_descriptor
from .draft_regeneration.enums import (
    DraftRegenerationOutcome,
    DraftRegenerationPreparationStatus,
    DraftRegenerationStatus,
)
from .draft_regeneration.generation_boundary import ControlledGenerationGateway
from .draft_regeneration.models import (
    DraftRegenerationOutputReference,
    DraftRegenerationResult,
    map_regeneration_outcome,
)
from .draft_regeneration.policy import DraftRegenerationPolicy
from .draft_regeneration.preparation import DraftRegenerationRequestFactory
from .draft_regeneration.validation import validate_draft_regeneration_result


class DraftRegenerationRuntimePhase(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    PREPARING = "preparing"
    GENERATING = "generating"
    VALIDATING_RESULT = "validating_result"
    WRAPPING = "wrapping"
    COMPLETED = "completed"
    FAILED = "failed"


class DraftRegenerationRuntimeState(FrozenModel):
    phase: DraftRegenerationRuntimePhase
    revision: int
    executor_request_fingerprint: str
    event_codes: tuple[str, ...]
    state_fingerprint: str

    @classmethod
    def initial(cls, request: CorrectiveActionExecutorRequest):
        values = {
            "phase": DraftRegenerationRuntimePhase.RECEIVED,
            "revision": 0,
            "executor_request_fingerprint": request.request_fingerprint,
            "event_codes": ("runtime_received",),
        }
        return cls(**values, state_fingerprint=fingerprint(values))

    def transition(self, phase: DraftRegenerationRuntimePhase):
        order = (
            DraftRegenerationRuntimePhase.RECEIVED,
            DraftRegenerationRuntimePhase.VALIDATING,
            DraftRegenerationRuntimePhase.PREPARING,
            DraftRegenerationRuntimePhase.GENERATING,
            DraftRegenerationRuntimePhase.VALIDATING_RESULT,
            DraftRegenerationRuntimePhase.WRAPPING,
            DraftRegenerationRuntimePhase.COMPLETED,
        )
        valid = phase is DraftRegenerationRuntimePhase.FAILED or (
            self.phase in order
            and order.index(self.phase) + 1 < len(order)
            and phase is order[order.index(self.phase) + 1]
        )
        if (
            self.phase
            in {
                DraftRegenerationRuntimePhase.COMPLETED,
                DraftRegenerationRuntimePhase.FAILED,
            }
            or not valid
        ):
            raise ValueError("invalid draft-regeneration runtime transition")
        values = {
            "phase": phase,
            "revision": self.revision + 1,
            "executor_request_fingerprint": self.executor_request_fingerprint,
            "event_codes": self.event_codes + (f"runtime_{phase.value}",),
        }
        return type(self)(**values, state_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"state_fingerprint"}, mode="python")
        )
        if (
            self.state_fingerprint != expected
            or self.revision != len(self.event_codes) - 1
        ):
            raise ValueError("runtime state identity is inconsistent")
        return self


class ControlledGenerationResultValidator:
    """Validate the existing generation result and fresh-draft invariant."""

    def validate(
        self, result: ControlledGenerationResult, source_draft: EpisodeDraft | None
    ) -> None:
        if not isinstance(result, ControlledGenerationResult):
            raise TypeError("invalid Controlled Generation result")
        ControlledGenerationResult.model_validate(result.model_dump(mode="python"))
        EpisodeDraft.model_validate(result.draft.model_dump(mode="python"))
        if source_draft is not None and result.draft is source_draft:
            raise ValueError("Controlled Generation reused source-draft identity")


class DraftRegenerationResultFactory:
    """Construct capability results and their content-free output references."""

    def success(self, request, generation_result):
        draft = generation_result.draft
        reference = DraftRegenerationOutputReference.build(
            regeneration_request_fingerprint=request.request_fingerprint,
            regenerated_draft_fingerprint=fingerprint(draft),
            generation_result_fingerprint=fingerprint(generation_result),
        )
        result = DraftRegenerationResult.build(
            request=request,
            operational_outcome=DraftRegenerationOutcome.COMPLETED,
            status=DraftRegenerationStatus.COMPLETED,
            generation_result=generation_result,
            regenerated_draft=draft,
            output_reference=reference,
            diagnostic=None,
        )
        validate_draft_regeneration_result(result)
        return result


class DraftRegenerationExecutor:
    """Execute exactly one prepared regeneration request with no retry."""

    def __init__(
        self,
        request_factory: DraftRegenerationRequestFactory,
        generation_gateway: ControlledGenerationGateway,
        generation_validator: ControlledGenerationResultValidator,
        result_factory: DraftRegenerationResultFactory,
        policy: DraftRegenerationPolicy,
    ):
        self._request_factory = request_factory
        self._gateway = generation_gateway
        self._validator = generation_validator
        self._result_factory = result_factory
        self._policy = policy

    @property
    def descriptor(self):
        return build_draft_regeneration_executor_descriptor()

    def execute(
        self, request: CorrectiveActionExecutorRequest
    ) -> CorrectiveActionExecutorResult:
        state = DraftRegenerationRuntimeState.initial(request)
        try:
            state = state.transition(DraftRegenerationRuntimePhase.VALIDATING)
            validate_executor_request(request)
            state = state.transition(DraftRegenerationRuntimePhase.PREPARING)
            preparation = self._request_factory.prepare(request, self._policy)
            if preparation.status is not DraftRegenerationPreparationStatus.PREPARED:
                return _executor_failure(
                    request, CorrectiveActionExecutorOutcome.FAILED_PRECONDITION
                )
            generation_request = preparation.controlled_generation_request
            state = state.transition(DraftRegenerationRuntimePhase.GENERATING)
            generation_result = self._gateway.generate(generation_request)
            state = state.transition(DraftRegenerationRuntimePhase.VALIDATING_RESULT)
            source = preparation.regeneration_request.regeneration_input.source_draft
            self._validator.validate(generation_result, source)
            regeneration_result = self._result_factory.success(
                preparation.regeneration_request, generation_result
            )
            state = state.transition(DraftRegenerationRuntimePhase.WRAPPING)
            outcome, status = map_regeneration_outcome(
                regeneration_result.operational_outcome
            )
            generic_reference = CorrectiveActionOutputReference.build(
                output_type="episode-draft",
                capability=request.plan.required_capability,
                output_fingerprint=regeneration_result.output_reference.output_reference_fingerprint,
                capability_result_fingerprint=regeneration_result.result_fingerprint,
            )
            result = CorrectiveActionExecutorResult.build(
                executor_descriptor=request.executor_descriptor,
                request=request,
                operational_outcome=outcome,
                execution_status=status,
                output_reference=generic_reference,
                diagnostic=None,
            )
            state.transition(DraftRegenerationRuntimePhase.COMPLETED)
            return result
        except Exception:  # noqa: BLE001 - sanitize the production executor boundary
            return _executor_failure(
                request, CorrectiveActionExecutorOutcome.FAILED_INTERNAL
            )


def _executor_failure(request, outcome):
    diagnostic = CorrectiveActionExecutionDispatchDiagnostic.build(
        code=CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
        category=CorrectiveActionExecutionDispatchDiagnosticCategory.EXECUTOR,
        safe_message="Draft regeneration execution failed.",
        fingerprint_references=(("executor_request", request.request_fingerprint),),
    )
    return CorrectiveActionExecutorResult.build(
        executor_descriptor=request.executor_descriptor,
        request=request,
        operational_outcome=outcome,
        execution_status=CorrectiveActionExecutionStatus.FAILED,
        output_reference=None,
        diagnostic=diagnostic,
    )
