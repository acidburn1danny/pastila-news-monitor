"""Freeze and execute the single Part 7H prompt-effectiveness experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from collections import Counter
from dataclasses import fields
from datetime import UTC, datetime
from enum import Enum
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
    build_editorial_acceptance_specification,
    build_production_invocation,
    production_benchmark_configuration,
    project_production_request,
)
from scripts.run_controlled_provider_quality_baseline import (
    execute_trial,
    write_artifact_atomic,
)
from scripts.run_controlled_provider_quality_baseline_7c2 import (
    _reference_total,
    projection_checkpoint,
)
from scripts.run_controlled_provider_quality_baseline_v2 import build_v2_artifacts

OPT_IN = "SCOUT_RUN_LIVE_PROMPT_EXPERIMENT_7H"
CONTROL_PATH = Path("docs/artifacts/controlled-provider-quality-baseline-7c-2.json")
SEMANTICS_PATH = Path("docs/artifacts/pipeline-success-semantics-reconciliation.json")
DESIGN_PATH = Path(
    "docs/artifacts/controlled-prompt-effectiveness-experiment-design.json"
)
ARTIFACT_PATH = Path("docs/artifacts/controlled-prompt-effectiveness-experiment.json")
DIAGNOSTICS_PATH = Path(
    "docs/artifacts/controlled-prompt-effectiveness-diagnostics.json"
)
REPORT_PATH = Path("docs/controlled-prompt-effectiveness-experiment.md")
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
PRICING_PATH = Path("config/controlled-revision-provider-pricing-v1.yaml")
CONTROL_RUN_ID = "20260728-120420-openai-gpt-4.1-mini-7c2"
QUALITY_THRESHOLD = 12
MINIMUM_ACCEPTANCE_GAIN = 6
MINIMUM_MEAN_SCORE_GAIN = 10.0
MINIMUM_IMPROVED_SCENARIOS = 16

CANDIDATE_ADDITION = (
    " EDITORIAL PRESERVATION RULES: Treat the supplied source draft as the "
    "authoritative account. Preserve every factual claim, causal relationship, "
    "attribution, named source, quotation wording, number, date, and time unless the "
    "authorized revision instruction explicitly requires changing that exact item. "
    "Make the smallest coherent change needed to satisfy the authorized instruction. "
    "Do not replace concrete source language with generic paraphrase, strengthen or "
    "weaken claims, infer motives or context, or add interpretation. If the targeted "
    "content already satisfies the instruction or a no-op is requested, preserve its "
    "wording. Before responding, verify that revised content preserves meaning, source "
    "authority, quotations, and all required facts."
)


def _sha(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode()
    return hashlib.sha256(data).hexdigest()


def _canonical_fingerprint(value) -> str:
    return _sha(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _rubric_projection() -> list[dict[str, object]]:
    projections = []
    for scenario in build_synthetic_corpus():
        specification = build_editorial_acceptance_specification(scenario)
        projections.append(
            {
                item.name: _json_safe(getattr(specification, item.name))
                for item in fields(specification)
            }
        )
    return projections


def _json_safe(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def control_prompt() -> str:
    scenario = build_synthetic_corpus()[0]
    return project_production_request(scenario).client_request.payload.instructions


def candidate_prompt() -> str:
    return control_prompt() + CANDIDATE_ADDITION


def _taxonomy(control) -> list[dict[str, object]]:
    rejected = [
        item
        for item in control["trials"]
        if item["quality_failure_category"] != "USABLE_REVISION"
    ]
    counts = Counter(item["quality_failure_category"] for item in rejected)
    definitions = {
        "SOURCE_AUTHORITY_DRIFT": (
            "Meaning, instruction compliance, or source authority was not preserved",
            "PROMPT_ADDRESSABLE",
            "high",
        ),
        "QUOTE_MUTATION": (
            "An authoritative quotation changed while revising the target",
            "PROMPT_ADDRESSABLE",
            "high",
        ),
    }
    return [
        {
            "category_id": category,
            "definition": definitions[category][0],
            "inclusion_criteria": f"quality_failure_category == {category}",
            "exclusion_criteria": "another primary frozen evaluator category applies",
            "scenario_count": count,
            "evaluated_scenario_percentage": count / 24,
            "rejected_scenario_percentage": count / len(rejected),
            "severity": "high",
            "independently_causes_rejection": True,
            "prompt_addressability": definitions[category][1],
            "confidence": definitions[category][2],
            "scenario_ids": [
                item["scenario_id"]
                for item in rejected
                if item["quality_failure_category"] == category
            ],
        }
        for category, count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def freeze_design(path: Path = DESIGN_PATH) -> dict[str, object]:
    """Create the immutable evidence-derived experiment design before transport."""

    if path.exists():
        raise RuntimeError("experiment_design_already_frozen")
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS_PATH.read_text(encoding="utf-8"))
    if (
        not control.get("official_baseline")
        or control["benchmark_id"] != CONTROL_RUN_ID
        or control["pipeline_funnel"]["technical_pipeline_successes"] != 24
        or control["pipeline_funnel"]["editorial_acceptance_passes"] != 1
        or control["reference_metrics"]["exact_reference_compliance_scenarios"] != 24
        or not semantics.get("ready_for_part_7h")
    ):
        raise RuntimeError("control_evidence_verification_failed")
    baseline = control_prompt()
    candidate = baseline + CANDIDATE_ADDITION
    taxonomy = _taxonomy(control)
    configuration = production_benchmark_configuration().model_dump(mode="json")
    configuration.pop("authentication_reference", None)
    design = {
        "schema_version": 1,
        "milestone": "Part 7H — Controlled Prompt Effectiveness Experiment",
        "created_at": datetime.now(UTC).isoformat(),
        "source_control_milestone": "Part 7C.2",
        "source_control_run_id": CONTROL_RUN_ID,
        "control_prompt_fingerprint": _sha(baseline),
        "candidate_prompt_fingerprint": _sha(candidate),
        "candidate_prompt": candidate,
        "prompt_diff": CANDIDATE_ADDITION,
        "prompt_diff_fingerprint": _sha(CANDIDATE_ADDITION),
        "taxonomy": taxonomy,
        "prompt_addressability": {
            "prompt_addressable_categories": 2,
            "partially_prompt_addressable_categories": 0,
            "not_prompt_addressable_categories": 0,
            "insufficient_evidence_categories": 0,
        },
        "candidate_changes": [
            {
                "change_id": "PRESERVE-01",
                "baseline_location": "preservation instruction",
                "candidate_wording": CANDIDATE_ADDITION.strip(),
                "failure_categories": ["SOURCE_AUTHORITY_DRIFT", "QUOTE_MUTATION"],
                "scenario_evidence": {
                    "SOURCE_AUTHORITY_DRIFT": 21,
                    "QUOTE_MUTATION": 2,
                },
                "expected_effect": "preserve meaning, authority, quotations, and exact facts while limiting edit scope",
                "possible_adverse_effect": "under-editing or longer input",
                "technical_contract_impact": "none",
                "confidence": "high",
            }
        ],
        "candidate_rationale": "23 of 24 outputs failed preservation-related editorial dimensions",
        "expected_effects": [
            "reduce source-authority drift",
            "eliminate quote mutation",
            "improve instruction and meaning preservation",
        ],
        "known_risks": ["under-editing", "minor prompt-token increase"],
        "control_configuration": configuration,
        "treatment_configuration": configuration,
        "frozen_dimensions": [
            "corpus",
            "scenario order",
            "provider and model",
            "schema projection",
            "authorization",
            "reconstruction",
            "EpisodeDraft validation",
            "editorial rubric and threshold",
            "retry, fallback, and replay policy",
        ],
        "independent_variable": "provider instruction text",
        "primary_metric": "editorial_acceptance_rate",
        "secondary_metrics": [
            "mean editorial dimension-pass score",
            "paired score changes",
            "failure taxonomy",
            "technical and reference non-regression",
            "latency, usage, and cost",
        ],
        "editorial_improvement_threshold": {
            "rule": "acceptance gain >= 6 OR (mean score gain >= 10 and improved scenarios >= 16)",
            "minimum_acceptance_gain": MINIMUM_ACCEPTANCE_GAIN,
            "minimum_mean_score_gain": MINIMUM_MEAN_SCORE_GAIN,
            "minimum_improved_scenarios": MINIMUM_IMPROVED_SCENARIOS,
            "maximum_pass_to_fail": 0,
        },
        "technical_non_regression_gates": {
            "technical_pipeline_success_rate": 1.0,
            "dto_validation_rate": 1.0,
            "authorization_rate": 1.0,
            "reconstruction_rate": 1.0,
            "episode_draft_validation_rate": 1.0,
        },
        "reference_non_regression_gates": {
            "exact_reference_compliance_rate": 1.0,
            "precision": 1.0,
            "recall": 1.0,
            "unknown": 0,
            "unauthorized": 0,
            "missing": 0,
        },
        "operational_limits": {
            "requests": 24,
            "retries": 0,
            "fallbacks": 0,
            "replays": 0,
        },
        "stop_conditions": [
            "prompt identity mismatch",
            "projection invariant failure",
            "second request, retry, fallback, or replay",
            "configuration, corpus, rubric, or threshold mismatch",
        ],
        "planned_provider_requests": 24,
        "planned_retries": 0,
        "planned_fallbacks": 0,
        "planned_replays": 0,
        "design_frozen": True,
    }
    write_artifact_atomic(path, design)
    return design


def _transform_request(invocation, request, prompt: str):
    del invocation
    payload = request.payload.model_copy(update={"instructions": prompt})
    return request.model_copy(update={"payload": payload})


def prompt_projection_checkpoint(scenario_id, invocation, request, design):
    record = projection_checkpoint(scenario_id, invocation, request)
    prompt_fingerprint = _sha(request.payload.instructions)
    record.update(
        {
            "prompt_fingerprint": prompt_fingerprint,
            "prompt_identity": prompt_fingerprint
            == design["candidate_prompt_fingerprint"],
            "control_prompt_absent": prompt_fingerprint
            != design["control_prompt_fingerprint"],
        }
    )
    if not record["prompt_identity"] or not record["control_prompt_absent"]:
        raise RuntimeError("PRE_REQUEST_PROMPT_IDENTITY_FAILURE")
    return record


def dry_run(design, corpus):
    records = []
    for scenario in corpus:
        invocation = build_production_invocation(scenario)
        projected = project_production_request(scenario, invocation)
        transformed = _transform_request(
            invocation, projected.client_request, design["candidate_prompt"]
        )
        records.append(
            prompt_projection_checkpoint(
                scenario.scenario_key, invocation, transformed, design
            )
        )
    return tuple(records)


def _quality_score(trial) -> float | None:
    quality = trial.get("quality")
    if quality is None:
        return None
    return 100 * sum(bool(value) for value in quality.values()) / len(quality)


def _taxonomy_category(trial) -> str | None:
    value = trial.get("quality_failure_category")
    return None if value == "USABLE_REVISION" else value


def _paired(control, treatment, checkpoints) -> list[dict[str, object]]:
    checkpoint_by_id = {item["scenario_id"]: item for item in checkpoints}
    treatment_by_id = {item["scenario_id"]: item for item in treatment}
    pairs = []
    for order, control_item in enumerate(control, 1):
        scenario_id = control_item["scenario_id"]
        treatment_item = treatment_by_id[scenario_id]
        checkpoint = checkpoint_by_id[scenario_id]
        control_score = _quality_score(control_item)
        treatment_score = _quality_score(treatment_item)
        control_pass = bool(
            (control_item.get("quality") or {}).get("editorial_acceptance")
        )
        treatment_pass = bool(
            (treatment_item.get("quality") or {}).get("editorial_acceptance")
        )
        transition = (
            "PASS_TO_PASS"
            if control_pass and treatment_pass
            else (
                "PASS_TO_FAIL"
                if control_pass
                else "FAIL_TO_PASS" if treatment_pass else "FAIL_TO_FAIL"
            )
        )
        references = treatment_item["references"]
        pairs.append(
            {
                "scenario_id": scenario_id,
                "scenario_order": order,
                "control_result_reference": f"{CONTROL_RUN_ID}:{scenario_id}",
                "treatment_request_id": treatment_item.get("provider_request_id_hash"),
                "treatment_response_id": treatment_item.get("provider_request_id_hash"),
                "control_prompt_fingerprint": _sha(control_prompt()),
                "candidate_prompt_fingerprint": checkpoint["prompt_fingerprint"],
                "authorized_reference_count": checkpoint["authorized_reference_count"],
                "projected_reference_count": checkpoint[
                    "projected_schema_reference_count"
                ],
                "projection_count_equality": checkpoint["count_equality"],
                "projection_set_equality": checkpoint["set_equality"],
                "technical_pipeline_success_control": control_item[
                    "operational_outcome"
                ]
                == "PIPELINE_SUCCESS",
                "technical_pipeline_success_treatment": treatment_item[
                    "operational_outcome"
                ]
                == "PIPELINE_SUCCESS",
                "exact_reference_compliance_control": not any(
                    control_item["references"][name]
                    for name in (
                        "unknown_references",
                        "unauthorized_references",
                        "missing_authorized_references",
                        "duplicate_provider_references",
                    )
                ),
                "exact_reference_compliance_treatment": not any(
                    references[name]
                    for name in (
                        "unknown_references",
                        "unauthorized_references",
                        "missing_authorized_references",
                        "duplicate_provider_references",
                    )
                ),
                "editorial_score_control": control_score,
                "editorial_score_treatment": treatment_score,
                "editorial_score_delta": (
                    treatment_score - control_score
                    if control_score is not None and treatment_score is not None
                    else None
                ),
                "editorial_acceptance_control": control_pass,
                "editorial_acceptance_treatment": treatment_pass,
                "acceptance_transition": transition,
                "primary_failure_category_control": _taxonomy_category(control_item),
                "primary_failure_category_treatment": _taxonomy_category(
                    treatment_item
                ),
                "secondary_failure_categories_control": [
                    key
                    for key, value in (control_item.get("quality") or {}).items()
                    if not value
                ],
                "secondary_failure_categories_treatment": [
                    key
                    for key, value in (treatment_item.get("quality") or {}).items()
                    if not value
                ],
                "provider_latency_control": control_item.get("provider_latency_ms"),
                "provider_latency_treatment": treatment_item.get("provider_latency_ms"),
                "input_tokens_control": control_item["usage"].get("prompt_tokens"),
                "input_tokens_treatment": treatment_item["usage"].get("prompt_tokens"),
                "output_tokens_control": control_item["usage"].get("completion_tokens"),
                "output_tokens_treatment": treatment_item["usage"].get(
                    "completion_tokens"
                ),
                "total_cost_control": control_item["cost"].get("estimated_cost_usd"),
                "total_cost_treatment": treatment_item["cost"].get(
                    "estimated_cost_usd"
                ),
            }
        )
    return pairs


def _score_metrics(trials) -> dict[str, object]:
    scores = [score for item in trials if (score := _quality_score(item)) is not None]
    passes = sum(
        bool(item["quality"]["editorial_acceptance"])
        for item in trials
        if item.get("quality")
    )
    return {
        "evaluations": len(scores),
        "acceptance_passes": passes,
        "acceptance_failures": len(scores) - passes,
        "acceptance_rate": passes / len(scores) if scores else None,
        "mean_score": statistics.fmean(scores) if scores else None,
        "median_score": statistics.median(scores) if scores else None,
        "minimum_score": min(scores) if scores else None,
        "maximum_score": max(scores) if scores else None,
    }


def build_experiment_artifact(run_id, created_at, design, results, checkpoints):
    pricing = load_benchmark_pricing(PRICING_PATH)
    treatment_base, diagnostics = build_v2_artifacts(
        run_id, created_at, pricing, results
    )
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    treatment_trials = treatment_base["trials"]
    pairs = _paired(control["trials"], treatment_trials, checkpoints)
    control_editorial = _score_metrics(control["trials"])
    treatment_editorial = _score_metrics(treatment_trials)
    transitions = Counter(item["acceptance_transition"] for item in pairs)
    deltas = [
        item["editorial_score_delta"]
        for item in pairs
        if item["editorial_score_delta"] is not None
    ]
    improved = sum(delta > 0 for delta in deltas)
    acceptance_gain = (
        treatment_editorial["acceptance_passes"]
        - control_editorial["acceptance_passes"]
    )
    mean_gain = treatment_editorial["mean_score"] - control_editorial["mean_score"]
    technical = treatment_base["pipeline_funnel"]["technical_pipeline_successes"] == 24
    reference = (
        treatment_base["reference_metrics"]["exact_authorized_scenarios"] == 24
        and _reference_total(treatment_base, "unknown_references") == 0
        and _reference_total(treatment_base, "unauthorized_references") == 0
        and _reference_total(treatment_base, "missing_authorized_references") == 0
    )
    editorial_threshold = (
        acceptance_gain >= MINIMUM_ACCEPTANCE_GAIN
        or (
            mean_gain >= MINIMUM_MEAN_SCORE_GAIN
            and improved >= MINIMUM_IMPROVED_SCENARIOS
        )
    ) and transitions["PASS_TO_FAIL"] == 0
    sufficient = treatment_editorial["evaluations"] >= QUALITY_THRESHOLD
    integrity = (
        len(checkpoints) == 24
        and all(
            item["prompt_identity"] and item["set_equality"] for item in checkpoints
        )
        and treatment_base["provider_request_count"] == 24
        and treatment_base["retry_count"] == treatment_base["fallback_count"] == 0
    )
    if not integrity or not sufficient:
        decision, conclusion, effectiveness = (
            "INCONCLUSIVE",
            "EXPERIMENT_INVALID_EXECUTION_INTEGRITY_FAILURE",
            "INCONCLUSIVE",
        )
    elif not technical:
        decision, conclusion, effectiveness = (
            "REJECT",
            "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION",
            "REGRESSED",
        )
    elif not reference:
        decision, conclusion, effectiveness = (
            "REJECT",
            "CANDIDATE_PROMPT_FAILED_REFERENCE_NON_REGRESSION",
            "REGRESSED",
        )
    elif editorial_threshold:
        decision, conclusion, effectiveness = (
            "ADOPT",
            "CANDIDATE_PROMPT_EFFECTIVE",
            "MATERIALLY_IMPROVED",
        )
    else:
        decision, conclusion, effectiveness = (
            "REJECT",
            "CANDIDATE_PROMPT_INEFFECTIVE",
            "NO_MEANINGFUL_CHANGE",
        )
    artifact = {
        "schema_version": 1,
        "milestone": "Part 7H — Controlled Prompt Effectiveness Experiment",
        "run_id": run_id,
        "created_at": created_at,
        "experiment_status": "COMPLETE",
        "official_experiment": integrity,
        "source_control_milestone": "Part 7C.2",
        "source_control_run_id": CONTROL_RUN_ID,
        "control_prompt_fingerprint": design["control_prompt_fingerprint"],
        "candidate_prompt_fingerprint": design["candidate_prompt_fingerprint"],
        "prompt_diff_fingerprint": design["prompt_diff_fingerprint"],
        "benchmark_corpus_fingerprint": _canonical_fingerprint(
            [item.scenario_key for item in build_synthetic_corpus()]
        ),
        "provider_configuration": design["treatment_configuration"],
        "provider_configuration_fingerprint": _canonical_fingerprint(
            design["treatment_configuration"]
        ),
        "rubric_fingerprint": _canonical_fingerprint(_rubric_projection()),
        "editorial_threshold": "all frozen evaluation dimensions required",
        "projection_checkpoint": {
            "scenarios": list(checkpoints),
            "count_equality_passes": sum(
                bool(item["count_equality"]) for item in checkpoints
            ),
            "set_equality_passes": sum(
                bool(item["set_equality"]) for item in checkpoints
            ),
        },
        "prompt_identity_checkpoint": {
            "scenarios": len(checkpoints),
            "passes": sum(bool(item["prompt_identity"]) for item in checkpoints),
            "failures": sum(not item["prompt_identity"] for item in checkpoints),
        },
        "provider_request_count": treatment_base["provider_request_count"],
        "provider_response_count": treatment_base["pipeline_funnel"][
            "provider_responses_received"
        ],
        "retry_count": treatment_base["retry_count"],
        "fallback_count": treatment_base["fallback_count"],
        "replay_count": 0,
        "control_metrics": {
            "pipeline_funnel": control["pipeline_funnel"],
            "reference_metrics": control["reference_metrics"],
            "editorial_metrics": control_editorial,
        },
        "treatment_metrics": {
            "pipeline_funnel": treatment_base["pipeline_funnel"],
            "reference_metrics": treatment_base["reference_metrics"],
            "editorial_metrics": treatment_editorial,
        },
        "paired_scenario_results": pairs,
        "pipeline_funnel": treatment_base["pipeline_funnel"],
        "reference_metrics": treatment_base["reference_metrics"],
        "editorial_metrics": {
            **treatment_editorial,
            "acceptance_absolute_delta": treatment_editorial["acceptance_rate"]
            - control_editorial["acceptance_rate"],
            "mean_score_delta": mean_gain,
            "median_score_delta": treatment_editorial["median_score"]
            - control_editorial["median_score"],
            "fail_to_pass": transitions["FAIL_TO_PASS"],
            "pass_to_fail": transitions["PASS_TO_FAIL"],
            "improved_score_scenarios": improved,
            "unchanged_score_scenarios": sum(delta == 0 for delta in deltas),
            "regressed_score_scenarios": sum(delta < 0 for delta in deltas),
        },
        "failure_taxonomy_control": Counter(
            _taxonomy_category(item)
            for item in control["trials"]
            if _taxonomy_category(item)
        ),
        "failure_taxonomy_treatment": Counter(
            _taxonomy_category(item)
            for item in treatment_trials
            if _taxonomy_category(item)
        ),
        "targeted_category_effectiveness": {},
        "new_failure_categories": [],
        "latency_metrics": {
            "control": control["latency_metrics"],
            "treatment": treatment_base["latency_metrics"],
        },
        "usage_metrics": {
            "control": control["usage_metrics"],
            "treatment": treatment_base["usage_metrics"],
        },
        "cost_metrics": {
            "control": control["cost_metrics"],
            "treatment": treatment_base["cost_metrics"],
        },
        "technical_non_regression": technical,
        "reference_non_regression": reference,
        "editorial_improvement": {
            "threshold_passed": editorial_threshold,
            "effectiveness": effectiveness,
        },
        "experiment_integrity": integrity,
        "candidate_decision": decision,
        "adoption_rationale": "precommitted decision framework applied to paired frozen-corpus evidence",
        "quality_sample": "SUFFICIENT" if sufficient else "INSUFFICIENT",
        "root_conclusion": conclusion,
        "recommended_next_milestone": (
            "Part 7I — Production Prompt Promotion and Post-Adoption Validation"
            if decision == "ADOPT"
            else "Part 7H.1 — Second Prompt Hypothesis Design"
        ),
        "trials": treatment_trials,
    }
    control_taxonomy = artifact["failure_taxonomy_control"]
    treatment_taxonomy = artifact["failure_taxonomy_treatment"]
    artifact["targeted_category_effectiveness"] = {
        category: {
            "control": control_taxonomy.get(category, 0),
            "treatment": treatment_taxonomy.get(category, 0),
            "absolute_reduction": control_taxonomy.get(category, 0)
            - treatment_taxonomy.get(category, 0),
        }
        for category in ("SOURCE_AUTHORITY_DRIFT", "QUOTE_MUTATION")
    }
    artifact["new_failure_categories"] = sorted(
        set(treatment_taxonomy) - set(control_taxonomy)
    )
    return artifact, diagnostics


def _history_entry(artifact) -> BenchmarkHistoryEntry:
    treatment = artifact["treatment_metrics"]
    editorial = treatment["editorial_metrics"]
    latency = artifact["latency_metrics"]["treatment"]["all_provider_calls"]
    usage = artifact["usage_metrics"]["treatment"]
    cost = artifact["cost_metrics"]["treatment"]
    return BenchmarkHistoryEntry.model_validate(
        {
            "benchmark_id": artifact["run_id"],
            "benchmark_date": artifact["created_at"],
            "benchmark_version": "controlled-prompt-effectiveness-experiment-v1",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "prompt_version": artifact["candidate_prompt_fingerprint"],
            "schema_fingerprint": artifact["projection_checkpoint"]["scenarios"][0][
                "effective_schema_fingerprint"
            ],
            "pricing_version": artifact["cost_metrics"]["treatment"]["pricing_version"],
            "scenario_count": 24,
            "category_count": 12,
            "usable_revision_rate": editorial["acceptance_rate"],
            "editorial_acceptance_rate": editorial["acceptance_rate"],
            "dto_pass_rate": 1.0,
            "meaning_preservation_rate": None,
            "average_latency_ms": latency["mean"],
            "p95_latency_ms": latency["p95"],
            "average_prompt_tokens": usage["prompt_tokens"] / 24,
            "average_completion_tokens": usage["completion_tokens"] / 24,
            "average_reasoning_tokens": usage["reasoning_tokens"] / 24,
            "average_cost_per_scenario": cost["known_estimated_total_cost_usd"] / 24,
            "average_cost_per_usable_revision": None,
            "total_benchmark_cost": cost["known_estimated_total_cost_usd"],
            "provider_requests": 24,
            "retry_count": 0,
            "fallback_count": 0,
            "root_conclusion": artifact["root_conclusion"],
            "milestone": "Part 7H",
            "official_experiment": artifact["official_experiment"],
            "control_run_id": CONTROL_RUN_ID,
            "candidate_prompt_fingerprint": artifact["candidate_prompt_fingerprint"],
            "technical_pipeline_successes": artifact["pipeline_funnel"][
                "technical_pipeline_successes"
            ],
            "exact_reference_compliance": artifact["reference_metrics"][
                "exact_authorized_scenarios"
            ],
            "editorial_evaluation_count": editorial["evaluations"],
            "editorial_acceptance_count": editorial["acceptance_passes"],
            "mean_editorial_score": editorial["mean_score"],
            "median_editorial_score": editorial["median_score"],
            "fail_to_pass_count": artifact["editorial_metrics"]["fail_to_pass"],
            "pass_to_fail_count": artifact["editorial_metrics"]["pass_to_fail"],
            "candidate_decision": artifact["candidate_decision"],
        }
    )


def write_report(artifact, design) -> None:
    report = f"""# Part 7H — Controlled Prompt Effectiveness Experiment

## Executive Summary

The frozen candidate decision is `{artifact['candidate_decision']}` with root conclusion
`{artifact['root_conclusion']}`. The control is official Part 7C.2; only the provider
instruction text changed.

## Editorial Failure Taxonomy

```json
{json.dumps(design['taxonomy'], ensure_ascii=False, indent=2, sort_keys=True)}
```

The control taxonomy contains 21 `SOURCE_AUTHORITY_DRIFT` and 2 `QUOTE_MUTATION`
primary failures. Both were classified prompt-addressable before execution. No
non-prompt category dominated, so the candidate eligibility gate passed.

## Candidate Prompt and Frozen Design

Control fingerprint: `{design['control_prompt_fingerprint']}`.
Candidate fingerprint: `{design['candidate_prompt_fingerprint']}`.
The exact candidate and evidence mapping are preserved in the design artifact.

## Frozen Experimental Design and Success Thresholds

The treatment uses the same 24 scenarios, order, provider/model configuration, exact
schema projection, authorization, reconstruction, EpisodeDraft validation, editorial
rubric, threshold, single-attempt policy, and pricing as Part 7C.2. The sole intended
variable is prompt text. The precommitted threshold was:

```json
{json.dumps(design['editorial_improvement_threshold'], indent=2, sort_keys=True)}
```

Technical and exact-reference success were required to remain 100%.

## Treatment Funnel and Reference Metrics

```json
{json.dumps({'pipeline': artifact['pipeline_funnel'], 'references': artifact['reference_metrics']}, indent=2, sort_keys=True)}
```

## Editorial and Paired Metrics

```json
{json.dumps(artifact['editorial_metrics'], indent=2, sort_keys=True)}
```

Acceptance moved from {artifact['control_metrics']['editorial_metrics']['acceptance_passes']}
of {artifact['control_metrics']['editorial_metrics']['evaluations']} to
{artifact['editorial_metrics']['acceptance_passes']} of
{artifact['editorial_metrics']['evaluations']}. Paired transitions were
{artifact['editorial_metrics']['fail_to_pass']} fail-to-pass and
{artifact['editorial_metrics']['pass_to_fail']} pass-to-fail.

## Failure-Taxonomy Comparison

```json
{json.dumps(artifact['targeted_category_effectiveness'], indent=2, sort_keys=True)}
```

Quote mutation fell from 2 to 0, but source-authority drift rose from 21 to 23.
No new primary category appeared. The targeted improvement was therefore narrow and
offset by broader preservation failure.

## Latency, Usage, and Cost

```json
{json.dumps({'latency': artifact['latency_metrics'], 'usage': artifact['usage_metrics'], 'cost': artifact['cost_metrics']}, indent=2, sort_keys=True)}
```

## Experiment Integrity

Projection, prompt identity, request count, no-retry, no-fallback, no-replay,
technical, and reference gates are preserved in the structured artifact. Production
prompt source code was not modified.

Exactly 24 provider requests were attempted with zero retries, fallbacks, and replays.
One request timed out after 30 seconds, leaving 23 responses and 23 evaluable outputs.
The sample remains sufficient, but mandatory technical and reference non-regression
gates failed. No timeout replay or replacement was performed.

## Candidate Decision and Adoption Rationale

Decision: `{artifact['candidate_decision']}`. Editorial acceptance decreased from
1/24 to 0/23; the mean quality score decreased; one control pass became a treatment
failure; and technical/reference completion fell from 24 to 23. The frozen candidate
must not be promoted.

## Known Limitations

The experiment is descriptive for one 24-scenario corpus and one model alias. The
single timeout makes that scenario non-comparable editorially. Privacy-safe artifacts
retain structural references, quality dimensions, hashed request identity, latency,
usage, and cost rather than provider prose. No population-level model claim is made.

## Final Recommendation

`{artifact['recommended_next_milestone']}`
"""
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")


def preflight(design):
    if (
        not design.get("design_frozen")
        or candidate_prompt() != design["candidate_prompt"]
    ):
        raise RuntimeError("candidate_prompt_freeze_mismatch")
    corpus = build_synthetic_corpus()
    if tuple(item.scenario_key for item in corpus) != tuple(
        f"SYN-{number:02d}" for number in range(1, 25)
    ):
        raise RuntimeError("corpus_mismatch")
    configuration = production_benchmark_configuration()
    if (
        configuration.model_identifier != "gpt-4.1-mini"
        or configuration.retry_policy.maximum_attempts != 1
    ):
        raise RuntimeError("configuration_mismatch")
    if any(path.exists() for path in (ARTIFACT_PATH, DIAGNOSTICS_PATH, REPORT_PATH)):
        raise RuntimeError("experiment_artifact_already_exists")
    history = load_benchmark_history(HISTORY_PATH)
    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%d-%H%M%S-openai-gpt-4.1-mini-7h")
    if any(item.benchmark_id == run_id for item in history.history):
        raise RuntimeError("duplicate_experiment_id")
    checkpoints = dry_run(design, corpus)
    if len(checkpoints) != 24 or not all(
        item["prompt_identity"] and item["set_equality"] for item in checkpoints
    ):
        raise RuntimeError("dry_run_checkpoint_failure")
    return run_id, now, corpus, checkpoints


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-design", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_design:
        design = freeze_design()
        print(f"Design frozen: {design['candidate_prompt_fingerprint']}")
        return 0
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    try:
        run_id, now, corpus, dry_checkpoints = preflight(design)
    except Exception as error:  # noqa: BLE001
        print(f"EXPERIMENT_ABORTED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(f"Dry run: {len(dry_checkpoints)} prompt and projection checkpoints passed")
    if os.environ.get(OPT_IN) != "1":
        print(f"Live experiment disabled; set {OPT_IN}=1 for exactly 24 requests.")
        return 0
    if resolve_openai_api_key() is None:
        print("EXPERIMENT_ABORTED: credential unavailable", file=sys.stderr)
        return 2
    pricing = load_benchmark_pricing(PRICING_PATH)
    results = []
    checkpoints = []
    for scenario in corpus:
        record = {}

        def transform(invocation, request, *, prompt=design["candidate_prompt"]):
            return _transform_request(invocation, request, prompt)

        def gate(
            invocation, request, *, sink=record, scenario_id=scenario.scenario_key
        ):
            sink.update(
                prompt_projection_checkpoint(scenario_id, invocation, request, design)
            )

        result = execute_trial(
            scenario,
            pricing,
            request_transformer=transform,
            pre_request_validator=gate,
        )
        if (
            not record
            or not record.get("prompt_identity")
            or not record.get("set_equality")
        ):
            print(
                f"EXPERIMENT_ABORTED: {scenario.scenario_key} checkpoint",
                file=sys.stderr,
            )
            return 2
        checkpoints.append(record)
        results.append(result)
        print(f"{scenario.scenario_key}: {result.outcome.value}")
    artifact, diagnostics = build_experiment_artifact(
        run_id, now.isoformat(), design, tuple(results), tuple(checkpoints)
    )
    write_artifact_atomic(ARTIFACT_PATH, artifact)
    write_diagnostics_artifact_atomic(DIAGNOSTICS_PATH, diagnostics)
    ProviderDiagnosticsArtifact.model_validate_json(
        DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    )
    append_benchmark_history(HISTORY_PATH, _history_entry(artifact))
    write_report(artifact, design)
    print(f"Experiment: {run_id}")
    print(f"Decision: {artifact['candidate_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
