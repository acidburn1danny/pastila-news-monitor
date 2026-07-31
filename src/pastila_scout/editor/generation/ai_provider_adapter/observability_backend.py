"""Safe Part 6B composition boundary for operational metric backends.

No production backend is selected by this module.  The repository currently
has no deployable metrics infrastructure, so unsupported real-backend requests
degrade to the Part 6A no-op sink without affecting business execution.
"""

from __future__ import annotations

# Backend lifecycle failures are explicitly non-authoritative.
# ruff: noqa: BLE001
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .production_observability import (
    ALLOWED_DIMENSIONS,
    COUNTER_NAMES,
    DURATION_NAMES,
    ControlledRevisionMetricSink,
    InMemoryControlledRevisionMetricSink,
    NoOpControlledRevisionMetricSink,
)


class BackendStrategy(StrEnum):
    ADAPT_EXISTING_BACKEND = "ADAPT_EXISTING_BACKEND"
    IMPLEMENT_STANDARDS_BASED_BACKEND = "IMPLEMENT_STANDARDS_BASED_BACKEND"
    RETAIN_INTERFACE_ONLY = "RETAIN_INTERFACE_ONLY"


class TelemetryBackend(StrEnum):
    DISABLED = "disabled"
    NO_OP = "no_op"
    IN_MEMORY_TEST = "in_memory_test"
    REAL_BACKEND = "real_backend"


class TelemetryHealth(StrEnum):
    DISABLED = "DISABLED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class TelemetryConfigurationStatus(StrEnum):
    READY = "READY"
    TELEMETRY_DISABLED_DUE_TO_CONFIGURATION = "TELEMETRY_DISABLED_DUE_TO_CONFIGURATION"
    TELEMETRY_BACKEND_UNAVAILABLE = "TELEMETRY_BACKEND_UNAVAILABLE"
    TELEMETRY_INITIALIZATION_FAILED = "TELEMETRY_INITIALIZATION_FAILED"


class ExportMode(StrEnum):
    LOCAL_IN_PROCESS_NON_NETWORK_EXPORT = "LOCAL_IN_PROCESS_NON_NETWORK_EXPORT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BackpressureMode(StrEnum):
    AGGREGATE_IN_MEMORY = "AGGREGATE_IN_MEMORY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


ENV_ENABLED = "CONTROLLED_REVISION_TELEMETRY_ENABLED"
ENV_BACKEND = "CONTROLLED_REVISION_TELEMETRY_BACKEND"
ENV_EXPORT_TIMEOUT_MS = "CONTROLLED_REVISION_TELEMETRY_EXPORT_TIMEOUT_MS"
DEFAULT_EXPORT_TIMEOUT_MS = 250
DEFAULT_FLUSH_TIMEOUT_MS = 250

COUNTER_MAPPING = MappingProxyType(
    {name: (name, "counter", "1") for name in COUNTER_NAMES}
)
DURATION_MAPPING = MappingProxyType(
    {name: (name, "histogram", "ms") for name in DURATION_NAMES}
)
HISTOGRAM_BOUNDARIES_MS = (
    10,
    25,
    50,
    100,
    250,
    500,
    1_000,
    2_000,
    5_000,
    10_000,
    30_000,
    60_000,
)

DIMENSION_VALUE_COUNTS = MappingProxyType(
    {
        "operational_outcome": 4,
        "scenario_class": 5,
        "provider_family": 1,
        "model_family": 1,
        "failure_layer": 9,
        "safe_failure_category": 17,
        "acceptance_result": 2,
        "telemetry_enabled": 2,
        "environment_class": 3,
    }
)
THEORETICAL_MAX_CARDINALITY = 36_720


@dataclass(frozen=True, slots=True)
class ControlledRevisionTelemetrySettings:
    """Explicit backend settings; safe defaults never enable export."""

    enabled: bool = False
    backend: TelemetryBackend = TelemetryBackend.DISABLED
    export_timeout_ms: int = DEFAULT_EXPORT_TIMEOUT_MS
    flush_timeout_ms: int = DEFAULT_FLUSH_TIMEOUT_MS

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> ControlledRevisionTelemetrySettings:
        """Parse only repository-owned variables without retaining their source."""

        values = os.environ if environment is None else environment
        enabled = values.get(ENV_ENABLED, "false").strip().casefold()
        if enabled not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("invalid controlled-revision telemetry enabled value")
        enabled_value = enabled in {"true", "1", "yes"}
        backend_value = values.get(
            ENV_BACKEND, "no_op" if enabled_value else "disabled"
        ).strip()
        try:
            backend = TelemetryBackend(backend_value)
        except ValueError as exc:
            raise ValueError("invalid controlled-revision telemetry backend") from exc
        try:
            timeout = int(
                values.get(ENV_EXPORT_TIMEOUT_MS, str(DEFAULT_EXPORT_TIMEOUT_MS))
            )
        except ValueError as exc:
            raise ValueError("invalid controlled-revision telemetry timeout") from exc
        if timeout <= 0 or timeout > 10_000:
            raise ValueError("controlled-revision telemetry timeout out of range")
        return cls(enabled=enabled_value, backend=backend, export_timeout_ms=timeout)


@dataclass(frozen=True, slots=True)
class ControlledRevisionTelemetryHealthSnapshot:
    status: TelemetryHealth
    configuration_status: TelemetryConfigurationStatus
    backend_type: str
    initialized: bool
    shutdown: bool
    export_failure_count: int
    dropped_metric_count: int


class ControlledRevisionTelemetryLifecycle:
    """Idempotent, bounded lifecycle owner for a composed sink."""

    def __init__(
        self,
        sink: ControlledRevisionMetricSink,
        *,
        status: TelemetryHealth,
        configuration_status: TelemetryConfigurationStatus,
        backend_type: str,
    ) -> None:
        self.sink = sink
        self._status = status
        self._configuration_status = configuration_status
        self._backend_type = backend_type
        self._initialized = False
        self._shutdown = False
        self._export_failures = 0
        self._dropped = 0

    def initialize(self) -> ControlledRevisionMetricSink:
        if not self._shutdown:
            self._initialized = True
        return self.sink

    def flush(self, timeout_ms: int = DEFAULT_FLUSH_TIMEOUT_MS) -> bool:
        if timeout_ms <= 0 or self._shutdown:
            return False
        try:
            flush = getattr(self.sink, "flush", None)
            return True if flush is None else bool(flush(timeout_ms=timeout_ms))
        except Exception:
            self._export_failures += 1
            self._status = TelemetryHealth.DEGRADED
            return False

    def shutdown(self, timeout_ms: int = DEFAULT_FLUSH_TIMEOUT_MS) -> bool:
        if self._shutdown:
            return True
        try:
            self.flush(timeout_ms)
            shutdown = getattr(self.sink, "shutdown", None)
            if shutdown is not None:
                shutdown(timeout_ms=timeout_ms)
        except Exception:
            self._export_failures += 1
            self._status = TelemetryHealth.DEGRADED
        finally:
            self._shutdown = True
        return True

    def health(self) -> ControlledRevisionTelemetryHealthSnapshot:
        return ControlledRevisionTelemetryHealthSnapshot(
            status=self._status,
            configuration_status=self._configuration_status,
            backend_type=self._backend_type,
            initialized=self._initialized,
            shutdown=self._shutdown,
            export_failure_count=self._export_failures,
            dropped_metric_count=self._dropped,
        )


@dataclass(frozen=True, slots=True)
class ControlledRevisionTelemetryBackendComposition:
    strategy: BackendStrategy
    settings: ControlledRevisionTelemetrySettings
    sink: ControlledRevisionMetricSink
    lifecycle: ControlledRevisionTelemetryLifecycle
    export_mode: ExportMode
    backpressure_mode: BackpressureMode


def create_controlled_revision_metric_sink(
    settings: ControlledRevisionTelemetrySettings,
) -> ControlledRevisionTelemetryBackendComposition:
    """Create one safe sink; unavailable real export always degrades to no-op."""

    if not settings.enabled or settings.backend is TelemetryBackend.DISABLED:
        sink: ControlledRevisionMetricSink = NoOpControlledRevisionMetricSink()
        health = TelemetryHealth.DISABLED
        config_status = TelemetryConfigurationStatus.READY
        backend_type = TelemetryBackend.DISABLED.value
        export_mode = ExportMode.NOT_APPLICABLE
        backpressure = BackpressureMode.NOT_APPLICABLE
    elif settings.backend is TelemetryBackend.IN_MEMORY_TEST:
        sink = InMemoryControlledRevisionMetricSink()
        health = TelemetryHealth.READY
        config_status = TelemetryConfigurationStatus.READY
        backend_type = TelemetryBackend.IN_MEMORY_TEST.value
        export_mode = ExportMode.LOCAL_IN_PROCESS_NON_NETWORK_EXPORT
        backpressure = BackpressureMode.AGGREGATE_IN_MEMORY
    elif settings.backend is TelemetryBackend.NO_OP:
        sink = NoOpControlledRevisionMetricSink()
        health = TelemetryHealth.READY
        config_status = TelemetryConfigurationStatus.READY
        backend_type = TelemetryBackend.NO_OP.value
        export_mode = ExportMode.NOT_APPLICABLE
        backpressure = BackpressureMode.NOT_APPLICABLE
    else:
        sink = NoOpControlledRevisionMetricSink()
        health = TelemetryHealth.DEGRADED
        config_status = TelemetryConfigurationStatus.TELEMETRY_BACKEND_UNAVAILABLE
        backend_type = "interface_only"
        export_mode = ExportMode.NOT_APPLICABLE
        backpressure = BackpressureMode.NOT_APPLICABLE
    lifecycle = ControlledRevisionTelemetryLifecycle(
        sink,
        status=health,
        configuration_status=config_status,
        backend_type=backend_type,
    )
    lifecycle.initialize()
    return ControlledRevisionTelemetryBackendComposition(
        strategy=BackendStrategy.RETAIN_INTERFACE_ONLY,
        settings=settings,
        sink=sink,
        lifecycle=lifecycle,
        export_mode=export_mode,
        backpressure_mode=backpressure,
    )


def create_controlled_revision_metric_sink_from_environment(
    environment: Mapping[str, str] | None = None,
) -> ControlledRevisionTelemetryBackendComposition:
    """Compose safely from environment; malformed settings disable telemetry."""

    try:
        settings = ControlledRevisionTelemetrySettings.from_environment(environment)
    except ValueError:
        settings = ControlledRevisionTelemetrySettings()
        composition = create_controlled_revision_metric_sink(settings)
        lifecycle = ControlledRevisionTelemetryLifecycle(
            composition.sink,
            status=TelemetryHealth.DEGRADED,
            configuration_status=(
                TelemetryConfigurationStatus.TELEMETRY_DISABLED_DUE_TO_CONFIGURATION
            ),
            backend_type="disabled",
        )
        lifecycle.initialize()
        return ControlledRevisionTelemetryBackendComposition(
            strategy=composition.strategy,
            settings=settings,
            sink=composition.sink,
            lifecycle=lifecycle,
            export_mode=composition.export_mode,
            backpressure_mode=composition.backpressure_mode,
        )
    return create_controlled_revision_metric_sink(settings)


def validate_metric_mapping() -> tuple[str, ...]:
    """Return missing/extra mapping identifiers without mutating any registry."""

    issues = []
    if set(COUNTER_MAPPING) != set(COUNTER_NAMES):
        issues.append("counter_mapping_mismatch")
    if set(DURATION_MAPPING) != set(DURATION_NAMES):
        issues.append("duration_mapping_mismatch")
    if set(DIMENSION_VALUE_COUNTS) != set(ALLOWED_DIMENSIONS):
        issues.append("dimension_mapping_mismatch")
    return tuple(issues)
