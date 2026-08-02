"""Non-operational runner for an explicitly confirmed future live smoke test."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Never, Self

from pydantic import ValidationError

from .errors import (
    OpenAISmokeTestConfigurationError,
    OpenAISmokeTestConfirmationError,
    OpenAISmokeTestDependencyError,
    OpenAISmokeTestError,
)
from .models import OpenAISmokeTestConfigurationV2


class OpenAISmokeTestRunnerV2:
    """Validate opt-in policy without performing any operational action."""

    __slots__ = ()

    def run(self, configuration: object) -> Never:
        """Reject safely after validation because Revision 2 is non-operational."""

        outcome = _evaluate_configuration(configuration)
        del configuration
        del self
        _return_or_raise_smoke_outcome(outcome)

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


class _SmokeFailureCategory(Enum):
    CONFIGURATION_INVALID = auto()
    CONFIRMATION_REQUIRED = auto()
    NOT_OPERATIONAL = auto()


@dataclass(frozen=True, slots=True)
class _SafeSmokeOutcome:
    category: _SmokeFailureCategory


def _evaluate_configuration(
    configuration: object,
) -> _SafeSmokeOutcome:
    try:
        authority = OpenAISmokeTestConfigurationV2.model_validate(configuration)
    except (TypeError, ValueError, ValidationError):
        return _SafeSmokeOutcome(_SmokeFailureCategory.CONFIGURATION_INVALID)
    if not authority.confirm_live:
        return _SafeSmokeOutcome(_SmokeFailureCategory.CONFIRMATION_REQUIRED)
    return _SafeSmokeOutcome(_SmokeFailureCategory.NOT_OPERATIONAL)


def _return_or_raise_smoke_outcome(outcome: _SafeSmokeOutcome) -> Never:
    if outcome.category is _SmokeFailureCategory.CONFIGURATION_INVALID:
        error_type: type[OpenAISmokeTestError] = OpenAISmokeTestConfigurationError
        message = "invalid OpenAI smoke-test configuration"
    elif outcome.category is _SmokeFailureCategory.CONFIRMATION_REQUIRED:
        error_type = OpenAISmokeTestConfirmationError
        message = "explicit live OpenAI smoke-test confirmation is required"
    else:
        error_type = OpenAISmokeTestDependencyError
        message = "OpenAI live smoke test is not operational"
    error = error_type(message)
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
