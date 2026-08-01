"""Non-operational trusted OpenAI runtime composition specification."""

from dataclasses import dataclass, field
from inspect import iscoroutinefunction, signature
from types import FunctionType, MappingProxyType

from pydantic import ValidationError

from .errors import (
    OpenAIRuntimeConfigurationError,
    OpenAIRuntimeCredentialError,
    OpenAIRuntimeDependencyError,
)
from .models import OpenAIRuntimeCompositionV2, OpenAIRuntimeConfigV2


@dataclass(frozen=True, slots=True, init=False)
class OpenAIRuntimeComposerV2:
    """Validated composition plan with deliberately deferred operations."""

    config: OpenAIRuntimeConfigV2
    _credential_source: object = field(repr=False)
    _sdk_factory: object = field(repr=False)

    def __init__(
        self,
        config: object,
        *,
        credential_source: object,
        sdk_factory: object,
    ) -> None:
        authority = _validate_config(config)
        if authority is None:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI runtime config")
        if not _has_static_method(credential_source, "get_api_key", mode="source"):
            raise OpenAIRuntimeConfigurationError("invalid OpenAI credential source")
        if not _has_static_method(sdk_factory, "create_client", mode="factory"):
            raise OpenAIRuntimeConfigurationError("invalid OpenAI SDK factory")
        if not _has_static_method(sdk_factory, "close_client", mode="closer"):
            raise OpenAIRuntimeConfigurationError("invalid OpenAI SDK lifecycle")
        object.__setattr__(self, "config", authority)
        object.__setattr__(self, "_credential_source", credential_source)
        object.__setattr__(self, "_sdk_factory", sdk_factory)

    def compose(self) -> OpenAIRuntimeCompositionV2:
        """Refuse operational composition until the separately verified revision."""

        outcome = _non_operational_composition_outcome()
        del self
        return _return_or_raise_dependency(outcome)


@dataclass(frozen=True, slots=True)
class _SafeDependencyFailureOutcome:
    category: str
    message: str


def _non_operational_composition_outcome() -> _SafeDependencyFailureOutcome:
    return _SafeDependencyFailureOutcome(
        category="dependency",
        message="OpenAI runtime composition is not implemented",
    )


def _return_or_raise_dependency(
    outcome: _SafeDependencyFailureOutcome,
) -> OpenAIRuntimeCompositionV2:
    error = OpenAIRuntimeDependencyError(outcome.message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _validate_config(value: object) -> OpenAIRuntimeConfigV2 | None:
    try:
        return OpenAIRuntimeConfigV2.model_validate(value)
    except (TypeError, ValueError, ValidationError):
        return None


def _validate_api_key(value: object) -> None:
    """Validate a retrieved key without retaining or exposing its contents."""

    if (
        type(value) is not str
        or not value
        or not value.strip()
        or value != value.strip()
    ):
        raise OpenAIRuntimeCredentialError("invalid OpenAI credential")


def _has_static_method(value: object, name: str, *, mode: str) -> bool:
    value_type = type(value)
    if type(value_type) is not type:
        return False
    hierarchy = type.__getattribute__(value_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return False
    if any(
        "__getattr__" in namespace
        or (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        )
        for namespace in namespaces
    ):
        return False
    for namespace in namespaces:
        if name not in namespace:
            continue
        function = namespace[name]
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
        if iscoroutinefunction(clone):
            return False
        try:
            bound = signature(clone, follow_wrapped=False)
            if mode == "source":
                bound.bind(value)
            elif mode == "factory":
                bound.bind(value, api_key="key", max_retries=0)
            else:
                bound.bind(value, object())
        except (TypeError, ValueError):
            return False
        return True
    return False


__all__ = ("OpenAIRuntimeComposerV2",)
