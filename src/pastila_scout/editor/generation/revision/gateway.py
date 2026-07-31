"""Versioned provider-neutral gateway boundary for targeted revision."""

from typing import Protocol

from .contracts import ControlledRevisionGatewayResult, ControlledRevisionInvocation


class ControlledRevisionGateway(Protocol):
    """A revision-capable adapter boundary, separate from legacy generation."""

    def revise(
        self, invocation: ControlledRevisionInvocation
    ) -> ControlledRevisionGatewayResult: ...
