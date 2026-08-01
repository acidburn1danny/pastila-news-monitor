"""Injected OpenAI SDK capability shell; live dispatch is deferred."""

from dataclasses import dataclass, field
from inspect import signature
from types import FunctionType, MappingProxyType
from typing import Protocol, runtime_checkable

from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)

from .errors import (
    OpenAISDKConfigurationError,
    OpenAISDKDependencyError,
    OpenAISDKResponseError,
)
from .models import OpenAISDKRequestV2


@runtime_checkable
class OpenAISDKCapabilityV2(Protocol):
    """Narrow future one-shot SDK operation; retry policy is external."""

    def create(self, request: OpenAISDKRequestV2) -> object: ...


@dataclass(frozen=True, slots=True, init=False)
class OpenAISDKClientV2:
    """Non-operational client shell around an explicitly injected capability."""

    _sdk_client: OpenAISDKCapabilityV2 = field(repr=False)

    def __init__(self, sdk_client: OpenAISDKCapabilityV2) -> None:
        object.__setattr__(self, "_sdk_client", sdk_client)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not _has_static_create(self._sdk_client):
            raise OpenAISDKConfigurationError("invalid OpenAI SDK capability")

    def complete(self, request: OpenAIExecutionRequestV2) -> OpenAIExecutionResponseV2:
        """Defer dispatch until Revision 2; never fabricate provider output."""

        raise OpenAISDKDependencyError("OpenAI SDK dispatch is not implemented")


def _has_static_create(value: object) -> bool:
    client_type = type(value)
    if type(client_type) is not type:
        return False
    hierarchy = type.__getattribute__(client_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return False
    for namespace in namespaces:
        if "__getattr__" in namespace:
            return False
        if (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        ):
            return False
    for namespace in namespaces:
        if "create" in namespace:
            function = namespace["create"]
            if type(function) is not FunctionType:
                return False
            clone = FunctionType(
                function.__code__,
                function.__globals__,
                function.__name__,
                function.__defaults__,
                function.__closure__,
            )
            clone.__kwdefaults__ = function.__kwdefaults__
            try:
                signature(clone, follow_wrapped=False).bind(value, object())
            except (TypeError, ValueError):
                return False
            return True
    return False


def classify_openai_sdk_exception(error: BaseException) -> OpenAIClientErrorCategoryV2:
    """Classify structured status without inspecting exception text."""

    if isinstance(error, TimeoutError):
        return OpenAIClientErrorCategoryV2.TIMEOUT
    if isinstance(error, OpenAISDKResponseError):
        return OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE
    try:
        namespace = object.__getattribute__(error, "__dict__")
    except AttributeError:
        namespace = {}
    status = namespace.get("status_code") if type(namespace) is dict else None
    if status == 401:
        return OpenAIClientErrorCategoryV2.AUTHENTICATION
    if status == 408:
        return OpenAIClientErrorCategoryV2.TIMEOUT
    if status == 429:
        return OpenAIClientErrorCategoryV2.RATE_LIMITED
    if status == 499:
        return OpenAIClientErrorCategoryV2.CANCELLED
    if status in {400, 404, 409, 422}:
        return OpenAIClientErrorCategoryV2.INVALID_REQUEST
    if type(status) is int and 500 <= status <= 599:
        return OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE
    return OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR


__all__ = (
    "OpenAISDKCapabilityV2",
    "OpenAISDKClientV2",
    "classify_openai_sdk_exception",
)
