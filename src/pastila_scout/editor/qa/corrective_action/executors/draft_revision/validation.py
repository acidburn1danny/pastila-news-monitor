"""Pure fail-closed validation for M6C.6D Part 1 contracts."""

from pydantic import ValidationError

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    validate_executor_descriptor,
    validate_executor_request,
)

from .descriptor import build_draft_revision_executor_descriptor
from .models import (
    DraftRevisionDiagnostic,
    DraftRevisionInstructions,
    DraftRevisionOutputReference,
    DraftRevisionRequest,
    DraftRevisionResult,
    DraftRevisionScope,
    DraftRevisionTarget,
)
from .policy import DraftRevisionPolicy


def validate_draft_revision_policy(value: DraftRevisionPolicy) -> None:
    _revalidate(DraftRevisionPolicy, value)


def validate_draft_revision_target(value: DraftRevisionTarget) -> None:
    _revalidate(DraftRevisionTarget, value)


def validate_draft_revision_scope(value: DraftRevisionScope) -> None:
    _revalidate(DraftRevisionScope, value)
    for target in value.targets:
        validate_draft_revision_target(target)


def validate_draft_revision_instructions(value: DraftRevisionInstructions) -> None:
    _revalidate(DraftRevisionInstructions, value)


def validate_draft_revision_request(value: DraftRevisionRequest) -> None:
    _require_type(DraftRevisionRequest, value)
    value.invariants()
    validate_executor_request(value.executor_request)
    validate_draft_revision_policy(value.policy)
    validate_draft_revision_scope(value.scope)
    validate_draft_revision_instructions(value.instructions)
    _revalidate(EpisodeDraft, value.source_draft)


def validate_draft_revision_diagnostic(value: DraftRevisionDiagnostic) -> None:
    _revalidate(DraftRevisionDiagnostic, value)


def validate_draft_revision_output_reference(
    value: DraftRevisionOutputReference,
) -> None:
    _revalidate(DraftRevisionOutputReference, value)


def validate_draft_revision_result(value: DraftRevisionResult) -> None:
    _require_type(DraftRevisionResult, value)
    value.invariants()
    validate_draft_revision_request(value.revision_request)
    if value.diagnostic:
        validate_draft_revision_diagnostic(value.diagnostic)
    if value.output_reference:
        validate_draft_revision_output_reference(value.output_reference)
    if value.revised_draft:
        _revalidate(EpisodeDraft, value.revised_draft)


def validate_draft_revision_executor_descriptor() -> None:
    descriptor = build_draft_revision_executor_descriptor()
    validate_executor_descriptor(descriptor)


def _revalidate(model_type, value) -> None:
    _require_type(model_type, value)
    try:
        model_type.model_validate(value.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(f"{model_type.__name__} integrity validation failed") from exc


def _require_type(model_type, value) -> None:
    if not isinstance(value, model_type):
        raise TypeError(f"invalid {model_type.__name__}")
