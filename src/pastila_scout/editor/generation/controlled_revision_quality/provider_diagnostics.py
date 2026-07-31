"""Provider-neutral, content-free benchmark diagnostic contracts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import tempfile
from collections import Counter
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .pricing import BenchmarkPricingSpecification

MALFORMED_REFERENCE = "<MALFORMED_REFERENCE>"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProviderOperationalOutcome(StrEnum):
    PIPELINE_SUCCESS = "PIPELINE_SUCCESS"
    PROVIDER_OUTPUT_REJECTED_SAFELY = "PROVIDER_OUTPUT_REJECTED_SAFELY"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_SERVICE_FAILURE = "PROVIDER_SERVICE_FAILURE"
    PROVIDER_TRANSPORT_FAILURE = "PROVIDER_TRANSPORT_FAILURE"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    BENCHMARK_INTERNAL_FAILURE = "BENCHMARK_INTERNAL_FAILURE"
    BENCHMARK_ABORTED = "BENCHMARK_ABORTED"


class DiagnosticFailureStage(StrEnum):
    REQUEST_CONSTRUCTION = "REQUEST_CONSTRUCTION"
    PROVIDER_CALL = "PROVIDER_CALL"
    PROVIDER_RESPONSE_CAPTURE = "PROVIDER_RESPONSE_CAPTURE"
    JSON_PARSE = "JSON_PARSE"
    PROVIDER_DTO_VALIDATION = "PROVIDER_DTO_VALIDATION"
    REFERENCE_MAPPING = "REFERENCE_MAPPING"
    AUTHORIZATION = "AUTHORIZATION"
    RECONSTRUCTION = "RECONSTRUCTION"
    EPISODE_DRAFT_VALIDATION = "EPISODE_DRAFT_VALIDATION"
    EDITORIAL_ACCEPTANCE = "EDITORIAL_ACCEPTANCE"
    QUALITY_EVALUATION = "QUALITY_EVALUATION"
    ARTIFACT_PERSISTENCE = "ARTIFACT_PERSISTENCE"
    HISTORY_APPEND = "HISTORY_APPEND"
    NONE = "NONE"


class FirstInvalidReferenceKind(StrEnum):
    UNKNOWN = "UNKNOWN"
    UNAUTHORIZED = "UNAUTHORIZED"
    DUPLICATE = "DUPLICATE"
    MALFORMED = "MALFORMED"
    NONE = "NONE"


class TotalTokensSource(StrEnum):
    PROVIDER_REPORTED = "PROVIDER_REPORTED"
    BENCHMARK_DERIVED = "BENCHMARK_DERIVED"
    UNAVAILABLE = "UNAVAILABLE"


class CostStatus(StrEnum):
    CALCULATED = "CALCULATED"
    INSUFFICIENT_USAGE = "INSUFFICIENT_USAGE"
    PRICING_UNAVAILABLE = "PRICING_UNAVAILABLE"


class ProviderUsageDiagnostic(FrozenModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    cached_prompt_tokens: int | None = Field(default=None, ge=0)
    input_audio_tokens: int | None = Field(default=None, ge=0)
    output_audio_tokens: int | None = Field(default=None, ge=0)
    provider_reported_total_tokens: int | None = Field(default=None, ge=0)
    derived_total_tokens: int | None = Field(default=None, ge=0)
    total_tokens_source: TotalTokensSource = TotalTokensSource.UNAVAILABLE

    @model_validator(mode="after")
    def validate_total_source(self):
        if self.provider_reported_total_tokens is not None:
            if self.total_tokens_source is not TotalTokensSource.PROVIDER_REPORTED:
                raise ValueError("provider total requires provider-reported source")
        elif self.prompt_tokens is not None and self.completion_tokens is not None:
            expected = self.prompt_tokens + self.completion_tokens
            if self.derived_total_tokens != expected:
                raise ValueError("derived token total is inconsistent")
            if self.total_tokens_source is not TotalTokensSource.BENCHMARK_DERIVED:
                raise ValueError("derived total requires benchmark-derived source")
        elif self.total_tokens_source is not TotalTokensSource.UNAVAILABLE:
            raise ValueError("unavailable total requires unavailable source")
        return self

    @property
    def effective_total_tokens(self) -> int | None:
        return (
            self.provider_reported_total_tokens
            if self.provider_reported_total_tokens is not None
            else self.derived_total_tokens
        )


class ProviderCostDiagnostic(FrozenModel):
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    cost_status: CostStatus
    pricing_version: str | None = None
    pricing_effective_date: str | None = None
    pricing_source: str | None = None
    estimated: bool = True


class ReferenceDiagnostic(FrozenModel):
    authorized_references: tuple[str, ...]
    provider_produced_references_ordered: tuple[str, ...]
    recognized_provider_references: tuple[str, ...]
    unknown_references: tuple[str, ...]
    unauthorized_references: tuple[str, ...]
    missing_authorized_references: tuple[str, ...]
    unexpected_references: tuple[str, ...]
    duplicate_provider_references: tuple[str, ...]
    first_invalid_reference: str | None
    first_invalid_reference_kind: FirstInvalidReferenceKind
    reference_overlap_count: int = Field(ge=0)
    authorized_reference_count: int = Field(ge=0)
    provider_reference_count: int = Field(ge=0)
    reference_precision: float | None = Field(default=None, ge=0, le=1)
    reference_recall: float | None = Field(default=None, ge=0, le=1)


class ProviderTrialDiagnostic(FrozenModel):
    scenario_id: str = Field(pattern=r"^[A-Z0-9_-]+$", max_length=100)
    category: str = Field(pattern=r"^[A-Z0-9_-]+$", max_length=100)
    provider: str = Field(pattern=r"^[a-z0-9.-]+$", max_length=100)
    model: str = Field(pattern=r"^[a-zA-Z0-9._-]+$", max_length=200)
    operational_outcome: ProviderOperationalOutcome
    failure_code: str | None = Field(
        default=None, pattern=r"^[a-z0-9_]+$", max_length=100
    )
    failure_stage: DiagnosticFailureStage
    references: ReferenceDiagnostic
    provider_latency_ms: float | None = Field(default=None, ge=0)
    usage: ProviderUsageDiagnostic
    cost: ProviderCostDiagnostic
    provider_request_id_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )


class ProviderDiagnosticsArtifact(FrozenModel):
    schema_version: int = 1
    benchmark_id: str | None = None
    provider: str | None = None
    model: str | None = None
    schema_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_version: str
    trials: tuple[ProviderTrialDiagnostic, ...] = ()
    aggregate: dict[str, object] | None = None


def hash_provider_request_id(value: str | None) -> str | None:
    """Hash a provider identifier without retaining its raw value."""

    if not value:
        return None
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def safe_reference(value: object) -> str:
    """Return a bounded structural reference or a non-content sentinel."""

    if not isinstance(value, str) or not (1 <= len(value) <= 100):
        return MALFORMED_REFERENCE
    if value in {"opening", "closing", "call_to_action"}:
        return value
    parts = value.split(":")
    if len(parts) == 2 and parts[0] == "story" and parts[1].isdigit():
        return value
    if (
        len(parts) == 3
        and parts[0] == "transition"
        and parts[1].isdigit()
        and parts[2].isdigit()
    ):
        return value
    return MALFORMED_REFERENCE


def build_reference_diagnostic(
    *,
    authorized: tuple[str, ...],
    produced: tuple[object, ...],
    recognized_registry: frozenset[str],
    required: tuple[str, ...] | None = None,
) -> ReferenceDiagnostic:
    """Compare ordered provider references with exact invocation authorization."""

    safe = tuple(safe_reference(value) for value in produced)
    authorized_set = set(authorized)
    recognized = tuple(
        sorted({value for value in safe if value in recognized_registry})
    )
    unknown = tuple(
        sorted({value for value in safe if value not in recognized_registry})
    )
    unauthorized = tuple(sorted(set(recognized) - authorized_set))
    required_values = set(authorized if required is None else required)
    missing = tuple(sorted(required_values - set(safe)))
    unexpected = tuple(sorted(set(unknown) | set(unauthorized)))
    counts = Counter(safe)
    duplicates = tuple(sorted(value for value, count in counts.items() if count > 1))
    first, kind = _first_invalid(safe, authorized_set, recognized_registry, counts)
    true_positives = len(authorized_set & set(safe))
    precision = true_positives / len(set(safe)) if safe else None
    recall = true_positives / len(required_values) if required_values else None
    return ReferenceDiagnostic(
        authorized_references=authorized,
        provider_produced_references_ordered=safe,
        recognized_provider_references=recognized,
        unknown_references=unknown,
        unauthorized_references=unauthorized,
        missing_authorized_references=missing,
        unexpected_references=unexpected,
        duplicate_provider_references=duplicates,
        first_invalid_reference=first,
        first_invalid_reference_kind=kind,
        reference_overlap_count=true_positives,
        authorized_reference_count=len(authorized),
        provider_reference_count=len(safe),
        reference_precision=precision,
        reference_recall=recall,
    )


def _first_invalid(safe, authorized, registry, counts):
    seen: set[str] = set()
    for value in safe:
        if value == MALFORMED_REFERENCE:
            return value, FirstInvalidReferenceKind.MALFORMED
        if value in seen and counts[value] > 1:
            return value, FirstInvalidReferenceKind.DUPLICATE
        seen.add(value)
        if value not in registry:
            return value, FirstInvalidReferenceKind.UNKNOWN
        if value not in authorized:
            return value, FirstInvalidReferenceKind.UNAUTHORIZED
    return None, FirstInvalidReferenceKind.NONE


def build_usage_diagnostic(
    *, prompt: int | None, completion: int | None, total: int | None, **details
) -> ProviderUsageDiagnostic:
    derived = (
        prompt + completion
        if total is None and prompt is not None and completion is not None
        else None
    )
    source = (
        TotalTokensSource.PROVIDER_REPORTED
        if total is not None
        else (
            TotalTokensSource.BENCHMARK_DERIVED
            if derived is not None
            else TotalTokensSource.UNAVAILABLE
        )
    )
    return ProviderUsageDiagnostic(
        prompt_tokens=prompt,
        completion_tokens=completion,
        provider_reported_total_tokens=total,
        derived_total_tokens=derived,
        total_tokens_source=source,
        **details,
    )


def calculate_cost(
    usage: ProviderUsageDiagnostic,
    pricing: BenchmarkPricingSpecification | None,
) -> ProviderCostDiagnostic:
    if pricing is None:
        return ProviderCostDiagnostic(cost_status=CostStatus.PRICING_UNAVAILABLE)
    if usage.prompt_tokens is None or usage.completion_tokens is None:
        return ProviderCostDiagnostic(
            cost_status=CostStatus.INSUFFICIENT_USAGE,
            pricing_version=pricing.pricing_version,
            pricing_effective_date=pricing.effective_date,
            pricing_source=pricing.pricing_source,
        )
    cost = pricing.estimate_cost(
        input_tokens=usage.prompt_tokens,
        cached_input_tokens=usage.cached_prompt_tokens or 0,
        output_tokens=usage.completion_tokens,
        reasoning_tokens=usage.reasoning_tokens or 0,
    )
    return ProviderCostDiagnostic(
        estimated_cost_usd=cost,
        cost_status=CostStatus.CALCULATED,
        pricing_version=pricing.pricing_version,
        pricing_effective_date=pricing.effective_date,
        pricing_source=pricing.pricing_source,
    )


def aggregate_provider_diagnostics(
    trials: tuple[ProviderTrialDiagnostic, ...],
) -> dict[str, object] | None:
    if not trials:
        return None
    references = [item.references for item in trials]
    precision = [
        item.reference_precision
        for item in references
        if item.reference_precision is not None
    ]
    recall = [
        item.reference_recall
        for item in references
        if item.reference_recall is not None
    ]
    latencies = [
        item.provider_latency_ms
        for item in trials
        if item.provider_latency_ms is not None
    ]
    costs = [
        item.cost.estimated_cost_usd
        for item in trials
        if item.cost.estimated_cost_usd is not None
    ]
    return {
        "operational_outcome_distribution": _enum_counts(
            item.operational_outcome for item in trials
        ),
        "failure_code_distribution": dict(
            sorted(
                Counter(
                    item.failure_code for item in trials if item.failure_code
                ).items()
            )
        ),
        "failure_stage_distribution": _enum_counts(
            item.failure_stage for item in trials
        ),
        "unknown_reference_frequency": _frequency(references, "unknown_references"),
        "unauthorized_reference_frequency": _frequency(
            references, "unauthorized_references"
        ),
        "missing_reference_frequency": _frequency(
            references, "missing_authorized_references"
        ),
        "duplicate_reference_frequency": _frequency(
            references, "duplicate_provider_references"
        ),
        "first_invalid_reference_frequency": dict(
            sorted(
                Counter(
                    item.first_invalid_reference
                    for item in references
                    if item.first_invalid_reference
                ).items()
            )
        ),
        "reference_confusion_matrix": _confusion(references),
        "reference_precision": _summary(precision),
        "reference_recall": _summary(recall),
        "provider_latency_ms": _summary(latencies),
        "token_usage": {
            "prompt": _summary(
                [
                    item.usage.prompt_tokens
                    for item in trials
                    if item.usage.prompt_tokens is not None
                ]
            ),
            "completion": _summary(
                [
                    item.usage.completion_tokens
                    for item in trials
                    if item.usage.completion_tokens is not None
                ]
            ),
        },
        "estimated_cost_usd": _summary(costs),
        "usage_availability_rate": sum(
            item.usage.effective_total_tokens is not None for item in trials
        )
        / len(trials),
        "cost_calculability_rate": len(costs) / len(trials),
    }


def _enum_counts(values) -> dict[str, int]:
    return dict(sorted(Counter(value.value for value in values).items()))


def _frequency(items, field) -> dict[str, int]:
    return dict(
        sorted(
            Counter(value for item in items for value in getattr(item, field)).items()
        )
    )


def _confusion(items) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        for expected in item.authorized_references:
            for produced in item.provider_produced_references_ordered or ("<MISSING>",):
                counts[f"{expected} -> {produced}"] += 1
    return dict(sorted(counts.items()))


def _summary(values) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "p95": ordered[index],
    }


def write_diagnostics_artifact_atomic(
    path: Path, artifact: ProviderDiagnosticsArtifact
) -> None:
    payload = (
        json.dumps(
            artifact.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
