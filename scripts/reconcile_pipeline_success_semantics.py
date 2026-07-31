"""Reconcile Part 7C.2 derived metrics from its frozen scenario evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.run_controlled_provider_quality_baseline import write_artifact_atomic

ARTIFACT_PATH = Path("docs/artifacts/controlled-provider-quality-baseline-7c-2.json")
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
REPORT_PATH = Path("docs/controlled-provider-quality-baseline-7c-2.md")
SOURCE_RUN_ID = "20260728-120420-openai-gpt-4.1-mini-7c2"
QUALITY_THRESHOLD = 12


def derive_semantic_metrics(trials) -> dict[str, int]:
    """Derive explicit technical and editorial counts from frozen trial records."""

    technical = sum(
        item.get("operational_outcome") == "PIPELINE_SUCCESS" for item in trials
    )
    evaluated = tuple(item for item in trials if item.get("quality") is not None)
    accepted = sum(
        bool(item["quality"].get("editorial_acceptance")) for item in evaluated
    )
    metrics = {
        "technical_pipeline_successes": technical,
        "editorial_evaluation_attempts": len(evaluated),
        "editorial_evaluation_completions": len(evaluated),
        "editorial_acceptance_passes": accepted,
        "editorial_acceptance_failures": len(evaluated) - accepted,
    }
    if metrics["editorial_evaluation_attempts"] > technical:
        raise ValueError("editorial evaluations exceed technical completions")
    if accepted + metrics["editorial_acceptance_failures"] != len(evaluated):
        raise ValueError("editorial outcomes do not reconcile")
    return metrics


def reconcile_artifact(artifact: dict[str, object], reconciled_at: str):
    """Return a backward-compatible artifact with explicit metric semantics."""

    if artifact.get("benchmark_id") != SOURCE_RUN_ID:
        raise ValueError("unexpected Part 7C.2 source run")
    trials = artifact.get("trials")
    if not isinstance(trials, list) or len(trials) != 24:
        raise ValueError("frozen Part 7C.2 trials are unavailable")
    metrics = derive_semantic_metrics(trials)
    funnel = dict(artifact["pipeline_funnel"])
    original = {
        "pipeline_successes": funnel["pipeline_successes"],
        "editorial_acceptance_passes": funnel["editorial_acceptance_passes"],
    }
    funnel.update(metrics)
    funnel["pipeline_successes"] = metrics["technical_pipeline_successes"]
    funnel["quality_evaluation_completions"] = metrics[
        "editorial_evaluation_completions"
    ]
    if (
        funnel["episode_draft_validation_passes"]
        < metrics["technical_pipeline_successes"]
    ):
        raise ValueError("technical successes exceed valid EpisodeDraft outputs")
    updated = dict(artifact)
    updated["schema_version"] = 4
    updated["pipeline_funnel"] = funnel
    updated["metric_semantics"] = {
        "pipeline_successes": {
            "status": "deprecated_alias",
            "canonical_field": "technical_pipeline_successes",
            "definition": "valid EpisodeDraft produced by the technical provider pipeline",
            "includes_editorial_acceptance": False,
        },
        "editorial_acceptance_passes": {
            "definition": "technically valid output passing the frozen editorial rubric",
            "includes_technical_completion": True,
        },
        "quality_sample_sufficiency": {
            "denominator": "editorial_evaluation_completions",
            "minimum": QUALITY_THRESHOLD,
        },
    }
    updated["reconciliation"] = {
        "reconciliation_milestone": "Part 7C.2.1",
        "reconciled_at": reconciled_at,
        "source_run_id": SOURCE_RUN_ID,
        "provider_requests_executed": 0,
        "benchmark_executions": 0,
        "benchmark_replays": 0,
        "raw_scenario_results_modified": False,
        "semantic_fields_reconciled": [
            "pipeline_funnel.technical_pipeline_successes",
            "pipeline_funnel.editorial_evaluation_attempts",
            "pipeline_funnel.editorial_evaluation_completions",
            "pipeline_funnel.editorial_acceptance_passes",
            "pipeline_funnel.editorial_acceptance_failures",
        ],
        "previous_metric_names": ["pipeline_successes"],
        "canonical_metric_names": [
            "technical_pipeline_successes",
            "editorial_evaluation_completions",
            "editorial_acceptance_passes",
            "editorial_acceptance_failures",
        ],
        "previous_aggregate_values": original,
        "reconciled_aggregate_values": metrics,
        "reason": "funnel rendering conflated technical completion with editorial acceptance",
        "evidence": [
            "OperationalOutcome.PIPELINE_SUCCESS",
            "test_acceptance_failure_remains_pipeline_success",
            "frozen Part 7C.2 trial quality records",
        ],
    }
    return updated


def reconcile_history(history: dict[str, object], metrics: dict[str, int]):
    """Add semantic metadata only to the matching history entry."""

    updated = json.loads(json.dumps(history))
    matches = [
        item for item in updated["history"] if item["benchmark_id"] == SOURCE_RUN_ID
    ]
    if len(matches) != 1:
        raise ValueError("Part 7C.2 history entry is unavailable")
    entry = matches[0]
    if entry.get("pipeline_success_count") != metrics["technical_pipeline_successes"]:
        raise ValueError("history technical success count is inconsistent")
    entry.update(
        {
            "pipeline_success_semantics": "technical_pipeline_completion",
            **metrics,
            "full_benchmark_successes": None,
            "quality_sample_sufficiency_rule": "editorial_evaluation_completions >= 12",
            "ready_for_part_7h": metrics["editorial_evaluation_completions"]
            >= QUALITY_THRESHOLD,
            "reconciled_by": "Part 7C.2.1",
        }
    )
    return updated


def render_report(artifact: dict[str, object]) -> str:
    """Render the reconciled report without changing frozen observations."""

    funnel = artifact["pipeline_funnel"]
    return f"""# Controlled Provider Quality Baseline — Part 7C.2

## Reconciliation Notice

Part 7C.2.1 clarified that the original `pipeline_successes = 24` means technical
pipeline completion. The original funnel incorrectly copied that number into editorial
acceptance. Frozen scenario evidence yields 24 completed editorial evaluations, 1 pass,
and 23 failures. No provider request, replay, or raw result modification occurred.

## Canonical Funnel

- Provider DTO validation passes: {funnel['provider_dto_passes']}
- Authorization passes: {funnel['authorization_passes']}
- Reconstruction passes: {funnel['reconstruction_passes']}
- EpisodeDraft validation passes: {funnel['episode_draft_validation_passes']}
- Technical pipeline successes: {funnel['technical_pipeline_successes']}
- Editorial evaluations completed: {funnel['editorial_evaluation_completions']}
- Editorial acceptance passes: {funnel['editorial_acceptance_passes']}
- Editorial acceptance failures: {funnel['editorial_acceptance_failures']}

`pipeline_successes` remains a deprecated backward-compatible alias for technical
pipeline success. No full-benchmark-success metric is defined.

## Quality Sample Sufficiency

The frozen threshold is 12 editorially evaluable technical outputs. This run has
{funnel['editorial_evaluation_completions']}; therefore the sample is
`{artifact['quality_sample_status']}`. Acceptance is an outcome measured over this
sample, not its admission criterion.

## Reference Remediation

Exact reference compliance remains 24/24. Authorization, reconstruction, and valid
EpisodeDraft production remain 24/24. The remediation classification remains
`{artifact['remediation_effectiveness']}` and the root conclusion remains
`{artifact['root_conclusion']}`.

## Part 7C.1 Comparison

The comparison remains valid: technical pipeline successes advanced from 0 to 24.
Editorial acceptance is reported separately and is not attributed to Part 7G.

## Audit Metadata

```json
{json.dumps(artifact['reconciliation'], ensure_ascii=False, indent=2, sort_keys=True)}
```

## Final Recommendation

`{artifact['final_recommendation']}`
"""


def main() -> int:
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    reconciled_at = datetime.now(UTC).isoformat()
    reconciled = reconcile_artifact(artifact, reconciled_at)
    metrics = derive_semantic_metrics(reconciled["trials"])
    reconciled_history = reconcile_history(history, metrics)
    write_artifact_atomic(ARTIFACT_PATH, reconciled)
    write_artifact_atomic(HISTORY_PATH, reconciled_history)
    REPORT_PATH.write_text(render_report(reconciled), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
