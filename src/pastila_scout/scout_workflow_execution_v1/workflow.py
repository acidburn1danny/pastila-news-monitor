"""Opt-in provider-neutral execution at the Scout workflow boundary."""

import inspect
from dataclasses import dataclass
from types import FunctionType
from typing import NoReturn, get_type_hints

from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeExecutionBridgeV1,
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)

from .errors import ScoutWorkflowExecutionError
from .protocols import LegacyScoutWorkflowExecutionV1


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class ScoutWorkflowExecutionV1:
    """Keep legacy execution as the default and expose one explicit new path."""

    legacy_workflow: LegacyScoutWorkflowExecutionV1
    runtime_bridge: ScoutRuntimeExecutionBridgeV1

    def __init__(
        self,
        legacy_workflow: LegacyScoutWorkflowExecutionV1,
        runtime_bridge: ScoutRuntimeExecutionBridgeV1,
    ) -> None:
        message = _dependency_error(legacy_workflow, runtime_bridge)
        if message is not None:
            del self, legacy_workflow, runtime_bridge
            _raise_error(message)
        object.__setattr__(self, "legacy_workflow", legacy_workflow)
        object.__setattr__(self, "runtime_bridge", runtime_bridge)

    def __repr__(self) -> str:
        message = _state_error(self)
        if message is not None:
            del self
            _raise_error(message)
        return (
            "ScoutWorkflowExecutionV1("
            "legacy_workflow=<injected LegacyScoutWorkflowExecutionV1>, "
            "runtime_bridge=<injected ScoutRuntimeExecutionBridgeV1>)"
        )

    def __eq__(self, other: object) -> bool:
        message = _state_error(self)
        if message is not None:
            del self, other
            _raise_error(message)
        if type(other) is not ScoutWorkflowExecutionV1:
            return False
        other_message = _state_error(other)
        if other_message is not None:
            del self, other
            _raise_error(other_message)
        return (
            self.legacy_workflow is other.legacy_workflow
            and self.runtime_bridge is other.runtime_bridge
        )

    def __copy__(self) -> ScoutWorkflowExecutionV1:
        message = _state_error(self)
        if message is not None:
            del self
            _raise_error(message)
        return ScoutWorkflowExecutionV1(self.legacy_workflow, self.runtime_bridge)

    def __deepcopy__(self, memo: dict[int, object]) -> ScoutWorkflowExecutionV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        message = _state_error(self)
        if message is not None:
            del self, protocol
            _raise_error(message)
        del self, protocol
        raise TypeError("Scout workflow execution boundary does not support pickle")

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        """Use the unchanged legacy boundary; this remains the default method."""
        message = _state_error(self)
        if message is None and type(request) is not ScoutRuntimeRequestV1:
            message = "invalid Scout workflow request"
        if message is not None:
            del self, request
            _raise_error(message)
        legacy_workflow = object.__getattribute__(self, "legacy_workflow")
        failed = False
        try:
            result = legacy_workflow.execute(request)
        except Exception:  # noqa: BLE001 - legacy failures remain boundary-private
            failed = True
            result = None
        if failed:
            del self, request, legacy_workflow, result
            _raise_error("legacy Scout workflow failed")
        if type(result) is not ScoutRuntimeResultV1:
            del self, request, legacy_workflow, result
            _raise_error("invalid legacy Scout workflow result")
        return result

    def execute_provider_neutral(
        self, request: ScoutRuntimeRequestV1
    ) -> ScoutRuntimeResultV1:
        """Execute once through the injected verified runtime bridge."""
        message = _state_error(self)
        if message is None and type(request) is not ScoutRuntimeRequestV1:
            message = "invalid Scout workflow request"
        if message is not None:
            del self, request
            _raise_error(message)
        runtime_bridge = object.__getattribute__(self, "runtime_bridge")
        failed = False
        try:
            result = runtime_bridge.execute(request)
        except Exception:  # noqa: BLE001 - lower failures remain boundary-private
            failed = True
            result = None
        if failed:
            del self, request, runtime_bridge, result
            _raise_error("Scout runtime execution bridge failed")
        return result


def _dependency_error(legacy_workflow: object, runtime_bridge: object) -> str | None:
    if not _valid_legacy_workflow(legacy_workflow):
        return "invalid legacy Scout workflow"
    if type(runtime_bridge) is not ScoutRuntimeExecutionBridgeV1:
        return "invalid Scout runtime execution bridge"
    return None


def _state_error(value: object) -> str | None:
    if type(value) is not ScoutWorkflowExecutionV1:
        return "invalid Scout workflow execution boundary"
    try:
        legacy_workflow = object.__getattribute__(value, "legacy_workflow")
        runtime_bridge = object.__getattribute__(value, "runtime_bridge")
    except AttributeError:
        return "invalid Scout workflow execution boundary"
    return _dependency_error(legacy_workflow, runtime_bridge)


def _valid_legacy_workflow(value: object) -> bool:
    try:
        descriptor = inspect.getattr_static(type(value), "execute")
    except AttributeError:
        return False
    if type(descriptor) is not FunctionType:
        return False
    if hasattr(descriptor, "__signature__") or hasattr(descriptor, "__wrapped__"):
        return False
    try:
        signature = inspect.signature(descriptor, follow_wrapped=False)
        annotations = get_type_hints(descriptor)
    except (NameError, TypeError, ValueError):
        return False
    parameters = tuple(signature.parameters.values())
    return (
        len(parameters) == 2
        and parameters[0].name == "self"
        and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[0].default is inspect.Parameter.empty
        and parameters[1].name == "request"
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and annotations
        == {
            "request": ScoutRuntimeRequestV1,
            "return": ScoutRuntimeResultV1,
        }
    )


def _raise_error(message: str) -> NoReturn:
    error = ScoutWorkflowExecutionError(message)
    error.__suppress_context__ = True
    raise error


__all__ = ("ScoutWorkflowExecutionV1",)
