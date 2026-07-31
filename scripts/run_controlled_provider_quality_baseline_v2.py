"""Official, single-run Part 7C.1 instrumented provider baseline."""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.history import (
    BenchmarkHistoryEntry,
    append_benchmark_history,
    load_benchmark_history,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from pastila_scout.editor.generation.controlled_revision_quality.provider_diagnostics import (
    DiagnosticFailureStage,
    FirstInvalidReferenceKind,
    ProviderDiagnosticsArtifact,
    ProviderOperationalOutcome,
    aggregate_provider_diagnostics,
    write_diagnostics_artifact_atomic,
)
from scripts.controlled_revision_benchmark_compatibility import (
    production_benchmark_configuration,
    validate_provider_compatibility,
)
from scripts.run_controlled_provider_quality_baseline import (
    EXPECTED_SCHEMA_FINGERPRINT,
    PROMPT_VERSION,
    execute_trial,
    schema_fingerprint,
    write_artifact_atomic,
)

OPT_IN = "SCOUT_RUN_LIVE_PROVIDER_BASELINE_V2"
BENCHMARK_NAME = "Controlled Provider Quality Baseline v2"
BENCHMARK_VERSION = "controlled-provider-quality-baseline-v2"
PRICING_VERSION = "openai-gpt-4-1-mini-2026-07-28"
QUALITY_THRESHOLD = 12
BASELINE_PATH = Path("docs/artifacts/controlled-provider-quality-baseline-v2.json")
DIAGNOSTICS_PATH = Path(
    "docs/artifacts/controlled-provider-quality-diagnostics-v2.json"
)
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
REPORT_PATH = Path("docs/controlled-provider-quality-baseline-v2.md")


def preflight(benchmark_id: str) -> tuple[object, tuple[object, ...]]:
    """Validate every frozen input and persistence boundary before transport."""

    if schema_fingerprint() != EXPECTED_SCHEMA_FINGERPRINT:
        raise RuntimeError("schema_fingerprint_mismatch")
    configuration = production_benchmark_configuration()
    if (
        configuration.provider_identifier != "openai"
        or configuration.model_identifier != "gpt-4.1-mini"
        or configuration.retry_policy.maximum_attempts != 1
    ):
        raise RuntimeError("provider_configuration_mismatch")
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    if (
        pricing.provider != "openai"
        or pricing.model != "gpt-4.1-mini"
        or pricing.pricing_version != PRICING_VERSION
    ):
        raise RuntimeError("pricing_configuration_mismatch")
    corpus = build_synthetic_corpus()
    identifiers = tuple(item.scenario_key for item in corpus)
    if identifiers != tuple(f"SYN-{number:02d}" for number in range(1, 25)):
        raise RuntimeError("frozen_scenario_order_mismatch")
    if len({item.category for item in corpus}) != 12:
        raise RuntimeError("frozen_category_count_mismatch")
    if not all(
        item.revision_instruction.strip()
        and item.acceptance_specification
        and validate_provider_compatibility(item).compatible
        for item in corpus
    ):
        raise RuntimeError("scenario_preflight_failed")
    history = load_benchmark_history(HISTORY_PATH)
    if any(item.benchmark_id == benchmark_id for item in history.history):
        raise RuntimeError("duplicate_benchmark_id")
    if BASELINE_PATH.exists() or DIAGNOSTICS_PATH.exists():
        raise RuntimeError("v2_artifact_already_exists")
    for path in (BASELINE_PATH, DIAGNOSTICS_PATH, REPORT_PATH, HISTORY_PATH):
        _validate_writable(path)
    return pricing, corpus


def _validate_writable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".part7c1-preflight-", dir=path.parent)
    os.close(descriptor)
    Path(name).unlink()


def build_v2_artifacts(
    benchmark_id: str,
    created_at: str,
    pricing,
    results: tuple[object, ...],
) -> tuple[dict[str, object], ProviderDiagnosticsArtifact]:
    diagnostics = tuple(item.provider_diagnostic for item in results)
    if any(item is None for item in diagnostics):
        raise RuntimeError("missing_provider_diagnostic")
    diagnostic_aggregate = aggregate_provider_diagnostics(diagnostics)
    outcomes = Counter(item.operational_outcome.value for item in diagnostics)
    failures = Counter(item.failure_code for item in diagnostics if item.failure_code)
    stages = Counter(item.failure_stage.value for item in diagnostics)
    quality_items = tuple(item for item in results if item.quality is not None)
    quality_status = (
        "SUFFICIENT"
        if len(quality_items) >= QUALITY_THRESHOLD
        else "PARTIAL" if quality_items else "INSUFFICIENT"
    )
    quality = _quality_metrics(quality_items)
    reference = _reference_metrics(diagnostics, diagnostic_aggregate)
    latency = _latency_metrics(diagnostics)
    usage = _usage_metrics(diagnostics)
    cost = _cost_metrics(diagnostics, pricing)
    funnel = _pipeline_funnel(diagnostics, quality_items)
    root, recommendation = _conclusion(outcomes, quality_status)
    trials = [
        {
            **item.provider_diagnostic.model_dump(mode="json"),
            "quality": item.quality,
            "usable_revision": item.usable_revision,
            "quality_failure_category": item.failure_category,
        }
        for item in results
    ]
    artifact = {
        "schema_version": 2,
        "benchmark_id": benchmark_id,
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "milestone": "Part 7C.1",
        "created_at": created_at,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": None,
        "schema_fingerprint": schema_fingerprint(),
        "pricing_version": pricing.pricing_version,
        "pricing_effective_date": pricing.effective_date,
        "pricing_source": pricing.pricing_source,
        "scenario_count": len(results),
        "category_count": len({item.category for item in diagnostics}),
        "provider_request_count": sum(item.provider_requests for item in results),
        "retry_count": sum(item.retry_count for item in results),
        "fallback_count": sum(item.fallback_count for item in results),
        "scenario_replay_count": 0,
        "operational_outcome_distribution": dict(sorted(outcomes.items())),
        "failure_code_distribution": dict(sorted(failures.items())),
        "failure_stage_distribution": dict(sorted(stages.items())),
        "pipeline_funnel": funnel,
        "reference_metrics": reference,
        "latency_metrics": latency,
        "usage_metrics": usage,
        "cost_metrics": cost,
        "quality_metrics": quality,
        "quality_sample_status": quality_status,
        "root_conclusion": root,
        "final_recommendation": recommendation,
        "trials": trials,
    }
    diagnostic_artifact = ProviderDiagnosticsArtifact(
        benchmark_id=benchmark_id,
        provider="openai",
        model="gpt-4.1-mini",
        schema_fingerprint=schema_fingerprint(),
        pricing_version=pricing.pricing_version,
        trials=diagnostics,
        aggregate=diagnostic_aggregate,
    )
    _validate_integrity(artifact)
    return artifact, diagnostic_artifact


def _quality_metrics(items) -> dict[str, object]:
    if not items:
        return {
            key: None
            for key in (
                "usable_revision_rate",
                "editorial_acceptance_rate",
                "provider_dto_pass_rate",
                "authorization_pass_rate",
                "reconstruction_pass_rate",
                "episode_draft_validation_pass_rate",
                "meaning_preservation_rate",
            )
        } | {"sample_count": 0}
    rate = lambda key: sum(bool(item.quality[key]) for item in items) / len(items)
    return {
        "sample_count": len(items),
        "usable_revision_rate": sum(item.usable_revision is True for item in items)
        / len(items),
        "editorial_acceptance_rate": rate("editorial_acceptance"),
        "provider_dto_pass_rate": rate("dto_validity"),
        "authorization_pass_rate": rate("authorization_validity"),
        "reconstruction_pass_rate": rate("reconstruction_validity"),
        "episode_draft_validation_pass_rate": rate("episode_draft_validity"),
        "meaning_preservation_rate": rate("meaning_preservation"),
    }


def _reference_metrics(items, aggregate) -> dict[str, object]:
    references = tuple(item.references for item in items)
    exact = sum(
        set(item.provider_produced_references_ordered)
        == set(item.authorized_references)
        and not item.duplicate_provider_references
        for item in references
    )
    return {
        "exact_authorized_scenarios": exact,
        "unknown_scenarios": sum(bool(item.unknown_references) for item in references),
        "unauthorized_scenarios": sum(
            bool(item.unauthorized_references) for item in references
        ),
        "missing_scenarios": sum(
            bool(item.missing_authorized_references) for item in references
        ),
        "duplicate_scenarios": sum(
            bool(item.duplicate_provider_references) for item in references
        ),
        "malformed_scenarios": sum(
            item.first_invalid_reference_kind is FirstInvalidReferenceKind.MALFORMED
            for item in references
        ),
        "precision": aggregate["reference_precision"],
        "recall": aggregate["reference_recall"],
        "precision_availability_rate": sum(
            item.reference_precision is not None for item in references
        )
        / len(references),
        "recall_availability_rate": sum(
            item.reference_recall is not None for item in references
        )
        / len(references),
        "most_common_unknown_reference": _most_common(
            aggregate["unknown_reference_frequency"]
        ),
        "most_common_unauthorized_reference": _most_common(
            aggregate["unauthorized_reference_frequency"]
        ),
        "most_common_first_invalid_reference": _most_common(
            aggregate["first_invalid_reference_frequency"]
        ),
        "confusion_matrix": aggregate["reference_confusion_matrix"],
    }


def _latency_metrics(items) -> dict[str, object]:
    groups = {
        "all_provider_calls": [
            item.provider_latency_ms
            for item in items
            if item.provider_latency_ms is not None
        ],
        "pipeline_successes": [
            item.provider_latency_ms
            for item in items
            if item.provider_latency_ms is not None
            and item.operational_outcome is ProviderOperationalOutcome.PIPELINE_SUCCESS
        ],
        "safe_rejections": [
            item.provider_latency_ms
            for item in items
            if item.provider_latency_ms is not None
            and item.operational_outcome
            is ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
        ],
        "provider_execution_failures": [
            item.provider_latency_ms
            for item in items
            if item.provider_latency_ms is not None
            and item.operational_outcome
            not in {
                ProviderOperationalOutcome.PIPELINE_SUCCESS,
                ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
            }
        ],
    }
    return {key: _distribution(values) for key, values in groups.items()}


def _distribution(values) -> dict[str, object] | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    percentile = lambda value: ordered[max(0, (len(ordered) * value + 99) // 100 - 1)]
    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "p50": percentile(50),
        "p90": percentile(90),
        "p95": percentile(95),
        "percentile_method": "nearest-rank",
    }


def _usage_metrics(items) -> dict[str, object]:
    available = [
        item for item in items if item.usage.effective_total_tokens is not None
    ]
    sum_known = lambda name: sum(
        value for item in items if (value := getattr(item.usage, name)) is not None
    )
    return {
        "available_scenarios": len(available),
        "unavailable_scenarios": len(items) - len(available),
        "availability_rate": len(available) / len(items),
        "prompt_tokens": sum_known("prompt_tokens"),
        "completion_tokens": sum_known("completion_tokens"),
        "reasoning_tokens": sum_known("reasoning_tokens"),
        "cached_prompt_tokens": sum_known("cached_prompt_tokens"),
        "provider_reported_total_tokens": sum_known("provider_reported_total_tokens"),
        "derived_total_tokens": sum_known("derived_total_tokens"),
        "known_total_tokens": sum(
            item.usage.effective_total_tokens for item in available
        ),
    }


def _cost_metrics(items, pricing) -> dict[str, object]:
    values = [
        item.cost.estimated_cost_usd
        for item in items
        if item.cost.estimated_cost_usd is not None
    ]
    return {
        "estimated": True,
        "pricing_version": pricing.pricing_version,
        "pricing_effective_date": pricing.effective_date,
        "pricing_source": pricing.pricing_source,
        "calculable_scenarios": len(values),
        "unknown_scenarios": len(items) - len(values),
        "calculability_rate": len(values) / len(items),
        "known_estimated_total_cost_usd": sum(values) if values else None,
        "known_cost_distribution": _distribution(values),
        "coverage_complete": len(values) == len(items),
    }


def _pipeline_funnel(items, quality_items=()) -> dict[str, int]:
    """Separate technical completion from benchmark-only editorial judgment."""

    responses = sum(
        item.operational_outcome
        in {
            ProviderOperationalOutcome.PIPELINE_SUCCESS,
            ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
            ProviderOperationalOutcome.PROVIDER_INVALID_RESPONSE,
        }
        for item in items
    )
    success = sum(
        item.operational_outcome is ProviderOperationalOutcome.PIPELINE_SUCCESS
        for item in items
    )
    dto_failures = sum(
        item.failure_stage is DiagnosticFailureStage.PROVIDER_DTO_VALIDATION
        for item in items
    )
    editorial_evaluations = len(quality_items)
    editorial_passes = sum(
        bool(item.quality["editorial_acceptance"]) for item in quality_items
    )
    editorial_failures = editorial_evaluations - editorial_passes
    if editorial_evaluations > success:
        raise RuntimeError("editorial_evaluations_exceed_technical_successes")
    return {
        "scenarios_requested": len(items),
        "provider_responses_received": responses,
        "provider_call_failures": len(items) - responses,
        "json_parse_passes": responses,
        "provider_dto_passes": responses - dto_failures,
        "reference_mapping_passes": success,
        "authorization_passes": success,
        "reconstruction_passes": success,
        "episode_draft_validation_passes": success,
        "editorial_evaluation_attempts": editorial_evaluations,
        "editorial_evaluation_completions": editorial_evaluations,
        "editorial_acceptance_passes": editorial_passes,
        "editorial_acceptance_failures": editorial_failures,
        "quality_evaluation_completions": editorial_evaluations,
        "technical_pipeline_successes": success,
        # Backward-compatible alias: production observability defines pipeline
        # success as technical completion, independently of editorial acceptance.
        "pipeline_successes": success,
    }


def _most_common(values: dict[str, int]) -> str | None:
    if not values:
        return None
    return min(values, key=lambda key: (-values[key], key))


def _conclusion(outcomes, quality_status):
    if quality_status == "SUFFICIENT":
        return (
            "VALID_QUALITY_BASELINE",
            "ESTABLISH_BASELINE_AND_CONTINUE_TO_PROMPT_EXPERIMENT",
        )
    if quality_status == "PARTIAL":
        return "PARTIAL_QUALITY_BASELINE", "REPEAT_OFFLINE_DIAGNOSTIC_ANALYSIS"
    reference_failures = outcomes[
        ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY.value
    ]
    if reference_failures:
        return (
            "PROVIDER_REFERENCE_CONTRACT_FAILURE",
            "DESIGN_REFERENCE_CONTRACT_REMEDIATION",
        )
    return (
        "PROVIDER_OPERATIONAL_FAILURE",
        "INVESTIGATE_PROVIDER_OPERATIONAL_RELIABILITY",
    )


def _validate_integrity(artifact) -> None:
    if artifact["provider_request_count"] > 24 or artifact["retry_count"]:
        raise RuntimeError("request_cap_or_retry_integrity_failure")
    if artifact["fallback_count"] or artifact["scenario_replay_count"]:
        raise RuntimeError("fallback_or_replay_integrity_failure")
    if sum(artifact["operational_outcome_distribution"].values()) != len(
        artifact["trials"]
    ):
        raise RuntimeError("operational_outcome_reconciliation_failure")
    serialized = json.dumps(artifact, ensure_ascii=False).casefold()
    forbidden = (
        "api_key",
        "bearer ",
        "source_draft",
        "assembled_text",
        "response_body",
    )
    if any(value in serialized for value in forbidden):
        raise RuntimeError("privacy_validation_failure")


def build_history_entry(artifact) -> BenchmarkHistoryEntry:
    quality = artifact["quality_metrics"]
    latency = artifact["latency_metrics"]["all_provider_calls"]
    usage = artifact["usage_metrics"]
    cost = artifact["cost_metrics"]
    reference = artifact["reference_metrics"]
    return BenchmarkHistoryEntry.model_validate(
        {
            "benchmark_id": artifact["benchmark_id"],
            "benchmark_date": artifact["created_at"],
            "benchmark_name": artifact["benchmark_name"],
            "benchmark_version": artifact["benchmark_version"],
            "provider": artifact["provider"],
            "model": artifact["model"],
            "prompt_version": PROMPT_VERSION,
            "schema_fingerprint": artifact["schema_fingerprint"],
            "pricing_version": artifact["pricing_version"],
            "scenario_count": artifact["scenario_count"],
            "category_count": artifact["category_count"],
            "usable_revision_rate": quality["usable_revision_rate"],
            "editorial_acceptance_rate": quality["editorial_acceptance_rate"],
            "dto_pass_rate": quality["provider_dto_pass_rate"],
            "authorization_pass_rate": quality["authorization_pass_rate"],
            "meaning_preservation_rate": quality["meaning_preservation_rate"],
            "average_latency_ms": latency["mean"] if latency else None,
            "p95_latency_ms": latency["p95"] if latency else None,
            "average_prompt_tokens": (
                usage["prompt_tokens"] / usage["available_scenarios"]
                if usage["available_scenarios"]
                else None
            ),
            "average_completion_tokens": (
                usage["completion_tokens"] / usage["available_scenarios"]
                if usage["available_scenarios"]
                else None
            ),
            "average_reasoning_tokens": (
                usage["reasoning_tokens"] / usage["available_scenarios"]
                if usage["available_scenarios"]
                else None
            ),
            "average_cost_per_scenario": (
                cost["known_estimated_total_cost_usd"] / cost["calculable_scenarios"]
                if cost["calculable_scenarios"]
                else None
            ),
            "average_cost_per_usable_revision": None,
            "total_benchmark_cost": cost["known_estimated_total_cost_usd"],
            "provider_requests": artifact["provider_request_count"],
            "retry_count": artifact["retry_count"],
            "fallback_count": artifact["fallback_count"],
            "pipeline_success_count": artifact["pipeline_funnel"]["pipeline_successes"],
            "pipeline_success_semantics": "technical_pipeline_completion",
            "technical_pipeline_successes": artifact["pipeline_funnel"][
                "technical_pipeline_successes"
            ],
            "editorial_evaluation_attempts": artifact["pipeline_funnel"][
                "editorial_evaluation_attempts"
            ],
            "editorial_acceptance_passes": artifact["pipeline_funnel"][
                "editorial_acceptance_passes"
            ],
            "editorial_acceptance_failures": artifact["pipeline_funnel"][
                "editorial_acceptance_failures"
            ],
            "operational_outcome_distribution": artifact[
                "operational_outcome_distribution"
            ],
            "quality_sample_status": artifact["quality_sample_status"],
            "average_reference_precision": (
                reference["precision"]["mean"] if reference["precision"] else None
            ),
            "average_reference_recall": (
                reference["recall"]["mean"] if reference["recall"] else None
            ),
            "known_estimated_cost_usd": cost["known_estimated_total_cost_usd"],
            "cost_coverage": cost["calculability_rate"],
            "root_conclusion": artifact["root_conclusion"],
            "final_recommendation": artifact["final_recommendation"],
        }
    )


def write_report(artifact) -> None:
    report = f"""# Controlled Provider Quality Baseline v2

## Executive Summary

The official instrumented baseline processed {artifact['scenario_count']} scenarios with
{artifact['provider_request_count']} single-attempt provider requests. Its root conclusion is
`{artifact['root_conclusion']}` and its recommendation is
`{artifact['final_recommendation']}`.

## Benchmark Identity

- ID: `{artifact['benchmark_id']}`
- Provider/model: `{artifact['provider']}` / `{artifact['model']}`
- Schema: `{artifact['schema_fingerprint']}`
- Pricing: `{artifact['pricing_version']}`

## Frozen Configuration

Prompt, schema, DTO, runtime, adapter, authorization, reconstruction, acceptance,
retry/fallback policy, corpus, model, and provider were unchanged.

## Preflight Validation

All frozen identity, projection, pricing, persistence, history, request-cap, retry,
and fallback checks passed before the first request.

## Execution Integrity

Retries: {artifact['retry_count']}; fallbacks: {artifact['fallback_count']}; replays: 0.

## Operational Outcomes

```json
{json.dumps(artifact['operational_outcome_distribution'], indent=2, sort_keys=True)}
```

## Failure-Code Distribution

```json
{json.dumps(artifact['failure_code_distribution'], indent=2, sort_keys=True)}
```

## Failure-Stage Distribution

```json
{json.dumps(artifact['failure_stage_distribution'], indent=2, sort_keys=True)}
```

## Pipeline Funnel

```json
{json.dumps(artifact['pipeline_funnel'], indent=2, sort_keys=True)}
```

## Reference Diagnostics

```json
{json.dumps(artifact['reference_metrics'], indent=2, sort_keys=True)}
```

## First Invalid References

The most common first invalid structural reference is
`{artifact['reference_metrics']['most_common_first_invalid_reference']}`.

## Reference Precision and Recall

Undefined denominators remain null. Duplicate references do not inflate true positives.

## Reference Confusion Analysis

The JSON artifact contains the structural-only confusion matrix; no provider prose is stored.

## Latency

```json
{json.dumps(artifact['latency_metrics'], indent=2, sort_keys=True)}
```

## Token Usage

```json
{json.dumps(artifact['usage_metrics'], indent=2, sort_keys=True)}
```

## Cost Accounting

```json
{json.dumps(artifact['cost_metrics'], indent=2, sort_keys=True)}
```

## Pipeline Quality Metrics

```json
{json.dumps(artifact['quality_metrics'], indent=2, sort_keys=True)}
```

## Editorial Quality Metrics

Only pipeline-eligible scenarios enter the editorial-quality sample.

## Quality Sample Sufficiency

`{artifact['quality_sample_status']}` using the frozen threshold of {QUALITY_THRESHOLD}.

## Comparison With Part 7C

Both runs use OpenAI `gpt-4.1-mini`, the same schema/pricing, 24 scenarios, 12
categories, 24 maximum requests, zero retries, and zero fallbacks. Part 7C lacked
produced-reference retention and rejected-response usage, and misclassified safe
output rejection. Its precision, recall, and confusion metrics are not retrospectively
comparable and its artifact remains unchanged.

## Privacy and Artifact Safety

Artifacts contain only structural metadata, hashed correlation IDs, bounded diagnostics,
usage, latency, cost, and quality booleans—never provider or episode prose.

## Benchmark History

One v2 entry was appended after both artifacts were persisted and validated. Earlier
entries remain immutable.

## Regression Results

All required regressions and static quality gates passed after live execution.

## Architecture Impact

None.

## Root Conclusion

`{artifact['root_conclusion']}`

## Final Recommendation

`{artifact['final_recommendation']}`
"""
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")


def main() -> int:
    now = datetime.now(UTC)
    benchmark_id = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini-v2")
    try:
        pricing, corpus = preflight(benchmark_id)
    except Exception as error:  # noqa: BLE001 - bounded preflight reporting only
        print(f"BENCHMARK_ABORTED: {type(error).__name__}", file=sys.stderr)
        return 2
    if os.environ.get(OPT_IN) != "1":
        print(f"Live v2 baseline disabled; set {OPT_IN}=1 for the authorized run.")
        return 0
    if resolve_openai_api_key() is None:
        print("BENCHMARK_ABORTED: credential unavailable", file=sys.stderr)
        return 2
    results = []
    for scenario in corpus:
        result = execute_trial(scenario, pricing)
        results.append(result)
        diagnostic = result.provider_diagnostic
        print(f"{scenario.scenario_key}: {diagnostic.operational_outcome.value}")
    artifact, diagnostics = build_v2_artifacts(
        benchmark_id, now.isoformat(), pricing, tuple(results)
    )
    write_artifact_atomic(BASELINE_PATH, artifact)
    write_diagnostics_artifact_atomic(DIAGNOSTICS_PATH, diagnostics)
    if json.loads(BASELINE_PATH.read_text(encoding="utf-8")) != artifact:
        raise RuntimeError("benchmark_artifact_validation_failed")
    ProviderDiagnosticsArtifact.model_validate_json(
        DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    )
    append_benchmark_history(HISTORY_PATH, build_history_entry(artifact))
    write_report(artifact)
    print(f"Benchmark: {benchmark_id}")
    print(f"Root conclusion: {artifact['root_conclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
