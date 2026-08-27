"""Strict Phase 2 audit contracts and pure controller receipt builders.

This module has no prompt rendering, grammar, provider, tokenizer, model, runner,
or filesystem dependency. Model responses contain per-entry analysis only;
controller receipts derive record coverage and terminal status.
"""
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .immutable_source_span_reference_v1 import SourceRoleV1, SourceSpanReferenceV1


COMMITMENT_RESPONSE_SCHEMA = "pastila-semantic-admission-v2-stage-p-commitment-span-audit-response"
COMMITMENT_RECEIPT_SCHEMA = "pastila-semantic-admission-v2-stage-p-commitment-span-audit-receipt"
AUTHORITY_RESPONSE_SCHEMA = "pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response"
AUTHORITY_RECEIPT_SCHEMA = "pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-receipt"
RESPONSE_VERSION = "1.0.0-evaluation-candidate.1"
RECEIPT_VERSION = "1.0.0-evaluation.1"

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
EntryId = Annotated[str, StringConstraints(pattern=r"^P[1-8]$")]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CommitmentDecision(StrEnum):
    SPAN_SUPPORTS_COMPLETE_COMMITMENT = "SPAN_SUPPORTS_COMPLETE_COMMITMENT"
    COMMITMENT_EXCEEDS_SPAN = "COMMITMENT_EXCEEDS_SPAN"
    SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING = "SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING"
    ENTRY_ROLE_MISCLASSIFIED = "ENTRY_ROLE_MISCLASSIFIED"
    UNRESOLVED_FAIL_CLOSED = "UNRESOLVED_FAIL_CLOSED"


class CommitmentReason(StrEnum):
    COMMITMENT_EXCEEDS = "CSPAN_COMMITMENT_EXCEEDS_PROJECTED_SPAN"
    MATERIAL_UNRECONCILED = "CSPAN_MATERIAL_MEANING_UNRECONCILED"
    ROLE_MISCLASSIFIED = "CSPAN_ENTRY_ROLE_MISCLASSIFIED"
    UNRESOLVED = "CSPAN_SCOPE_OR_SUPPORT_UNRESOLVED"


_COMMITMENT_REASON_BY_DECISION = {
    CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT: None,
    CommitmentDecision.COMMITMENT_EXCEEDS_SPAN: CommitmentReason.COMMITMENT_EXCEEDS,
    CommitmentDecision.SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING:
        CommitmentReason.MATERIAL_UNRECONCILED,
    CommitmentDecision.ENTRY_ROLE_MISCLASSIFIED: CommitmentReason.ROLE_MISCLASSIFIED,
    CommitmentDecision.UNRESOLVED_FAIL_CLOSED: CommitmentReason.UNRESOLVED,
}


class CommitmentSpanRecordV1(_Frozen):
    entry_id: EntryId
    decision: CommitmentDecision
    assertion_checked: Literal[True]
    presupposition_checked: Literal[True]
    entailment_checked: Literal[True]
    necessary_implication_checked: Literal[True]
    reason_code: CommitmentReason | None
    basis: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def tuple_is_coherent(self) -> "CommitmentSpanRecordV1":
        if self.reason_code is not _COMMITMENT_REASON_BY_DECISION[self.decision]:
            raise ValueError("COMMITMENT_SPAN_DECISION_REASON_INCOHERENT")
        return self


class CommitmentSpanAuditResponseV1(_Frozen):
    schema_name: Literal[COMMITMENT_RESPONSE_SCHEMA] = COMMITMENT_RESPONSE_SCHEMA
    schema_version: Literal[RESPONSE_VERSION] = RESPONSE_VERSION
    audit_kind: Literal["COMMITMENT_SPAN_AUDIT"] = "COMMITMENT_SPAN_AUDIT"
    records: tuple[CommitmentSpanRecordV1, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_entries(self) -> "CommitmentSpanAuditResponseV1":
        ids = [record.entry_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("COMMITMENT_SPAN_DUPLICATE_ENTRY")
        return self


class ControllerStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"


class ParseStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CoverageStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CommitmentSpanAuditReceiptV1(_Frozen):
    schema_name: Literal[COMMITMENT_RECEIPT_SCHEMA] = COMMITMENT_RECEIPT_SCHEMA
    schema_version: Literal[RECEIPT_VERSION] = RECEIPT_VERSION
    request_identity: Sha256
    prompt_identity: Sha256
    model_identity: str
    grammar_identity: Sha256
    raw_response_sha256: Sha256
    expected_entry_ids: tuple[EntryId, ...] = Field(min_length=1, max_length=8)
    parse_status: ParseStatus
    record_coverage_status: CoverageStatus
    records: tuple[CommitmentSpanRecordV1, ...] = Field(max_length=8)
    derived_status: ControllerStatus
    derived_reason_code: str | None
    elapsed_ms: float = Field(ge=0)
    error_code: str | None

    @model_validator(mode="after")
    def receipt_is_coherent(self) -> "CommitmentSpanAuditReceiptV1":
        if len(self.expected_entry_ids) != len(set(self.expected_entry_ids)):
            raise ValueError("COMMITMENT_RECEIPT_DUPLICATE_EXPECTED_ENTRY")
        if self.parse_status is ParseStatus.FAIL:
            valid = (self.record_coverage_status is CoverageStatus.FAIL and not self.records and
                     self.derived_status is ControllerStatus.FAIL and self.error_code is not None)
        else:
            observed = tuple(record.entry_id for record in self.records)
            coverage_matches = observed == self.expected_entry_ids
            valid = (self.parse_status is ParseStatus.PASS and self.error_code is None and
                     ((self.record_coverage_status is CoverageStatus.PASS and coverage_matches) or
                      (self.record_coverage_status is CoverageStatus.FAIL and not coverage_matches)))
        if not valid:
            raise ValueError("COMMITMENT_RECEIPT_STATE_INCOHERENT")
        return self


def build_commitment_span_receipt_v1(
    *, raw_response: bytes, response: CommitmentSpanAuditResponseV1 | None,
    expected_entry_ids: tuple[str, ...], request_identity: str, prompt_identity: str,
    model_identity: str, grammar_identity: str, elapsed_ms: float,
    error_code: str | None = None,
) -> CommitmentSpanAuditReceiptV1:
    """Derive exact coverage and terminal status without repairing a response."""
    _validate_expected_ids(expected_entry_ids, allow_empty=False)
    digest = hashlib.sha256(bytes(raw_response)).hexdigest()
    if response is None:
        if not error_code:
            raise ValueError("COMMITMENT_PARSE_FAILURE_REQUIRES_ERROR")
        return CommitmentSpanAuditReceiptV1(
            request_identity=request_identity, prompt_identity=prompt_identity,
            model_identity=model_identity, grammar_identity=grammar_identity,
            raw_response_sha256=digest, expected_entry_ids=expected_entry_ids,
            parse_status=ParseStatus.FAIL, record_coverage_status=CoverageStatus.FAIL,
            records=(), derived_status=ControllerStatus.FAIL,
            derived_reason_code="CSPAN_RESPONSE_PARSE_OR_SCHEMA_FAILURE",
            elapsed_ms=elapsed_ms, error_code=error_code)
    if error_code is not None:
        raise ValueError("COMMITMENT_SUCCESS_CANNOT_HAVE_ERROR")
    observed = tuple(record.entry_id for record in response.records)
    if observed != expected_entry_ids:
        return CommitmentSpanAuditReceiptV1(
            request_identity=request_identity, prompt_identity=prompt_identity,
            model_identity=model_identity, grammar_identity=grammar_identity,
            raw_response_sha256=digest, expected_entry_ids=expected_entry_ids,
            parse_status=ParseStatus.PASS, record_coverage_status=CoverageStatus.FAIL,
            records=response.records, derived_status=ControllerStatus.FAIL,
            derived_reason_code="CSPAN_RECORD_COVERAGE_MISMATCH",
            elapsed_ms=elapsed_ms, error_code=None)
    unresolved = next((record for record in response.records
                       if record.decision is CommitmentDecision.UNRESOLVED_FAIL_CLOSED), None)
    failed = next((record for record in response.records
                   if record.decision is not CommitmentDecision.SPAN_SUPPORTS_COMPLETE_COMMITMENT), None)
    status = (ControllerStatus.INDETERMINATE if unresolved else
              ControllerStatus.FAIL if failed else ControllerStatus.PASS)
    reason = (unresolved.reason_code.value if unresolved else
              failed.reason_code.value if failed else None)
    return CommitmentSpanAuditReceiptV1(
        request_identity=request_identity, prompt_identity=prompt_identity,
        model_identity=model_identity, grammar_identity=grammar_identity,
        raw_response_sha256=digest, expected_entry_ids=expected_entry_ids,
        parse_status=ParseStatus.PASS, record_coverage_status=CoverageStatus.PASS,
        records=response.records, derived_status=status, derived_reason_code=reason,
        elapsed_ms=elapsed_ms, error_code=None)


class AuthorityDecision(StrEnum):
    GOVERNED_SUPPORTED = "GOVERNED_SUPPORTED"
    UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION = "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION"
    NOT_A_REAL_WORLD_COMMITMENT = "NOT_A_REAL_WORLD_COMMITMENT"
    UNRESOLVED_FAIL_CLOSED = "UNRESOLVED_FAIL_CLOSED"


class AxisDecision(StrEnum):
    MATCH = "MATCH"
    MUTATION = "MUTATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"


class FindingStatus(StrEnum):
    DECISIVE = "DECISIVE"
    SUPPORTING = "SUPPORTING"


FSEM_CODES = frozenset({
    "FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY", "FSEM_UNSUPPORTED_MOTIVE_OR_INTENT",
    "FSEM_UNSUPPORTED_CAUSALITY", "FSEM_UNSUPPORTED_OUTCOME_OR_STATUS",
    "FSEM_UNSUPPORTED_EMOTION_OR_REACTION", "FSEM_UNSUPPORTED_CAPACITY",
    "FSEM_CERTAINTY_MUTATION", "FSEM_TIMING_MUTATION", "FSEM_UNSUPPORTED_LIFE_STAKES",
    "FSEM_INVENTED_SPEECH_OR_ROLE_KNOWLEDGE", "FSEM_UNSUPPORTED_PREMISE_TO_DIRECTIVE",
    "FSEM_FICTION_RETURN_TO_FACT", "AREC_UNSUPPORTED_OTHER_REAL_WORLD_PROPOSITION",
})


class UnsupportedFindingV1(_Frozen):
    finding_id: str = Field(pattern=r"^F(?:[1-9]|1[0-6])$")
    entry_id: EntryId
    candidate_proposition_ref: SourceSpanReferenceV1
    reason_code: str
    reason_status: FindingStatus
    basis: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def finding_is_coherent(self) -> "UnsupportedFindingV1":
        if self.candidate_proposition_ref.source_role is not SourceRoleV1.CANDIDATE:
            raise ValueError("AUTHORITY_FINDING_CANDIDATE_ROLE_REQUIRED")
        if self.reason_code not in FSEM_CODES:
            raise ValueError("AUTHORITY_FINDING_REASON_UNKNOWN")
        return self


class AuthorityReconciliationRecordV1(_Frozen):
    entry_id: EntryId
    full_authority_compared: Literal[True]
    decision: AuthorityDecision
    authority_support_ref: SourceSpanReferenceV1 | None
    event_axis: AxisDecision
    modality_axis: AxisDecision
    timing_axis: AxisDecision
    unsupported_finding_ids: tuple[str, ...] = Field(max_length=16)
    basis: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def local_tuple_is_coherent(self) -> "AuthorityReconciliationRecordV1":
        if self.authority_support_ref is not None and self.authority_support_ref.source_role is not SourceRoleV1.FACTUAL_AUTHORITY:
            raise ValueError("AUTHORITY_SUPPORT_ROLE_REQUIRED")
        axes = (self.event_axis, self.modality_axis, self.timing_axis)
        if self.decision is AuthorityDecision.GOVERNED_SUPPORTED:
            valid = self.authority_support_ref is not None and all(axis is AxisDecision.MATCH for axis in axes) and not self.unsupported_finding_ids
        elif self.decision is AuthorityDecision.UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION:
            valid = self.authority_support_ref is None and bool(self.unsupported_finding_ids) and AxisDecision.UNRESOLVED not in axes
        elif self.decision is AuthorityDecision.NOT_A_REAL_WORLD_COMMITMENT:
            valid = self.authority_support_ref is None and all(axis is AxisDecision.NOT_APPLICABLE for axis in axes) and not self.unsupported_finding_ids
        else:
            valid = self.authority_support_ref is None and AxisDecision.UNRESOLVED in axes and not self.unsupported_finding_ids
        if not valid:
            raise ValueError("AUTHORITY_RECONCILIATION_DECISION_TUPLE_INCOHERENT")
        if len(self.unsupported_finding_ids) != len(set(self.unsupported_finding_ids)):
            raise ValueError("AUTHORITY_RECONCILIATION_DUPLICATE_FINDING_LINK")
        return self


class AuthorityReconciliationAuditResponseV1(_Frozen):
    schema_name: Literal[AUTHORITY_RESPONSE_SCHEMA] = AUTHORITY_RESPONSE_SCHEMA
    schema_version: Literal[RESPONSE_VERSION] = RESPONSE_VERSION
    audit_kind: Literal["AUTHORITY_RECONCILIATION_AUDIT"] = "AUTHORITY_RECONCILIATION_AUDIT"
    records: tuple[AuthorityReconciliationRecordV1, ...] = Field(max_length=8)
    unsupported_findings: tuple[UnsupportedFindingV1, ...] = Field(max_length=16)

    @model_validator(mode="after")
    def graph_is_coherent(self) -> "AuthorityReconciliationAuditResponseV1":
        entry_ids = [record.entry_id for record in self.records]
        finding_ids = [finding.finding_id for finding in self.unsupported_findings]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("AUTHORITY_RECONCILIATION_DUPLICATE_ENTRY")
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("AUTHORITY_RECONCILIATION_DUPLICATE_FINDING")
        finding_index = {finding.finding_id: finding for finding in self.unsupported_findings}
        linked: list[str] = []
        for record in self.records:
            for finding_id in record.unsupported_finding_ids:
                finding = finding_index.get(finding_id)
                if finding is None or finding.entry_id != record.entry_id:
                    raise ValueError("AUTHORITY_RECONCILIATION_FINDING_LINK_INVALID")
                linked.append(finding_id)
            if record.decision is AuthorityDecision.UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION:
                findings = [finding_index[item] for item in record.unsupported_finding_ids]
                if not any(finding.reason_status is FindingStatus.DECISIVE for finding in findings):
                    raise ValueError("AUTHORITY_RECONCILIATION_DECISIVE_FINDING_REQUIRED")
        if sorted(linked) != sorted(finding_ids):
            raise ValueError("AUTHORITY_RECONCILIATION_ORPHAN_OR_REUSED_FINDING")
        return self


class AuthorityReconciliationAuditReceiptV1(_Frozen):
    schema_name: Literal[AUTHORITY_RECEIPT_SCHEMA] = AUTHORITY_RECEIPT_SCHEMA
    schema_version: Literal[RECEIPT_VERSION] = RECEIPT_VERSION
    request_identity: Sha256
    prompt_identity: Sha256
    model_identity: str
    grammar_identity: Sha256
    raw_response_sha256: Sha256
    expected_entry_ids: tuple[EntryId, ...] = Field(max_length=8)
    parse_status: ParseStatus
    record_coverage_status: CoverageStatus
    source_projection_status: CoverageStatus
    records: tuple[AuthorityReconciliationRecordV1, ...] = Field(max_length=8)
    unsupported_findings: tuple[UnsupportedFindingV1, ...] = Field(max_length=16)
    derived_status: ControllerStatus
    derived_reason_code: str | None
    elapsed_ms: float = Field(ge=0)
    error_code: str | None
    deterministic_no_entries: bool

    @model_validator(mode="after")
    def receipt_is_coherent(self) -> "AuthorityReconciliationAuditReceiptV1":
        if len(self.expected_entry_ids) != len(set(self.expected_entry_ids)):
            raise ValueError("AUTHORITY_RECEIPT_DUPLICATE_EXPECTED_ENTRY")
        observed = tuple(record.entry_id for record in self.records)
        if self.deterministic_no_entries:
            valid = (not self.expected_entry_ids and not self.records and not self.unsupported_findings and
                     self.parse_status is ParseStatus.NOT_APPLICABLE and
                     self.record_coverage_status is CoverageStatus.NOT_APPLICABLE and
                     self.source_projection_status is CoverageStatus.NOT_APPLICABLE and
                     self.derived_status is ControllerStatus.PASS and self.error_code is None)
        elif self.parse_status is ParseStatus.FAIL:
            valid = (bool(self.expected_entry_ids) and not self.records and not self.unsupported_findings and
                     self.record_coverage_status is CoverageStatus.FAIL and
                     self.source_projection_status is CoverageStatus.FAIL and
                     self.derived_status is ControllerStatus.FAIL and self.error_code is not None)
        else:
            coverage_matches = observed == self.expected_entry_ids
            valid = (bool(self.expected_entry_ids) and self.parse_status is ParseStatus.PASS and
                     self.error_code is None and
                     ((self.record_coverage_status is CoverageStatus.PASS and coverage_matches) or
                      (self.record_coverage_status is CoverageStatus.FAIL and not coverage_matches)) and
                     self.source_projection_status in {CoverageStatus.PASS, CoverageStatus.FAIL})
        if not valid:
            raise ValueError("AUTHORITY_RECEIPT_STATE_INCOHERENT")
        return self


def build_authority_reconciliation_receipt_v1(
    *, raw_response: bytes, response: AuthorityReconciliationAuditResponseV1 | None,
    expected_entry_ids: tuple[str, ...], request_identity: str, prompt_identity: str,
    model_identity: str, grammar_identity: str, elapsed_ms: float,
    source_projection_pass: bool = True, error_code: str | None = None,
) -> AuthorityReconciliationAuditReceiptV1:
    """Derive authority-audit status, including the zero-entry no-call path."""
    _validate_expected_ids(expected_entry_ids, allow_empty=True)
    digest = hashlib.sha256(bytes(raw_response)).hexdigest()
    common = dict(request_identity=request_identity, prompt_identity=prompt_identity,
                  model_identity=model_identity, grammar_identity=grammar_identity,
                  raw_response_sha256=digest, expected_entry_ids=expected_entry_ids,
                  elapsed_ms=elapsed_ms)
    if not expected_entry_ids:
        if response is not None or raw_response or error_code is not None:
            raise ValueError("AUTHORITY_ZERO_ENTRY_PATH_MUST_NOT_HAVE_MODEL_EVIDENCE")
        return AuthorityReconciliationAuditReceiptV1(
            **common, parse_status=ParseStatus.NOT_APPLICABLE,
            record_coverage_status=CoverageStatus.NOT_APPLICABLE,
            source_projection_status=CoverageStatus.NOT_APPLICABLE, records=(),
            unsupported_findings=(), derived_status=ControllerStatus.PASS,
            derived_reason_code="AREC_NO_REAL_WORLD_COMMITMENTS",
            error_code=None, deterministic_no_entries=True)
    if response is None:
        if not error_code:
            raise ValueError("AUTHORITY_PARSE_FAILURE_REQUIRES_ERROR")
        return AuthorityReconciliationAuditReceiptV1(
            **common, parse_status=ParseStatus.FAIL,
            record_coverage_status=CoverageStatus.FAIL,
            source_projection_status=CoverageStatus.FAIL, records=(), unsupported_findings=(),
            derived_status=ControllerStatus.FAIL,
            derived_reason_code="AREC_RESPONSE_PARSE_OR_SCHEMA_FAILURE",
            error_code=error_code, deterministic_no_entries=False)
    if error_code is not None:
        raise ValueError("AUTHORITY_SUCCESS_CANNOT_HAVE_ERROR")
    observed = tuple(record.entry_id for record in response.records)
    coverage_pass = observed == expected_entry_ids
    if not coverage_pass or not source_projection_pass:
        reason = ("AREC_RECORD_COVERAGE_MISMATCH" if not coverage_pass
                  else "AREC_SOURCE_PROJECTION_FAILURE")
        return AuthorityReconciliationAuditReceiptV1(
            **common, parse_status=ParseStatus.PASS,
            record_coverage_status=CoverageStatus.PASS if coverage_pass else CoverageStatus.FAIL,
            source_projection_status=CoverageStatus.PASS if source_projection_pass else CoverageStatus.FAIL,
            records=response.records, unsupported_findings=response.unsupported_findings,
            derived_status=ControllerStatus.FAIL, derived_reason_code=reason,
            error_code=None, deterministic_no_entries=False)
    unresolved = next((record for record in response.records
                       if record.decision is AuthorityDecision.UNRESOLVED_FAIL_CLOSED), None)
    failed = next((record for record in response.records
                   if record.decision is not AuthorityDecision.GOVERNED_SUPPORTED), None)
    status = (ControllerStatus.INDETERMINATE if unresolved else
              ControllerStatus.FAIL if failed else ControllerStatus.PASS)
    reason = ("AREC_RECONCILIATION_UNRESOLVED" if unresolved else
              "AREC_UNSUPPORTED_OR_ROLE_MISCLASSIFIED" if failed else None)
    return AuthorityReconciliationAuditReceiptV1(
        **common, parse_status=ParseStatus.PASS, record_coverage_status=CoverageStatus.PASS,
        source_projection_status=CoverageStatus.PASS, records=response.records,
        unsupported_findings=response.unsupported_findings, derived_status=status,
        derived_reason_code=reason, error_code=None, deterministic_no_entries=False)


def _validate_expected_ids(entry_ids: tuple[str, ...], *, allow_empty: bool) -> None:
    if type(entry_ids) is not tuple or (not allow_empty and not entry_ids) or len(entry_ids) > 8:
        raise ValueError("AUDIT_EXPECTED_ENTRY_SET_INVALID")
    if len(entry_ids) != len(set(entry_ids)) or any(
            type(item) is not str or len(item) != 2 or item[0] != "P" or item[1] not in "12345678"
            for item in entry_ids):
        raise ValueError("AUDIT_EXPECTED_ENTRY_SET_INVALID")


def canonical_audit_receipt_bytes_v1(receipt: BaseModel) -> bytes:
    return (json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


__all__ = tuple(name for name in globals() if name.endswith("V1")) + (
    "AxisDecision", "AuthorityDecision", "CommitmentDecision", "CommitmentReason",
    "ControllerStatus", "CoverageStatus", "FSEM_CODES", "FindingStatus", "ParseStatus",
    "build_authority_reconciliation_receipt_v1", "build_commitment_span_receipt_v1",
    "canonical_audit_receipt_bytes_v1",
)
