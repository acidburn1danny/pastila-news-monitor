"""Evaluation-only Stage P contract with mandatory construction-role auditing."""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .stage_p_creative_target_contract_v1 import (
    CreativeTargetLedgerV1,
    CreativeTargetCoverageReceiptV1,
    CreativeTargetAuditV1,
    _Frozen,
    validate_creative_target_sources,
)
from .stage_p_role_coherence_contract_v1 import EntryType
from .stage_p_scope_graph_contract_v1 import _any_overlap, _occurrences
from .stage_p_scope_graph_contract_v1_1 import ScopeGraphEntryV1_1


class ConstructionDisposition(StrEnum):
    NO_MATERIAL_CREATIVE_CONSTRUCTION = "NO_MATERIAL_CREATIVE_CONSTRUCTION"
    ONE_OR_MORE_MATERIAL_CONSTRUCTIONS = "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS"
    UNRESOLVED_CONSTRUCTION_ROLE = "UNRESOLVED_CONSTRUCTION_ROLE"


class ConstructionRole(StrEnum):
    LITERAL_ONLY = "LITERAL_ONLY"
    MATERIAL_CREATIVE_OR_EDITORIAL = "MATERIAL_CREATIVE_OR_EDITORIAL"
    MIXED_CREATIVE_AND_REAL_WORLD = "MIXED_CREATIVE_AND_REAL_WORLD"
    NON_MATERIAL_RHETORICAL_COLOR = "NON_MATERIAL_RHETORICAL_COLOR"
    UNRESOLVED = "UNRESOLVED"


class ConstructionResolution(StrEnum):
    LITERAL_PATH_RETAINED = "LITERAL_PATH_RETAINED"
    CREATIVE_HOST_REQUIRED = "CREATIVE_HOST_REQUIRED"
    MIXED_HOST_AND_RETURNS_REQUIRED = "MIXED_HOST_AND_RETURNS_REQUIRED"
    RHETORICAL_COLOR_RETAINED = "RHETORICAL_COLOR_RETAINED"
    FAIL_CLOSED_UNRESOLVED = "FAIL_CLOSED_UNRESOLVED"


class ConstructionRecordV1(_Frozen):
    construction_id: str = Field(pattern=r"^C[1-8]$")
    candidate_span: str = Field(min_length=1)
    construction_role: ConstructionRole
    role_basis: str = Field(min_length=1, max_length=500)
    creative_host_entry_id: str | None = Field(default=None, pattern=r"^P[1-8]$")
    literal_or_return_entry_ids: tuple[str, ...] = Field(max_length=8)
    resolution: ConstructionResolution

    @model_validator(mode="after")
    def role_tuple_is_coherent(self):
        expected = {
            ConstructionRole.LITERAL_ONLY: ConstructionResolution.LITERAL_PATH_RETAINED,
            ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL: ConstructionResolution.CREATIVE_HOST_REQUIRED,
            ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD: ConstructionResolution.MIXED_HOST_AND_RETURNS_REQUIRED,
            ConstructionRole.NON_MATERIAL_RHETORICAL_COLOR: ConstructionResolution.RHETORICAL_COLOR_RETAINED,
            ConstructionRole.UNRESOLVED: ConstructionResolution.FAIL_CLOSED_UNRESOLVED,
        }[self.construction_role]
        if self.resolution is not expected:
            raise ValueError("CONSTRUCTION_ROLE_RESOLUTION_MISMATCH")
        needs_host = self.construction_role in {
            ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
            ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD,
        }
        if needs_host != (self.creative_host_entry_id is not None):
            raise ValueError("CONSTRUCTION_HOST_PRESENCE_MISMATCH")
        if self.construction_role is ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD:
            if not self.literal_or_return_entry_ids:
                raise ValueError("MIXED_CONSTRUCTION_REQUIRES_RETURN")
        elif self.construction_role in {ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
                                      ConstructionRole.UNRESOLVED}:
            if self.literal_or_return_entry_ids:
                raise ValueError("CONSTRUCTION_UNEXPECTED_LITERAL_OR_RETURN")
        return self


class ConstructionRoleAuditV1(_Frozen):
    candidate_reviewed_as_construction: bool
    overall_disposition: ConstructionDisposition
    construction_records: tuple[ConstructionRecordV1, ...] = Field(max_length=8)
    literal_path_basis: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def disposition_is_coherent(self):
        roles = {record.construction_role for record in self.construction_records}
        material = bool(roles & {ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
                                 ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD})
        unresolved = ConstructionRole.UNRESOLVED in roles
        if not self.candidate_reviewed_as_construction:
            raise ValueError("CONSTRUCTION_REVIEW_REQUIRED")
        if self.overall_disposition is ConstructionDisposition.NO_MATERIAL_CREATIVE_CONSTRUCTION:
            if material or unresolved or not self.literal_path_basis:
                raise ValueError("NO_MATERIAL_DISPOSITION_INCOHERENT")
        elif self.overall_disposition is ConstructionDisposition.ONE_OR_MORE_MATERIAL_CONSTRUCTIONS:
            if not material or unresolved or self.literal_path_basis is not None:
                raise ValueError("MATERIAL_DISPOSITION_INCOHERENT")
        elif not unresolved or self.literal_path_basis is not None:
            raise ValueError("UNRESOLVED_DISPOSITION_INCOHERENT")
        identifiers = [record.construction_id for record in self.construction_records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("DUPLICATE_CONSTRUCTION_ID")
        return self


class ConstructionRoleCoverageReceiptV1(CreativeTargetCoverageReceiptV1):
    construction_roles_reviewed: bool
    construction_to_ledger_reconciled: bool


class ConstructionRoleLedgerV1(_Frozen):
    stage_id: str = Field(pattern=r"^PROPOSITION_LEDGER$")
    construction_role_audit: ConstructionRoleAuditV1
    entries: tuple[ScopeGraphEntryV1_1, ...] = Field(min_length=1, max_length=8)
    creative_target_audits: tuple[CreativeTargetAuditV1, ...] = Field(max_length=16)
    coverage_receipt: ConstructionRoleCoverageReceiptV1
    coverage_decision: str = Field(pattern=r"^(COMPLETE|INDETERMINATE)$")

    @model_validator(mode="after")
    def construction_graph_is_coherent(self):
        base = CreativeTargetLedgerV1.model_validate({
            "stage_id": self.stage_id,
            "entries": [entry.model_dump(mode="json") for entry in self.entries],
            "creative_target_audits": [audit.model_dump(mode="json") for audit in self.creative_target_audits],
            "coverage_receipt": {key: value for key, value in self.coverage_receipt.model_dump().items()
                                 if key not in {"construction_roles_reviewed", "construction_to_ledger_reconciled"}},
            "coverage_decision": self.coverage_decision,
        }, strict=False)
        del base
        index = {entry.entry_id: entry for entry in self.entries}
        mapped_hosts: set[str] = set()
        unresolved_record = False
        for record in self.construction_role_audit.construction_records:
            host_id = record.creative_host_entry_id
            if host_id is not None:
                host = index.get(host_id)
                if host is None or host.entry_type is not EntryType.CONTAINED_CREATIVE:
                    raise ValueError("CONSTRUCTION_HOST_INVALID")
                mapped_hosts.add(host_id)
            for entry_id in record.literal_or_return_entry_ids:
                entry = index.get(entry_id)
                if entry is None or entry.entry_type is not EntryType.REAL_WORLD_COMMITMENT:
                    raise ValueError("CONSTRUCTION_LITERAL_OR_RETURN_INVALID")
                if record.construction_role is ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD:
                    if entry.creative_host_entry_id != host_id:
                        raise ValueError("MIXED_RETURN_HOST_MISMATCH")
            unresolved_record |= record.construction_role is ConstructionRole.UNRESOLVED
        creative_ids = {entry.entry_id for entry in self.entries if entry.entry_type is EntryType.CONTAINED_CREATIVE}
        if creative_ids != mapped_hosts:
            raise ValueError("CONSTRUCTION_CREATIVE_HOST_COVERAGE_MISMATCH")
        if unresolved_record and not any(entry.entry_type is EntryType.UNRESOLVED_SCOPE for entry in self.entries):
            raise ValueError("UNRESOLVED_CONSTRUCTION_REQUIRES_UNRESOLVED_ENTRY")
        receipts = self.coverage_receipt
        if self.coverage_decision == "COMPLETE" and not (
                receipts.construction_roles_reviewed and receipts.construction_to_ledger_reconciled):
            raise ValueError("COMPLETE_CONSTRUCTION_RECEIPTS_INCOHERENT")
        if self.construction_role_audit.overall_disposition is ConstructionDisposition.UNRESOLVED_CONSTRUCTION_ROLE:
            if self.coverage_decision != "INDETERMINATE" or not receipts.unresolved_scope_present:
                raise ValueError("UNRESOLVED_CONSTRUCTION_MUST_FAIL_CLOSED")
        return self


def validate_construction_role_sources(ledger: ConstructionRoleLedgerV1, *, factual_summary: str,
                                       candidate: str) -> None:
    proxy = CreativeTargetLedgerV1.model_validate({
        "stage_id": ledger.stage_id,
        "entries": [entry.model_dump(mode="json") for entry in ledger.entries],
        "creative_target_audits": [audit.model_dump(mode="json") for audit in ledger.creative_target_audits],
        "coverage_receipt": {key: value for key, value in ledger.coverage_receipt.model_dump().items()
                             if key not in {"construction_roles_reviewed", "construction_to_ledger_reconciled"}},
        "coverage_decision": ledger.coverage_decision,
    }, strict=False)
    validate_creative_target_sources(proxy, factual_summary=factual_summary, candidate=candidate)
    positions = {entry.entry_id: _occurrences(candidate, entry.candidate_span) for entry in ledger.entries}
    for record in ledger.construction_role_audit.construction_records:
        spans = _occurrences(candidate, record.candidate_span)
        if not spans:
            raise ValueError("CONSTRUCTION_SPAN_NOT_IN_CANDIDATE")
        if record.creative_host_entry_id and not _any_overlap(spans, positions[record.creative_host_entry_id]):
            raise ValueError("CONSTRUCTION_SPAN_DOES_NOT_OVERLAP_HOST")
        for entry_id in record.literal_or_return_entry_ids:
            if not _any_overlap(spans, positions[entry_id]):
                raise ValueError("CONSTRUCTION_SPAN_DOES_NOT_OVERLAP_LITERAL_OR_RETURN")


__all__ = ("ConstructionDisposition", "ConstructionResolution", "ConstructionRole",
           "ConstructionRecordV1", "ConstructionRoleAuditV1", "ConstructionRoleCoverageReceiptV1",
           "ConstructionRoleLedgerV1", "validate_construction_role_sources")
