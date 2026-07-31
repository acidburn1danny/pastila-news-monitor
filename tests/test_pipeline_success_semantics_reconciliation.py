"""Offline tests for Part 7C.2.1 metric semantics reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.reconcile_pipeline_success_semantics import (
    SOURCE_RUN_ID,
    derive_semantic_metrics,
    reconcile_artifact,
    reconcile_history,
    render_report,
)

ARTIFACT = Path("docs/artifacts/controlled-provider-quality-baseline-7c-2.json")
HISTORY = Path("docs/artifacts/controlled-provider-quality-history.json")
REPORT = Path("docs/controlled-provider-quality-baseline-7c-2.md")


def _artifact():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_frozen_trial_evidence_separates_technical_and_editorial_success():
    metrics = derive_semantic_metrics(_artifact()["trials"])

    assert metrics == {
        "technical_pipeline_successes": 24,
        "editorial_evaluation_attempts": 24,
        "editorial_evaluation_completions": 24,
        "editorial_acceptance_passes": 1,
        "editorial_acceptance_failures": 23,
    }


def test_editorial_rejection_does_not_erase_technical_completion():
    trials = [
        {
            "operational_outcome": "PIPELINE_SUCCESS",
            "quality": {"editorial_acceptance": False},
        }
    ]

    metrics = derive_semantic_metrics(trials)

    assert metrics["technical_pipeline_successes"] == 1
    assert metrics["editorial_acceptance_passes"] == 0
    assert metrics["editorial_acceptance_failures"] == 1


def test_reconciliation_preserves_raw_trials_and_adds_auditable_semantics():
    source = _artifact()
    frozen_trials = json.dumps(source["trials"], sort_keys=True)

    reconciled = reconcile_artifact(source, "2026-07-28T12:30:00+00:00")

    assert json.dumps(reconciled["trials"], sort_keys=True) == frozen_trials
    assert reconciled["pipeline_funnel"]["pipeline_successes"] == 24
    assert reconciled["pipeline_funnel"]["technical_pipeline_successes"] == 24
    assert reconciled["pipeline_funnel"]["editorial_acceptance_passes"] == 1
    assert reconciled["reconciliation"]["provider_requests_executed"] == 0
    assert reconciled["reconciliation"]["raw_scenario_results_modified"] is False


def test_aggregate_invariants_reject_editorial_evaluation_without_technical_output():
    trials = [
        {
            "operational_outcome": "PROVIDER_OUTPUT_REJECTED_SAFELY",
            "quality": {"editorial_acceptance": False},
        }
    ]
    with pytest.raises(ValueError, match="exceed"):
        derive_semantic_metrics(trials)


def test_history_reconciliation_changes_only_matching_entry_additively():
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    prior = json.dumps(history["history"][:2], sort_keys=True)
    metrics = derive_semantic_metrics(_artifact()["trials"])

    reconciled = reconcile_history(history, metrics)

    assert json.dumps(reconciled["history"][:2], sort_keys=True) == prior
    entry = next(
        item for item in reconciled["history"] if item["benchmark_id"] == SOURCE_RUN_ID
    )
    assert entry["benchmark_id"] == SOURCE_RUN_ID
    assert entry["pipeline_success_semantics"] == "technical_pipeline_completion"
    assert entry["editorial_acceptance_passes"] == 1
    assert entry["editorial_acceptance_failures"] == 23


def test_reconciled_markdown_uses_the_same_canonical_counts():
    reconciled = reconcile_artifact(_artifact(), "2026-07-28T12:30:00+00:00")
    report = render_report(reconciled)

    assert "Technical pipeline successes: 24" in report
    assert "Editorial evaluations completed: 24" in report
    assert "Editorial acceptance passes: 1" in report
    assert "Editorial acceptance failures: 23" in report


def test_quality_sample_and_part_7h_readiness_use_evaluable_output_count():
    artifact = reconcile_artifact(_artifact(), "2026-07-28T12:30:00+00:00")
    metrics = artifact["pipeline_funnel"]

    assert metrics["editorial_evaluation_completions"] >= 12
    assert artifact["quality_sample_status"] == "SUFFICIENT"
    assert artifact["final_recommendation"] == (
        "RUN_CONTROLLED_PROMPT_EFFECTIVENESS_EXPERIMENT"
    )


def test_checked_in_json_markdown_and_history_use_identical_semantics():
    artifact = _artifact()
    funnel = artifact["pipeline_funnel"]
    history = next(
        item
        for item in json.loads(HISTORY.read_text(encoding="utf-8"))["history"]
        if item["benchmark_id"] == SOURCE_RUN_ID
    )
    report = REPORT.read_text(encoding="utf-8")

    assert artifact["schema_version"] == 4
    assert funnel["technical_pipeline_successes"] == 24
    assert funnel["editorial_evaluation_completions"] == 24
    assert funnel["editorial_acceptance_passes"] == 1
    assert funnel["editorial_acceptance_failures"] == 23
    assert history["technical_pipeline_successes"] == 24
    assert history["editorial_acceptance_passes"] == 1
    assert "Technical pipeline successes: 24" in report
    assert "Editorial acceptance passes: 1" in report
    assert artifact["root_conclusion"] == history["root_conclusion"]
