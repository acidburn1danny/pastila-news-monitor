"""Pinned synchronous Responses API capability with no client construction."""

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import signature
from types import FunctionType, MappingProxyType

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    UnprocessableEntityError,
)
from pydantic import ValidationError

from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionResponseV2,
)

from .errors import (
    OpenAISDKBoundaryError,
    OpenAISDKConfigurationError,
    OpenAISDKResponseError,
)
from .mapping import reconstruct_openai_sdk_response
from .models import OpenAISDKOutputV2, OpenAISDKRequestV2, OpenAISDKResponseV2


@dataclass(frozen=True, slots=True, init=False)
class OpenAISDKCapabilityV2:
    """Trusted-composition Responses operation pinned for adapter dispatch."""

    _function: FunctionType = field(repr=False)
    _receiver: object = field(repr=False)
    max_retries: int

    def __init__(self, responses: object, *, max_retries: object) -> None:
        if type(max_retries) is not int or max_retries != 0:
            raise OpenAISDKConfigurationError("OpenAI SDK retries must be disabled")
        authority = _validated_create_authority(responses)
        if authority is None:
            raise OpenAISDKConfigurationError("invalid OpenAI Responses capability")
        function, receiver = authority
        object.__setattr__(self, "_function", function)
        object.__setattr__(self, "_receiver", receiver)
        object.__setattr__(self, "max_retries", 0)

    def _invoke(self, **arguments: object) -> object:
        return self._function(self._receiver, **arguments)


@dataclass(frozen=True, slots=True, init=False)
class OpenAISDKClientV2:
    """Operational synchronous client over one pinned Responses API capability."""

    _sdk_capability: OpenAISDKCapabilityV2 = field(repr=False)

    def __init__(self, sdk_capability: OpenAISDKCapabilityV2) -> None:
        if type(sdk_capability) is not OpenAISDKCapabilityV2:
            raise OpenAISDKConfigurationError("invalid OpenAI SDK capability")
        object.__setattr__(self, "_sdk_capability", sdk_capability)

    def complete(self, request: OpenAISDKRequestV2) -> OpenAIExecutionResponseV2:
        """Invoke the pinned non-streaming Responses operation exactly once."""

        outcome = _execute_and_sanitize(self._sdk_capability, request)
        del request
        del self
        return _return_or_raise(outcome)


def _validated_create_authority(
    responses: object,
) -> tuple[FunctionType, object] | None:
    response_type = type(responses)
    if type(response_type) is not type:
        return None
    hierarchy = type.__getattribute__(response_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return None
    for namespace in namespaces:
        if "__getattr__" in namespace:
            return None
        if (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        ):
            return None
    for namespace in namespaces:
        if "create" not in namespace:
            continue
        function = namespace["create"]
        if type(function) is not FunctionType:
            return None
        clone = FunctionType(
            function.__code__,
            function.__globals__,
            function.__name__,
            function.__defaults__,
            function.__closure__,
        )
        clone.__kwdefaults__ = function.__kwdefaults__
        try:
            signature(clone, follow_wrapped=False).bind(
                responses,
                model="model",
                input=[],
                timeout=1.0,
                store=False,
                stream=False,
                background=False,
            )
        except (TypeError, ValueError):
            return None
        return function, responses
    return None


@dataclass(frozen=True, slots=True)
class _SafeExecutionFailure:
    code: str
    category: OpenAIClientErrorCategoryV2 | None = None


def _execute_and_sanitize(
    capability: OpenAISDKCapabilityV2,
    request: object,
) -> OpenAIExecutionResponseV2 | _SafeExecutionFailure:
    if type(capability) is not OpenAISDKCapabilityV2:
        return _SafeExecutionFailure("capability")
    authority = _validate_request_isolated(request)
    if authority is None:
        return _SafeExecutionFailure("request")
    if authority.stop_sequences:
        return _SafeExecutionFailure("stop")
    arguments: dict[str, object] = {
        "model": authority.model,
        "input": [
            {"role": item.role, "content": item.content} for item in authority.messages
        ],
        "timeout": authority.timeout_seconds,
        "store": False,
        "stream": False,
        "background": False,
    }
    if authority.temperature is not None:
        arguments["temperature"] = authority.temperature
    if authority.max_output_tokens is not None:
        arguments["max_output_tokens"] = authority.max_output_tokens
    invocation = _invoke_isolated(capability, arguments)
    if isinstance(invocation, _SafeInvocationFailure):
        return _SafeExecutionFailure("client", invocation.category)
    extraction = _extract_sdk_response_isolated(invocation)
    if isinstance(extraction, _SafeResponseFailure):
        return _SafeExecutionFailure("response")
    try:
        return reconstruct_openai_sdk_response(extraction)
    except OpenAISDKResponseError:
        return _SafeExecutionFailure("response")


def _return_or_raise(
    outcome: OpenAIExecutionResponseV2 | _SafeExecutionFailure,
) -> OpenAIExecutionResponseV2:
    if not isinstance(outcome, _SafeExecutionFailure):
        return outcome
    if outcome.code == "capability":
        raise OpenAISDKConfigurationError("invalid OpenAI SDK capability")
    if outcome.code == "request":
        raise OpenAISDKConfigurationError("invalid OpenAI SDK request")
    if outcome.code == "stop":
        raise OpenAISDKConfigurationError(
            "OpenAI Responses API does not support stop sequences"
        )
    if outcome.code == "response":
        raise OpenAISDKResponseError("invalid OpenAI SDK response")
    raise OpenAISDKBoundaryError(
        "OpenAI SDK client failure",
        category=outcome.category,
    )


@dataclass(frozen=True, slots=True)
class _SafeInvocationFailure:
    category: OpenAIClientErrorCategoryV2


def _validate_request_isolated(value: object) -> OpenAISDKRequestV2 | None:
    try:
        return OpenAISDKRequestV2.model_validate(value)
    except (TypeError, ValueError, ValidationError):
        return None


def _invoke_isolated(
    capability: OpenAISDKCapabilityV2,
    arguments: dict[str, object],
) -> object | _SafeInvocationFailure:
    """Discard raw SDK exceptions before returning safe invocation state."""

    try:
        return capability._invoke(**arguments)
    except Exception as error:  # noqa: BLE001 - SDK exceptions share no base
        category = classify_openai_sdk_exception(error)
    return _SafeInvocationFailure(category=category)


@dataclass(frozen=True, slots=True)
class _SafeResponseFailure:
    pass


def _extract_sdk_response(value: object) -> OpenAISDKResponseV2:
    extraction = _extract_sdk_response_isolated(value)
    if isinstance(extraction, _SafeResponseFailure):
        raise OpenAISDKResponseError("invalid OpenAI SDK response")
    return extraction


def _extract_sdk_response_isolated(
    value: object,
) -> OpenAISDKResponseV2 | _SafeResponseFailure:
    try:
        fields = _plain_fields(value)
        status = fields["status"]
        finish_reason = _finish_reason(status, fields.get("incomplete_details"))
        outputs = []
        for item in _required_list(fields.get("output")):
            item_fields = _plain_fields(item)
            if item_fields.get("type") != "message":
                raise ValueError("unsupported OpenAI response output item")
            if item_fields.get("status") != status:
                raise ValueError("contradictory OpenAI response output status")
            if any(
                marker in item_fields
                for marker in ("finish_reason", "incomplete_details", "error")
            ):
                raise ValueError("unsupported OpenAI response output marker")
            for content in _required_list(item_fields.get("content")):
                content_fields = _plain_fields(content)
                if content_fields.get("type") != "output_text":
                    raise ValueError("unsupported OpenAI response content item")
                outputs.append(
                    OpenAISDKOutputV2(
                        ordinal=len(outputs),
                        text=content_fields["text"],
                        finish_reason=finish_reason,
                    )
                )
        created_at = fields["created_at"]
        if type(created_at) not in {int, float} or not math.isfinite(created_at):
            raise ValueError("invalid OpenAI response timestamp")
        try:
            finished_at = datetime.fromtimestamp(created_at, tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            raise ValueError("invalid OpenAI response timestamp") from error
        return OpenAISDKResponseV2(
            response_id=fields["id"],
            model=fields["model"],
            finished_at=finished_at,
            outputs=tuple(outputs),
        )
    except (
        AttributeError,
        KeyError,
        OverflowError,
        OSError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return _SafeResponseFailure()


def _plain_fields(value: object) -> dict[str, object]:
    if type(value) is dict:
        return value
    fields = object.__getattribute__(value, "__dict__")
    if type(fields) is not dict:
        raise TypeError("unsupported SDK response object")
    return fields


def _required_list(value: object) -> list[object]:
    if type(value) is not list or not value:
        raise TypeError("missing SDK response collection")
    return value


def _finish_reason(status: object, incomplete_details: object) -> str:
    if status == "completed":
        if incomplete_details is not None:
            raise ValueError("completed response has incomplete details")
        return "stop"
    if status != "incomplete":
        raise ValueError("unknown OpenAI response status")
    details = _plain_fields(incomplete_details)
    reason = details.get("reason")
    mapping = {"max_output_tokens": "length", "content_filter": "content_filter"}
    try:
        return mapping[reason]
    except (KeyError, TypeError) as error:
        raise ValueError("unknown OpenAI incomplete reason") from error


def classify_openai_sdk_exception(error: BaseException) -> OpenAIClientErrorCategoryV2:
    """Classify structured status without inspecting exception text."""

    if isinstance(error, (TimeoutError, APITimeoutError)):
        return OpenAIClientErrorCategoryV2.TIMEOUT
    if isinstance(error, OpenAISDKResponseError):
        return OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE
    if isinstance(error, AuthenticationError):
        return OpenAIClientErrorCategoryV2.AUTHENTICATION
    if isinstance(error, RateLimitError):
        return OpenAIClientErrorCategoryV2.RATE_LIMITED
    if isinstance(
        error,
        (BadRequestError, NotFoundError, ConflictError, UnprocessableEntityError),
    ):
        return OpenAIClientErrorCategoryV2.INVALID_REQUEST
    if isinstance(error, (InternalServerError, APIConnectionError)):
        return OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE
    if isinstance(error, APIStatusError):
        status = error.status_code
        if status == 408:
            return OpenAIClientErrorCategoryV2.TIMEOUT
        if type(status) is int and 500 <= status <= 599:
            return OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE
    return OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR


__all__ = (
    "OpenAISDKCapabilityV2",
    "OpenAISDKClientV2",
    "classify_openai_sdk_exception",
)
