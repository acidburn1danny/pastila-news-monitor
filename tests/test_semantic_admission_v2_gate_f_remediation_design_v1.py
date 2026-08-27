import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-remediation-design-v1.json"


def test_design_binds_run4_and_all_ten_acceptance_cases() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    assert design["source_run_identity"] == "5c7938c0029df9a0da46ff9235d40e351f2e7c0862e5da94de97789de265ed6e"
    cases = design["run4_case_contract"]
    assert [case["case_id"] for case in cases] == [f"HMCV1-SASC-{number:02d}" for number in range(1, 11)]
    expected_pass = [case["case_id"] for case in cases if case["required_gate_f"] == "PASS"]
    assert expected_pass == ["HMCV1-SASC-01", "HMCV1-SASC-02", "HMCV1-SASC-04"]


def test_design_protects_nonfactual_transformation_without_blanket_exemption() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    boundary = design["governing_boundary"]
    assert "PERSONIFICATION" in boundary["permitted_nonfactual_operations"]
    assert "returns to an unsupported proposition" in boundary["permission_limit"]
    prohibited = design["bounded_remediation_options"]["prohibited"]
    assert "LEXICAL_ALLOWLIST_FOR_METAPHOR" in prohibited
    assert "AUTOMATIC_PASS_FOR_COUNTERFACTUALS" in prohibited


def test_design_requires_exhaustive_embedded_proposition_evaluation() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    rule = design["governing_boundary"]["exhaustive_proposition_rule"]
    assert "presupposition, entailment, or necessary implication" in rule
    assert "cannot shield an unsupported real-world proposition" in rule
    classification = next(
        stage["requirement"]
        for stage in design["required_reasoning_sequence"]
        if stage["stage"] == "5_SEMANTIC_HEAD_CLASSIFICATION"
    )
    assert "every unsupported real-world proposition" in classification
    assert "rather than only the sentence's surface/main head" in classification


def test_gate_s_is_an_independent_non_authorized_track() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    gate_s = design["gate_s_separate_track"]
    assert gate_s["included_in_this_design"] is False
    assert len(gate_s["preserved_findings"]) == 2
    assert design["authority"] == {
        "implementation": False,
        "inference": False,
        "prompt_or_model_change": False,
        "runtime": False,
        "training": False,
        "curriculum_exposure": False,
    }
