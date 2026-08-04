"""Structured ranking-provider adapter over one neutral workflow call."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from inspect import Parameter, signature
from types import FunctionType
from typing import NoReturn, Self, get_type_hints

from pastila_scout.ai.provider import (
    ProviderError,
    StructuredAIRequest,
    StructuredAIResponse,
)
from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderResultStatusV2
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1

from .prompt import serialize_ranking_task

_TIMEOUT_SECONDS = 30.0


class ProviderNeutralRankingProviderV1:
    """Implement the existing structured provider protocol without postprocessing."""

    __slots__ = ("_execute", "_now", "_provider")

    def __init__(
        self,
        provider: ProviderChoiceV1,
        execute: Callable[
            [ProviderChoiceV1, ProviderExecutionRequestV2], ScoutRuntimeResultV1
        ],
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if (
            type(provider) is not ProviderChoiceV1
            or not _valid_execute(execute)
            or not _valid_now(now)
        ):
            del self, provider, execute, now
            raise ValueError("invalid provider-neutral ranking dependency")
        object.__setattr__(self, "_provider", provider)
        object.__setattr__(self, "_execute", execute)
        object.__setattr__(self, "_now", now)

    def __repr__(self) -> str:
        provider, _, _ = _validated_state(self)
        return (
            "ProviderNeutralRankingProviderV1("
            f"provider={provider.value!r}, execute=<injected>, now=<injected>)"
        )

    def __eq__(self, other: object) -> bool:
        provider, execute, now = _validated_state(self)
        if type(other) is not ProviderNeutralRankingProviderV1:
            return False
        other_provider, other_execute, other_now = _validated_state(other)
        return (
            provider is other_provider and execute is other_execute and now is other_now
        )

    def __copy__(self) -> Self:
        _validated_state(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        _validated_state(self)
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        _validated_state(self)
        del self, protocol
        raise TypeError("provider-neutral ranking adapters cannot be serialized")

    def complete_structured(self, task: StructuredAIRequest) -> StructuredAIResponse:
        _validated_state(self)
        outcome = _complete_isolated(self, task)
        del self, task
        if type(outcome) is _SafeProviderFailure:
            del outcome
            _raise_provider_error()
        return outcome


class _SafeProviderFailure:
    __slots__ = ()


def _complete_isolated(
    provider: ProviderNeutralRankingProviderV1, task: StructuredAIRequest
) -> StructuredAIResponse | _SafeProviderFailure:
    try:
        prompt = serialize_ranking_task(task)
        requested_at = provider._now()
        reference = sha256(f"{requested_at.isoformat()}\0{prompt}".encode()).hexdigest()
        application = ApplicationProviderRequestV1(
            provider._provider,
            prompt,
            f"rank-events-v1:{reference}",
            requested_at,
            TimeoutPolicyV2(timeout_seconds=_TIMEOUT_SECONDS),
            CancellationTokenV2(cancellation_requested=False),
        )
        provider_request = ApplicationRequestAuthorityV1().build(application)
        runtime_result = provider._execute(provider._provider, provider_request)
        projection = runtime_result.provider_result.provider_result
        if (
            projection is None
            or projection.status is not ProviderResultStatusV2.SUCCESS
            or len(projection.outputs) != 1
        ):
            raise ValueError
        return StructuredAIResponse(output_text=projection.outputs[0].generated_text)
    except Exception:  # noqa: BLE001 - lower diagnostics are discarded here
        return _SafeProviderFailure()


def _valid_execute(value: object) -> bool:
    if type(value) is not FunctionType:
        return False
    if hasattr(value, "__wrapped__") or hasattr(value, "__signature__"):
        return False
    try:
        parameters = tuple(signature(value, follow_wrapped=False).parameters.values())
        annotations = get_type_hints(value)
    except (NameError, TypeError, ValueError):
        return False
    return (
        len(parameters) == 2
        and parameters[0].name == "provider"
        and parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
        and parameters[0].default is Parameter.empty
        and parameters[1].name == "request"
        and parameters[1].kind is Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is Parameter.empty
        and annotations
        == {
            "provider": ProviderChoiceV1,
            "request": ProviderExecutionRequestV2,
            "return": ScoutRuntimeResultV1,
        }
    )


def _valid_now(value: object) -> bool:
    if type(value) is not FunctionType:
        return False
    if hasattr(value, "__wrapped__") or hasattr(value, "__signature__"):
        return False
    try:
        return not signature(value, follow_wrapped=False).parameters
    except (TypeError, ValueError):
        return False


def _validated_state(
    value: object,
) -> tuple[
    ProviderChoiceV1,
    Callable[[ProviderChoiceV1, ProviderExecutionRequestV2], ScoutRuntimeResultV1],
    Callable[[], datetime],
]:
    if type(value) is not ProviderNeutralRankingProviderV1:
        raise ValueError("invalid provider-neutral ranking adapter")
    try:
        provider = object.__getattribute__(value, "_provider")
        execute = object.__getattribute__(value, "_execute")
        now = object.__getattribute__(value, "_now")
    except AttributeError:
        raise ValueError("invalid provider-neutral ranking adapter") from None
    if (
        type(provider) is not ProviderChoiceV1
        or not _valid_execute(execute)
        or not _valid_now(now)
    ):
        raise ValueError("invalid provider-neutral ranking adapter")
    return provider, execute, now


def _raise_provider_error() -> NoReturn:
    error = ProviderError("Provider-neutral ranking failed", retryable=False)
    error.__suppress_context__ = True
    raise error from None


__all__ = ("ProviderNeutralRankingProviderV1",)
