import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"docs/artifacts/semantic-admission-v2-staged-gate-f-feasibility-design-v1.json"


def test_stage_p_cannot_decide_admission_or_treat_empty_as_complete() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    stage=design["stage_p"]
    assert "Do not decide admission" in stage["task"]
    assert any("empty entries array cannot be COMPLETE" in item for item in stage["complete_invariants"])
    assert stage["coverage_decisions"]==["COMPLETE","INDETERMINATE"]


def test_deterministic_boundary_cannot_infer_or_repair() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    prohibited=design["deterministic_ledger_validation"]["prohibited_checks"]
    assert any("No inference" in item for item in prohibited)
    assert any("No semantic correction" in item for item in prohibited)
    assert design["deterministic_ledger_validation"]["failure"].endswith("Stage C is not called.")


def test_stage_c_audits_completeness_against_originals() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    stage=design["stage_c"]
    assert stage["ledger_trust"]=="UNTRUSTED_ASSISTIVE_EVIDENCE_ONLY"
    assert "never evidence of safety" in stage["omission_rule"]
    assert "original authority and candidate" in design["architecture"]["independence_rule"]


def test_call_ceiling_and_two_case_contract_are_bounded() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    assert design["call_ceiling"]=={"normal_candidate_maximum":2,"stage_p_failure_or_indeterminate_maximum":1,"two_case_probe_maximum":4,"retry_or_repair_calls":0,"unused_call_budget":"Never consumed after an earlier terminal abstention."}
    proof=design["bounded_proof_contract"]
    assert proof["case_ids"]==["HMCV1-SASC-01","HMCV1-SASC-10"]
    assert proof["maximum_provider_calls"]==4


def test_design_grants_no_implementation_or_inference_authority() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    assert all(value is False for value in design["authority"].values())
    assert design["gate_s_separate"]["included"] is False
