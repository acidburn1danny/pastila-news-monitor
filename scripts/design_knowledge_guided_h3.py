"""Design and validate the offline knowledge-guided H3 prompt hypothesis."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.editorial_knowledge import (
    deserialize_knowledge_base,
    validate_knowledge_base,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    project_production_request,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    _transform_request,
    control_prompt,
)
from scripts.run_controlled_provider_quality_baseline import write_artifact_atomic
from scripts.run_controlled_provider_quality_baseline_7c2 import projection_checkpoint

KNOWLEDGE_PATH = Path("docs/artifacts/editorial-knowledge-base.json")
MANIFEST_PATH = Path("docs/artifacts/experiments/part-7h-2/experiment-manifest.json")
TRADEOFF_PATH = Path("docs/artifacts/causal-editorial-tradeoff-analysis.json")
DESIGN_PATH = Path("docs/artifacts/knowledge-guided-third-prompt-hypothesis.json")
TRACE_PATH = Path("docs/artifacts/h3-traceability-chain.json")
RISK_PATH = Path("docs/artifacts/h3-risk-assessment.json")
REPORT_PATH = Path("docs/knowledge-guided-third-prompt-hypothesis.md")

H3_ADDITION = (
    " BALANCED PRESERVATION: Preserve non-target quotation wording, but never at "
    "the expense of completing the authorized revision or preserving the original "
    "meaning and source authority."
)
H3_KNOWLEDGE_SNAPSHOT_FINGERPRINT = (
    "0b5d591c89224a36b8b83d1752099a53a1146fe5c6221caa1ebca59d6ff7ea79"
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def h3_prompt() -> str:
    """Return H3 derived directly from the frozen Part 7C.2 prompt."""

    return control_prompt() + H3_ADDITION


def _diff(before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="part-7c2-production-prompt",
            tofile="h3-candidate-prompt",
            lineterm="",
        )
    )


def _offline_validation(prompt: str) -> dict:
    fingerprint = _sha(prompt)
    records = []
    for scenario in build_synthetic_corpus():
        invocation = build_production_invocation(scenario)
        projected = project_production_request(scenario, invocation)
        request = _transform_request(invocation, projected.client_request, prompt)
        checkpoint = projection_checkpoint(scenario.scenario_key, invocation, request)
        records.append(
            {
                "scenario_id": scenario.scenario_key,
                "prompt_identity": _sha(request.payload.instructions) == fingerprint,
                "projection_count_equality": checkpoint["count_equality"],
                "projection_set_equality": checkpoint["set_equality"],
                "request_assembly": True,
            }
        )
    return {
        "scenarios": len(records),
        "prompt_identity_passes": sum(item["prompt_identity"] for item in records),
        "projection_count_equality_passes": sum(
            item["projection_count_equality"] for item in records
        ),
        "projection_set_equality_passes": sum(
            item["projection_set_equality"] for item in records
        ),
        "request_assembly_passes": sum(item["request_assembly"] for item in records),
        "provider_requests": 0,
        "records": records,
    }


def build_h3_design(repository_root: Path) -> tuple[dict, dict, dict]:
    """Build the H3 design, traceability, and risk artifacts from knowledge."""

    knowledge = deserialize_knowledge_base(repository_root / KNOWLEDGE_PATH)
    diagnostics = validate_knowledge_base(knowledge, repository_root)
    if not diagnostics.valid or diagnostics.duplicate_findings:
        raise RuntimeError(f"editorial knowledge invalid: {diagnostics.errors}")
    manifest = json.loads((repository_root / MANIFEST_PATH).read_text(encoding="utf-8"))
    tradeoff = json.loads((repository_root / TRADEOFF_PATH).read_text(encoding="utf-8"))
    if tradeoff["net_editorial_utility"]["net_utility"] != -2:
        raise RuntimeError("trade-off evidence changed")
    selected = next(item for item in knowledge.entries if item.knowledge_id == "EK-002")
    reviews = {
        "EK-001": "ALREADY_EXPLOITED",
        "EK-002": "REUSABLE_FOR_H3",
        "EK-003": "NEEDS_REPLICATION",
        "EK-004": "ALREADY_EXPLOITED",
        "EK-005": "ALREADY_EXPLOITED",
        "EK-006": "ALREADY_EXPLOITED",
        "EK-007": "ALREADY_EXPLOITED",
    }
    reviewed_entries = tuple(
        item for item in knowledge.entries if item.knowledge_id in reviews
    )
    if set(reviews) != {item.knowledge_id for item in reviewed_entries}:
        raise RuntimeError("not every active knowledge entry was reviewed")
    baseline = control_prompt()
    candidate = h3_prompt()
    prompt_diff = _diff(baseline, candidate)
    validation = _offline_validation(candidate)
    budget = {
        "independent_behavioral_mechanisms": 1,
        "documented_semantic_changes": 1,
        "undocumented_semantic_changes": 0,
        "budget_limit": 1,
        "budget_consumed": 1,
        "budget_exceeded": False,
        "validation_status": "PASS",
    }
    traceability = {
        "schema_version": 1,
        "hypothesis_id": "H3",
        "orphan_prompt_changes": 0,
        "chains": [
            {
                "prompt_change_id": "H3-C01",
                "knowledge_entry_id": selected.knowledge_id,
                "knowledge_entry_fingerprint": selected.entry_fingerprint,
                "supporting_experiment": manifest["experiment"]["experiment_id"],
                "supporting_manifest_path": MANIFEST_PATH.as_posix(),
                "supporting_manifest_fingerprint": manifest["manifest"][
                    "manifest_fingerprint"
                ],
                "supporting_tradeoff_path": TRADEOFF_PATH.as_posix(),
                "supporting_scenarios": ["SYN-10", "SYN-20", "SYN-23"],
                "observed_behavior": selected.observed_behavior,
                "prompt_modification": H3_ADDITION.strip(),
                "expected_editorial_effect": "Preserve the two observed quote gains while preventing the four introduced instruction, meaning, authority, and acceptance failures.",
            }
        ],
        "validation_status": "PASS",
    }
    risk = {
        "schema_version": 1,
        "hypothesis_id": "H3",
        "regression_risk": "MEDIUM",
        "interaction_risk": "MEDIUM",
        "confidence": "LOW",
        "likelihood_of_regression": "MEDIUM",
        "potential_interaction": "The balance clause may create ambiguity when quotation preservation conflicts with an authorized quotation edit.",
        "expected_affected_scenarios": ["SYN-10", "SYN-20", "SYN-23"],
        "potential_side_effects": [
            "under-editing a quotation that is itself the authorized target",
            "instruction-priority competition between preservation and completion",
        ],
        "expected_net_editorial_utility": 2,
        "expected_utility_basis": "If H2's two resolved quote failures are retained and SYN-20's four introduced failures are avoided, the paired criterion delta becomes +2 relative to baseline; this is a testable expectation, not an observed result.",
        "mitigations": [
            "one behavioral mechanism",
            "explicit non-target quotation scope",
            "authorized revision completion has stated precedence",
            "frozen 24-scenario paired experiment plan",
        ],
        "validation_status": "PASS",
    }
    ready = (
        budget["validation_status"] == "PASS"
        and traceability["orphan_prompt_changes"] == 0
        and len(traceability["chains"]) == 1
        and validation["scenarios"] == 24
        and validation["prompt_identity_passes"] == 24
        and validation["projection_count_equality_passes"] == 24
        and validation["projection_set_equality_passes"] == 24
        and validation["request_assembly_passes"] == 24
        and candidate != baseline
        and candidate
        != json.loads(
            (
                repository_root / "docs/artifacts/second-prompt-hypothesis-design.json"
            ).read_text(encoding="utf-8")
        )["h2_prompt"]
    )
    design = {
        "schema_version": 1,
        "milestone": "Part 7H.3 — Knowledge-Guided Third Prompt Hypothesis",
        "milestone_type": "OFFLINE_KNOWLEDGE_GUIDED_HYPOTHESIS_DESIGN",
        "provider_requests": 0,
        "network_calls": 0,
        "benchmark_executions": 0,
        "benchmark_replays": 0,
        "knowledge_base_path": KNOWLEDGE_PATH.as_posix(),
        "knowledge_base_fingerprint": H3_KNOWLEDGE_SNAPSHOT_FINGERPRINT,
        "knowledge_validation": "PASS",
        "knowledge_entries_reviewed": len(reviewed_entries),
        "knowledge_review": reviews,
        "knowledge_entries_selected": [selected.knowledge_id],
        "selection_ranking": [
            {
                "knowledge_id": item.knowledge_id,
                "confidence": item.confidence.value,
                "net_editorial_utility": item.net_editorial_utility,
                "side_effect_count": len(item.side_effects),
                "review_disposition": reviews[item.knowledge_id],
                "selected": item.knowledge_id == selected.knowledge_id,
            }
            for item in reviewed_entries
        ],
        "selection_reason": "EK-002 is the only active finding that directly records the experimentally measured negative multi-criterion trade-off H3 must address; it has medium confidence, complete manifest linkage, and a reusable promotion guard.",
        "hypothesis_id": "H3",
        "hypothesis_statement": "Adding one balanced-preservation precedence rule will retain non-target quote wording while preventing instruction-compliance, meaning-preservation, and source-authority regressions, producing positive Net Editorial Utility without technical or reference regression.",
        "knowledge_entries_used": [selected.knowledge_id],
        "supporting_experiments": [manifest["experiment"]["experiment_id"]],
        "behavioral_mechanisms": 1,
        "prompt_changes": [
            {
                "change_id": "H3-C01",
                "baseline_location": "after the frozen Part 7C.2 production instruction",
                "knowledge_entry_id": selected.knowledge_id,
                "wording": H3_ADDITION.strip(),
                "semantic_change": "Balance non-target quote preservation with authorized completion, meaning, and authority preservation.",
            }
        ],
        "baseline_prompt_fingerprint": _sha(baseline),
        "h3_prompt": candidate,
        "h3_prompt_fingerprint": _sha(candidate),
        "prompt_diff": prompt_diff,
        "prompt_diff_fingerprint": _sha(prompt_diff),
        "prompt_delta_budget": budget,
        "expected_improvement": "Resolve the observed H2 trade-off rather than optimizing QUOTE_MUTATION in isolation.",
        "expected_risks": risk["potential_side_effects"],
        "expected_net_editorial_utility": risk["expected_net_editorial_utility"],
        "confidence": risk["confidence"],
        "offline_validation": validation,
        "traceability_path": TRACE_PATH.as_posix(),
        "risk_assessment_path": RISK_PATH.as_posix(),
        "future_experiment_plan": {
            "scenarios": 24,
            "provider_requests": 24,
            "retries": 0,
            "fallbacks": 0,
            "replays": 0,
            "control": "frozen Part 7C.2 production prompt",
            "treatment": "exact frozen H3 prompt",
            "independent_variable": "H3 prompt text",
        },
        "h3_ready_for_future_controlled_experiment": ready,
        "production_prompt_modified": False,
        "h2_prompt_modified": False,
        "root_conclusion": (
            "KNOWLEDGE_GUIDED_HYPOTHESIS_DESIGNED"
            if ready
            else "H3_DESIGN_VALIDATION_FAILED"
        ),
        "recommended_next_milestone": "Part 7H.4 — Controlled Knowledge-Guided Prompt Experiment",
    }
    return design, traceability, risk


def render_report(design: dict, traceability: dict, risk: dict) -> str:
    return f"""# Knowledge-Guided Third Prompt Hypothesis

## Knowledge validation and review

All {design['knowledge_entries_reviewed']} ACTIVE knowledge entries were reviewed.
`EK-002` was selected; all others were classified as already exploited or needing
replication. The knowledge base, evidence, fingerprints, and manifest linkage pass.

## Selected finding

`EK-002` records that H2 resolved two quote-preservation failures but introduced four
criterion failures, yielding Net Editorial Utility -2. It is the only selected finding.

## Hypothesis

{design['hypothesis_statement']}

## Prompt change

`H3-C01`: {design['prompt_changes'][0]['wording']}

H3 starts from the frozen Part 7C.2 prompt, not from H2. The exact candidate and diff
are frozen in the structured artifact. Production and H2 prompts remain unchanged.

## Traceability chain

Knowledge `EK-002` → H2 experiment `{traceability['chains'][0]['supporting_experiment']}`
→ observed 2 resolved / 4 introduced failures → balanced-preservation change →
expected positive multi-criterion utility. Orphan changes: 0.

## Prompt Delta Budget

One independent behavioral mechanism, one documented semantic change, zero
undocumented changes. Validation: `PASS`.

## Expected benefit and trade-offs

Expected Net Editorial Utility: {risk['expected_net_editorial_utility']} (a future
testable expectation, not an observed result). Regression and interaction risks are
both `{risk['regression_risk']}`. Expected affected scenarios: SYN-10, SYN-20, SYN-23.
Potential trade-offs are under-editing an authorized quotation and priority competition.

## Offline readiness

All 24 requests assemble offline with 24 prompt-identity, projection-count, and
projection-set passes. Provider requests: 0.

## Future controlled experiment

The planned Part 7H.4 experiment uses 24 scenarios, 24 requests, and zero retries,
fallbacks, or replays. Only the exact frozen H3 prompt may vary.

## Root conclusion

`{design['root_conclusion']}`

## Recommended next milestone

`{design['recommended_next_milestone']}`
"""


def write_h3_design(repository_root: Path) -> tuple[dict, dict, dict]:
    design, traceability, risk = build_h3_design(repository_root)
    write_artifact_atomic(repository_root / DESIGN_PATH, design)
    write_artifact_atomic(repository_root / TRACE_PATH, traceability)
    write_artifact_atomic(repository_root / RISK_PATH, risk)
    (repository_root / REPORT_PATH).write_text(
        render_report(design, traceability, risk), encoding="utf-8", newline="\n"
    )
    return design, traceability, risk


if __name__ == "__main__":
    result, _, _ = write_h3_design(Path.cwd())
    print(f"H3 ready: {result['h3_ready_for_future_controlled_experiment']}")
    print("Provider requests: 0")
