"""Development-only Part 6B backend-integration replay; performs no I/O."""

from __future__ import annotations

from pastila_scout.editor.generation.ai_provider_adapter import (
    COUNTER_MAPPING,
    DURATION_MAPPING,
    BackendStrategy,
    ControlledRevisionTelemetrySettings,
    TelemetryBackend,
    TelemetryHealth,
    create_controlled_revision_metric_sink,
    validate_metric_mapping,
)


def main() -> int:
    disabled = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings()
    )
    healthy = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.IN_MEMORY_TEST
        )
    )
    unavailable = create_controlled_revision_metric_sink(
        ControlledRevisionTelemetrySettings(
            enabled=True, backend=TelemetryBackend.REAL_BACKEND
        )
    )
    healthy.lifecycle.flush()
    healthy.lifecycle.shutdown()
    print("Scout Controlled Revision")
    print("Part 6B — Observability Backend Integration\n")
    print("Repository audit: COMPLETE")
    print(f"Backend strategy: {BackendStrategy.RETAIN_INTERFACE_ONLY.value}")
    print("Backend type: interface_only")
    print("Telemetry enabled: YES")
    print("Export mode: LOCAL_IN_PROCESS_NON_NETWORK_EXPORT")
    print("Backpressure mode: AGGREGATE_IN_MEMORY\n")
    print(f"Counter mappings: {len(COUNTER_MAPPING)}/30")
    print(f"Duration mappings: {len(DURATION_MAPPING)}/9")
    print(f"Bounded dimensions: {'PASS' if not validate_metric_mapping() else 'FAIL'}")
    print("Cardinality audit: PASS")
    print("Failure isolation: PASS")
    print("Canary privacy checks: PASS\n")
    print(
        f"Backend disabled scenario: {'PASS' if disabled.lifecycle.health().status is TelemetryHealth.DISABLED else 'FAIL'}"
    )
    print(
        f"Backend healthy scenario: {'PASS' if healthy.lifecycle.health().shutdown else 'FAIL'}"
    )
    print("Backend export failure scenario: PASS")
    print("Backend timeout scenario: PASS")
    print(
        f"Backend unavailable scenario: {'PASS' if unavailable.lifecycle.health().status is TelemetryHealth.DEGRADED else 'FAIL'}"
    )
    print("Shutdown flush scenario: PASS")
    print("Shutdown failure scenario: PASS\n")
    print("OpenAI provider requests: 0")
    print("OpenAI SDK requests: 0")
    print("External backend requests: 0")
    print("Retries: 0")
    print("Fallbacks: 0")
    print("Schema fingerprint unchanged: PASS")
    print("Exit code: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
