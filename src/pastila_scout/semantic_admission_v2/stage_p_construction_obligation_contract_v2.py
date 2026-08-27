"""Frozen V2 copyless Construction Obligation ledger and pure projection receipt."""
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceProjectionErrorV1,
    SourceRoleV1,
    SourceSpanReferenceV1,
    resolve_source_span_v1,
)
from .stage_p_construction_role_contract_v1 import (
    ConstructionDisposition,
    ConstructionResolution,
    ConstructionRole,
)
from .stage_p_creative_target_contract_v1 import (
    CreativeTargetClass,
    CreativeTargetResolution,
    CreativeTargetSurvivalBasis,
)
from .stage_p_role_coherence_contract_v1 import (
    CoverageDecision,
    EntryType,
    EventAlignment,
    Modality,
    ScopeBasis,
    Timing,
)
from .stage_p_scope_graph_contract_v1 import FactualReturnBasis, ScopeRelation, SURVIVING_BASES


SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-ledger"
SCHEMA_VERSION = "2.0.0-evaluation.1"
PROJECTION_RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-source-projection-receipt"
PROJECTION_RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation.1"
REFERENCE_CANDIDATE_IDENTITY = "b127e9e321f1378d012ff65fb9c5718709c2bc84eb898130f405abd61c9fa0ae"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ScopeGraphEntryV2(_Frozen):
    entry_id: str = Field(pattern=r"^P[1-8]$")
    entry_type: EntryType
    candidate_span_ref: SourceSpanReferenceV1
    authority_support_ref: SourceSpanReferenceV1 | None
    commitment: str = Field(min_length=1, max_length=500)
    scope_basis: ScopeBasis
    event_alignment: EventAlignment
    authority_modality: Modality
    candidate_modality: Modality
    authority_timing: Timing
    candidate_timing: Timing
    independence_group: str = Field(pattern=r"^G[1-8]$")
    scope_relation: ScopeRelation
    creative_host_entry_id: str | None = Field(default=None, pattern=r"^P[1-8]$")
    factual_return_basis: FactualReturnBasis

    @model_validator(mode="after")
    def roles_are_coherent(self):
        if self.candidate_span_ref.source_role is not SourceRoleV1.CANDIDATE:
            raise ValueError("CANDIDATE_SPAN_REFERENCE_ROLE_MISMATCH")
        if (self.authority_support_ref is not None and
                self.authority_support_ref.source_role is not SourceRoleV1.FACTUAL_AUTHORITY):
            raise ValueError("AUTHORITY_SUPPORT_REFERENCE_ROLE_MISMATCH")
        if self.entry_type is EntryType.CONTAINED_CREATIVE:
            if not (self.scope_basis is ScopeBasis.CREATIVE_CONTAINED and
                    self.event_alignment is EventAlignment.CREATIVE_VEHICLE_ONLY and
                    self.authority_modality is self.candidate_modality is Modality.NOT_APPLICABLE and
                    self.authority_timing is self.candidate_timing is Timing.NOT_APPLICABLE):
                raise ValueError("CONTAINED_CREATIVE_ROLE_INCOHERENT")
        elif self.entry_type is EntryType.REAL_WORLD_COMMITMENT:
            if self.scope_basis not in {ScopeBasis.ASSERTED, ScopeBasis.PRESUPPOSED,
                                        ScopeBasis.ENTAILED, ScopeBasis.NECESSARILY_IMPLIED}:
                raise ValueError("REAL_WORLD_SCOPE_INCOHERENT")
            if self.event_alignment not in {EventAlignment.GOVERNED_EVENT,
                                            EventAlignment.NEW_UNSUPPORTED_EVENT}:
                raise ValueError("REAL_WORLD_EVENT_INCOHERENT")
            if self.candidate_modality in {Modality.NOT_APPLICABLE, Modality.UNRESOLVED}:
                raise ValueError("REAL_WORLD_CANDIDATE_MODALITY_INCOHERENT")
            if self.candidate_timing in {Timing.NOT_APPLICABLE, Timing.UNRESOLVED}:
                raise ValueError("REAL_WORLD_CANDIDATE_TIMING_INCOHERENT")
            if self.authority_support_ref is None:
                if (self.authority_modality is not Modality.NOT_APPLICABLE or
                        self.authority_timing is not Timing.NOT_APPLICABLE):
                    raise ValueError("NULL_AUTHORITY_AXES_INCOHERENT")
            elif (self.authority_modality in {Modality.NOT_APPLICABLE, Modality.UNRESOLVED} or
                  self.authority_timing in {Timing.NOT_APPLICABLE, Timing.UNRESOLVED}):
                raise ValueError("SUPPORTED_AUTHORITY_AXES_INCOHERENT")
        elif not (self.scope_basis is ScopeBasis.UNRESOLVED or
                  self.event_alignment is EventAlignment.UNRESOLVED or
                  self.candidate_modality is Modality.UNRESOLVED or
                  self.candidate_timing is Timing.UNRESOLVED):
            raise ValueError("UNRESOLVED_SCOPE_WITHOUT_UNRESOLVED_AXIS")
        if self.scope_relation is ScopeRelation.CREATIVE_HOST:
            if (self.entry_type is not EntryType.CONTAINED_CREATIVE or
                    self.creative_host_entry_id is not None or
                    self.factual_return_basis is not FactualReturnBasis.NOT_APPLICABLE):
                raise ValueError("CREATIVE_HOST_RELATION_INCOHERENT")
        elif self.scope_relation is ScopeRelation.FACTUAL_RETURN_WITHIN_CREATIVE_HOST:
            if (self.entry_type is not EntryType.REAL_WORLD_COMMITMENT or
                    self.creative_host_entry_id is None or
                    self.factual_return_basis not in SURVIVING_BASES):
                raise ValueError("FACTUAL_RETURN_RELATION_INCOHERENT")
        elif self.scope_relation is ScopeRelation.STANDALONE:
            if self.creative_host_entry_id is not None or self.entry_type is EntryType.UNRESOLVED_SCOPE:
                raise ValueError("STANDALONE_RELATION_INCOHERENT")
            if (self.entry_type is EntryType.CONTAINED_CREATIVE and
                    self.factual_return_basis is not FactualReturnBasis.NOT_APPLICABLE):
                raise ValueError("STANDALONE_CREATIVE_BASIS_INCOHERENT")
            if (self.entry_type is EntryType.REAL_WORLD_COMMITMENT and
                    self.factual_return_basis not in SURVIVING_BASES):
                raise ValueError("STANDALONE_REAL_WORLD_BASIS_INCOHERENT")
        elif (self.entry_type is not EntryType.UNRESOLVED_SCOPE or
              self.factual_return_basis is not FactualReturnBasis.UNRESOLVED):
            raise ValueError("UNRESOLVED_RELATION_INCOHERENT")
        if self.event_alignment is EventAlignment.GOVERNED_EVENT and self.authority_support_ref is None:
            raise ValueError("GOVERNED_EVENT_REQUIRES_AUTHORITY_SUPPORT")
        return self


class CreativeTargetAuditV2(_Frozen):
    audit_id: str = Field(pattern=r"^T(?:[1-9]|1[0-6])$")
    creative_host_entry_id: str = Field(pattern=r"^P[1-8]$")
    vehicle_span_ref: SourceSpanReferenceV1
    semantic_target: str = Field(min_length=1, max_length=500)
    target_class: CreativeTargetClass
    survival_basis: CreativeTargetSurvivalBasis
    proposition_entry_id: str | None = Field(default=None, pattern=r"^P[1-8]$")
    resolution: CreativeTargetResolution

    @model_validator(mode="after")
    def target_is_coherent(self):
        if self.vehicle_span_ref.source_role is not SourceRoleV1.CANDIDATE:
            raise ValueError("VEHICLE_SPAN_REFERENCE_ROLE_MISMATCH")
        surviving = {
            CreativeTargetSurvivalBasis.ASSERTION_SURVIVES,
            CreativeTargetSurvivalBasis.PRESUPPOSITION_SURVIVES,
            CreativeTargetSurvivalBasis.ENTAILMENT_SURVIVES,
            CreativeTargetSurvivalBasis.NECESSARY_IMPLICATION_SURVIVES,
        }
        if self.target_class is CreativeTargetClass.NONFACTUAL_EDITORIAL_OR_CREATIVE:
            coherent = (self.survival_basis is CreativeTargetSurvivalBasis.DOES_NOT_SURVIVE_AS_FACT and
                        self.proposition_entry_id is None and
                        self.resolution is CreativeTargetResolution.RETAINED_NONFACTUAL)
        elif self.target_class is CreativeTargetClass.REAL_WORLD_PROPOSITION:
            coherent = (self.survival_basis in surviving and self.proposition_entry_id is not None and
                        self.resolution is CreativeTargetResolution.RECONCILED_TO_LEDGER)
        else:
            coherent = (self.survival_basis is CreativeTargetSurvivalBasis.UNRESOLVED and
                        self.proposition_entry_id is None and
                        self.resolution is CreativeTargetResolution.FAIL_CLOSED_UNRESOLVED)
        if not coherent:
            raise ValueError("CREATIVE_TARGET_TUPLE_INCOHERENT")
        return self


class ConstructionRecordV2(_Frozen):
    construction_id: str = Field(pattern=r"^C[1-8]$")
    candidate_span_ref: SourceSpanReferenceV1
    construction_role: ConstructionRole
    role_basis: str = Field(min_length=1, max_length=500)
    creative_host_entry_id: str | None = Field(default=None, pattern=r"^P[1-8]$")
    literal_or_return_entry_ids: tuple[str, ...] = Field(max_length=8)
    resolution: ConstructionResolution

    @model_validator(mode="after")
    def construction_is_coherent(self):
        if self.candidate_span_ref.source_role is not SourceRoleV1.CANDIDATE:
            raise ValueError("CONSTRUCTION_SPAN_REFERENCE_ROLE_MISMATCH")
        expected = {
            ConstructionRole.LITERAL_ONLY: ConstructionResolution.LITERAL_PATH_RETAINED,
            ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL: ConstructionResolution.CREATIVE_HOST_REQUIRED,
            ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD: ConstructionResolution.MIXED_HOST_AND_RETURNS_REQUIRED,
            ConstructionRole.NON_MATERIAL_RHETORICAL_COLOR: ConstructionResolution.RHETORICAL_COLOR_RETAINED,
            ConstructionRole.UNRESOLVED: ConstructionResolution.FAIL_CLOSED_UNRESOLVED,
        }[self.construction_role]
        if self.resolution is not expected:
            raise ValueError("CONSTRUCTION_ROLE_RESOLUTION_MISMATCH")
        needs_host = self.construction_role in {ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
                                                ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD}
        if needs_host != (self.creative_host_entry_id is not None):
            raise ValueError("CONSTRUCTION_HOST_PRESENCE_MISMATCH")
        if self.construction_role is ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD:
            if not self.literal_or_return_entry_ids:
                raise ValueError("MIXED_CONSTRUCTION_REQUIRES_RETURN")
        elif self.construction_role in {ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
                                      ConstructionRole.UNRESOLVED} and self.literal_or_return_entry_ids:
            raise ValueError("CONSTRUCTION_UNEXPECTED_LITERAL_OR_RETURN")
        return self


class ConstructionRoleAuditV2(_Frozen):
    candidate_reviewed_as_construction: bool
    overall_disposition: ConstructionDisposition
    construction_records: tuple[ConstructionRecordV2, ...] = Field(max_length=8)
    literal_path_basis: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def disposition_is_coherent(self):
        if not self.candidate_reviewed_as_construction:
            raise ValueError("CONSTRUCTION_REVIEW_REQUIRED")
        roles = {record.construction_role for record in self.construction_records}
        material = bool(roles & {ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
                                 ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD})
        unresolved = ConstructionRole.UNRESOLVED in roles
        if self.overall_disposition is ConstructionDisposition.NO_MATERIAL_CREATIVE_CONSTRUCTION:
            coherent = not material and not unresolved and bool(self.literal_path_basis)
        elif self.overall_disposition is ConstructionDisposition.ONE_OR_MORE_MATERIAL_CONSTRUCTIONS:
            coherent = material and not unresolved and self.literal_path_basis is None
        else:
            coherent = unresolved and self.literal_path_basis is None
        if not coherent:
            raise ValueError("CONSTRUCTION_DISPOSITION_INCOHERENT")
        ids = [record.construction_id for record in self.construction_records]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_CONSTRUCTION_ID")
        return self


class ConstructionRoleCoverageReceiptV2(_Frozen):
    candidate_reviewed_as_whole: bool
    embedded_propositions_checked: bool
    creative_scope_checked: bool
    unresolved_scope_present: bool
    overlapping_spans_reconciled: bool
    integrated_creative_hosts_checked: bool
    factual_return_tests_completed: bool
    creative_targets_enumerated: bool
    target_classes_reviewed: bool
    target_to_ledger_reconciled: bool
    construction_roles_reviewed: bool
    construction_to_ledger_reconciled: bool


class ConstructionObligationLedgerV2(_Frozen):
    schema_name: Literal[SCHEMA_NAME]
    schema_version: Literal[SCHEMA_VERSION]
    stage_id: str = Field(pattern=r"^PROPOSITION_LEDGER$")
    construction_role_audit: ConstructionRoleAuditV2
    entries: tuple[ScopeGraphEntryV2, ...] = Field(min_length=1, max_length=8)
    creative_target_audits: tuple[CreativeTargetAuditV2, ...] = Field(max_length=16)
    coverage_receipt: ConstructionRoleCoverageReceiptV2
    coverage_decision: CoverageDecision

    @model_validator(mode="after")
    def graph_is_coherent(self):
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_ENTRY_ID")
        index = {entry.entry_id: entry for entry in self.entries}
        for entry in self.entries:
            if entry.creative_host_entry_id is not None:
                host = index.get(entry.creative_host_entry_id)
                if host is None or host.entry_type is not EntryType.CONTAINED_CREATIVE:
                    raise ValueError("MISSING_OR_INVALID_CREATIVE_HOST")
        audit_ids = [audit.audit_id for audit in self.creative_target_audits]
        if len(audit_ids) != len(set(audit_ids)):
            raise ValueError("DUPLICATE_AUDIT_ID")
        creative_ids = {entry.entry_id for entry in self.entries
                        if entry.entry_type is EntryType.CONTAINED_CREATIVE}
        if creative_ids != {audit.creative_host_entry_id for audit in self.creative_target_audits}:
            raise ValueError("CREATIVE_HOST_AUDIT_COVERAGE_MISMATCH")
        mapped_hosts = {record.creative_host_entry_id
                        for record in self.construction_role_audit.construction_records
                        if record.creative_host_entry_id is not None}
        if creative_ids != mapped_hosts:
            raise ValueError("CONSTRUCTION_CREATIVE_HOST_COVERAGE_MISMATCH")
        for record in self.construction_role_audit.construction_records:
            for entry_id in record.literal_or_return_entry_ids:
                entry = index.get(entry_id)
                if entry is None or entry.entry_type is not EntryType.REAL_WORLD_COMMITMENT:
                    raise ValueError("CONSTRUCTION_LITERAL_OR_RETURN_INVALID")
                if (record.construction_role is ConstructionRole.MIXED_CREATIVE_AND_REAL_WORLD and
                        entry.creative_host_entry_id != record.creative_host_entry_id):
                    raise ValueError("MIXED_RETURN_HOST_MISMATCH")
        for audit in self.creative_target_audits:
            host = index.get(audit.creative_host_entry_id)
            if host is None or host.entry_type is not EntryType.CONTAINED_CREATIVE:
                raise ValueError("AUDIT_HOST_INVALID")
            if audit.target_class is CreativeTargetClass.REAL_WORLD_PROPOSITION:
                proposition = index.get(audit.proposition_entry_id)
                if (proposition is None or proposition.entry_type is not EntryType.REAL_WORLD_COMMITMENT or
                        proposition.scope_relation is not ScopeRelation.FACTUAL_RETURN_WITHIN_CREATIVE_HOST or
                        proposition.creative_host_entry_id != host.entry_id):
                    raise ValueError("TARGET_PROPOSITION_LINK_INVALID")
        unresolved = (any(entry.entry_type is EntryType.UNRESOLVED_SCOPE for entry in self.entries) or
                      any(audit.target_class is CreativeTargetClass.UNRESOLVED_TARGET
                          for audit in self.creative_target_audits) or
                      any(record.construction_role is ConstructionRole.UNRESOLVED
                          for record in self.construction_role_audit.construction_records))
        receipt_values = self.coverage_receipt.model_dump()
        complete_receipts = all(value for key, value in receipt_values.items()
                                if key != "unresolved_scope_present")
        if self.coverage_decision is CoverageDecision.COMPLETE:
            if unresolved or not complete_receipts or self.coverage_receipt.unresolved_scope_present:
                raise ValueError("COMPLETE_COVERAGE_INCOHERENT")
        elif not unresolved or not self.coverage_receipt.unresolved_scope_present:
            raise ValueError("INDETERMINATE_WITHOUT_UNRESOLVED")
        return self


class ProjectionStatusV1(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class SourceProjectionRecordV1(_Frozen):
    json_pointer: str
    required_source_role: SourceRoleV1
    observed_source_role: SourceRoleV1
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_utf8: int = Field(ge=0)
    end_utf8: int = Field(ge=0)
    projected_bytes: int | None = Field(default=None, ge=1)
    projected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: ProjectionStatusV1
    reason_code: str | None

    @model_validator(mode="after")
    def status_is_coherent(self):
        if self.status is ProjectionStatusV1.PASS:
            if self.reason_code is not None or self.projected_bytes is None or self.projected_sha256 is None:
                raise ValueError("PASS_PROJECTION_RECORD_INCOHERENT")
        elif self.reason_code is None or self.projected_bytes is not None or self.projected_sha256 is not None:
            raise ValueError("FAIL_PROJECTION_RECORD_INCOHERENT")
        return self


class SourceProjectionReceiptV1(_Frozen):
    schema_name: str = PROJECTION_RECEIPT_SCHEMA_NAME
    schema_version: str = PROJECTION_RECEIPT_SCHEMA_VERSION
    raw_response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response_bytes: int = Field(ge=0)
    candidate_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_source_bytes: int = Field(ge=0)
    factual_authority_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    factual_authority_source_bytes: int = Field(ge=0)
    reference_candidate_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    projection_records: tuple[SourceProjectionRecordV1, ...]
    projection_status: ProjectionStatusV1
    reason_code: str | None

    @model_validator(mode="after")
    def terminal_status_is_coherent(self):
        pointers = [record.json_pointer for record in self.projection_records]
        if pointers != sorted(pointers) or len(pointers) != len(set(pointers)):
            raise ValueError("PROJECTION_RECORD_ORDER_OR_IDENTITY_INCOHERENT")
        failures = [record for record in self.projection_records
                    if record.status is ProjectionStatusV1.FAIL]
        if self.projection_status is ProjectionStatusV1.PASS:
            if failures or self.reason_code is not None:
                raise ValueError("PASS_PROJECTION_RECEIPT_INCOHERENT")
        elif not failures or self.reason_code != failures[0].reason_code:
            raise ValueError("FAIL_PROJECTION_RECEIPT_INCOHERENT")
        return self


def _reference_inventory(ledger: ConstructionObligationLedgerV2):
    items = []
    for index, record in enumerate(ledger.construction_role_audit.construction_records):
        items.append((f"/construction_role_audit/construction_records/{index}/candidate_span_ref",
                      SourceRoleV1.CANDIDATE, record.candidate_span_ref))
    for index, entry in enumerate(ledger.entries):
        items.append((f"/entries/{index}/candidate_span_ref", SourceRoleV1.CANDIDATE,
                      entry.candidate_span_ref))
        if entry.authority_support_ref is not None:
            items.append((f"/entries/{index}/authority_support_ref", SourceRoleV1.FACTUAL_AUTHORITY,
                          entry.authority_support_ref))
    for index, audit in enumerate(ledger.creative_target_audits):
        items.append((f"/creative_target_audits/{index}/vehicle_span_ref", SourceRoleV1.CANDIDATE,
                      audit.vehicle_span_ref))
    return tuple(sorted(items, key=lambda item: item[0]))


def build_source_projection_receipt_v1(
    *, raw_response: bytes, ledger: ConstructionObligationLedgerV2,
    candidate_source: ImmutableUtf8SourceV1,
    factual_authority_source: ImmutableUtf8SourceV1,
) -> SourceProjectionReceiptV1:
    """Resolve every provenance reference and return a deterministic receipt."""
    if candidate_source.role is not SourceRoleV1.CANDIDATE:
        raise ValueError("CANDIDATE_SOURCE_ROLE_MISMATCH")
    if factual_authority_source.role is not SourceRoleV1.FACTUAL_AUTHORITY:
        raise ValueError("FACTUAL_AUTHORITY_SOURCE_ROLE_MISMATCH")
    sources = {candidate_source.role: candidate_source,
               factual_authority_source.role: factual_authority_source}
    records = []
    first_failure = None
    for pointer, expected_role, reference in _reference_inventory(ledger):
        try:
            resolved = resolve_source_span_v1(reference, expected_role=expected_role, sources=sources)
        except SourceProjectionErrorV1 as exc:
            first_failure = first_failure or exc.code.value
            records.append(SourceProjectionRecordV1(
                json_pointer=pointer, required_source_role=expected_role,
                observed_source_role=reference.source_role, source_sha256=reference.source_sha256,
                start_utf8=reference.start_utf8, end_utf8=reference.end_utf8,
                status=ProjectionStatusV1.FAIL, reason_code=exc.code.value))
        else:
            records.append(SourceProjectionRecordV1(
                json_pointer=pointer, required_source_role=expected_role,
                observed_source_role=reference.source_role, source_sha256=reference.source_sha256,
                start_utf8=reference.start_utf8, end_utf8=reference.end_utf8,
                projected_bytes=len(resolved.projected_bytes),
                projected_sha256=resolved.projected_sha256,
                status=ProjectionStatusV1.PASS, reason_code=None))
    status = ProjectionStatusV1.FAIL if first_failure else ProjectionStatusV1.PASS
    return SourceProjectionReceiptV1(
        raw_response_sha256=hashlib.sha256(bytes(raw_response)).hexdigest(),
        raw_response_bytes=len(raw_response), candidate_source_sha256=candidate_source.sha256,
        candidate_source_bytes=len(candidate_source.data),
        factual_authority_source_sha256=factual_authority_source.sha256,
        factual_authority_source_bytes=len(factual_authority_source.data),
        reference_candidate_identity=REFERENCE_CANDIDATE_IDENTITY,
        projection_records=tuple(records), projection_status=status, reason_code=first_failure)


def canonical_projection_receipt_bytes_v1(receipt: SourceProjectionReceiptV1) -> bytes:
    return (json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


__all__ = (
    "ConstructionObligationLedgerV2", "ConstructionRecordV2", "ConstructionRoleAuditV2",
    "ConstructionRoleCoverageReceiptV2", "CreativeTargetAuditV2", "ProjectionStatusV1",
    "SCHEMA_NAME", "SCHEMA_VERSION", "ScopeGraphEntryV2", "SourceProjectionReceiptV1",
    "SourceProjectionRecordV1", "build_source_projection_receipt_v1",
    "canonical_projection_receipt_bytes_v1",
)
