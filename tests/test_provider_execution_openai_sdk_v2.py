from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import FunctionType

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

import pastila_scout.provider_execution_openai_sdk_v2 as public_api
import pastila_scout.provider_execution_openai_sdk_v2.client as client_module
from pastila_scout.provider_execution_openai_sdk_v2 import (
    OpenAISDKBoundaryError,
    OpenAISDKCapabilityV2,
    OpenAISDKClientV2,
    OpenAISDKConfigurationError,
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


def _operational_request(*, stop_sequences=()) -> public_api.OpenAISDKRequestV2:
    return public_api.OpenAISDKRequestV2(
        model="gpt-contract-model",
        messages=(
            OpenAISDKMessageV2(role="system", content="System"),
            OpenAISDKMessageV2(role="user", content="User"),
        ),
        timeout_seconds=17.5,
        temperature=0.25,
        max_output_tokens=123,
        stop_sequences=stop_sequences,
    )


def _raw_response(*, status="completed", reason=None, text="Result"):
    return {
        "id": "response-id",
        "model": "gpt-contract-model",
        "created_at": FINISHED_AT.timestamp(),
        "status": status,
        "incomplete_details": None if reason is None else {"reason": reason},
        "output": [
            {
                "type": "message",
                "status": status,
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


@dataclass
class _RetryPolicy:
    max_retries: int = 0


@dataclass
class _Capability:
    response: object = field(default_factory=_raw_response)
    calls: list[dict[str, object]] = field(default_factory=list)
    _client: _RetryPolicy = field(default_factory=_RetryPolicy)

    def create(self, **arguments):
        self.calls.append(arguments)
        return self.response


def _seal_for_testing(
    dispatch: FunctionType, receiver: object, *, max_retries: object
) -> OpenAISDKCapabilityV2:
    if type(dispatch) is not FunctionType:
        raise OpenAISDKConfigurationError("invalid sealed dispatch authority")
    return OpenAISDKCapabilityV2(receiver, max_retries=max_retries)


def _client(resource: object, *, max_retries: object = 0) -> OpenAISDKClientV2:
    resource._client = _RetryPolicy(max_retries=max_retries)
    function = type.__getattribute__(type(resource), "__dict__")["create"]
    capability = _seal_for_testing(function, resource, max_retries=max_retries)
    return OpenAISDKClientV2(sdk_capability=capability)


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


def test_production_contains_no_registry_or_test_transport_state() -> None:
    source = (PACKAGE / "client.py").read_text(encoding="utf-8")
    for forbidden in (
        "_TRUSTED_CAPABILITIES",
        "_RegistryEntry",
        "TrustedTestTransport",
        "mint_trusted_capability_for_testing",
        "transport_attempts",
        "last_error",
        "last_request",
        "request_history",
        "exception_history",
    ):
        assert forbidden not in source


def test_revision_six_documentation_states_honest_trust_boundary() -> None:
    documentation = (
        ROOT / "docs" / "editorial-script-composer" / "Phase7_3_OpenAISDKBoundary.md"
    ).read_text(encoding="utf-8")
    for statement in (
        "In-process trust boundary",
        "exactly one adapter-level invocation",
        "does not claim exactly one SDK-internal or network",
        "must construct the official client with `max_retries=0`",
        "Python private names, frozen",
        "Production contains no authority registry",
    ):
        assert statement in documentation


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
    resource = _Capability()
    capability = _seal_for_testing(_Capability.create, resource, max_retries=0)
    client = OpenAISDKClientV2(sdk_capability=capability)

    assert client._sdk_capability is capability
    assert resource.calls == []

    with pytest.raises(TypeError):
        OpenAISDKClientV2()  # type: ignore[call-arg]
    with pytest.raises(OpenAISDKConfigurationError, match="capability"):
        OpenAISDKClientV2(object())  # type: ignore[arg-type]

    class WrongSignature:
        def create(self):
            return None

    with pytest.raises(OpenAISDKConfigurationError, match="Responses capability"):
        OpenAISDKCapabilityV2(WrongSignature(), max_retries=0)

    with pytest.raises(OpenAISDKConfigurationError, match="retries"):
        _client(resource, max_retries=1)


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
        OpenAISDKCapabilityV2(DynamicCapability(), max_retries=0)
    assert descriptor.calls == 0


def test_complete_invokes_responses_api_once_with_exact_arguments() -> None:
    resource = _Capability()
    client = _client(resource)

    result = client.complete(_operational_request())

    assert result.status is ProviderResultStatusV2.SUCCESS
    assert result.outputs[0].generated_text == "Result"
    assert len(resource.calls) == 1
    assert resource.calls[0] == {
        "model": "gpt-contract-model",
        "input": [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User"},
        ],
        "timeout": 17.5,
        "store": False,
        "stream": False,
        "background": False,
        "temperature": 0.25,
        "max_output_tokens": 123,
    }


def test_operational_client_rejects_invalid_request_and_stops_before_dispatch() -> None:
    resource = _Capability()
    client = _client(resource)
    forged = _operational_request().model_copy(update={"model": " "})

    with pytest.raises(OpenAISDKConfigurationError, match="request"):
        client.complete(forged)
    with pytest.raises(OpenAISDKConfigurationError, match="stop sequences"):
        client.complete(_operational_request(stop_sequences=("STOP",)))

    assert resource.calls == []


def test_operational_client_repeated_calls_are_exactly_once_each() -> None:
    resource = _Capability()
    client = _client(resource)

    results = tuple(client.complete(_operational_request()) for _ in range(3))

    assert len(resource.calls) == 3
    assert all(result.status is ProviderResultStatusV2.SUCCESS for result in results)


@pytest.mark.parametrize(
    ("status", "reason", "expected_status", "finish", "category"),
    (
        (
            "completed",
            None,
            ProviderResultStatusV2.SUCCESS,
            ProviderFinishReasonV2.COMPLETED,
            None,
        ),
        (
            "incomplete",
            "max_output_tokens",
            ProviderResultStatusV2.PARTIAL,
            ProviderFinishReasonV2.LENGTH,
            None,
        ),
        (
            "incomplete",
            "content_filter",
            ProviderResultStatusV2.PARTIAL,
            ProviderFinishReasonV2.CONTENT_FILTERED,
            OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
        ),
    ),
)
def test_operational_response_terminal_state_mapping(
    status, reason, expected_status, finish, category
) -> None:
    resource = _Capability(response=_raw_response(status=status, reason=reason))

    result = _client(resource).complete(_operational_request())

    assert result.status is expected_status
    assert result.outputs[0].finish_reason is finish
    assert result.failure_category is category
    assert result.finished_at == FINISHED_AT
    assert len(resource.calls) == 1


@pytest.mark.parametrize(
    "response",
    (
        {},
        _raw_response(status="mystery"),
        _raw_response(text=" "),
        {**_raw_response(), "output": [{"type": "tool_call", "content": []}]},
        {
            **_raw_response(),
            "output": [{"type": "message", "content": [{"type": "refusal"}]}],
        },
    ),
)
def test_operational_malformed_response_fails_after_one_call(response) -> None:
    resource = _Capability(response=response)

    with pytest.raises(
        OpenAISDKResponseError, match="invalid OpenAI SDK response"
    ) as raised:
        _client(resource).complete(_operational_request())

    assert len(resource.calls) == 1
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    ("status", "reason", "item_status", "marker"),
    (
        ("completed", "content_filter", "completed", None),
        ("completed", "max_output_tokens", "completed", None),
        ("completed", None, "incomplete", None),
        ("completed", None, "failed", None),
        ("incomplete", None, "incomplete", None),
        ("incomplete", "unknown", "incomplete", None),
        ("incomplete", "max_output_tokens", "completed", None),
        ("incomplete", "max_output_tokens", "incomplete", "content_filter"),
        ("incomplete", "content_filter", "completed", None),
        ("incomplete", "content_filter", "incomplete", "length"),
        ("failed", None, "failed", None),
        ("cancelled", None, "cancelled", None),
        ("in_progress", None, "in_progress", None),
        ("queued", None, "queued", None),
    ),
)
def test_operational_response_rejects_terminal_state_contradictions(
    status, reason, item_status, marker
) -> None:
    response = _raw_response(status=status, reason=reason)
    response["output"][0]["status"] = item_status
    if marker is not None:
        response["output"][0]["finish_reason"] = marker
    resource = _Capability(response=response)

    with pytest.raises(OpenAISDKResponseError, match="invalid OpenAI SDK response"):
        _client(resource).complete(_operational_request())

    assert len(resource.calls) == 1


@pytest.mark.parametrize(
    "value",
    (False, 0.0, "0", None, -1, 1, 2, type("IntSubclass", (int,), {})(0), object()),
)
def test_sealed_capability_rejects_non_exact_retry_zero(value) -> None:
    resource = _Capability()
    with pytest.raises(OpenAISDKConfigurationError, match="retries"):
        _seal_for_testing(_Capability.create, resource, max_retries=value)


def test_sealed_dispatch_ignores_nested_authority_replacements() -> None:
    resource = _Capability()
    replacement_calls = 0
    client = _client(resource)

    def replacement(**arguments):
        nonlocal replacement_calls
        replacement_calls += 1
        return _raw_response(text="replacement")

    resource.create = replacement
    resource._post = replacement
    resource._client = _RetryPolicy(2)

    result = client.complete(_operational_request())

    assert result.outputs[0].generated_text == "Result"
    assert len(resource.calls) == 1
    assert replacement_calls == 0


def test_operational_multiple_text_fragments_preserve_order() -> None:
    response = _raw_response()
    response["output"][0]["content"] = [
        {"type": "output_text", "text": "one"},
        {"type": "output_text", "text": " two "},
    ]
    resource = _Capability(response=response)

    result = _client(resource).complete(_operational_request())

    assert tuple(item.generated_text for item in result.outputs) == ("one", " two ")
    assert tuple(item.ordinal for item in result.outputs) == (0, 1)


class _StructuredSDKError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


def test_operational_exception_is_classified_without_text_and_without_retry() -> None:
    class RaisingResource:
        def __init__(self):
            self.calls = []

        def create(self, **arguments):
            self.calls.append(arguments)
            response = httpx.Response(429, request=httpx.Request("POST", "https://x"))
            raise RateLimitError("secret", response=response, body={"secret": True})

    resource = RaisingResource()

    with pytest.raises(OpenAISDKBoundaryError, match="client failure") as raised:
        _client(resource).complete(_operational_request())

    assert raised.value.category is OpenAIClientErrorCategoryV2.RATE_LIMITED
    assert str(raised.value) == "OpenAI SDK client failure"
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert len(resource.calls) == 1


def test_operational_exception_discards_secret_bearing_raw_object_graph() -> None:
    class SecretError(Exception):
        def __init__(self):
            super().__init__("api-key-secret")
            self.headers = {"Authorization": "Bearer secret"}
            self.body = {"prompt": "secret prompt"}
            self.transport = object()

        def __repr__(self):
            raise AssertionError("raw repr executed")

        def __str__(self):
            raise AssertionError("raw str executed")

    raw_error = SecretError()

    class RaisingResource:
        def __init__(self):
            self.calls = []

        def create(self, **arguments):
            self.calls.append(arguments)
            raise raw_error

    resource = RaisingResource()
    with pytest.raises(OpenAISDKBoundaryError) as raised:
        _client(resource).complete(_operational_request())

    error = raised.value
    assert str(error) == "OpenAI SDK client failure"
    assert error.category is OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR
    assert error.__context__ is None
    assert error.__cause__ is None
    assert raw_error not in error.args
    assert raw_error not in vars(error).values()
    assert raw_error not in vars(client_module).values()
    traceback = error.__traceback__
    adapter_frames = []
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("client.py"):
            adapter_frames.append(dict(traceback.tb_frame.f_locals))
        traceback = traceback.tb_next
    assert adapter_frames
    for local_values in adapter_frames:
        assert (
            not {
                "request",
                "arguments",
                "authority",
                "capability",
                "record",
                "raw_response",
                "error",
            }
            & local_values.keys()
        )
        assert raw_error not in local_values.values()
        assert "secret prompt" not in repr(local_values).lower()
    assert len(resource.calls) == 1


def test_provider_temperature_rejection_is_structured_without_fallback() -> None:
    class RejectingResource:
        def __init__(self):
            self.calls = []

        def create(self, **arguments):
            self.calls.append(arguments)
            response = httpx.Response(400, request=httpx.Request("POST", "https://x"))
            raise BadRequestError(
                "model rejects temperature",
                response=response,
                body={"prompt": "hidden"},
            )

    resource = RejectingResource()
    with pytest.raises(OpenAISDKBoundaryError) as raised:
        _client(resource).complete(_operational_request())

    assert raised.value.category is OpenAIClientErrorCategoryV2.INVALID_REQUEST
    assert raised.value.__context__ is None
    assert len(resource.calls) == 1
    assert resource.calls[0]["temperature"] == 0.25


@pytest.mark.parametrize(
    ("timestamp", "accepted"),
    (
        (0, True),
        (-1, True),
        (float("nan"), False),
        (float("inf"), False),
        (1e308, False),
        (True, False),
        ("0", False),
    ),
)
def test_operational_timestamp_policy_is_closed(timestamp, accepted) -> None:
    response = _raw_response()
    response["created_at"] = timestamp
    resource = _Capability(response=response)

    if accepted:
        result = _client(resource).complete(_operational_request())
        assert result.finished_at == datetime.fromtimestamp(timestamp, tz=UTC)
    else:
        with pytest.raises(OpenAISDKResponseError):
            _client(resource).complete(_operational_request())
    assert len(resource.calls) == 1


def test_pinned_responses_callable_resists_class_and_instance_replacement() -> None:
    class Resource:
        def __init__(self):
            self.original = 0
            self.replacement = 0

        def create(self, **arguments):
            self.original += 1
            return _raw_response()

    resource = Resource()
    resource._client = _RetryPolicy()
    capability = _seal_for_testing(Resource.__dict__["create"], resource, max_retries=0)
    original = Resource.__dict__["create"]

    def replacement(self, **arguments):
        self.replacement += 1
        return _raw_response(text="replacement")

    Resource.create = replacement
    resource.create = lambda **arguments: pytest.fail("instance shadow executed")
    result = OpenAISDKClientV2(capability).complete(_operational_request())
    Resource.create = original

    assert result.outputs[0].generated_text == "Result"
    assert resource.original == 1
    assert resource.replacement == 0


def test_capability_validation_ignores_forged_callable_metadata() -> None:
    from inspect import Parameter, Signature

    class Incompatible:
        def create(self):
            return _raw_response()

    Incompatible.create.__signature__ = Signature(  # type: ignore[attr-defined]
        (
            Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("kwargs", Parameter.VAR_KEYWORD),
        )
    )
    Incompatible.create.__wrapped__ = _Capability.create  # type: ignore[attr-defined]
    with pytest.raises(OpenAISDKConfigurationError):
        OpenAISDKCapabilityV2(Incompatible(), max_retries=0)

    class Compatible:
        def __init__(self):
            self._client = _RetryPolicy()

        def create(self, **arguments):
            return _raw_response()

    Compatible.create.__signature__ = Signature(())  # type: ignore[attr-defined]
    Compatible.create.__wrapped__ = Incompatible.create  # type: ignore[attr-defined]
    OpenAISDKCapabilityV2(Compatible(), max_retries=0)


def test_capability_rejects_custom_lookup_and_metaclass_without_execution() -> None:
    class LookupResource:
        def __init__(self):
            object.__setattr__(self, "lookups", 0)

        def __getattribute__(self, name):
            if name == "create":
                object.__setattr__(
                    self,
                    "lookups",
                    object.__getattribute__(self, "lookups") + 1,
                )
            return object.__getattribute__(self, name)

        def create(self, **arguments):
            return _raw_response()

    resource = LookupResource()
    with pytest.raises(OpenAISDKConfigurationError):
        OpenAISDKCapabilityV2(resource, max_retries=0)
    assert object.__getattribute__(resource, "lookups") == 0

    class Meta(type):
        lookups = 0

        def __getattribute__(cls, name):
            type.__setattr__(cls, "lookups", type.__getattribute__(cls, "lookups") + 1)
            return type.__getattribute__(cls, name)

    class MetaResource(metaclass=Meta):
        def create(self, **arguments):
            return _raw_response()

    type.__setattr__(MetaResource, "lookups", 0)
    with pytest.raises(OpenAISDKConfigurationError):
        OpenAISDKCapabilityV2(MetaResource(), max_retries=0)
    assert type.__getattribute__(MetaResource, "lookups") == 0


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


def _api_status_error(error_type, status):
    response = httpx.Response(status, request=httpx.Request("POST", "https://x"))
    return error_type("secret", response=response, body={"secret": True})


@pytest.mark.parametrize(
    ("error", "category"),
    (
        (
            _api_status_error(AuthenticationError, 401),
            OpenAIClientErrorCategoryV2.AUTHENTICATION,
        ),
        (
            _api_status_error(RateLimitError, 429),
            OpenAIClientErrorCategoryV2.RATE_LIMITED,
        ),
        (TimeoutError("secret"), OpenAIClientErrorCategoryV2.TIMEOUT),
        (
            APITimeoutError(httpx.Request("POST", "https://x")),
            OpenAIClientErrorCategoryV2.TIMEOUT,
        ),
        (
            _api_status_error(BadRequestError, 400),
            OpenAIClientErrorCategoryV2.INVALID_REQUEST,
        ),
        (
            _api_status_error(InternalServerError, 503),
            OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE,
        ),
        (
            APIConnectionError(request=httpx.Request("POST", "https://x")),
            OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE,
        ),
        (_StatusError(499), OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR),
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
