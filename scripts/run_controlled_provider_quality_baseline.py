"""Execute the frozen Part 7C provider benchmark exactly once per scenario.

The artifact intentionally contains only content-free measurements and diagnostics.
Live execution is opt-in so importing or testing this module cannot contact a provider.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from time import monotonic

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderExecutionFailureKind,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionAdapter,
    compose_openai_controlled_revision_adapter,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.evaluation import (
    evaluate_scenario,
)
from pastila_scout.editor.generation.controlled_revision_quality.history import (
    BenchmarkHistoryEntry,
    append_benchmark_history,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    BenchmarkPricingSpecification,
    load_benchmark_pricing,
)
from pastila_scout.editor.generation.controlled_revision_quality.provider_diagnostics import (
    DiagnosticFailureStage,
    ProviderOperationalOutcome,
    ProviderTrialDiagnostic,
    build_reference_diagnostic,
    build_usage_diagnostic,
    calculate_cost,
)
from pastila_scout.editor.generation.controlled_revision_quality.scenario import (
    CandidateRevision,
    SyntheticRevisionScenario,
)
from pastila_scout.editor.generation.revision import validate_revision_gateway_result
from scripts.controlled_provider_diagnostics_capture import (
    CapturingOpenAIInterpreter,
    CapturingProviderClient,
    EarlyProviderCapture,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_editorial_acceptance_specification,
    build_production_invocation,
    production_benchmark_configuration,
)
from scripts.openai_controlled_revision_acceptance import (
    evaluate_editorial_acceptance,
)
from scripts.validate_openai_controlled_revision_e2e import (
    CapturingRuntime,
    CountingOpenAIFactory,
    EnvironmentCredentialProvider,
    EventRecorder,
)

EXPECTED_SCHEMA_FINGERPRINT = (
    "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
)
PROMPT_VERSION = (
    "sha256:cb6f07d47ec80ee8dfa246e5151f4c5a625adac2372f05a7cbccf4cbc3ebbf1c"
)
BENCHMARK_VERSION = "controlled-provider-quality-baseline-v1"
OPT_IN = "SCOUT_RUN_LIVE_PROVIDER_BASELINE"
MINIMUM_QUALITY_SAMPLE = 12


class OperationalOutcome(StrEnum):
    PIPELINE_SUCCESS = "PIPELINE_SUCCESS"
    PROVIDER_OUTPUT_REJECTED_SAFELY = "PROVIDER_OUTPUT_REJECTED_SAFELY"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    BENCHMARK_ABORTED = "BENCHMARK_ABORTED"


@dataclass(frozen=True, slots=True)
class TrialResult:
    scenario_id: str
    category: str
    outcome: OperationalOutcome
    diagnostic_code: str | None
    provider_requests: int
    retry_count: int
    fallback_count: int
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int | None
    cached_prompt_tokens: int | None
    billable_tokens: int
    estimated_cost: float
    quality: dict[str, bool] | None
    usable_revision: bool | None
    failure_category: str | None
    provider_diagnostic: ProviderTrialDiagnostic | None = None

    def __post_init__(self) -> None:
        numeric = (
            self.provider_requests,
            self.retry_count,
            self.fallback_count,
            self.latency_ms,
            self.prompt_tokens,
            self.completion_tokens,
            self.billable_tokens,
            self.estimated_cost,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("benchmark measurements must be non-negative")

    def safe_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "operational_outcome": self.outcome.value,
            "diagnostic_code": self.diagnostic_code,
            "provider_requests": self.provider_requests,
            "retry_count": self.retry_count,
            "fallback_count": self.fallback_count,
            "latency_ms": round(self.latency_ms, 3),
            "tokens": {
                "prompt": self.prompt_tokens,
                "completion": self.completion_tokens,
                "reasoning": self.reasoning_tokens,
                "cached_prompt": self.cached_prompt_tokens,
                "billable": self.billable_tokens,
            },
            "cost": {
                "amount": self.estimated_cost,
                "currency": "USD",
                "estimated": True,
            },
            "quality": self.quality,
            "usable_revision": self.usable_revision,
            "failure_category": self.failure_category,
            "provider_diagnostic": (
                self.provider_diagnostic.model_dump(mode="json")
                if self.provider_diagnostic
                else None
            ),
        }


def schema_fingerprint() -> str:
    return hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()


def execute_trial(
    scenario: SyntheticRevisionScenario,
    pricing: BenchmarkPricingSpecification,
    *,
    pre_request_validator=None,
    request_transformer=None,
) -> TrialResult:
    """Execute one scenario through the complete production adapter pipeline."""

    invocation = build_production_invocation(scenario)
    credentials = EnvironmentCredentialProvider()
    factory = CountingOpenAIFactory()
    observer = EventRecorder()
    composition = compose_openai_controlled_revision_adapter(
        configuration=production_benchmark_configuration(),
        credential_provider=credentials,
        client_factory=factory,
        execution_observer=observer,
    )
    early = EarlyProviderCapture()
    runtime = composition.runtime_composition.runtime
    runtime.client = CapturingProviderClient(
        runtime.client,
        early,
        pre_request_validator=(
            (lambda request: pre_request_validator(invocation, request))
            if pre_request_validator is not None
            else None
        ),
        request_transformer=(
            (lambda request: request_transformer(invocation, request))
            if request_transformer is not None
            else None
        ),
    )
    runtime.interpreter = CapturingOpenAIInterpreter(runtime.interpreter, early)
    capture = CapturingRuntime(runtime)
    gateway = OpenAIControlledRevisionAdapter(composition.configuration, capture)
    started = monotonic()
    try:
        gateway_result = gateway.revise(invocation)
        elapsed = (monotonic() - started) * 1000
        validate_revision_gateway_result(gateway_result, invocation)
        result = capture.result
        acceptance = evaluate_editorial_acceptance(
            scenario.source_draft,
            gateway_result.revised_draft,
            build_editorial_acceptance_specification(scenario),
        )
        candidate = CandidateRevision(
            draft=gateway_result.revised_draft,
            editorial_accepted=acceptance.passed,
            instruction_followed=acceptance.passed,
            improved=(
                gateway_result.revised_draft.assembled_text
                != scenario.source_draft.assembled_text
            )
            or scenario.expects_no_change,
            source_authority_preserved=acceptance.passed,
        )
        live_scenario = scenario.model_copy(update={"candidate": candidate})
        evaluation = evaluate_scenario(live_scenario)
        usage = result.usage
        cost = pricing.estimate_cost(
            input_tokens=usage.prompt_tokens,
            cached_input_tokens=0,
            output_tokens=usage.completion_tokens,
        )
        diagnostic = _provider_diagnostic(
            scenario, pricing, early, ProviderOperationalOutcome.PIPELINE_SUCCESS
        )
        return TrialResult(
            scenario.scenario_key,
            scenario.category.value,
            OperationalOutcome.PIPELINE_SUCCESS,
            None,
            len(result.attempts),
            max(0, len(result.attempts) - 1),
            0,
            usage.cumulative_latency_ms or elapsed,
            usage.prompt_tokens,
            usage.completion_tokens,
            None,
            None,
            usage.total_tokens,
            cost,
            evaluation.dimensions.model_dump(mode="json"),
            evaluation.usable_revision,
            evaluation.failure_category.value,
            diagnostic,
        )
    except Exception:  # noqa: BLE001 - continue with a content-free failure record
        elapsed = (monotonic() - started) * 1000
        result = capture.result
        diagnostic = result.diagnostic if result is not None else None
        kind = diagnostic.failure_kind if diagnostic else None
        attempts = len(result.attempts) if result is not None else 0
        usage = result.usage if result is not None else None
        prompt = usage.prompt_tokens if usage else 0
        completion = usage.completion_tokens if usage else 0
        cost = pricing.estimate_cost(
            input_tokens=prompt, cached_input_tokens=0, output_tokens=completion
        )
        outcome = _provider_failure_outcome(
            diagnostic.diagnostic_code if diagnostic else None,
            early.provider_response_received,
        )
        provider_diagnostic = _provider_diagnostic(
            scenario,
            pricing,
            early,
            outcome,
            failure_code=(
                diagnostic.diagnostic_code
                if diagnostic
                else "benchmark_internal_failure"
            ),
        )
        return TrialResult(
            scenario.scenario_key,
            scenario.category.value,
            _failure_outcome(kind),
            (
                diagnostic.diagnostic_code
                if diagnostic
                else "unclassified_provider_failure"
            ),
            attempts,
            max(0, attempts - 1),
            0,
            usage.cumulative_latency_ms if usage else elapsed,
            prompt,
            completion,
            None,
            None,
            prompt + completion,
            cost,
            None,
            None,
            None,
            provider_diagnostic,
        )


def _provider_diagnostic(
    scenario,
    pricing,
    capture,
    outcome,
    *,
    failure_code=None,
):
    references = capture.references or build_reference_diagnostic(
        authorized=tuple(scenario.authorized_components),
        produced=(),
        recognized_registry=_source_registry(scenario),
    )
    usage = capture.usage or build_usage_diagnostic(
        prompt=None, completion=None, total=None
    )
    return ProviderTrialDiagnostic(
        scenario_id=scenario.scenario_key,
        category=scenario.category.value,
        provider="openai",
        model="gpt-4.1-mini",
        operational_outcome=outcome,
        failure_code=failure_code,
        failure_stage=_failure_stage(failure_code, outcome),
        references=references,
        provider_latency_ms=capture.provider_latency_ms,
        usage=usage,
        cost=calculate_cost(usage, pricing),
        provider_request_id_hash=capture.provider_request_id_hash,
    )


def _source_registry(scenario):
    source = scenario.source_draft
    values = {"opening", "closing"}
    values.update(f"story:{item.story_id}" for item in source.stories)
    values.update(
        f"transition:{item.from_story_id}:{item.to_story_id}"
        for item in source.transitions
    )
    if source.cta is not None:
        values.add("call_to_action")
    return frozenset(values)


def _provider_failure_outcome(code, response_received):
    if response_received:
        return ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
    mapping = {
        "provider_timeout": ProviderOperationalOutcome.PROVIDER_TIMEOUT,
        "provider_rate_limited": ProviderOperationalOutcome.PROVIDER_RATE_LIMIT,
        "provider_unavailable": ProviderOperationalOutcome.PROVIDER_SERVICE_FAILURE,
        "provider_transport_failed": ProviderOperationalOutcome.PROVIDER_TRANSPORT_FAILURE,
        "openai_sdk_response_invalid": ProviderOperationalOutcome.PROVIDER_INVALID_RESPONSE,
    }
    return mapping.get(code, ProviderOperationalOutcome.BENCHMARK_INTERNAL_FAILURE)


def _failure_stage(code, outcome):
    if outcome is ProviderOperationalOutcome.PIPELINE_SUCCESS:
        return DiagnosticFailureStage.NONE
    if outcome is not ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY:
        return DiagnosticFailureStage.PROVIDER_CALL
    if code == "openai_provider_output_schema_invalid":
        return DiagnosticFailureStage.PROVIDER_DTO_VALIDATION
    if code in {
        "openai_provider_output_reference_unknown",
        "openai_provider_output_reference_unauthorized",
        "openai_provider_output_required_component_missing",
    }:
        return DiagnosticFailureStage.REFERENCE_MAPPING
    return DiagnosticFailureStage.RECONSTRUCTION


def _failure_outcome(kind: AIProviderExecutionFailureKind | None) -> OperationalOutcome:
    if kind in {
        AIProviderExecutionFailureKind.SCHEMA,
        AIProviderExecutionFailureKind.INTERPRETATION,
        AIProviderExecutionFailureKind.INVALID_GATEWAY_PROJECTION,
        AIProviderExecutionFailureKind.MISSING_STRUCTURED_OUTPUT,
        AIProviderExecutionFailureKind.UNSUPPORTED_OUTPUT,
    }:
        return OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
    if kind is AIProviderExecutionFailureKind.MALFORMED_RESPONSE:
        return OperationalOutcome.PROVIDER_INVALID_RESPONSE
    code = kind.value if kind else ""
    if "timeout" in code:
        return OperationalOutcome.PROVIDER_TIMEOUT
    if "rate" in code:
        return OperationalOutcome.PROVIDER_RATE_LIMIT
    return OperationalOutcome.PROVIDER_FAILURE


def aggregate_results(trials: tuple[TrialResult, ...]) -> dict[str, object]:
    quality_trials = tuple(item for item in trials if item.quality is not None)
    metric_names = tuple(next(iter(quality_trials)).quality) if quality_trials else ()
    quality_rates = {
        name: sum(bool(item.quality[name]) for item in quality_trials)
        / len(quality_trials)
        for name in metric_names
    }
    latencies = [item.latency_ms for item in trials]
    costs = [item.estimated_cost for item in trials]
    usable = sum(item.usable_revision is True for item in quality_trials)
    accepted = sum(
        bool(item.quality["editorial_acceptance"]) for item in quality_trials
    )
    structural = sum(
        bool(item.quality["structural_validity"]) for item in quality_trials
    )
    return {
        "scenario_count": len(trials),
        "category_count": len({item.category for item in trials}),
        "quality_sample_count": len(quality_trials),
        "operational_outcomes": dict(
            sorted(Counter(item.outcome.value for item in trials).items())
        ),
        "quality_rates": quality_rates,
        "usable_revision_rate": usable / len(quality_trials) if quality_trials else 0.0,
        "latency_ms": _distribution(latencies),
        "tokens": {
            "prompt": _distribution([item.prompt_tokens for item in trials]),
            "completion": _distribution([item.completion_tokens for item in trials]),
            "reasoning": None,
            "cached_prompt": None,
            "billable_total": sum(item.billable_tokens for item in trials),
        },
        "cost": {
            "estimated": True,
            "scenario": _distribution(costs),
            "total": sum(costs),
            "average_per_usable_revision": _safe_average(sum(costs), usable),
            "average_per_editorial_acceptance": _safe_average(sum(costs), accepted),
            "average_per_structural_success": _safe_average(sum(costs), structural),
        },
        "provider_requests": sum(item.provider_requests for item in trials),
        "retry_count": sum(item.retry_count for item in trials),
        "fallback_count": sum(item.fallback_count for item in trials),
    }


def _distribution(values: list[float | int]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {key: 0.0 for key in ("mean", "median", "minimum", "maximum", "p95")}
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "p95": ordered[index],
    }


def _safe_average(total: float, count: int) -> float | None:
    return total / count if count else None


def build_artifact(
    benchmark_id: str,
    generated_at: str,
    pricing: BenchmarkPricingSpecification,
    trials: tuple[TrialResult, ...],
) -> dict[str, object]:
    aggregate = aggregate_results(trials)
    sample = int(aggregate["quality_sample_count"])
    conclusion = (
        "CONTROLLED_PROVIDER_BASELINE_COMPLETE"
        if len(trials) == 24 and sample >= MINIMUM_QUALITY_SAMPLE
        else "INSUFFICIENT_SAMPLE"
    )
    return {
        "artifact_version": 1,
        "benchmark_id": benchmark_id,
        "benchmark_date": generated_at,
        "benchmark_version": BENCHMARK_VERSION,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_version": PROMPT_VERSION,
        "schema_fingerprint": schema_fingerprint(),
        "pricing_version": pricing.pricing_version,
        "pricing_basis": "estimated",
        "trials": [item.safe_dict() for item in trials],
        "aggregate": aggregate,
        "root_conclusion": conclusion,
        "final_recommendation": (
            "READY_FOR_PROMPT_EFFECTIVENESS_EXPERIMENT"
            if conclusion == "CONTROLLED_PROVIDER_BASELINE_COMPLETE"
            else "INVESTIGATE_PROVIDER_FAILURES"
        ),
    }


def write_artifact_atomic(path: Path, artifact: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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


def history_entry(artifact: dict[str, object]) -> BenchmarkHistoryEntry:
    aggregate = artifact["aggregate"]
    quality = aggregate["quality_rates"]
    return BenchmarkHistoryEntry(
        benchmark_id=artifact["benchmark_id"],
        benchmark_date=artifact["benchmark_date"],
        benchmark_version=artifact["benchmark_version"],
        provider=artifact["provider"],
        model=artifact["model"],
        prompt_version=artifact["prompt_version"],
        schema_fingerprint=artifact["schema_fingerprint"],
        pricing_version=artifact["pricing_version"],
        scenario_count=aggregate["scenario_count"],
        category_count=aggregate["category_count"],
        usable_revision_rate=aggregate["usable_revision_rate"],
        editorial_acceptance_rate=quality.get("editorial_acceptance", 0.0),
        dto_pass_rate=quality.get("dto_validity", 0.0),
        meaning_preservation_rate=quality.get("meaning_preservation", 0.0),
        average_latency_ms=aggregate["latency_ms"]["mean"],
        p95_latency_ms=aggregate["latency_ms"]["p95"],
        average_prompt_tokens=aggregate["tokens"]["prompt"]["mean"],
        average_completion_tokens=aggregate["tokens"]["completion"]["mean"],
        average_reasoning_tokens=None,
        average_cost_per_scenario=aggregate["cost"]["scenario"]["mean"],
        average_cost_per_usable_revision=aggregate["cost"][
            "average_per_usable_revision"
        ],
        total_benchmark_cost=aggregate["cost"]["total"],
        provider_requests=aggregate["provider_requests"],
        retry_count=aggregate["retry_count"],
        fallback_count=aggregate["fallback_count"],
        root_conclusion=artifact["root_conclusion"],
    )


def main() -> int:
    if schema_fingerprint() != EXPECTED_SCHEMA_FINGERPRINT:
        print(
            "BENCHMARK_ABORTED: production schema fingerprint changed", file=sys.stderr
        )
        return 2
    corpus = build_synthetic_corpus()
    if len(corpus) != 24 or len({item.category for item in corpus}) != 12:
        print("BENCHMARK_ABORTED: frozen corpus shape changed", file=sys.stderr)
        return 2
    if os.environ.get(OPT_IN) != "1":
        print(
            f"Live benchmark disabled; set {OPT_IN}=1 to authorize exactly 24 requests."
        )
        return 0
    if resolve_openai_api_key() is None:
        print("PROVIDER_UNAVAILABLE: OpenAI credential not found", file=sys.stderr)
        return 2
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    now = datetime.now(UTC)
    identifier = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini")
    trials: list[TrialResult] = []
    for scenario in corpus:
        result = execute_trial(scenario, pricing)
        trials.append(result)
        print(f"{result.scenario_id}: {result.outcome.value}")
    artifact = build_artifact(identifier, now.isoformat(), pricing, tuple(trials))
    artifact_path = Path("docs/artifacts/controlled-provider-quality-baseline.json")
    history_path = Path("docs/artifacts/controlled-provider-quality-history.json")
    write_artifact_atomic(artifact_path, artifact)
    append_benchmark_history(history_path, history_entry(artifact))
    print(f"Benchmark: {identifier}")
    print(f"Root conclusion: {artifact['root_conclusion']}")
    return (
        0
        if artifact["root_conclusion"] == "CONTROLLED_PROVIDER_BASELINE_COMPLETE"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
