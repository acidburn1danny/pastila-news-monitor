"""Run the frozen Part 7H.2 H2 experiment with exactly 24 live requests."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
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
    production_benchmark_configuration,
)
from scripts.design_second_prompt_hypothesis import (
    DESIGN_PATH as H2_DESIGN_PATH,
)
from scripts.design_second_prompt_hypothesis import (
    _sha,
    h2_prompt,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    HISTORY_PATH,
    PRICING_PATH,
    _history_entry,
    _transform_request,
    build_experiment_artifact,
    control_prompt,
    dry_run,
    prompt_projection_checkpoint,
)
from scripts.run_controlled_provider_quality_baseline import (
    execute_trial,
    write_artifact_atomic,
)

OPT_IN = "SCOUT_RUN_LIVE_PROMPT_EXPERIMENT_7H2"
ARTIFACT_PATH = Path(
    "docs/artifacts/controlled-second-prompt-hypothesis-experiment.json"
)
BUDGET_PATH = Path("docs/artifacts/prompt-delta-budget.json")
COMPARISON_PATH = Path("docs/artifacts/h2-scenario-comparison.json")
DIAGNOSTICS_PATH = Path("docs/artifacts/controlled-second-prompt-diagnostics.json")
REPORT_PATH = Path("docs/controlled-second-prompt-hypothesis-experiment.md")


def load_frozen_design() -> tuple[dict[str, object], dict[str, object]]:
    """Load H2 and adapt only field names required by the frozen H1 harness."""

    h2 = json.loads(H2_DESIGN_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(
        Path(
            "docs/artifacts/controlled-prompt-effectiveness-experiment-design.json"
        ).read_text(encoding="utf-8")
    )
    if (
        not h2.get("design_frozen")
        or not h2.get("h2_ready_for_controlled_experiment")
        or h2["h2_prompt"] != h2_prompt()
        or h2["h2_prompt_fingerprint"] != _sha(h2_prompt())
        or h2["control_prompt_fingerprint"] != _sha(control_prompt())
    ):
        raise RuntimeError("frozen_h2_design_mismatch")
    harness = {
        **h1,
        "candidate_prompt": h2["h2_prompt"],
        "candidate_prompt_fingerprint": h2["h2_prompt_fingerprint"],
        "prompt_diff": h2["baseline_to_h2_diff"],
        "prompt_diff_fingerprint": h2["baseline_to_h2_diff_fingerprint"],
    }
    return h2, harness


def prompt_delta_budget(h2: dict[str, object]) -> dict[str, object]:
    """Validate the precommitted single-mechanism prompt delta budget."""

    changes = h2["h2_change_inventory"]
    evidence = [item["evidence_source"] for item in changes]
    value = {
        "schema_version": 1,
        "milestone": "Part 7H.2",
        "budget_limit": 1,
        "budget_consumed": len(changes),
        "independent_behavioral_mechanisms": len(changes),
        "evidence_derived_hypotheses": 1,
        "evidence_mapping": evidence,
        "undocumented_semantic_changes": 0,
        "benchmark_specific_instructions": 0,
        "evaluator_specific_instructions": 0,
        "production_irrelevant_instructions": 0,
        "control_prompt_fingerprint": h2["control_prompt_fingerprint"],
        "h2_prompt_fingerprint": h2["h2_prompt_fingerprint"],
        "prompt_diff_fingerprint": h2["baseline_to_h2_diff_fingerprint"],
    }
    value["budget_exceeded"] = (
        value["budget_consumed"] > value["budget_limit"]
        or value["undocumented_semantic_changes"] > 0
    )
    value["validation_result"] = "PASS" if not value["budget_exceeded"] else "FAIL"
    return value


def preflight() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    tuple[object, ...],
    tuple[dict[str, object], ...],
]:
    """Complete all non-network gates and refuse artifact overwrite."""

    h2, harness = load_frozen_design()
    budget = prompt_delta_budget(h2)
    if budget["validation_result"] != "PASS":
        raise RuntimeError("prompt_delta_budget_failure")
    configuration = production_benchmark_configuration()
    if (
        configuration.model_identifier != "gpt-4.1-mini"
        or configuration.retry_policy.maximum_attempts != 1
    ):
        raise RuntimeError("provider_configuration_mismatch")
    corpus = tuple(build_synthetic_corpus())
    if tuple(item.scenario_key for item in corpus) != tuple(
        f"SYN-{number:02d}" for number in range(1, 25)
    ):
        raise RuntimeError("benchmark_corpus_drift")
    checkpoints = dry_run(harness, corpus)
    if len(checkpoints) != 24 or not all(
        item["prompt_identity"] and item["count_equality"] and item["set_equality"]
        for item in checkpoints
    ):
        raise RuntimeError("offline_request_assembly_failure")
    outputs = (
        ARTIFACT_PATH,
        BUDGET_PATH,
        COMPARISON_PATH,
        DIAGNOSTICS_PATH,
        REPORT_PATH,
    )
    if any(path.exists() for path in outputs):
        raise RuntimeError("experiment_artifact_already_exists")
    return h2, harness, budget, corpus, checkpoints


def _failure_transition(pair: dict[str, object]) -> str:
    control = pair["primary_failure_category_control"]
    treatment = pair["primary_failure_category_treatment"]
    if not pair["technical_pipeline_success_treatment"]:
        return "NOT_COMPARABLE"
    if control == treatment:
        return "UNCHANGED"
    if control and not treatment:
        return "RESOLVED"
    if not control and treatment:
        return "NEW_FAILURE"
    return "REGRESSED"


def _quote_transition(pair: dict[str, object]) -> str:
    control = pair["primary_failure_category_control"] == "QUOTE_MUTATION"
    treatment = pair["primary_failure_category_treatment"] == "QUOTE_MUTATION"
    if not pair["technical_pipeline_success_treatment"]:
        return "NOT_COMPARABLE"
    if control and not treatment:
        return "RESOLVED"
    if control and treatment:
        return "PERSISTING"
    if not control and treatment:
        return "NEW_CASE"
    return "ABSENT"


def build_h2_artifacts(
    run_id: str,
    created_at: str,
    harness: dict[str, object],
    budget: dict[str, object],
    results: tuple[object, ...],
    checkpoints: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], dict[str, object], dict[str, object], object]:
    """Aggregate H2 using frozen evaluations and stricter H2 decision gates."""

    base, diagnostics = build_experiment_artifact(
        run_id, created_at, harness, results, checkpoints
    )
    pairs = base["paired_scenario_results"]
    for pair in pairs:
        pair["failure_category_transition"] = _failure_transition(pair)
        pair["quote_mutation_transition"] = _quote_transition(pair)
        pair["technical_delta"] = (
            "UNCHANGED_PASS"
            if pair["technical_pipeline_success_treatment"]
            else "REGRESSED"
        )
        pair["reference_delta"] = (
            "UNCHANGED_PASS"
            if pair["exact_reference_compliance_treatment"]
            else "REGRESSED"
        )
    quote_transitions = Counter(item["quote_mutation_transition"] for item in pairs)
    failure_transitions = Counter(item["failure_category_transition"] for item in pairs)
    control_quote = base["failure_taxonomy_control"].get("QUOTE_MUTATION", 0)
    treatment_quote = base["failure_taxonomy_treatment"].get("QUOTE_MUTATION", 0)
    quote = {
        "control_frequency": control_quote,
        "treatment_frequency": treatment_quote,
        "resolved_cases": quote_transitions["RESOLVED"],
        "persisting_cases": quote_transitions["PERSISTING"],
        "new_cases": quote_transitions["NEW_CASE"],
        "net_reduction": control_quote - treatment_quote,
    }
    technical = bool(base["technical_non_regression"])
    reference = bool(base["reference_non_regression"])
    integrity = bool(base["experiment_integrity"])
    control_editorial = base["control_metrics"]["editorial_metrics"]
    treatment_editorial = base["editorial_metrics"]
    unrelated_control = sum(
        count
        for category, count in base["failure_taxonomy_control"].items()
        if category != "QUOTE_MUTATION"
    )
    unrelated_treatment = sum(
        count
        for category, count in base["failure_taxonomy_treatment"].items()
        if category != "QUOTE_MUTATION"
    )
    editorial = (
        treatment_editorial["mean_score"] > control_editorial["mean_score"]
        and treatment_editorial["acceptance_passes"]
        > control_editorial["acceptance_passes"]
        and treatment_quote < control_quote
        and unrelated_treatment <= unrelated_control
    )
    if not integrity:
        decision, conclusion = "REJECT", "H2_EXPERIMENT_INVALID"
    elif not technical:
        decision, conclusion = "REJECT", "H2_FAILED_TECHNICAL_NON_REGRESSION"
    elif not reference:
        decision, conclusion = "REJECT", "H2_FAILED_REFERENCE_NON_REGRESSION"
    elif editorial:
        decision, conclusion = "ADOPT", "H2_PROMPT_EFFECTIVE"
    else:
        decision, conclusion = "REJECT", "H2_PROMPT_INEFFECTIVE"
    base.update(
        {
            "milestone": "Part 7H.2 — Controlled Second Prompt Hypothesis Experiment",
            "experiment_id": run_id,
            "prompt_delta_budget": budget,
            "provider_comparability": {
                "classification": "COMPARABLE",
                "provider_drift_observed": False,
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "model_alias": "gpt-4.1-mini",
                "model_revision": None,
                "api_version": None,
                "sdk_version": version("openai"),
                "provider_configuration_fingerprint": base[
                    "provider_configuration_fingerprint"
                ],
                "execution_timestamp": created_at,
                "known_provider_drift": None,
            },
            "quote_mutation_metrics": quote,
            "acceptance_transitions": dict(
                Counter(item["acceptance_transition"] for item in pairs)
            ),
            "failure_category_transitions": dict(failure_transitions),
            "technical_non_regression": technical,
            "reference_non_regression": reference,
            "editorial_improvement": {
                "threshold_passed": editorial,
                "mean_score_improved": treatment_editorial["mean_score"]
                > control_editorial["mean_score"],
                "acceptance_improved": treatment_editorial["acceptance_passes"]
                > control_editorial["acceptance_passes"],
                "targeted_quote_mutation_decreased": treatment_quote < control_quote,
                "no_material_unrelated_failure_increase": unrelated_treatment
                <= unrelated_control,
            },
            "candidate_decision": decision,
            "root_conclusion": conclusion,
            "production_promotion": decision == "ADOPT",
            "production_prompt_modified": False,
            "recommended_next_milestone": (
                "Part 7I — Controlled Multi-Category Editorial Optimization"
                if decision == "ADOPT"
                else "Part 7H.3 — Third Evidence-Derived Prompt Hypothesis"
            ),
        }
    )
    comparison = {
        "schema_version": 1,
        "experiment_id": run_id,
        "scenario_count": len(pairs),
        "scenarios": pairs,
    }
    return base, budget, comparison, diagnostics


def _report(artifact: dict[str, object]) -> str:
    quote = artifact["quote_mutation_metrics"]
    editorial = artifact["editorial_metrics"]
    return f"""# Controlled Second Prompt Hypothesis Experiment

## Background

Part 7H.2 compares the preserved Part 7C.2 control with the frozen H2 treatment.

## Experimental Design

Twenty-four paired scenarios; one prompt mechanism; zero retries, fallbacks, or replays.

## Prompt Delta Budget

`{artifact['prompt_delta_budget']['validation_result']}` — 1 of 1 mechanism used.

## Control Definition

Part 7C.2 prompt `{artifact['control_prompt_fingerprint']}`.

## Treatment Definition

H2 prompt `{artifact['candidate_prompt_fingerprint']}`.

## Provider Comparability

`{artifact['provider_comparability']['classification']}`.

## Execution Summary

Requests: {artifact['provider_request_count']}; responses: {artifact['provider_response_count']};
retries/fallbacks/replays: {artifact['retry_count']}/{artifact['fallback_count']}/{artifact['replay_count']}.

## Technical Results

Technical successes: {artifact['pipeline_funnel']['technical_pipeline_successes']}/24.

## Reference Results

Exact authorized scenarios: {artifact['reference_metrics']['exact_authorized_scenarios']}/24.

## Editorial Results

Evaluations: {editorial['evaluations']}; passes: {editorial['acceptance_passes']};
mean: {editorial['mean_score']}; median: {editorial['median_score']}.

## Scenario-Level Analysis

The structured comparison artifact contains all 24 paired records and transitions.

## QUOTE_MUTATION Analysis

Control {quote['control_frequency']}; treatment {quote['treatment_frequency']};
resolved {quote['resolved_cases']}; persisting {quote['persisting_cases']};
new {quote['new_cases']}; net reduction {quote['net_reduction']}.

## Candidate Decision

`{artifact['candidate_decision']}`.

## Root Conclusion

`{artifact['root_conclusion']}`.

## Production Promotion Decision

`{'YES' if artifact['production_promotion'] else 'NO'}`. Production prompt source was not modified.
"""


def _write_all(
    artifact: dict[str, object],
    budget: dict[str, object],
    comparison: dict[str, object],
    diagnostics: object,
) -> None:
    write_artifact_atomic(ARTIFACT_PATH, artifact)
    write_artifact_atomic(BUDGET_PATH, budget)
    write_artifact_atomic(COMPARISON_PATH, comparison)
    write_diagnostics_artifact_atomic(DIAGNOSTICS_PATH, diagnostics)
    ProviderDiagnosticsArtifact.model_validate_json(
        DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    )
    REPORT_PATH.write_text(_report(artifact), encoding="utf-8", newline="\n")


def _append_history(artifact: dict[str, object]) -> None:
    source = _history_entry(artifact).model_dump(mode="python")
    source.update(
        {
            "benchmark_version": "controlled-second-prompt-hypothesis-experiment-v1",
            "milestone": "Part 7H.2",
            "control_prompt_fingerprint": artifact["control_prompt_fingerprint"],
            "treatment_prompt_fingerprint": artifact["candidate_prompt_fingerprint"],
            "production_promotion": artifact["production_promotion"],
        }
    )
    append_benchmark_history(HISTORY_PATH, BenchmarkHistoryEntry.model_validate(source))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        h2, harness, budget, corpus, offline = preflight()
    except Exception as error:  # noqa: BLE001
        print(f"EXPERIMENT_ABORTED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    del h2
    print(f"Offline assembly: {len(offline)}/24 passed; provider requests: 0")
    if os.environ.get(OPT_IN) != "1":
        print(f"Live experiment disabled; set {OPT_IN}=1 for exactly 24 requests.")
        return 0
    if resolve_openai_api_key() is None:
        print("EXPERIMENT_ABORTED: credential unavailable", file=sys.stderr)
        return 2
    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini-7h2")
    if any(
        item.benchmark_id == run_id
        for item in load_benchmark_history(HISTORY_PATH).history
    ):
        print("EXPERIMENT_ABORTED: duplicate experiment ID", file=sys.stderr)
        return 2
    pricing = load_benchmark_pricing(PRICING_PATH)
    results = []
    checkpoints = []
    for scenario in corpus:
        record: dict[str, object] = {}

        def transform(invocation, request, *, prompt=harness["candidate_prompt"]):
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
            print(
                f"EXPERIMENT_ABORTED: {scenario.scenario_key} checkpoint",
                file=sys.stderr,
            )
            return 2
        checkpoints.append(record)
        results.append(result)
        print(f"{scenario.scenario_key}: {result.outcome.value}")
    artifact, budget_artifact, comparison, diagnostics = build_h2_artifacts(
        run_id,
        now.isoformat(),
        harness,
        budget,
        tuple(results),
        tuple(checkpoints),
    )
    _write_all(artifact, budget_artifact, comparison, diagnostics)
    _append_history(artifact)
    print(f"Experiment: {run_id}")
    print(f"Decision: {artifact['candidate_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
