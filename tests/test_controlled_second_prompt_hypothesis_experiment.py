"""Offline Part 7H.2 budget, pairing, gate, and artifact tests."""

from __future__ import annotations

import json

from test_controlled_provider_quality_baseline_v2 import _result

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from scripts.run_controlled_prompt_effectiveness_experiment import dry_run
from scripts.run_controlled_second_prompt_hypothesis_experiment import (
    ARTIFACT_PATH,
    BUDGET_PATH,
    COMPARISON_PATH,
    REPORT_PATH,
    _failure_transition,
    _quote_transition,
    build_h2_artifacts,
    load_frozen_design,
    prompt_delta_budget,
)


def _built(*, failing: int | None = None):
    h2, harness = load_frozen_design()
    budget = prompt_delta_budget(h2)
    checkpoints = dry_run(harness, build_synthetic_corpus())
    results = tuple(
        _result(number, success=number != failing) for number in range(1, 25)
    )
    return build_h2_artifacts(
        "20260728-150000-openai-gpt-4.1-mini-7h2",
        "2026-07-28T15:00:00+00:00",
        harness,
        budget,
        results,
        checkpoints,
    )


def test_prompt_delta_budget_consumes_exactly_one_mechanism():
    h2, _ = load_frozen_design()
    budget = prompt_delta_budget(h2)

    assert budget["validation_result"] == "PASS"
    assert budget["budget_limit"] == budget["budget_consumed"] == 1
    assert budget["independent_behavioral_mechanisms"] == 1
    assert budget["undocumented_semantic_changes"] == 0
    assert budget["budget_exceeded"] is False


def test_frozen_h2_identity_matches_all_offline_requests():
    _, harness = load_frozen_design()
    checkpoints = dry_run(harness, build_synthetic_corpus())

    assert len(checkpoints) == 24
    assert all(item["prompt_identity"] for item in checkpoints)
    assert all(item["count_equality"] for item in checkpoints)
    assert all(item["set_equality"] for item in checkpoints)


def test_scenario_pairing_is_complete_and_deterministic():
    artifact, _, comparison, _ = _built()

    assert comparison["scenario_count"] == 24
    assert [item["scenario_id"] for item in comparison["scenarios"]] == [
        f"SYN-{number:02d}" for number in range(1, 25)
    ]
    assert artifact["provider_request_count"] == 24


def test_acceptance_transitions_are_classified_for_every_pair():
    artifact, _, _, _ = _built()

    assert sum(artifact["acceptance_transitions"].values()) == 24
    assert set(artifact["acceptance_transitions"]) <= {
        "FAIL_TO_PASS",
        "FAIL_TO_FAIL",
        "PASS_TO_PASS",
        "PASS_TO_FAIL",
        "NOT_COMPARABLE",
    }


def test_failure_transition_classification():
    assert (
        _failure_transition(
            {
                "primary_failure_category_control": "QUOTE_MUTATION",
                "primary_failure_category_treatment": None,
                "technical_pipeline_success_treatment": True,
            }
        )
        == "RESOLVED"
    )
    assert (
        _failure_transition(
            {
                "primary_failure_category_control": None,
                "primary_failure_category_treatment": "SOURCE_AUTHORITY_DRIFT",
                "technical_pipeline_success_treatment": True,
            }
        )
        == "NEW_FAILURE"
    )


def test_quote_mutation_transition_classification():
    assert (
        _quote_transition(
            {
                "primary_failure_category_control": "QUOTE_MUTATION",
                "primary_failure_category_treatment": None,
                "technical_pipeline_success_treatment": True,
            }
        )
        == "RESOLVED"
    )
    assert (
        _quote_transition(
            {
                "primary_failure_category_control": None,
                "primary_failure_category_treatment": "QUOTE_MUTATION",
                "technical_pipeline_success_treatment": True,
            }
        )
        == "NEW_CASE"
    )


def test_quote_mutation_metrics_reconcile_with_scenarios():
    artifact, _, comparison, _ = _built()
    transitions = [
        item["quote_mutation_transition"] for item in comparison["scenarios"]
    ]

    assert artifact["quote_mutation_metrics"]["resolved_cases"] == transitions.count(
        "RESOLVED"
    )
    assert artifact["quote_mutation_metrics"]["new_cases"] == transitions.count(
        "NEW_CASE"
    )


def test_technical_regression_forces_rejection():
    artifact, _, _, _ = _built(failing=1)

    assert artifact["technical_non_regression"] is False
    assert artifact["candidate_decision"] == "REJECT"
    assert artifact["root_conclusion"] == "H2_FAILED_TECHNICAL_NON_REGRESSION"


def test_reference_and_technical_gates_pass_for_valid_results():
    artifact, _, _, _ = _built()

    assert artifact["technical_non_regression"] is True
    assert artifact["reference_non_regression"] is True
    assert artifact["experiment_integrity"] is True


def test_provider_comparability_metadata_is_recorded():
    artifact, _, _, _ = _built()
    comparability = artifact["provider_comparability"]

    assert comparability["classification"] == "COMPARABLE"
    assert comparability["provider"] == "openai"
    assert comparability["model"] == "gpt-4.1-mini"
    assert comparability["provider_configuration_fingerprint"]


def test_production_prompt_is_never_marked_modified_by_experiment():
    artifact, _, _, _ = _built()

    assert artifact["production_prompt_modified"] is False
    assert (
        artifact["control_prompt_fingerprint"]
        != artifact["candidate_prompt_fingerprint"]
    )


def test_artifact_counters_are_internally_consistent():
    artifact, _, comparison, _ = _built()

    trials = artifact["trials"]
    successes = sum(
        item["operational_outcome"] == "PIPELINE_SUCCESS" for item in trials
    )
    exact = sum(
        item["exact_reference_compliance_treatment"] for item in comparison["scenarios"]
    )
    assert successes == artifact["pipeline_funnel"]["technical_pipeline_successes"]
    assert exact == artifact["reference_metrics"]["exact_authorized_scenarios"]
    assert len(trials) == comparison["scenario_count"] == 24


def test_checked_in_experiment_artifacts_parse_and_match():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    budget = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    comparison = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == comparison["experiment_id"]
    assert artifact["prompt_delta_budget"] == budget
    assert comparison["scenario_count"] == len(comparison["scenarios"]) == 24
    assert artifact["provider_request_count"] == 24
    assert artifact["provider_response_count"] == 24


def test_checked_in_metrics_reconcile_to_scenario_evidence():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    comparison = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))
    scenarios = comparison["scenarios"]

    assert sum(item["technical_pipeline_success_treatment"] for item in scenarios) == 24
    assert sum(item["exact_reference_compliance_treatment"] for item in scenarios) == 24
    assert (
        sum(item["quote_mutation_transition"] == "RESOLVED" for item in scenarios) == 2
    )
    assert artifact["quote_mutation_metrics"] == {
        "control_frequency": 2,
        "treatment_frequency": 0,
        "resolved_cases": 2,
        "persisting_cases": 0,
        "new_cases": 0,
        "net_reduction": 2,
    }


def test_checked_in_report_matches_decision_and_keeps_production_frozen():
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert artifact["candidate_decision"] == "REJECT"
    assert artifact["root_conclusion"] == "H2_PROMPT_INEFFECTIVE"
    assert artifact["production_promotion"] is False
    assert artifact["production_prompt_modified"] is False
    assert "`REJECT`" in report
    assert "`H2_PROMPT_INEFFECTIVE`" in report
