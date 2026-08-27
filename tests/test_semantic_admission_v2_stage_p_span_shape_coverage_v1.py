from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2,
)
from pastila_scout.semantic_admission_v2.stage_p_span_shape_coverage_v1 import (
    AuditStatus,
    CoverageDisposition,
    PhaseReceiptInputV1,
    PhaseStatus,
    REQUIRED_PHASES,
    SpanShapeReason,
    build_span_shape_receipt_v1,
    canonical_receipt_bytes_v1,
    derive_coverage_receipt_v1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE01_REQUEST = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_request.json"
CASE01_LEDGER = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_ledger.json"
IDENTITY = "a" * 64


def _captured() -> tuple[dict[str, str], dict[str, object], ConstructionObligationLedgerV2]:
    request = json.loads(CASE01_REQUEST.read_text("utf-8"))
    ledger_bytes = CASE01_LEDGER.read_bytes().rstrip(b"\r\n")
    value = json.loads(ledger_bytes)
    return request, value, ConstructionObligationLedgerV2.model_validate_json(ledger_bytes)


def _source(request: dict[str, str]) -> ImmutableUtf8SourceV1:
    return ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE,
        data=request["candidate"].encode("utf-8"),
    )


def test_captured_run3_fails_mid_word_endpoints_deterministically() -> None:
    request, value, ledger = _captured()
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    receipt = build_span_shape_receipt_v1(
        ledger=ledger, ledger_bytes=raw, candidate_source=_source(request))
    failures = [record for record in receipt.records if record.status is AuditStatus.FAIL]
    assert receipt.status is AuditStatus.FAIL
    assert receipt.reason_code is SpanShapeReason.END_NOT_LINGUISTIC_BOUNDARY
    assert len(failures) == 4
    assert {record.json_pointer for record in failures} == {
        "/construction_role_audit/construction_records/0/candidate_span_ref",
        "/entries/0/candidate_span_ref",
        "/entries/1/candidate_span_ref",
        "/creative_target_audits/0/vehicle_span_ref",
    }
    assert canonical_receipt_bytes_v1(receipt) == canonical_receipt_bytes_v1(receipt)


def test_complete_clause_coordinates_pass_shape_and_geometry() -> None:
    request, value, _ = _captured()
    candidate_length = len(request["candidate"].encode("utf-8"))
    for record in value["construction_role_audit"]["construction_records"]:
        record["candidate_span_ref"]["start_utf8"] = 0
        record["candidate_span_ref"]["end_utf8"] = candidate_length
    for entry in value["entries"]:
        entry["candidate_span_ref"]["start_utf8"] = 0
        entry["candidate_span_ref"]["end_utf8"] = candidate_length
    for target in value["creative_target_audits"]:
        target["vehicle_span_ref"]["start_utf8"] = 0
        target["vehicle_span_ref"]["end_utf8"] = candidate_length
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ledger = ConstructionObligationLedgerV2.model_validate_json(raw)
    receipt = build_span_shape_receipt_v1(
        ledger=ledger, ledger_bytes=raw, candidate_source=_source(request))
    assert receipt.status is AuditStatus.PASS
    assert receipt.reason_code is None


def _phases(status: PhaseStatus = PhaseStatus.PASS) -> tuple[PhaseReceiptInputV1, ...]:
    return tuple(PhaseReceiptInputV1(
        phase=phase,
        status=status,
        receipt_identity=IDENTITY if status is PhaseStatus.PASS else None,
    ) for phase in REQUIRED_PHASES)


def test_derived_coverage_blocks_first_missing_semantic_phase() -> None:
    phases = list(_phases())
    index = REQUIRED_PHASES.index("INDEPENDENT_COMMITMENT_SPAN_AUDIT")
    phases[index] = PhaseReceiptInputV1(
        phase=REQUIRED_PHASES[index], status=PhaseStatus.NOT_EVALUATED)
    receipt = derive_coverage_receipt_v1(tuple(reversed(phases)))
    assert receipt.disposition is CoverageDisposition.BLOCKED
    assert receipt.blocking_phase == "INDEPENDENT_COMMITMENT_SPAN_AUDIT"
    assert receipt.reason_code == "STAGE_P_REQUIRED_PHASE_NOT_EVALUATED"


def test_derived_coverage_uses_precedence_and_requires_all_phases() -> None:
    phases = list(_phases())
    phases[2] = PhaseReceiptInputV1(
        phase=REQUIRED_PHASES[2], status=PhaseStatus.FAIL,
        reason_code=SpanShapeReason.END_NOT_LINGUISTIC_BOUNDARY.value)
    phases[4] = PhaseReceiptInputV1(
        phase=REQUIRED_PHASES[4], status=PhaseStatus.NOT_EVALUATED)
    blocked = derive_coverage_receipt_v1(tuple(phases))
    assert blocked.blocking_phase == "DETERMINISTIC_SPAN_SHAPE_AUDIT"
    assert blocked.reason_code == SpanShapeReason.END_NOT_LINGUISTIC_BOUNDARY.value
    complete = derive_coverage_receipt_v1(_phases())
    assert complete.disposition is CoverageDisposition.COMPLETE
    assert complete.blocking_phase is complete.reason_code is None
    assert hashlib.sha256(canonical_receipt_bytes_v1(complete)).hexdigest()
