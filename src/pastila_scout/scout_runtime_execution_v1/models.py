"""Immutable boundary models for opt-in Scout execution."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)

from .errors import ScoutRuntimeExecutionError


@dataclass(frozen=True, slots=True, init=False)
class ScoutRuntimeRequestV1:
    """One explicit opt-in carrying an authoritative neutral request."""

    provider_execution_opt_in: bool
    provider_request: ProviderExecutionRequestV2

    def __init__(
        self,
        provider_execution_opt_in: bool,
        provider_request: ProviderExecutionRequestV2,
    ) -> None:
        if type(provider_execution_opt_in) is not bool or not provider_execution_opt_in:
            del self, provider_execution_opt_in, provider_request
            _raise_error("Scout provider execution requires explicit opt-in")
        request, message = _request_state(provider_request)
        if message is not None:
            del self, provider_execution_opt_in, provider_request, request
            _raise_error(message)
        object.__setattr__(self, "provider_execution_opt_in", True)
        object.__setattr__(self, "provider_request", request)

    def __copy__(self) -> ScoutRuntimeRequestV1:
        return ScoutRuntimeRequestV1(
            object.__getattribute__(self, "provider_execution_opt_in"),
            object.__getattribute__(self, "provider_request"),
        )

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeRequestV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> tuple[type[ScoutRuntimeRequestV1], tuple[Any, ...]]:
        validated = self.__copy__()
        return (
            ScoutRuntimeRequestV1,
            (validated.provider_execution_opt_in, validated.provider_request),
        )


@dataclass(frozen=True, slots=True, init=False)
class ScoutRuntimeResultV1:
    """One Scout-owned projection of exactly one neutral execution result."""

    provider_result: ProviderExecutionResultV2

    def __init__(self, provider_result: ProviderExecutionResultV2) -> None:
        result, message = _result_state(provider_result)
        if message is not None:
            del self, provider_result, result
            _raise_error(message)
        object.__setattr__(self, "provider_result", result)

    def __copy__(self) -> ScoutRuntimeResultV1:
        return ScoutRuntimeResultV1(object.__getattribute__(self, "provider_result"))

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeResultV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> tuple[type[ScoutRuntimeResultV1], tuple[Any, ...]]:
        validated = self.__copy__()
        return (ScoutRuntimeResultV1, (validated.provider_result,))


def _request_state(
    value: object,
) -> tuple[ProviderExecutionRequestV2 | None, str | None]:
    try:
        payload = value.model_dump(mode="python", warnings=False)
        result = ProviderExecutionRequestV2.model_validate(payload, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None, "invalid Scout provider execution request"
    return result, None


def _result_state(
    value: object,
) -> tuple[ProviderExecutionResultV2 | None, str | None]:
    try:
        payload = value.model_dump(mode="python", warnings=False)
        result = ProviderExecutionResultV2.model_validate(payload, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None, "invalid Scout provider execution result"
    return result, None


def _raise_error(message: str) -> None:
    error = ScoutRuntimeExecutionError(message)
    error.__suppress_context__ = True
    raise error


__all__ = ("ScoutRuntimeRequestV1", "ScoutRuntimeResultV1")
