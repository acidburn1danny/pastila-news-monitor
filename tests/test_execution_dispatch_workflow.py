"""M6C.6B Part 3 production workflow and safe-report tests."""

from test_corrective_action_execution_dispatch_contracts import (
    _context,
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchWorkflowRequest,
    CorrectiveActionExecutionDispatchWorkflowService,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorBinding,
    CorrectiveActionExecutorBindings,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRegistry,
    CorrectiveActionExecutorResult,
    build_execution_dispatch_runtime_report,
    build_standard_corrective_action_execution_dispatch_policy,
    build_standard_corrective_action_execution_dispatch_service,
    dispatch_corrective_action_execution,
    render_execution_dispatch_runtime_report,
    serialize_execution_dispatch_runtime_report,
)


class _Executor:
    def __init__(self, descriptor):
        self._descriptor = descriptor
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, request):
        self.calls += 1
        return CorrectiveActionExecutorResult.build(
            executor_descriptor=self.descriptor,
            request=request,
            operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
            execution_status=CorrectiveActionExecutionStatus.COMPLETED,
            diagnostic=None,
        )


def _workflow():
    planning = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(planning.plan)
    executor = _Executor(descriptor)
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    bindings = CorrectiveActionExecutorBindings.build(
        registry, (CorrectiveActionExecutorBinding(descriptor, executor),)
    )
    service = build_standard_corrective_action_execution_dispatch_service(bindings)
    workflow = CorrectiveActionExecutionDispatchWorkflowService(service)
    request = CorrectiveActionExecutionDispatchWorkflowRequest.build(
        planning_result=planning,
        dispatch_policy=build_standard_corrective_action_execution_dispatch_policy(),
        execution_context=_context(),
    )
    return workflow, request, executor


def test_workflow_preserves_identity_and_dispatches_once() -> None:
    workflow, request, executor = _workflow()
    result = dispatch_corrective_action_execution(request, workflow)
    assert result.request is request
    assert result.dispatch_request.planning_result is request.planning_result
    assert result.dispatch_result.request is result.dispatch_request
    assert result.dispatch_result.executor_request.plan is request.planning_result.plan
    assert (
        result.dispatch_result.executor_result.request
        is result.dispatch_result.executor_request
    )
    assert executor.calls == 1


def test_workflow_and_reports_are_deterministic_and_content_safe() -> None:
    first_workflow, first_request, _ = _workflow()
    second_workflow, second_request, _ = _workflow()
    first = first_workflow.run(first_request)
    second = second_workflow.run(second_request)
    assert first == second
    report = build_execution_dispatch_runtime_report(first)
    serialized = serialize_execution_dispatch_runtime_report(report)
    rendered = render_execution_dispatch_runtime_report(report)
    assert serialized == serialize_execution_dispatch_runtime_report(report)
    assert "finding" not in serialized and "provider" not in serialized
    assert "Dispatch status: executor_completed" in rendered


def test_workflow_fingerprint_tampering_fails_closed_before_dispatch() -> None:
    workflow, request, executor = _workflow()
    tampered = request.model_copy(update={"request_fingerprint": "sha256:bad"})
    try:
        workflow.run(tampered)
    except ValueError:
        pass
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("tampered workflow request was accepted")
    assert executor.calls == 0
