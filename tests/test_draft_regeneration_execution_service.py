"""M6C.6C Part 3B service, composition, and freeze-readiness tests."""

from test_draft_regeneration_contracts import _executor_request, _input
from test_draft_regeneration_runtime import GatewaySpy

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
)
from pastila_scout.editor.qa.corrective_action.executors import (
    ControlledGenerationResultValidator,
    DraftRegenerationExecutionService,
    DraftRegenerationExecutor,
    DraftRegenerationResultFactory,
    build_draft_regeneration_execution_service,
    build_draft_regeneration_execution_service_report,
    serialize_draft_regeneration_execution_service_report,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_regeneration import (
    DraftRegenerationInputResolver,
    DraftRegenerationRequestFactory,
    build_standard_draft_regeneration_policy,
)


def test_composition_builds_isolated_runtime_graphs_and_preserves_identity():
    gateway = GatewaySpy()
    first = build_draft_regeneration_execution_service(gateway, _input())
    second = build_draft_regeneration_execution_service(gateway, _input())

    assert first is not second
    assert first.executor is not second.executor
    assert isinstance(first, DraftRegenerationExecutionService)
    assert first.descriptor == second.descriptor


def test_service_success_invokes_one_executor_and_one_gateway_call():
    gateway = GatewaySpy()
    service = build_draft_regeneration_execution_service(gateway, _input())
    request = _executor_request()

    result = service.execute(request)

    assert gateway.calls == 1
    assert result.operational_outcome is CorrectiveActionExecutorOutcome.COMPLETED
    assert result.output_reference is not None


def test_service_preserves_preparation_failure_zero_generation_calls():
    gateway = GatewaySpy()
    executor = DraftRegenerationExecutor(
        DraftRegenerationRequestFactory(DraftRegenerationInputResolver(None)),
        gateway,
        ControlledGenerationResultValidator(),
        DraftRegenerationResultFactory(),
        build_standard_draft_regeneration_policy(),
    )
    service = DraftRegenerationExecutionService(executor)

    result = service.execute(_executor_request())

    assert gateway.calls == 0
    assert result.execution_status is CorrectiveActionExecutionStatus.FAILED


def test_outer_service_exception_is_sanitized(monkeypatch):
    service = build_draft_regeneration_execution_service(GatewaySpy(), _input())
    request = _executor_request()

    def fail(_request):
        raise RuntimeError("credential path traceback")

    monkeypatch.setattr(service.executor, "execute", fail)
    result = service.execute(request)

    assert result.operational_outcome is CorrectiveActionExecutorOutcome.FAILED_INTERNAL
    assert (
        result.diagnostic.code
        is CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED
    )
    assert "credential" not in result.diagnostic.safe_message.casefold()


def test_service_report_is_safe_deterministic_projection():
    service = build_draft_regeneration_execution_service(GatewaySpy(), _input())
    request = _executor_request()
    result = service.execute(request)
    report = build_draft_regeneration_execution_service_report(service, request, result)
    serialized = serialize_draft_regeneration_execution_service_report(report)

    assert serialized == serialize_draft_regeneration_execution_service_report(report)
    assert report.executor_result_fingerprint == result.result_fingerprint
    for content in (
        "draft prose",
        "prompt text",
        "provider payload",
        "api_key",
        "c:\\",
    ):
        assert content not in serialized.casefold()


def test_composition_rejects_invalid_runtime_dependencies():
    try:
        build_draft_regeneration_execution_service(object(), _input())
    except TypeError as exc:
        assert str(exc) == "invalid Controlled Generation boundary"
    else:
        raise AssertionError("invalid generation boundary was accepted")
