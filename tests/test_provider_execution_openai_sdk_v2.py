from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

import pastila_scout.provider_execution_openai_sdk_v2 as public_api
from pastila_scout.provider_execution_openai_sdk_v2 import (
    OpenAISDKBoundaryError,
    OpenAISDKClientV2,
    OpenAISDKConfigurationError,
    OpenAISDKDependencyError,
    OpenAISDKResponseError,
    build_openai_sdk_request,
    classify_openai_sdk_exception,
    reconstruct_openai_sdk_response,
)
from pastila_scout.provider_execution_openai_sdk_v2.models import (
    OpenAISDKMessageV2,
    OpenAISDKOutputV2,
    OpenAISDKResponseV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionMessageV2,
    OpenAIExecutionRequestV2,
)
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_openai_sdk_v2"
FINISHED_AT = datetime(2026, 8, 1, 12, tzinfo=UTC)


def _request() -> OpenAIExecutionRequestV2:
    return OpenAIExecutionRequestV2(
        execution_request_id="sdk-request",
        request_envelope_identity="scout:sdk-request:authority",
        model="gpt-contract-model",
        messages=(
            OpenAIExecutionMessageV2(role="system", content="System", ordinal=0),
            OpenAIExecutionMessageV2(role="user", content="User", ordinal=1),
        ),
        timeout_seconds=17.5,
        cancellation_requested=False,
        temperature=0.25,
        max_output_tokens=123,
        stop_sequences=("STOP",),
    )


def _sdk_response(*, reason: str = "stop") -> OpenAISDKResponseV2:
    return OpenAISDKResponseV2(
        response_id="response-id",
        model="gpt-contract-model",
        finished_at=FINISHED_AT,
        outputs=(OpenAISDKOutputV2(ordinal=0, text="Result", finish_reason=reason),),
    )


@dataclass
class _Capability:
    calls: int = 0

    def create(self, request):
        self.calls += 1
        return _sdk_response()


def test_public_api_is_exact_and_minimal() -> None:
    assert public_api.__all__ == (
        "OpenAISDKBoundaryError",
        "OpenAISDKCapabilityV2",
        "OpenAISDKClientV2",
        "OpenAISDKConfigurationError",
        "OpenAISDKDependencyError",
        "OpenAISDKRequestV2",
        "OpenAISDKResponseError",
        "build_openai_sdk_request",
        "classify_openai_sdk_exception",
        "reconstruct_openai_sdk_response",
    )


def test_package_dependency_direction_and_capability_absence() -> None:
    forbidden = {
        "openai",
        "httpx",
        "requests",
        "socket",
        "os",
        "dotenv",
        "logging",
        "asyncio",
        "threading",
        "subprocess",
        "time",
        "uuid",
        "random",
    }
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not imports & forbidden
        source = path.read_text(encoding="utf-8")
        assert "provider_composition_v2" not in source
        assert "OpenAI(" not in source


def test_verified_packages_do_not_reverse_import_sdk_boundary() -> None:
    for relative in (
        "provider_v2",
        "provider_execution_v2",
        "provider_execution_testing_v2",
        "provider_execution_openai_v2",
    ):
        for path in (ROOT / "src" / "pastila_scout" / relative).glob("*.py"):
            assert "provider_execution_openai_sdk_v2" not in path.read_text(
                encoding="utf-8"
            )


def test_constructor_requires_static_injected_capability_without_invocation() -> None:
    capability = _Capability()
    client = OpenAISDKClientV2(sdk_client=capability)

    assert client._sdk_client is capability
    assert capability.calls == 0

    with pytest.raises(TypeError):
        OpenAISDKClientV2()  # type: ignore[call-arg]
    with pytest.raises(OpenAISDKConfigurationError, match="capability"):
        OpenAISDKClientV2(object())  # type: ignore[arg-type]

    class WrongSignature:
        def create(self):
            return None

    with pytest.raises(OpenAISDKConfigurationError, match="capability"):
        OpenAISDKClientV2(WrongSignature())  # type: ignore[arg-type]


def test_constructor_rejects_descriptor_without_binding() -> None:
    class Descriptor:
        calls = 0

        def __get__(self, instance, owner):
            self.calls += 1
            return lambda request: None

    class DynamicCapability:
        create = Descriptor()

    descriptor = DynamicCapability.__dict__["create"]
    with pytest.raises(OpenAISDKConfigurationError):
        OpenAISDKClientV2(DynamicCapability())  # type: ignore[arg-type]
    assert descriptor.calls == 0


def test_complete_is_explicitly_deferred_without_capability_call() -> None:
    capability = _Capability()
    client = OpenAISDKClientV2(capability)

    with pytest.raises(OpenAISDKDependencyError, match="not implemented"):
        client.complete(_request())
    assert capability.calls == 0


def test_request_mapping_is_deterministic_ordered_and_non_mutating() -> None:
    request = _request()
    before = request.model_dump(mode="json")

    first = build_openai_sdk_request(request)
    second = build_openai_sdk_request(request)

    assert first == second
    assert tuple((item.role, item.content) for item in first.messages) == (
        ("system", "System"),
        ("user", "User"),
    )
    assert first.timeout_seconds == 17.5
    assert first.temperature == 0.25
    assert first.max_output_tokens == 123
    assert first.stop_sequences == ("STOP",)
    assert request.model_dump(mode="json") == before


def test_request_mapping_rejects_copied_invalid_authority() -> None:
    forged = _request().model_copy(update={"timeout_seconds": True})
    with pytest.raises(OpenAISDKBoundaryError, match="request authority"):
        build_openai_sdk_request(forged)


@pytest.mark.parametrize(
    "value",
    ("", " ", " gpt-5", "gpt-5 ", 1, True, b"gpt-5"),
)
def test_sdk_request_rejects_invalid_model_identifiers(value) -> None:
    with pytest.raises(ValueError, match="model identifier|validation error"):
        public_api.OpenAISDKRequestV2(
            model=value,
            messages=(OpenAISDKMessageV2(role="user", content="content"),),
            timeout_seconds=1,
        )


@pytest.mark.parametrize("value", ("", " ", "\t", "\n", 1, True, b"content"))
def test_sdk_message_rejects_invalid_content(value) -> None:
    with pytest.raises(ValueError, match="message content|validation error"):
        OpenAISDKMessageV2(role="user", content=value)


@pytest.mark.parametrize(
    "value",
    (
        ("",),
        (" ",),
        ("\t",),
        ("\n",),
        (" stop",),
        ("stop ",),
        ("stop", "stop"),
        (1,),
        (True,),
        (b"bytes",),
    ),
)
def test_sdk_request_rejects_invalid_stop_sequences(value) -> None:
    with pytest.raises(
        (TypeError, ValueError), match="stop sequences|validation error"
    ):
        public_api.OpenAISDKRequestV2(
            model="gpt-5",
            messages=(OpenAISDKMessageV2(role="user", content="content"),),
            timeout_seconds=1,
            stop_sequences=value,
        )


def test_sdk_request_defensively_copies_mutable_collections() -> None:
    messages = [OpenAISDKMessageV2(role="user", content="content")]
    stops = ["one", "two"]
    request = public_api.OpenAISDKRequestV2(
        model="gpt-5",
        messages=messages,
        timeout_seconds=1,
        stop_sequences=stops,
    )

    messages.clear()
    stops[0] = "changed"
    stops.clear()

    assert request.messages == (OpenAISDKMessageV2(role="user", content="content"),)
    assert request.stop_sequences == ("one", "two")


def test_sdk_text_preserves_meaningful_surrounding_whitespace() -> None:
    for text in ("hello", " hello ", "\nhello\n"):
        output = OpenAISDKOutputV2(ordinal=0, text=text, finish_reason="stop")
        assert output.text == text


@pytest.mark.parametrize("text", ("", " ", "   ", "\t", "\n", "\r\n"))
def test_sdk_output_rejects_empty_or_whitespace_only_text(text) -> None:
    with pytest.raises(ValueError, match="output text|validation error"):
        OpenAISDKOutputV2(ordinal=0, text=text, finish_reason="stop")


@pytest.mark.parametrize(
    "update",
    (
        {"model": " "},
        {"model": " gpt-5"},
        {
            "messages": (
                OpenAISDKMessageV2(role="user", content="content").model_copy(
                    update={"content": " "}
                ),
            )
        },
        {"stop_sequences": ("stop", "stop")},
        {"stop_sequences": (" ",)},
        {"stop_sequences": (1,)},
    ),
)
def test_sdk_request_revalidates_copied_invalid_state(update) -> None:
    valid = public_api.OpenAISDKRequestV2(
        model="gpt-5",
        messages=(OpenAISDKMessageV2(role="user", content="content"),),
        timeout_seconds=1,
    )
    forged = valid.model_copy(update=update)

    with pytest.raises((TypeError, ValueError)):
        public_api.OpenAISDKRequestV2.model_validate(forged)


@pytest.mark.parametrize(
    ("reason", "finish", "status", "category"),
    (
        (
            "stop",
            ProviderFinishReasonV2.COMPLETED,
            ProviderResultStatusV2.SUCCESS,
            None,
        ),
        ("length", ProviderFinishReasonV2.LENGTH, ProviderResultStatusV2.PARTIAL, None),
        (
            "content_filter",
            ProviderFinishReasonV2.CONTENT_FILTERED,
            ProviderResultStatusV2.PARTIAL,
            OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
        ),
    ),
)
def test_response_reconstruction(reason, finish, status, category) -> None:
    source = _sdk_response(reason=reason)
    result = reconstruct_openai_sdk_response(source)

    assert result.provider_request_id == "response-id"
    assert result.finished_at == FINISHED_AT
    assert result.status is status
    assert result.outputs[0].finish_reason is finish
    assert result.failure_category is category
    assert result is not source


@pytest.mark.parametrize(
    "value",
    (
        {"model": "gpt", "finished_at": FINISHED_AT, "outputs": []},
        {
            "response_id": "id",
            "model": "gpt",
            "finished_at": FINISHED_AT,
            "outputs": [
                {"ordinal": 0, "text": "a", "finish_reason": "stop"},
                {"ordinal": 0, "text": "b", "finish_reason": "stop"},
            ],
        },
        {
            "response_id": "id",
            "model": "gpt",
            "finished_at": FINISHED_AT,
            "outputs": [{"ordinal": 0, "text": "a", "finish_reason": "mystery"}],
        },
    ),
)
def test_response_reconstruction_rejects_malformed_shapes(value) -> None:
    with pytest.raises(OpenAISDKResponseError, match="invalid OpenAI SDK response"):
        reconstruct_openai_sdk_response(value)


def test_response_reconstruction_revalidates_copied_nested_values() -> None:
    forged_output = _sdk_response().outputs[0].model_copy(update={"text": ""})
    forged = _sdk_response().model_copy(update={"outputs": (forged_output,)})
    with pytest.raises(OpenAISDKResponseError):
        reconstruct_openai_sdk_response(forged)


@pytest.mark.parametrize(
    "update",
    (
        {"text": " "},
        {"text": ""},
        {"ordinal": -1},
        {"finish_reason": "unknown"},
    ),
)
def test_response_reconstruction_rejects_copied_invalid_outputs(update) -> None:
    forged_output = _sdk_response().outputs[0].model_copy(update=update)
    forged = _sdk_response().model_copy(update={"outputs": (forged_output,)})

    with pytest.raises(OpenAISDKResponseError, match="invalid OpenAI SDK response"):
        reconstruct_openai_sdk_response(forged)


@pytest.mark.parametrize(
    "update",
    (
        {"response_id": " "},
        {"model": " "},
        {
            "outputs": (
                OpenAISDKOutputV2(ordinal=0, text="one", finish_reason="stop"),
                OpenAISDKOutputV2(ordinal=0, text="two", finish_reason="stop"),
            )
        },
    ),
)
def test_response_reconstruction_rejects_copied_invalid_responses(update) -> None:
    forged = _sdk_response().model_copy(update=update)
    with pytest.raises(OpenAISDKResponseError, match="invalid OpenAI SDK response"):
        reconstruct_openai_sdk_response(forged)


def test_malformed_response_diagnostics_are_deterministic_and_value_safe() -> None:
    forged_output = _sdk_response().outputs[0].model_copy(update={"text": "secret"})
    messages = []
    for _ in range(2):
        forged = _sdk_response().model_copy(
            update={"outputs": (forged_output.model_copy(update={"text": " "}),)}
        )
        with pytest.raises(OpenAISDKResponseError) as raised:
            reconstruct_openai_sdk_response(forged)
        messages.append(str(raised.value))

    assert messages == ["invalid OpenAI SDK response"] * 2
    assert "secret" not in messages[0]


class _StatusError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.parametrize(
    ("error", "category"),
    (
        (_StatusError(401), OpenAIClientErrorCategoryV2.AUTHENTICATION),
        (_StatusError(429), OpenAIClientErrorCategoryV2.RATE_LIMITED),
        (TimeoutError("secret"), OpenAIClientErrorCategoryV2.TIMEOUT),
        (_StatusError(499), OpenAIClientErrorCategoryV2.CANCELLED),
        (_StatusError(400), OpenAIClientErrorCategoryV2.INVALID_REQUEST),
        (_StatusError(503), OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE),
        (
            RuntimeError("authentication rate limit timeout"),
            OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR,
        ),
        (
            OpenAISDKResponseError("raw response hidden"),
            OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE,
        ),
    ),
)
def test_exception_classification_uses_structure_not_text(error, category) -> None:
    assert classify_openai_sdk_exception(error) is category
