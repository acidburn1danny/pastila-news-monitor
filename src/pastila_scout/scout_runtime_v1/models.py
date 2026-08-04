"""Strict immutable Scout runtime composition models."""

from dataclasses import dataclass
from typing import NoReturn

from .errors import ScoutRuntimeCompositionError


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class ScoutRuntimeConfigV1:
    """Identity of one explicitly supplied Scout configuration snapshot."""

    configuration_identity: str

    def __init__(self, configuration_identity: str) -> None:
        message = _identifier_error(
            configuration_identity, "invalid Scout runtime configuration"
        )
        if message is not None:
            del self, configuration_identity
            _raise_error(message)
        object.__setattr__(self, "configuration_identity", configuration_identity)

    def __repr__(self) -> str:
        identity = object.__getattribute__(self, "configuration_identity")
        message = _identifier_error(identity, "invalid Scout runtime configuration")
        if message is not None:
            del self, identity
            _raise_error(message)
        return f"ScoutRuntimeConfigV1(configuration_identity={identity!r})"

    def __eq__(self, other: object) -> bool:
        identity, message = _config_state(self)
        if message is not None:
            del self, other, identity
            _raise_error(message)
        if type(other) is not ScoutRuntimeConfigV1:
            return False
        other_identity, other_message = _config_state(other)
        if other_message is not None:
            del self, other, identity, other_identity
            _raise_error(other_message)
        return identity == other_identity

    def __copy__(self) -> ScoutRuntimeConfigV1:
        identity, message = _config_state(self)
        if message is not None:
            del self, identity
            _raise_error(message)
        return ScoutRuntimeConfigV1(identity)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeConfigV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> tuple[type[ScoutRuntimeConfigV1], tuple[str]]:
        identity, message = _config_state(self)
        if message is not None:
            del self, identity
            _raise_error(message)
        return (ScoutRuntimeConfigV1, (identity,))


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class ScoutRuntimeOptionsV1:
    """Identity of one explicitly supplied runtime-options snapshot."""

    options_identity: str

    def __init__(self, options_identity: str) -> None:
        message = _identifier_error(options_identity, "invalid Scout runtime options")
        if message is not None:
            del self, options_identity
            _raise_error(message)
        object.__setattr__(self, "options_identity", options_identity)

    def __repr__(self) -> str:
        identity = object.__getattribute__(self, "options_identity")
        message = _identifier_error(identity, "invalid Scout runtime options")
        if message is not None:
            del self, identity
            _raise_error(message)
        return f"ScoutRuntimeOptionsV1(options_identity={identity!r})"

    def __eq__(self, other: object) -> bool:
        identity, message = _options_state(self)
        if message is not None:
            del self, other, identity
            _raise_error(message)
        if type(other) is not ScoutRuntimeOptionsV1:
            return False
        other_identity, other_message = _options_state(other)
        if other_message is not None:
            del self, other, identity, other_identity
            _raise_error(other_message)
        return identity == other_identity

    def __copy__(self) -> ScoutRuntimeOptionsV1:
        identity, message = _options_state(self)
        if message is not None:
            del self, identity
            _raise_error(message)
        return ScoutRuntimeOptionsV1(identity)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeOptionsV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> tuple[type[ScoutRuntimeOptionsV1], tuple[str]]:
        identity, message = _options_state(self)
        if message is not None:
            del self, identity
            _raise_error(message)
        return (ScoutRuntimeOptionsV1, (identity,))


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class ScoutCancellationV1:
    """Immutable cancellation state injected into future Scout execution."""

    cancellation_requested: bool

    def __init__(self, cancellation_requested: bool) -> None:
        message = _cancellation_error(cancellation_requested)
        if message is not None:
            del self, cancellation_requested
            _raise_error(message)
        object.__setattr__(self, "cancellation_requested", cancellation_requested)

    def __repr__(self) -> str:
        requested = object.__getattribute__(self, "cancellation_requested")
        message = _cancellation_error(requested)
        if message is not None:
            del self, requested
            _raise_error(message)
        return f"ScoutCancellationV1(cancellation_requested={requested!r})"

    def __eq__(self, other: object) -> bool:
        requested, message = _cancellation_state(self)
        if message is not None:
            del self, other, requested
            _raise_error(message)
        if type(other) is not ScoutCancellationV1:
            return False
        other_requested, other_message = _cancellation_state(other)
        if other_message is not None:
            del self, other, requested, other_requested
            _raise_error(other_message)
        return requested is other_requested

    def __copy__(self) -> ScoutCancellationV1:
        requested, message = _cancellation_state(self)
        if message is not None:
            del self, requested
            _raise_error(message)
        return ScoutCancellationV1(requested)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutCancellationV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> tuple[type[ScoutCancellationV1], tuple[bool]]:
        requested, message = _cancellation_state(self)
        if message is not None:
            del self, requested
            _raise_error(message)
        return (ScoutCancellationV1, (requested,))


def _config_state(value: ScoutRuntimeConfigV1) -> tuple[str | None, str | None]:
    try:
        identity = object.__getattribute__(value, "configuration_identity")
    except AttributeError:
        return None, "invalid Scout runtime configuration"
    message = _identifier_error(identity, "invalid Scout runtime configuration")
    return (identity, None) if message is None else (None, message)


def _options_state(value: ScoutRuntimeOptionsV1) -> tuple[str | None, str | None]:
    try:
        identity = object.__getattribute__(value, "options_identity")
    except AttributeError:
        return None, "invalid Scout runtime options"
    message = _identifier_error(identity, "invalid Scout runtime options")
    return (identity, None) if message is None else (None, message)


def _cancellation_state(
    value: ScoutCancellationV1,
) -> tuple[bool | None, str | None]:
    try:
        requested = object.__getattribute__(value, "cancellation_requested")
    except AttributeError:
        return None, "invalid Scout cancellation dependency"
    message = _cancellation_error(requested)
    return (requested, None) if message is None else (None, message)


def _identifier_error(value: object, message: str) -> str | None:
    if (
        type(value) is not str
        or not value.strip()
        or value != value.strip()
        or len(value) > 200
    ):
        return message
    return None


def _cancellation_error(value: object) -> str | None:
    return None if type(value) is bool else "invalid Scout cancellation dependency"


def _raise_error(message: str) -> NoReturn:
    error = ScoutRuntimeCompositionError(message)
    error.__suppress_context__ = True
    raise error


__all__ = (
    "ScoutCancellationV1",
    "ScoutRuntimeConfigV1",
    "ScoutRuntimeOptionsV1",
)
