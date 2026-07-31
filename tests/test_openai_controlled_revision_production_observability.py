"""Part 6A privacy-safe production observability foundation."""

from __future__ import annotations

import hashlib
import json

import pytest

from pastila_scout.editor.generation.ai_provider_adapter import (
    COUNTER_NAMES,
    DURATION_NAMES,
    ControlledRevisionTelemetry,
    ControlledRevisionTelemetryConfiguration,
    InMemoryControlledRevisionMetricSink,
    IsolatedControlledRevisionMetricSink,
    NoOpControlledRevisionMetricSink,
    OperationalOutcome,
    RolloutStatus,
    SafeFailureCategory,
    ScenarioClass,
    Stage,
    calculate_rates,
    classify_safe_failure,
    evaluate_rollout,
    normalize_model_family,
    snapshot_from_sink,
    validate_stage_invariants,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    controlled_revision_schema_json,
)
from scripts.replay_controlled_revision_observability import replay

EXPECTED_SCHEMA = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"


def test_noop_sink_preserves_behavior() -> None:
    sink = NoOpControlledRevisionMetricSink()
    assert sink.increment(COUNTER_NAMES[0]) is None
    assert sink.observe_duration_ms(DURATION_NAMES[0], duration_ms=0) is None


def test_in_memory_sink_captures_bounded_metrics() -> None:
    sink = InMemoryControlledRevisionMetricSink()
    sink.increment(COUNTER_NAMES[0], dimensions={"provider_family": "openai"})
    sink.observe_duration_ms(DURATION_NAMES[0], duration_ms=1.5)
    assert sink.counters[0].value == 1
    assert sink.durations[0].value == 1.5
    with pytest.raises(ValueError, match="forbidden"):
        sink.increment(COUNTER_NAMES[0], dimensions={"request_id": "secret"})


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_durations_are_finite_and_non_negative(value: float) -> None:
    with pytest.raises(ValueError):
        InMemoryControlledRevisionMetricSink().observe_duration_ms(
            DURATION_NAMES[0], duration_ms=value
        )


def test_disabled_telemetry_uses_noop_even_when_sink_is_supplied() -> None:
    sink = InMemoryControlledRevisionMetricSink()
    telemetry = ControlledRevisionTelemetry(sink)
    telemetry.start()
    telemetry.complete(OperationalOutcome.LOCAL_RUNTIME_FAILURE)
    assert sink.counters == sink.durations == ()


def test_success_stage_order_and_terminal_uniqueness() -> None:
    telemetry, sink = replay(OperationalOutcome.PIPELINE_SUCCESS, acceptance="PASS")
    assert telemetry.stages == [
        Stage.EXECUTION_STARTED,
        Stage.PROVIDER_REQUEST_STARTED,
        Stage.PROVIDER_RESPONSE_RECEIVED,
        Stage.JSON_DECODE_STARTED,
        Stage.JSON_DECODE_PASSED,
        Stage.DTO_VALIDATION_STARTED,
        Stage.DTO_VALIDATION_PASSED,
        Stage.AUTHORIZATION_STARTED,
        Stage.AUTHORIZATION_PASSED,
        Stage.RECONSTRUCTION_STARTED,
        Stage.RECONSTRUCTION_PASSED,
        Stage.EPISODE_DRAFT_VALIDATION_STARTED,
        Stage.EPISODE_DRAFT_VALIDATION_PASSED,
        Stage.GATEWAY_STARTED,
        Stage.GATEWAY_PASSED,
        Stage.ACCEPTANCE_STARTED,
        Stage.ACCEPTANCE_PASSED,
        Stage.EXECUTION_COMPLETED,
    ]
    assert snapshot_from_sink(sink).pipeline_success_count == 1
    with pytest.raises(ValueError, match="already"):
        telemetry.complete(OperationalOutcome.PIPELINE_SUCCESS)


def test_acceptance_failure_remains_pipeline_success() -> None:
    telemetry, sink = replay(OperationalOutcome.PIPELINE_SUCCESS, acceptance="FAIL")
    snapshot = snapshot_from_sink(sink)
    assert telemetry.outcome is OperationalOutcome.PIPELINE_SUCCESS
    assert snapshot.acceptance_fail_count == snapshot.pipeline_success_count == 1


@pytest.mark.parametrize(
    ("category", "failure_stage"),
    [
        (
            SafeFailureCategory.DUPLICATE_COMPONENT_REFERENCE,
            Stage.DTO_VALIDATION_FAILED,
        ),
        (SafeFailureCategory.INVALID_JSON, Stage.JSON_DECODE_FAILED),
    ],
)
def test_safe_rejections_stop_before_authorization(category, failure_stage) -> None:
    telemetry, sink = replay(
        OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY, category=category
    )
    assert failure_stage in telemetry.stages
    assert Stage.AUTHORIZATION_STARTED not in telemetry.stages
    snapshot = snapshot_from_sink(sink)
    assert snapshot.safe_rejection_count == 1
    assert snapshot.safe_category_counts[category.value] == 1


def test_external_and_local_failures_are_distinct() -> None:
    _, external = replay(
        OperationalOutcome.EXTERNAL_PROVIDER_FAILURE,
        category=SafeFailureCategory.PROVIDER_TIMEOUT,
    )
    _, local = replay(
        OperationalOutcome.LOCAL_RUNTIME_FAILURE,
        category=SafeFailureCategory.UNEXPECTED_LOCAL_FAILURE,
    )
    assert snapshot_from_sink(external).external_failure_count == 1
    assert snapshot_from_sink(local).runtime_failure_count == 1


def test_failure_classifier_is_bounded_and_content_free() -> None:
    assert (
        classify_safe_failure(
            "provider_output_schema_invalid",
            {"duplicate_reference_validator_triggered": "yes"},
        )
        is SafeFailureCategory.DUPLICATE_COMPONENT_REFERENCE
    )
    assert (
        classify_safe_failure("unknown dynamic provider prose")
        is SafeFailureCategory.UNKNOWN_SAFE_REJECTION
    )


def test_sink_failure_is_suppressed_without_changing_outcome() -> None:
    class Broken:
        def increment(self, *args, **kwargs):
            raise RuntimeError("content-bearing backend failure")

        def observe_duration_ms(self, *args, **kwargs):
            raise RuntimeError("content-bearing backend failure")

    telemetry = ControlledRevisionTelemetry(
        IsolatedControlledRevisionMetricSink(Broken()),
        configuration=ControlledRevisionTelemetryConfiguration(enabled=True),
    )
    telemetry.start()
    telemetry.complete(OperationalOutcome.PIPELINE_SUCCESS)
    assert telemetry.outcome is OperationalOutcome.PIPELINE_SUCCESS


def test_snapshot_rates_percentiles_and_invariants() -> None:
    _, sink = replay(OperationalOutcome.PIPELINE_SUCCESS, acceptance="PASS")
    snapshot = snapshot_from_sink(sink)
    rates = calculate_rates(snapshot)
    assert rates["dto_success_rate"] == 1
    assert rates["editorial_acceptance_pass_rate"] == 1
    assert snapshot.p50_duration_ms is not None
    assert snapshot.p95_duration_ms is not None
    assert validate_stage_invariants(snapshot) == ()
    assert evaluate_rollout(snapshot) is RolloutStatus.OPERATIONALLY_HEALTHY


def test_zero_denominators_are_explicitly_unavailable() -> None:
    snapshot = snapshot_from_sink(InMemoryControlledRevisionMetricSink())
    assert set(calculate_rates(snapshot).values()) == {None}
    assert evaluate_rollout(snapshot) is RolloutStatus.INSUFFICIENT_SAMPLE


def test_inconsistent_snapshot_is_detected() -> None:
    sink = InMemoryControlledRevisionMetricSink()
    sink.increment("controlled_revision.provider.responses.total")
    snapshot = snapshot_from_sink(sink)
    assert validate_stage_invariants(snapshot) == (
        "provider_responses_exceed_requests",
    )
    assert evaluate_rollout(snapshot) is RolloutStatus.TELEMETRY_INCONSISTENT


def test_dimensions_never_contain_content_or_identifiers() -> None:
    _, sink = replay(OperationalOutcome.PIPELINE_SUCCESS, acceptance="PASS")
    serialized = json.dumps(
        [
            record.__dict__ if hasattr(record, "__dict__") else repr(record)
            for record in sink.counters
        ]
    )
    forbidden = (
        "component_reference",
        "request_id",
        "prompt",
        "credential",
        "source_url",
    )
    assert not any(value in serialized for value in forbidden)


def test_scenario_and_model_classification_are_bounded() -> None:
    assert len(ScenarioClass) == 5
    assert normalize_model_family("gpt-4.1-mini") == "gpt-4.1"
    assert normalize_model_family("customer/model/identifier") is None


def test_frozen_schema_fingerprint_is_unchanged() -> None:
    digest = hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()
    assert digest == EXPECTED_SCHEMA
