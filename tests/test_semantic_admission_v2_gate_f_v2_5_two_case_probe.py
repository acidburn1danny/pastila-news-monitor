import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_v25_probe_is_exactly_two_gate_f_calls() -> None:
    plan=json.loads((ROOT/"docs/artifacts/semantic-admission-v2-gate-f-v2-5-two-case-probe-v1.json").read_text("utf-8"))
    assert plan["case_ids"]==["HMCV1-SASC-01","HMCV1-SASC-10"]
    assert plan["maximum_provider_calls"]==2 and plan["attempts_per_case"]==1
    assert plan["raw_capture_boundary"]=="PROVIDER_RESULT_BEFORE_SEMANTIC_SPAN_VALIDATION"
    assert plan["gate_s_included"] is False


def test_v25_runner_persists_provider_raw_before_adapter_validation() -> None:
    source=(ROOT/"scripts/run_semantic_admission_v2_gate_f_v2_5_two_case_probe_v1.py").read_text("utf-8")
    assert "DurableProviderCaptureV1" in source
    assert "_write(self.path, self.ledger)" in source
    assert "adapter_exception" in source
    assert '"repair_count":0' in source and '"gate_s_included":False' in source


def test_sealed_v25_probe_records_unsafe_false_pass_and_stops() -> None:
    path=ROOT/".semantic-admission-v2-gate-f-v2-5-contract-probe-v1-evidence/evaluation-summary.json"
    if not path.exists():
        return
    summary=json.loads(path.read_text("utf-8"))
    assert summary["case_results"][0]["result"]=="EXACT_PASS"
    assert summary["case_results"][1]["result"]=="UNSAFE_FALSE_PASS"
    assert summary["unsafe_false_pass_count"]==1
    assert summary["full_ten_case_run_eligible"] is False
    assert summary["v2_5_candidate_eligible_for_further_execution"] is False
