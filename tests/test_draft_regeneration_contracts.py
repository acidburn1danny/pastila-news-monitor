"""M6C.6C Part 1 immutable draft-regeneration contract tests."""

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_dispatch_contracts import (
    _context,
    _descriptor,
    _planning_result,
)
from test_editorial_review_integration import _generation_case

from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    GenerationPolicy,
    GenerationTrace,
)
from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRequest,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_regeneration import (
    DraftRegenerationArchitectureDescriptor,
    DraftRegenerationDiagnostic,
    DraftRegenerationDiagnosticCategory,
    DraftRegenerationDiagnosticCode,
    DraftRegenerationInput,
    DraftRegenerationOutcome,
    DraftRegenerationOutputReference,
    DraftRegenerationPolicy,
    DraftRegenerationPrecondition,
    DraftRegenerationPreconditionCode,
    DraftRegenerationRequest,
    DraftRegenerationResult,
    DraftRegenerationStatus,
    build_draft_regeneration_executor_descriptor,
    build_draft_regeneration_report,
    build_standard_draft_regeneration_policy,
    map_regeneration_outcome,
    render_draft_regeneration_report,
    serialize_draft_regeneration_report,
    validate_draft_regeneration_executor_descriptor,
    validate_draft_regeneration_input,
    validate_draft_regeneration_precondition,
    validate_draft_regeneration_report,
    validate_draft_regeneration_request,
    validate_draft_regeneration_result,
    validate_regeneration_outcome_mapping,
)
from pastila_scout.editor.qa.models import fingerprint


def _executor_request(action=CorrectiveAction.REQUEST_REGENERATION):
    planning = _planning_result(
        action,
        **(
            {"revision_requires_human_authorization": False}
            if action is CorrectiveAction.REQUEST_REVISION
            else {}
        ),
    )
    descriptor = (
        build_draft_regeneration_executor_descriptor()
        if action is CorrectiveAction.REQUEST_REGENERATION
        else _descriptor(planning.plan)
    )
    return CorrectiveActionExecutorRequest.build(
        planning_result=planning,
        plan=planning.plan,
        executor_descriptor=descriptor,
        execution_context=_context(
            CorrectiveActionAuthorizationState.GRANTED
            if action is CorrectiveAction.REQUEST_REGENERATION
            else CorrectiveActionAuthorizationState.NOT_REQUIRED
        ),
    )


def _input(source_draft=None):
    _, invocation = _generation_case()
    return DraftRegenerationInput.build(
        generation_invocation=invocation,
        generation_policy=GenerationPolicy(),
        source_draft=source_draft,
    )


def _request(source_draft=None):
    return DraftRegenerationRequest.build(
        executor_request=_executor_request(),
        policy=build_standard_draft_regeneration_policy(),
        regeneration_input=_input(source_draft),
    )


def _draft(label):
    assembled = f"Deschidere {label}.\n\nÎnchidere {label}."
    return EpisodeDraft(
        episode_id=f"episode-{label}",
        opening=f"Deschidere {label}.",
        stories=(),
        transitions=(),
        closing=f"Închidere {label}.",
        cta=None,
        assembled_text=assembled,
        teleprompter_text=assembled,
    )


def _success_result():
    source = _draft("sursă")
    generated = _draft("nouă")
    request = _request(source)
    generation = ControlledGenerationResult(
        draft=generated,
        trace=GenerationTrace(attempts=()),
        manifest="safe-manifest",
        final_state="safe-state",
    )
    reference = DraftRegenerationOutputReference.build(
        regeneration_request_fingerprint=request.request_fingerprint,
        regenerated_draft_fingerprint=fingerprint(generated),
        generation_result_fingerprint=fingerprint(generation),
    )
    return DraftRegenerationResult.build(
        request=request,
        operational_outcome=DraftRegenerationOutcome.COMPLETED,
        status=DraftRegenerationStatus.COMPLETED,
        generation_result=generation,
        regenerated_draft=generated,
        output_reference=reference,
        diagnostic=None,
    )


def _failure_result(outcome=DraftRegenerationOutcome.FAILED_PRECONDITION):
    request = _request()
    diagnostic = DraftRegenerationDiagnostic.build(
        code=DraftRegenerationDiagnosticCode.PRECONDITION_NOT_SATISFIED,
        category=DraftRegenerationDiagnosticCategory.PRECONDITION,
        safe_message="A regeneration precondition was not satisfied.",
    )
    return DraftRegenerationResult.build(
        request=request,
        operational_outcome=outcome,
        status=DraftRegenerationStatus.FAILED,
        generation_result=None,
        regenerated_draft=None,
        output_reference=None,
        diagnostic=diagnostic,
    )


def test_policy_and_architecture_are_immutable_and_deterministic() -> None:
    assert build_standard_draft_regeneration_policy() == DraftRegenerationPolicy.build()
    architecture = DraftRegenerationArchitectureDescriptor.build()
    assert not architecture.part_one_invokes_generation
    with pytest.raises(ValidationError):
        architecture.part_one_invokes_generation = True
    with pytest.raises(ValidationError):
        DraftRegenerationPolicy.build(require_fresh_generation=False)


def test_descriptor_is_exact_narrow_and_frozen_compatible() -> None:
    descriptor = build_draft_regeneration_executor_descriptor()
    assert descriptor.executor_id == "draft-regeneration.v1"
    assert descriptor.supported_capability.value == "draft_regeneration"
    assert tuple(item.value for item in descriptor.supported_plan_types) == (
        "regenerate_draft",
    )
    assert descriptor.supports_automatic_invocation
    assert descriptor.supports_human_gated_invocation
    validate_draft_regeneration_executor_descriptor()


def test_preconditions_are_typed_immutable_validation_observations() -> None:
    value = DraftRegenerationPrecondition.build(
        code=DraftRegenerationPreconditionCode.PLAN_LINEAGE_VALID,
        satisfied=True,
        source_fingerprint="sha256:" + "1" * 64,
    )
    validate_draft_regeneration_precondition(value)
    with pytest.raises(ValidationError):
        value.satisfied = False
    with pytest.raises(ValidationError, match="source fingerprint"):
        DraftRegenerationPrecondition.build(
            code=DraftRegenerationPreconditionCode.PLAN_LINEAGE_VALID,
            satisfied=False,
            source_fingerprint="bad",
        )


def test_input_reuses_controlled_generation_contracts_and_preserves_identity() -> None:
    source = _draft("sursă")
    value = _input(source)
    assert value.source_draft is source
    assert value.generation_invocation is _input().generation_invocation or (
        value.generation_invocation.invocation_fingerprint
        == _input().generation_invocation.invocation_fingerprint
    )
    assert isinstance(value.generation_policy, GenerationPolicy)
    validate_draft_regeneration_input(value)
    with pytest.raises(ValueError):
        validate_draft_regeneration_input(
            value.model_copy(update={"input_fingerprint": "sha256:bad"})
        )


def test_request_preserves_executor_planning_plan_and_descriptor_identity() -> None:
    executor_request = _executor_request()
    value = DraftRegenerationRequest.build(
        executor_request=executor_request,
        policy=build_standard_draft_regeneration_policy(),
        regeneration_input=_input(),
    )
    assert value.executor_request is executor_request
    assert value.executor_request.plan is executor_request.plan
    assert value.executor_request.planning_result is executor_request.planning_result
    assert (
        value.executor_request.executor_descriptor
        is executor_request.executor_descriptor
    )
    validate_draft_regeneration_request(value)


def test_request_rejects_revision_plan_and_fingerprint_tampering() -> None:
    with pytest.raises(ValidationError, match="REGENERATE_DRAFT"):
        DraftRegenerationRequest.build(
            executor_request=_executor_request(CorrectiveAction.REQUEST_REVISION),
            policy=build_standard_draft_regeneration_policy(),
            regeneration_input=_input(),
        )
    value = _request()
    with pytest.raises(ValueError):
        validate_draft_regeneration_request(
            value.model_copy(update={"request_fingerprint": "sha256:bad"})
        )


def test_success_preserves_fresh_draft_and_complete_output_lineage() -> None:
    result = _success_result()
    assert result.regenerated_draft is result.generation_result.draft
    assert (
        result.regenerated_draft is not result.request.regeneration_input.source_draft
    )
    assert (
        result.output_reference.regeneration_request_fingerprint
        == result.request.request_fingerprint
    )
    validate_draft_regeneration_result(result)


def test_success_rejects_source_identity_reuse_and_bad_output_reference() -> None:
    source = _draft("aceeași")
    request = _request(source)
    generation = ControlledGenerationResult(
        draft=source,
        trace=GenerationTrace(attempts=()),
        manifest="safe",
        final_state="safe",
    )
    reference = DraftRegenerationOutputReference.build(
        regeneration_request_fingerprint=request.request_fingerprint,
        regenerated_draft_fingerprint=fingerprint(source),
        generation_result_fingerprint=fingerprint(generation),
    )
    with pytest.raises(ValidationError, match="reuses"):
        DraftRegenerationResult.build(
            request=request,
            operational_outcome=DraftRegenerationOutcome.COMPLETED,
            status=DraftRegenerationStatus.COMPLETED,
            generation_result=generation,
            regenerated_draft=source,
            output_reference=reference,
            diagnostic=None,
        )
    good = _success_result()
    with pytest.raises(ValidationError, match="lineage"):
        DraftRegenerationResult.build(
            request=good.request,
            operational_outcome=good.operational_outcome,
            status=good.status,
            generation_result=good.generation_result,
            regenerated_draft=good.regenerated_draft,
            output_reference=DraftRegenerationOutputReference.build(
                regeneration_request_fingerprint=good.request.request_fingerprint,
                regenerated_draft_fingerprint="sha256:" + "0" * 64,
                generation_result_fingerprint=(
                    good.output_reference.generation_result_fingerprint
                ),
            ),
            diagnostic=None,
        )


def test_failure_shapes_and_outcome_mapping_are_complete() -> None:
    failure = _failure_result()
    assert failure.regenerated_draft is None and failure.output_reference is None
    validate_draft_regeneration_result(failure)
    validate_regeneration_outcome_mapping()
    assert map_regeneration_outcome(DraftRegenerationOutcome.COMPLETED) == (
        CorrectiveActionExecutorOutcome.COMPLETED,
        CorrectiveActionExecutionStatus.COMPLETED,
    )
    assert all(
        map_regeneration_outcome(item)[1] is CorrectiveActionExecutionStatus.FAILED
        for item in DraftRegenerationOutcome
        if item is not DraftRegenerationOutcome.COMPLETED
    )
    with pytest.raises(TypeError):
        map_regeneration_outcome("unknown")


def test_unknown_values_and_all_contract_fingerprints_fail_closed() -> None:
    result = _failure_result()
    for field in ("result_version", "operational_outcome", "status"):
        values = result.model_dump(mode="python")
        values[field] = "unknown"
        with pytest.raises(ValidationError):
            DraftRegenerationResult.model_validate(values)
    with pytest.raises(ValueError):
        validate_draft_regeneration_result(
            result.model_copy(update={"result_fingerprint": "sha256:bad"})
        )
    with pytest.raises(ValidationError, match="lineage fingerprint"):
        DraftRegenerationOutputReference.build(
            regeneration_request_fingerprint="bad",
            regenerated_draft_fingerprint="sha256:" + "1" * 64,
            generation_result_fingerprint="sha256:" + "2" * 64,
        )


def test_diagnostics_reports_and_serialization_are_content_safe() -> None:
    result = _success_result()
    report = build_draft_regeneration_report(result)
    validate_draft_regeneration_report(report, result)
    serialized = serialize_draft_regeneration_report(report)
    rendered = render_draft_regeneration_report(report)
    assert serialized == serialize_draft_regeneration_report(report)
    forbidden = ("deschidere", "închidere", "prompt", "provider", "manifest")
    assert all(item not in serialized.casefold() for item in forbidden)
    assert all(item not in rendered.casefold() for item in forbidden)
    with pytest.raises(ValidationError, match="unsafe"):
        DraftRegenerationDiagnostic.build(
            code=DraftRegenerationDiagnosticCode.REGENERATION_INTERNAL_FAILURE,
            category=DraftRegenerationDiagnosticCategory.INTERNAL,
            safe_message="API token C:\\private\\draft.txt",
        )
