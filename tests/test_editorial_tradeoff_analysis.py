"""Offline Part 7H.2.2 causal editorial trade-off analysis tests."""

from __future__ import annotations

import json

from scripts.analyze_editorial_tradeoffs import (
    ANALYSIS_PATH,
    CLASSIFICATIONS,
    CONFIDENCE,
    GRAPH_PATH,
    MATRIX_PATH,
    REPORT_PATH,
    _classification,
    build_analysis,
    render_report,
)


def _built():
    return build_analysis(created_at="2026-07-28T15:30:00+00:00")


def test_all_24_scenarios_are_analyzed_in_order():
    analysis, _, _ = _built()

    assert analysis["scenarios_analyzed"] == 24
    assert [item["scenario_id"] for item in analysis["scenario_analysis"]] == [
        f"SYN-{number:02d}" for number in range(1, 25)
    ]


def test_scenario_transitions_preserve_paired_evidence():
    analysis, _, _ = _built()
    changed = {
        item["scenario_id"]: item
        for item in analysis["scenario_analysis"]
        if item["editorial_failures_removed"] or item["editorial_failures_introduced"]
    }

    assert set(changed) == {"SYN-10", "SYN-20", "SYN-23"}
    assert changed["SYN-10"]["editorial_failures_removed"] == ["quote_preservation"]
    assert changed["SYN-23"]["editorial_failures_removed"] == ["quote_preservation"]
    assert changed["SYN-20"]["acceptance_transition"] == "PASS_TO_FAIL"
    assert len(changed["SYN-20"]["editorial_failures_introduced"]) == 4


def test_every_matrix_category_has_exact_classification_and_confidence():
    _, matrix, _ = _built()

    assert matrix["criterion_level_rows"]
    assert all(
        item["classification"] in CLASSIFICATIONS
        for item in matrix["criterion_level_rows"]
    )
    assert all(
        item["causal_confidence"] in CONFIDENCE
        for item in matrix["criterion_level_rows"]
    )
    assert len(
        {item["editorial_category"] for item in matrix["criterion_level_rows"]}
    ) == len(matrix["criterion_level_rows"])


def test_transition_classification_covers_required_states():
    assert _classification(2, 0) == "ELIMINATED"
    assert _classification(4, 2) == "REDUCED"
    assert _classification(2, 2) == "UNCHANGED"
    assert _classification(2, 3) == "INCREASED"
    assert _classification(0, 1) == "NEW"
    assert _classification(0, 0) == "NOT_PRESENT"


def test_net_editorial_utility_uses_criterion_transitions_without_double_counting():
    analysis, _, _ = _built()
    utility = analysis["net_editorial_utility"]

    assert utility["resolved_failures"] == 2
    assert utility["new_failures"] == 4
    assert utility["net_utility"] == -2
    assert utility["supplement_only"] is True


def test_h2_hypothesis_and_production_assessments_remain_independent():
    analysis, _, _ = _built()

    assert analysis["h2_assessment"]["hypothesis_correct"] is True
    assert analysis["h2_assessment"]["production_candidate"] is False
    assert analysis["root_conclusion"] == "EDITORIAL_TRADE_OFFS_CHARACTERIZED"


def test_dependency_graph_is_observational_and_internally_consistent():
    _, _, graph = _built()
    nodes = set(graph["nodes"])

    assert graph["observational_only"] is True
    assert all(
        item["source"] in nodes and item["target"] in nodes for item in graph["edges"]
    )
    assert all(
        item["label"] in {"LIKELY_CAUSES", "POSSIBLY_CAUSES", "INSUFFICIENT_EVIDENCE"}
        for item in graph["edges"]
    )
    assert all(item["confidence"] in CONFIDENCE for item in graph["edges"])


def test_causal_confidence_counts_reconcile_to_claims():
    analysis, _, _ = _built()
    counts = analysis["causal_confidence_counts"]

    assert counts == {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 5,
        "INSUFFICIENT_EVIDENCE": 0,
    }
    assert sum(counts.values()) == len(analysis["causal_claims"])


def test_analysis_is_strictly_offline_and_preserves_source_decision():
    analysis, _, _ = _built()

    assert analysis["provider_requests"] == 0
    assert analysis["network_calls"] == 0
    assert analysis["benchmark_executions"] == 0
    assert analysis["benchmark_replays"] == 0
    assert "H2_PROMPT_INEFFECTIVE" in REPORT_PATH.read_text(encoding="utf-8")


def test_checked_in_artifacts_match_canonical_analysis():
    checked_analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
    checked_matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    checked_graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    expected = build_analysis(created_at=checked_analysis["created_at"])

    assert (checked_analysis, checked_matrix, checked_graph) == expected
    assert REPORT_PATH.read_text(encoding="utf-8") == render_report(*expected)
