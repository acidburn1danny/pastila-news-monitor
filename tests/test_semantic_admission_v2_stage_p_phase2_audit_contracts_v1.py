from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    SourceRoleV1,
    SourceSpanReferenceV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_audit_contracts_v1 import (
    AxisDecision,
    AuthorityDecision,
    AuthorityReconciliationAuditResponseV1,
    AuthorityReconciliationRecordV1,
    CommitmentDecision,
    CommitmentReason,
    CommitmentSpanAuditResponseV1,
    CommitmentSpanAuditReceiptV1,
    CommitmentSpanRecordV1,
    ControllerStatus,
    CoverageStatus,
    FindingStatus,
    ParseStatus,
    UnsupportedFindingV1,
    build_authority_reconciliation_receipt_v1,
    build_commitment_span_receipt_v1,
    canonical_audit_receipt_bytes_v1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE01_REQUEST = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_request.json"
CASE01_LEDGER = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_ledger.json"
IDENTITY = "a" * 64


def _commitment_record(entry_id: str, decision: CommitmentDecision) -> CommitmentSpanRecordV1:
    reasons = {
        CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT: None,
        CommitmentDecision.COMMITMENT_EXCEEDS_SPAN: CommitmentReason.COMMITMENT_EXCEEDS,
        CommitmentDecision.SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING:
            CommitmentReason.MATERIAL_UNRECONCILED,
        CommitmentDecision.ENTRY_ROLE_MISCLASSIFIED: CommitmentReason.ROLE_MISCLASSIFIED,
        CommitmentDecision.UNRESOLVED_FAIL_CLOSED: CommitmentReason.UNRESOLVED,
    }
    return CommitmentSpanRecordV1(
        entry_id=entry_id, decision=decision, assertion_checked=True,
        presupposition_checked=True, entailment_checked=True,
        necessary_implication_checked=True, reason_code=reasons[decision], basis="Audit basis.")


def _commitment_receipt(response: CommitmentSpanAuditResponseV1, expected=("P1", "P2")):
    return build_commitment_span_receipt_v1(
        raw_response=canonical_audit_receipt_bytes_v1(response), response=response,
        expected_entry_ids=expected, request_identity=IDENTITY, prompt_identity=IDENTITY,
        model_identity="evaluation-model", grammar_identity=IDENTITY, elapsed_ms=1.0)


def test_captured_case01_shaped_span_excess_fails_without_repair() -> None:
    request = json.loads(CASE01_REQUEST.read_text("utf-8"))
    ledger = json.loads(CASE01_LEDGER.read_text("utf-8"))
    assert hashlib.sha256(request["candidate"].encode()).hexdigest() == "52a54bad5c68d16bd326c9dac8c544b5c4b0a45b9129262a0da139167362682b"
    assert ledger["entries"][1]["candidate_span_ref"]["end_utf8"] == 40
    response = CommitmentSpanAuditResponseV1(records=(
        _commitment_record("P1", CommitmentDecision.COMMITMENT_EXCEEDS_SPAN),
        _commitment_record("P2", CommitmentDecision.COMMITMENT_EXCEEDS_SPAN),
    ))
    receipt = _commitment_receipt(response)
    assert receipt.derived_status is ControllerStatus.FAIL
    assert receipt.derived_reason_code == CommitmentReason.COMMITMENT_EXCEEDS.value
    assert receipt.records == response.records


def test_commitment_controller_derives_pass_indeterminate_and_coverage_failure() -> None:
    passed = CommitmentSpanAuditResponseV1(records=(
        _commitment_record("P1", CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT),
        _commitment_record("P2", CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT),
    ))
    assert _commitment_receipt(passed).derived_status is ControllerStatus.PASS
    unresolved = CommitmentSpanAuditResponseV1(records=(
        _commitment_record("P1", CommitmentDecision.UNRESOLVED_FAIL_CLOSED),
        _commitment_record("P2", CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT),
    ))
    assert _commitment_receipt(unresolved).derived_status is ControllerStatus.INDETERMINATE
    reversed_receipt = _commitment_receipt(
        CommitmentSpanAuditResponseV1(records=tuple(reversed(passed.records))))
    assert reversed_receipt.derived_status is ControllerStatus.FAIL
    assert reversed_receipt.derived_reason_code == "CSPAN_RECORD_COVERAGE_MISMATCH"


def test_commitment_tuple_and_parse_failure_are_fail_closed() -> None:
    with pytest.raises(ValidationError, match="COMMITMENT_SPAN_DECISION_REASON_INCOHERENT"):
        CommitmentSpanRecordV1(
            entry_id="P1", decision=CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT,
            assertion_checked=True, presupposition_checked=True, entailment_checked=True,
            necessary_implication_checked=True, reason_code=CommitmentReason.UNRESOLVED,
            basis="Invalid tuple.")
    receipt = build_commitment_span_receipt_v1(
        raw_response=b"not-json", response=None, expected_entry_ids=("P1",),
        request_identity=IDENTITY, prompt_identity=IDENTITY, model_identity="evaluation-model",
        grammar_identity=IDENTITY, elapsed_ms=1.0, error_code="JSON_INVALID")
    assert receipt.derived_status is ControllerStatus.FAIL
    assert receipt.records == ()


def _reference(role: SourceRoleV1, digest: str = IDENTITY) -> SourceSpanReferenceV1:
    return SourceSpanReferenceV1(
        source_role=role, source_sha256=digest, start_utf8=0, end_utf8=10)


def _authority_receipt(response: AuthorityReconciliationAuditResponseV1, expected=("P1",)):
    return build_authority_reconciliation_receipt_v1(
        raw_response=canonical_audit_receipt_bytes_v1(response), response=response,
        expected_entry_ids=expected, request_identity=IDENTITY, prompt_identity=IDENTITY,
        model_identity="evaluation-model", grammar_identity=IDENTITY, elapsed_ms=1.0)


def test_supported_authority_tuple_passes_with_exact_reference() -> None:
    response = AuthorityReconciliationAuditResponseV1(records=(
        AuthorityReconciliationRecordV1(
            entry_id="P1", full_authority_compared=True,
            decision=AuthorityDecision.GOVERNED_SUPPORTED,
            authority_support_ref=_reference(SourceRoleV1.FACTUAL_AUTHORITY),
            event_axis=AxisDecision.MATCH, modality_axis=AxisDecision.MATCH,
            timing_axis=AxisDecision.MATCH, unsupported_finding_ids=(), basis="Authority supports it."),
    ), unsupported_findings=())
    receipt = _authority_receipt(response)
    assert receipt.derived_status is ControllerStatus.PASS
    assert receipt.source_projection_status.value == "PASS"


def test_unsupported_authority_tuple_requires_linked_decisive_finding() -> None:
    finding = UnsupportedFindingV1(
        finding_id="F1", entry_id="P1",
        candidate_proposition_ref=_reference(SourceRoleV1.CANDIDATE),
        reason_code="FSEM_TIMING_MUTATION", reason_status=FindingStatus.DECISIVE,
        basis="Candidate timing exceeds authority.")
    response = AuthorityReconciliationAuditResponseV1(records=(
        AuthorityReconciliationRecordV1(
            entry_id="P1", full_authority_compared=True,
            decision=AuthorityDecision.UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION,
            authority_support_ref=None, event_axis=AxisDecision.MATCH,
            modality_axis=AxisDecision.MATCH, timing_axis=AxisDecision.MUTATION,
            unsupported_finding_ids=("F1",), basis="Unsupported timing mutation."),
    ), unsupported_findings=(finding,))
    receipt = _authority_receipt(response)
    assert receipt.derived_status is ControllerStatus.FAIL
    assert receipt.unsupported_findings == (finding,)
    with pytest.raises(ValidationError, match="DECISIVE_FINDING_REQUIRED"):
        AuthorityReconciliationAuditResponseV1(
            records=response.records,
            unsupported_findings=(finding.model_copy(update={"reason_status": FindingStatus.SUPPORTING}),))


def test_zero_real_world_entry_path_is_deterministic_and_model_free() -> None:
    receipt = build_authority_reconciliation_receipt_v1(
        raw_response=b"", response=None, expected_entry_ids=(), request_identity=IDENTITY,
        prompt_identity=IDENTITY, model_identity="evaluation-model", grammar_identity=IDENTITY,
        elapsed_ms=0.0)
    assert receipt.derived_status is ControllerStatus.PASS
    assert receipt.deterministic_no_entries is True
    assert receipt.derived_reason_code == "AREC_NO_REAL_WORLD_COMMITMENTS"
    with pytest.raises(ValueError, match="ZERO_ENTRY_PATH"):
        build_authority_reconciliation_receipt_v1(
            raw_response=b"unexpected", response=None, expected_entry_ids=(),
            request_identity=IDENTITY, prompt_identity=IDENTITY,
            model_identity="evaluation-model", grammar_identity=IDENTITY, elapsed_ms=0.0)


def test_authority_coverage_and_source_projection_fail_closed() -> None:
    response = AuthorityReconciliationAuditResponseV1(records=(
        AuthorityReconciliationRecordV1(
            entry_id="P1", full_authority_compared=True,
            decision=AuthorityDecision.GOVERNED_SUPPORTED,
            authority_support_ref=_reference(SourceRoleV1.FACTUAL_AUTHORITY),
            event_axis=AxisDecision.MATCH, modality_axis=AxisDecision.MATCH,
            timing_axis=AxisDecision.MATCH, unsupported_finding_ids=(), basis="Supported."),
    ), unsupported_findings=())
    mismatch = _authority_receipt(response, expected=("P2",))
    assert mismatch.derived_reason_code == "AREC_RECORD_COVERAGE_MISMATCH"
    projection = build_authority_reconciliation_receipt_v1(
        raw_response=canonical_audit_receipt_bytes_v1(response), response=response,
        expected_entry_ids=("P1",), request_identity=IDENTITY, prompt_identity=IDENTITY,
        model_identity="evaluation-model", grammar_identity=IDENTITY, elapsed_ms=1.0,
        source_projection_pass=False)
    assert projection.derived_reason_code == "AREC_SOURCE_PROJECTION_FAILURE"


def test_receipt_models_reject_direct_state_bypass() -> None:
    record = _commitment_record("P1", CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT)
    with pytest.raises(ValidationError, match="COMMITMENT_RECEIPT_STATE_INCOHERENT"):
        CommitmentSpanAuditReceiptV1(
            request_identity=IDENTITY, prompt_identity=IDENTITY,
            model_identity="evaluation-model", grammar_identity=IDENTITY,
            raw_response_sha256=IDENTITY, expected_entry_ids=("P1",),
            parse_status=ParseStatus.FAIL, record_coverage_status=CoverageStatus.PASS,
            records=(record,), derived_status=ControllerStatus.PASS,
            derived_reason_code=None, elapsed_ms=1.0,
            error_code=None)
