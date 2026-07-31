"""Execute the single authorized Part 7C.2 post-remediation live baseline."""

from __future__ import annotations

import hashlib
import json
import os
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
    ProviderDiagnosticsArtifact,
    write_diagnostics_artifact_atomic,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    production_benchmark_configuration,
    project_production_request,
    validate_provider_compatibility,
)
from scripts.run_controlled_provider_quality_baseline import (
    PROMPT_VERSION,
    execute_trial,
    write_artifact_atomic,
)
from scripts.run_controlled_provider_quality_baseline_v2 import (
    build_history_entry,
    build_v2_artifacts,
)

OPT_IN = "SCOUT_RUN_LIVE_PROVIDER_BASELINE_7C2"
MILESTONE = "Part 7C.2"
BENCHMARK_VERSION = "controlled-provider-quality-baseline-7c2"
QUALITY_THRESHOLD = 12
ARTIFACT_PATH = Path("docs/artifacts/controlled-provider-quality-baseline-7c-2.json")
DIAGNOSTICS_PATH = Path(
    "docs/artifacts/controlled-provider-quality-diagnostics-7c-2.json"
)
REPORT_PATH = Path("docs/controlled-provider-quality-baseline-7c-2.md")
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
PART_7C1_PATH = Path("docs/artifacts/controlled-provider-quality-baseline-v2.json")
PART_7G_PATH = Path(
    "docs/artifacts/reference-contract-schema-projection-implementation.json"
)
PART_7F_PATH = Path("docs/artifacts/reference-contract-remediation-design.json")
PRICING_PATH = Path("config/controlled-revision-provider-pricing-v1.yaml")


class ProjectionInvariantError(RuntimeError):
    """Raised before transport when an effective schema diverges from authorization."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fingerprint_values(values: tuple[str, ...]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return _sha256_bytes(payload.encode())


def _projected_references(client_request) -> tuple[str, ...]:
    payload = client_request.payload
    schema = json.loads(payload.schema_document_json)
    try:
        return tuple(
            definition["properties"]["component_reference"]["const"]
            for definition in schema["$defs"].values()
        )
    except (KeyError, TypeError) as error:
        raise ProjectionInvariantError(
            "projected_schema_reference_shape_invalid"
        ) from error


def projection_checkpoint(scenario_id, invocation, client_request) -> dict[str, object]:
    """Inspect the actual transport payload and fail closed on any set divergence."""

    authorized = tuple(
        target.canonical_reference for target in invocation.request.revision_targets
    )
    projected = _projected_references(client_request)
    duplicates = tuple(
        sorted(value for value, count in Counter(projected).items() if count > 1)
    )
    authorized_set = set(authorized)
    projected_set = set(projected)
    record = {
        "scenario_id": scenario_id,
        "authorized_reference_count": len(authorized),
        "projected_schema_reference_count": len(projected),
        "authorized_reference_set_fingerprint": _fingerprint_values(
            tuple(sorted(authorized_set))
        ),
        "projected_schema_reference_set_fingerprint": _fingerprint_values(
            tuple(sorted(projected_set))
        ),
        "count_equality": len(authorized) == len(projected),
        "set_equality": authorized_set == projected_set,
        "missing_from_projection": sorted(authorized_set - projected_set),
        "unexpected_in_projection": sorted(projected_set - authorized_set),
        "duplicate_projected_references": list(duplicates),
        "effective_schema_fingerprint": client_request.payload.schema_fingerprint,
    }
    if not record["count_equality"] or not record["set_equality"] or duplicates:
        raise ProjectionInvariantError(
            "PRE_REQUEST_SCHEMA_PROJECTION_INVARIANT_FAILURE"
        )
    return record


def dry_run_projection(corpus) -> tuple[dict[str, object], ...]:
    """Assemble all actual production requests without invoking transport."""

    records = []
    for scenario in corpus:
        invocation = build_production_invocation(scenario)
        projected = project_production_request(scenario, invocation)
        records.append(
            projection_checkpoint(
                scenario.scenario_key, invocation, projected.client_request
            )
        )
    return tuple(records)


def _artifact_consistency() -> tuple[dict[str, object], dict[str, object]]:
    part_7f = json.loads(PART_7F_PATH.read_text(encoding="utf-8"))
    part_7g = json.loads(PART_7G_PATH.read_text(encoding="utf-8"))
    selected = part_7f.get("preferred_candidate", {})
    if selected.get("candidate_id") != "C2_DYNAMIC_EXACT_SCHEMA":
        raise RuntimeError("part_7f_decision_mismatch")
    if part_7g.get("root_conclusion") != (
        "EXACT_REFERENCE_SCHEMA_PROJECTION_IMPLEMENTED"
    ):
        raise RuntimeError("part_7g_conclusion_mismatch")
    if part_7g.get("recommended_next_milestone", "").split(" ", 2)[:2] != [
        "Part",
        "7C.2",
    ]:
        raise RuntimeError("part_7g_readiness_mismatch")
    return part_7f, part_7g


def preflight(benchmark_id: str):
    """Verify every frozen input and persistency boundary before live execution."""

    _artifact_consistency()
    configuration = production_benchmark_configuration()
    if (
        configuration.provider_identifier != "openai"
        or configuration.model_identifier != "gpt-4.1-mini"
        or configuration.retry_policy.maximum_attempts != 1
    ):
        raise RuntimeError("provider_configuration_mismatch")
    pricing = load_benchmark_pricing(PRICING_PATH)
    if pricing.provider != "openai" or pricing.model != "gpt-4.1-mini":
        raise RuntimeError("pricing_configuration_mismatch")
    corpus = build_synthetic_corpus()
    if tuple(item.scenario_key for item in corpus) != tuple(
        f"SYN-{number:02d}" for number in range(1, 25)
    ):
        raise RuntimeError("frozen_scenario_order_mismatch")
    if len({item.category for item in corpus}) != 12:
        raise RuntimeError("frozen_category_count_mismatch")
    if not all(validate_provider_compatibility(item).compatible for item in corpus):
        raise RuntimeError("scenario_compatibility_failure")
    if any(path.exists() for path in (ARTIFACT_PATH, DIAGNOSTICS_PATH, REPORT_PATH)):
        raise RuntimeError("part_7c2_artifact_already_exists")
    history = load_benchmark_history(HISTORY_PATH)
    if any(item.benchmark_id == benchmark_id for item in history.history):
        raise RuntimeError("duplicate_benchmark_id")
    for path in (ARTIFACT_PATH, DIAGNOSTICS_PATH, REPORT_PATH, HISTORY_PATH):
        _validate_writable(path)
    checkpoints = dry_run_projection(corpus)
    if len(checkpoints) != 24:
        raise RuntimeError("dry_run_projection_count_mismatch")
    return configuration, pricing, corpus, checkpoints


def _validate_writable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".part7c2-preflight-", dir=path.parent)
    os.close(descriptor)
    Path(name).unlink()


def _projection_aggregate(records) -> dict[str, object]:
    count_passes = sum(bool(item["count_equality"]) for item in records)
    set_passes = sum(bool(item["set_equality"]) for item in records)
    return {
        "scenarios_checked": len(records),
        "count_equality_passes": count_passes,
        "count_equality_failures": len(records) - count_passes,
        "set_equality_passes": set_passes,
        "set_equality_failures": len(records) - set_passes,
        "all_scenarios_passed": count_passes == set_passes == len(records),
        "authorized_reference_count_total": sum(
            int(item["authorized_reference_count"]) for item in records
        ),
        "projected_schema_reference_count_total": sum(
            int(item["projected_schema_reference_count"]) for item in records
        ),
        "scenarios": list(records),
    }


def _safe_provider_configuration() -> dict[str, object]:
    configuration = production_benchmark_configuration().model_dump(mode="json")
    configuration.pop("authentication_reference", None)
    configuration["authentication"] = "environment credential reference (redacted)"
    return configuration


def _exact_compliance(diagnostic) -> bool:
    references = diagnostic.references
    return bool(
        references.authorized_reference_count
        and not references.unknown_references
        and not references.unauthorized_references
        and not references.missing_authorized_references
        and not references.duplicate_provider_references
        and set(references.provider_produced_references_ordered)
        == set(references.authorized_references)
    )


def _comparison(artifact, baseline) -> dict[str, object]:
    current_funnel = artifact["pipeline_funnel"]
    prior_funnel = baseline["pipeline_funnel"]
    current_reference = artifact["reference_metrics"]
    prior_reference = baseline["reference_metrics"]
    current_cost = artifact["cost_metrics"]["known_estimated_total_cost_usd"]
    prior_cost = baseline["cost_metrics"]["known_estimated_total_cost_usd"]
    reference_totals = {
        name: [
            _reference_total(baseline, name),
            _reference_total(artifact, name),
        ]
        for name in (
            "unknown_references",
            "unauthorized_references",
            "missing_authorized_references",
            "duplicate_provider_references",
        )
    }
    return {
        "part_7c_1_benchmark_id": baseline["benchmark_id"],
        "provider_requests": [
            baseline["provider_request_count"],
            artifact["provider_request_count"],
        ],
        "authorization_passes": [
            prior_funnel["authorization_passes"],
            current_funnel["authorization_passes"],
        ],
        "reconstruction_passes": [
            prior_funnel["reconstruction_passes"],
            current_funnel["reconstruction_passes"],
        ],
        "pipeline_successes": [
            prior_funnel["pipeline_successes"],
            current_funnel["pipeline_successes"],
        ],
        "unknown_references": reference_totals["unknown_references"],
        "unauthorized_references": reference_totals["unauthorized_references"],
        "missing_authorized_references": reference_totals[
            "missing_authorized_references"
        ],
        "duplicate_references": reference_totals["duplicate_provider_references"],
        "average_reference_precision": [
            (
                prior_reference["precision"]["mean"]
                if prior_reference["precision"]
                else None
            ),
            (
                current_reference["precision"]["mean"]
                if current_reference["precision"]
                else None
            ),
        ],
        "average_reference_recall": [
            prior_reference["recall"]["mean"] if prior_reference["recall"] else None,
            (
                current_reference["recall"]["mean"]
                if current_reference["recall"]
                else None
            ),
        ],
        "total_cost_usd": [prior_cost, current_cost],
    }


def _reference_total(artifact, field: str) -> int:
    return sum(
        len(trial.get("references", {}).get(field, ()))
        for trial in artifact.get("trials", ())
    )


def build_artifacts(benchmark_id, created_at, pricing, results, checkpoints):
    """Build comparable structured artifacts without altering trial evidence."""

    artifact, diagnostics = build_v2_artifacts(
        benchmark_id, created_at, pricing, results
    )
    artifact.update(
        {
            "schema_version": 3,
            "benchmark_name": "Controlled Provider Quality Baseline After Reference Contract Remediation",
            "benchmark_version": BENCHMARK_VERSION,
            "milestone": MILESTONE,
            "official_baseline": True,
            "production_prompt_fingerprint": PROMPT_VERSION,
            "provider_configuration": _safe_provider_configuration(),
            "provider_configuration_fingerprint": _sha256_bytes(
                json.dumps(
                    _safe_provider_configuration(),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ),
            "pricing_configuration": pricing.model_dump(mode="json"),
            "pricing_fingerprint": _sha256_bytes(PRICING_PATH.read_bytes()),
            "part_7g_artifact_fingerprint": _sha256_bytes(PART_7G_PATH.read_bytes()),
            "projection_checkpoint": _projection_aggregate(checkpoints),
            "repository_revision": None,
            "working_tree_status": "git metadata unavailable in workspace",
        }
    )
    diagnostic_items = tuple(item.provider_diagnostic for item in results)
    compliance = sum(_exact_compliance(item) for item in diagnostic_items)
    artifact["reference_metrics"]["exact_reference_compliance_scenarios"] = compliance
    artifact["reference_metrics"]["exact_reference_compliance_rate"] = compliance / len(
        diagnostic_items
    )
    quality_status = artifact["quality_sample_status"]
    if quality_status == "SUFFICIENT":
        effectiveness = "EFFECTIVE"
        root = "REFERENCE_CONTRACT_REMEDIATION_EFFECTIVE"
        recommendation = "RUN_CONTROLLED_PROMPT_EFFECTIVENESS_EXPERIMENT"
    elif compliance:
        effectiveness = "PARTIALLY_EFFECTIVE"
        root = "REFERENCE_CONTRACT_REMEDIATION_PARTIALLY_EFFECTIVE"
        recommendation = "INVESTIGATE_POST_AUTHORIZATION_FAILURES"
    else:
        effectiveness = "INEFFECTIVE"
        root = "REFERENCE_CONTRACT_REMEDIATION_INEFFECTIVE"
        recommendation = "RETURN_TO_REFERENCE_CONTRACT_ARCHITECTURE_REVIEW"
    artifact["remediation_effectiveness"] = effectiveness
    artifact["root_conclusion"] = root
    artifact["final_recommendation"] = recommendation
    baseline = json.loads(PART_7C1_PATH.read_text(encoding="utf-8"))
    artifact["comparison_with_part_7c_1"] = _comparison(artifact, baseline)
    _validate_integrity(artifact)
    return artifact, diagnostics


def _validate_integrity(artifact) -> None:
    checkpoint = artifact["projection_checkpoint"]
    if not checkpoint["all_scenarios_passed"]:
        raise RuntimeError("projection_checkpoint_failed")
    if artifact["provider_request_count"] != 24:
        raise RuntimeError("provider_request_count_mismatch")
    if (
        artifact["retry_count"]
        or artifact["fallback_count"]
        or artifact["scenario_replay_count"]
    ):
        raise RuntimeError("execution_policy_integrity_failure")
    if len(artifact["trials"]) != 24:
        raise RuntimeError("trial_count_mismatch")
    serialized = json.dumps(artifact, ensure_ascii=False).casefold()
    if any(secret in serialized for secret in ("api_key", "bearer ", "authorization:")):
        raise RuntimeError("privacy_validation_failure")


def _history_entry(artifact) -> BenchmarkHistoryEntry:
    entry = build_history_entry(artifact).model_dump(mode="python")
    entry.update(
        {
            "benchmark_version": BENCHMARK_VERSION,
            "root_conclusion": artifact["root_conclusion"],
            "official_baseline": artifact["official_baseline"],
            "replay_count": artifact["scenario_replay_count"],
            "authorization_passes": artifact["pipeline_funnel"]["authorization_passes"],
            "reconstruction_passes": artifact["pipeline_funnel"][
                "reconstruction_passes"
            ],
            "exact_reference_compliance_rate": artifact["reference_metrics"][
                "exact_reference_compliance_rate"
            ],
            "quality_sample_sufficiency": artifact["quality_sample_status"],
        }
    )
    return BenchmarkHistoryEntry.model_validate(entry)


def write_report(artifact) -> None:
    """Write a complete UTF-8 human-readable benchmark report."""

    comparison = artifact["comparison_with_part_7c_1"]
    report = f"""# Controlled Provider Quality Baseline — Part 7C.2

## Executive Summary

The official post-remediation run sent {artifact['provider_request_count']} requests
with zero retries, fallbacks, and replays. Remediation effectiveness is
`{artifact['remediation_effectiveness']}` and the root conclusion is
`{artifact['root_conclusion']}`.

## Projection Checkpoint

```json
{json.dumps(artifact['projection_checkpoint'], ensure_ascii=False, indent=2, sort_keys=True)}
```

## Pipeline Funnel

```json
{json.dumps(artifact['pipeline_funnel'], indent=2, sort_keys=True)}
```

## Reference Metrics

```json
{json.dumps(artifact['reference_metrics'], ensure_ascii=False, indent=2, sort_keys=True)}
```

## Quality, Latency, Usage, and Cost

```json
{json.dumps({'quality': artifact['quality_metrics'], 'latency': artifact['latency_metrics'], 'usage': artifact['usage_metrics'], 'cost': artifact['cost_metrics']}, indent=2, sort_keys=True)}
```

## Direct Comparison With Part 7C.1

```json
{json.dumps(comparison, indent=2, sort_keys=True)}
```

## Experimental Integrity

The 24-scenario corpus, scenario order, production prompt identity, model,
single-attempt retry policy, no-fallback policy, exact authorization, deterministic
reconstruction, diagnostics, and pricing methodology were preserved. The only intended
independent variable was the invocation-specific exact-reference schema introduced by
Part 7G. No output was repaired, normalized, aliased, retried, or replayed.

## Root Conclusion

`{artifact['root_conclusion']}`

## Final Recommendation

`{artifact['final_recommendation']}`
"""
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")


def main() -> int:
    now = datetime.now(UTC)
    benchmark_id = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini-7c2")
    try:
        _, pricing, corpus, dry_checkpoints = preflight(benchmark_id)
    except Exception as error:  # noqa: BLE001 - bounded preflight signal
        print(f"BENCHMARK_ABORTED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(
        f"Dry run: {len(dry_checkpoints)} scenarios, "
        f"{sum(bool(item['set_equality']) for item in dry_checkpoints)} exact sets"
    )
    if os.environ.get(OPT_IN) != "1":
        print(f"Live Part 7C.2 disabled; set {OPT_IN}=1 for exactly 24 requests.")
        return 0
    if resolve_openai_api_key() is None:
        print("BENCHMARK_ABORTED: credential unavailable", file=sys.stderr)
        return 2

    results = []
    live_checkpoints = []
    for scenario in corpus:
        record: dict[str, object] = {}

        def gate(
            invocation,
            client_request,
            *,
            scenario_id=scenario.scenario_key,
            sink=record,
        ):
            sink.update(projection_checkpoint(scenario_id, invocation, client_request))

        result = execute_trial(scenario, pricing, pre_request_validator=gate)
        if (
            not record
            or not record.get("count_equality")
            or not record.get("set_equality")
        ):
            print(
                f"BENCHMARK_ABORTED: {scenario.scenario_key} projection gate did not pass",
                file=sys.stderr,
            )
            return 2
        live_checkpoints.append(record)
        results.append(result)
        print(f"{scenario.scenario_key}: {result.outcome.value}")
    artifact, diagnostics = build_artifacts(
        benchmark_id, now.isoformat(), pricing, tuple(results), tuple(live_checkpoints)
    )
    write_artifact_atomic(ARTIFACT_PATH, artifact)
    write_diagnostics_artifact_atomic(DIAGNOSTICS_PATH, diagnostics)
    ProviderDiagnosticsArtifact.model_validate_json(
        DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    )
    append_benchmark_history(HISTORY_PATH, _history_entry(artifact))
    write_report(artifact)
    print(f"Benchmark: {benchmark_id}")
    print(f"Root conclusion: {artifact['root_conclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
