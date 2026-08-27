"""Pure span-shape auditing and controller-derived Stage P coverage.

This evaluation-only module performs no I/O, model loading, generation, semantic
classification, or source-text repair. It deliberately treats semantic audits
that have not run as missing receipts and therefore blocks derived completion.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
    SourceSpanReferenceV1,
    resolve_source_span_v1,
)
from .stage_p_construction_obligation_contract_v2 import ConstructionObligationLedgerV2
from .stage_p_construction_role_contract_v1 import ConstructionRole


SPAN_RECEIPT_SCHEMA = "pastila-semantic-admission-v2-stage-p-span-shape-receipt"
SPAN_RECEIPT_VERSION = "1.0.0-evaluation.1"
COVERAGE_RECEIPT_SCHEMA = "pastila-semantic-admission-v2-stage-p-derived-coverage-receipt"
COVERAGE_RECEIPT_VERSION = "1.0.0-evaluation.1"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AuditStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class SpanShapeReason(StrEnum):
    START_NOT_LINGUISTIC_BOUNDARY = "STAGE_P_SPAN_START_NOT_LINGUISTIC_BOUNDARY"
    END_NOT_LINGUISTIC_BOUNDARY = "STAGE_P_SPAN_END_NOT_LINGUISTIC_BOUNDARY"
    CONSTRUCTION_LINK_OUTSIDE = "STAGE_P_CONSTRUCTION_LINK_OUTSIDE_SPAN"
    VEHICLE_OUTSIDE_HOST = "STAGE_P_VEHICLE_OUTSIDE_HOST_SPAN"
    RETURN_OUTSIDE_CONSTRUCTION = "STAGE_P_RETURN_OUTSIDE_CONSTRUCTION_SPAN"
    SHAPE_UNRESOLVED = "STAGE_P_SPAN_SHAPE_UNRESOLVED"


class SpanShapeRecordV1(_Frozen):
    json_pointer: str
    status: AuditStatus
    reason_code: SpanShapeReason | None = None
    related_json_pointer: str | None = None

    @model_validator(mode="after")
    def status_is_coherent(self) -> "SpanShapeRecordV1":
        if (self.status is AuditStatus.PASS) != (self.reason_code is None):
            raise ValueError("SPAN_SHAPE_RECORD_STATUS_INCOHERENT")
        return self


class SpanShapeReceiptV1(_Frozen):
    schema_name: Literal[SPAN_RECEIPT_SCHEMA] = SPAN_RECEIPT_SCHEMA
    schema_version: Literal[SPAN_RECEIPT_VERSION] = SPAN_RECEIPT_VERSION
    ledger_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    records: tuple[SpanShapeRecordV1, ...]
    status: AuditStatus
    reason_code: SpanShapeReason | None = None

    @model_validator(mode="after")
    def receipt_is_coherent(self) -> "SpanShapeReceiptV1":
        failures = [record for record in self.records if record.status is AuditStatus.FAIL]
        if self.status is AuditStatus.PASS:
            if failures or self.reason_code is not None:
                raise ValueError("SPAN_SHAPE_PASS_INCOHERENT")
        elif not failures or self.reason_code is not failures[0].reason_code:
            raise ValueError("SPAN_SHAPE_FAIL_INCOHERENT")
        return self


def _character_at_byte(data: bytes, offset: int, *, before: bool) -> str | None:
    text = data.decode("utf-8", errors="strict")
    byte_cursor = 0
    previous = None
    for character in text:
        next_cursor = byte_cursor + len(character.encode("utf-8"))
        if before and next_cursor == offset:
            return character
        if not before and byte_cursor == offset:
            return character
        previous = character
        byte_cursor = next_cursor
    if before and byte_cursor == offset:
        return previous
    return None


def _is_word_constituent(character: str | None) -> bool:
    if character is None:
        return False
    category = unicodedata.category(character)
    return category[0] in {"L", "M", "N"} or category == "Pc"


def _is_punctuation(character: str | None) -> bool:
    return character is not None and unicodedata.category(character).startswith("P")


def _is_linguistic_boundary(data: bytes, offset: int) -> bool:
    if offset in {0, len(data)}:
        return True
    left = _character_at_byte(data, offset, before=True)
    right = _character_at_byte(data, offset, before=False)
    if right is not None and unicodedata.category(right).startswith("M"):
        return False
    if _is_word_constituent(left) and _is_word_constituent(right):
        return False
    if _is_punctuation(left) and _is_punctuation(right) and left == right:
        return False
    return True


def _contains(outer: SourceSpanReferenceV1, inner: SourceSpanReferenceV1) -> bool:
    return (outer.source_role is inner.source_role and outer.source_sha256 == inner.source_sha256
            and outer.start_utf8 <= inner.start_utf8 and inner.end_utf8 <= outer.end_utf8)


def _overlaps(left: SourceSpanReferenceV1, right: SourceSpanReferenceV1) -> bool:
    return (left.source_role is right.source_role and left.source_sha256 == right.source_sha256
            and max(left.start_utf8, right.start_utf8) < min(left.end_utf8, right.end_utf8))


def build_span_shape_receipt_v1(
    *, ledger: ConstructionObligationLedgerV2, ledger_bytes: bytes,
    candidate_source: ImmutableUtf8SourceV1,
) -> SpanShapeReceiptV1:
    """Audit linguistic endpoints and construction graph geometry."""
    if candidate_source.role is not SourceRoleV1.CANDIDATE:
        raise ValueError("SPAN_SHAPE_CANDIDATE_ROLE_MISMATCH")
    entry_index = {entry.entry_id: (index, entry) for index, entry in enumerate(ledger.entries)}
    records: list[SpanShapeRecordV1] = []
    references: list[tuple[str, SourceSpanReferenceV1]] = []
    for index, construction in enumerate(ledger.construction_role_audit.construction_records):
        references.append((
            f"/construction_role_audit/construction_records/{index}/candidate_span_ref",
            construction.candidate_span_ref,
        ))
    for index, entry in enumerate(ledger.entries):
        references.append((f"/entries/{index}/candidate_span_ref", entry.candidate_span_ref))
    for index, target in enumerate(ledger.creative_target_audits):
        references.append((f"/creative_target_audits/{index}/vehicle_span_ref", target.vehicle_span_ref))
    for pointer, reference in references:
        resolve_source_span_v1(reference, expected_role=SourceRoleV1.CANDIDATE,
                               sources={SourceRoleV1.CANDIDATE: candidate_source})
        if not _is_linguistic_boundary(candidate_source.data, reference.start_utf8):
            records.append(SpanShapeRecordV1(
                json_pointer=pointer, status=AuditStatus.FAIL,
                reason_code=SpanShapeReason.START_NOT_LINGUISTIC_BOUNDARY))
        elif not _is_linguistic_boundary(candidate_source.data, reference.end_utf8):
            records.append(SpanShapeRecordV1(
                json_pointer=pointer, status=AuditStatus.FAIL,
                reason_code=SpanShapeReason.END_NOT_LINGUISTIC_BOUNDARY))
        else:
            records.append(SpanShapeRecordV1(json_pointer=pointer, status=AuditStatus.PASS))

    construction_index: dict[str, tuple[int, object]] = {}
    for index, construction in enumerate(ledger.construction_role_audit.construction_records):
        construction_index[construction.construction_id] = (index, construction)
        outer_pointer = f"/construction_role_audit/construction_records/{index}/candidate_span_ref"
        linked_ids = tuple(filter(None, (construction.creative_host_entry_id,))) + construction.literal_or_return_entry_ids
        for entry_id in linked_ids:
            entry_position, entry = entry_index[entry_id]
            if not _contains(construction.candidate_span_ref, entry.candidate_span_ref):
                reason = (SpanShapeReason.RETURN_OUTSIDE_CONSTRUCTION
                          if entry_id in construction.literal_or_return_entry_ids
                          else SpanShapeReason.CONSTRUCTION_LINK_OUTSIDE)
                records.append(SpanShapeRecordV1(
                    json_pointer=outer_pointer, status=AuditStatus.FAIL, reason_code=reason,
                    related_json_pointer=f"/entries/{entry_position}/candidate_span_ref"))

    for target_position, target in enumerate(ledger.creative_target_audits):
        host_position, host = entry_index[target.creative_host_entry_id]
        if not _contains(host.candidate_span_ref, target.vehicle_span_ref):
            records.append(SpanShapeRecordV1(
                json_pointer=f"/creative_target_audits/{target_position}/vehicle_span_ref",
                status=AuditStatus.FAIL, reason_code=SpanShapeReason.VEHICLE_OUTSIDE_HOST,
                related_json_pointer=f"/entries/{host_position}/candidate_span_ref"))

    for _, construction in construction_index.values():
        if construction.construction_role is not ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD:
            continue
        _, host = entry_index[construction.creative_host_entry_id]
        for entry_id in construction.literal_or_return_entry_ids:
            entry_position, entry = entry_index[entry_id]
            if not _overlaps(host.candidate_span_ref, entry.candidate_span_ref):
                records.append(SpanShapeRecordV1(
                    json_pointer=f"/entries/{entry_position}/candidate_span_ref",
                    status=AuditStatus.FAIL, reason_code=SpanShapeReason.SHAPE_UNRESOLVED,
                    related_json_pointer=f"/entries/{entry_index[host.entry_id][0]}/candidate_span_ref"))

    failures = [record for record in records if record.status is AuditStatus.FAIL]
    return SpanShapeReceiptV1(
        ledger_sha256=hashlib.sha256(bytes(ledger_bytes)).hexdigest(),
        candidate_sha256=candidate_source.sha256,
        records=tuple(records),
        status=AuditStatus.FAIL if failures else AuditStatus.PASS,
        reason_code=failures[0].reason_code if failures else None,
    )


class PhaseStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class CoverageDisposition(StrEnum):
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class PhaseReceiptInputV1(_Frozen):
    phase: str
    status: PhaseStatus
    receipt_identity: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason_code: str | None = None

    @model_validator(mode="after")
    def phase_is_coherent(self) -> "PhaseReceiptInputV1":
        if self.status is PhaseStatus.PASS and (self.receipt_identity is None or self.reason_code is not None):
            raise ValueError("PASS_PHASE_RECEIPT_INCOHERENT")
        if self.status is PhaseStatus.FAIL and self.reason_code is None:
            raise ValueError("FAIL_PHASE_RECEIPT_REASON_REQUIRED")
        if self.status is PhaseStatus.NOT_EVALUATED and (self.receipt_identity is not None or self.reason_code is not None):
            raise ValueError("UNEVALUATED_PHASE_RECEIPT_INCOHERENT")
        return self


class DerivedCoverageReceiptV1(_Frozen):
    schema_name: Literal[COVERAGE_RECEIPT_SCHEMA] = COVERAGE_RECEIPT_SCHEMA
    schema_version: Literal[COVERAGE_RECEIPT_VERSION] = COVERAGE_RECEIPT_VERSION
    phase_receipts: tuple[PhaseReceiptInputV1, ...]
    disposition: CoverageDisposition
    blocking_phase: str | None
    reason_code: str | None


REQUIRED_PHASES = (
    "STRICT_LEDGER_SCHEMA", "COPYLESS_SOURCE_PROJECTION", "DETERMINISTIC_SPAN_SHAPE_AUDIT",
    "GRAPH_AND_OBLIGATION_COHERENCE", "INDEPENDENT_COMMITMENT_SPAN_AUDIT",
    "INDEPENDENT_AUTHORITY_RECONCILIATION_AUDIT", "CREATIVE_TARGET_RECONCILIATION",
)


def derive_coverage_receipt_v1(
    phase_receipts: tuple[PhaseReceiptInputV1, ...],
) -> DerivedCoverageReceiptV1:
    """Derive completion in fixed precedence; missing semantic work blocks."""
    by_phase = {receipt.phase: receipt for receipt in phase_receipts}
    if len(by_phase) != len(phase_receipts) or set(by_phase) != set(REQUIRED_PHASES):
        raise ValueError("DERIVED_COVERAGE_PHASE_SET_INVALID")
    ordered = tuple(by_phase[phase] for phase in REQUIRED_PHASES)
    for receipt in ordered:
        if receipt.status is PhaseStatus.FAIL:
            return DerivedCoverageReceiptV1(
                phase_receipts=ordered, disposition=CoverageDisposition.BLOCKED,
                blocking_phase=receipt.phase, reason_code=receipt.reason_code)
        if receipt.status is PhaseStatus.NOT_EVALUATED:
            return DerivedCoverageReceiptV1(
                phase_receipts=ordered, disposition=CoverageDisposition.BLOCKED,
                blocking_phase=receipt.phase, reason_code="STAGE_P_REQUIRED_PHASE_NOT_EVALUATED")
    return DerivedCoverageReceiptV1(
        phase_receipts=ordered, disposition=CoverageDisposition.COMPLETE,
        blocking_phase=None, reason_code=None)


def canonical_receipt_bytes_v1(receipt: BaseModel) -> bytes:
    return (json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


__all__ = (
    "AuditStatus", "CoverageDisposition", "DerivedCoverageReceiptV1", "PhaseReceiptInputV1",
    "PhaseStatus", "REQUIRED_PHASES", "SpanShapeReason", "SpanShapeReceiptV1",
    "build_span_shape_receipt_v1", "canonical_receipt_bytes_v1", "derive_coverage_receipt_v1",
)
