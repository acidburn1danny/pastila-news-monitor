"""Provider-neutral dependency protocols for the inert Phase A seam."""

from typing import Protocol, runtime_checkable

from pastila_scout.provider_execution_v2 import ProviderExecutionResultV2

from .models import (
    ProducerCompatibilityEventV1,
    ProducerDiagnosticsObservationV1,
)


@runtime_checkable
class ProducerCompatibilityClockV1(Protocol):
    """Supply monotonic nanosecond samples when a later phase executes."""

    def read_monotonic_ns(self) -> int: ...


@runtime_checkable
class ProducerDiagnosticsAuthorityV1(Protocol):
    """Supply one correlated safe observation after a future execution."""

    def observe(
        self,
        *,
        correlation_id: str,
        attempt_number: int,
        execution_request_id: str,
        request_envelope_identity: str,
        result: ProviderExecutionResultV2,
    ) -> ProducerDiagnosticsObservationV1 | None: ...


@runtime_checkable
class ProducerCompatibilityObserverV1(Protocol):
    """Receive content-free compatibility events in a later phase."""

    def emit(self, event: ProducerCompatibilityEventV1) -> None: ...


__all__ = ()
