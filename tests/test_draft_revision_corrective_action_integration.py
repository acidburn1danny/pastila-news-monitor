"""M6C.6D Part 3B end-to-end integration guarantees."""

from dataclasses import FrozenInstanceError

import pytest
from test_draft_revision_executor import (
    ControlledServiceSpy,
    _controlled_success,
    _executor,
)
from test_draft_revision_preparation import _prepared

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatcherV2,
    CorrectiveActionExecutionPhaseV2,
    CorrectiveActionExecutionResponse,
    CorrectiveActionExecutionResponseStatus,
    CorrectiveActionV2Binding,
    build_execution_safe_report,
    serialize_execution_safe_report,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    compose_draft_revision_execution_dispatcher,
    compose_draft_revision_preparation_service,
)
from pastila_scout.editor.qa.corrective_action.models import CorrectiveAction


class PreparationSpy:
    def __init__(self, service):
        self.service = service
        self.calls = 0
        self.received = None

    def prepare(self, request):
        self.calls += 1
        self.received = request
        return self.service.prepare(request)


class ExecutorSpy:
    def __init__(self, executor):
        self.executor = executor
        self.calls = 0
        self.received = None

    def execute(self, preparation):
        self.calls += 1
        self.received = preparation
        return self.executor.execute(preparation)


def test_integrated_success_preserves_identity_and_exact_call_counts():
    request, prepared = _prepared()
    controlled_result = _controlled_success(prepared)
    controlled = ControlledServiceSpy(controlled_result)
    preparation = PreparationSpy(
        compose_draft_revision_preparation_service(request.executor_descriptor)
    )
    executor = ExecutorSpy(_executor(controlled))
    dispatcher = compose_draft_revision_execution_dispatcher(
        preparation_service=preparation, draft_revision_executor=executor
    )

    response = dispatcher.dispatch(request)

    assert response.status is CorrectiveActionExecutionResponseStatus.SUCCESS
    assert preparation.calls == executor.calls == controlled.calls == 1
    assert preparation.received is request
    assert request.legacy_request is request.legacy_request
    assert executor.received is response.capability_result.preparation_result
    assert response.capability_result.controlled_revision_result is controlled_result
    assert response.capability_result.revised_draft is controlled_result.revised_draft


def test_safe_report_is_deterministic_and_content_free():
    request, prepared = _prepared()
    controlled_result = _controlled_success(prepared)
    dispatcher = compose_draft_revision_execution_dispatcher(
        preparation_service=compose_draft_revision_preparation_service(
            request.executor_descriptor
        ),
        draft_revision_executor=_executor(ControlledServiceSpy(controlled_result)),
    )
    response = dispatcher.dispatch(request)

    first = serialize_execution_safe_report(build_execution_safe_report(response))
    second = serialize_execution_safe_report(build_execution_safe_report(response))

    assert first == second
    assert request.planning_input.source_draft.assembled_text not in first
    assert response.capability_result.revised_draft.assembled_text not in first


def test_unsupported_route_performs_no_downstream_calls():
    request, _ = _prepared()
    preparation = PreparationSpy(
        compose_draft_revision_preparation_service(request.executor_descriptor)
    )
    controlled = ControlledServiceSpy()
    executor = ExecutorSpy(_executor(controlled))
    dispatcher = CorrectiveActionExecutionDispatcherV2(())

    response = dispatcher.dispatch(request)

    assert (
        response.status
        is CorrectiveActionExecutionResponseStatus.CORRECTIVE_ACTION_ROUTING_FAILED
    )
    assert preparation.calls == executor.calls == controlled.calls == 0


def test_cross_request_preparation_is_rejected_before_execution():
    current_request, _ = _prepared()
    other_request, other_preparation = _prepared()
    assert current_request is not other_request
    assert current_request.request_fingerprint == other_request.request_fingerprint

    class SubstitutingPreparation:
        def prepare(self, request):
            return other_preparation

    controlled = ControlledServiceSpy(_controlled_success(other_preparation))
    executor = ExecutorSpy(_executor(controlled))
    dispatcher = compose_draft_revision_execution_dispatcher(
        preparation_service=SubstitutingPreparation(),
        draft_revision_executor=executor,
    )

    response = dispatcher.dispatch(current_request)

    assert (
        response.status
        is CorrectiveActionExecutionResponseStatus.CAPABILITY_PREPARATION_FAILED
    )
    assert response.diagnostic_code == "preparation_request_identity_mismatch"
    assert executor.calls == controlled.calls == 0


def test_malformed_request_is_normalized_without_downstream_calls():
    response = CorrectiveActionExecutionDispatcherV2(()).dispatch(object())

    assert (
        response.status
        is CorrectiveActionExecutionResponseStatus.CORRECTIVE_ACTION_ROUTING_FAILED
    )
    assert response.request is None
    assert response.diagnostic_code == "invalid_executor_request"


def test_invalid_v2_request_fingerprint_is_normalized():
    request, _ = _prepared()
    invalid = request.model_copy(update={"request_fingerprint": "sha256:invalid"})

    response = CorrectiveActionExecutionDispatcherV2(()).dispatch(invalid)

    assert (
        response.status
        is CorrectiveActionExecutionResponseStatus.CORRECTIVE_ACTION_ROUTING_FAILED
    )
    assert response.diagnostic_code == "invalid_executor_request"


def test_dispatcher_bindings_are_immutable():
    dispatcher = CorrectiveActionExecutionDispatcherV2(())

    with pytest.raises(FrozenInstanceError):
        dispatcher.bindings = ()


class StaticIntegration:
    def __init__(self, response):
        self.response = response

    def execute(self, request):
        return self.response


def _dispatcher_for(response):
    return CorrectiveActionExecutionDispatcherV2(
        (
            CorrectiveActionV2Binding(
                capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
                action=CorrectiveAction.REQUEST_REVISION,
                integration=StaticIntegration(response),
            ),
        )
    )


@pytest.mark.parametrize("invalid_response", [object(), None, "invalid"])
def test_malformed_integration_response_is_normalized(invalid_response):
    request, _ = _prepared()

    response = _dispatcher_for(invalid_response).dispatch(request)

    assert (
        response.status
        is CorrectiveActionExecutionResponseStatus.INTERNAL_CORRECTIVE_ACTION_EXECUTION_FAILURE
    )
    assert response.diagnostic_code == "invalid_integration_response"


def test_dispatcher_rejects_response_for_another_request_identity():
    current_request, _ = _prepared()
    other_request, _ = _prepared()
    foreign = CorrectiveActionExecutionResponse.build(
        request=other_request,
        capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
        action=CorrectiveAction.REQUEST_REVISION,
        status=CorrectiveActionExecutionResponseStatus.CAPABILITY_NOT_EXECUTABLE,
        lifecycle=(
            CorrectiveActionExecutionPhaseV2.CREATED,
            CorrectiveActionExecutionPhaseV2.FAILED,
        ),
        diagnostic_code="capability_not_executable",
    )

    response = _dispatcher_for(foreign).dispatch(current_request)

    assert response.diagnostic_code == "invalid_integration_response"


def test_dispatcher_rejects_invalid_response_fingerprint():
    request, _ = _prepared()
    valid = CorrectiveActionExecutionResponse.build(
        request=request,
        capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
        action=CorrectiveAction.REQUEST_REVISION,
        status=CorrectiveActionExecutionResponseStatus.CAPABILITY_NOT_EXECUTABLE,
        lifecycle=(
            CorrectiveActionExecutionPhaseV2.CREATED,
            CorrectiveActionExecutionPhaseV2.FAILED,
        ),
        diagnostic_code="capability_not_executable",
    )
    invalid = valid.model_copy(update={"response_fingerprint": "sha256:invalid"})

    response = _dispatcher_for(invalid).dispatch(request)

    assert response.diagnostic_code == "invalid_integration_response"


def test_response_rejects_capability_result_lineage_mismatch():
    request, preparation = _prepared()
    controlled = ControlledServiceSpy(_controlled_success(preparation))
    execution = _executor(controlled).execute(preparation)

    with pytest.raises(ValueError, match="execution lineage"):
        CorrectiveActionExecutionResponse.build(
            request=request,
            capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
            action=CorrectiveAction.REQUEST_REVISION,
            status=CorrectiveActionExecutionResponseStatus.SUCCESS,
            lifecycle=(
                CorrectiveActionExecutionPhaseV2.CREATED,
                CorrectiveActionExecutionPhaseV2.COMPLETED,
            ),
            execution_fingerprint="sha256:" + "0" * 64,
            capability_result=execution,
        )
