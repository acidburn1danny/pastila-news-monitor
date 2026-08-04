"""Inert application composition boundary for future Scout migration."""

from dataclasses import dataclass
from typing import NoReturn

from pastila_scout.provider_selection_v1 import ProviderSelectorV1

from .errors import ScoutRuntimeCompositionError
from .models import (
    ScoutCancellationV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class ScoutRuntimeCompositionV1:
    """Validated injected dependencies with no execution behavior."""

    selector: ProviderSelectorV1
    config: ScoutRuntimeConfigV1
    options: ScoutRuntimeOptionsV1
    cancellation: ScoutCancellationV1

    def __init__(
        self,
        selector: ProviderSelectorV1,
        config: ScoutRuntimeConfigV1,
        options: ScoutRuntimeOptionsV1,
        cancellation: ScoutCancellationV1,
    ) -> None:
        message = _dependency_error(selector, config, options, cancellation)
        if message is not None:
            del self, selector, config, options, cancellation
            _raise_error(message)
        validated_config = ScoutRuntimeConfigV1(
            object.__getattribute__(config, "configuration_identity")
        )
        validated_options = ScoutRuntimeOptionsV1(
            object.__getattribute__(options, "options_identity")
        )
        validated_cancellation = ScoutCancellationV1(
            object.__getattribute__(cancellation, "cancellation_requested")
        )
        object.__setattr__(self, "selector", selector)
        object.__setattr__(self, "config", validated_config)
        object.__setattr__(self, "options", validated_options)
        object.__setattr__(self, "cancellation", validated_cancellation)

    def __repr__(self) -> str:
        state, message = _composition_state(self)
        if message is not None:
            del self, state
            _raise_error(message)
        _, config, options, cancellation = state
        return (
            "ScoutRuntimeCompositionV1("
            "selector=<injected ProviderSelectorV1>, "
            f"config={config!r}, options={options!r}, "
            f"cancellation={cancellation!r})"
        )

    def __eq__(self, other: object) -> bool:
        state, message = _composition_state(self)
        if message is not None:
            del self, other, state
            _raise_error(message)
        if type(other) is not ScoutRuntimeCompositionV1:
            return False
        other_state, other_message = _composition_state(other)
        if other_message is not None:
            del self, other, state, other_state
            _raise_error(other_message)
        selector, config, options, cancellation = state
        other_selector, other_config, other_options, other_cancellation = other_state
        return (
            selector is other_selector
            and config == other_config
            and options == other_options
            and cancellation == other_cancellation
        )

    def __copy__(self) -> ScoutRuntimeCompositionV1:
        state, message = _composition_state(self)
        if message is not None:
            del self, state
            _raise_error(message)
        return ScoutRuntimeCompositionV1(*state)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeCompositionV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        state, message = _composition_state(self)
        if message is not None:
            del self, protocol, state
            _raise_error(message)
        del self, protocol, state
        _raise_pickle_error()


def _dependency_error(
    selector: object,
    config: object,
    options: object,
    cancellation: object,
) -> str | None:
    if type(selector) is not ProviderSelectorV1:
        return "invalid Scout provider selector"
    if type(config) is not ScoutRuntimeConfigV1 or not _valid_identifier_field(
        config, "configuration_identity"
    ):
        return "invalid Scout runtime configuration"
    if type(options) is not ScoutRuntimeOptionsV1 or not _valid_identifier_field(
        options, "options_identity"
    ):
        return "invalid Scout runtime options"
    if type(cancellation) is not ScoutCancellationV1:
        return "invalid Scout cancellation dependency"
    try:
        requested = object.__getattribute__(cancellation, "cancellation_requested")
    except AttributeError:
        return "invalid Scout cancellation dependency"
    if type(requested) is not bool:
        return "invalid Scout cancellation dependency"
    return None


def _composition_state(
    value: ScoutRuntimeCompositionV1,
) -> tuple[
    tuple[
        ProviderSelectorV1,
        ScoutRuntimeConfigV1,
        ScoutRuntimeOptionsV1,
        ScoutCancellationV1,
    ]
    | None,
    str | None,
]:
    try:
        selector = object.__getattribute__(value, "selector")
        config = object.__getattribute__(value, "config")
        options = object.__getattribute__(value, "options")
        cancellation = object.__getattribute__(value, "cancellation")
    except AttributeError:
        return None, "invalid Scout runtime composition"
    message = _dependency_error(selector, config, options, cancellation)
    if message is not None:
        return None, message
    return (selector, config, options, cancellation), None


def _valid_identifier_field(value: object, field: str) -> bool:
    try:
        identifier = object.__getattribute__(value, field)
    except AttributeError:
        return False
    return (
        type(identifier) is str
        and bool(identifier.strip())
        and identifier == identifier.strip()
        and len(identifier) <= 200
    )


def _raise_error(message: str) -> NoReturn:
    error = ScoutRuntimeCompositionError(message)
    error.__suppress_context__ = True
    raise error


def _raise_pickle_error() -> NoReturn:
    raise TypeError("Scout runtime composition does not support pickle")


__all__ = ("ScoutRuntimeCompositionV1",)
