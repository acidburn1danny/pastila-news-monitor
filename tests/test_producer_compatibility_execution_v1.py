"""Focused tests for the explicit opt-in neutral Producer path."""

from __future__ import annotations

import copy
import inspect
import sys

import test_producer_compatibility_v1 as phase_a

from pastila_scout.editor.generation.provider_compatibility_execution_v1 import (
    compose_producer_compatibility_runtime_v1,
)
from pastila_scout.editor.generation.provider_compatibility_v1 import (
    ProducerCompatibilityConfigurationError,
    ProducerCompatibilityEventV1,
    ProducerDiagnosticsObservationV1,
    ProducerExecutionFailureV1,
    ProducerExecutionRequestV1,
    ProducerFailureCodeV1,
    ProducerTokenUsageV1,
)
from pastila_scout.editor.generation.provider_compatibility_v1.models import (
    AIProviderExecutionStatus,
    AIRetryPolicy,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    build_provider_request_envelope,
)


class Authorities:
    def __init__(self, results=(), cancellation=(False,), observation=True):
        self.results = list(results)
        self.cancellation = list(cancellation)
        self.observation = observation
        self.execute_calls = 0
        self.observe_calls = 0
        self.clock_calls = 0
        self.retry_calls = 0
        self.sleep_calls = 0
        self.events = []

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.execute_calls += 1
        result = self.results.pop(0)
        return phase_a._result(result, request=request)

    def observe(
        self,
        *,
        correlation_id: str,
        attempt_number: int,
        execution_request_id: str,
        request_envelope_identity: str,
        result: ProviderExecutionResultV2,
    ) -> ProducerDiagnosticsObservationV1 | None:
        self.observe_calls += 1
        if not self.observation:
            return None
        return ProducerDiagnosticsObservationV1(
            correlation_id=correlation_id,
            attempt_number=attempt_number,
            execution_request_id=execution_request_id,
            request_envelope_identity=request_envelope_identity,
            usage=ProducerTokenUsageV1(
                prompt_tokens=2, completion_tokens=3, total_tokens=5
            ),
            provider_request_id="provider-request",
            returned_model_id="test-model",
        )

    def read_monotonic_ns(self) -> int:
        self.clock_calls += 1
        return self.clock_calls * 1_000_000

    def emit(self, event: ProducerCompatibilityEventV1) -> None:
        self.events.append(event)

    def is_cancelled(self) -> bool:
        return self.cancellation.pop(0) if self.cancellation else False

    def should_retry(
        self,
        *,
        failure: ProducerExecutionFailureV1,
        attempt_number: int,
        policy: AIRetryPolicy,
    ) -> bool:
        self.retry_calls += 1
        return True

    def sleep(self, delay_seconds: float) -> None:
        self.sleep_calls += 1


class GatewayProjector:
    def __init__(self, gateway):
        self.gateway = gateway
        self.calls = 0

    def project(self, *, request, result):
        self.calls += 1
        return self.gateway


class RaisingExecutor(Authorities):
    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.execute_calls += 1
        raise RuntimeError("unsafe provider detail")


class ExactResultExecutor(Authorities):
    def __init__(self, result):
        super().__init__(())
        self.result = result

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.execute_calls += 1
        return self.result


def _request(*, retries=1):
    gateway = phase_a._gateway()
    base = phase_a._request(
        invocation_fingerprint=gateway.invocation_fingerprint,
        draft_fingerprint=gateway.source_draft_fingerprint[7:],
    )
    request = ProducerExecutionRequestV1.build(
        invocation_reference=base.invocation_reference,
        invocation_fingerprint=base.invocation_fingerprint,
        provider_request=base.provider_request,
        retry_policy=AIRetryPolicy(maximum_attempts=retries),
    )
    return request, gateway


def _runtime(authorities, *, retries=1):
    request, gateway = _request(retries=retries)
    gateway_projector = GatewayProjector(gateway)
    runtime = compose_producer_compatibility_runtime_v1(
        request=request,
        executor=authorities,
        diagnostics_authority=authorities,
        clock=authorities,
        cancellation_token=authorities,
        retry_decider=authorities,
        sleeper=authorities,
        gateway_projector=gateway_projector,
        observer=authorities,
    )
    return runtime, gateway_projector


def test_neutral_success_executes_once_and_projects_complete_result() -> None:
    authorities = Authorities((ExecutionOutcomeV2.COMPLETED,))
    runtime, gateway = _runtime(authorities)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.SUCCESS
    assert result.gateway_result is not None
    assert len(result.attempts) == 1
    assert result.diagnostics.usage.total_tokens == 5
    assert result.diagnostics.latency_ms == "1"
    assert authorities.execute_calls == authorities.observe_calls == gateway.calls == 1
    assert authorities.clock_calls == 2


def test_provider_failure_is_mapped_without_gateway_projection() -> None:
    authorities = Authorities((ExecutionOutcomeV2.PROVIDER_FAILURE,))
    runtime, gateway = _runtime(authorities)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.FAILED
    assert (
        result.failure.diagnostic_code
        is ProducerFailureCodeV1.PROVIDER_EXECUTION_FAILED
    )
    assert gateway.calls == 0
    assert authorities.execute_calls == authorities.observe_calls == 1


def test_timeout_is_retained_and_retry_exhaustion_is_explicit() -> None:
    authorities = Authorities((ExecutionOutcomeV2.TIMEOUT,))
    runtime, _ = _runtime(authorities)

    result = runtime.execute()

    assert result.attempts[0].outcome is ExecutionOutcomeV2.TIMEOUT
    assert result.failure.diagnostic_code is ProducerFailureCodeV1.RETRY_EXHAUSTED


def test_pre_dispatch_cancellation_performs_no_execution_or_diagnostics() -> None:
    authorities = Authorities((), cancellation=(True,))
    runtime, gateway = _runtime(authorities)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.CANCELLED
    assert result.attempts == ()
    assert authorities.execute_calls == authorities.observe_calls == gateway.calls == 0
    assert authorities.clock_calls == 0


def test_lower_cancellation_remains_a_cancelled_terminal_result() -> None:
    authorities = Authorities((ExecutionOutcomeV2.CANCELLED,))
    runtime, gateway = _runtime(authorities)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.CANCELLED
    assert result.attempts[0].outcome is ExecutionOutcomeV2.CANCELLED
    assert result.failure.source_outcome is ExecutionOutcomeV2.CANCELLED
    assert result.failure.source_failure_code == "execution-failed"
    assert gateway.calls == 0


def test_foreign_and_copied_output_lineage_cannot_authorize_success() -> None:
    request, gateway = _request()
    lower = phase_a._result(
        ExecutionOutcomeV2.COMPLETED, request=request.provider_request
    )
    output = lower.provider_result.outputs[0]
    copied_invalid = copy.deepcopy(output)
    object.__setattr__(copied_invalid, "source_request_reference", "foreign-copied")
    candidates = (
        output.model_copy(update={"source_request_reference": "foreign-output"}),
        output.model_copy(update={"source_request_reference": "source-request:other"}),
        copied_invalid,
        copy.copy(copied_invalid),
    )
    for candidate in candidates:
        projection = lower.provider_result.model_copy(update={"outputs": (candidate,)})
        executor = ExactResultExecutor(
            lower.model_copy(update={"provider_result": projection})
        )
        gateway_projector = GatewayProjector(gateway)
        runtime = compose_producer_compatibility_runtime_v1(
            request=request,
            executor=executor,
            diagnostics_authority=executor,
            clock=executor,
            cancellation_token=executor,
            retry_decider=executor,
            sleeper=executor,
            gateway_projector=gateway_projector,
        )

        result = runtime.execute()

        assert result.status is AIProviderExecutionStatus.FAILED
        assert (
            result.failure.diagnostic_code
            is ProducerFailureCodeV1.PROVIDER_RESULT_INVALID
        )
        assert gateway_projector.calls == 0


def test_foreign_attempt_lineage_fails_before_gateway_projection() -> None:
    request, gateway = _request()
    lower = phase_a._result(
        ExecutionOutcomeV2.COMPLETED, request=request.provider_request
    ).model_copy(update={"request_id": "foreign-attempt"})
    executor = ExactResultExecutor(lower)
    gateway_projector = GatewayProjector(gateway)
    runtime = compose_producer_compatibility_runtime_v1(
        request=request,
        executor=executor,
        diagnostics_authority=executor,
        clock=executor,
        cancellation_token=executor,
        retry_decider=executor,
        sleeper=executor,
        gateway_projector=gateway_projector,
    )

    result = runtime.execute()

    assert (
        result.failure.diagnostic_code is ProducerFailureCodeV1.PROVIDER_RESULT_INVALID
    )
    assert gateway_projector.calls == 0


def test_valid_output_order_is_preserved_after_lineage_validation() -> None:
    base, gateway = _request()
    first = base.provider_request.request_intent.request_units[0]
    second = type(first)(
        source_request_reference="source-request:second",
        ordinal=1,
        messages=first.messages,
    )
    intent = base.provider_request.request_intent.model_copy(
        update={"request_units": (first, second)}
    )
    provider_request = ProviderExecutionRequestV2(
        provider=base.provider_request.provider,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(
            intent, base.provider_request.provider
        ),
        context=base.provider_request.context,
        timeout_policy=base.provider_request.timeout_policy,
    )
    request = ProducerExecutionRequestV1.build(
        invocation_reference=base.invocation_reference,
        invocation_fingerprint=base.invocation_fingerprint,
        provider_request=provider_request,
        retry_policy=base.retry_policy,
    )
    outputs = tuple(
        ProviderOutputInputV2(
            source_request_reference=unit.source_request_reference,
            ordinal=unit.ordinal,
            generated_text=f"output-{unit.ordinal}",
            finish_reason=ProviderFinishReasonV2.COMPLETED,
        )
        for unit in intent.request_units
    )
    lower = ProviderExecutionResultV2(
        request_id=provider_request.context.request_id,
        provider_id=provider_request.provider.provider_id,
        request_envelope_identity=provider_request.request_envelope.identity,
        outcome=ExecutionOutcomeV2.COMPLETED,
        finished_at=phase_a._result(ExecutionOutcomeV2.COMPLETED).finished_at,
        provider_result=ProviderResultProjectionV2(
            status=ProviderResultStatusV2.SUCCESS,
            outputs=outputs,
        ),
    )
    executor = ExactResultExecutor(lower)
    runtime = compose_producer_compatibility_runtime_v1(
        request=request,
        executor=executor,
        diagnostics_authority=executor,
        clock=executor,
        cancellation_token=executor,
        retry_decider=executor,
        sleeper=executor,
        gateway_projector=GatewayProjector(gateway),
    )

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.SUCCESS
    assert tuple(
        item.source_request_reference
        for item in result.attempts[0].diagnostics.finish_metadata
    ) == ("source-request:test", "source-request:second")


def test_gateway_projection_failure_cannot_become_success() -> None:
    authorities = Authorities((ExecutionOutcomeV2.COMPLETED,))
    request, _ = _request()
    runtime = compose_producer_compatibility_runtime_v1(
        request=request,
        executor=authorities,
        diagnostics_authority=authorities,
        clock=authorities,
        cancellation_token=authorities,
        retry_decider=authorities,
        sleeper=authorities,
        gateway_projector=GatewayProjector(None),
    )

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.FAILED
    assert (
        result.failure.diagnostic_code
        is ProducerFailureCodeV1.GATEWAY_PROJECTION_FAILED
    )


def test_executor_exception_is_mapped_and_never_escapes() -> None:
    authorities = RaisingExecutor(())
    runtime, _ = _runtime(authorities)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.FAILED
    assert result.attempts[0].outcome is None
    assert (
        result.failure.diagnostic_code
        is ProducerFailureCodeV1.PROVIDER_EXECUTOR_CONTRACT_FAILED
    )


def test_retry_is_producer_owned_and_reuses_the_injected_executor() -> None:
    authorities = Authorities(
        (ExecutionOutcomeV2.TIMEOUT, ExecutionOutcomeV2.COMPLETED)
    )
    runtime, gateway = _runtime(authorities, retries=2)

    result = runtime.execute()

    assert result.status is AIProviderExecutionStatus.SUCCESS
    assert tuple(attempt.attempt_number for attempt in result.attempts) == (1, 2)
    assert authorities.execute_calls == 2
    assert authorities.retry_calls == authorities.sleep_calls == 1
    assert gateway.calls == 1


def test_diagnostics_are_only_taken_from_injected_authority() -> None:
    authorities = Authorities((ExecutionOutcomeV2.PROVIDER_FAILURE,), observation=False)
    runtime, _ = _runtime(authorities)

    result = runtime.execute()

    assert result.diagnostics.usage is None
    assert result.diagnostics.provider_request_id is None
    assert result.diagnostics.returned_model_id is None
    assert authorities.observe_calls == 1


def test_composition_is_explicit_and_does_not_execute_during_construction() -> None:
    authorities = Authorities((ExecutionOutcomeV2.COMPLETED,))

    runtime, gateway = _runtime(authorities)

    assert runtime is not None
    assert authorities.execute_calls == authorities.observe_calls == 0
    assert authorities.clock_calls == gateway.calls == 0


def test_diagnostics_and_clock_are_required_for_explicit_opt_in() -> None:
    import pytest

    request, gateway = _request()
    authorities = Authorities((ExecutionOutcomeV2.COMPLETED,))
    for diagnostics, clock in ((None, authorities), (authorities, None)):
        with pytest.raises(Exception, match="configuration is invalid"):
            compose_producer_compatibility_runtime_v1(
                request=request,
                executor=authorities,
                diagnostics_authority=diagnostics,
                clock=clock,
                cancellation_token=authorities,
                retry_decider=authorities,
                sleeper=authorities,
                gateway_projector=GatewayProjector(gateway),
            )
    assert authorities.execute_calls == 0


def test_configuration_error_traceback_retains_no_phase_b_authority() -> None:
    request, gateway = _request()
    authorities = Authorities(())
    targets = (request, authorities, gateway)
    try:
        compose_producer_compatibility_runtime_v1(
            request=request,
            executor=object(),
            diagnostics_authority=authorities,
            clock=authorities,
            cancellation_token=authorities,
            retry_decider=authorities,
            sleeper=authorities,
            gateway_projector=gateway,
            observer=authorities,
        )
    except ProducerCompatibilityConfigurationError as error:
        retained = []
        traceback = error.__traceback__
        while traceback:
            if (
                "provider_compatibility_execution_v1"
                in traceback.tb_frame.f_code.co_filename
            ):
                retained.extend(traceback.tb_frame.f_locals.values())
            traceback = traceback.tb_next
        assert all(value is not target for value in retained for target in targets)
        assert error.__context__ is None
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
    else:
        raise AssertionError("invalid Phase B composition was accepted")


def test_latency_keeps_integer_trailing_zeroes() -> None:
    authorities = Authorities((ExecutionOutcomeV2.COMPLETED,))
    authorities.read_monotonic_ns = lambda: 0
    samples = iter((0, 10_000_000))
    authorities.read_monotonic_ns = lambda: next(samples)
    runtime, _ = _runtime(authorities)

    result = runtime.execute()

    assert result.diagnostics.latency_ms == "10"


def test_legacy_api_and_default_path_remain_unchanged() -> None:
    import pastila_scout.editor.generation.ai_provider_adapter.openai as legacy

    assert "compose_openai_controlled_revision_adapter" in legacy.__all__
    assert "provider_compatibility_execution_v1" not in inspect.getsource(legacy)


def test_neutral_package_has_no_openai_sdk_or_runtime_dependency() -> None:
    import pastila_scout.editor.generation.provider_compatibility_execution_v1 as neutral

    source = "\n".join(
        inspect.getsource(sys.modules[name])
        for name in (
            neutral.__name__ + ".protocols",
            neutral.__name__ + ".runtime",
        )
    )
    assert "openai" not in source.casefold()
    assert "provider_runtime" not in source
    assert "provider_execution_openai" not in source
    assert "provider_execution_v2" in source
