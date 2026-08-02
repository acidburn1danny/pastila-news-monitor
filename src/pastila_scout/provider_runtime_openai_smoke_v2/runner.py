"""Descriptor-safe injected orchestration for the offline smoke boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from inspect import (
    Parameter,
    getattr_static,
    isasyncgenfunction,
    iscoroutinefunction,
    isgeneratorfunction,
    signature,
)
from types import FunctionType, MappingProxyType
from typing import Never, Self

from pydantic import ValidationError

from .errors import (
    OpenAISmokeTestConfigurationError,
    OpenAISmokeTestConfirmationError,
    OpenAISmokeTestDependencyError,
    OpenAISmokeTestError,
)
from .interface import _CredentialSourceV2, _RuntimeComposerV2
from .models import OpenAISmokeTestConfigurationV2, OpenAISmokeTestResultV2


class OpenAISmokeTestRunnerV2:
    """Immutable holder of two statically pinned injected authorities."""

    __slots__ = ("_composer_authority", "_credential_authority")

    def __init__(
        self,
        credential_source: _CredentialSourceV2,
        runtime_composer: _RuntimeComposerV2,
    ) -> None:
        credential_authority = _pin_method(credential_source, "get_api_key", "zero")
        composer_authority = _pin_method(runtime_composer, "compose", "compose")
        if credential_authority is None or composer_authority is None:
            del credential_authority
            del composer_authority
            del credential_source
            del runtime_composer
            del self
            _raise_invalid_dependency()
        object.__setattr__(self, "_credential_authority", credential_authority)
        object.__setattr__(self, "_composer_authority", composer_authority)

    def run(self, configuration: object) -> OpenAISmokeTestResultV2:
        """Run one independently scoped offline smoke orchestration."""

        outcome = _evaluate_and_execute(
            configuration,
            self._credential_authority,
            self._composer_authority,
        )
        del configuration
        del self
        return _return_or_raise_smoke_outcome(outcome)

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

    def __setattr__(self, name: str, value: object) -> Never:
        del name
        del value
        raise AttributeError("OpenAI smoke-test runner is immutable")

    def __delattr__(self, name: str) -> Never:
        del name
        raise AttributeError("OpenAI smoke-test runner is immutable")

    def __repr__(self) -> str:
        return "OpenAISmokeTestRunnerV2()"


@dataclass(frozen=True, slots=True)
class _PinnedAuthority:
    function: FunctionType
    receiver: object | None

    def invoke(self, **arguments: object) -> object:
        if self.receiver is None:
            return self.function(**arguments)
        return self.function(self.receiver, **arguments)


class _InvocationCategory(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    BASE_EXCEPTION = auto()


@dataclass(frozen=True, slots=True)
class _InvocationOutcome:
    category: _InvocationCategory
    value: object = None


class _SmokeOutcomeCategory(Enum):
    SUCCESS = auto()
    CONFIGURATION_INVALID = auto()
    CONFIRMATION_REQUIRED = auto()
    CREDENTIAL_FAILED = auto()
    COMPOSITION_FAILED = auto()
    EXECUTION_FAILED = auto()
    CLEANUP_FAILED = auto()
    BASE_EXCEPTION = auto()


@dataclass(frozen=True, slots=True)
class _SafeSmokeOutcome:
    category: _SmokeOutcomeCategory
    value: object = None


def _evaluate_and_execute(
    configuration: object,
    credential_authority: _PinnedAuthority,
    composer_authority: _PinnedAuthority,
) -> _SafeSmokeOutcome:
    try:
        authority = OpenAISmokeTestConfigurationV2.model_validate(configuration)
    except (TypeError, ValueError, ValidationError):
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.CONFIGURATION_INVALID)
    if not authority.confirm_live:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.CONFIRMATION_REQUIRED)

    credential_outcome = _invoke_authority(credential_authority)
    if credential_outcome.category is _InvocationCategory.BASE_EXCEPTION:
        return _SafeSmokeOutcome(
            _SmokeOutcomeCategory.BASE_EXCEPTION, credential_outcome.value
        )
    if credential_outcome.category is _InvocationCategory.FAILURE:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.CREDENTIAL_FAILED)
    api_key = credential_outcome.value
    if (
        type(api_key) is not str
        or not api_key
        or not api_key.strip()
        or api_key != api_key.strip()
    ):
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.CREDENTIAL_FAILED)

    composition_outcome = _invoke_authority(
        composer_authority,
        api_key=api_key,
        model=authority.model,
        timeout_seconds=authority.timeout_seconds,
    )
    if composition_outcome.category is _InvocationCategory.BASE_EXCEPTION:
        return _SafeSmokeOutcome(
            _SmokeOutcomeCategory.BASE_EXCEPTION, composition_outcome.value
        )
    if composition_outcome.category is _InvocationCategory.FAILURE:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.COMPOSITION_FAILED)
    handoff = _validate_composition_handoff(composition_outcome.value)
    if handoff is None:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.COMPOSITION_FAILED)
    execute_authority, close_authority = handoff

    execution_outcome = _invoke_authority(execute_authority)
    cleanup_outcome = _invoke_authority(close_authority)
    if cleanup_outcome.category is _InvocationCategory.BASE_EXCEPTION:
        return _SafeSmokeOutcome(
            _SmokeOutcomeCategory.BASE_EXCEPTION, cleanup_outcome.value
        )
    if cleanup_outcome.category is _InvocationCategory.FAILURE:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.CLEANUP_FAILED)
    if execution_outcome.category is _InvocationCategory.BASE_EXCEPTION:
        return _SafeSmokeOutcome(
            _SmokeOutcomeCategory.BASE_EXCEPTION, execution_outcome.value
        )
    if execution_outcome.category is _InvocationCategory.FAILURE:
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.EXECUTION_FAILED)
    response_text = execution_outcome.value
    if (
        type(response_text) is not str
        or not response_text.strip()
        or response_text != response_text.strip()
    ):
        return _SafeSmokeOutcome(_SmokeOutcomeCategory.EXECUTION_FAILED)
    return _SafeSmokeOutcome(_SmokeOutcomeCategory.SUCCESS, response_text)


def _invoke_authority(
    authority: _PinnedAuthority, **arguments: object
) -> _InvocationOutcome:
    try:
        value = authority.invoke(**arguments)
    except BaseException as error:  # noqa: BLE001 - BaseExceptions are detached
        if isinstance(error, Exception):
            return _InvocationOutcome(_InvocationCategory.FAILURE)
        error.__traceback__ = None
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True
        return _InvocationOutcome(_InvocationCategory.BASE_EXCEPTION, error)
    return _InvocationOutcome(_InvocationCategory.SUCCESS, value)


def _validate_composition_handoff(
    composition: object,
) -> tuple[_PinnedAuthority, _PinnedAuthority] | None:
    executor = _static_instance_value(composition, "executor")
    if executor is None:
        return None
    execute_authority = _pin_method(executor, "execute", "zero")
    close_authority = _pin_method(composition, "close", "zero")
    if execute_authority is None or close_authority is None:
        return None
    return execute_authority, close_authority


def _static_instance_value(value: object, name: str) -> object | None:
    if not _has_safe_type_hierarchy(value):
        return None
    try:
        namespace = object.__getattribute__(value, "__dict__")
    except AttributeError:
        return None
    if type(namespace) is not dict or name not in namespace:
        return None
    return namespace[name]


def _pin_method(value: object, name: str, shape: str) -> _PinnedAuthority | None:
    if not _has_safe_type_hierarchy(value) or _has_instance_member(value, name):
        return None
    try:
        raw = getattr_static(value, name)
    except (AttributeError, TypeError):
        return None
    if type(raw) is FunctionType:
        function = raw
        receiver: object | None = value
    elif type(raw) is staticmethod and type(raw.__func__) is FunctionType:
        function = raw.__func__
        receiver = None
    elif type(raw) is classmethod and type(raw.__func__) is FunctionType:
        function = raw.__func__
        receiver = type(value)
    else:
        return None
    if getattr_static(function, "__isabstractmethod__", False) is True:
        return None
    clone = FunctionType(
        function.__code__,
        function.__globals__,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    if (
        iscoroutinefunction(clone)
        or isgeneratorfunction(clone)
        or isasyncgenfunction(clone)
    ):
        return None
    try:
        actual = signature(clone, follow_wrapped=False)
    except (TypeError, ValueError):
        return None
    parameters = tuple(actual.parameters.values())
    if receiver is not None:
        if not parameters:
            return None
        parameters = parameters[1:]
    if not _parameters_match(parameters, shape):
        return None
    return _PinnedAuthority(function, receiver)


def _parameters_match(parameters: tuple[Parameter, ...], shape: str) -> bool:
    if shape == "zero":
        return not parameters
    if shape != "compose" or len(parameters) != 3:
        return False
    return all(
        parameter.name == name
        and parameter.kind is Parameter.KEYWORD_ONLY
        and parameter.default is Parameter.empty
        for parameter, name in zip(
            parameters,
            ("api_key", "model", "timeout_seconds"),
            strict=True,
        )
    )


def _has_safe_type_hierarchy(value: object) -> bool:
    value_type = type(value)
    if type(value_type) is not type:
        return False
    hierarchy = type.__getattribute__(value_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return False
    return not any(
        "__getattr__" in namespace
        or (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        )
        for namespace in namespaces
    )


def _has_instance_member(value: object, name: str) -> bool:
    try:
        namespace = object.__getattribute__(value, "__dict__")
    except AttributeError:
        return False
    return type(namespace) is dict and name in namespace


def _return_or_raise_smoke_outcome(
    outcome: _SafeSmokeOutcome,
) -> OpenAISmokeTestResultV2:
    if outcome.category is _SmokeOutcomeCategory.SUCCESS:
        return OpenAISmokeTestResultV2.model_validate(
            {"success": True, "response_text": outcome.value}
        )
    if outcome.category is _SmokeOutcomeCategory.BASE_EXCEPTION:
        error = outcome.value
        assert isinstance(error, BaseException)
        try:
            raise error from None
        finally:
            error.__context__ = None
            error.__cause__ = None
            error.__suppress_context__ = True
    if outcome.category is _SmokeOutcomeCategory.CONFIGURATION_INVALID:
        error_type: type[OpenAISmokeTestError] = OpenAISmokeTestConfigurationError
        message = "invalid OpenAI smoke-test configuration"
    elif outcome.category is _SmokeOutcomeCategory.CONFIRMATION_REQUIRED:
        error_type = OpenAISmokeTestConfirmationError
        message = "explicit live OpenAI smoke-test confirmation is required"
    elif outcome.category is _SmokeOutcomeCategory.CREDENTIAL_FAILED:
        error_type = OpenAISmokeTestDependencyError
        message = "OpenAI smoke-test credential source failed"
    elif outcome.category is _SmokeOutcomeCategory.COMPOSITION_FAILED:
        error_type = OpenAISmokeTestDependencyError
        message = "OpenAI smoke-test runtime composition failed"
    elif outcome.category is _SmokeOutcomeCategory.EXECUTION_FAILED:
        error_type = OpenAISmokeTestDependencyError
        message = "OpenAI smoke-test execution failed"
    else:
        error_type = OpenAISmokeTestDependencyError
        message = "OpenAI smoke-test runtime cleanup failed"
    error = error_type(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_invalid_dependency() -> Never:
    error = OpenAISmokeTestDependencyError("invalid OpenAI smoke-test dependency")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error() -> Never:
    error = TypeError("OpenAI smoke-test runners cannot be serialized")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


__all__ = ("OpenAISmokeTestRunnerV2",)
