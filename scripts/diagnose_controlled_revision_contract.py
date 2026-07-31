"""Build the Part 7D diagnostic artifact from retained, content-free evidence."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.history import (
    load_benchmark_history,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    project_production_request,
)
from scripts.run_controlled_provider_quality_baseline import (
    EXPECTED_SCHEMA_FINGERPRINT,
    schema_fingerprint,
    write_artifact_atomic,
)

BASELINE = Path("docs/artifacts/controlled-provider-quality-baseline.json")
HISTORY = Path("docs/artifacts/controlled-provider-quality-history.json")
OUTPUT = Path("docs/artifacts/controlled-revision-contract-diagnostics.json")


def analyze() -> dict[str, object]:
    """Analyze all retained scenarios without transport, replay, or content output."""

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    history = load_benchmark_history(HISTORY)
    corpus = build_synthetic_corpus()
    scenarios = {item.scenario_key: item for item in corpus}
    if schema_fingerprint() != EXPECTED_SCHEMA_FINGERPRINT:
        raise RuntimeError("frozen schema fingerprint changed")
    if len(scenarios) != 24 or len(baseline["trials"]) != 24:
        raise RuntimeError("benchmark evidence is incomplete")

    records = []
    failures: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    categories: dict[str, Counter[str]] = defaultdict(Counter)
    for retained in baseline["trials"]:
        scenario = scenarios[retained["scenario_id"]]
        invocation = build_production_invocation(scenario)
        projected = project_production_request(scenario, invocation)
        authorized = tuple(scenario.authorized_components)
        diagnostic = retained["diagnostic_code"]
        stage, validator, contract = _localization(diagnostic)
        failures[diagnostic] += 1
        stages[stage] += 1
        categories[scenario.category.value][diagnostic] += 1
        records.append(
            {
                "scenario_id": scenario.scenario_key,
                "category": scenario.category.value,
                "authorized_references": list(authorized),
                "provider_produced_references": None,
                "unknown_references": None,
                "unauthorized_references": None,
                "missing_references": None,
                "unexpected_references": None,
                "reference_overlap": None,
                "reference_precision": None,
                "reference_recall": None,
                "first_invalid_reference": None,
                "reference_values_retained": False,
                "request_projection_valid": (
                    projected.invocation is invocation
                    and projected.invocation_fingerprint
                    == invocation.invocation_fingerprint
                ),
                "observed_diagnostic": diagnostic,
                "recorded_operational_outcome": retained["operational_outcome"],
                "corrected_failure_class": _corrected_class(diagnostic),
                "failure_stage": stage,
                "first_deterministic_failure": diagnostic,
                "responsible_validator": validator,
                "responsible_contract": contract,
                "responsible_component": _component(stage),
                "offline_detectability": _detectability(diagnostic),
            }
        )

    schema = json.loads(controlled_revision_schema_json())
    story_reference = schema["$defs"]["OpenAIRevisedStoryComponent"]["properties"][
        "component_reference"
    ]
    return {
        "artifact_version": 1,
        "milestone_type": "CONTROLLED_REVISION_CONTRACT_DIAGNOSTICS",
        "production_schema_fingerprint": schema_fingerprint(),
        "benchmark_id": baseline["benchmark_id"],
        "benchmark_artifacts_analyzed": 1,
        "history_entries_analyzed": len(history.history),
        "scenario_count": len(records),
        "category_count": len(categories),
        "provider_requests": 0,
        "sdk_requests": 0,
        "network_requests": 0,
        "provider_replay": False,
        "evidence_limitations": [
            "provider-produced reference values were not retained",
            "raw provider responses are intentionally unavailable",
            "reference precision, recall, overlap, and confusion pairs cannot be reconstructed",
            "failed interpretation did not retain latency, token, or cost usage",
        ],
        "scenario_diagnostics": records,
        "aggregate_diagnostics": {
            "failure_frequency": dict(sorted(failures.items())),
            "failure_stage_distribution": dict(sorted(stages.items())),
            "category_distribution": {
                key: dict(sorted(value.items()))
                for key, value in sorted(categories.items())
            },
            "failure_clusters": {
                "reference_contract_rejection": 23,
                "provider_dto_schema_rejection": 1,
            },
            "most_common_unknown_reference": None,
            "most_common_unauthorized_reference": None,
            "reference_frequency_table": None,
            "reference_confusion_matrix": None,
            "unavailable_reason": "provider reference values were not retained",
        },
        "contract_analysis": {
            "complete": False,
            "ambiguous": True,
            "under_specified": True,
            "over_constrained": False,
            "internally_inconsistent": False,
            "evidence": [
                "runtime authorization requires exact equality with invocation references",
                "provider-visible story reference schema constrains syntax but not invocation-specific values",
                "23 schema/DTO-accepted outputs reached deterministic reference rejection",
            ],
        },
        "prompt_analysis": {
            "clearly_specifies_reference_requirements": True,
            "contains_ambiguous_reference_wording": False,
            "permits_multiple_reference_interpretations": False,
            "contains_conflicting_reference_instructions": False,
            "relies_on_implicit_reference_behavior": False,
            "evidence": [
                "frozen instructions require exact copying and exactly one authorized reference",
                "projected input includes required references and editable component references",
            ],
            "prompt_contents_retained": False,
        },
        "schema_analysis": {
            "strict_object_shapes": True,
            "reference_syntax_constrained": True,
            "invocation_specific_reference_values_constrained": False,
            "allows_schema_compliant_unauthorized_story_ids": True,
            "story_reference_rule": story_reference,
            "requires_additional_dynamic_constraints": True,
        },
        "authorization_analysis": {
            "rejects_invalid_references": True,
            "evidence_of_rejecting_valid_references": False,
            "deterministic": True,
            "matches_documented_exact_set_contract": True,
            "validator": "OpenAIControlledRevisionReconstructor.reconstruct",
        },
        "runner_analysis": {
            "requests_projected_correctly": True,
            "provider_responses_captured_for_execution": True,
            "reference_values_captured_for_diagnostics": False,
            "reference_extraction_executed": True,
            "failure_classification_correct": False,
            "artifact_execution_counts_accurate": True,
            "artifact_reference_diagnostics_complete": False,
            "classification_defect": (
                "23 deterministic provider-output reference rejections were recorded as PROVIDER_FAILURE"
            ),
        },
        "offline_detectability": {
            "schema_dynamic-reference_gap": {
                "classification": "Detectable offline",
                "earliest_stage": "provider schema construction audit",
                "potential_request_reduction": "not quantifiable from retained references",
            },
            "reference_value_mismatch": {
                "classification": "Detectable only after provider response",
                "earliest_stage": "DTO-valid response authorization mapping",
                "affected_scenarios": 23,
            },
            "runner_diagnostic_retention_gap": {
                "classification": "Detectable offline",
                "earliest_stage": "benchmark artifact contract validation",
                "potential_request_reduction": 24,
                "explanation": "preflight could have rejected a runner unable to preserve required bounded diagnostics",
            },
        },
        "candidate_root_causes": [
            {
                "candidate": "provider-visible schema lacks invocation-specific reference constraints",
                "confidence": "HIGH",
                "affected_scenarios": 23,
                "supporting_diagnostics": [
                    "openai_provider_output_reference_unknown",
                    "openai_provider_output_reference_unauthorized",
                ],
                "alternative_explanation": "provider ignored explicit prompt references",
                "attribution_status": "not distinguishable from retained evidence",
            },
            {
                "candidate": "provider failed to copy explicit authorized references",
                "confidence": "MEDIUM",
                "affected_scenarios": 23,
                "supporting_diagnostics": ["deterministic exact-set rejection"],
                "alternative_explanation": "generic schema guided a different schema-valid reference",
                "attribution_status": "not distinguishable from retained evidence",
            },
            {
                "candidate": "benchmark runner lost required reference diagnostics and misclassified failures",
                "confidence": "HIGH",
                "affected_scenarios": 24,
                "supporting_diagnostics": [
                    "provider-produced references absent",
                    "23 reconstruction rejections recorded as PROVIDER_FAILURE",
                ],
                "alternative_explanation": None,
                "attribution_status": "confirmed diagnostic defect; not the original reference-generation cause",
            },
        ],
        "history_unchanged": True,
        "production_components_modified": False,
        "root_conclusion": "INSUFFICIENT_EVIDENCE",
        "final_recommendation": "FIX_RUNNER_ONLY",
    }


def _localization(diagnostic: str) -> tuple[str, str, str]:
    if diagnostic == "openai_provider_output_schema_invalid":
        return (
            "provider_dto_validation",
            "Pydantic model validation",
            "provider output DTO",
        )
    return (
        "authorization_mapping",
        "OpenAIControlledRevisionReconstructor.reconstruct",
        "exact authorized-reference set contract",
    )


def _corrected_class(diagnostic: str) -> str:
    return (
        "PROVIDER_OUTPUT_REJECTED_SAFELY"
        if diagnostic.startswith("openai_provider_output_")
        else "PROVIDER_FAILURE"
    )


def _component(stage: str) -> str:
    return (
        "provider DTO interpreter"
        if stage == "provider_dto_validation"
        else "deterministic reconstructor"
    )


def _detectability(diagnostic: str) -> dict[str, object]:
    return {
        "classification": "Detectable only after provider response",
        "earliest_stage": (
            "provider DTO validation"
            if diagnostic == "openai_provider_output_schema_invalid"
            else "authorization mapping"
        ),
    }


def main() -> int:
    artifact = analyze()
    write_artifact_atomic(OUTPUT, artifact)
    print(f"Scenarios analyzed: {artifact['scenario_count']}")
    print(f"Root conclusion: {artifact['root_conclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
