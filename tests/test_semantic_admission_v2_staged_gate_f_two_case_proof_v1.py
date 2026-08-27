import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-staged-gate-f-two-case-proof-v1-evidence"


def test_run_consumed_two_calls_without_retry_or_stage_c() -> None:
    run=json.loads((EVIDENCE/"raw-run-receipts.json").read_text("utf-8"))
    assert run["provider_call_count"]==2
    assert run["retry_count"]==run["repair_count"]==run["selection_count"]==0
    assert all(item["stage_c"]["called"] is False for item in run["receipts"])
    assert all(item["calls_consumed"]==1 and item["unused_call_budget"]==1 for item in run["receipts"])


def test_both_cases_failed_safe_on_stage_p_transport_timeout() -> None:
    run=json.loads((EVIDENCE/"raw-run-receipts.json").read_text("utf-8"))
    assert [item["case_id"] for item in run["receipts"]]==["HMCV1-SASC-01","HMCV1-SASC-10"]
    assert all(item["final_decision"]=="ABSTAIN" for item in run["receipts"])
    assert all(item["precedence_reason"]=="STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE" for item in run["receipts"])
    assert all(240000 <= item["stage_p"]["elapsed_ms"] < 241000 for item in run["receipts"])


def test_acceptance_failed_and_inference_state_is_not_overclaimed() -> None:
    summary=json.loads((EVIDENCE/"evaluation-summary.json").read_text("utf-8"))
    assert summary["proof_result"]=="FAIL" and summary["semantic_result"]=="NOT_OBSERVED"
    assert summary["runner_inference_state"].startswith("UNKNOWN_AFTER_TIMEOUT")
    assert summary["host_trace_initial_inference_started_false_is_not_PROOF_OF_NO_RUNNER_INFERENCE"] is True
    assert summary["runtime_authority"] is summary["training_authority"] is False
