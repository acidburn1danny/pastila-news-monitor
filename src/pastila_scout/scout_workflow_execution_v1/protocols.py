"""Minimal legacy Scout execution contract retained beside the opt-in path."""

from typing import Protocol

from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)


class LegacyScoutWorkflowExecutionV1(Protocol):
    """Execute the unchanged legacy workflow boundary."""

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        """Return the existing workflow execution result."""


__all__ = ("LegacyScoutWorkflowExecutionV1",)
