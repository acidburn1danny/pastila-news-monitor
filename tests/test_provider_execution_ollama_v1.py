"""Offline contract tests for the Ollama ProviderExecutionV2 implementation."""

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_execution_ollama_v1 import (
    OllamaExecutionConfigV1,
    OllamaHttpClientV1,
    OllamaProviderExecutorV1,
    build_ollama_request,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionConfigurationError,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultStatusV2,
    build_provider_request_envelope,
)

NOW = datetime(2026, 8, 4, 12, tzinfo=UTC)
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"


def _request(*, units: int = 1, timeout: float = 17.5) -> ProviderExecutionRequestV2:
    intent = ProviderRequestIntentV2(
        execution_plan_reference="plan:ollama",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:ollama",
        draft_fingerprint=ZERO,
        request_units=tuple(
            ProviderRequestUnitInputV2(
                source_request_reference=f"source:{ordinal}",
                ordinal=ordinal,
                messages=(
                    ProviderMessageInputV2(
                        role="instruction",
                        content="Răspunde concis.",
                        ordinal=0,
                    ),
                    ProviderMessageInputV2(
                        role="generation",
                        content=f"Prompt {ordinal}",
                        ordinal=1,
                    ),
                ),
            )
            for ordinal in range(units)
        ),
    )
    descriptor = OllamaProviderAdapter.descriptor
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(request_id="ollama-request", requested_at=NOW),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=timeout),
    )


def _config() -> OllamaExecutionConfigV1:
    return OllamaExecutionConfigV1(
        model="qwen3:14b",
        temperature=0.2,
        max_output_tokens=321,
        stop_sequences=("STOP",),
    )


def _response(*, done: bool = True, reason: str = "stop", content: str = "Salut"):
    return {
        "model": "qwen3:14b",
        "created_at": "2026-08-04T12:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": done,
        "done_reason": reason,
    }


def _executor(handler) -> tuple[OllamaProviderExecutorV1, httpx.Client]:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    client = OllamaHttpClientV1(http)
    return OllamaProviderExecutorV1(client, _config()), http


def test_request_mapping_preserves_messages_and_generation_controls() -> None:
    mapped = build_ollama_request(_request(), _config())

    assert mapped.model == "qwen3:14b"
    assert mapped.stream is False
    assert tuple((item.role, item.content) for item in mapped.messages) == (
        ("system", "Răspunde concis."),
        ("user", "Prompt 0"),
    )
    assert mapped.options == {
        "temperature": 0.2,
        "num_predict": 321,
        "stop": ["STOP"],
    }


def test_configuration_and_client_dependencies_are_authoritatively_validated() -> None:
    class TextSubclass(str):
        pass

    with pytest.raises(ValidationError):
        OllamaExecutionConfigV1(model=TextSubclass("qwen3:14b"))
    forged = _config().model_copy(update={"model": " "})
    with httpx.Client(transport=httpx.MockTransport(lambda request: None)) as http:
        client = OllamaHttpClientV1(http)
        with pytest.raises(ExecutionConfigurationError) as captured:
            OllamaProviderExecutorV1(client, forged)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert captured.value.__suppress_context__ is True
    with pytest.raises(ExecutionConfigurationError):
        OllamaProviderExecutorV1(object(), _config())  # type: ignore[arg-type]


def test_unsupported_multiple_units_are_rejected_before_http() -> None:
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_response())

    executor, http = _executor(handler)
    with http, pytest.raises(ExecutionConfigurationError, match="unsupported"):
        executor.execute(_request(units=2))
    assert calls == 0


def test_success_maps_response_and_applies_timeout_once() -> None:
    observed = []

    def handler(request):
        observed.append(request)
        return httpx.Response(200, json=_response())

    executor, http = _executor(handler)
    with http:
        result = executor.execute(_request(timeout=17.5))

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.provider_result is not None
    assert result.provider_result.status is ProviderResultStatusV2.SUCCESS
    assert result.provider_result.outputs[0].generated_text == "Salut"
    assert (
        result.provider_result.outputs[0].finish_reason
        is ProviderFinishReasonV2.COMPLETED
    )
    assert len(observed) == 1
    assert observed[0].url.path == "/api/chat"
    assert observed[0].extensions["timeout"] == {
        "connect": 17.5,
        "read": 17.5,
        "write": 17.5,
        "pool": 17.5,
    }
    assert result.finished_at == NOW


def test_length_completion_maps_to_partial_without_fabricated_output_metadata() -> None:
    executor, http = _executor(
        lambda request: httpx.Response(200, json=_response(reason="length"))
    )
    with http:
        result = executor.execute(_request())
    assert result.provider_result is not None
    assert result.provider_result.status is ProviderResultStatusV2.PARTIAL
    assert result.provider_result.failure_code == "ollama-finish-length"
    assert (
        result.provider_result.outputs[0].finish_reason is ProviderFinishReasonV2.LENGTH
    )


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"unexpected": True}, "ollama-malformed-response"),
        (_response(done=False), "ollama-malformed-response"),
        (_response(content=""), "ollama-malformed-response"),
    ],
)
def test_malformed_responses_are_deterministic(payload, code) -> None:
    executor, http = _executor(lambda request: httpx.Response(200, json=payload))
    with http:
        first = executor.execute(_request())
        second = executor.execute(_request())
    assert first == second
    assert first.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert first.failure_code == code


@pytest.mark.parametrize(
    "payload",
    [
        _response(reason="unsupported"),
        {**_response(), "unexpected": "field"},
        {**_response(), "done_reason": None},
        {**_response(), "created_at": "not-a-time"},
    ],
)
def test_contradictory_or_unexpected_response_schema_fails_closed(payload) -> None:
    executor, http = _executor(lambda request: httpx.Response(200, json=payload))
    with http:
        result = executor.execute(_request())
    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "ollama-malformed-response"


def test_unexpected_transport_exception_is_isolated_without_retry() -> None:
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        raise RuntimeError("secret response body")

    executor, http = _executor(handler)
    with http:
        result = executor.execute(_request())
    assert calls == 1
    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "ollama-transport-contract-failure"
    assert "secret" not in result.failure_message


def test_provider_created_at_makes_repeated_results_deterministic() -> None:
    executor, http = _executor(
        lambda request: httpx.Response(
            200,
            json={
                **_response(),
                "total_duration": 10,
                "eval_count": 2,
                "message": {
                    "role": "assistant",
                    "content": "Salut",
                    "thinking": "provider-only detail",
                },
            },
        )
    )
    with http:
        first = executor.execute(_request())
        second = executor.execute(_request())
    assert first == second
    assert first.finished_at == NOW


@pytest.mark.parametrize(
    ("handler", "outcome", "code"),
    [
        (
            lambda request: (_ for _ in ()).throw(
                httpx.ReadTimeout("late", request=request)
            ),
            ExecutionOutcomeV2.TIMEOUT,
            "ollama-timeout",
        ),
        (
            lambda request: httpx.Response(503, json={"error": "busy"}),
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "ollama-http-failure",
        ),
        (
            lambda request: (_ for _ in ()).throw(
                httpx.ConnectError("offline", request=request)
            ),
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "ollama-connection-failure",
        ),
        (
            lambda request: httpx.Response(
                404, json={"error": "model qwen3:14b not found"}
            ),
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "ollama-model-unavailable",
        ),
        (
            lambda request: httpx.Response(400, json={"error": "invalid options"}),
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "ollama-invalid-request",
        ),
        (
            lambda request: httpx.Response(200, json={"error": "provider failed"}),
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "ollama-http-failure",
        ),
    ],
)
def test_transport_and_provider_failures_map_deterministically(
    handler, outcome, code
) -> None:
    executor, http = _executor(handler)
    with http:
        result = executor.execute(_request())
    assert result.outcome is outcome
    assert result.failure_code == code


def test_passive_import_performs_no_http(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        httpx.Client, "request", lambda *args, **kwargs: calls.append(args)
    )
    import pastila_scout.provider_execution_ollama_v1 as package

    assert package.OllamaProviderExecutorV1
    assert calls == []
