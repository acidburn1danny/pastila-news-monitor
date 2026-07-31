"""Pure fail-closed validation for M6C.6C Part 1 contracts."""

from pydantic import ValidationError

from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    GenerationPolicy,
)
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    validate_execution_context,
    validate_executor_descriptor,
    validate_executor_request,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.integration.models import ControlledGenerationInvocation

from .descriptor import build_draft_regeneration_executor_descriptor
from .models import (
    DraftRegenerationDiagnostic,
    DraftRegenerationInput,
    DraftRegenerationOutputReference,
    DraftRegenerationPrecondition,
    DraftRegenerationRequest,
    DraftRegenerationResult,
    map_regeneration_outcome,
)
from .policy import DraftRegenerationPolicy


def validate_draft_regeneration_policy(policy: DraftRegenerationPolicy) -> None:
    _require_type(DraftRegenerationPolicy, policy)
    policy.invariants()


def validate_draft_regeneration_input(value: DraftRegenerationInput) -> None:
    _require_type(DraftRegenerationInput, value)
    value.invariants()
    _revalidate(ControlledGenerationInvocation, value.generation_invocation)
    _revalidate(GenerationPolicy, value.generation_policy)
    if value.source_draft is not None:
        _revalidate(EpisodeDraft, value.source_draft)


def validate_draft_regeneration_request(value: DraftRegenerationRequest) -> None:
    _require_type(DraftRegenerationRequest, value)
    value.invariants()
    validate_executor_request(value.executor_request)
    validate_draft_regeneration_policy(value.policy)
    validate_draft_regeneration_input(value.regeneration_input)
    executor_request = value.executor_request
    plan = executor_request.plan
    descriptor = executor_request.executor_descriptor
    canonical = build_draft_regeneration_executor_descriptor()
    if plan.plan_type is not CorrectiveActionExecutionPlanType.REGENERATE_DRAFT:
        raise ValueError("draft regeneration requires REGENERATE_DRAFT")
    if (
        plan.required_capability
        is not CorrectiveActionExecutionCapability.DRAFT_REGENERATION
    ):
        raise ValueError("draft regeneration requires DRAFT_REGENERATION")
    if descriptor != canonical:
        raise ValueError("executor request does not use the regeneration descriptor")
    validate_executor_descriptor(descriptor)
    validate_execution_context(executor_request.execution_context)
    if plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE:
        raise ValueError("draft regeneration cannot be non-executable")
    if (
        plan.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
        and executor_request.execution_context.authorization_state
        is not CorrectiveActionAuthorizationState.GRANTED
    ):
        raise ValueError("human-gated regeneration requires authorization")
    if not plan.preconditions.requires_generation_context:
        raise ValueError("regeneration plan lacks generation-context precondition")


def validate_draft_regeneration_precondition(
    value: DraftRegenerationPrecondition,
) -> None:
    _require_type(DraftRegenerationPrecondition, value)
    value.invariants()


def validate_draft_regeneration_diagnostic(
    value: DraftRegenerationDiagnostic,
) -> None:
    _require_type(DraftRegenerationDiagnostic, value)
    value.invariants()


def validate_draft_regeneration_output_reference(
    value: DraftRegenerationOutputReference,
) -> None:
    _require_type(DraftRegenerationOutputReference, value)
    value.invariants()


def validate_draft_regeneration_result(value: DraftRegenerationResult) -> None:
    _require_type(DraftRegenerationResult, value)
    value.invariants()
    validate_draft_regeneration_request(value.request)
    if value.diagnostic is not None:
        validate_draft_regeneration_diagnostic(value.diagnostic)
    if value.output_reference is not None:
        validate_draft_regeneration_output_reference(value.output_reference)
    if value.generation_result is not None:
        _require_type(ControlledGenerationResult, value.generation_result)
        _revalidate(EpisodeDraft, value.generation_result.draft)
    map_regeneration_outcome(value.operational_outcome)


def validate_draft_regeneration_executor_descriptor() -> None:
    """Validate the canonical descriptor using the frozen M6C.6B validator."""

    descriptor = build_draft_regeneration_executor_descriptor()
    validate_executor_descriptor(descriptor)
    if descriptor != build_draft_regeneration_executor_descriptor():
        raise ValueError("draft-regeneration descriptor is nondeterministic")


def validate_regeneration_outcome_mapping() -> None:
    """Prove every supported regeneration outcome has one explicit mapping."""

    from .enums import DraftRegenerationOutcome

    if len(
        tuple(map_regeneration_outcome(item) for item in DraftRegenerationOutcome)
    ) != len(DraftRegenerationOutcome):
        raise ValueError("draft-regeneration outcome mapping is incomplete")


def _revalidate(model_type, value) -> None:
    _require_type(model_type, value)
    try:
        model_type.model_validate(value.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(f"{model_type.__name__} integrity validation failed") from exc


def _require_type(model_type, value) -> None:
    if not isinstance(value, model_type):
        raise TypeError(f"invalid {model_type.__name__}")
