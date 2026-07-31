"""Execute the frozen Part 7H.4 H3 experiment and predictive validation."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from scripts.design_knowledge_guided_h3 import (
    DESIGN_PATH,
    RISK_PATH,
    TRACE_PATH,
    _sha,
    h3_prompt,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    PRICING_PATH,
    _transform_request,
    build_experiment_artifact,
    dry_run,
    prompt_projection_checkpoint,
)
from scripts.run_controlled_provider_quality_baseline import (
    execute_trial,
    write_artifact_atomic,
)

OPT_IN = "SCOUT_RUN_LIVE_PROMPT_EXPERIMENT_7H4"
EXPERIMENT_PATH = Path("docs/artifacts/h3-experiment.json")
PREDICTION_PATH = Path("docs/artifacts/prediction-validation.json")
METRICS_PATH = Path("docs/artifacts/prediction-metrics.json")
KNOWLEDGE_VALIDATION_PATH = Path("docs/artifacts/knowledge-validation.json")
REPORT_PATH = Path("docs/controlled-h3-experiment.md")


def precision_recall_f1(predicted: set[str], observed: set[str]) -> dict[str, float]:
    """Compute deterministic set precision, recall, and F1."""

    overlap = len(predicted & observed)
    precision = (
        overlap / len(predicted) if predicted else (1.0 if not observed else 0.0)
    )
    recall = overlap / len(observed) if observed else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def prediction_accuracy(predicted: int, observed: int) -> float:
    """Normalize absolute utility error to 0–100."""

    scale = max(abs(predicted), abs(observed), 1)
    return max(0.0, 100.0 * (1.0 - abs(predicted - observed) / scale))


def confidence_calibration(confidence: str, prompt_outcome: str) -> str:
    """Classify the precommitted confidence against observed prompt outcome."""

    if confidence == "LOW":
        return "UNDERCONFIDENT" if prompt_outcome == "EFFECTIVE" else "WELL_CALIBRATED"
    if confidence == "HIGH":
        return "WELL_CALIBRATED" if prompt_outcome == "EFFECTIVE" else "OVERCONFIDENT"
    return (
        "WELL_CALIBRATED"
        if prompt_outcome == "PARTIALLY_EFFECTIVE"
        else ("UNDERCONFIDENT" if prompt_outcome == "EFFECTIVE" else "OVERCONFIDENT")
    )


def predictive_quality_score(
    utility_accuracy: float,
    scenario_f1: float,
    failure_f1: float,
    risk_accuracy: str,
    calibration: str,
) -> float:
    """Average five equally weighted normalized predictive dimensions."""

    risk_score = {"ACCURATE": 100.0, "PARTIALLY_ACCURATE": 50.0, "INACCURATE": 0.0}[
        risk_accuracy
    ]
    calibration_score = {
        "WELL_CALIBRATED": 100.0,
        "UNDERCONFIDENT": 75.0,
        "OVERCONFIDENT": 25.0,
    }[calibration]
    return (
        utility_accuracy
        + 100 * scenario_f1
        + 100 * failure_f1
        + risk_score
        + calibration_score
    ) / 5


def load_frozen_h3() -> tuple[dict, dict, dict, dict]:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    risk = json.loads(RISK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(
        Path(
            "docs/artifacts/controlled-prompt-effectiveness-experiment-design.json"
        ).read_text(encoding="utf-8")
    )
    if (
        not design["h3_ready_for_future_controlled_experiment"]
        or design["h3_prompt"] != h3_prompt()
        or design["h3_prompt_fingerprint"] != _sha(h3_prompt())
        or design["prompt_delta_budget"]["validation_status"] != "PASS"
        or trace["validation_status"] != "PASS"
        or trace["orphan_prompt_changes"] != 0
        or risk["validation_status"] != "PASS"
    ):
        raise RuntimeError("frozen H3 design mismatch")
    harness = {
        **h1,
        "candidate_prompt": design["h3_prompt"],
        "candidate_prompt_fingerprint": design["h3_prompt_fingerprint"],
        "prompt_diff": design["prompt_diff"],
        "prompt_diff_fingerprint": design["prompt_diff_fingerprint"],
    }
    return design, trace, risk, harness


def preflight() -> tuple[dict, dict, dict, tuple, tuple]:
    design, trace, risk, harness = load_frozen_h3()
    corpus = tuple(build_synthetic_corpus())
    checkpoints = dry_run(harness, corpus)
    if len(checkpoints) != 24 or not all(
        item["prompt_identity"] and item["count_equality"] and item["set_equality"]
        for item in checkpoints
    ):
        raise RuntimeError("offline H3 request assembly failed")
    if any(
        path.exists()
        for path in (
            EXPERIMENT_PATH,
            PREDICTION_PATH,
            METRICS_PATH,
            KNOWLEDGE_VALIDATION_PATH,
            REPORT_PATH,
        )
    ):
        raise RuntimeError("H3 experiment artifacts already exist")
    return design, trace, risk, corpus, checkpoints


def build_h3_results(
    run_id: str,
    created_at: str,
    design: dict,
    risk: dict,
    harness: dict,
    results: tuple,
    checkpoints: tuple,
) -> tuple[dict, dict, dict, dict]:
    """Aggregate experiment and prediction outcomes from frozen paired evidence."""

    base, _ = build_experiment_artifact(
        run_id, created_at, harness, results, checkpoints
    )
    pairs = base["paired_scenario_results"]
    resolved = 0
    introduced = 0
    observed_scenarios: set[str] = set()
    observed_failures: set[str] = set()
    scenario_transitions = []
    for pair in pairs:
        control = set(pair["secondary_failure_categories_control"])
        treatment = set(pair["secondary_failure_categories_treatment"])
        removed = sorted(control - treatment)
        added = sorted(treatment - control)
        resolved += len(removed)
        introduced += len(added)
        if removed or added:
            observed_scenarios.add(pair["scenario_id"])
        observed_failures.update(removed)
        observed_failures.update(added)
        scenario_transitions.append(
            {
                "scenario_id": pair["scenario_id"],
                "removed_failures": removed,
                "introduced_failures": added,
                "unchanged_failures": sorted(control & treatment),
                "score_delta": pair["editorial_score_delta"],
                "acceptance_transition": pair["acceptance_transition"],
            }
        )
    observed_utility = resolved - introduced
    predicted_utility = risk["expected_net_editorial_utility"]
    predicted_scenarios = set(risk["expected_affected_scenarios"])
    predicted_failures = {
        "quote_preservation",
        "editorial_acceptance",
        "instruction_compliance",
        "meaning_preservation",
        "source_authority_preservation",
    }
    scenario_metrics = precision_recall_f1(predicted_scenarios, observed_scenarios)
    failure_metrics = precision_recall_f1(predicted_failures, observed_failures)
    regression_observed = (
        introduced > 0 or base["editorial_metrics"]["pass_to_fail"] > 0
    )
    interaction_observed = resolved > 0 and introduced > 0
    risk_accuracy = (
        "ACCURATE"
        if risk["regression_risk"] == "MEDIUM"
        and risk["interaction_risk"] == "MEDIUM"
        and regression_observed
        and interaction_observed
        else (
            "PARTIALLY_ACCURATE"
            if regression_observed or interaction_observed
            else "INACCURATE"
        )
    )
    control_editorial = base["control_metrics"]["editorial_metrics"]
    treatment_editorial = base["editorial_metrics"]
    technical = base["technical_non_regression"]
    reference = base["reference_non_regression"]
    if (
        technical
        and reference
        and treatment_editorial["acceptance_passes"]
        > control_editorial["acceptance_passes"]
        and observed_utility > 0
    ):
        prompt_outcome, prompt_conclusion, decision = (
            "EFFECTIVE",
            "H3_PROMPT_EFFECTIVE",
            "ADOPT",
        )
    elif technical and reference and observed_utility > 0:
        prompt_outcome, prompt_conclusion, decision = (
            "PARTIALLY_EFFECTIVE",
            "H3_PROMPT_PARTIALLY_EFFECTIVE",
            "REJECT",
        )
    else:
        prompt_outcome, prompt_conclusion, decision = (
            "INEFFECTIVE",
            "H3_PROMPT_INEFFECTIVE",
            "REJECT",
        )
    calibration = confidence_calibration(risk["confidence"], prompt_outcome)
    utility_accuracy = prediction_accuracy(predicted_utility, observed_utility)
    composite = predictive_quality_score(
        utility_accuracy,
        scenario_metrics["f1"],
        failure_metrics["f1"],
        risk_accuracy,
        calibration,
    )
    prediction_outcome = (
        "H3_PREDICTION_VALIDATED"
        if composite >= 80
        else (
            "H3_PREDICTION_PARTIALLY_VALIDATED"
            if composite >= 50
            else "H3_PREDICTION_INVALIDATED"
        )
    )
    causal = (
        "CONFIRMED"
        if observed_utility == predicted_utility
        and observed_scenarios == predicted_scenarios
        else (
            "PARTIALLY_CONFIRMED"
            if observed_utility > 0 or observed_scenarios & predicted_scenarios
            else "NOT_CONFIRMED"
        )
    )
    knowledge_status = (
        "SUPPORTED"
        if causal == "CONFIRMED"
        else "REFINED" if causal == "PARTIALLY_CONFIRMED" else "INVALIDATED"
    )
    prediction = {
        "schema_version": 1,
        "experiment_id": run_id,
        "predicted_net_editorial_utility": predicted_utility,
        "observed_net_editorial_utility": observed_utility,
        "prediction_error": observed_utility - predicted_utility,
        "predicted_affected_scenarios": sorted(predicted_scenarios),
        "observed_affected_scenarios": sorted(observed_scenarios),
        "scenario_metrics": scenario_metrics,
        "predicted_failure_categories": sorted(predicted_failures),
        "observed_failure_categories": sorted(observed_failures),
        "failure_metrics": failure_metrics,
        "risk_validation": {
            "predicted_regression_risk": risk["regression_risk"],
            "observed_regression": regression_observed,
            "predicted_interaction_risk": risk["interaction_risk"],
            "observed_interaction": interaction_observed,
            "classification": risk_accuracy,
        },
        "predicted_confidence": risk["confidence"],
        "confidence_calibration": calibration,
        "causal_mechanism": causal,
        "predictive_quality_score": composite,
        "prediction_root_conclusion": prediction_outcome,
    }
    metrics = {
        "schema_version": 1,
        "experiment_id": run_id,
        "utility_accuracy": utility_accuracy,
        "scenario_precision": scenario_metrics["precision"],
        "scenario_recall": scenario_metrics["recall"],
        "scenario_f1": scenario_metrics["f1"],
        "failure_precision": failure_metrics["precision"],
        "failure_recall": failure_metrics["recall"],
        "failure_f1": failure_metrics["f1"],
        "risk_prediction": risk_accuracy,
        "confidence_calibration": calibration,
        "predictive_quality_score": composite,
        "weighting": "five equal 20% dimensions",
    }
    knowledge = {
        "schema_version": 1,
        "experiment_id": run_id,
        "knowledge_entry_id": "EK-002",
        "prior_status": "ACTIVE",
        "validation_outcome": knowledge_status,
        "causal_mechanism": causal,
        "evidence": {
            "observed_net_editorial_utility": observed_utility,
            "observed_affected_scenarios": sorted(observed_scenarios),
            "scenario_transitions": scenario_transitions,
        },
        "knowledge_base_update_required": True,
        "update_strategy": "append a new immutable experiment finding; retain EK-002",
    }
    base.update(
        {
            "milestone": "Part 7H.4 — Controlled Knowledge-Guided Prompt Experiment",
            "experiment_id": run_id,
            "h3_prompt_fingerprint": design["h3_prompt_fingerprint"],
            "knowledge_base_fingerprint": design["knowledge_base_fingerprint"],
            "knowledge_traceability": "PASS",
            "prompt_delta_budget": design["prompt_delta_budget"],
            "net_editorial_utility": {
                "resolved_failures": resolved,
                "introduced_failures": introduced,
                "value": observed_utility,
            },
            "scenario_transitions": scenario_transitions,
            "prompt_outcome": prompt_outcome,
            "candidate_decision": decision,
            "prompt_root_conclusion": prompt_conclusion,
            "prediction_root_conclusion": prediction_outcome,
            "production_promotion": False,
            "production_promotion_recommended": decision == "ADOPT",
            "production_prompt_modified": False,
        }
    )
    return base, prediction, metrics, knowledge


def _report(experiment: dict, prediction: dict, knowledge: dict) -> str:
    return f"""# Controlled H3 Experiment

H3 completed 24 controlled scenarios with {experiment['provider_request_count']} requests,
{experiment['provider_response_count']} responses, and zero retries, fallbacks, or replays.

Technical non-regression: `{experiment['technical_non_regression']}`. Reference
non-regression: `{experiment['reference_non_regression']}`. Editorial acceptance:
{experiment['editorial_metrics']['acceptance_passes']}/24. Net Editorial Utility:
{experiment['net_editorial_utility']['value']}.

Prompt outcome: `{experiment['prompt_root_conclusion']}`; candidate decision:
`{experiment['candidate_decision']}`; production prompt modified: `NO`.

Prediction expected utility {prediction['predicted_net_editorial_utility']} and observed
{prediction['observed_net_editorial_utility']}, error {prediction['prediction_error']}.
Scenario F1: {prediction['scenario_metrics']['f1']}; failure F1:
{prediction['failure_metrics']['f1']}; predictive quality:
{prediction['predictive_quality_score']}. Prediction conclusion:
`{prediction['prediction_root_conclusion']}`.

Knowledge `EK-002`: `{knowledge['validation_outcome']}`. Causal mechanism:
`{knowledge['causal_mechanism']}`. The knowledge base is updated through a new immutable
finding; EK-002 remains traceable.
"""


def preflight_harness() -> tuple[dict, dict, dict, dict, tuple, tuple]:
    design, trace, risk, harness = load_frozen_h3()
    corpus = tuple(build_synthetic_corpus())
    checkpoints = dry_run(harness, corpus)
    if len(checkpoints) != 24 or not all(
        item["prompt_identity"] and item["count_equality"] and item["set_equality"]
        for item in checkpoints
    ):
        raise RuntimeError("H3 preflight failed")
    if any(
        path.exists()
        for path in (
            EXPERIMENT_PATH,
            PREDICTION_PATH,
            METRICS_PATH,
            KNOWLEDGE_VALIDATION_PATH,
            REPORT_PATH,
        )
    ):
        raise RuntimeError("H3 artifacts already exist")
    return design, trace, risk, harness, corpus, checkpoints


def main() -> int:
    try:
        design, trace, risk, harness, corpus, offline = preflight_harness()
    except Exception as error:  # noqa: BLE001
        print(f"EXPERIMENT_ABORTED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    del trace
    print(f"Offline assembly: {len(offline)}/24; provider requests: 0")
    if os.environ.get(OPT_IN) != "1":
        print(f"Live experiment disabled; set {OPT_IN}=1 for exactly 24 requests.")
        return 0
    if resolve_openai_api_key() is None:
        print("EXPERIMENT_ABORTED: credential unavailable", file=sys.stderr)
        return 2
    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini-7h4")
    pricing = load_benchmark_pricing(PRICING_PATH)
    results = []
    checkpoints = []
    for scenario in corpus:
        record: dict = {}

        def transform(invocation, request, *, prompt=design["h3_prompt"]):
            return _transform_request(invocation, request, prompt)

        def gate(
            invocation, request, *, sink=record, scenario_id=scenario.scenario_key
        ):
            sink.update(
                prompt_projection_checkpoint(scenario_id, invocation, request, harness)
            )

        result = execute_trial(
            scenario,
            pricing,
            request_transformer=transform,
            pre_request_validator=gate,
        )
        if not record or not all(
            record.get(key)
            for key in ("prompt_identity", "count_equality", "set_equality")
        ):
            print(f"EXPERIMENT_ABORTED: {scenario.scenario_key} gate", file=sys.stderr)
            return 2
        results.append(result)
        checkpoints.append(record)
        print(f"{scenario.scenario_key}: {result.outcome.value}")
    experiment, prediction, metrics, knowledge = build_h3_results(
        run_id,
        now.isoformat(),
        design,
        risk,
        harness,
        tuple(results),
        tuple(checkpoints),
    )
    for path, artifact in (
        (EXPERIMENT_PATH, experiment),
        (PREDICTION_PATH, prediction),
        (METRICS_PATH, metrics),
        (KNOWLEDGE_VALIDATION_PATH, knowledge),
    ):
        write_artifact_atomic(path, artifact)
    REPORT_PATH.write_text(
        _report(experiment, prediction, knowledge), encoding="utf-8", newline="\n"
    )
    print(f"Experiment: {run_id}")
    print(f"Prompt: {experiment['prompt_root_conclusion']}")
    print(f"Prediction: {prediction['prediction_root_conclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
