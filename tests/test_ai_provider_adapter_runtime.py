"""Reusable behavioral contract tests for the canonical AI provider runtime."""

from dataclasses import FrozenInstanceError

import pytest
from pydantic import SecretStr
from test_ai_provider_adapter_architecture import _configuration
from test_controlled_revision_runtime import _success as gateway_success
from test_draft_revision_preparation import _prepared

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderAuthenticationError,
    AIProviderClientRequest,
    AIProviderClientResponse,
    AIProviderExecutionStatus,
    AIProviderInterpretationResult,
    AIProviderTimeoutError,
    AIProviderUsage,
    AIRetryPolicy,
    ProjectedAIProviderRequest,
    build_ai_provider_execution_safe_report,
    compose_ai_provider_runtime,
    serialize_ai_provider_execution_safe_report,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    ControlledRevisionInvocationFactory,
)


class Projector:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def project(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return ProjectedAIProviderRequest(
            invocation=request.invocation,
            invocation_fingerprint=request.invocation.invocation_fingerprint,
            client_request=AIProviderClientRequest(
                provider_identifier=request.provider_identifier,
                timeout_seconds=20,
                correlation_identifier=request.correlation_identifier,
                payload={"opaque": True},
            ),
        )


class SubstitutingProjector(Projector):
    def __init__(self, substitute, fingerprint=None):
        super().__init__()
        self.substitute = substitute
        self.fingerprint = fingerprint or substitute.invocation_fingerprint

    def project(self, request):
        self.calls += 1
        return ProjectedAIProviderRequest(
            invocation=self.substitute,
            invocation_fingerprint=self.fingerprint,
            client_request=AIProviderClientRequest(
                provider_identifier=request.provider_identifier,
                timeout_seconds=20,
                payload={"opaque": True},
            ),
        )


class Credentials:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def resolve(self, reference):
        self.calls += 1
        if self.error:
            raise self.error
        return SecretStr("sentinel-secret")


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def send(self, request, *, credential_provider):
        self.calls += 1
        credential_provider.resolve("env:AI_PROVIDER_KEY")
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class Interpreter:
    def __init__(self, gateway_result, error=None):
        self.gateway_result = gateway_result
        self.error = error
        self.calls = 0

    def interpret(self, request, response):
        self.calls += 1
        if self.error:
            raise self.error
        return AIProviderInterpretationResult(
            gateway_result=self.gateway_result,
            usage=AIProviderUsage(
                prompt_tokens=3,
                completion_tokens=2,
                total_tokens=5,
                latency_ms=response.latency_ms,
            ),
            provider_request_identifier="req_synthetic",
            provider_model_identifier="returned-model",
            metadata=(("completion_category", "completed"),),
        )


class Sleeper:
    def __init__(self):
        self.delays = []

    def sleep(self, delay):
        self.delays.append(delay)


class Cancellation:
    def __init__(self, cancelled=False):
        self.cancelled = cancelled

    def is_cancelled(self):
        return self.cancelled


class Observer:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event.code.value)


def _inputs(
    *,
    responses,
    retries=1,
    projector=None,
    credentials=None,
    interpreter_error=None,
    cancelled=False
):
    _, preparation = _prepared()
    invocation = ControlledRevisionInvocationFactory().create(preparation)
    gateway_result = gateway_success(invocation, invocation.request.source_draft)
    configuration = _configuration().model_copy(
        update={
            "retry_policy": AIRetryPolicy(maximum_attempts=retries, delay_seconds=2)
        }
    )
    dependencies = {
        "configuration": configuration,
        "client": Client(responses),
        "credential_provider": credentials or Credentials(),
        "projector": projector or Projector(),
        "interpreter": Interpreter(gateway_result, interpreter_error),
        "sleeper": Sleeper(),
        "cancellation_token": Cancellation(cancelled),
        "observer": Observer(),
    }
    composition = compose_ai_provider_runtime(**dependencies)
    return invocation, dependencies, composition.runtime


def _response(prompt=3, completion=2, latency=10):
    return AIProviderClientResponse(payload={"opaque": "response"}, latency_ms=latency)


def test_success_preserves_invocation_and_exact_call_counts():
    invocation, deps, runtime = _inputs(responses=[_response()])

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.SUCCESS
    assert result.request.invocation is invocation
    assert deps["projector"].calls == deps["credential_provider"].calls == 1
    assert deps["client"].calls == deps["interpreter"].calls == 1
    assert result.usage.total_tokens == 5
    assert result.gateway_result is result.interpretation_result.gateway_result
    assert result.interpretation_result.provider_request_identifier == "req_synthetic"
    assert result.interpretation_result.provider_model_identifier == "returned-model"


def test_retry_reuses_projection_and_backoff_then_interprets_once():
    invocation, deps, runtime = _inputs(
        responses=[AIProviderTimeoutError("unsafe raw"), _response()], retries=2
    )

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.SUCCESS
    assert deps["projector"].calls == deps["credential_provider"].calls == 1
    assert deps["client"].calls == 2
    assert deps["interpreter"].calls == 1
    assert deps["sleeper"].delays == [2]


def test_retry_exhaustion_never_interprets_or_leaks_exception():
    invocation, deps, runtime = _inputs(
        responses=[AIProviderTimeoutError("SECRET"), AIProviderTimeoutError("SECRET")],
        retries=2,
    )

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.FAILED
    assert deps["client"].calls == 2
    assert deps["interpreter"].calls == 0
    assert "SECRET" not in repr(result)


def test_permanent_client_failure_is_not_retried():
    invocation, deps, runtime = _inputs(
        responses=[AIProviderAuthenticationError("unsafe credential")], retries=3
    )

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.FAILED
    assert deps["client"].calls == 1
    assert deps["interpreter"].calls == 0
    assert deps["sleeper"].delays == []


def test_interpretation_failure_occurs_once_without_retry():
    invocation, deps, runtime = _inputs(
        responses=[_response()], retries=3, interpreter_error=ValueError("raw body")
    )

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.FAILED
    assert deps["client"].calls == deps["interpreter"].calls == 1
    assert deps["sleeper"].delays == []


def test_projection_and_credential_failures_stop_before_transport():
    invocation, deps, runtime = _inputs(
        responses=[], projector=Projector(ValueError("payload leaked"))
    )
    projection = runtime.execute(invocation)
    assert deps["projector"].calls == 1
    assert deps["credential_provider"].calls == deps["client"].calls == 0
    assert projection.diagnostic.diagnostic_code == "provider_projection_failed"

    invocation, deps, runtime = _inputs(
        responses=[], credentials=Credentials(ValueError("secret"))
    )
    credential = runtime.execute(invocation)
    assert deps["projector"].calls == deps["credential_provider"].calls == 1
    assert deps["client"].calls == 0
    assert (
        credential.diagnostic.diagnostic_code == "provider_credential_resolution_failed"
    )


def test_identity_distinct_equivalent_projection_is_rejected_before_credentials():
    invocation, _, _ = _inputs(responses=[])
    substitute = invocation.model_copy()
    assert substitute is not invocation
    assert substitute.invocation_fingerprint == invocation.invocation_fingerprint
    projector = SubstitutingProjector(substitute)
    _, deps, runtime = _inputs(responses=[], projector=projector)

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.FAILED
    assert projector.calls == 1
    assert deps["credential_provider"].calls == deps["client"].calls == 0


def test_projected_fingerprint_mismatch_is_rejected_before_credentials():
    invocation, _, _ = _inputs(responses=[])
    projector = SubstitutingProjector(invocation, "sha256:" + "0" * 64)
    _, deps, runtime = _inputs(responses=[], projector=projector)

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.FAILED
    assert deps["credential_provider"].calls == deps["client"].calls == 0


def test_interpretation_contract_is_immutable_and_rejects_unsafe_metadata():
    invocation, _, _ = _inputs(responses=[])
    gateway_result = gateway_success(invocation, invocation.request.source_draft)
    interpretation = AIProviderInterpretationResult(
        gateway_result=gateway_result,
        metadata=(("completion_category", "completed"),),
    )

    with pytest.raises((FrozenInstanceError, ValueError)):
        interpretation.provider_model_identifier = "changed"
    with pytest.raises(ValueError, match="canonical"):
        AIProviderInterpretationResult(
            gateway_result=gateway_result,
            metadata=(("z", "1"), ("a", "2")),
        )
    with pytest.raises(ValueError, match="unsafe"):
        AIProviderInterpretationResult(
            gateway_result=gateway_result,
            metadata=(("header", "Bearer fake-secret"),),
        )


def test_client_response_is_transport_only():
    fields = set(AIProviderClientResponse.model_fields)

    assert fields == {"payload", "latency_ms"}


def test_cancellation_before_execution_has_zero_calls():
    invocation, deps, runtime = _inputs(responses=[], cancelled=True)

    result = runtime.execute(invocation)

    assert result.status is AIProviderExecutionStatus.CANCELLED
    assert deps["projector"].calls == deps["credential_provider"].calls == 0
    assert deps["client"].calls == deps["interpreter"].calls == 0


def test_observability_and_safe_report_are_deterministic_and_content_free():
    invocation, deps, runtime = _inputs(responses=[_response()])
    result = runtime.execute(invocation)
    report = build_ai_provider_execution_safe_report(result)
    first = serialize_ai_provider_execution_safe_report(report)
    second = serialize_ai_provider_execution_safe_report(report)

    assert first == second
    assert "sentinel-secret" not in first
    assert invocation.request.source_draft.assembled_text not in first
    assert deps["observer"].events == [
        "execution_started",
        "projection_completed",
        "projection_validated",
        "credential_resolution_started",
        "credential_resolution_completed",
        "attempt_started",
        "attempt_succeeded",
        "interpretation_started",
        "interpretation_completed",
        "usage_aggregated",
        "execution_succeeded",
    ]
