from __future__ import annotations

import hashlib
import json
from pathlib import Path

ARTIFACT = Path("docs/artifacts/reference-contract-remediation-design.json")
REPORT = Path("docs/reference-contract-remediation-design.md")
V2 = Path("docs/artifacts/controlled-provider-quality-baseline-v2.json")
HISTORY = Path("docs/artifacts/controlled-provider-quality-history.json")


def _artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_architecture_artifact_has_required_contract_and_no_implementation() -> None:
    artifact = _artifact()
    required = {
        "schema_version",
        "milestone",
        "created_at",
        "candidate_families",
        "evaluation_matrix",
        "trade_offs",
        "failure_analysis",
        "security_analysis",
        "migration_analysis",
        "ranking",
        "preferred_candidate",
        "rejected_candidates",
        "root_conclusion",
        "final_recommendation",
    }
    assert required <= artifact.keys()
    assert artifact["implementation_included"] is False
    assert artifact["provider_requests"] == 0
    assert artifact["benchmark_executions"] == 0
    assert artifact["benchmark_replays"] == 0


def test_discovery_merges_equivalents_and_records_every_elimination() -> None:
    artifact = _artifact()
    discovery = artifact["discovery"]
    assert len(discovery["raw_ideas"]) == 10
    assert discovery["families_after_merge"] == 7
    assert len(discovery["equivalence_merges"]) == 2
    families = artifact["candidate_families"]
    assert len(families) == 7
    eliminated = [item for item in families if item["status"].startswith("ELIMINATED")]
    assert len(eliminated) == 3
    assert all(item["elimination_reason"] for item in eliminated)


def test_all_viable_candidates_use_the_same_mandatory_criteria() -> None:
    artifact = _artifact()
    criteria = artifact["evaluation_method"]["criteria"]
    matrix = artifact["evaluation_matrix"]
    assert len(criteria) == 19
    assert len(matrix) == 4
    assert all(len(item["scores"]) == len(criteria) for item in matrix)
    assert all(sum(item["scores"]) == item["total"] for item in matrix)
    assert all(all(1 <= score <= 5 for score in item["scores"]) for item in matrix)


def test_ranking_is_derived_and_dominance_is_explicit() -> None:
    artifact = _artifact()
    assert artifact["ranking"][0] == {
        "rank": 1,
        "candidate_id": "C2_DYNAMIC_EXACT_SCHEMA",
        "score": 85,
    }
    dominated = artifact["dominance_analysis"]
    assert {item["dominated"] for item in dominated} == {
        "E1_STATIC_REGISTRY_ENUM",
        "C3_OPAQUE_HANDLES",
    }
    assert all(item["dominant"] == "C2_DYNAMIC_EXACT_SCHEMA" for item in dominated)


def test_preferred_candidate_preserves_every_frozen_guarantee() -> None:
    artifact = _artifact()
    preferred = artifact["preferred_candidate"]
    assert preferred["candidate_id"] == "C2_DYNAMIC_EXACT_SCHEMA"
    guarantees = set(preferred["guarantees_preserved"])
    assert {
        "single request",
        "single authorization",
        "single reconstruction",
        "fail-closed runtime",
        "provider-neutral domain contract",
        "offline validation",
        "benchmark reproducibility",
    } <= guarantees
    assert artifact["root_conclusion"] == "SCHEMA_REMEDIATION_RECOMMENDED"
    assert artifact["final_recommendation"] == "IMPLEMENT_SELECTED_REFERENCE_CONTRACT"


def test_recommendation_matches_instrumented_benchmark_evidence() -> None:
    baseline = json.loads(V2.read_text(encoding="utf-8"))
    assert baseline["scenario_count"] == 24
    assert baseline["pipeline_funnel"]["pipeline_successes"] == 0
    assert baseline["reference_metrics"]["missing_scenarios"] == 24
    assert baseline["reference_metrics"]["exact_authorized_scenarios"] == 0
    assert baseline["root_conclusion"] == "PROVIDER_REFERENCE_CONTRACT_FAILURE"


def test_report_contains_every_required_architecture_section() -> None:
    report = REPORT.read_text(encoding="utf-8")
    sections = (
        "Executive Summary",
        "Problem Statement",
        "Evidence Summary",
        "Architectural Constraints",
        "Candidate Discovery",
        "Candidate Families",
        "Comparative Matrix",
        "Trade-off Analysis",
        "Failure Analysis",
        "Security Analysis",
        "Migration Analysis",
        "Candidate Ranking",
        "Recommended Architecture",
        "Rejected Alternatives",
        "Future Work",
        "Architecture Impact",
        "Root Conclusion",
        "Final Recommendation",
    )
    assert all(f"## {section}" in report for section in sections)


def test_architecture_artifacts_contain_no_patch_or_provider_content() -> None:
    payload = (
        ARTIFACT.read_text(encoding="utf-8") + REPORT.read_text(encoding="utf-8")
    ).casefold()
    forbidden = (
        "api_key",
        "bearer ",
        "provider response payload",
        "diff --git",
        "*** begin patch",
    )
    assert not any(value in payload for value in forbidden)


def test_frozen_benchmark_history_prefix_is_unchanged_after_append() -> None:
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    frozen_prefix = {**history, "history": history["history"][:2]}
    serialized = (
        json.dumps(frozen_prefix, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    assert (
        hashlib.sha256(serialized.encode()).hexdigest()
        == "21cfc66204ba1f86b575d3ed9b7ba3b28d9ee351bcb71c49ccf4b09d692fbc19"
    )
