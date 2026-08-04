"""First explicit Scout execution path through the verified selector."""

import copy
from dataclasses import dataclass
from typing import NoReturn

from pastila_scout.provider_execution_v2 import ProviderExecutionResultV2
from pastila_scout.provider_selection_v1 import ProviderSelectorV1
from pastila_scout.scout_runtime_v1 import ScoutRuntimeCompositionV1

from .errors import ScoutRuntimeExecutionError
from .mapping import map_provider_execution_result, map_scout_runtime_request
from .models import ScoutRuntimeRequestV1, ScoutRuntimeResultV1


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class ScoutRuntimeExecutionBridgeV1:
    """Execute one opted-in neutral request through the injected composition."""

    composition: ScoutRuntimeCompositionV1
    _authorized_executor: object

    def __init__(self, composition: ScoutRuntimeCompositionV1) -> None:
        message = _composition_error(composition)
        if message is not None:
            del self, composition
            _raise_error(message)
        selector = object.__getattribute__(composition, "selector")
        executor = object.__getattribute__(selector, "executor")
        object.__setattr__(self, "composition", composition)
        object.__setattr__(self, "_authorized_executor", executor)

    def __repr__(self) -> str:
        message = _bridge_error(self)
        if message is not None:
            del self
            _raise_error(message)
        return (
            "ScoutRuntimeExecutionBridgeV1("
            "composition=<injected ScoutRuntimeCompositionV1>)"
        )

    def __eq__(self, other: object) -> bool:
        message = _bridge_error(self)
        if message is not None:
            del self, other
            _raise_error(message)
        if type(other) is not ScoutRuntimeExecutionBridgeV1:
            return False
        other_message = _bridge_error(other)
        if other_message is not None:
            del self, other
            _raise_error(other_message)
        return (
            self.composition is other.composition
            and self._authorized_executor is other._authorized_executor
        )

    def __copy__(self) -> ScoutRuntimeExecutionBridgeV1:
        message = _bridge_error(self)
        if message is not None:
            del self
            _raise_error(message)
        return ScoutRuntimeExecutionBridgeV1(self.composition)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutRuntimeExecutionBridgeV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        message = _bridge_error(self)
        if message is not None:
            del self, protocol
            _raise_error(message)
        del self, protocol
        raise TypeError("Scout runtime execution bridge does not support pickle")

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        """Invoke the selected executor exactly once with no retry or fallback."""
        request_error = None
        try:
            provider_request = map_scout_runtime_request(request)
        except ScoutRuntimeExecutionError as error:
            request_error = str(error)
            provider_request = None
        if request_error is not None:
            del self, request, provider_request
            _raise_error(request_error)
        selector = object.__getattribute__(self.composition, "selector")
        if type(selector) is not ProviderSelectorV1:
            del self, request, provider_request, selector
            _raise_error("invalid Scout provider selector")
        executor = object.__getattribute__(selector, "executor")
        authorized_executor = object.__getattribute__(self, "_authorized_executor")
        if executor is not authorized_executor:
            del self, request, provider_request, selector, executor, authorized_executor
            _raise_error("selected provider executor authority changed")
        executor_failed = False
        try:
            raw_result = executor.execute(provider_request)
        except Exception:  # noqa: BLE001 - neutral executors share no exception type
            executor_failed = True
            raw_result = None
        if executor_failed:
            del (
                self,
                request,
                provider_request,
                selector,
                executor,
                authorized_executor,
                raw_result,
            )
            _raise_error("selected provider executor failed")
        if type(raw_result) is not ProviderExecutionResultV2:
            del (
                self,
                request,
                provider_request,
                selector,
                executor,
                authorized_executor,
                raw_result,
            )
            _raise_error("selected provider executor returned an invalid result")
        result_error = None
        try:
            result = map_provider_execution_result(raw_result, provider_request)
        except ScoutRuntimeExecutionError as error:
            result_error = str(error)
            result = None
        if result_error is not None:
            del (
                self,
                request,
                provider_request,
                selector,
                executor,
                authorized_executor,
                raw_result,
                result,
            )
            _raise_error(result_error)
        return result


def _composition_error(value: object) -> str | None:
    if type(value) is not ScoutRuntimeCompositionV1:
        return "invalid Scout runtime composition"
    try:
        selector = object.__getattribute__(value, "selector")
    except AttributeError:
        return "invalid Scout runtime composition"
    if type(selector) is not ProviderSelectorV1:
        return "invalid Scout provider selector"
    try:
        copy.copy(value)
    except Exception:  # noqa: BLE001 - frozen composition owns its validation
        return "invalid Scout runtime composition"
    return None


def _bridge_error(value: object) -> str | None:
    if type(value) is not ScoutRuntimeExecutionBridgeV1:
        return "invalid Scout runtime execution bridge"
    try:
        composition = object.__getattribute__(value, "composition")
        authorized = object.__getattribute__(value, "_authorized_executor")
    except AttributeError:
        return "invalid Scout runtime execution bridge"
    message = _composition_error(composition)
    if message is not None:
        return message
    selector = object.__getattribute__(composition, "selector")
    current = object.__getattribute__(selector, "executor")
    if current is not authorized:
        return "selected provider executor authority changed"
    return None


def _raise_error(message: str) -> None:
    error = ScoutRuntimeExecutionError(message)
    error.__suppress_context__ = True
    raise error


__all__ = ("ScoutRuntimeExecutionBridgeV1",)
