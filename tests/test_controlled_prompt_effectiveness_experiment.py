"""Offline Part 7H taxonomy, prompt, checkpoint, and decision tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_controlled_provider_quality_baseline_v2 import _result

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    project_production_request,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    ARTIFACT_PATH,
    CANDIDATE_ADDITION,
    DESIGN_PATH,
    HISTORY_PATH,
    REPORT_PATH,
    _sha,
    _transform_request,
    build_experiment_artifact,
    candidate_prompt,
    control_prompt,
    dry_run,
    freeze_design,
    prompt_projection_checkpoint,
)


def _design(tmp_path: Path):
    return freeze_design(tmp_path / "design.json")


def test_failure_taxonomy_is_derived_from_frozen_control_evidence(tmp_path):
    design = _design(tmp_path)
    counts = {
        item["category_id"]: item["scenario_count"] for item in design["taxonomy"]
    }

    assert counts == {"SOURCE_AUTHORITY_DRIFT": 21, "QUOTE_MUTATION": 2}
    assert all(
        item["prompt_addressability"] == "PROMPT_ADDRESSABLE"
        for item in design["taxonomy"]
    )


def test_exactly_one_evidence_mapped_candidate_is_frozen(tmp_path):
    design = _design(tmp_path)

    assert design["design_frozen"] is True
    assert len(design["candidate_changes"]) == 1
    assert design["candidate_changes"][0]["scenario_evidence"] == {
        "SOURCE_AUTHORITY_DRIFT": 21,
        "QUOTE_MUTATION": 2,
    }
    assert design["candidate_prompt"] == candidate_prompt()
    assert design["candidate_prompt_fingerprint"] == _sha(candidate_prompt())


def test_candidate_is_general_and_does_not_leak_benchmark_or_threshold(tmp_path):
    candidate = _design(tmp_path)["candidate_prompt"]

    assert "SYN-" not in candidate
    assert "acceptance threshold" not in candidate.casefold()
    assert "score" not in CANDIDATE_ADDITION.casefold()
    assert "story:101" not in candidate


def test_control_prompt_remains_the_unmodified_production_projection():
    projected = project_production_request(build_synthetic_corpus()[0])
    assert control_prompt() == projected.client_request.payload.instructions
    assert candidate_prompt() == control_prompt() + CANDIDATE_ADDITION


def test_offline_dry_run_checks_prompt_identity_and_exact_projection(tmp_path):
    records = dry_run(_design(tmp_path), build_synthetic_corpus())

    assert len(records) == 24
    assert all(item["prompt_identity"] for item in records)
    assert all(item["count_equality"] and item["set_equality"] for item in records)


def test_prompt_identity_checkpoint_rejects_control_prompt(tmp_path):
    design = _design(tmp_path)
    scenario = build_synthetic_corpus()[0]
    invocation = build_production_invocation(scenario)
    request = project_production_request(scenario, invocation).client_request

    with pytest.raises(RuntimeError, match="PROMPT_IDENTITY"):
        prompt_projection_checkpoint(scenario.scenario_key, invocation, request, design)


def test_request_transform_changes_only_the_experimental_instruction(tmp_path):
    design = _design(tmp_path)
    scenario = build_synthetic_corpus()[0]
    invocation = build_production_invocation(scenario)
    original = project_production_request(scenario, invocation).client_request
    transformed = _transform_request(invocation, original, design["candidate_prompt"])

    assert transformed.payload.instructions == design["candidate_prompt"]
    assert transformed.payload.input == original.payload.input
    assert (
        transformed.payload.schema_document_json
        == original.payload.schema_document_json
    )
    assert transformed.payload.model == original.payload.model


def test_precommitted_decision_adopts_material_editorial_improvement(tmp_path):
    design = _design(tmp_path)
    results = tuple(_result(number, success=True) for number in range(1, 25))
    checkpoints = dry_run(design, build_synthetic_corpus())

    artifact, _ = build_experiment_artifact(
        "20260728-130000-openai-gpt-4.1-mini-7h",
        "2026-07-28T13:00:00+00:00",
        design,
        results,
        checkpoints,
    )

    assert artifact["technical_non_regression"] is True
    assert artifact["reference_non_regression"] is True
    assert artifact["editorial_improvement"]["threshold_passed"] is True
    assert artifact["candidate_decision"] == "ADOPT"


def test_technical_regression_blocks_adoption(tmp_path):
    design = _design(tmp_path)
    results = tuple(_result(number, success=number != 1) for number in range(1, 25))
    checkpoints = dry_run(design, build_synthetic_corpus())

    artifact, _ = build_experiment_artifact(
        "20260728-130000-openai-gpt-4.1-mini-7h",
        "2026-07-28T13:00:00+00:00",
        design,
        results,
        checkpoints,
    )

    assert artifact["technical_non_regression"] is False
    assert artifact["candidate_decision"] == "REJECT"
    assert artifact["root_conclusion"] == (
        "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION"
    )


def test_design_artifact_contains_no_secret_or_provider_execution(tmp_path):
    design = _design(tmp_path)
    serialized = json.dumps(design).casefold()

    assert "api_key" not in serialized
    assert design["planned_provider_requests"] == 24
    assert design["planned_retries"] == 0
    assert design["planned_fallbacks"] == 0
    assert design["planned_replays"] == 0


def test_checked_in_experiment_preserves_request_budget_and_checkpoints():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))

    assert artifact["provider_request_count"] == 24
    assert artifact["retry_count"] == 0
    assert artifact["fallback_count"] == 0
    assert artifact["replay_count"] == 0
    assert artifact["projection_checkpoint"]["count_equality_passes"] == 24
    assert artifact["projection_checkpoint"]["set_equality_passes"] == 24
    assert artifact["prompt_identity_checkpoint"] == {
        "scenarios": 24,
        "passes": 24,
        "failures": 0,
    }


def test_checked_in_candidate_decision_follows_precommitted_non_regression_gates():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))

    assert artifact["technical_non_regression"] is False
    assert artifact["reference_non_regression"] is False
    assert artifact["editorial_improvement"]["threshold_passed"] is False
    assert artifact["candidate_decision"] == "REJECT"
    assert artifact["root_conclusion"] == (
        "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION"
    )


def test_checked_in_paired_analysis_reports_regressions_without_repair():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    editorial = artifact["editorial_metrics"]

    assert editorial["fail_to_pass"] == 0
    assert editorial["pass_to_fail"] == 1
    assert editorial["improved_score_scenarios"] == 2
    assert editorial["unchanged_score_scenarios"] == 20
    assert editorial["regressed_score_scenarios"] == 1
    assert artifact["pipeline_funnel"]["technical_pipeline_successes"] == 23
    assert artifact["quality_sample"] == "SUFFICIENT"


def test_checked_in_report_design_artifact_and_history_agree():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    history_entries = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))["history"]
    history = next(
        item for item in history_entries if item["benchmark_id"] == artifact["run_id"]
    )
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        artifact["candidate_prompt_fingerprint"]
        == design["candidate_prompt_fingerprint"]
    )
    assert history["benchmark_id"] == artifact["run_id"]
    assert history["candidate_decision"] == artifact["candidate_decision"]
    assert history["provider_requests"] == artifact["provider_request_count"]
    assert "Decision: `REJECT`" in report
