import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-evidence-trace-remediation-v1-evidence"
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-evidence-trace-remediation-v1-candidate.json"


def test_case01_receipt_preserves_raw_and_exact_failure_phase() -> None:
    value=json.loads((EVIDENCE/"case01-phase-receipt-v2.json").read_text("utf-8"))
    assert value["transport"]==value["raw_persistence"]==value["schema_validation"]=="SUCCESS"
    assert value["source_membership"]=="FAIL"
    assert value["raw_bytes"]==1462 and value["reason_code"]=="STAGE_P_CANDIDATE_SPAN_SOURCE_MEMBERSHIP_FAILURE"


def test_case01_lifecycle_reconciliation_corrects_generic_phase_view() -> None:
    value=json.loads((EVIDENCE/"case01-lifecycle-reconciliation-v1.json").read_text("utf-8"))
    assert value["reconciliation_status"]=="VALID" and value["file_count"]==46
    assert value["model_load"]==value["generation"]==value["terminal_eos"]==value["response_persisted"]=="OBSERVED"
    assert value["host_timeout"]=="NOT_OBSERVED_BEFORE_TERMINAL_EVENT"


def test_candidate_stops_before_prompt_decoder_or_model() -> None:
    value=json.loads(CANDIDATE.read_text("utf-8"))
    assert value["implemented_tracks"]==["TRACK_B_EVIDENCE_RECEIPT_SEPARATION","TRACK_C_TRACE_LIFECYCLE_RECONCILIATION"]
    assert value["verification"]["new_model_calls"]==0 and value["verification"]["inference"] is False
    assert all(item is False for item in value["authority"].values())
