"""Private concrete dependencies for operational OpenAI runtime composition."""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from dataclasses import FrozenInstanceError, dataclass, field
from enum import Enum, auto
from importlib import import_module
from typing import Never, Self

from .composition import _mint_factory_handoff, _static_method_authority
from .errors import (
    OpenAIRuntimeCredentialError,
    OpenAIRuntimeDependencyError,
    OpenAIRuntimeLifecycleError,
)


class _ExplicitOpenAICredentialSourceV2:
    """Immutable identity source for one explicitly injected OpenAI API key."""

    __slots__ = ("_api_key",)

    def __init__(self, api_key: object) -> None:
        valid = _api_key_is_valid(api_key)
        if not valid:
            del api_key
            del self
            _raise_credential_error("invalid OpenAI credential")
        object.__setattr__(self, "_api_key", api_key)

    def get_api_key(self) -> str:
        return object.__getattribute__(self, "_api_key")

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
        return "_ExplicitOpenAICredentialSourceV2(<private>)"


class _EnvironmentOpenAICredentialSourceV2:
    """Stateless source that reads only OPENAI_API_KEY when explicitly invoked."""

    __slots__ = ()

    def get_api_key(self) -> str:
        outcome = _read_environment_credential_isolated()
        del self
        return _return_or_raise_credential_outcome(outcome)

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
        return "_EnvironmentOpenAICredentialSourceV2(<private>)"


class _OfficialOpenAISDKFactoryV2:
    """Stateless factory that constructs one official synchronous SDK client."""

    __slots__ = ()

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        outcome = _create_client_isolated(api_key, max_retries, request_timeout_seconds)
        del api_key
        del max_retries
        del request_timeout_seconds
        del self
        return _return_or_raise_factory_outcome(outcome)

    def close_client(self, client: object) -> None:
        """Close a client that remains under pre-handoff factory ownership."""

        outcome = _close_unclaimed_client(client)
        del client
        del self
        if outcome is not _CleanupOutcome.SUCCESS:
            _raise_dependency_error("OpenAI SDK cleanup failed")

    def __repr__(self) -> str:
        return "_OfficialOpenAISDKFactoryV2()"


class _CleanupOutcome(Enum):
    SUCCESS = auto()
    FAILED = auto()
    UNAVAILABLE = auto()


@dataclass(frozen=True, slots=True)
class _SafeSDKImportOutcome:
    constructor: Callable[..., object] | None = field(repr=False)
    failure_category: str | None


@dataclass(frozen=True, slots=True)
class _SafeConstructorOutcome:
    client: object | None = field(repr=False)
    failed: bool


@dataclass(frozen=True, slots=True)
class _SafeFactoryFailure:
    category: str
    message: str


@dataclass(frozen=True, slots=True)
class _SafeCredentialFailure:
    message: str


def _read_environment_credential_isolated() -> str | _SafeCredentialFailure:
    try:
        value = os.getenv("OPENAI_API_KEY")
    except Exception:  # noqa: BLE001 - process environment failures share no base
        return _SafeCredentialFailure("OpenAI credential retrieval failed")
    if value is None:
        return _SafeCredentialFailure("OpenAI environment credential is unavailable")
    if not _api_key_is_valid(value):
        del value
        return _SafeCredentialFailure("invalid OpenAI credential")
    return value


def _return_or_raise_credential_outcome(
    outcome: str | _SafeCredentialFailure,
) -> str:
    if type(outcome) is str:
        return outcome
    message = outcome.message
    del outcome
    _raise_credential_error(message)


def _create_client_isolated(
    api_key: object,
    max_retries: object,
    request_timeout_seconds: object,
) -> object | _SafeFactoryFailure:
    if not _api_key_is_valid(api_key):
        return _SafeFactoryFailure("dependency", "invalid OpenAI SDK credential")
    if type(max_retries) is not int or max_retries != 0:
        return _SafeFactoryFailure("dependency", "invalid OpenAI SDK retry policy")
    if not _timeout_is_valid(request_timeout_seconds):
        return _SafeFactoryFailure("dependency", "invalid OpenAI SDK timeout")
    imported = _load_openai_constructor()
    if imported.failure_category is not None:
        category = imported.failure_category
        del imported
        if category == "unavailable":
            return _SafeFactoryFailure("dependency", "OpenAI SDK is unavailable")
        if category == "incompatible":
            return _SafeFactoryFailure("dependency", "OpenAI SDK is incompatible")
        return _SafeFactoryFailure("dependency", "OpenAI SDK could not be loaded")
    constructor = imported.constructor
    del imported
    if constructor is None:
        return _SafeFactoryFailure("dependency", "OpenAI SDK is incompatible")
    constructed = _construct_client_isolated(
        constructor, api_key, request_timeout_seconds
    )
    del constructor
    del api_key
    del request_timeout_seconds
    if constructed.failed:
        del constructed
        return _SafeFactoryFailure("dependency", "OpenAI SDK construction failed")
    raw_client = constructed.client
    del constructed
    try:
        handoff = _mint_factory_handoff(raw_client)
    except Exception:  # noqa: BLE001 - factory retains pre-handoff ownership
        cleanup = _close_unclaimed_client(raw_client)
        del raw_client
        if cleanup is _CleanupOutcome.FAILED:
            return _SafeFactoryFailure("lifecycle", "OpenAI SDK cleanup failed")
        return _SafeFactoryFailure("dependency", "invalid OpenAI SDK client")
    del raw_client
    return handoff


def _load_openai_constructor() -> _SafeSDKImportOutcome:
    try:
        module = import_module("openai")
    except (ModuleNotFoundError, ImportError):
        return _SafeSDKImportOutcome(None, "unavailable")
    except Exception:  # noqa: BLE001 - broken SDK imports share no base
        return _SafeSDKImportOutcome(None, "load_failure")
    try:
        namespace = vars(module)
        constructor = namespace.get("OpenAI")
    except Exception:  # noqa: BLE001 - incompatible modules are untrusted
        return _SafeSDKImportOutcome(None, "incompatible")
    del namespace
    del module
    if not callable(constructor):
        del constructor
        return _SafeSDKImportOutcome(None, "incompatible")
    return _SafeSDKImportOutcome(constructor, None)


def _construct_client_isolated(
    constructor: Callable[..., object],
    api_key: str,
    request_timeout_seconds: float,
) -> _SafeConstructorOutcome:
    try:
        client = constructor(
            api_key=api_key,
            max_retries=0,
            timeout=request_timeout_seconds,
        )
    except Exception:  # noqa: BLE001 - constructor diagnostics remain private
        return _SafeConstructorOutcome(None, True)
    return _SafeConstructorOutcome(client, False)


def _close_unclaimed_client(client: object) -> _CleanupOutcome:
    function = _static_method_authority(client, "close", mode="raw_closer")
    if function is None:
        return _CleanupOutcome.UNAVAILABLE
    try:
        function(client)
    except Exception:  # noqa: BLE001 - raw cleanup diagnostics remain private
        return _CleanupOutcome.FAILED
    return _CleanupOutcome.SUCCESS


def _return_or_raise_factory_outcome(outcome: object | _SafeFactoryFailure) -> object:
    if type(outcome) is not _SafeFactoryFailure:
        return outcome
    category = outcome.category
    message = outcome.message
    del outcome
    if category == "lifecycle":
        error = OpenAIRuntimeLifecycleError(message)
    else:
        error = OpenAIRuntimeDependencyError(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _api_key_is_valid(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and bool(value.strip())
        and value == value.strip()
    )


def _timeout_is_valid(value: object) -> bool:
    if type(value) is int:
        return value > 0
    if type(value) is float:
        return math.isfinite(value) and value > 0.0
    return False


def _raise_credential_error(message: str) -> Never:
    error = OpenAIRuntimeCredentialError(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_dependency_error(message: str) -> Never:
    error = OpenAIRuntimeDependencyError(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error() -> Never:
    error = TypeError("OpenAI credential sources cannot be serialized")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_frozen_error() -> Never:
    error = FrozenInstanceError("OpenAI credential source is immutable")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


__all__: tuple[str, ...] = ()
