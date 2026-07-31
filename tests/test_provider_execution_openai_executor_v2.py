from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from inspect import Parameter, Signature
from pathlib import Path
from typing import ClassVar

import pytest

from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionConfigurationError,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutorV2,
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

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = (
    ROOT / "src" / "pastila_scout" / "provider_execution_openai_v2" / "executor.py"
)
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"
REQUESTED_AT = datetime(2026, 7, 31, 12, tzinfo=UTC)
FINISHED_AT = datetime(2026, 7, 31, 12, 1, tzinfo=UTC)


def _intent(*, units: int = 2) -> ProviderRequestIntentV2:
    return ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:executor",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:executor",
        draft_fingerprint=ZERO,
        request_units=tuple(
            ProviderRequestUnitInputV2(
                source_request_reference=f"source:{ordinal}",
                ordinal=ordinal,
                messages=(
                    ProviderMessageInputV2(
                        role="generation",
                        content=f"Conținut {ordinal}",
                        ordinal=0,
                    ),
                ),
            )
            for ordinal in range(units)
        ),
    )


def _request(*, cancelled: bool = False, units: int = 2) -> ProviderExecutionRequestV2:
    intent = _intent(units=units)
    descriptor = OpenAIProviderAdapter.descriptor
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id="request-executor",
            requested_at=REQUESTED_AT,
            cancellation=CancellationTokenV2(cancellation_requested=cancelled),
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=17.5),
    )


def _response(*, outputs: int = 2) -> OpenAIExecutionResponseV2:
    return OpenAIExecutionResponseV2(
        provider_request_id="provider-request",
        model="gpt-contract-model",
        finished_at=FINISHED_AT,
        status=ProviderResultStatusV2.SUCCESS,
        outputs=tuple(
            OpenAIExecutionOutputV2(
                ordinal=ordinal,
                generated_text=f"Rezultat {ordinal}",
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            )
            for ordinal in range(outputs)
        ),
    )


@dataclass
class _FixedClient:
    response: object
    calls: list[OpenAIExecutionRequestV2] = field(default_factory=list)

    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        self.calls.append(request)
        return self.response  # type: ignore[return-value]


@dataclass
class _RaisingClient:
    calls: list[OpenAIExecutionRequestV2] = field(default_factory=list)

    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        self.calls.append(request)
        raise RuntimeError("sensitive provider detail")


class _NonCallableClient:
    complete = "not-callable"


class _WrongSignatureClient:
    def complete(self) -> OpenAIExecutionResponseV2:
        return _response()


class _InheritedClient(_FixedClient):
    pass


class _OverriddenClient(_FixedClient):
    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        self.calls.append(request)
        return self.response  # type: ignore[return-value]


class _PropertyClient:
    def __init__(self) -> None:
        self.lookups = 0

    @property
    def complete(self):
        self.lookups += 1
        return lambda request: _response()


class _RaisingPropertyClient:
    @property
    def complete(self):
        raise RuntimeError("must not execute")


class _CachedPropertyClient:
    def __init__(self) -> None:
        self.lookups = 0

    @cached_property
    def complete(self):
        self.lookups += 1
        return lambda request: _response()


class _CallableDescriptor:
    def __init__(self) -> None:
        self.lookups = 0

    def __get__(self, instance, owner):
        self.lookups += 1
        return lambda request: _response()


class _DescriptorClient:
    complete = _CallableDescriptor()


class _NonCallableDescriptor:
    def __init__(self) -> None:
        self.lookups = 0

    def __get__(self, instance, owner):
        self.lookups += 1
        return "not-callable"


class _NonCallableDescriptorClient:
    complete = _NonCallableDescriptor()


class _GetattributeClient:
    def __init__(self) -> None:
        object.__setattr__(self, "lookups", 0)

    def __getattribute__(self, name):
        if name == "complete":
            object.__setattr__(
                self, "lookups", object.__getattribute__(self, "lookups") + 1
            )
        return object.__getattribute__(self, name)

    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        return _response()


class _GetattrClient:
    def __init__(self) -> None:
        self.lookups = 0

    def __getattr__(self, name):
        if name == "complete":
            self.lookups += 1
            return lambda request: _response()
        raise AttributeError(name)


class _GetattributeMetaclass(type):
    lookups = 0

    def __getattribute__(cls, name):
        if name in {"__mro__", "__dict__", "complete"}:
            type.__setattr__(
                cls,
                "lookups",
                type.__getattribute__(cls, "lookups") + 1,
            )
        return type.__getattribute__(cls, name)


class _GetattributeMetaclassClient(metaclass=_GetattributeMetaclass):
    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        return _response()


class _GetattrMetaclass(type):
    lookups = 0

    def __getattr__(cls, name):
        type.__setattr__(
            cls,
            "lookups",
            type.__getattribute__(cls, "lookups") + 1,
        )
        if name == "complete":
            return lambda request: _response()
        raise AttributeError(name)


class _GetattrMetaclassClient(metaclass=_GetattrMetaclass):
    pass


class _FakeCompleteMetaclass(type):
    lookups = 0

    def __getattribute__(cls, name):
        if name == "complete":
            type.__setattr__(
                cls,
                "lookups",
                type.__getattribute__(cls, "lookups") + 1,
            )
            return lambda request: _response()
        return type.__getattribute__(cls, name)


class _FakeCompleteMetaclassClient(metaclass=_FakeCompleteMetaclass):
    pass


class _StaticMethodClient:
    calls: ClassVar[list[OpenAIExecutionRequestV2]] = []

    @staticmethod
    def complete(
        request: OpenAIExecutionRequestV2,
    ) -> OpenAIExecutionResponseV2:
        _StaticMethodClient.calls.append(request)
        return _response()


class _ClassMethodClient:
    calls: ClassVar[list[OpenAIExecutionRequestV2]] = []

    @classmethod
    def complete(cls, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        cls.calls.append(request)
        return _response()


class _CompatibleWrongReturnAnnotationClient:
    def complete(self, request: OpenAIExecutionRequestV2) -> str:
        return "runtime response validation remains authoritative"


def _executor(client) -> OpenAIProviderExecutorV2:
    return OpenAIProviderExecutorV2(
        client=client,
        config=OpenAIExecutionConfigV2(
            model="gpt-contract-model",
            temperature=0,
            max_output_tokens=100,
            stop_sequences=("STOP",),
        ),
    )


def test_constructor_injects_valid_client_and_reconstructs_config() -> None:
    client = _FixedClient(_response())
    config = OpenAIExecutionConfigV2(model="gpt-contract-model")
    executor = OpenAIProviderExecutorV2(client=client, config=config)

    assert isinstance(executor, ProviderExecutorV2)
    assert executor.client is client
    assert executor.config == config
    assert executor.config is not config
    assert client.calls == []


@pytest.mark.parametrize(
    "client", (None, object(), _NonCallableClient(), _WrongSignatureClient())
)
def test_constructor_rejects_structurally_invalid_client(client) -> None:
    with pytest.raises(ExecutionConfigurationError, match="client"):
        OpenAIProviderExecutorV2(
            client=client,  # type: ignore[arg-type]
            config=OpenAIExecutionConfigV2(model="gpt-contract-model"),
        )


@pytest.mark.parametrize(
    "client",
    (
        _PropertyClient(),
        _RaisingPropertyClient(),
        _CachedPropertyClient(),
        _DescriptorClient(),
        _NonCallableDescriptorClient(),
        _GetattributeClient(),
        _GetattrClient(),
    ),
)
def test_constructor_rejects_dynamic_lifecycle_without_executing_client_code(
    client,
) -> None:
    before = getattr(client, "lookups", 0)

    with pytest.raises(ExecutionConfigurationError, match="client"):
        _executor(client)

    assert getattr(client, "lookups", 0) == before == 0
    descriptor = vars(type(client)).get("complete")
    if isinstance(descriptor, (_CallableDescriptor, _NonCallableDescriptor)):
        assert descriptor.lookups == 0


@pytest.mark.parametrize(
    "client_type",
    (
        _GetattributeMetaclassClient,
        _GetattrMetaclassClient,
        _FakeCompleteMetaclassClient,
    ),
)
def test_constructor_rejects_custom_metaclass_without_executing_lookup(
    client_type,
) -> None:
    type.__setattr__(client_type, "lookups", 0)

    with pytest.raises(ExecutionConfigurationError, match="client"):
        _executor(client_type())

    assert type.__getattribute__(client_type, "lookups") == 0


@pytest.mark.parametrize("client_type", (_InheritedClient, _OverriddenClient))
def test_constructor_accepts_inherited_and_overridden_instance_methods(
    client_type,
) -> None:
    client = client_type(_response())

    executor = _executor(client)

    assert executor.client is client
    assert client.calls == []


def test_client_lifecycle_is_first_invoked_only_during_execute() -> None:
    client = _OverriddenClient(_response())
    executor = _executor(client)

    assert client.calls == []
    result = executor.execute(_request())

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert len(client.calls) == 1


@pytest.mark.parametrize("client_type", (_StaticMethodClient, _ClassMethodClient))
def test_constructor_accepts_static_and_class_method_shapes(client_type) -> None:
    client_type.calls.clear()
    executor = _executor(client_type())

    assert client_type.calls == []
    result = executor.execute(_request())

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert len(client_type.calls) == 1


def test_constructor_preserves_revision_7_return_annotation_behavior() -> None:
    executor = _executor(_CompatibleWrongReturnAnnotationClient())

    result = executor.execute(_request())

    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "openai-malformed-response"


def test_constructor_ignores_forged_signature_metadata() -> None:
    class IncompatibleClient:
        def complete(self) -> OpenAIExecutionResponseV2:
            return _response()

    IncompatibleClient.complete.__signature__ = Signature(  # type: ignore[attr-defined]
        (
            Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD),
        )
    )
    with pytest.raises(ExecutionConfigurationError, match="client"):
        _executor(IncompatibleClient())

    class CompatibleClient:
        def complete(self, request) -> OpenAIExecutionResponseV2:
            return _response()

    CompatibleClient.complete.__signature__ = Signature(  # type: ignore[attr-defined]
        (Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),)
    )
    assert _executor(CompatibleClient()).client.__class__ is CompatibleClient


def test_constructor_ignores_wrapped_metadata_without_executing_wrapped_body() -> None:
    wrapped_calls = 0

    def compatible_wrapped(self, request):
        nonlocal wrapped_calls
        wrapped_calls += 1
        return _response()

    class IncompatibleClient:
        def complete(self):
            return _response()

    IncompatibleClient.complete.__wrapped__ = compatible_wrapped  # type: ignore[attr-defined]
    compatible_wrapped.__wrapped__ = IncompatibleClient.complete
    with pytest.raises(ExecutionConfigurationError, match="client"):
        _executor(IncompatibleClient())
    assert wrapped_calls == 0

    class CompatibleClient:
        def complete(self, request):
            return _response()

    def incompatible_wrapped():
        nonlocal wrapped_calls
        wrapped_calls += 1

    CompatibleClient.complete.__wrapped__ = incompatible_wrapped  # type: ignore[attr-defined]
    incompatible_wrapped.__wrapped__ = object()  # type: ignore[attr-defined]
    executor = _executor(CompatibleClient())
    assert wrapped_calls == 0
    assert executor.execute(_request()).outcome is ExecutionOutcomeV2.COMPLETED
    assert wrapped_calls == 0


def test_pinned_instance_method_resists_class_replacement_and_deletion() -> None:
    class Client:
        def __init__(self) -> None:
            self.original_calls = 0

        def complete(self, request):
            self.original_calls += 1
            return _response()

    class ReplacementDescriptor:
        def __init__(self) -> None:
            self.lookups = 0

        def __get__(self, instance, owner):
            self.lookups += 1
            raise RuntimeError("replacement must not bind")

    replacements = (
        lambda self, request: pytest.fail("replacement method executed"),
        property(lambda self: pytest.fail("replacement property executed")),
        ReplacementDescriptor(),
        lambda: pytest.fail("wrong-signature replacement executed"),
        object(),
    )
    original = Client.__dict__["complete"]
    for replacement in replacements:
        Client.complete = original
        client = Client()
        executor = _executor(client)
        Client.complete = replacement  # type: ignore[assignment]

        result = executor.execute(_request())

        assert result.outcome is ExecutionOutcomeV2.COMPLETED
        assert client.original_calls == 1
        if isinstance(replacement, ReplacementDescriptor):
            assert replacement.lookups == 0

    Client.complete = original
    client = Client()
    executor = _executor(client)
    del Client.complete
    assert executor.execute(_request()).outcome is ExecutionOutcomeV2.COMPLETED
    assert client.original_calls == 1


def test_pinned_instance_method_resists_instance_shadowing() -> None:
    class Client:
        def __init__(self) -> None:
            self.original_calls = 0

        def complete(self, request):
            self.original_calls += 1
            return _response()

    class Replacement:
        def __init__(self) -> None:
            object.__setattr__(self, "observations", 0)

        def __getattribute__(self, name):
            object.__setattr__(
                self,
                "observations",
                object.__getattribute__(self, "observations") + 1,
            )
            return object.__getattribute__(self, name)

        def __call__(self, request):
            pytest.fail("instance replacement executed")

    replacements = (
        Replacement(),
        lambda request: pytest.fail("shadow executed"),
        object(),
    )
    for replacement in replacements:
        client = Client()
        executor = _executor(client)
        client.complete = replacement  # type: ignore[method-assign]

        result = executor.execute(_request())

        assert result.outcome is ExecutionOutcomeV2.COMPLETED
        assert client.original_calls == 1
        if isinstance(replacement, Replacement):
            assert object.__getattribute__(replacement, "observations") == 0


def test_constructor_rejects_none_and_copied_invalid_config_without_client_call() -> (
    None
):
    client = _FixedClient(_response())
    with pytest.raises(ExecutionConfigurationError, match="configuration"):
        OpenAIProviderExecutorV2(client=client, config=None)  # type: ignore[arg-type]
    forged = OpenAIExecutionConfigV2(model="gpt").model_copy(update={"model": " "})
    with pytest.raises(ExecutionConfigurationError, match="configuration"):
        OpenAIProviderExecutorV2(client=client, config=forged)
    assert client.calls == []


def test_success_executes_once_and_preserves_exact_mapping_and_inputs() -> None:
    response = _response()
    client = _FixedClient(response)
    executor = _executor(client)
    request = _request()
    snapshots = (
        request.model_dump(mode="json"),
        executor.config.model_dump(mode="json"),
        response.model_dump(mode="json"),
    )

    result = executor.execute(request)

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.finished_at == FINISHED_AT
    assert len(client.calls) == 1
    sent = client.calls[0]
    assert sent.execution_request_id == request.context.request_id
    assert sent.request_envelope_identity == request.request_envelope.identity
    assert sent.timeout_seconds == 17.5
    assert sent.cancellation_requested is False
    assert tuple(item.content for item in sent.messages) == (
        "Conținut 0",
        "Conținut 1",
    )
    assert snapshots == (
        request.model_dump(mode="json"),
        executor.config.model_dump(mode="json"),
        response.model_dump(mode="json"),
    )


def test_repeated_execution_call_count_and_results_are_deterministic() -> None:
    client = _FixedClient(_response())
    executor = _executor(client)
    request = _request()

    results = tuple(executor.execute(request) for _ in range(3))

    assert tuple(range(1, len(client.calls) + 1)) == (1, 2, 3)
    assert results[0] == results[1] == results[2]
    assert client.calls[0] == client.calls[1] == client.calls[2]


def test_pre_dispatch_cancellation_returns_without_mapping_or_client_call() -> None:
    client = _FixedClient(_response())
    result = _executor(client).execute(_request(cancelled=True))

    assert result.outcome is ExecutionOutcomeV2.CANCELLED
    assert result.finished_at == REQUESTED_AT
    assert result.failure_code == "openai-pre-dispatch-cancelled"
    assert client.calls == []


def test_invalid_copied_request_raises_before_client_call() -> None:
    client = _FixedClient(_response())
    valid = _request()
    forged = valid.model_copy(
        update={
            "timeout_policy": valid.timeout_policy.model_copy(
                update={"timeout_seconds": True}
            )
        }
    )

    with pytest.raises(ExecutionConfigurationError, match="request"):
        _executor(client).execute(forged)
    assert client.calls == []


def test_client_exception_maps_to_internal_failure_without_retry_or_leakage() -> None:
    client = _RaisingClient()
    result = _executor(client).execute(_request())

    assert len(client.calls) == 1
    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "openai-client-contract-failure"
    assert result.failure_message == "The injected OpenAI client failed."
    assert "sensitive" not in result.failure_message
    assert result.finished_at == REQUESTED_AT


@pytest.mark.parametrize("response", (None, object(), {"invalid": "response"}))
def test_malformed_client_response_maps_to_deterministic_internal_failure(
    response,
) -> None:
    client = _FixedClient(response)
    result = _executor(client).execute(_request())

    assert len(client.calls) == 1
    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "openai-malformed-response"
    assert result.failure_message == (
        "The injected OpenAI client returned an invalid response."
    )


def test_copied_invalid_response_maps_to_internal_failure_without_mutation() -> None:
    response = _response().model_copy(update={"model": " "})
    before = response.model_dump(mode="json")
    client = _FixedClient(response)

    result = _executor(client).execute(_request())

    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "openai-malformed-response"
    assert response.model_dump(mode="json") == before
    assert len(client.calls) == 1


def test_projection_failure_maps_to_internal_failure_without_retry() -> None:
    response = _response(outputs=1)
    before = response.model_dump(mode="json")
    client = _FixedClient(response)

    result = _executor(client).execute(_request(units=2))

    assert result.outcome is ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    assert result.failure_code == "openai-response-projection-failure"
    assert result.failure_message == "The OpenAI response could not be projected."
    assert response.model_dump(mode="json") == before
    assert len(client.calls) == 1


def test_executor_has_no_hidden_operational_capabilities() -> None:
    tree = ast.parse(EXECUTOR.read_text(encoding="utf-8"))
    forbidden_imports = {
        "openai",
        "httpx",
        "requests",
        "aiohttp",
        "urllib",
        "socket",
        "ssl",
        "os",
        "dotenv",
        "logging",
        "sqlite3",
        "threading",
        "asyncio",
        "random",
        "uuid",
        "time",
    }
    imports = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imports & forbidden_imports
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "complete" not in calls
    assert not calls & {"connect", "close", "login", "authenticate", "sleep"}
