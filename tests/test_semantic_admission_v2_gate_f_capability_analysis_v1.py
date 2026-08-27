import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"docs/artifacts/semantic-admission-v2-gate-f-v2-4-v2-5-capability-analysis-v1.json"


def test_analysis_separates_proven_observation_from_hypothesis() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    assert any("Case 10 changed" in item for item in design["proven_observations"])
    assert "Prompt length alone caused the unsafe PASS." in design["not_proven"]
    assert design["evidence"]["case_10_rendered_prompt_bytes"]["increase_percent"]==38.44


def test_analysis_stops_v25_and_does_not_promote_v24() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    dispositions=design["candidate_dispositions"]
    assert dispositions["v2_5"]=="STOP_UNSAFE_FALSE_PASS_NO_FURTHER_EXECUTION"
    assert dispositions["v2_4"]=="SAFER_EMPIRICAL_REFERENCE_ONLY_NOT_RUNTIME_ELIGIBLE"


def test_preferred_direction_separates_extraction_validation_and_classification() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    staged=design["preferred_staged_design"]
    assert "FSEM codes" in staged["stage_p_proposition_ledger"]["task"]
    assert "No semantic inference" in staged["deterministic_boundary"]["prohibited"]
    assert "must not treat ledger omission as proof of safety" in staged["stage_c_classification"]["safety_rule"]
    assert staged["call_cost"].startswith("Two model calls")


def test_analysis_grants_no_design_implementation_or_inference_authority() -> None:
    design=json.loads(SPEC.read_text("utf-8"))
    assert design["authority"]=={"staged_design":False,"candidate_implementation":False,"inference":False,"runtime":False,"training":False,"gate_s":False}
