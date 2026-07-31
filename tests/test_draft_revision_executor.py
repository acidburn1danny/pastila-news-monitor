"""M6C.6D Part 3A production Draft Revision executor tests."""

import inspect

from test_controlled_revision_runtime import GatewaySpy as RevisionGatewaySpy
from test_controlled_revision_runtime import _success as gateway_success
from test_draft_revision_preparation import _prepared

from pastila_scout.editor.generation.models import EpisodeDraft, derive_assembled_text
from pastila_scout.editor.generation.revision import (
    ControlledRevisionResult,
    RevisionResultStatus,
    compose_controlled_revision_execution_service,
    validate_controlled_revision_invocation,
    validate_controlled_revision_result,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    ControlledRevisionInvocationFactory,
    DraftRevisionExecutionDiagnosticCode,
    DraftRevisionExecutionLifecycleFactory,
    DraftRevisionExecutionOutcome,
    DraftRevisionExecutionPhase,
    DraftRevisionExecutionResultFactory,
    DraftRevisionExecutionStatus,
    DraftRevisionExecutor,
    build_draft_revision_execution_report,
    serialize_draft_revision_execution_report,
    validate_draft_revision_execution_result,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision.preparation import (
    validate_draft_revision_preparation_result,
)


class ControlledServiceSpy:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0
        self.last_invocation = None

    def execute(self, invocation):
        self.calls += 1
        self.last_invocation = invocation
        if self.error:
            raise self.error
        return self.result


class CallableSpy:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.wrapped(*args, **kwargs)


class FactorySpy:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.calls = 0

    def create(self, *args):
        self.calls += 1
        return self.wrapped.create(*args)


def _controlled_success(preparation):
    invocation = ControlledRevisionInvocationFactory().create(preparation)
    source = invocation.request.source_draft
    opening = "Deschidere revizuită."
    assembled = derive_assembled_text(
        opening=opening,
        stories=source.stories,
        transitions=source.transitions,
        closing=source.closing,
        cta=source.cta,
    )
    revised = EpisodeDraft(
        episode_id=source.episode_id,
        opening=opening,
        stories=source.stories,
        transitions=source.transitions,
        closing=source.closing,
        cta=source.cta,
        assembled_text=assembled,
        teleprompter_text=assembled,
    )
    gateway_result = gateway_success(invocation, revised)
    result = compose_controlled_revision_execution_service(
        RevisionGatewaySpy(gateway_result)
    ).execute(invocation)
    assert result.status is RevisionResultStatus.SUCCESS
    return result


def _executor(service, *, spies=False):
    lifecycle = DraftRevisionExecutionLifecycleFactory()
    result_factory = DraftRevisionExecutionResultFactory(lifecycle)
    preparation_validator = CallableSpy(validate_draft_revision_preparation_result)
    invocation_factory = FactorySpy(ControlledRevisionInvocationFactory())
    invocation_validator = CallableSpy(validate_controlled_revision_invocation)
    controlled_validator = CallableSpy(validate_controlled_revision_result)
    result_validator = CallableSpy(validate_draft_revision_execution_result)
    executor = DraftRevisionExecutor(
        controlled_revision_service=service,
        preparation_result_validator=preparation_validator,
        invocation_factory=invocation_factory,
        invocation_validator=invocation_validator,
        controlled_revision_result_validator=controlled_validator,
        execution_result_factory=result_factory,
        execution_result_validator=result_validator,
    )
    dependencies = (
        preparation_validator,
        invocation_factory,
        invocation_validator,
        controlled_validator,
        result_validator,
    )
    return (executor, dependencies) if spies else executor


def test_success_preserves_exact_objects_and_invokes_once():
    _, preparation = _prepared()
    controlled = _controlled_success(preparation)
    service = ControlledServiceSpy(controlled)
    executor, dependencies = _executor(service, spies=True)

    result = executor.execute(preparation)

    assert service.calls == 1
    assert result.status is DraftRevisionExecutionStatus.SUCCESS
    assert result.outcome is DraftRevisionExecutionOutcome.COMPLETED
    assert result.preparation_result is preparation
    assert result.controlled_revision_invocation is service.last_invocation
    assert service.last_invocation.request is preparation.generation_request
    assert result.controlled_revision_result is controlled
    assert result.revised_draft is controlled.revised_draft
    assert result.lifecycle.phases[-1] is DraftRevisionExecutionPhase.COMPLETED
    assert tuple(item.calls for item in dependencies) == (1, 1, 1, 1, 1)


def test_equivalent_execution_is_deterministic():
    _, preparation = _prepared()
    controlled = _controlled_success(preparation)
    first = _executor(ControlledServiceSpy(controlled)).execute(preparation)
    second = _executor(ControlledServiceSpy(controlled)).execute(preparation)

    assert first.execution_fingerprint == second.execution_fingerprint
    assert first.lifecycle == second.lifecycle
    first_report = build_draft_revision_execution_report(first)
    second_report = build_draft_revision_execution_report(second)
    assert first_report.report_fingerprint == second_report.report_fingerprint
    assert serialize_draft_revision_execution_report(
        first_report
    ) == serialize_draft_revision_execution_report(second_report)


def test_invalid_preparation_calls_controlled_revision_zero_times():
    _, preparation = _prepared()
    invalid = preparation.model_copy(
        update={"preparation_fingerprint": "sha256:" + "0" * 64}
    )
    service = ControlledServiceSpy()
    result = _executor(service).execute(invalid)

    assert service.calls == 0
    assert result.outcome is DraftRevisionExecutionOutcome.INVALID_PREPARATION
    assert (
        result.diagnostic.code
        is DraftRevisionExecutionDiagnosticCode.INVALID_DRAFT_REVISION_PREPARATION
    )
    assert result.preparation_result is None


def test_rejected_preparation_is_not_executable_and_calls_zero_times():
    request, _ = _prepared()
    rejected = request.model_copy(update={"request_fingerprint": "sha256:" + "0" * 64})
    from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
        compose_draft_revision_preparation_service,
    )

    preparation = compose_draft_revision_preparation_service(
        request.executor_descriptor
    ).prepare(rejected)
    service = ControlledServiceSpy()
    result = _executor(service).execute(preparation)

    assert service.calls == 0
    assert result.outcome is DraftRevisionExecutionOutcome.PREPARATION_NOT_EXECUTABLE
    assert (
        result.diagnostic.code
        is DraftRevisionExecutionDiagnosticCode.DRAFT_REVISION_PREPARATION_NOT_EXECUTABLE
    )


def test_service_exception_is_sanitized_and_not_retried():
    _, preparation = _prepared()
    sentinel = "OPENAI_API_KEY=secret C:\\private\\provider.py"
    service = ControlledServiceSpy(error=RuntimeError(sentinel))
    result = _executor(service).execute(preparation)
    report = serialize_draft_revision_execution_report(
        build_draft_revision_execution_report(result)
    )

    assert service.calls == 1
    assert result.outcome is DraftRevisionExecutionOutcome.CONTROLLED_REVISION_FAILED
    assert result.revised_draft is None
    assert sentinel not in repr(result)
    assert sentinel not in report


def test_wrong_or_malformed_controlled_result_fails_after_one_call():
    _, preparation = _prepared()
    for returned in (object(), "wrong-type"):
        service = ControlledServiceSpy(returned)
        result = _executor(service).execute(preparation)
        assert service.calls == 1
        assert (
            result.outcome
            is DraftRevisionExecutionOutcome.INVALID_CONTROLLED_REVISION_RESULT
        )
        assert (
            result.diagnostic.code
            is DraftRevisionExecutionDiagnosticCode.INVALID_CONTROLLED_REVISION_RESULT
        )

    controlled = _controlled_success(preparation).model_copy(
        update={"result_version": "unknown"}
    )
    service = ControlledServiceSpy(controlled)
    result = _executor(service).execute(preparation)
    assert service.calls == 1
    assert (
        result.outcome
        is DraftRevisionExecutionOutcome.INVALID_CONTROLLED_REVISION_RESULT
    )


def test_valid_but_mismatched_lineage_fails_after_one_call():
    _, preparation = _prepared()
    controlled = _controlled_success(preparation)
    data = controlled.model_dump(exclude={"result_fingerprint"}, mode="python")
    data["invocation_fingerprint"] = "sha256:" + "0" * 64
    mismatched = ControlledRevisionResult.build(**data)
    service = ControlledServiceSpy(mismatched)
    result = _executor(service).execute(preparation)

    assert service.calls == 1
    assert result.outcome is DraftRevisionExecutionOutcome.LINEAGE_MISMATCH
    assert result.revised_draft is None


def test_approved_controlled_failure_maps_without_retry_or_output():
    _, preparation = _prepared()
    invocation = ControlledRevisionInvocationFactory().create(preparation)
    controlled = compose_controlled_revision_execution_service(
        RevisionGatewaySpy(error=RuntimeError("provider detail"))
    ).execute(invocation)
    service = ControlledServiceSpy(controlled)
    result = _executor(service).execute(preparation)

    assert service.calls == 1
    assert result.outcome is DraftRevisionExecutionOutcome.CONTROLLED_REVISION_FAILED
    assert result.controlled_revision_result is controlled
    assert result.revised_draft is None
    assert (
        result.diagnostic.controlled_revision_diagnostic_code
        == "revision_gateway_failure"
    )


def test_invocation_factory_failure_calls_service_zero_times():
    _, preparation = _prepared()

    class BrokenFactory:
        def create(self, preparation):
            raise ValueError("sentinel")

    service = ControlledServiceSpy()
    lifecycle = DraftRevisionExecutionLifecycleFactory()
    executor = DraftRevisionExecutor(
        controlled_revision_service=service,
        preparation_result_validator=validate_draft_revision_preparation_result,
        invocation_factory=BrokenFactory(),
        invocation_validator=validate_controlled_revision_invocation,
        controlled_revision_result_validator=validate_controlled_revision_result,
        execution_result_factory=DraftRevisionExecutionResultFactory(lifecycle),
        execution_result_validator=validate_draft_revision_execution_result,
    )
    result = executor.execute(preparation)

    assert service.calls == 0
    assert result.outcome is DraftRevisionExecutionOutcome.INVALID_INVOCATION


def test_report_and_safe_repr_exclude_all_content():
    _, preparation = _prepared()
    controlled = _controlled_success(preparation)
    result = _executor(ControlledServiceSpy(controlled)).execute(preparation)
    report = build_draft_revision_execution_report(result)
    text = serialize_draft_revision_execution_report(report)

    assert preparation.resolved_input.source_draft.assembled_text not in text
    assert (
        preparation.generation_request.revision_instructions.editorial_instruction
        not in text
    )
    assert controlled.revised_draft.assembled_text not in text
    assert controlled.revised_draft.assembled_text not in repr(result)
    assert text == serialize_draft_revision_execution_report(report)


def test_executor_has_no_preparation_gateway_regeneration_or_provider_dependency():
    from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
        execution,
    )

    source = inspect.getsource(execution)
    executor_source = inspect.getsource(DraftRevisionExecutor)
    assert "ControlledRevisionGateway" not in source
    assert "DraftRevisionPreparationService" not in source
    assert "DraftRevisionInputResolver" not in source
    assert "DraftRevisionPreconditionEvaluator" not in source
    assert "DraftRevisionPreservationManifestBuilder" not in source
    assert "DraftRegeneration" not in source
    assert ".generate(" not in source
    assert "retry" not in executor_source.casefold()
    assert "fallback" not in executor_source.casefold()
