"""Application-owned explicit provider selector."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import CO_VARARGS, CO_VARKEYWORDS, getattr_static
from types import FunctionType
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pastila_scout.provider_execution_v2 import ProviderExecutorV2

from .errors import (
    DuplicateProviderRegistrationError,
    InvalidProviderExecutorError,
    MissingProviderRegistrationError,
    ProviderSelectionConfigurationError,
    UnknownProviderSelectionError,
)
from .models import ProviderChoiceV1, ProviderSelectionConfigV1

_SUPPORTED_PROVIDERS = (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA)


@dataclass(frozen=True, slots=True)
class ProviderExecutorRegistrationV1:
    """One application-owned association between identity and executor."""

    provider: ProviderChoiceV1
    executor: object

    def __post_init__(self) -> None:
        _validate_registration(self)


@dataclass(frozen=True, slots=True, init=False)
class ProviderSelectorV1:
    """Expose exactly one injected executor selected by explicit configuration."""

    executor: ProviderExecutorV2

    def __init__(
        self,
        config: ProviderSelectionConfigV1,
        registrations: tuple[ProviderExecutorRegistrationV1, ...],
    ) -> None:
        selection = _validated_config(config)
        entries = _validated_registrations(registrations)
        by_provider = {entry.provider: entry.executor for entry in entries}
        missing = tuple(
            item for item in _SUPPORTED_PROVIDERS if item not in by_provider
        )
        if missing:
            raise _isolated(
                MissingProviderRegistrationError(
                    "supported provider registration is missing"
                )
            )
        selected = by_provider.get(selection.provider)
        if selected is None:
            raise _isolated(
                UnknownProviderSelectionError("selected provider is not registered")
            )
        object.__setattr__(self, "executor", cast("ProviderExecutorV2", selected))


def _validated_config(value: object) -> ProviderSelectionConfigV1:
    if type(value) is not ProviderSelectionConfigV1:
        raise _isolated(
            ProviderSelectionConfigurationError(
                "invalid provider selection configuration"
            )
        )
    provider = object.__getattribute__(value, "provider")
    if type(provider) is not ProviderChoiceV1:
        raise _isolated(
            ProviderSelectionConfigurationError(
                "invalid provider selection configuration"
            )
        )
    return ProviderSelectionConfigV1(provider=provider)


def _validated_registrations(
    value: object,
) -> tuple[ProviderExecutorRegistrationV1, ...]:
    if type(value) is not tuple or any(
        type(item) is not ProviderExecutorRegistrationV1 for item in value
    ):
        raise _isolated(
            ProviderSelectionConfigurationError("invalid provider registrations")
        )
    for item in value:
        _validate_registration(item)
    providers = tuple(item.provider for item in value)
    if len(providers) != len(set(providers)):
        raise _isolated(
            DuplicateProviderRegistrationError("provider registration is duplicated")
        )
    return value


def _has_executor_shape(value: object) -> bool:
    if type(type(value)) is not type:
        return False
    try:
        lifecycle = getattr_static(type(value), "execute")
        if type(lifecycle) is not FunctionType:
            return False
        code = lifecycle.__code__
        if (
            code.co_argcount != 2
            or code.co_posonlyargcount != 0
            or code.co_kwonlyargcount != 0
            or code.co_flags & (CO_VARARGS | CO_VARKEYWORDS)
            or code.co_varnames[:2] != ("self", "request")
            or lifecycle.__defaults__ is not None
            or lifecycle.__kwdefaults__
        ):
            return False
        annotations = lifecycle.__annotations__
        if set(annotations) != {"request", "return"}:
            return False
        if not _is_contract_annotation(
            annotations["request"], "ProviderExecutionRequestV2"
        ) or not _is_contract_annotation(
            annotations["return"], "ProviderExecutionResultV2"
        ):
            return False
    except Exception:  # noqa: BLE001 - malformed injected metadata has no base type
        return False
    return True


def _validate_registration(value: ProviderExecutorRegistrationV1) -> None:
    provider = object.__getattribute__(value, "provider")
    executor = object.__getattribute__(value, "executor")
    if type(provider) is not ProviderChoiceV1:
        raise _isolated(
            ProviderSelectionConfigurationError("invalid provider registration")
        )
    if not _has_executor_shape(executor):
        raise _isolated(InvalidProviderExecutorError("invalid provider executor"))


def _is_contract_annotation(value: object, contract_name: str) -> bool:
    if (
        isinstance(value, type)
        and type.__getattribute__(value, "__name__") == contract_name
        and type.__getattribute__(value, "__module__")
        == "pastila_scout.provider_execution_v2.models"
    ):
        return True
    if type(value) is not str:
        return False
    return value in {
        contract_name,
        f"pastila_scout.provider_execution_v2.models.{contract_name}",
    }


def _isolated[ErrorT: BaseException](error: ErrorT) -> ErrorT:
    error.__suppress_context__ = True
    return error


__all__ = ("ProviderExecutorRegistrationV1", "ProviderSelectorV1")
