"""Strict immutable contracts for OpenAI runtime policy and composition."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError, dataclass
from inspect import iscoroutinefunction, signature
from types import FunctionType, MappingProxyType
from typing import TYPE_CHECKING, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)

from .errors import (
    OpenAIRuntimeConfigurationError,
    OpenAIRuntimeLifecycleError,
)

if TYPE_CHECKING:
    from pastila_scout.provider_execution_openai_sdk_v2 import OpenAISDKClientV2
    from pastila_scout.provider_execution_openai_v2 import OpenAIProviderExecutorV2


class OpenAIRuntimeConfigV2(BaseModel):
    """Safe startup policy; credentials and transport state are excluded."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    model: StrictStr
    enabled: StrictBool = True
    max_retries: StrictInt = 0
    request_timeout_seconds: StrictInt | StrictFloat = Field(gt=0)

    @field_validator("model", mode="before")
    @classmethod
    def validate_model(cls, value: object) -> object:
        if type(value) is not str or not value.strip() or value != value.strip():
            raise ValueError("invalid OpenAI runtime model")
        return value

    @field_validator("max_retries", mode="before")
    @classmethod
    def validate_retry_policy(cls, value: object) -> object:
        if type(value) is not int or value != 0:
            raise ValueError("OpenAI runtime retries must be disabled")
        return value

    @field_validator("request_timeout_seconds", mode="before")
    @classmethod
    def validate_timeout(cls, value: object) -> object:
        if type(value) not in {int, float} or not math.isfinite(value):
            raise ValueError("invalid OpenAI runtime timeout")
        return value


class _OpenAIRuntimeLifecycleOwnerV2:
    """Private single-threaded close-once owner for one runtime resource."""

    __slots__ = (
        "_closed",
        "_failure_function",
        "_function",
        "_receiver",
        "_success_function",
        "_transition_receiver",
    )

    def __init__(self, lifecycle: object) -> None:
        authority = _validated_close_authority(lifecycle)
        if authority is None:
            raise OpenAIRuntimeLifecycleError("invalid OpenAI runtime lifecycle")
        function, receiver = authority
        object.__setattr__(self, "_function", function)
        object.__setattr__(self, "_receiver", receiver)
        object.__setattr__(self, "_success_function", None)
        object.__setattr__(self, "_failure_function", None)
        object.__setattr__(self, "_transition_receiver", None)
        object.__setattr__(self, "_closed", False)

    @classmethod
    def _from_pinned(
        cls,
        function: FunctionType,
        receiver: object,
        success_function: FunctionType,
        failure_function: FunctionType,
        transition_receiver: object,
    ) -> _OpenAIRuntimeLifecycleOwnerV2:
        owner = object.__new__(cls)
        object.__setattr__(owner, "_function", function)
        object.__setattr__(owner, "_receiver", receiver)
        object.__setattr__(owner, "_success_function", success_function)
        object.__setattr__(owner, "_failure_function", failure_function)
        object.__setattr__(owner, "_transition_receiver", transition_receiver)
        object.__setattr__(owner, "_closed", False)
        return owner

    @property
    def closed(self) -> bool:
        return object.__getattribute__(self, "_closed")

    def close(self) -> None:
        outcome = self._close_and_sanitize()
        del self
        _return_or_raise_cleanup(outcome)

    def _close_and_sanitize(self) -> _SafeCleanupOutcome:
        if object.__getattribute__(self, "_closed"):
            return _SafeCleanupOutcome(False)
        object.__setattr__(self, "_closed", True)
        function = object.__getattribute__(self, "_function")
        receiver = object.__getattribute__(self, "_receiver")
        success_function = object.__getattribute__(self, "_success_function")
        failure_function = object.__getattribute__(self, "_failure_function")
        transition_receiver = object.__getattribute__(self, "_transition_receiver")
        failed = not _close_isolated(function, receiver)
        transition_function = failure_function if failed else success_function
        if transition_function is not None:
            _transition_isolated(transition_function, transition_receiver)
        object.__setattr__(self, "_function", None)
        object.__setattr__(self, "_receiver", None)
        object.__setattr__(self, "_success_function", None)
        object.__setattr__(self, "_failure_function", None)
        object.__setattr__(self, "_transition_receiver", None)
        del function
        del receiver
        del success_function
        del failure_function
        del transition_function
        del transition_receiver
        return _SafeCleanupOutcome(failed)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("OpenAI runtime lifecycle ownership is not serializable")

    def __setattr__(self, name: str, value: object) -> None:
        raise FrozenInstanceError("OpenAI runtime lifecycle ownership is immutable")

    def __delattr__(self, name: str) -> None:
        raise FrozenInstanceError("OpenAI runtime lifecycle ownership is immutable")

    def __repr__(self) -> str:
        return "_OpenAIRuntimeLifecycleOwnerV2(<private>)"


class OpenAIRuntimeCompositionV2:
    """Owned runtime boundary without credentials or raw SDK-client exposure."""

    __slots__ = ("_lifecycle", "executor", "sdk_client")

    sdk_client: OpenAISDKClientV2
    executor: OpenAIProviderExecutorV2
    _lifecycle: _OpenAIRuntimeLifecycleOwnerV2

    def __init__(
        self,
        sdk_client: object,
        executor: object,
        _lifecycle: object,
    ) -> None:
        from pastila_scout.provider_execution_openai_sdk_v2 import OpenAISDKClientV2
        from pastila_scout.provider_execution_openai_v2 import OpenAIProviderExecutorV2

        if type(sdk_client) is not OpenAISDKClientV2:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI runtime SDK client")
        if type(executor) is not OpenAIProviderExecutorV2:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI runtime executor")
        if object.__getattribute__(executor, "client") is not sdk_client:
            raise OpenAIRuntimeConfigurationError(
                "inconsistent OpenAI runtime composition"
            )
        if type(_lifecycle) is not _OpenAIRuntimeLifecycleOwnerV2:
            raise OpenAIRuntimeLifecycleError("invalid OpenAI runtime lifecycle")
        object.__setattr__(self, "sdk_client", sdk_client)
        object.__setattr__(self, "executor", executor)
        object.__setattr__(self, "_lifecycle", _lifecycle)

    @property
    def closed(self) -> bool:
        return self._lifecycle.closed

    def __repr__(self) -> str:
        return (
            "OpenAIRuntimeCompositionV2("
            "sdk_client=<OpenAISDKClientV2>, "
            "executor=<OpenAIProviderExecutorV2>, "
            f"closed={self.closed})"
        )

    def close(self) -> None:
        """Close the owned SDK client; the lifecycle contract is idempotent."""

        lifecycle = object.__getattribute__(self, "_lifecycle")
        outcome = lifecycle._close_and_sanitize()
        del lifecycle
        del self
        _return_or_raise_cleanup(outcome)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        lifecycle = object.__getattribute__(self, "_lifecycle")
        outcome = lifecycle._close_and_sanitize()
        del lifecycle
        del _
        del self
        _return_or_raise_cleanup(outcome)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("OpenAI runtime composition is not serializable")

    def __setattr__(self, name: str, value: object) -> None:
        raise FrozenInstanceError("OpenAI runtime composition is immutable")

    def __delattr__(self, name: str) -> None:
        raise FrozenInstanceError("OpenAI runtime composition is immutable")


@dataclass(frozen=True, slots=True)
class _SafeCleanupOutcome:
    failed: bool


def _validated_close_authority(value: object) -> tuple[FunctionType, object] | None:
    value_type = type(value)
    if type(value_type) is not type:
        return None
    hierarchy = type.__getattribute__(value_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return None
    if any(
        "__getattr__" in namespace
        or (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        )
        for namespace in namespaces
    ):
        return None
    for namespace in namespaces:
        if "close" not in namespace:
            continue
        function = namespace["close"]
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
        if iscoroutinefunction(clone):
            return None
        try:
            signature(clone, follow_wrapped=False).bind(value)
        except (TypeError, ValueError):
            return None
        return function, value
    return None


def _close_isolated(function: FunctionType, receiver: object) -> bool:
    """Exit the raw failure scope before the public lifecycle error is raised."""

    try:
        function(receiver)
    except Exception:  # noqa: BLE001 - injected lifecycles share no base
        return False
    return True


def _transition_isolated(function: FunctionType, receiver: object) -> None:
    try:
        function(receiver)
    except Exception:  # noqa: BLE001 - bookkeeping cannot trigger another close
        return


def _return_or_raise_cleanup(outcome: _SafeCleanupOutcome) -> None:
    if outcome.failed:
        error = OpenAIRuntimeLifecycleError("OpenAI runtime cleanup failed")
        try:
            raise error from None
        finally:
            error.__context__ = None
            error.__cause__ = None
            error.__suppress_context__ = True


__all__ = ("OpenAIRuntimeCompositionV2", "OpenAIRuntimeConfigV2")
