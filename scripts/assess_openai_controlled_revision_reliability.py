"""Opt-in, content-free Controlled Revision model reliability assessment."""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.projector import (
    _COMPONENT_SHAPE_INSTRUCTIONS,
)

try:
    from scripts.validate_openai_controlled_revision_e2e import (
        SCENARIOS,
        ScenarioResult,
        execute_scenario,
    )
except ModuleNotFoundError:  # Direct script execution puts scripts/ on sys.path.
    from validate_openai_controlled_revision_e2e import (  # type: ignore[no-redef]
        SCENARIOS,
        ScenarioResult,
        execute_scenario,
    )

LIVE_FLAG = "SCOUT_RUN_LIVE_OPENAI_PART5I"
MODELS_VARIABLE = "SCOUT_PART5I_MODELS"
SCENARIOS_VARIABLE = "SCOUT_PART5I_SCENARIOS"
RUNS_VARIABLE = "SCOUT_PART5I_RUNS_PER_SCENARIO"
MAXIMUM_REQUESTS = 40
ALLOWED_MODELS = frozenset({"gpt-4.1-mini", "gpt-4.1"})
FROZEN_SCHEMA_SHA256 = (
    "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
)
FROZEN_DTO_SHA256 = "3973409a1069fd0d9b965aeddb554604dda452bdb570631c443056288fdca6ee"
ARTIFACT_PATH = Path("docs/artifacts/openai-controlled-revision-model-reliability.json")


class AssessmentConfigurationError(ValueError):
    """Raised before execution when explicit assessment controls are invalid."""


@dataclass(frozen=True, slots=True)
class AssessmentConfiguration:
    models: tuple[str, ...]
    scenarios: tuple[str, ...]
    runs_per_scenario: int

    @property
    def request_budget(self) -> int:
        return len(self.models) * len(self.scenarios) * self.runs_per_scenario


@dataclass(frozen=True, slots=True)
class TrialPlan:
    ordinal: int
    sample_index: int
    scenario: str
    model: str


@dataclass(frozen=True, slots=True)
class TrialRecord:
    scenario: str
    configured_model: str
    sample_index: int
    result_category: str
    furthest_stage: str
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    usage_available: bool
    request_id_available: bool
    returned_model_available: bool
    dto_error_count: int | None
    affected_component_count: int | None
    union_error_count: int | None
    union_expansion_suspected: bool | None
    duplicate_reference_triggered: bool | None
    primary_safe_category: str | None
    aggregate_pass: bool


def parse_configuration(environment: dict[str, str]) -> AssessmentConfiguration:
    """Parse an explicit, bounded assessment configuration."""

    models = _parse_list(environment.get(MODELS_VARIABLE), "model")
    unknown_models = set(models) - ALLOWED_MODELS
    if unknown_models:
        raise AssessmentConfigurationError("unsupported assessment model")
    scenarios = _parse_list(environment.get(SCENARIOS_VARIABLE), "scenario")
    known = {item.identifier for item in SCENARIOS}
    if set(scenarios) - known:
        raise AssessmentConfigurationError("unknown assessment scenario")
    try:
        runs = int(environment.get(RUNS_VARIABLE, ""))
    except ValueError as error:
        raise AssessmentConfigurationError(
            "run count must be a positive integer"
        ) from error
    if runs <= 0:
        raise AssessmentConfigurationError("run count must be a positive integer")
    configuration = AssessmentConfiguration(models, scenarios, runs)
    if configuration.request_budget > MAXIMUM_REQUESTS:
        raise AssessmentConfigurationError("assessment request budget exceeds maximum")
    return configuration


def build_plan(configuration: AssessmentConfiguration) -> tuple[TrialPlan, ...]:
    """Build sample/scenario/model interleaving deterministically."""

    plans: list[TrialPlan] = []
    for sample in range(1, configuration.runs_per_scenario + 1):
        for scenario in configuration.scenarios:
            for model in configuration.models:
                plans.append(TrialPlan(len(plans) + 1, sample, scenario, model))
    return tuple(plans)


def wilson_interval(successes: int, trials: int) -> tuple[float, float] | None:
    """Return the deterministic 95% Wilson score interval."""

    if trials == 0:
        return None
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1 + z * z / trials
    centre = (proportion + z * z / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
        )
        / denominator
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def record_trial(plan: TrialPlan, result: ScenarioResult) -> TrialRecord:
    """Reduce one execution to approved content-free metadata."""

    metadata = dict(result.dto_safe_metadata)
    category = _category(result, metadata)
    dto_valid = result.dto_validated or result.dto_validations > 0
    stage = "request_started"
    if result.attempts:
        stage = "provider_response_received"
    if result.dto_entered:
        stage = "json_decoded"
    if dto_valid:
        stage = "provider_dto_validated"
    if result.authorizations:
        stage = "references_authorized"
    if result.reconstructions:
        stage = "draft_reconstructed"
    if result.domain_validations:
        stage = "episode_draft_validated"
    if result.gateway_results:
        stage = "gateway_result_created"
    if result.acceptance is not None:
        stage = "acceptance_evaluated"
    if result.passed:
        stage = "aggregate_passed"
    usage = result.total_tokens > 0
    return TrialRecord(
        scenario=plan.scenario,
        configured_model=plan.model,
        sample_index=plan.sample_index,
        result_category=category,
        furthest_stage=stage,
        duration_ms=round(result.duration_ms),
        input_tokens=result.prompt_tokens if usage else None,
        output_tokens=result.completion_tokens if usage else None,
        total_tokens=result.total_tokens if usage else None,
        usage_available=usage,
        request_id_available=result.request_id_available,
        returned_model_available=result.model_id_available,
        dto_error_count=_integer(metadata.get("total_error_count")),
        affected_component_count=_integer(metadata.get("affected_component_count")),
        union_error_count=_integer(metadata.get("union_branch_error_count")),
        union_expansion_suspected=_boolean(metadata.get("union_expansion_suspected")),
        duplicate_reference_triggered=_boolean(
            metadata.get("duplicate_reference_validator_triggered")
        ),
        primary_safe_category=metadata.get("probable_primary_failure_category"),
        aggregate_pass=result.passed,
    )


def summarize(records: tuple[TrialRecord, ...]) -> list[dict[str, object]]:
    """Aggregate records by model and scenario without content fields."""

    groups: dict[tuple[str, str], list[TrialRecord]] = defaultdict(list)
    for record in records:
        groups[(record.configured_model, record.scenario)].append(record)
    summaries = []
    for (model, scenario), values in sorted(groups.items()):
        categories = Counter(item.result_category for item in values)
        dto_passes = sum(
            item.furthest_stage
            in {
                "provider_dto_validated",
                "references_authorized",
                "draft_reconstructed",
                "episode_draft_validated",
                "gateway_result_created",
                "acceptance_evaluated",
                "aggregate_passed",
            }
            for item in values
        )
        interval = wilson_interval(dto_passes, len(values))
        durations = [item.duration_ms for item in values]
        tokens = [item.total_tokens for item in values if item.total_tokens is not None]
        summaries.append(
            {
                "model": model,
                "scenario": scenario,
                "completed_trials": len(values),
                "dto_passes": dto_passes,
                "dto_failures": len(values) - dto_passes,
                "malformed_component_failures": categories[
                    "PROVIDER_DTO_MALFORMED_COMPONENT"
                ],
                "other_structural_failures": sum(
                    count
                    for category, count in categories.items()
                    if category.startswith("PROVIDER_DTO_")
                    and category != "PROVIDER_DTO_MALFORMED_COMPONENT"
                ),
                "authorization_failures": categories["REFERENCE_AUTHORIZATION_FAILURE"],
                "editorial_failures": categories["EDITORIAL_ACCEPTANCE_FAILURE"],
                "end_to_end_passes": sum(item.aggregate_pass for item in values),
                "external_failures": categories["EXTERNAL_PROVIDER_FAILURE"],
                "dto_success_rate": dto_passes / len(values),
                "dto_wilson_95": list(interval) if interval else None,
                "end_to_end_success_rate": sum(item.aggregate_pass for item in values)
                / len(values),
                "median_duration_ms": statistics.median(durations),
                "median_total_tokens": statistics.median(tokens) if tokens else None,
            }
        )
    return summaries


def schema_fingerprint_valid() -> bool:
    return _sha256(controlled_revision_schema_json()) == FROZEN_SCHEMA_SHA256


def dto_fingerprint_valid() -> bool:
    canonical = json.dumps(
        OpenAIControlledRevisionProviderOutput.model_json_schema(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical) == FROZEN_DTO_SHA256


def main() -> int:
    """Validate configuration, optionally execute, and write a safe artifact."""

    try:
        configuration = parse_configuration(dict(os.environ))
    except AssessmentConfigurationError as error:
        print(f"Configuration error: {error}")
        return 2
    plan = build_plan(configuration)
    print("Scout Controlled Revision Part 5I — Preflight")
    print(f"Models: {','.join(configuration.models)}")
    print(f"Scenarios: {','.join(configuration.scenarios)}")
    print(f"Runs per scenario: {configuration.runs_per_scenario}")
    print(f"Maximum planned requests: {configuration.request_budget}")
    print("Maximum attempts per trial: 1")
    print("SDK retries: 0")
    print("Fallback policy: none")
    print(
        f"Schema fingerprint verified: {'PASS' if schema_fingerprint_valid() else 'FAIL'}"
    )
    print(f"DTO fingerprint verified: {'PASS' if dto_fingerprint_valid() else 'FAIL'}")
    print(
        "Prompt correction present: "
        f"{'PASS' if _COMPONENT_SHAPE_INSTRUCTIONS else 'FAIL'}"
    )
    if not schema_fingerprint_valid() or not dto_fingerprint_valid():
        print("Status: STOPPED — frozen contract drift")
        return 2
    if os.environ.get(LIVE_FLAG) != "1":
        print("Live assessment skipped")
        print("Provider calls: 0")
        print("SDK requests: 0")
        return 0
    if resolve_openai_api_key() is None:
        print("Status: STOPPED — credential unavailable")
        return 2
    by_identifier = {item.identifier: item for item in SCENARIOS}
    records = []
    for item in plan:
        result = execute_scenario(
            by_identifier[item.scenario],
            item.ordinal,
            item.model,
            capture_dto_diagnostics=True,
        )
        record = record_trial(item, result)
        records.append(record)
        print(
            f"Trial {item.ordinal}/{len(plan)}: {item.scenario} {item.model} "
            f"sample {item.sample_index} — {record.result_category}"
        )
    artifact = {
        "assessment_version": "part5i-v1",
        "configuration": asdict(configuration),
        "request_budget": configuration.request_budget,
        "ordering": "sample, scenario, model",
        "schema_sha256": FROZEN_SCHEMA_SHA256,
        "dto_sha256": FROZEN_DTO_SHA256,
        "trials": [asdict(item) for item in records],
        "summary": summarize(tuple(records)),
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Completed live requests: {len(records)}")
    print(f"Safe artifact: {ARTIFACT_PATH}")
    return 0


def _parse_list(raw: str | None, label: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in (raw or "").split(",") if item.strip())
    if not values or len(values) != len(set(values)):
        raise AssessmentConfigurationError(f"explicit unique {label} list required")
    return values


def _category(result: ScenarioResult, metadata: dict[str, str]) -> str:
    if result.passed:
        return "PASS"
    if result.dto_entered and not result.dto_validated:
        if metadata.get("duplicate_reference_validator_triggered") == "yes":
            return "PROVIDER_DTO_DUPLICATE_REFERENCE"
        if (
            metadata.get("probable_primary_failure_category")
            == "invalid_component_shape"
        ):
            return "PROVIDER_DTO_MALFORMED_COMPONENT"
        return "PROVIDER_DTO_OTHER_STRUCTURAL_FAILURE"
    if result.acceptance is not None:
        return "EDITORIAL_ACCEPTANCE_FAILURE"
    if result.classification.startswith("openai_provider_"):
        return "EXTERNAL_PROVIDER_FAILURE"
    return "UNCLASSIFIED_FAILURE"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _integer(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _boolean(value: str | None) -> bool | None:
    return {"yes": True, "no": False}.get(value) if value is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
