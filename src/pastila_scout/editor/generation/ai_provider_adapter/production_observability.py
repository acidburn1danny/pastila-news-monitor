"""Privacy-safe operational telemetry for Controlled Revision.

This module contains no provider transport and observes, but never controls, the
business pipeline.  All labels are repository-owned bounded enum values.
"""

# Telemetry backends are untrusted; isolation deliberately catches all failures.
# ruff: noqa: BLE001

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from types import MappingProxyType
from typing import Protocol


class OperationalOutcome(StrEnum):
    PIPELINE_SUCCESS = "PIPELINE_SUCCESS"
    PROVIDER_OUTPUT_REJECTED_SAFELY = "PROVIDER_OUTPUT_REJECTED_SAFELY"
    EXTERNAL_PROVIDER_FAILURE = "EXTERNAL_PROVIDER_FAILURE"
    LOCAL_RUNTIME_FAILURE = "LOCAL_RUNTIME_FAILURE"


class SafeFailureCategory(StrEnum):
    DUPLICATE_COMPONENT_REFERENCE = "duplicate_component_reference"
    REFERENCE_TYPE_MISMATCH = "reference_type_mismatch"
    INVALID_COMPONENT_SHAPE = "invalid_component_shape"
    INVALID_PAYLOAD_STRUCTURE = "invalid_payload_structure"
    INVALID_JSON = "invalid_json"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNAUTHORIZED_REFERENCE = "unauthorized_reference"
    MISSING_AUTHORIZED_REFERENCE = "missing_authorized_reference"
    COMPONENT_COUNT_MISMATCH = "component_count_mismatch"
    COMPONENT_ORDER_MISMATCH = "component_order_mismatch"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    PROVIDER_AUTHENTICATION = "provider_authentication"
    PROVIDER_TRANSPORT = "provider_transport"
    PROVIDER_SERVER_ERROR = "provider_server_error"
    UNEXPECTED_LOCAL_FAILURE = "unexpected_local_failure"
    UNKNOWN_SAFE_REJECTION = "unknown_safe_rejection"


class Stage(StrEnum):
    EXECUTION_STARTED = "execution_started"
    PROVIDER_REQUEST_STARTED = "provider_request_started"
    PROVIDER_RESPONSE_RECEIVED = "provider_response_received"
    PROVIDER_REQUEST_FAILED = "provider_request_failed"
    JSON_DECODE_STARTED = "json_decode_started"
    JSON_DECODE_PASSED = "json_decode_passed"
    JSON_DECODE_FAILED = "json_decode_failed"
    DTO_VALIDATION_STARTED = "DTO_validation_started"
    DTO_VALIDATION_PASSED = "DTO_validation_passed"
    DTO_VALIDATION_FAILED = "DTO_validation_failed"
    AUTHORIZATION_STARTED = "authorization_started"
    AUTHORIZATION_PASSED = "authorization_passed"
    AUTHORIZATION_FAILED = "authorization_failed"
    RECONSTRUCTION_STARTED = "reconstruction_started"
    RECONSTRUCTION_PASSED = "reconstruction_passed"
    RECONSTRUCTION_FAILED = "reconstruction_failed"
    EPISODE_DRAFT_VALIDATION_STARTED = "episode_draft_validation_started"
    EPISODE_DRAFT_VALIDATION_PASSED = "episode_draft_validation_passed"
    EPISODE_DRAFT_VALIDATION_FAILED = "episode_draft_validation_failed"
    GATEWAY_STARTED = "gateway_started"
    GATEWAY_PASSED = "gateway_passed"
    GATEWAY_FAILED = "gateway_failed"
    ACCEPTANCE_STARTED = "acceptance_started"
    ACCEPTANCE_PASSED = "acceptance_passed"
    ACCEPTANCE_FAILED = "acceptance_failed"
    EXECUTION_COMPLETED = "execution_completed"


class ScenarioClass(StrEnum):
    MINIMAL_CLARITY = "MINIMAL_CLARITY"
    SUBSTANTIAL_REWRITE = "SUBSTANTIAL_REWRITE"
    PROTECTED_STRUCTURE = "PROTECTED_STRUCTURE"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    PRODUCTION_UNCLASSIFIED = "PRODUCTION_UNCLASSIFIED"


class RolloutStatus(StrEnum):
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    OPERATIONALLY_HEALTHY = "OPERATIONALLY_HEALTHY"
    ELEVATED_SAFE_REJECTION_RATE = "ELEVATED_SAFE_REJECTION_RATE"
    ELEVATED_EXTERNAL_FAILURE_RATE = "ELEVATED_EXTERNAL_FAILURE_RATE"
    RUNTIME_SAFETY_VIOLATION = "RUNTIME_SAFETY_VIOLATION"
    TELEMETRY_INCONSISTENT = "TELEMETRY_INCONSISTENT"


ALLOWED_DIMENSIONS = frozenset(
    {
        "operational_outcome",
        "scenario_class",
        "provider_family",
        "model_family",
        "failure_layer",
        "safe_failure_category",
        "acceptance_result",
        "telemetry_enabled",
        "environment_class",
    }
)

COUNTER_NAMES = (
    "controlled_revision.executions.total",
    "controlled_revision.provider.requests.total",
    "controlled_revision.provider.responses.total",
    "controlled_revision.provider.failures.total",
    "controlled_revision.json_decode.pass.total",
    "controlled_revision.json_decode.fail.total",
    "controlled_revision.dto.pass.total",
    "controlled_revision.dto.fail.total",
    "controlled_revision.safe_rejections.total",
    "controlled_revision.authorization.reached.total",
    "controlled_revision.authorization.pass.total",
    "controlled_revision.authorization.fail.total",
    "controlled_revision.reconstruction.reached.total",
    "controlled_revision.reconstruction.pass.total",
    "controlled_revision.reconstruction.fail.total",
    "controlled_revision.episode_draft.pass.total",
    "controlled_revision.episode_draft.fail.total",
    "controlled_revision.gateway.reached.total",
    "controlled_revision.gateway.pass.total",
    "controlled_revision.gateway.fail.total",
    "controlled_revision.acceptance.reached.total",
    "controlled_revision.acceptance.pass.total",
    "controlled_revision.acceptance.fail.total",
    "controlled_revision.pipeline_success.total",
    "controlled_revision.external_failure.total",
    "controlled_revision.runtime_failure.total",
    "controlled_revision.retries.total",
    "controlled_revision.provider_fallbacks.total",
    "controlled_revision.model_fallbacks.total",
    "controlled_revision.telemetry_failures.total",
)

DURATION_NAMES = (
    "controlled_revision.execution.duration_ms",
    "controlled_revision.provider.duration_ms",
    "controlled_revision.json_decode.duration_ms",
    "controlled_revision.dto_validation.duration_ms",
    "controlled_revision.authorization.duration_ms",
    "controlled_revision.reconstruction.duration_ms",
    "controlled_revision.episode_draft_validation.duration_ms",
    "controlled_revision.gateway.duration_ms",
    "controlled_revision.acceptance.duration_ms",
)


class ControlledRevisionMetricSink(Protocol):
    def increment(
        self,
        name: str,
        *,
        value: int = 1,
        dimensions: Mapping[str, str] | None = None,
    ) -> None: ...

    def observe_duration_ms(
        self,
        name: str,
        *,
        duration_ms: float,
        dimensions: Mapping[str, str] | None = None,
    ) -> None: ...


class NoOpControlledRevisionMetricSink:
    """Production-safe default sink."""

    def increment(self, name, *, value=1, dimensions=None) -> None:
        return None

    def observe_duration_ms(self, name, *, duration_ms, dimensions=None) -> None:
        return None


@dataclass(frozen=True, slots=True)
class MetricRecord:
    name: str
    value: float
    dimensions: tuple[tuple[str, str], ...]


class InMemoryControlledRevisionMetricSink:
    """Strict content-free sink for tests and local aggregate replay."""

    def __init__(self) -> None:
        self._counters: list[MetricRecord] = []
        self._durations: list[MetricRecord] = []

    @property
    def counters(self) -> tuple[MetricRecord, ...]:
        return tuple(self._counters)

    @property
    def durations(self) -> tuple[MetricRecord, ...]:
        return tuple(self._durations)

    def increment(self, name, *, value=1, dimensions=None) -> None:
        if name not in COUNTER_NAMES or not isinstance(value, int) or value < 0:
            raise ValueError("invalid controlled-revision counter")
        self._counters.append(MetricRecord(name, value, _dimensions(dimensions)))

    def observe_duration_ms(self, name, *, duration_ms, dimensions=None) -> None:
        if name not in DURATION_NAMES:
            raise ValueError("invalid controlled-revision duration")
        value = float(duration_ms)
        if not math.isfinite(value) or value < 0:
            raise ValueError("duration must be finite and non-negative")
        self._durations.append(MetricRecord(name, value, _dimensions(dimensions)))


class IsolatedControlledRevisionMetricSink:
    """Suppress every backend failure so telemetry remains transparent."""

    def __init__(self, sink: ControlledRevisionMetricSink) -> None:
        self.sink = sink
        self.failure_count = 0

    def increment(self, name, *, value=1, dimensions=None) -> None:
        self._call(self.sink.increment, name, value=value, dimensions=dimensions)

    def observe_duration_ms(self, name, *, duration_ms, dimensions=None) -> None:
        self._call(
            self.sink.observe_duration_ms,
            name,
            duration_ms=duration_ms,
            dimensions=dimensions,
        )

    def _call(self, function, name, **kwargs) -> None:
        try:
            function(name, **kwargs)
        except Exception:  # telemetry backends are never authoritative
            self.failure_count += 1


@dataclass(frozen=True, slots=True)
class ControlledRevisionTelemetryConfiguration:
    enabled: bool = False
    scenario_class: ScenarioClass = ScenarioClass.PRODUCTION_UNCLASSIFIED
    provider_family: str | None = None
    model_family: str | None = None
    environment_class: str = "production"


@dataclass(frozen=True, slots=True)
class OperationalSnapshot:
    execution_count: int
    provider_request_count: int
    provider_response_count: int
    dto_pass_count: int
    dto_fail_count: int
    json_decode_fail_count: int
    safe_rejection_count: int
    authorization_reached_count: int
    authorization_pass_count: int
    reconstruction_reached_count: int
    reconstruction_pass_count: int
    episode_draft_pass_count: int
    gateway_reached_count: int
    gateway_pass_count: int
    acceptance_reached_count: int
    acceptance_pass_count: int
    acceptance_fail_count: int
    pipeline_success_count: int
    external_failure_count: int
    runtime_failure_count: int
    retry_count: int
    provider_fallback_count: int
    model_fallback_count: int
    duration_count: int
    p50_duration_ms: float | None
    p95_duration_ms: float | None
    safe_category_counts: Mapping[str, int]


class ControlledRevisionTelemetry:
    """Execution-scoped stage recorder with exactly one terminal outcome."""

    def __init__(self, sink=None, *, configuration=None, clock: Callable = monotonic):
        self.configuration = configuration or ControlledRevisionTelemetryConfiguration()
        backend = (
            sink
            if self.configuration.enabled and sink
            else NoOpControlledRevisionMetricSink()
        )
        self.sink = IsolatedControlledRevisionMetricSink(backend)
        self.clock = clock
        self.stages: list[Stage] = []
        self._started: dict[str, float] = {}
        self.outcome: OperationalOutcome | None = None
        self.safe_category: SafeFailureCategory | None = None

    def start(self) -> None:
        self._stage(Stage.EXECUTION_STARTED)
        self._started["execution"] = self.clock()
        self._increment("controlled_revision.executions.total")

    def begin(self, stage: Stage, duration_key: str | None = None) -> None:
        self._stage(stage)
        if duration_key:
            self._started[duration_key] = self.clock()

    def pass_stage(
        self,
        stage: Stage,
        *,
        counter: str | None = None,
        duration_key: str | None = None,
    ) -> None:
        self._stage(stage)
        if counter:
            self._increment(counter)
        if duration_key:
            self._duration(duration_key)

    def fail_stage(
        self,
        stage: Stage,
        *,
        counter: str | None = None,
        duration_key: str | None = None,
    ) -> None:
        self.pass_stage(stage, counter=counter, duration_key=duration_key)

    def increment(self, name: str, value: int = 1) -> None:
        self._increment(name, value)

    def complete(
        self,
        outcome: OperationalOutcome,
        *,
        safe_category: SafeFailureCategory | None = None,
        acceptance_result: str | None = None,
    ) -> None:
        if self.outcome is not None:
            raise ValueError("terminal operational outcome already recorded")
        self.outcome = outcome
        self.safe_category = safe_category
        outcome_counter = {
            OperationalOutcome.PIPELINE_SUCCESS: "controlled_revision.pipeline_success.total",
            OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY: "controlled_revision.safe_rejections.total",
            OperationalOutcome.EXTERNAL_PROVIDER_FAILURE: "controlled_revision.external_failure.total",
            OperationalOutcome.LOCAL_RUNTIME_FAILURE: "controlled_revision.runtime_failure.total",
        }[outcome]
        extra = {"operational_outcome": outcome.value}
        if safe_category:
            extra["safe_failure_category"] = safe_category.value
        if acceptance_result:
            extra["acceptance_result"] = acceptance_result
        self._increment(outcome_counter, dimensions=extra)
        self._duration("execution")
        self._stage(Stage.EXECUTION_COMPLETED)

    def _stage(self, stage: Stage) -> None:
        if self.stages and self.stages[-1] is Stage.EXECUTION_COMPLETED:
            raise ValueError("execution already completed")
        self.stages.append(stage)

    def _duration(self, key: str) -> None:
        started = self._started.pop(key, None)
        if started is None:
            return
        self.sink.observe_duration_ms(
            f"controlled_revision.{key}.duration_ms",
            duration_ms=max(0.0, (self.clock() - started) * 1000),
            dimensions=self._base_dimensions(),
        )

    def _increment(self, name, value=1, dimensions=None) -> None:
        merged = dict(self._base_dimensions())
        merged.update(dimensions or {})
        self.sink.increment(name, value=value, dimensions=merged)

    def _base_dimensions(self) -> dict[str, str]:
        config = self.configuration
        result = {
            "scenario_class": config.scenario_class.value,
            "telemetry_enabled": "true" if config.enabled else "false",
            "environment_class": config.environment_class,
        }
        if config.provider_family in {"openai"}:
            result["provider_family"] = config.provider_family
        if config.model_family in {"gpt-4.1"}:
            result["model_family"] = config.model_family
        return result


def classify_safe_failure(code: str, metadata: Mapping[str, str] | None = None):
    """Map stable internal codes to one bounded, content-free category."""

    data = metadata or {}
    probable = data.get("probable_primary_failure_category")
    if data.get("duplicate_reference_validator_triggered") == "yes":
        return SafeFailureCategory.DUPLICATE_COMPONENT_REFERENCE
    mappings = {
        "structured_output_malformed_json": SafeFailureCategory.INVALID_JSON,
        "reconstruction_reference_type_mismatch": SafeFailureCategory.REFERENCE_TYPE_MISMATCH,
        "reconstruction_unauthorized_reference": SafeFailureCategory.UNAUTHORIZED_REFERENCE,
        "reconstruction_missing_reference": SafeFailureCategory.MISSING_AUTHORIZED_REFERENCE,
        "reconstruction_component_count_mismatch": SafeFailureCategory.COMPONENT_COUNT_MISMATCH,
        "reconstruction_component_order_mismatch": SafeFailureCategory.COMPONENT_ORDER_MISMATCH,
        "provider_timeout": SafeFailureCategory.PROVIDER_TIMEOUT,
        "provider_rate_limited": SafeFailureCategory.PROVIDER_RATE_LIMIT,
        "authentication_failed": SafeFailureCategory.PROVIDER_AUTHENTICATION,
        "provider_transport_failed": SafeFailureCategory.PROVIDER_TRANSPORT,
        "provider_unavailable": SafeFailureCategory.PROVIDER_SERVER_ERROR,
    }
    if code in mappings:
        return mappings[code]
    probable_map = {
        "missing_required_field": SafeFailureCategory.MISSING_REQUIRED_FIELD,
        "invalid_component_shape": SafeFailureCategory.INVALID_COMPONENT_SHAPE,
        "duplicate_component_reference": SafeFailureCategory.DUPLICATE_COMPONENT_REFERENCE,
    }
    return probable_map.get(probable, SafeFailureCategory.UNKNOWN_SAFE_REJECTION)


def snapshot_from_sink(
    sink: InMemoryControlledRevisionMetricSink,
) -> OperationalSnapshot:
    totals = Counter()
    categories = Counter()
    for record in sink.counters:
        totals[record.name] += int(record.value)
        dimensions = dict(record.dimensions)
        if category := dimensions.get("safe_failure_category"):
            categories[category] += int(record.value)
    execution_durations = sorted(
        item.value
        for item in sink.durations
        if item.name == "controlled_revision.execution.duration_ms"
    )
    get = totals.__getitem__
    return OperationalSnapshot(
        execution_count=get("controlled_revision.executions.total"),
        provider_request_count=get("controlled_revision.provider.requests.total"),
        provider_response_count=get("controlled_revision.provider.responses.total"),
        dto_pass_count=get("controlled_revision.dto.pass.total"),
        dto_fail_count=get("controlled_revision.dto.fail.total"),
        json_decode_fail_count=get("controlled_revision.json_decode.fail.total"),
        safe_rejection_count=get("controlled_revision.safe_rejections.total"),
        authorization_reached_count=get(
            "controlled_revision.authorization.reached.total"
        ),
        authorization_pass_count=get("controlled_revision.authorization.pass.total"),
        reconstruction_reached_count=get(
            "controlled_revision.reconstruction.reached.total"
        ),
        reconstruction_pass_count=get("controlled_revision.reconstruction.pass.total"),
        episode_draft_pass_count=get("controlled_revision.episode_draft.pass.total"),
        gateway_reached_count=get("controlled_revision.gateway.reached.total"),
        gateway_pass_count=get("controlled_revision.gateway.pass.total"),
        acceptance_reached_count=get("controlled_revision.acceptance.reached.total"),
        acceptance_pass_count=get("controlled_revision.acceptance.pass.total"),
        acceptance_fail_count=get("controlled_revision.acceptance.fail.total"),
        pipeline_success_count=get("controlled_revision.pipeline_success.total"),
        external_failure_count=get("controlled_revision.external_failure.total"),
        runtime_failure_count=get("controlled_revision.runtime_failure.total"),
        retry_count=get("controlled_revision.retries.total"),
        provider_fallback_count=get("controlled_revision.provider_fallbacks.total"),
        model_fallback_count=get("controlled_revision.model_fallbacks.total"),
        duration_count=len(execution_durations),
        p50_duration_ms=_percentile(execution_durations, 0.50),
        p95_duration_ms=_percentile(execution_durations, 0.95),
        safe_category_counts=MappingProxyType(dict(sorted(categories.items()))),
    )


def calculate_rates(snapshot: OperationalSnapshot) -> Mapping[str, float | None]:
    dto_reached = snapshot.dto_pass_count + snapshot.dto_fail_count
    return MappingProxyType(
        {
            "dto_success_rate": _ratio(snapshot.dto_pass_count, dto_reached),
            "safe_rejection_rate": _ratio(
                snapshot.safe_rejection_count, snapshot.provider_response_count
            ),
            "pipeline_success_rate": _ratio(
                snapshot.pipeline_success_count, snapshot.execution_count
            ),
            "external_failure_rate": _ratio(
                snapshot.external_failure_count, snapshot.execution_count
            ),
            "runtime_failure_rate": _ratio(
                snapshot.runtime_failure_count, snapshot.execution_count
            ),
            "editorial_acceptance_pass_rate": _ratio(
                snapshot.acceptance_pass_count, snapshot.acceptance_reached_count
            ),
            "gateway_reach_rate": _ratio(
                snapshot.gateway_reached_count, snapshot.execution_count
            ),
        }
    )


def validate_stage_invariants(snapshot: OperationalSnapshot) -> tuple[str, ...]:
    checks = {
        "provider_responses_exceed_requests": snapshot.provider_response_count
        > snapshot.provider_request_count,
        "dto_results_exceed_responses": snapshot.dto_pass_count
        + snapshot.dto_fail_count
        > snapshot.provider_response_count,
        "authorization_exceeds_dto_pass": snapshot.authorization_reached_count
        > snapshot.dto_pass_count,
        "reconstruction_exceeds_authorization": snapshot.reconstruction_reached_count
        > snapshot.authorization_pass_count,
        "gateway_exceeds_episode_draft": snapshot.gateway_reached_count
        > snapshot.episode_draft_pass_count,
        "acceptance_exceeds_gateway": snapshot.acceptance_reached_count
        > snapshot.gateway_pass_count,
        "success_exceeds_acceptance": snapshot.pipeline_success_count
        > snapshot.acceptance_reached_count,
        "safe_rejections_exceed_validation_failures": snapshot.safe_rejection_count
        > snapshot.dto_fail_count + snapshot.json_decode_fail_count,
        "retries_present": snapshot.retry_count != 0,
        "provider_fallbacks_present": snapshot.provider_fallback_count != 0,
        "model_fallbacks_present": snapshot.model_fallback_count != 0,
    }
    return tuple(name for name, failed in checks.items() if failed)


def evaluate_rollout(snapshot: OperationalSnapshot, *, minimum_sample: int = 1):
    if validate_stage_invariants(snapshot):
        return RolloutStatus.TELEMETRY_INCONSISTENT
    if snapshot.runtime_failure_count:
        return RolloutStatus.RUNTIME_SAFETY_VIOLATION
    if snapshot.execution_count < minimum_sample:
        return RolloutStatus.INSUFFICIENT_SAMPLE
    return RolloutStatus.OPERATIONALLY_HEALTHY


def normalize_model_family(model: str) -> str | None:
    """Return only explicitly bounded model families."""

    return "gpt-4.1" if model == "gpt-4.1" or model.startswith("gpt-4.1-") else None


def _dimensions(values: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    result = values or {}
    if not set(result).issubset(ALLOWED_DIMENSIONS):
        raise ValueError("forbidden controlled-revision metric dimension")
    if any(not isinstance(value, str) or len(value) > 64 for value in result.values()):
        raise ValueError("invalid controlled-revision metric dimension value")
    return tuple(sorted(result.items()))


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    index = max(0, math.ceil(quantile * len(values)) - 1)
    return values[index]
