"""Capability-neutral public executor protocol for future M6C.6B runtime work."""

from typing import Protocol, runtime_checkable

from .models import (
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
)


@runtime_checkable
class CorrectiveActionExecutor(Protocol):
    """One exact-capability executor contract; no implementation is provided."""

    @property
    def descriptor(self) -> CorrectiveActionExecutorDescriptor:
        """Return the executor's immutable descriptor."""

        ...

    def execute(
        self, request: CorrectiveActionExecutorRequest
    ) -> CorrectiveActionExecutorResult:
        """Execute one immutable request in a future authorized milestone."""

        ...
