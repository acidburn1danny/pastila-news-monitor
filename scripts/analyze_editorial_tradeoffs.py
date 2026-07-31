"""Build the offline Part 7H.2.2 causal editorial trade-off analysis."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from scripts.run_controlled_provider_quality_baseline import write_artifact_atomic

COMPARISON_PATH = Path("docs/artifacts/h2-scenario-comparison.json")
EXPERIMENT_PATH = Path(
    "docs/artifacts/controlled-second-prompt-hypothesis-experiment.json"
)
MANIFEST_PATH = Path("docs/artifacts/experiments/part-7h-2/experiment-manifest.json")
ANALYSIS_PATH = Path("docs/artifacts/causal-editorial-tradeoff-analysis.json")
MATRIX_PATH = Path("docs/artifacts/editorial-tradeoff-matrix.json")
GRAPH_PATH = Path("docs/artifacts/editorial-dependency-graph.json")
REPORT_PATH = Path("docs/causal-editorial-tradeoff-analysis.md")

CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"}
CLASSIFICATIONS = {
    "ELIMINATED",
    "REDUCED",
    "UNCHANGED",
    "INCREASED",
    "NEW",
    "NOT_PRESENT",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _classification(control: int, treatment: int) -> str:
    if control == treatment == 0:
        return "NOT_PRESENT"
    if control > 0 and treatment == 0:
        return "ELIMINATED"
    if 0 < treatment < control:
        return "REDUCED"
    if treatment == control:
        return "UNCHANGED"
    if control == 0 and treatment > 0:
        return "NEW"
    return "INCREASED"


def _relative_delta(control: int, treatment: int) -> float | None:
    return None if control == 0 else (treatment - control) / control


def build_analysis(*, created_at: str | None = None) -> tuple[dict, dict, dict]:
    """Construct all analysis artifacts from immutable paired evidence."""

    comparison = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))
    experiment = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scenarios = comparison["scenarios"]
    if (
        len(scenarios) != 24
        or experiment["candidate_decision"] != "REJECT"
        or experiment["root_conclusion"] != "H2_PROMPT_INEFFECTIVE"
        or manifest["manifest"]["manifest_fingerprint"]
        != "2a47289e42c0397277de3e4ee7b563131ded24a41697a539540b1c7feb822fd6"
    ):
        raise RuntimeError("frozen Part 7H.2 evidence mismatch")

    scenario_analysis = []
    control_counts: Counter[str] = Counter()
    treatment_counts: Counter[str] = Counter()
    removed_total = 0
    introduced_total = 0
    for pair in scenarios:
        control = set(pair["secondary_failure_categories_control"])
        treatment = set(pair["secondary_failure_categories_treatment"])
        removed = sorted(control - treatment)
        introduced = sorted(treatment - control)
        unchanged = sorted(control & treatment)
        control_counts.update(control)
        treatment_counts.update(treatment)
        removed_total += len(removed)
        introduced_total += len(introduced)
        scenario_analysis.append(
            {
                "scenario_id": pair["scenario_id"],
                "scenario_order": pair["scenario_order"],
                "baseline_primary_category": pair["primary_failure_category_control"],
                "treatment_primary_category": pair[
                    "primary_failure_category_treatment"
                ],
                "editorial_failures_removed": removed,
                "editorial_failures_introduced": introduced,
                "editorial_failures_unchanged": unchanged,
                "editorial_score_delta": pair["editorial_score_delta"],
                "acceptance_transition": pair["acceptance_transition"],
                "failure_category_transition": pair["failure_category_transition"],
                "quote_mutation_transition": pair["quote_mutation_transition"],
            }
        )

    categories = sorted(set(control_counts) | set(treatment_counts))
    cause_by_category = {
        "quote_preservation": (
            "Prompt wording",
            "MEDIUM",
            ["SYN-10", "SYN-23"],
            "Both preidentified quote failures disappeared under the quote-specific H2 instruction; one paired run cannot exclude provider stochasticity.",
        ),
        "editorial_acceptance": (
            "Prompt interaction",
            "LOW",
            ["SYN-20"],
            "The only control pass became a failure together with three underlying criterion regressions.",
        ),
        "instruction_compliance": (
            "Prompt interaction",
            "LOW",
            ["SYN-20"],
            "One new failure coincided with H2, but one provider sample cannot isolate wording from stochasticity.",
        ),
        "meaning_preservation": (
            "Prompt interaction",
            "LOW",
            ["SYN-20"],
            "One new failure coincided with H2, with provider stochasticity and benchmark variance remaining alternatives.",
        ),
        "source_authority_preservation": (
            "Prompt interaction",
            "LOW",
            ["SYN-20"],
            "One new failure coincided with H2; H1/H2 evidence does not independently isolate the mechanism.",
        ),
    }
    matrix_rows = []
    for category in categories:
        control = control_counts[category]
        treatment = treatment_counts[category]
        cause, confidence, evidence, explanation = cause_by_category.get(
            category,
            (
                "No observed change",
                "LOW",
                [],
                "Frequency was unchanged; no causal movement is inferred.",
            ),
        )
        matrix_rows.append(
            {
                "editorial_category": category,
                "baseline_frequency": control,
                "treatment_frequency": treatment,
                "absolute_delta": treatment - control,
                "relative_delta": _relative_delta(control, treatment),
                "classification": _classification(control, treatment),
                "evidence_count": len(evidence),
                "evidence_scenarios": evidence,
                "causal_confidence": confidence,
                "likely_cause": cause,
                "causal_explanation": explanation,
            }
        )

    primary_control = Counter(
        item["baseline_primary_category"]
        for item in scenario_analysis
        if item["baseline_primary_category"]
    )
    primary_treatment = Counter(
        item["treatment_primary_category"]
        for item in scenario_analysis
        if item["treatment_primary_category"]
    )
    primary_matrix = [
        {
            "editorial_category": category,
            "baseline_frequency": primary_control[category],
            "treatment_frequency": primary_treatment[category],
            "absolute_delta": primary_treatment[category] - primary_control[category],
            "relative_delta": _relative_delta(
                primary_control[category], primary_treatment[category]
            ),
            "classification": _classification(
                primary_control[category], primary_treatment[category]
            ),
        }
        for category in sorted(set(primary_control) | set(primary_treatment))
    ]
    matrix = {
        "schema_version": 1,
        "milestone": "Part 7H.2.2",
        "frequency_unit": "scenario-category failure",
        "net_change_convention": "treatment_frequency - baseline_frequency",
        "criterion_level_rows": matrix_rows,
        "primary_taxonomy_rows": primary_matrix,
    }
    graph = {
        "schema_version": 1,
        "milestone": "Part 7H.2.2",
        "observational_only": True,
        "nodes": sorted(set(categories) | {"QUOTE_MUTATION", "SOURCE_AUTHORITY_DRIFT"}),
        "edges": [
            {
                "source": "QUOTE_MUTATION",
                "target": "SOURCE_AUTHORITY_DRIFT",
                "label": "POSSIBLY_CAUSES",
                "evidence_scenarios": ["SYN-10", "SYN-23"],
                "confidence": "LOW",
                "interpretation": "Removing quote failure exposed an already-present authority failure as the primary category; it did not introduce the underlying criterion failures.",
            },
            {
                "source": "instruction_compliance",
                "target": "editorial_acceptance",
                "label": "LIKELY_CAUSES",
                "evidence_scenarios": ["SYN-20"],
                "confidence": "LOW",
                "interpretation": "The new instruction-compliance failure co-occurred with the only pass-to-fail transition.",
            },
            {
                "source": "meaning_preservation",
                "target": "editorial_acceptance",
                "label": "LIKELY_CAUSES",
                "evidence_scenarios": ["SYN-20"],
                "confidence": "LOW",
                "interpretation": "The new meaning-preservation failure co-occurred with the only pass-to-fail transition.",
            },
            {
                "source": "source_authority_preservation",
                "target": "editorial_acceptance",
                "label": "LIKELY_CAUSES",
                "evidence_scenarios": ["SYN-20"],
                "confidence": "LOW",
                "interpretation": "The new authority failure co-occurred with the only pass-to-fail transition.",
            },
        ],
    }
    causal_claims = [
        {
            "claim_id": "CAUSAL-01",
            "changed_category": "quote_preservation",
            "likely_cause": "Prompt wording",
            "confidence": "MEDIUM",
            "evidence": ["SYN-10", "SYN-23"],
            "counterevidence": "No factorial or repeated-provider trial isolates H2 from stochasticity.",
        },
        *[
            {
                "claim_id": f"CAUSAL-{number:02d}",
                "changed_category": category,
                "likely_cause": "Prompt interaction",
                "confidence": "LOW",
                "evidence": ["SYN-20"],
                "counterevidence": "A single paired response cannot exclude provider stochasticity or benchmark variance.",
            }
            for number, category in enumerate(
                (
                    "editorial_acceptance",
                    "instruction_compliance",
                    "meaning_preservation",
                    "source_authority_preservation",
                    "SOURCE_AUTHORITY_DRIFT",
                ),
                2,
            )
        ],
    ]
    confidence_counts = Counter(item["confidence"] for item in causal_claims)
    analysis = {
        "schema_version": 1,
        "milestone": "Part 7H.2.2 — Causal Editorial Trade-off Analysis",
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "source_experiment_id": experiment["experiment_id"],
        "source_manifest_fingerprint": manifest["manifest"]["manifest_fingerprint"],
        "evidence_fingerprints": {
            "experiment": _sha(EXPERIMENT_PATH),
            "scenario_comparison": _sha(COMPARISON_PATH),
            "experiment_manifest": _sha(MANIFEST_PATH),
        },
        "provider_requests": 0,
        "network_calls": 0,
        "benchmark_executions": 0,
        "benchmark_replays": 0,
        "scenarios_analyzed": len(scenario_analysis),
        "scenario_analysis": scenario_analysis,
        "h2_assessment": {
            "hypothesis_correct": True,
            "production_candidate": False,
            "reason": "QUOTE_MUTATION fell from 2 to 0, but acceptance fell from 1 to 0 and aggregate editorial improvement failed.",
        },
        "net_editorial_utility": {
            "formula": "resolved scenario-criterion failures - introduced scenario-criterion failures",
            "resolved_failures": removed_total,
            "new_failures": introduced_total,
            "net_utility": removed_total - introduced_total,
            "supplement_only": True,
        },
        "causal_claims": causal_claims,
        "causal_confidence_counts": {
            level: confidence_counts[level]
            for level in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE")
        },
        "hidden_tradeoffs": [
            {
                "type": "FAILURE_SUBSTITUTION",
                "finding": "QUOTE_MUTATION ceased to be primary in SYN-10 and SYN-23, exposing pre-existing SOURCE_AUTHORITY_DRIFT rather than curing those scenarios.",
            },
            {
                "type": "COMPENSATING_FAILURE",
                "finding": "SYN-20 introduced four criterion failures and became PASS_TO_FAIL, offsetting the two resolved quote-preservation failures.",
            },
            {
                "type": "CONSTRAINT_OVER_FITTING",
                "finding": "The quote-specific constraint improved its narrow target but did not generalize to aggregate editorial acceptance.",
            },
            {
                "type": "INSTRUCTION_COMPETITION",
                "finding": "Possible only: SYN-20 regressed in instruction compliance, meaning, and authority; one paired sample is insufficient for causal isolation.",
            },
            {
                "type": "PROMPT_SATURATION",
                "finding": "Not supported: H2 added one short mechanism and preserved technical behavior.",
            },
        ],
        "causal_narrative": "H2 successfully reduced observed quote mutation in both targeted control cases. Those cases still failed on pre-existing source-authority criteria, while SYN-20 newly failed four criteria and moved pass-to-fail. The trade-off prevented aggregate editorial improvement. Evidence for the targeted effect is medium; attribution of the SYN-20 regression is low-confidence because provider stochasticity and benchmark variance remain plausible.",
        "h3_design_guidance": {
            "prompt_addressable": [
                "quote_preservation remains prompt-responsive but cannot be optimized alone",
                "instruction compliance may be prompt-addressable with explicit trade-off protection",
            ],
            "architectural_candidates": [
                "independent editorial criterion gating before aggregate acceptance",
                "multi-objective experiment design for preservation interactions",
            ],
            "additional_evidence_required": [
                "SOURCE_AUTHORITY_DRIFT causal mechanism",
                "SYN-20 pass-to-fail reproducibility",
                "interaction between quote constraints and broader meaning preservation",
            ],
        },
        "matrix_path": str(MATRIX_PATH).replace("\\", "/"),
        "graph_path": str(GRAPH_PATH).replace("\\", "/"),
        "root_conclusion": "EDITORIAL_TRADE_OFFS_CHARACTERIZED",
        "recommended_next_milestone": "Part 7H.3 — Third Evidence-Derived Prompt Hypothesis",
    }
    return analysis, matrix, graph


def render_report(analysis: dict, matrix: dict, graph: dict) -> str:
    """Render the human-readable causal analysis."""

    rows = "\n".join(
        f"| {item['editorial_category']} | {item['baseline_frequency']} | {item['treatment_frequency']} | {item['absolute_delta']} | {item['classification']} | {item['causal_confidence']} | {item['likely_cause']} |"
        for item in matrix["criterion_level_rows"]
    )
    utility = analysis["net_editorial_utility"]
    return f"""# Causal Editorial Trade-off Analysis

## Scope and evidence

This offline analysis covers all 24 paired Part 7H.2 scenarios. It preserves the
official `REJECT` / `H2_PROMPT_INEFFECTIVE` decision and makes no provider requests.

## Scenario-level findings

Twenty-one scenarios had unchanged criterion failures. `SYN-10` and `SYN-23`
resolved `quote_preservation` but remained rejected under pre-existing authority,
meaning, and instruction failures. `SYN-20` introduced `editorial_acceptance`,
`instruction_compliance`, `meaning_preservation`, and
`source_authority_preservation`, moving `PASS_TO_FAIL`.

## Editorial trade-off matrix

| Category | Baseline | Treatment | Delta | Classification | Confidence | Likely cause |
|---|---:|---:|---:|---|---|---|
{rows}

Primary taxonomy movement is retained separately in the structured matrix. In the
two quote scenarios, `SOURCE_AUTHORITY_DRIFT` became primary because quote failure
was removed; the underlying authority criteria were already failing.

## Net Editorial Utility

Formula: resolved scenario-criterion failures minus introduced scenario-criterion
failures. Resolved: {utility['resolved_failures']}; introduced:
{utility['new_failures']}; net utility: {utility['net_utility']}.
This supplements but never replaces frozen editorial acceptance.

## Causal attribution and hidden trade-offs

The quote effect has `MEDIUM` confidence: both targeted paired cases improved, but
there was no repeated or factorial provider trial. The four SYN-20 regressions have
`LOW` confidence because prompt interaction, provider stochasticity, and benchmark
variance cannot be separated. Evidence supports failure substitution and a
compensating failure; prompt saturation is not supported.

## Observational dependency graph

The graph contains {len(graph['nodes'])} nodes and {len(graph['edges'])} observational
edges. Edges are labeled only `LIKELY_CAUSES` or `POSSIBLY_CAUSES` and retain scenario
evidence and uncertainty.

## H2 assessment

Hypothesis correct: **YES** under this corpus (`QUOTE_MUTATION` 2→0).
Production candidate: **NO** because acceptance decreased 1→0, mean score decreased,
and aggregate editorial improvement failed.

## H2 causal narrative

{analysis['causal_narrative']}

## H3 design guidance

H3 may address prompt-responsive preservation interactions, but this milestone does
not design it. Source-authority causality and SYN-20 reproducibility require more
evidence; independent criterion gating and multi-objective experiments are possible
architectural design-space items.

## Root conclusion

`{analysis['root_conclusion']}`

## Recommended next milestone

`{analysis['recommended_next_milestone']}`
"""


def write_analysis() -> tuple[dict, dict, dict]:
    """Write all four UTF-8 analysis artifacts."""

    analysis, matrix, graph = build_analysis()
    write_artifact_atomic(ANALYSIS_PATH, analysis)
    write_artifact_atomic(MATRIX_PATH, matrix)
    write_artifact_atomic(GRAPH_PATH, graph)
    REPORT_PATH.write_text(
        render_report(analysis, matrix, graph), encoding="utf-8", newline="\n"
    )
    return analysis, matrix, graph


if __name__ == "__main__":
    written, _, _ = write_analysis()
    print(f"Scenarios analyzed: {written['scenarios_analyzed']}")
    print("Provider requests: 0")
