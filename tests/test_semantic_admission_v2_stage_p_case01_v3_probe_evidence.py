import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.staged_gate_f_contract_v1 import PropositionLedgerV1,validate_source_membership


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-case01-v3-probe-evidence"
PACK=ROOT/"docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json"


def test_exactly_one_call_and_no_stage_c() -> None:
    result=json.loads((EVIDENCE/"probe-result.json").read_text("utf-8"))
    binding=json.loads((EVIDENCE/"identity-binding.json").read_text("utf-8"))
    assert result["provider_call_count"]==binding["maximum_provider_calls"]==1
    assert result["stage_c_constructed"] is result["stage_c_called"] is False
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False
    assert binding["retry_count"]==binding["repair_count"]==binding["selection_count"]==0


def test_terminal_raw_is_schema_valid_but_fails_source_membership() -> None:
    raw=(EVIDENCE/"stage-p-raw.bin").read_bytes()
    assert len(raw)==1462 and hashlib.sha256(raw).hexdigest()=="f37ed5f2c30a72fad91953f3a1f87f590685c0e4987c7efb3957cfac23ed8be8"
    ledger=PropositionLedgerV1.model_validate_json(raw,strict=True)
    case=json.loads(PACK.read_text("utf-8"))["cases"][0]
    assert ledger.coverage_decision.value=="INDETERMINATE"
    with pytest.raises(ValueError,match="CANDIDATE_SPAN_NOT_IN_CANDIDATE"):
        validate_source_membership(ledger,factual_summary=case["factual_summary"],candidate=case["candidate"])
    assert ledger.entries[0].candidate_span not in case["candidate"]
    assert ledger.entries[1].candidate_span in case["candidate"]


def test_validated_analysis_is_fail_closed_and_quarantined() -> None:
    value=json.loads((EVIDENCE/"validated-analysis.json").read_text("utf-8"))
    assert value["final_result"]=="FAIL_CLOSED_STAGE_P_SOURCE_MEMBERSHIP"
    assert value["transport"]["terminal_eos"] is True and value["raw_output"]["schema_validation"]=="PASS"
    assert value["source_membership_validation"]["reason_code"]=="CANDIDATE_SPAN_NOT_IN_CANDIDATE"
    assert value["durable_lifecycle"]["file_count"]==46
    assert all(item is False for item in value["authority"].values())
