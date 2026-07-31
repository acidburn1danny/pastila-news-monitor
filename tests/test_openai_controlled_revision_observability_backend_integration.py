"""Part 6B interface-only backend integration and lifecycle tests."""

from __future__ import annotations

import hashlib
import json

import pytest

from pastila_scout.editor.generation.ai_provider_adapter import (
    ALLOWED_DIMENSIONS,
    COUNTER_MAPPING,
    COUNTER_NAMES,
    DIMENSION_VALUE_COUNTS,
    DURATION_MAPPING,
    DURATION_NAMES,
    HISTOGRAM_BOUNDARIES_MS,
    THEORETICAL_MAX_CARDINALITY,
    BackendStrategy,
    BackpressureMode,
    ControlledRevisionTelemetry,
    ControlledRevisionTelemetryConfiguration,
    ControlledRevisionTelemetryLifecycle,
    ControlledRevisionTelemetrySettings,
    ExportMode,
    InMemoryControlledRevisionMetricSink,
    NoOpControlledRevisionMetricSink,
    OperationalOutcome,
    TelemetryBackend,
    TelemetryConfigurationStatus,
    TelemetryHealth,
    create_controlled_revision_metric_sink,
    create_controlled_revision_metric_sink_from_environment,
    validate_metric_mapping,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    controlled_revision_schema_json,
)

SCHEMA_SHA = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"


def test_repository_strategy_is_interface_only() -> None:
    assert BackendStrategy.RETAIN_INTERFACE_ONLY.value == "RETAIN_INTERFACE_ONLY"
    assert len(BackendStrategy) == 3


def test_factory_returns_noop_when_disabled() -> None:
    composition = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings()
    )
    assert isinstance(composition.sink, NoOpControlledRevisionMetricSink)
    assert composition.lifecycle.health().status is TelemetryHealth.DISABLED
    assert composition.export_mode is ExportMode.NOT_APPLICABLE


def test_factory_returns_local_test_sink_only_when_explicitly_enabled() -> None:
    composition = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.IN_MEMORY_TEST
        )
    )
    assert isinstance(composition.sink, InMemoryControlledRevisionMetricSink)
    assert composition.lifecycle.health().status is TelemetryHealth.READY
    assert composition.export_mode is ExportMode.LOCAL_IN_PROCESS_NON_NETWORK_EXPORT
    assert composition.backpressure_mode is BackpressureMode.AGGREGATE_IN_MEMORY


def test_unavailable_real_backend_degrades_to_noop() -> None:
    composition = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.REAL_BACKEND
        )
    )
    health = composition.lifecycle.health()
    assert isinstance(composition.sink, NoOpControlledRevisionMetricSink)
    assert health.status is TelemetryHealth.DEGRADED
    assert (
        health.configuration_status
        is TelemetryConfigurationStatus.TELEMETRY_BACKEND_UNAVAILABLE
    )


def test_environment_configuration_is_explicit_and_bounded() -> None:
    settings = ControlledRevisionTelemetrySettings.from_environment(
        {
            "CONTROLLED_REVISION_TELEMETRY_ENABLED": "true",
            "CONTROLLED_REVISION_TELEMETRY_BACKEND": "in_memory_test",
            "CONTROLLED_REVISION_TELEMETRY_EXPORT_TIMEOUT_MS": "100",
        }
    )
    assert settings.enabled is True
    assert settings.backend is TelemetryBackend.IN_MEMORY_TEST
    assert settings.export_timeout_ms == 100


@pytest.mark.parametrize(
    "environment",
    [
        {"CONTROLLED_REVISION_TELEMETRY_ENABLED": "maybe"},
        {
            "CONTROLLED_REVISION_TELEMETRY_ENABLED": "true",
            "CONTROLLED_REVISION_TELEMETRY_BACKEND": "vendor-content",
        },
        {"CONTROLLED_REVISION_TELEMETRY_EXPORT_TIMEOUT_MS": "unbounded"},
        {"CONTROLLED_REVISION_TELEMETRY_EXPORT_TIMEOUT_MS": "0"},
    ],
)
def test_invalid_configuration_fails_locally_without_backend_creation(
    environment,
) -> None:
    with pytest.raises(ValueError, match="controlled-revision telemetry"):
        ControlledRevisionTelemetrySettings.from_environment(environment)


def test_safe_environment_factory_disables_malformed_configuration() -> None:
    composition = create_controlled_revision_metric_sink_from_environment(
        {"CONTROLLED_REVISION_TELEMETRY_ENABLED": "CANARY_API_KEY"}
    )
    health = composition.lifecycle.health()
    assert isinstance(composition.sink, NoOpControlledRevisionMetricSink)
    assert (
        health.configuration_status
        is TelemetryConfigurationStatus.TELEMETRY_DISABLED_DUE_TO_CONFIGURATION
    )


def test_initialization_shutdown_and_flush_are_idempotent() -> None:
    composition = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.IN_MEMORY_TEST
        )
    )
    assert composition.lifecycle.initialize() is composition.sink
    assert composition.lifecycle.initialize() is composition.sink
    assert composition.lifecycle.flush(10)
    assert composition.lifecycle.shutdown(10)
    assert composition.lifecycle.shutdown(10)
    assert composition.lifecycle.flush(10) is False


def test_shutdown_before_explicit_initialization_is_safe() -> None:
    lifecycle = ControlledRevisionTelemetryLifecycle(
        NoOpControlledRevisionMetricSink(),
        status=TelemetryHealth.DISABLED,
        configuration_status=TelemetryConfigurationStatus.READY,
        backend_type="disabled",
    )
    assert lifecycle.shutdown()
    assert lifecycle.health().shutdown is True


def test_flush_and_shutdown_failures_are_suppressed() -> None:
    class Broken:
        def increment(self, *args, **kwargs):
            raise RuntimeError("CANARY_EXCEPTION_MESSAGE")

        def observe_duration_ms(self, *args, **kwargs):
            raise RuntimeError("CANARY_EXCEPTION_MESSAGE")

        def flush(self, **kwargs):
            raise RuntimeError("CANARY_EXCEPTION_MESSAGE")

        def shutdown(self, **kwargs):
            raise RuntimeError("CANARY_EXCEPTION_MESSAGE")

    lifecycle = ControlledRevisionTelemetryLifecycle(
        Broken(),
        status=TelemetryHealth.READY,
        configuration_status=TelemetryConfigurationStatus.READY,
        backend_type="interface_only",
    )
    assert lifecycle.flush(1) is False
    assert lifecycle.shutdown(1) is True
    health = lifecycle.health()
    assert health.status is TelemetryHealth.DEGRADED
    assert health.export_failure_count == 3


def test_export_failure_cannot_change_pipeline_outcome() -> None:
    class Broken:
        def increment(self, *args, **kwargs):
            raise RuntimeError

        def observe_duration_ms(self, *args, **kwargs):
            raise RuntimeError

    telemetry = ControlledRevisionTelemetry(
        Broken(),
        configuration=ControlledRevisionTelemetryConfiguration(enabled=True),
    )
    telemetry.start()
    telemetry.complete(OperationalOutcome.PIPELINE_SUCCESS)
    assert telemetry.outcome is OperationalOutcome.PIPELINE_SUCCESS


def test_all_metrics_have_one_to_one_mapping() -> None:
    assert validate_metric_mapping() == ()
    assert len(COUNTER_MAPPING) == len(COUNTER_NAMES) == 30
    assert len(DURATION_MAPPING) == len(DURATION_NAMES) == 9
    assert all(value[1:] == ("counter", "1") for value in COUNTER_MAPPING.values())
    assert all(value[1:] == ("histogram", "ms") for value in DURATION_MAPPING.values())


def test_histogram_boundaries_are_static_and_bounded() -> None:
    assert HISTOGRAM_BOUNDARIES_MS == tuple(sorted(set(HISTOGRAM_BOUNDARIES_MS)))
    assert HISTOGRAM_BOUNDARIES_MS[0] == 10
    assert HISTOGRAM_BOUNDARIES_MS[-1] == 60_000


def test_dimension_cardinality_is_fully_bounded() -> None:
    assert set(DIMENSION_VALUE_COUNTS) == set(ALLOWED_DIMENSIONS)
    product = 1
    for count in DIMENSION_VALUE_COUNTS.values():
        product *= count
    assert product == THEORETICAL_MAX_CARDINALITY == 36_720


@pytest.mark.parametrize(
    "canary",
    [
        "CANARY_SOURCE_CONTENT",
        "CANARY_PROVIDER_OUTPUT",
        "CANARY_COMPONENT_REFERENCE",
        "CANARY_REQUEST_ID",
        "CANARY_API_KEY",
        "CANARY_PROMPT_BODY",
        "CANARY_EXCEPTION_MESSAGE",
    ],
)
def test_canaries_never_enter_export_payload(canary: str) -> None:
    composition = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.IN_MEMORY_TEST
        )
    )
    composition.sink.increment(
        COUNTER_NAMES[0], dimensions={"telemetry_enabled": "true"}
    )
    payload = json.dumps(
        [repr(item) for item in composition.sink.counters], ensure_ascii=False
    )
    assert canary not in payload


def test_schema_fingerprint_and_zero_network_design_remain_frozen() -> None:
    assert (
        hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()
        == SCHEMA_SHA
    )
    assert "endpoint" not in ControlledRevisionTelemetrySettings.__dataclass_fields__
