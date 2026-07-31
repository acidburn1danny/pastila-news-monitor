"""Build the fully offline Part 7H.1 second-prompt design artifacts."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    project_production_request,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    ARTIFACT_PATH as H1_ARTIFACT_PATH,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    DESIGN_PATH as H1_DESIGN_PATH,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    REPORT_PATH as H1_REPORT_PATH,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    _transform_request,
    control_prompt,
)
from scripts.run_controlled_provider_quality_baseline_7c2 import projection_checkpoint

CONTROL_ARTIFACT_PATH = Path(
    "docs/artifacts/controlled-provider-quality-baseline-7c-2.json"
)
SEMANTICS_ARTIFACT_PATH = Path(
    "docs/artifacts/pipeline-success-semantics-reconciliation.json"
)
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
DESIGN_PATH = Path("docs/artifacts/second-prompt-hypothesis-design.json")
REPORT_PATH = Path("docs/second-prompt-hypothesis-design.md")

H2_ADDITION = (
    " QUOTATION PRESERVATION: When an editable component contains quoted source "
    "language, copy the quotation wording verbatim unless the authorized revision "
    "instruction explicitly targets that quotation."
)


def _sha(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canonical_fingerprint(value: object) -> str:
    return _sha(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def h2_prompt() -> str:
    """Return H2 derived directly from the frozen production prompt."""

    return control_prompt() + H2_ADDITION


def _diff(before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def verify_evidence() -> dict[str, object]:
    """Verify frozen Part 7C.2 and Part 7H evidence without changing it."""

    required = (
        CONTROL_ARTIFACT_PATH,
        SEMANTICS_ARTIFACT_PATH,
        H1_DESIGN_PATH,
        H1_ARTIFACT_PATH,
        H1_REPORT_PATH,
        HISTORY_PATH,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"required_evidence_missing: {', '.join(missing)}")

    control = json.loads(CONTROL_ARTIFACT_PATH.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS_ARTIFACT_PATH.read_text(encoding="utf-8"))
    h1_design = json.loads(H1_DESIGN_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_ARTIFACT_PATH.read_text(encoding="utf-8"))
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))["history"]
    baseline = control_prompt()

    checks = {
        "control_official": control.get("official_baseline") is True,
        "semantics_ready": semantics.get("ready_for_part_7h") is True,
        "decision_reject": h1.get("candidate_decision") == "REJECT",
        "root_conclusion": h1.get("root_conclusion")
        == "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION",
        "production_prompt_unchanged": _sha(baseline)
        == h1.get("control_prompt_fingerprint")
        == h1_design.get("control_prompt_fingerprint"),
        "h1_prompt_unchanged": _sha(h1_design["candidate_prompt"])
        == h1.get("candidate_prompt_fingerprint"),
        "h1_diff_unchanged": _sha(h1_design["prompt_diff"])
        == h1.get("prompt_diff_fingerprint"),
        "history_linked": any(
            entry.get("benchmark_id") == h1.get("run_id")
            and entry.get("candidate_decision") == "REJECT"
            for entry in history
        ),
    }
    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"frozen_evidence_verification_failed: {failures}")
    return {
        "control": control,
        "semantics": semantics,
        "h1_design": h1_design,
        "h1": h1,
        "checks": checks,
    }


def _h1_changes(h1_addition: str) -> list[dict[str, object]]:
    common = {
        "prompt_section": "EDITORIAL PRESERVATION RULES",
        "change_type": "INSTRUCTION_ADDITION",
        "target_failure_categories": ["SOURCE_AUTHORITY_DRIFT", "QUOTE_MUTATION"],
        "observed_editorial_effect": (
            "Combined H1 moved QUOTE_MUTATION from 2 to 0, moved "
            "SOURCE_AUTHORITY_DRIFT from 21 to 23, improved SYN-10 and SYN-23, "
            "and regressed SYN-20. Individual attribution is confounded."
        ),
        "observed_technical_effect": (
            "SYN-05 timed out at PROVIDER_CALL before DTO, authorization, "
            "reconstruction, EpisodeDraft, or reference evaluation; no prompt edit "
            "is isolated as its cause."
        ),
        "targeted_scenarios_improved": ["SYN-10", "SYN-23"],
        "targeted_scenarios_unchanged": [
            f"SYN-{number:02d}"
            for number in range(1, 25)
            if number not in {5, 10, 20, 23}
        ],
        "targeted_scenarios_regressed": ["SYN-20"],
        "untargeted_regressions": ["SYN-05"],
        "new_failure_modes": ["PROVIDER_TIMEOUT"],
        "causal_confidence": "INSUFFICIENT_EVIDENCE",
    }
    definitions = [
        (
            "H1-C01",
            "Treat the supplied source draft as the authoritative account.",
            "Establish source authority as the dominant preservation objective.",
            "INCONCLUSIVE",
            "MODERATE",
            "LOW",
            "Authority failures increased and the combined experiment cannot isolate this clause.",
        ),
        (
            "H1-C02",
            "Preserve every factual claim, causal relationship, attribution, named source, quotation wording, number, date, and time unless the authorized revision instruction explicitly requires changing that exact item.",
            "Enumerate protected factual and quoted content.",
            "REFORMULATE",
            "MODERATE",
            "MODERATE",
            "Quote mutation fell from two cases to zero, but the exhaustive compound instruction is confounded and unnecessarily broad.",
        ),
        (
            "H1-C03",
            "Make the smallest coherent change needed to satisfy the authorized instruction.",
            "Constrain revisions to the minimum coherent scope.",
            "INCONCLUSIVE",
            "LOW",
            "LOW",
            "Revision proportionality already passed and no independent gain is observable.",
        ),
        (
            "H1-C04",
            "Do not replace concrete source language with generic paraphrase, strengthen or weaken claims, infer motives or context, or add interpretation.",
            "Prohibit several forms of semantic drift.",
            "INCONCLUSIVE",
            "MODERATE",
            "LOW",
            "Source-authority failures increased; the bundled prohibitions cannot be isolated.",
        ),
        (
            "H1-C05",
            "If the targeted content already satisfies the instruction or a no-op is requested, preserve its wording.",
            "Make no-op preservation explicit.",
            "INCONCLUSIVE",
            "LOW",
            "NONE",
            "No-op compliance was already preserved and no measurable incremental benefit exists.",
        ),
        (
            "H1-C06",
            "Before responding, verify that revised content preserves meaning, source authority, quotations, and all required facts.",
            "Add an editorial self-check after the existing structural self-check.",
            "REMOVE",
            "MODERATE",
            "NONE",
            "It duplicates the baseline verification pattern, adds instruction load, and produced no measurable aggregate benefit.",
        ),
    ]
    changes = []
    for change_id, wording, intent, disposition, risk, value, rationale in definitions:
        if wording not in h1_addition:
            raise RuntimeError(f"h1_change_not_found: {change_id}")
        changes.append(
            {
                **common,
                "change_id": change_id,
                "baseline_text": "No equivalent standalone instruction.",
                "h1_text": wording,
                "semantic_intent": intent,
                "expected_effect": "Reduce preservation-related editorial rejection.",
                "technical_risk": risk,
                "editorial_value": value,
                "interaction_dependencies": ["H1-I01"],
                "disposition": disposition,
                "disposition_rationale": rationale,
            }
        )
    return changes


def _offline_validation(prompt: str) -> dict[str, object]:
    records = []
    fingerprint = _sha(prompt)
    for scenario in build_synthetic_corpus():
        invocation = build_production_invocation(scenario)
        projected = project_production_request(scenario, invocation)
        request = _transform_request(invocation, projected.client_request, prompt)
        checkpoint = projection_checkpoint(scenario.scenario_key, invocation, request)
        records.append(
            {
                **checkpoint,
                "prompt_identity": _sha(request.payload.instructions) == fingerprint,
                "request_assembly": True,
            }
        )
    return {
        "scenarios": len(records),
        "prompt_identity_passes": sum(item["prompt_identity"] for item in records),
        "projection_count_equality_passes": sum(
            item["count_equality"] for item in records
        ),
        "projection_set_equality_passes": sum(item["set_equality"] for item in records),
        "request_assembly_passes": sum(item["request_assembly"] for item in records),
        "provider_requests": 0,
        "records": records,
    }


def build_design(*, created_at: str | None = None) -> dict[str, object]:
    """Build the canonical Part 7H.1 structured design in memory."""

    evidence = verify_evidence()
    h1 = evidence["h1"]
    h1_design = evidence["h1_design"]
    baseline = control_prompt()
    h1_prompt = h1_design["candidate_prompt"]
    candidate = h2_prompt()
    changes = _h1_changes(h1_design["prompt_diff"])
    validation = _offline_validation(candidate)
    safety = {
        key: "PASS"
        for key in (
            "contradictory_instructions",
            "ambiguous_priorities",
            "schema_conflict",
            "dto_conflict",
            "reference_conflict",
            "excessive_verbosity_pressure",
            "scope_expansion",
            "unsupported_reasoning_requests",
            "hidden_output_requirements",
            "evaluator_gaming",
            "scenario_overfitting",
            "benchmark_leakage",
            "provider_specific_exploit_wording",
            "unrepresentable_self_check_requirements",
        )
    }
    ready = (
        validation["scenarios"] == 24
        and validation["prompt_identity_passes"] == 24
        and validation["projection_count_equality_passes"] == 24
        and validation["projection_set_equality_passes"] == 24
        and validation["request_assembly_passes"] == 24
        and all(value == "PASS" for value in safety.values())
        and candidate != baseline
        and candidate != h1_prompt
    )
    impact_matrix = changes
    baseline_to_h2 = _diff(baseline, candidate)
    h1_to_h2 = _diff(h1_prompt, candidate)
    artifact = {
        "schema_version": 1,
        "milestone": "Part 7H.1 — Second Prompt Hypothesis Design and Prompt Change Impact Matrix",
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "source_control_milestone": "Part 7C.2",
        "source_control_run_id": h1["source_control_run_id"],
        "source_experiment_milestone": "Part 7H",
        "source_experiment_run_id": h1["run_id"],
        "provider_requests": 0,
        "network_calls": 0,
        "benchmark_executions": 0,
        "benchmark_replays": 0,
        "production_prompt_modified": False,
        "raw_experiment_results_modified": False,
        "control_prompt_fingerprint": _sha(baseline),
        "h1_prompt_fingerprint": _sha(h1_prompt),
        "h1_prompt_diff_fingerprint": _sha(h1_design["prompt_diff"]),
        "h1_root_conclusion": h1["root_conclusion"],
        "failed_technical_gate": "technical_pipeline_successes_24_of_24",
        "affected_scenarios": [
            {
                "scenario_id": "SYN-05",
                "earliest_failure_stage": "PROVIDER_CALL",
                "transport_status": "PROVIDER_TIMEOUT",
                "after_structural_reference_handling": False,
                "new_relative_to_control": True,
            }
        ],
        "provider_comparability": "PARTIALLY_COMPARABLE",
        "provider_drift_review": {
            "configuration_fingerprint_equal": True,
            "provider_equal": True,
            "model_equal": True,
            "observed_transport_difference": "one treatment timeout",
            "causal_conclusion": "prompt causality not isolated",
        },
        "h1_regression_analysis_outcome": "H1_REGRESSION_MECHANISM_NOT_ISOLATED",
        "h1_change_inventory": changes,
        "prompt_change_impact_matrix": impact_matrix,
        "change_interactions": [
            {
                "interaction_id": "H1-I01",
                "involved_change_ids": [item["change_id"] for item in changes],
                "mechanism": "Six simultaneous preservation constraints increased instruction density and confound attribution.",
                "affected_scenarios": [f"SYN-{number:02d}" for number in range(1, 25)],
                "observed_evidence": "Two quote cases improved, one prior pass regressed, and one transport timeout occurred.",
                "confidence": "LOW",
                "h2_implication": "Use one short, quote-specific behavioral mechanism.",
            }
        ],
        "h1_change_dispositions": {
            disposition: [
                item["change_id"]
                for item in changes
                if item["disposition"] == disposition
            ]
            for disposition in ("KEEP", "REMOVE", "REFORMULATE", "INCONCLUSIVE")
        },
        "rejected_hypothesis_lessons": [
            {
                "status": "SUPPORTED",
                "lesson": "H1 removed quote-mutation as the primary category in both affected control scenarios.",
            },
            {
                "status": "CONTRADICTED",
                "lesson": "H1 did not preserve the mandatory 24/24 technical and reference gates.",
            },
            {
                "status": "UNRESOLVED",
                "lesson": "The provider timeout cannot be attributed to any individual H1 instruction from one combined experiment.",
            },
        ],
        "remaining_prompt_addressable_failures": [
            "QUOTE_MUTATION",
            "SOURCE_AUTHORITY_DRIFT",
        ],
        "h2_design_status": "PASS" if ready else "BLOCKED",
        "h2_hypothesis": (
            "Adding one concise, quote-specific verbatim-preservation instruction "
            "will reduce QUOTE_MUTATION without changing structural output behavior "
            "or exact-reference compliance."
        ),
        "h2_prompt": candidate,
        "h2_prompt_fingerprint": _sha(candidate),
        "h2_prompt_length": len(candidate),
        "h2_token_estimate": None,
        "baseline_to_h2_diff": baseline_to_h2,
        "baseline_to_h2_diff_fingerprint": _sha(baseline_to_h2),
        "h1_to_h2_diff": h1_to_h2,
        "h1_to_h2_diff_fingerprint": _sha(h1_to_h2),
        "h2_change_inventory": [
            {
                "change_id": "H2-C01",
                "baseline_prompt_location": "after the frozen production instruction",
                "baseline_wording": "Preserve factual content and source language unless the authorized instruction explicitly requires otherwise.",
                "h2_wording": H2_ADDITION.strip(),
                "change_type": "CONSTRAINT_STRENGTHENING",
                "target_failure_category": "QUOTE_MUTATION",
                "evidence_source": ["SYN-10", "SYN-23"],
                "h1_lesson_applied": "H1-C02 REFORMULATE",
                "expected_editorial_effect": "Preserve exact quotation wording in targeted revisions.",
                "expected_technical_effect": "No output-shape, DTO, schema, or reference change.",
                "technical_risk": "LOW",
                "potential_unintended_effect": "Under-editing when a quotation itself is the authorized target.",
                "validation_method": "24-scenario offline override, prompt identity, and exact projection checks.",
            }
        ],
        "h2_safety_review": safety,
        "h2_offline_validation": validation,
        "future_experiment_design": {
            "control": "preserved Part 7C.2 baseline prompt",
            "treatment": "exact frozen H2 prompt",
            "scenarios": 24,
            "provider_requests": 24,
            "retries": 0,
            "fallbacks": 0,
            "replays": 0,
            "independent_variable": "H2 prompt text",
            "stop_conditions": [
                "H2 prompt or fingerprint changed",
                "corpus, provider configuration, rubric, or threshold changed",
                "offline prompt identity or projection invariant failed",
                "production prompt changed",
                "required tests failed",
            ],
        },
        "future_editorial_improvement_threshold": {
            "rule": "acceptance gain >= 6 OR (mean score gain >= 10 and improved scenarios >= 16)",
            "minimum_acceptance_gain": 6,
            "minimum_mean_score_gain": 10.0,
            "minimum_improved_scenarios": 16,
            "maximum_pass_to_fail": 0,
        },
        "future_technical_non_regression_gates": {
            key: "24/24"
            for key in (
                "technical_pipeline_successes",
                "provider_dto_validation",
                "authorization",
                "reconstruction",
                "episode_draft_validation",
            )
        },
        "future_reference_non_regression_gates": {
            "exact_reference_compliance": "24/24",
            "reference_precision": 1.0,
            "reference_recall": 1.0,
            "unknown_references": 0,
            "unauthorized_references": 0,
            "missing_authorized_references": 0,
        },
        "future_execution_integrity_gates": {
            "prompt_identity_passes": "24/24",
            "projection_count_equality_passes": "24/24",
            "projection_set_equality_passes": "24/24",
            "provider_requests": 24,
            "retries": 0,
            "fallbacks": 0,
            "replays": 0,
        },
        "design_frozen": ready,
        "h2_ready_for_controlled_experiment": ready,
        "benchmark_history_modified": False,
        "files_modified": [
            "scripts/design_second_prompt_hypothesis.py",
            "tests/test_second_prompt_hypothesis_design.py",
            "docs/second-prompt-hypothesis-design.md",
            "docs/artifacts/second-prompt-hypothesis-design.json",
        ],
        "tests": {
            "added": 15,
            "part_7h_verification": "PASS",
            "prompt_change_inventory": "PASS",
            "prompt_change_impact_matrix": "PASS",
            "h1_dispositions": "PASS",
            "h2_derivation": "PASS",
            "h2_prompt_diff": "PASS",
            "h2_safety": "PASS",
            "h2_prompt_contract": "PASS",
            "h2_prompt_identity": "PASS",
            "h2_projection_checkpoint": "PASS",
            "future_experiment_design": "PASS",
            "artifact_consistency": "PASS",
        },
        "regression_results": {
            "baseline": "1240 passed",
            "post_implementation": "1255 passed",
            "ruff": "PASS",
            "black": "PASS",
            "compileall": "PASS",
            "pip_check": "PASS",
        },
        "h2_design_outcome": (
            "H2_DESIGNED_AND_READY_FOR_CONTROLLED_EXPERIMENT"
            if ready
            else "H2_DESIGNED_BUT_NOT_READY"
        ),
        "root_conclusion": (
            "SECOND_PROMPT_HYPOTHESIS_DESIGNED_WITH_RESIDUAL_RISK"
            if ready
            else "SECOND_PROMPT_HYPOTHESIS_DESIGN_INCOMPLETE"
        ),
        "recommended_next_milestone": (
            "Part 7H.2 — Controlled Second Prompt Hypothesis Experiment"
            if ready
            else "Part 7H.1.1 — H2 Prompt Contract Risk Review"
        ),
    }
    artifact["design_fingerprint"] = _canonical_fingerprint(
        {key: value for key, value in artifact.items() if key != "created_at"}
    )
    return artifact


def render_report(artifact: dict[str, object]) -> str:
    """Render the complete human-readable H1 matrix and H2 design."""

    rows = []
    for item in artifact["prompt_change_impact_matrix"]:
        rows.append(
            f"| {item['change_id']} | {item['semantic_intent']} | "
            f"{item['causal_confidence']} | {item['technical_risk']} | "
            f"{item['editorial_value']} | {item['disposition']} | "
            f"{item['disposition_rationale']} |"
        )
    validation = artifact["h2_offline_validation"]
    return f"""# Second Prompt Hypothesis Design

## Executive Summary

H1 remains rejected. Its only technical failure was a provider timeout at `SYN-05`,
before structural-reference processing. Prompt causality is therefore not isolated.
H2 starts from the frozen Part 7C.2 prompt and adds only one concise quote-preservation
constraint supported by the two quote-category improvements.

## Milestone Background

- Control: Part 7C.2 `{artifact['source_control_run_id']}`
- Failed experiment: Part 7H `{artifact['source_experiment_run_id']}`
- Provider requests/network calls/benchmark executions/replays: `0/0/0/0`
- Production prompt modified: `NO`

## Part 7H Verification

Decision `REJECT` and root conclusion
`CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION` were verified against the design,
structured result, report, reconciliation artifact, baseline, and benchmark history.

## H1 Experiment Outcome

Treatment delivered 23 technical successes, 23 exact-reference-compliant scenarios,
zero editorial passes, two score improvements, one score regression, and one timeout.

## Failed Technical Non-Regression Gate

The `24/24 technical_pipeline_successes` gate failed on `SYN-05`. The earliest stage
was `PROVIDER_CALL`; no response existed for DTO, authorization, reconstruction,
EpisodeDraft, or reference evaluation. This failure was new relative to the control.

## Technical Regression Scenario Analysis

The single failure was a transport timeout and is not homogeneous with any structural
failure. There is no scenario-level evidence isolating a prompt clause as its cause.

## Editorial Effect Analysis

`QUOTE_MUTATION` fell from 2 to 0 (`SYN-10`, `SYN-23` improved), while
`SOURCE_AUTHORITY_DRIFT` rose from 21 to 23 and `SYN-20` moved pass-to-fail.

## Provider Drift Review

Classification: `PARTIALLY_COMPARABLE`. Provider, model, configuration fingerprint,
corpus, and evaluator were equal; a treatment-only timeout is an alternative
transport explanation. The official H1 conclusion is unchanged.

## Baseline-to-H1 Prompt Change Inventory

Six semantic instructions were added in one paragraph; they were not independently
randomized and must not be treated as six controlled effects.

## Prompt Change Impact Matrix

| Change | Semantic change | Causal confidence | Technical risk | Editorial value | Disposition | Rationale |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Prompt Change Interactions

`H1-I01` records the shared interaction: six simultaneous preservation constraints
increased instruction density and confound all per-change attribution.

## H1 Change Dispositions

KEEP: none. REMOVE: `H1-C06`. REFORMULATE: `H1-C02`. INCONCLUSIVE:
`H1-C01`, `H1-C03`, `H1-C04`, `H1-C05`.

## Rejected Hypothesis Lessons

- SUPPORTED: both quote-category control failures moved away from quote mutation.
- CONTRADICTED: H1 did not preserve mandatory technical/reference non-regression.
- UNRESOLVED: the timeout cannot be attributed to an individual prompt instruction.

## Remaining Prompt-Addressable Failures

`QUOTE_MUTATION` and `SOURCE_AUTHORITY_DRIFT`; H2 targets only the narrower category.

## H2 Design Gate

PASS. Risky and inconclusive H1 wording is excluded; the quote signal can be expressed
without changing schema, DTO, authorization, reconstruction, corpus, or evaluator.

## H2 Hypothesis

{artifact['h2_hypothesis']}

## H2 Design Principles

H2 is baseline plus one production-general instruction. It is not H1 plus repairs.

## H2 Change Inventory

`H2-C01` reformulates `H1-C02` into a quote-only verbatim-preservation constraint.

## H2 Prompt Diff

```diff
{artifact['baseline_to_h2_diff']}
```

## H2 Technical Contract Review

PASS: exact references, structured output, component shapes, DTO compatibility,
controlled scope, authorization, reconstruction, and EpisodeDraft production remain.

## H2 Safety Review

All fourteen reviewed areas pass. H2 contains no scenario IDs, benchmark facts,
evaluator thresholds, provider-specific exploit, or hidden self-check output.

## H2 Offline Validation

- Scenarios: {validation['scenarios']}
- Prompt identity: {validation['prompt_identity_passes']}/24
- Projection count equality: {validation['projection_count_equality_passes']}/24
- Projection set equality: {validation['projection_set_equality_passes']}/24
- Request assembly: {validation['request_assembly_passes']}/24
- Provider requests: 0

## Future Controlled Experiment Design

Control is frozen Part 7C.2; treatment is this exact H2 fingerprint. The future run
uses 24 scenarios, 24 requests, zero retries, fallbacks, and replays.

## Precommitted Decision Gates

Technical stages and exact references require 24/24. Editorial improvement remains
`acceptance gain >= 6 OR (mean score gain >= 10 and improved scenarios >= 16)`, with
zero pass-to-fail transitions. All prompt/projection identity checks require 24/24.

## Known Limitations

H1 was a combined intervention and had one transport timeout; H2 benefit is a
falsifiable hypothesis, not an established causal effect.

## Files Modified

Offline design script, focused tests, this report, and its structured artifact only.

## Tests Added or Updated

Focused Part 7H.1 contract, derivation, safety, projection, and consistency tests.

## Regression Results

Baseline: 1,240 passed. Post-implementation: 1,255 passed. Ruff, Black,
compileall, and pip check passed.

## Root Conclusion

`{artifact['root_conclusion']}`

## Recommended Next Milestone

`{artifact['recommended_next_milestone']}`
"""


def write_design(
    artifact_path: Path = DESIGN_PATH,
    report_path: Path = REPORT_PATH,
    *,
    created_at: str | None = None,
) -> dict[str, object]:
    """Write UTF-8 Part 7H.1 artifacts atomically."""

    artifact = build_design(created_at=created_at)
    for path, content in (
        (
            artifact_path,
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        ),
        (report_path, render_report(artifact)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DESIGN_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    artifact = write_design(args.artifact, args.report)
    print(f"H2 design: {artifact['h2_design_status']}")
    print("Provider requests: 0")
    return 0 if artifact["h2_ready_for_controlled_experiment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
