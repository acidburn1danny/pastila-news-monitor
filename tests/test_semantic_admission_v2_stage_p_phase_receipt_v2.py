import hashlib
import json

from pastila_scout.semantic_admission_v2.stage_p_phase_receipt_v2 import classify_persisted_stage_p_v2,execute_and_capture_stage_p_v2


def test_synthetic_raw_keeps_bytes_and_classifies_membership_not_provider(tmp_path) -> None:
    raw=b'{"candidate_span":"outside"}';path=tmp_path/"raw.bin";path.write_bytes(raw)
    receipt=classify_persisted_stage_p_v2(raw_path=path,provider_called=True,transport_succeeded=True,
        schema_validator=json.loads,
        membership_validator=lambda _value:(_ for _ in ()).throw(ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")))
    assert receipt.transport.value==receipt.raw_persistence.value==receipt.schema_validation.value=="SUCCESS"
    assert receipt.source_membership.value=="FAIL"
    assert receipt.reason_code=="STAGE_P_CANDIDATE_SPAN_SOURCE_MEMBERSHIP_FAILURE"
    assert receipt.raw_bytes==len(raw) and receipt.raw_sha256==hashlib.sha256(raw).hexdigest()
    assert receipt.final_decision=="ABSTAIN_FAIL_CLOSED"


def test_schema_failure_preserves_raw_and_does_not_run_membership(tmp_path) -> None:
    raw=tmp_path/"raw.bin";raw.write_bytes(b"{}")
    receipt=classify_persisted_stage_p_v2(raw_path=raw,provider_called=True,transport_succeeded=True,
        schema_validator=lambda _raw:(_ for _ in ()).throw(ValueError("bad")),membership_validator=lambda _:None)
    assert receipt.raw_persistence.value=="SUCCESS" and receipt.raw_bytes==2
    assert receipt.schema_validation.value=="FAIL" and receipt.source_membership.value=="NOT_RUN"
    assert receipt.reason_code=="STAGE_P_SCHEMA_VALIDATION_FAILURE"


def test_transport_and_missing_raw_are_distinct(tmp_path) -> None:
    never=lambda _:None
    transport=classify_persisted_stage_p_v2(raw_path=None,provider_called=True,transport_succeeded=False,
        schema_validator=never,membership_validator=never)
    missing=classify_persisted_stage_p_v2(raw_path=tmp_path/"absent",provider_called=True,transport_succeeded=True,
        schema_validator=never,membership_validator=never)
    assert transport.reason_code=="STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE"
    assert missing.reason_code=="STAGE_P_RAW_PERSISTENCE_FAILURE"


def test_execute_calls_once_persists_before_membership_and_keeps_raw(tmp_path) -> None:
    calls=[];raw='{"ok":true}'
    def evaluator(request): calls.append(request);return raw
    receipt=execute_and_capture_stage_p_v2(evaluator=evaluator,request={"case":"01"},raw_path=tmp_path/"raw.bin",
        schema_validator=lambda data:json.loads(data),
        membership_validator=lambda _value:(_ for _ in ()).throw(ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")))
    assert calls==[{"case":"01"}]
    assert (tmp_path/"raw.bin").read_text("utf-8")==raw
    assert receipt.transport.value==receipt.raw_persistence.value==receipt.schema_validation.value=="SUCCESS"
    assert receipt.source_membership.value=="FAIL" and receipt.raw_bytes==len(raw)
