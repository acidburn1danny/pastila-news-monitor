"""Offline knowledge-guided H3 design and traceability tests."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.editorial_knowledge import (
    deserialize_knowledge_base,
    validate_knowledge_base,
)
from scripts.design_knowledge_guided_h3 import (
    DESIGN_PATH,
    H3_ADDITION,
    KNOWLEDGE_PATH,
    MANIFEST_PATH,
    REPORT_PATH,
    RISK_PATH,
    TRACE_PATH,
    build_h3_design,
    h3_prompt,
    render_report,
)
from scripts.run_controlled_prompt_effectiveness_experiment import control_prompt

ROOT = Path.cwd()


def _built():
    return build_h3_design(ROOT)


def test_knowledge_base_and_manifest_references_validate():
    knowledge = deserialize_knowledge_base(KNOWLEDGE_PATH)
    diagnostics = validate_knowledge_base(knowledge, ROOT)
    design, traceability, _ = _built()

    assert diagnostics.valid
    assert design["knowledge_validation"] == "PASS"
    assert (
        traceability["chains"][0]["supporting_manifest_path"]
        == MANIFEST_PATH.as_posix()
    )
    assert traceability["chains"][0]["supporting_manifest_fingerprint"]


def test_every_active_knowledge_entry_is_reviewed():
    knowledge = deserialize_knowledge_base(KNOWLEDGE_PATH)
    design, _, _ = _built()

    assert design["knowledge_entries_reviewed"] == 7
    assert len(knowledge.entries) == 8
    assert set(design["knowledge_review"]) == {
        f"EK-{number:03d}" for number in range(1, 8)
    }


def test_exactly_one_reusable_finding_is_selected():
    design, _, _ = _built()

    assert design["knowledge_entries_selected"] == ["EK-002"]
    assert sum(item["selected"] for item in design["selection_ranking"]) == 1
    assert "negative multi-criterion trade-off" in design["selection_reason"]


def test_traceability_chain_has_no_orphan_prompt_changes():
    design, traceability, _ = _built()
    chain = traceability["chains"][0]

    assert traceability["validation_status"] == "PASS"
    assert traceability["orphan_prompt_changes"] == 0
    assert len(traceability["chains"]) == len(design["prompt_changes"]) == 1
    assert chain["knowledge_entry_id"] == design["knowledge_entries_used"][0]
    assert chain["prompt_change_id"] == design["prompt_changes"][0]["change_id"]
    assert chain["supporting_scenarios"] == ["SYN-10", "SYN-20", "SYN-23"]


def test_h3_uses_one_balanced_preservation_mechanism():
    design, _, _ = _built()

    assert design["hypothesis_id"] == "H3"
    assert design["behavioral_mechanisms"] == 1
    assert design["prompt_changes"][0]["wording"] == H3_ADDITION.strip()
    assert "positive Net Editorial Utility" in design["hypothesis_statement"]


def test_h3_is_derived_from_production_baseline_not_h2():
    design, _, _ = _built()
    h2 = json.loads(
        Path("docs/artifacts/second-prompt-hypothesis-design.json").read_text(
            encoding="utf-8"
        )
    )

    assert h3_prompt() == control_prompt() + H3_ADDITION
    assert design["h3_prompt"] != h2["h2_prompt"]
    assert design["production_prompt_modified"] is False
    assert design["h2_prompt_modified"] is False


def test_prompt_delta_budget_is_exactly_one_and_valid():
    design, _, _ = _built()
    budget = design["prompt_delta_budget"]

    assert budget == {
        "independent_behavioral_mechanisms": 1,
        "documented_semantic_changes": 1,
        "undocumented_semantic_changes": 0,
        "budget_limit": 1,
        "budget_consumed": 1,
        "budget_exceeded": False,
        "validation_status": "PASS",
    }


def test_risk_assessment_is_bounded_and_evidence_specific():
    design, _, risk = _built()

    assert risk["regression_risk"] == "MEDIUM"
    assert risk["interaction_risk"] == "MEDIUM"
    assert risk["confidence"] == design["confidence"] == "LOW"
    assert risk["expected_affected_scenarios"] == ["SYN-10", "SYN-20", "SYN-23"]
    assert risk["expected_net_editorial_utility"] == 2
    assert "testable expectation" in risk["expected_utility_basis"]


def test_all_24_offline_assemblies_preserve_identity_and_projection():
    design, _, _ = _built()
    validation = design["offline_validation"]

    assert validation["scenarios"] == 24
    assert validation["prompt_identity_passes"] == 24
    assert validation["projection_count_equality_passes"] == 24
    assert validation["projection_set_equality_passes"] == 24
    assert validation["request_assembly_passes"] == 24
    assert validation["provider_requests"] == 0


def test_future_experiment_plan_has_fixed_request_budget():
    design, _, _ = _built()
    future = design["future_experiment_plan"]

    assert future["scenarios"] == future["provider_requests"] == 24
    assert future["retries"] == future["fallbacks"] == future["replays"] == 0
    assert design["h3_ready_for_future_controlled_experiment"] is True
    assert design["root_conclusion"] == "KNOWLEDGE_GUIDED_HYPOTHESIS_DESIGNED"


def test_design_is_strictly_offline_and_contains_no_benchmark_leakage():
    design, _, _ = _built()
    addition = H3_ADDITION.casefold()

    assert design["provider_requests"] == 0
    assert design["network_calls"] == 0
    assert design["benchmark_executions"] == 0
    assert design["benchmark_replays"] == 0
    assert "syn-" not in addition
    assert "benchmark" not in addition
    assert "score" not in addition


def test_checked_in_artifacts_and_report_match_builder():
    checked_design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    checked_trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    checked_risk = json.loads(RISK_PATH.read_text(encoding="utf-8"))
    expected = _built()

    assert (checked_design, checked_trace, checked_risk) == expected
    assert REPORT_PATH.read_text(encoding="utf-8") == render_report(*expected)
