from __future__ import annotations

import ast
import copy
import json
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError, dataclass, field
from datetime import UTC, datetime
from functools import wraps
from inspect import signature
from pathlib import Path
from types import FunctionType

import pytest

import pastila_scout.provider_execution_openai_sdk_bridge_v2 as public_api
import pastila_scout.provider_execution_openai_sdk_bridge_v2.client as client_module
from pastila_scout.provider_execution_openai_sdk_bridge_v2 import (
    OpenAIExecutionSDKBridgeClientV2,
    OpenAIExecutionSDKBridgeConfigurationError,
    OpenAIExecutionSDKBridgeDependencyError,
    OpenAIExecutionSDKBridgeError,
)
from pastila_scout.provider_execution_openai_sdk_bridge_v2 import (
    bootstrap as bootstrap_module,
)
from pastila_scout.provider_execution_openai_sdk_v2 import (
    OpenAISDKCapabilityV2,
    OpenAISDKClientV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionMessageV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_openai_sdk_bridge_v2"
FINISHED_AT = datetime(2026, 8, 2, 12, tzinfo=UTC)
_DEFAULT_RESPONSE = object()


@dataclass
class _Responses:
    response: object
    calls: list[dict[str, object]] = field(default_factory=list)
    nested_call: object | None = None

    def create(self, **arguments: object) -> object:
        self.calls.append(arguments)
        nested = self.nested_call
        self.nested_call = None
        if nested is not None:
            nested()
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def _raw_response(
    *,
    status: str = "completed",
    reason: str | None = None,
    texts: tuple[str, ...] = ("Result",),
) -> dict[str, object]:
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
                "content": [{"type": "output_text", "text": text} for text in texts],
            }
        ],
    }


def _sdk_client(
    response: object = _DEFAULT_RESPONSE,
) -> tuple[OpenAISDKClientV2, _Responses]:
    receiver = _Responses(
        _raw_response() if response is _DEFAULT_RESPONSE else response
    )
    capability = OpenAISDKCapabilityV2(receiver, max_retries=0)
    return OpenAISDKClientV2(capability), receiver


def _request(
    *,
    cancellation_requested: bool = False,
    stop_sequences: tuple[str, ...] = (),
    timeout_seconds: float = 17.5,
) -> OpenAIExecutionRequestV2:
    return OpenAIExecutionRequestV2(
        execution_request_id="bridge-request",
        request_envelope_identity="scout:bridge-request:authority",
        model="gpt-contract-model",
        messages=(
            OpenAIExecutionMessageV2(
                role="system", content="  preserve this whitespace  ", ordinal=0
            ),
            OpenAIExecutionMessageV2(role="user", content="User", ordinal=1),
        ),
        timeout_seconds=timeout_seconds,
        cancellation_requested=cancellation_requested,
        temperature=0.25,
        max_output_tokens=123,
        stop_sequences=stop_sequences,
    )


def _bridge(response: object = _DEFAULT_RESPONSE):
    sdk_client, receiver = _sdk_client(response)
    return bootstrap_module._bootstrap_bridge(sdk_client), receiver


def test_public_api_is_exact_and_ordered() -> None:
    assert public_api.__all__ == (
        "OpenAIExecutionSDKBridgeClientV2",
        "OpenAIExecutionSDKBridgeError",
        "OpenAIExecutionSDKBridgeConfigurationError",
        "OpenAIExecutionSDKBridgeDependencyError",
    )
    assert (
        set(vars(public_api))
        & {
            "OpenAIExecutionRequestV2",
            "OpenAIExecutionResponseV2",
            "OpenAISDKClientV2",
            "OpenAISDKRequestV2",
            "build_openai_sdk_request",
        }
        == set()
    )
    assert issubclass(
        OpenAIExecutionSDKBridgeConfigurationError, OpenAIExecutionSDKBridgeError
    )
    assert issubclass(
        OpenAIExecutionSDKBridgeDependencyError, OpenAIExecutionSDKBridgeError
    )


@pytest.mark.parametrize(
    "module_name",
    [
        "pastila_scout.provider_execution_openai_sdk_bridge_v2",
        "pastila_scout.provider_execution_openai_sdk_bridge_v2.client",
        "pastila_scout.provider_execution_openai_sdk_bridge_v2.errors",
    ],
)
def test_passive_import_is_sdk_environment_and_openai_clean(module_name: str) -> None:
    script = f"""
import json
import os
import sys

relevant = {{
    'OPENAI_API_KEY',
    'AZURE_OPENAI_AD_TOKEN',
    'AZURE_OPENAI_ENDPOINT',
    'OPENAI_API_TYPE',
    'OPENAI_API_VERSION',
}}
reads = []
original_getitem = os._Environ.__getitem__
original_get = os._Environ.get

def tracked_getitem(self, key):
    if key in relevant or str(key).startswith('OPENAI_'):
        reads.append(str(key))
    return original_getitem(self, key)

def tracked_get(self, key, default=None):
    if key in relevant or str(key).startswith('OPENAI_'):
        reads.append(str(key))
    return original_get(self, key, default)

os._Environ.__getitem__ = tracked_getitem
os._Environ.get = tracked_get
__import__({module_name!r})
print(json.dumps({{
    'reads': reads,
    'openai': 'openai' in sys.modules,
    'sdk_package': 'pastila_scout.provider_execution_openai_sdk_v2' in sys.modules,
    'sdk_client': 'pastila_scout.provider_execution_openai_sdk_v2.client' in sys.modules,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    audit = json.loads(completed.stdout)
    assert audit == {
        "reads": [],
        "openai": False,
        "sdk_package": False,
        "sdk_client": False,
    }
    assert completed.stderr == ""


def test_explicit_bootstrap_retains_no_environment_marker_in_project_module() -> None:
    script = """
import json
import os

markers = {
    'OPENAI_LOG': 'BRIDGE_MARKER_LOG',
    'OPENAI_API_TYPE': 'BRIDGE_MARKER_TYPE',
    'OPENAI_API_VERSION': 'BRIDGE_MARKER_VERSION',
    'AZURE_OPENAI_ENDPOINT': 'BRIDGE_MARKER_ENDPOINT',
    'AZURE_OPENAI_AD_TOKEN': 'BRIDGE_MARKER_TOKEN',
}
os.environ.update(markers)
import pastila_scout.provider_execution_openai_sdk_bridge_v2.bootstrap as module
project_values = repr(tuple(vars(module).values()))
print(json.dumps({
    'retained': [value for value in markers.values() if value in project_values],
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {"retained": []}
    assert completed.stderr == ""


def test_explicit_bootstrap_accepts_exact_sdk_client_without_dispatch() -> None:
    bridge, receiver = _bridge()
    assert type(bridge) is OpenAIExecutionSDKBridgeClientV2
    assert receiver.calls == []


def test_repeated_bootstrap_reuses_authority_without_caching_clients() -> None:
    first_client, first_receiver = _sdk_client()
    second_client, second_receiver = _sdk_client()
    first = bootstrap_module._bootstrap_bridge(first_client)
    generation = bootstrap_module._AUTHORITY_GENERATION
    second = bootstrap_module._bootstrap_bridge(second_client)
    assert bootstrap_module._AUTHORITY_GENERATION is generation
    assert first is not second
    assert first_client is not second_client
    assert first_receiver.calls == second_receiver.calls == []
    assert generation is not None
    assert all(
        value is not first_client and value is not second_client
        for value in (
            generation.client_type,
            generation.complete_function,
            generation.mapper_function,
            generation.request_type,
        )
    )


def test_direct_construction_rejects_even_an_exact_sdk_client() -> None:
    sdk_client, receiver = _sdk_client()
    with pytest.raises(OpenAIExecutionSDKBridgeDependencyError):
        OpenAIExecutionSDKBridgeClientV2(sdk_client)
    assert receiver.calls == []


def test_no_argument_direct_construction_uses_fixed_dependency_error() -> None:
    with pytest.raises(
        OpenAIExecutionSDKBridgeDependencyError,
        match="^OpenAI execution-to-SDK bridge dependency failure$",
    ):
        OpenAIExecutionSDKBridgeClientV2()


def test_fabricated_mint_authority_cannot_bypass_bootstrap() -> None:
    forged_calls: list[object] = []
    dangerous_parameters = {
        "sdk_client",
        "complete_function",
        "mapper_function",
        "sdk_request_type",
        "authority",
    }
    discovered = {
        name: value
        for module in (client_module, bootstrap_module)
        for name, value in vars(module).items()
        if callable(value)
    }
    for value in discovered.values():
        try:
            parameters = set(signature(value, follow_wrapped=False).parameters)
        except (TypeError, ValueError):
            continue
        assert not dangerous_parameters <= parameters
    assert not hasattr(client_module, "_mint_bridge")
    assert not hasattr(client_module, "_BRIDGE_MINT_AUTHORITY")
    assert not hasattr(bootstrap_module, "_mint_bridge")
    assert not hasattr(bootstrap_module, "_BRIDGE_MINT_AUTHORITY")
    sdk_client, receiver = _sdk_client()
    bridge = bootstrap_module._bootstrap_bridge(sdk_client)
    assert type(bridge) is OpenAIExecutionSDKBridgeClientV2
    assert forged_calls == []
    assert receiver.calls == []


def test_explicit_bootstrap_import_failure_maps_to_fresh_safe_error(
    monkeypatch,
) -> None:
    sdk_client, receiver = _sdk_client()

    def broken_import(name):
        del name
        raise ImportError("private import path")

    monkeypatch.setattr(bootstrap_module, "import_module", broken_import)
    errors = []
    for _ in range(2):
        with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
            bootstrap_module._bootstrap_bridge(sdk_client)
        errors.append(captured.value)
    assert errors[0] is not errors[1]
    assert receiver.calls == []
    for error in errors:
        assert str(error) == "OpenAI execution-to-SDK bridge dependency failure"
        assert error.__context__ is None
        assert error.__cause__ is None
        assert error.__suppress_context__ is True


def test_bootstrap_failure_recursive_owned_graph_retains_no_call_state(
    monkeypatch,
) -> None:
    sdk_client, _ = _sdk_client()
    import_failure = RuntimeError("IMPORT_GRAPH_MARKER")
    caller_failure = ValueError("CALLER_GRAPH_MARKER")

    def broken_import(name):
        del name
        raise import_failure

    monkeypatch.setattr(bootstrap_module, "import_module", broken_import)
    try:
        raise caller_failure
    except ValueError:
        with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
            bootstrap_module._bootstrap_bridge(sdk_client)
    error = captured.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    pending: list[object] = [error, error.args, error.__traceback__]
    seen: set[int] = set()
    forbidden = (sdk_client, import_failure, caller_failure)
    while pending:
        value = pending.pop()
        if value is None or id(value) in seen:
            continue
        seen.add(id(value))
        assert all(value is not item for item in forbidden)
        if isinstance(value, BaseException):
            pending.extend((value.args, value.__context__, value.__cause__))
        elif isinstance(value, tuple | list | set | frozenset):
            pending.extend(value)
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif hasattr(value, "tb_frame"):
            frame = value.tb_frame
            if frame.f_globals.get("__name__", "").startswith(
                "pastila_scout.provider_execution_openai_sdk_bridge_v2"
            ):
                pending.extend(frame.f_locals.values())
            pending.append(value.tb_next)


@pytest.mark.parametrize("invalid", [None, object()])
def test_constructor_rejects_non_clients(invalid: object) -> None:
    with pytest.raises(
        OpenAIExecutionSDKBridgeDependencyError,
        match="^OpenAI execution-to-SDK bridge dependency failure$",
    ):
        OpenAIExecutionSDKBridgeClientV2(invalid)  # type: ignore[arg-type]


def test_constructor_rejects_sdk_client_subclass() -> None:
    class Derived(OpenAISDKClientV2):
        pass

    sdk_client, _ = _sdk_client()
    derived = object.__new__(Derived)
    object.__setattr__(
        derived,
        "_sdk_capability",
        object.__getattribute__(sdk_client, "_sdk_capability"),
    )
    with pytest.raises(OpenAIExecutionSDKBridgeDependencyError):
        OpenAIExecutionSDKBridgeClientV2(derived)


def test_representation_copy_immutability_and_pickle_policy() -> None:
    bridge, _ = _bridge()
    assert repr(bridge) == "OpenAIExecutionSDKBridgeClientV2()"
    assert str(bridge) == "OpenAIExecutionSDKBridgeClientV2()"
    assert copy.copy(bridge) is bridge
    assert copy.deepcopy(bridge) is bridge
    with pytest.raises(FrozenInstanceError):
        bridge.extra = object()  # type: ignore[attr-defined]
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(
            TypeError,
            match="^OpenAI execution SDK bridge clients cannot be serialized$",
        ):
            pickle.dumps(bridge, protocol=protocol)


def test_valid_request_is_mapped_once_with_exact_preservation() -> None:
    bridge, receiver = _bridge()
    result = bridge.complete(_request())
    assert type(result) is OpenAIExecutionResponseV2
    assert len(receiver.calls) == 1
    call = receiver.calls[0]
    assert call == {
        "model": "gpt-contract-model",
        "input": [
            {"role": "system", "content": "  preserve this whitespace  "},
            {"role": "user", "content": "User"},
        ],
        "timeout": 17.5,
        "store": False,
        "stream": False,
        "background": False,
        "temperature": 0.25,
        "max_output_tokens": 123,
    }


@pytest.mark.parametrize("timeout", [9, 9.5])
def test_integer_and_fractional_timeouts_are_preserved(timeout: float) -> None:
    bridge, receiver = _bridge()
    bridge.complete(_request(timeout_seconds=timeout))
    assert receiver.calls[0]["timeout"] == timeout
    assert type(receiver.calls[0]["timeout"]) is type(timeout)


@pytest.mark.parametrize(
    ("candidate", "mutation"),
    [
        (_request(cancellation_requested=True), None),
        (_request(stop_sequences=("STOP",)), None),
        (_request(), ("provider_id", "foreign")),
    ],
)
def test_compatibility_rejections_make_zero_sdk_calls(
    candidate: OpenAIExecutionRequestV2,
    mutation: tuple[str, object] | None,
) -> None:
    if mutation is not None:
        object.__setattr__(candidate, *mutation)
    bridge, receiver = _bridge()
    with pytest.raises(
        OpenAIExecutionSDKBridgeConfigurationError,
        match="^invalid OpenAI execution-to-SDK bridge request$",
    ):
        bridge.complete(candidate)
    assert receiver.calls == []


@pytest.mark.parametrize("invalid", [None, object()])
def test_hostile_request_shapes_are_rejected_without_dispatch(invalid: object) -> None:
    bridge, receiver = _bridge()
    with pytest.raises(OpenAIExecutionSDKBridgeConfigurationError):
        bridge.complete(invalid)  # type: ignore[arg-type]
    assert receiver.calls == []


def test_request_subclasses_and_copied_invalid_nested_messages_are_rejected() -> None:
    class DerivedRequest(OpenAIExecutionRequestV2):
        pass

    valid = _request()
    derived = DerivedRequest.model_validate(valid.model_dump())
    copied_invalid = _request()
    object.__setattr__(copied_invalid.messages[0], "ordinal", 9)
    for invalid in (derived, copied_invalid):
        bridge, receiver = _bridge()
        with pytest.raises(OpenAIExecutionSDKBridgeConfigurationError):
            bridge.complete(invalid)
        assert receiver.calls == []


@pytest.mark.parametrize(
    ("target", "field_name", "invalid"),
    [
        ("message", "role", "foreign"),
        ("message", "content", "   "),
        ("request", "timeout_seconds", 0),
        ("request", "temperature", float("inf")),
        ("request", "max_output_tokens", 0),
    ],
)
def test_each_copied_invalid_request_control_is_rejected_before_dispatch(
    target: str, field_name: str, invalid: object
) -> None:
    candidate = _request()
    owner = candidate.messages[0] if target == "message" else candidate
    object.__setattr__(owner, field_name, invalid)
    bridge, receiver = _bridge()
    with pytest.raises(OpenAIExecutionSDKBridgeConfigurationError):
        bridge.complete(candidate)
    assert receiver.calls == []


def test_private_mapping_result_is_exact_sdk_request() -> None:
    from pastila_scout.provider_execution_openai_sdk_v2 import (
        OpenAISDKRequestV2,
        build_openai_sdk_request,
    )

    mapped = client_module._map_sdk_request(
        build_openai_sdk_request, OpenAISDKRequestV2, _request()
    )
    assert type(mapped) is OpenAISDKRequestV2
    assert tuple((item.role, item.content) for item in mapped.messages) == (
        ("system", "  preserve this whitespace  "),
        ("user", "User"),
    )


@pytest.mark.parametrize(
    ("status", "reason", "expected_status", "expected_reason", "category"),
    [
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
    ],
)
def test_finish_and_status_semantics_are_preserved(
    status: str,
    reason: str | None,
    expected_status: ProviderResultStatusV2,
    expected_reason: ProviderFinishReasonV2,
    category: OpenAIClientErrorCategoryV2 | None,
) -> None:
    bridge, _ = _bridge(_raw_response(status=status, reason=reason))
    result = bridge.complete(_request())
    assert result.status is expected_status
    assert result.outputs[0].finish_reason is expected_reason
    assert result.failure_category is category
    assert result.provider_request_id == "response-id"
    assert result.model == "gpt-contract-model"
    assert result.finished_at == FINISHED_AT


def test_multiple_output_fragments_remain_ordered_and_untrimmed() -> None:
    bridge, _ = _bridge(_raw_response(texts=(" first ", "second")))
    result = bridge.complete(_request())
    assert tuple((item.ordinal, item.generated_text) for item in result.outputs) == (
        (0, " first "),
        (1, "second"),
    )


def test_copied_invalid_execution_response_and_nested_output_are_rejected() -> None:
    valid = OpenAIExecutionResponseV2(
        provider_request_id="response-id",
        model="gpt-contract-model",
        finished_at=FINISHED_AT,
        status=ProviderResultStatusV2.SUCCESS,
        outputs=(
            OpenAIExecutionOutputV2(
                ordinal=0,
                generated_text="Result",
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            ),
        ),
    )
    object.__setattr__(valid.outputs[0], "ordinal", 4)
    assert client_module._reconstruct_response(valid) is None


def test_error_graph_contains_no_request_or_sdk_dependency() -> None:
    secret = RuntimeError("secret")
    bridge, _ = _bridge(secret)
    candidate = _request()
    with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
        bridge.complete(candidate)
    pending = [captured.value]
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        assert value is not secret
        assert value is not candidate
        if isinstance(value, BaseException):
            pending.extend(
                item
                for item in (value.__context__, value.__cause__)
                if item is not None
            )


@pytest.mark.parametrize(
    "response",
    [
        None,
        object(),
        _raw_response(status="mystery"),
        _raw_response(texts=("   ",)),
    ],
)
def test_malformed_sdk_results_fail_once_without_retry(response: object) -> None:
    bridge, receiver = _bridge(response)
    with pytest.raises(
        OpenAIExecutionSDKBridgeDependencyError,
        match="^OpenAI execution-to-SDK bridge dependency failure$",
    ):
        bridge.complete(_request())
    assert len(receiver.calls) == 1


def test_ordinary_sdk_failure_is_isolated_and_safe() -> None:
    secret = RuntimeError("secret prompt and credential")
    bridge, receiver = _bridge(secret)
    try:
        raise ValueError("caller secret")
    except ValueError:
        with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
            bridge.complete(_request())
    error = captured.value
    assert str(error) == "OpenAI execution-to-SDK bridge dependency failure"
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert len(receiver.calls) == 1
    assert "secret" not in repr(error)


@pytest.mark.parametrize(
    "failure", [KeyboardInterrupt(), SystemExit(), GeneratorExit()]
)
def test_base_exceptions_propagate_unchanged(failure: BaseException) -> None:
    bridge, receiver = _bridge(failure)
    with pytest.raises(type(failure)) as captured:
        bridge.complete(_request())
    assert captured.value is failure
    assert len(receiver.calls) == 1


def test_repeated_calls_have_independent_one_call_state() -> None:
    bridge, receiver = _bridge()
    first = bridge.complete(_request())
    second = bridge.complete(_request(timeout_seconds=8))
    assert first is not second
    assert len(receiver.calls) == 2
    assert [item["timeout"] for item in receiver.calls] == [17.5, 8]


def test_reentrant_calls_are_independent() -> None:
    sdk_client, receiver = _sdk_client()
    bridge = bootstrap_module._bootstrap_bridge(sdk_client)
    nested_results: list[OpenAIExecutionResponseV2] = []
    receiver.nested_call = lambda: nested_results.append(
        bridge.complete(_request(timeout_seconds=3))
    )
    outer = bridge.complete(_request(timeout_seconds=7))
    assert type(outer) is OpenAIExecutionResponseV2
    assert len(nested_results) == 1
    assert [item["timeout"] for item in receiver.calls] == [7, 3]


def test_later_sdk_class_method_replacement_does_not_redirect(monkeypatch) -> None:
    bridge, receiver = _bridge()

    def replacement(self, request):
        raise AssertionError("replacement must not run")

    monkeypatch.setattr(OpenAISDKClientV2, "complete", replacement)
    result = bridge.complete(_request())
    assert type(result) is OpenAIExecutionResponseV2
    assert len(receiver.calls) == 1


def test_preconstruction_plain_function_replacement_is_rejected_and_restores() -> None:
    _bridge()
    sdk_client, receiver = _sdk_client()
    original = OpenAISDKClientV2.complete
    replacement_calls: list[object] = []

    def replacement(self, request):
        replacement_calls.append((self, request))
        return object()

    OpenAISDKClientV2.complete = replacement
    try:
        with pytest.raises(
            OpenAIExecutionSDKBridgeDependencyError,
            match="^OpenAI execution-to-SDK bridge dependency failure$",
        ) as captured:
            bootstrap_module._bootstrap_bridge(sdk_client)
    finally:
        OpenAISDKClientV2.complete = original
    assert replacement_calls == []
    assert receiver.calls == []
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True

    bridge = bootstrap_module._bootstrap_bridge(sdk_client)
    assert type(bridge.complete(_request())) is OpenAIExecutionResponseV2
    assert len(receiver.calls) == 1


def test_complete_authority_substitution_matrix_is_rejected_without_execution() -> None:
    _bridge()
    sdk_client, receiver = _sdk_client()
    original = OpenAISDKClientV2.complete
    calls: list[str] = []
    descriptor_calls: list[str] = []

    def compatible(self, request):
        calls.append("compatible")
        return object()

    def incompatible():
        calls.append("incompatible")
        return object()

    @wraps(original)
    def wrapped(self, request):
        calls.append("wrapped")
        return original(self, request)

    copied_code = FunctionType(
        original.__code__,
        original.__globals__,
        original.__name__,
        original.__defaults__,
        original.__closure__,
    )

    def copied_annotations(self, request):
        calls.append("annotations")
        return object()

    copied_annotations.__annotations__ = dict(original.__annotations__)

    def forged_signature(self, request):
        calls.append("signature")
        return object()

    forged_signature.__signature__ = "forged"  # type: ignore[attr-defined]

    def forged_wrapped(self, request):
        calls.append("forged-wrapped")
        return object()

    forged_wrapped.__wrapped__ = original  # type: ignore[attr-defined]

    class Descriptor:
        def __get__(self, instance, owner):
            descriptor_calls.append("descriptor")
            return compatible

    class CallableDescriptor:
        def __get__(self, instance, owner):
            descriptor_calls.append("callable-descriptor")
            return self

        def __call__(self, *args, **kwargs):
            calls.append("callable-descriptor")
            return object()

    class RaisingDescriptor:
        def __get__(self, instance, owner):
            descriptor_calls.append("raising-descriptor")
            raise AssertionError("descriptor must not execute")

    replacements = (
        compatible,
        incompatible,
        staticmethod(compatible),
        classmethod(compatible),
        property(lambda self: compatible),
        RaisingDescriptor(),
        Descriptor(),
        CallableDescriptor(),
        object(),
        wrapped,
        copied_code,
        copied_annotations,
        forged_signature,
        forged_wrapped,
    )
    errors = []
    try:
        for replacement in replacements:
            OpenAISDKClientV2.complete = replacement
            with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
                bootstrap_module._bootstrap_bridge(sdk_client)
            errors.append(captured.value)
    finally:
        OpenAISDKClientV2.complete = original
    assert len(errors) == len(replacements)
    assert len({id(error) for error in errors}) == len(errors)
    assert calls == []
    assert descriptor_calls == []
    assert receiver.calls == []


def test_mapper_module_replacement_cannot_redirect_trusted_anchor(monkeypatch) -> None:
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_module

    bridge, receiver = _bridge()
    replacement_calls: list[object] = []

    def replacement(request):
        replacement_calls.append(request)
        return object()

    monkeypatch.setattr(sdk_module, "build_openai_sdk_request", replacement)
    result = bridge.complete(_request())
    assert type(result) is OpenAIExecutionResponseV2
    assert replacement_calls == []
    assert len(receiver.calls) == 1


@pytest.mark.parametrize("mutation", ["package", "module", "both"])
def test_mapper_mutation_rejects_second_bootstrap_and_restoration_succeeds(
    mutation: str,
) -> None:
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_package
    import pastila_scout.provider_execution_openai_sdk_v2.mapping as mapping_module

    first, first_receiver = _bridge()
    second_client, second_receiver = _sdk_client()
    original_package = sdk_package.build_openai_sdk_request
    original_module = mapping_module.build_openai_sdk_request
    replacement_calls: list[object] = []

    def replacement(request):
        replacement_calls.append(request)
        return original_module(request)

    try:
        if mutation in {"package", "both"}:
            sdk_package.build_openai_sdk_request = replacement
        if mutation in {"module", "both"}:
            mapping_module.build_openai_sdk_request = replacement
        with pytest.raises(OpenAIExecutionSDKBridgeDependencyError):
            bootstrap_module._bootstrap_bridge(second_client)
        assert type(first.complete(_request())) is OpenAIExecutionResponseV2
    finally:
        sdk_package.build_openai_sdk_request = original_package
        mapping_module.build_openai_sdk_request = original_module
    restored = bootstrap_module._bootstrap_bridge(second_client)
    assert type(restored) is OpenAIExecutionSDKBridgeClientV2
    assert replacement_calls == []
    assert len(first_receiver.calls) == 1
    assert second_receiver.calls == []


def test_unexpected_trusted_mapper_failure_is_dependency_error(monkeypatch) -> None:
    def broken_mapper(request):
        del request
        raise RuntimeError("private project failure")

    bridge, receiver = _bridge()
    object.__setattr__(bridge, "_mapper_function", broken_mapper)
    with pytest.raises(
        OpenAIExecutionSDKBridgeDependencyError,
        match="^OpenAI execution-to-SDK bridge dependency failure$",
    ) as captured:
        bridge.complete(_request())
    assert receiver.calls == []
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_rejected_authority_isolated_from_active_nested_context() -> None:
    _bridge()
    sdk_client, _ = _sdk_client()
    original = OpenAISDKClientV2.complete
    repr_calls: list[str] = []

    class HostileError(RuntimeError):
        def __repr__(self):
            repr_calls.append("repr")
            return "hostile"

        def __str__(self):
            repr_calls.append("str")
            return "hostile"

    def replacement(self, request):
        return object()

    OpenAISDKClientV2.complete = replacement
    try:
        try:
            try:
                raise HostileError() from ValueError("caller cause")
            except HostileError:
                raise LookupError("outer caller")
        except LookupError:
            with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
                bootstrap_module._bootstrap_bridge(sdk_client)
    finally:
        OpenAISDKClientV2.complete = original
    error = captured.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert repr_calls == []


def test_rejected_authority_error_traceback_retains_no_client_or_replacement() -> None:
    _bridge()
    sdk_client, _ = _sdk_client()
    original = OpenAISDKClientV2.complete

    def replacement(self, request):
        return object()

    OpenAISDKClientV2.complete = replacement
    try:
        with pytest.raises(OpenAIExecutionSDKBridgeDependencyError) as captured:
            bootstrap_module._bootstrap_bridge(sdk_client)
    finally:
        OpenAISDKClientV2.complete = original
    traceback = captured.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").endswith(
            "provider_execution_openai_sdk_bridge_v2.client"
        ):
            values = tuple(traceback.tb_frame.f_locals.values())
            assert all(value is not sdk_client for value in values)
            assert all(value is not replacement for value in values)
            assert all(value is not original for value in values)
        traceback = traceback.tb_next


def test_private_anchors_are_identity_only_and_not_publicly_exported() -> None:
    _bridge()
    generation = bootstrap_module._AUTHORITY_GENERATION
    assert generation is not None
    assert generation.client_type is OpenAISDKClientV2
    assert generation.complete_function is OpenAISDKClientV2.complete
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_module

    assert generation.mapper_function is sdk_module.build_openai_sdk_request
    assert generation.request_type is sdk_module.OpenAISDKRequestV2
    assert not any(name.startswith("_TRUSTED_") for name in public_api.__all__)
    assert not hasattr(public_api, "_TRUSTED_COMPLETE")
    assert not hasattr(public_api, "_TRUSTED_MAPPER")


def test_forged_callable_metadata_is_ignored(monkeypatch) -> None:
    function = type.__getattribute__(OpenAISDKClientV2, "__dict__")["complete"]
    monkeypatch.setattr(function, "__signature__", "forged", raising=False)
    monkeypatch.setattr(function, "__wrapped__", object(), raising=False)
    bridge, receiver = _bridge()
    assert type(bridge.complete(_request())) is OpenAIExecutionResponseV2
    assert len(receiver.calls) == 1


def test_package_has_no_operational_capabilities_or_reverse_dependencies() -> None:
    forbidden_imports = {
        "argparse",
        "asyncio",
        "click",
        "dotenv",
        "httpx",
        "logging",
        "os",
        "requests",
        "socket",
        "subprocess",
        "threading",
        "time",
        "typer",
    }
    forbidden_text = {
        "OPENAI_API_KEY",
        "os.environ",
        "getenv",
        "OpenAI(",
        "responses.create",
        "AsyncOpenAI",
        "sleep(",
        "backoff",
        "telemetry",
        "persistence",
    }
    for path in PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
        assert not imports & forbidden_imports
        assert not any(marker in source for marker in forbidden_text)


def test_bridge_module_retains_no_request_or_response_global() -> None:
    import pastila_scout.provider_execution_openai_sdk_bridge_v2.client as module

    bridge, _ = _bridge()
    request = _request()
    response = bridge.complete(request)
    assert all(value is not request for value in vars(module).values())
    assert all(value is not response for value in vars(module).values())


def test_authority_generation_and_module_globals_retain_no_clients_or_bridges() -> None:
    first_client, _ = _sdk_client()
    second_client, _ = _sdk_client()
    first = bootstrap_module._bootstrap_bridge(first_client)
    second = bootstrap_module._bootstrap_bridge(second_client)
    generation = bootstrap_module._AUTHORITY_GENERATION
    assert generation is not None
    global_values = tuple(vars(bootstrap_module).values())
    for forbidden in (first_client, second_client, first, second):
        assert all(value is not forbidden for value in global_values)
        assert all(
            value is not forbidden
            for value in (
                generation.client_type,
                generation.complete_function,
                generation.mapper_function,
                generation.request_type,
            )
        )
