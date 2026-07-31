"""Offline Part 7H.4 predictive metric and experiment aggregation tests."""

from __future__ import annotations

import json

from test_controlled_provider_quality_baseline_v2 import _result

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from scripts.run_controlled_h3_experiment import (
    EXPERIMENT_PATH,
    KNOWLEDGE_VALIDATION_PATH,
    METRICS_PATH,
    PREDICTION_PATH,
    REPORT_PATH,
    build_h3_results,
    confidence_calibration,
    load_frozen_h3,
    precision_recall_f1,
    prediction_accuracy,
    predictive_quality_score,
)
from scripts.run_controlled_prompt_effectiveness_experiment import dry_run


def _built(*, failing: int | None = None):
    design, _, risk, harness = load_frozen_h3()
    checkpoints = dry_run(harness, build_synthetic_corpus())
    results = tuple(
        _result(number, success=number != failing) for number in range(1, 25)
    )
    return build_h3_results(
        "20260728-160000-openai-gpt-4.1-mini-7h4",
        "2026-07-28T16:00:00+00:00",
        design,
        risk,
        harness,
        results,
        checkpoints,
    )


def test_prediction_error_accuracy_is_bounded():
    assert prediction_accuracy(2, 2) == 100
    assert prediction_accuracy(2, 0) == 0
    assert prediction_accuracy(2, 1) == 50
    assert prediction_accuracy(0, 0) == 100


def test_scenario_precision_recall_and_f1():
    metrics = precision_recall_f1({"A", "B", "C"}, {"B", "C", "D"})

    assert metrics["precision"] == 2 / 3
    assert metrics["recall"] == 2 / 3
    assert metrics["f1"] == 2 / 3


def test_failure_precision_handles_empty_sets():
    assert precision_recall_f1(set(), set()) == {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert precision_recall_f1(set(), {"failure"})["f1"] == 0


def test_composite_predictive_score_uses_five_equal_dimensions():
    assert predictive_quality_score(100, 1, 1, "ACCURATE", "WELL_CALIBRATED") == 100
    assert predictive_quality_score(0, 0, 0, "INACCURATE", "OVERCONFIDENT") == 5


def test_confidence_calibration_for_low_confidence_prediction():
    assert confidence_calibration("LOW", "EFFECTIVE") == "UNDERCONFIDENT"
    assert confidence_calibration("LOW", "PARTIALLY_EFFECTIVE") == "WELL_CALIBRATED"
    assert confidence_calibration("LOW", "INEFFECTIVE") == "WELL_CALIBRATED"


def test_frozen_h3_traceability_and_offline_identity_pass():
    design, trace, risk, harness = load_frozen_h3()
    checkpoints = dry_run(harness, build_synthetic_corpus())

    assert design["h3_ready_for_future_controlled_experiment"]
    assert trace["orphan_prompt_changes"] == 0
    assert risk["validation_status"] == "PASS"
    assert len(checkpoints) == 24
    assert all(item["prompt_identity"] and item["set_equality"] for item in checkpoints)


def test_valid_technical_results_preserve_frozen_contracts():
    experiment, _, _, _ = _built()

    assert experiment["technical_non_regression"] is True
    assert experiment["reference_non_regression"] is True
    assert experiment["pipeline_funnel"]["technical_pipeline_successes"] == 24
    assert experiment["reference_metrics"]["exact_authorized_scenarios"] == 24


def test_technical_failure_prevents_prompt_adoption():
    experiment, _, _, _ = _built(failing=1)

    assert experiment["technical_non_regression"] is False
    assert experiment["candidate_decision"] == "REJECT"
    assert experiment["production_promotion"] is False


def test_prediction_and_metrics_artifacts_are_consistent():
    _, prediction, metrics, knowledge = _built()

    assert prediction["predictive_quality_score"] == metrics["predictive_quality_score"]
    assert prediction["scenario_metrics"]["precision"] == metrics["scenario_precision"]
    assert prediction["failure_metrics"]["recall"] == metrics["failure_recall"]
    assert knowledge["knowledge_entry_id"] == "EK-002"
    assert knowledge["knowledge_base_update_required"] is True


def test_knowledge_transition_vocabulary_and_causal_classification():
    _, prediction, _, knowledge = _built()

    assert knowledge["validation_outcome"] in {
        "SUPPORTED",
        "REFINED",
        "SUPERSEDED",
        "INVALIDATED",
    }
    assert prediction["causal_mechanism"] in {
        "CONFIRMED",
        "PARTIALLY_CONFIRMED",
        "NOT_CONFIRMED",
    }


def test_checked_in_h3_artifacts_are_internally_consistent():
    experiment = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
    prediction = json.loads(PREDICTION_PATH.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    knowledge = json.loads(KNOWLEDGE_VALIDATION_PATH.read_text(encoding="utf-8"))

    assert (
        experiment["provider_request_count"]
        == experiment["provider_response_count"]
        == 24
    )
    assert (
        experiment["retry_count"]
        == experiment["fallback_count"]
        == experiment["replay_count"]
        == 0
    )
    assert experiment["net_editorial_utility"] == {
        "resolved_failures": 13,
        "introduced_failures": 5,
        "value": 8,
    }
    assert (
        prediction["predictive_quality_score"]
        == metrics["predictive_quality_score"]
        == 75
    )
    assert knowledge["validation_outcome"] == "REFINED"


def test_checked_in_h3_decisions_preserve_explicit_promotion_boundary():
    experiment = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
    prediction = json.loads(PREDICTION_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert experiment["candidate_decision"] == "ADOPT"
    assert experiment["prompt_root_conclusion"] == "H3_PROMPT_EFFECTIVE"
    assert experiment["production_promotion"] is False
    assert experiment["production_promotion_recommended"] is True
    assert experiment["production_prompt_modified"] is False
    assert (
        prediction["prediction_root_conclusion"] == "H3_PREDICTION_PARTIALLY_VALIDATED"
    )
    assert "H3_PROMPT_EFFECTIVE" in report
