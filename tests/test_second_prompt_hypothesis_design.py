"""Offline Part 7H.1 impact-matrix and H2 design tests."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from scripts.design_second_prompt_hypothesis import (
    DESIGN_PATH,
    H2_ADDITION,
    REPORT_PATH,
    _sha,
    build_design,
    h2_prompt,
    verify_evidence,
    write_design,
)
from scripts.run_controlled_prompt_effectiveness_experiment import (
    CANDIDATE_ADDITION,
    candidate_prompt,
    control_prompt,
)

CREATED_AT = "2026-07-28T14:00:00+00:00"


def _artifact():
    return build_design(created_at=CREATED_AT)


def test_all_part_7h_evidence_is_discoverable_and_consistent():
    evidence = verify_evidence()

    assert all(evidence["checks"].values())
    assert evidence["h1"]["candidate_decision"] == "REJECT"
    assert evidence["h1"]["root_conclusion"] == (
        "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION"
    )


def test_production_and_rejected_prompts_remain_frozen():
    evidence = verify_evidence()

    assert _sha(control_prompt()) == evidence["h1"]["control_prompt_fingerprint"]
    assert candidate_prompt() == control_prompt() + CANDIDATE_ADDITION
    assert _sha(candidate_prompt()) == evidence["h1"]["candidate_prompt_fingerprint"]


def test_every_material_h1_change_has_stable_unique_id_and_disposition():
    changes = _artifact()["h1_change_inventory"]

    assert [item["change_id"] for item in changes] == [
        f"H1-C{number:02d}" for number in range(1, 7)
    ]
    assert len({item["change_id"] for item in changes}) == len(changes)
    assert all(
        item["disposition"] in {"KEEP", "REMOVE", "REFORMULATE", "INCONCLUSIVE"}
        for item in changes
    )


def test_impact_matrix_preserves_every_h1_change():
    artifact = _artifact()

    assert artifact["prompt_change_impact_matrix"] == artifact["h1_change_inventory"]
    assert artifact["h1_change_dispositions"] == {
        "KEEP": [],
        "REMOVE": ["H1-C06"],
        "REFORMULATE": ["H1-C02"],
        "INCONCLUSIVE": ["H1-C01", "H1-C03", "H1-C04", "H1-C05"],
    }


def test_h2_is_derived_from_baseline_not_rejected_h1():
    artifact = _artifact()

    assert h2_prompt() == control_prompt() + H2_ADDITION
    assert artifact["h2_prompt"] == h2_prompt()
    assert artifact["h2_prompt"] != candidate_prompt()
    assert CANDIDATE_ADDITION not in artifact["h2_prompt"]


def test_h2_copies_no_removed_or_inconclusive_change_unchanged():
    artifact = _artifact()
    excluded = [
        item
        for item in artifact["h1_change_inventory"]
        if item["disposition"] in {"REMOVE", "INCONCLUSIVE"}
    ]

    assert all(item["h1_text"] not in artifact["h2_prompt"] for item in excluded)
    assert artifact["h2_change_inventory"][0]["h1_lesson_applied"] == (
        "H1-C02 REFORMULATE"
    )


def test_every_h2_change_has_evidence_and_lesson_mapping():
    changes = _artifact()["h2_change_inventory"]

    assert len(changes) == 1
    assert changes[0]["evidence_source"] == ["SYN-10", "SYN-23"]
    assert changes[0]["h1_lesson_applied"]
    assert changes[0]["target_failure_category"] == "QUOTE_MUTATION"


def test_h2_contains_no_benchmark_leakage_or_evaluator_thresholds():
    prompt = h2_prompt().casefold()

    assert "syn-" not in prompt
    assert "benchmark" not in H2_ADDITION.casefold()
    assert "acceptance" not in H2_ADDITION.casefold()
    assert "score" not in H2_ADDITION.casefold()
    assert "24/24" not in prompt


def test_h2_preserves_structural_reference_and_dto_contract_instructions():
    prompt = h2_prompt()

    for required in (
        "Return exactly one revision for every supplied editable component",
        "Copy each component_reference exactly",
        "Keep the component_type identical",
        "Include every required field",
        "JSON Schema serialization contract",
    ):
        assert required in prompt


def test_all_24_offline_requests_pass_identity_and_projection_checks():
    validation = _artifact()["h2_offline_validation"]

    assert len(build_synthetic_corpus()) == 24
    assert validation["scenarios"] == 24
    assert validation["prompt_identity_passes"] == 24
    assert validation["projection_count_equality_passes"] == 24
    assert validation["projection_set_equality_passes"] == 24
    assert validation["request_assembly_passes"] == 24
    assert validation["provider_requests"] == 0


def test_h2_fingerprint_and_diffs_are_deterministic():
    first = _artifact()
    second = _artifact()

    assert first["h2_prompt_fingerprint"] == second["h2_prompt_fingerprint"]
    assert (
        first["baseline_to_h2_diff_fingerprint"]
        == second["baseline_to_h2_diff_fingerprint"]
    )
    assert first["h1_to_h2_diff_fingerprint"] == second["h1_to_h2_diff_fingerprint"]
    assert first["design_fingerprint"] == second["design_fingerprint"]


def test_h2_safety_review_and_design_gate_pass():
    artifact = _artifact()

    assert set(artifact["h2_safety_review"].values()) == {"PASS"}
    assert artifact["h2_design_status"] == "PASS"
    assert artifact["design_frozen"] is True
    assert artifact["h2_ready_for_controlled_experiment"] is True


def test_future_experiment_has_frozen_non_regression_and_integrity_gates():
    artifact = _artifact()
    future = artifact["future_experiment_design"]

    assert future["provider_requests"] == 24
    assert future["retries"] == future["fallbacks"] == future["replays"] == 0
    assert set(artifact["future_technical_non_regression_gates"].values()) == {"24/24"}
    assert (
        artifact["future_reference_non_regression_gates"]["exact_reference_compliance"]
        == "24/24"
    )
    assert (
        artifact["future_execution_integrity_gates"]["prompt_identity_passes"]
        == "24/24"
    )


def test_written_json_and_markdown_matrix_agree(tmp_path: Path):
    artifact_path = tmp_path / "design.json"
    report_path = tmp_path / "design.md"
    written = write_design(artifact_path, report_path, created_at=CREATED_AT)
    loaded = json.loads(artifact_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert loaded == written
    for item in loaded["prompt_change_impact_matrix"]:
        assert item["change_id"] in report
        assert item["disposition"] in report
    assert "quote-preservation" in report
    assert "Provider requests: 0" in report


def test_checked_in_artifacts_match_canonical_builder():
    checked_in = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    expected = build_design(created_at=checked_in["created_at"])
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert checked_in == expected
    assert report == __import__(
        "scripts.design_second_prompt_hypothesis", fromlist=["render_report"]
    ).render_report(checked_in)
    assert checked_in["provider_requests"] == checked_in["network_calls"] == 0
    assert checked_in["benchmark_executions"] == checked_in["benchmark_replays"] == 0
