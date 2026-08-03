"""Offline bridge between verified OpenAI execution and SDK contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from types import FunctionType
from typing import Never, Self

from pydantic import ValidationError

from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionMessageV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)

from .errors import (
    OpenAIExecutionSDKBridgeConfigurationError,
    OpenAIExecutionSDKBridgeDependencyError,
)

_CONFIGURATION_MESSAGE = "invalid OpenAI execution-to-SDK bridge request"
_DEPENDENCY_MESSAGE = "OpenAI execution-to-SDK bridge dependency failure"
_SERIALIZATION_MESSAGE = "OpenAI execution SDK bridge clients cannot be serialized"


@dataclass(frozen=True, slots=True)
class _SafeFailure:
    category: str


class OpenAIExecutionSDKBridgeClientV2:
    """Pinned, immutable adapter over one exact frozen SDK client."""

    __slots__ = (
        "_complete_function",
        "_mapper_function",
        "_sdk_client",
        "_sdk_request_type",
    )

    def __init__(self, sdk_client: object = None) -> None:
        del sdk_client
        del self
        _raise_dependency_error()

    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        """Map and dispatch exactly once, returning a reconstructed response."""

        function = object.__getattribute__(self, "_complete_function")
        mapper = object.__getattribute__(self, "_mapper_function")
        receiver = object.__getattribute__(self, "_sdk_client")
        sdk_request_type = object.__getattribute__(self, "_sdk_request_type")
        del self
        try:
            outcome = _complete_isolated(
                function, mapper, receiver, sdk_request_type, request
            )
        finally:
            del function
            del mapper
            del receiver
            del sdk_request_type
            del request
        return _return_or_raise(outcome)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> Never:
        del self
        _raise_serialization_error()

    def __reduce_ex__(self, protocol: int) -> Never:
        del protocol
        del self
        _raise_serialization_error()

    def __getstate__(self) -> Never:
        del self
        _raise_serialization_error()

    def __setstate__(self, state: object) -> Never:
        del state
        del self
        _raise_serialization_error()

    def __setattr__(self, name: str, value: object) -> None:
        del name
        del value
        del self
        _raise_frozen_error()

    def __delattr__(self, name: str) -> None:
        del name
        del self
        _raise_frozen_error()

    def __repr__(self) -> str:
        return "OpenAIExecutionSDKBridgeClientV2()"

    __str__ = __repr__


def _complete_isolated(
    function: FunctionType,
    mapper: FunctionType,
    sdk_client: object,
    sdk_request_type: type[object],
    request: object,
) -> OpenAIExecutionResponseV2 | _SafeFailure:
    authority = _reconstruct_request(request)
    del request
    if authority is None:
        del function
        del mapper, sdk_client, sdk_request_type
        return _SafeFailure("configuration")
    if (
        authority.provider_id != "openai"
        or authority.cancellation_requested
        or authority.stop_sequences
    ):
        del authority
        del function
        del mapper, sdk_client, sdk_request_type
        return _SafeFailure("configuration")
    mapped = _map_sdk_request(mapper, sdk_request_type, authority)
    del authority
    del mapper
    del sdk_request_type
    if type(mapped) is _SafeFailure:
        del function
        del sdk_client
        return mapped
    sdk_request = mapped
    try:
        raw_response = function(sdk_client, sdk_request)
    except Exception:  # noqa: BLE001 - the frozen SDK boundary owns classification
        del sdk_request
        del function
        del sdk_client
        return _SafeFailure("dependency")
    except BaseException:
        del sdk_request
        del function
        del sdk_client
        raise
    del sdk_request
    del function
    del sdk_client
    response = _reconstruct_response(raw_response)
    del raw_response
    if response is None:
        return _SafeFailure("dependency")
    return response


def _reconstruct_request(value: object) -> OpenAIExecutionRequestV2 | None:
    if type(value) is not OpenAIExecutionRequestV2:
        return None
    try:
        messages = object.__getattribute__(value, "messages")
        if type(messages) is not tuple or any(
            type(item) is not OpenAIExecutionMessageV2 for item in messages
        ):
            return None
        dumped = OpenAIExecutionRequestV2.model_dump(
            value, mode="python", warnings="error"
        )
        reconstructed = OpenAIExecutionRequestV2.model_validate(dumped, strict=True)
        if type(reconstructed) is not OpenAIExecutionRequestV2 or any(
            type(item) is not OpenAIExecutionMessageV2
            for item in reconstructed.messages
        ):
            return None
        return reconstructed
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _map_sdk_request(
    mapper: FunctionType,
    sdk_request_type: type[object],
    value: OpenAIExecutionRequestV2,
) -> object | None:
    try:
        mapped = mapper(value)
        if type(mapped) is not sdk_request_type:
            return _SafeFailure("dependency")
        dumped = sdk_request_type.model_dump(mapped, mode="python", warnings="error")
        reconstructed = sdk_request_type.model_validate(dumped, strict=True)
        if type(reconstructed) is not sdk_request_type:
            return _SafeFailure("dependency")
        if reconstructed.model != value.model:
            return _SafeFailure("dependency")
        if reconstructed.timeout_seconds != value.timeout_seconds:
            return _SafeFailure("dependency")
        if reconstructed.temperature != value.temperature:
            return _SafeFailure("dependency")
        if reconstructed.max_output_tokens != value.max_output_tokens:
            return _SafeFailure("dependency")
        if reconstructed.stop_sequences != value.stop_sequences:
            return _SafeFailure("dependency")
        expected_messages = tuple((item.role, item.content) for item in value.messages)
        actual_messages = tuple(
            (item.role, item.content) for item in reconstructed.messages
        )
        if actual_messages != expected_messages:
            return _SafeFailure("dependency")
        return reconstructed
    except Exception:  # noqa: BLE001 - trusted mapper failures are dependencies
        return _SafeFailure("dependency")


def _reconstruct_response(value: object) -> OpenAIExecutionResponseV2 | None:
    if type(value) is not OpenAIExecutionResponseV2:
        return None
    try:
        outputs = object.__getattribute__(value, "outputs")
        if type(outputs) is not tuple or any(
            type(item) is not OpenAIExecutionOutputV2 for item in outputs
        ):
            return None
        dumped = OpenAIExecutionResponseV2.model_dump(
            value, mode="python", warnings="error"
        )
        reconstructed = OpenAIExecutionResponseV2.model_validate(dumped, strict=True)
        if type(reconstructed) is not OpenAIExecutionResponseV2:
            return None
        return reconstructed
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _return_or_raise(
    outcome: OpenAIExecutionResponseV2 | _SafeFailure,
) -> OpenAIExecutionResponseV2:
    if type(outcome) is OpenAIExecutionResponseV2:
        return outcome
    category = outcome.category
    del outcome
    if category == "configuration":
        _raise_configuration_error()
    _raise_dependency_error()


def _raise_configuration_error() -> Never:
    error = OpenAIExecutionSDKBridgeConfigurationError(_CONFIGURATION_MESSAGE)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_dependency_error() -> Never:
    error = OpenAIExecutionSDKBridgeDependencyError(_DEPENDENCY_MESSAGE)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error() -> Never:
    error = TypeError(_SERIALIZATION_MESSAGE)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_frozen_error() -> Never:
    error = FrozenInstanceError("OpenAI execution SDK bridge clients are immutable")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


__all__ = ("OpenAIExecutionSDKBridgeClientV2",)
