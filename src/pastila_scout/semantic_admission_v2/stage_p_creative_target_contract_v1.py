"""Evaluation-only Stage P contract with auditable creative-target decomposition."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .stage_p_role_coherence_contract_v1 import EntryType
from .stage_p_scope_graph_contract_v1 import ScopeRelation, _any_overlap, _occurrences
from .stage_p_scope_graph_contract_v1_1 import ScopeGraphEntryV1_1, ScopeGraphLedgerV1_1


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreativeTargetClass(StrEnum):
    NONFACTUAL_EDITORIAL_OR_CREATIVE = "NONFACTUAL_EDITORIAL_OR_CREATIVE"
    REAL_WORLD_PROPOSITION = "REAL_WORLD_PROPOSITION"
    UNRESOLVED_TARGET = "UNRESOLVED_TARGET"


class CreativeTargetSurvivalBasis(StrEnum):
    DOES_NOT_SURVIVE_AS_FACT = "DOES_NOT_SURVIVE_AS_FACT"
    ASSERTION_SURVIVES = "ASSERTION_SURVIVES"
    PRESUPPOSITION_SURVIVES = "PRESUPPOSITION_SURVIVES"
    ENTAILMENT_SURVIVES = "ENTAILMENT_SURVIVES"
    NECESSARY_IMPLICATION_SURVIVES = "NECESSARY_IMPLICATION_SURVIVES"
    UNRESOLVED = "UNRESOLVED"


class CreativeTargetResolution(StrEnum):
    RETAINED_NONFACTUAL = "RETAINED_NONFACTUAL"
    RECONCILED_TO_LEDGER = "RECONCILED_TO_LEDGER"
    FAIL_CLOSED_UNRESOLVED = "FAIL_CLOSED_UNRESOLVED"


_SURVIVING = {
    CreativeTargetSurvivalBasis.ASSERTION_SURVIVES,
    CreativeTargetSurvivalBasis.PRESUPPOSITION_SURVIVES,
    CreativeTargetSurvivalBasis.ENTAILMENT_SURVIVES,
    CreativeTargetSurvivalBasis.NECESSARY_IMPLICATION_SURVIVES,
}


class CreativeTargetAuditV1(_Frozen):
    audit_id: str = Field(pattern=r"^T(?:[1-9]|1[0-6])$")
    creative_host_entry_id: str = Field(pattern=r"^P[1-8]$")
    vehicle_span: str = Field(min_length=1)
    semantic_target: str = Field(min_length=1, max_length=500)
    target_class: CreativeTargetClass
    survival_basis: CreativeTargetSurvivalBasis
    proposition_entry_id: str | None = Field(default=None, pattern=r"^P[1-8]$")
    resolution: CreativeTargetResolution

    @model_validator(mode="after")
    def tuple_is_coherent(self):
        if self.target_class is CreativeTargetClass.NONFACTUAL_EDITORIAL_OR_CREATIVE:
            if (self.survival_basis is not CreativeTargetSurvivalBasis.DOES_NOT_SURVIVE_AS_FACT or
                    self.proposition_entry_id is not None or
                    self.resolution is not CreativeTargetResolution.RETAINED_NONFACTUAL):
                raise ValueError("NONFACTUAL_TARGET_INCOHERENT")
        elif self.target_class is CreativeTargetClass.REAL_WORLD_PROPOSITION:
            if (self.survival_basis not in _SURVIVING or self.proposition_entry_id is None or
                    self.resolution is not CreativeTargetResolution.RECONCILED_TO_LEDGER):
                raise ValueError("REAL_WORLD_TARGET_INCOHERENT")
        elif (self.survival_basis is not CreativeTargetSurvivalBasis.UNRESOLVED or
              self.proposition_entry_id is not None or
              self.resolution is not CreativeTargetResolution.FAIL_CLOSED_UNRESOLVED):
            raise ValueError("UNRESOLVED_TARGET_INCOHERENT")
        return self


class CreativeTargetCoverageReceiptV1(_Frozen):
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


class CreativeTargetLedgerV1(_Frozen):
    stage_id: str = Field(pattern=r"^PROPOSITION_LEDGER$")
    entries: tuple[ScopeGraphEntryV1_1, ...] = Field(min_length=1, max_length=8)
    creative_target_audits: tuple[CreativeTargetAuditV1, ...] = Field(max_length=16)
    coverage_receipt: CreativeTargetCoverageReceiptV1
    coverage_decision: str = Field(pattern=r"^(COMPLETE|INDETERMINATE)$")

    @model_validator(mode="after")
    def graph_targets_and_coverage_are_coherent(self):
        base_receipt = {key: getattr(self.coverage_receipt, key) for key in (
            "candidate_reviewed_as_whole", "embedded_propositions_checked", "creative_scope_checked",
            "unresolved_scope_present", "overlapping_spans_reconciled",
            "integrated_creative_hosts_checked", "factual_return_tests_completed")}
        ScopeGraphLedgerV1_1.model_validate({"stage_id": self.stage_id,
            "entries": [entry.model_dump(mode="json") for entry in self.entries],
            "coverage_receipt": base_receipt, "coverage_decision": self.coverage_decision}, strict=False)
        entry_index = {entry.entry_id: entry for entry in self.entries}
        if len(entry_index) != len(self.entries):
            raise ValueError("DUPLICATE_ENTRY_ID")
        audit_ids = [audit.audit_id for audit in self.creative_target_audits]
        if len(audit_ids) != len(set(audit_ids)):
            raise ValueError("DUPLICATE_AUDIT_ID")
        creative_ids = {entry.entry_id for entry in self.entries if entry.entry_type is EntryType.CONTAINED_CREATIVE}
        audited_ids = {audit.creative_host_entry_id for audit in self.creative_target_audits}
        if creative_ids != audited_ids:
            raise ValueError("CREATIVE_HOST_AUDIT_COVERAGE_MISMATCH")
        unresolved_target = False
        for audit in self.creative_target_audits:
            host = entry_index.get(audit.creative_host_entry_id)
            if host is None or host.entry_type is not EntryType.CONTAINED_CREATIVE:
                raise ValueError("AUDIT_HOST_INVALID")
            if audit.target_class is CreativeTargetClass.REAL_WORLD_PROPOSITION:
                proposition = entry_index.get(audit.proposition_entry_id)
                if (proposition is None or proposition.entry_type is not EntryType.REAL_WORLD_COMMITMENT or
                        proposition.scope_relation is not ScopeRelation.FACTUAL_RETURN_WITHIN_CREATIVE_HOST or
                        proposition.creative_host_entry_id != host.entry_id or
                        host.scope_relation is not ScopeRelation.CREATIVE_HOST):
                    raise ValueError("TARGET_PROPOSITION_LINK_INVALID")
            unresolved_target |= audit.target_class is CreativeTargetClass.UNRESOLVED_TARGET
        unresolved_entry = any(entry.entry_type is EntryType.UNRESOLVED_SCOPE for entry in self.entries)
        if unresolved_target and not unresolved_entry:
            raise ValueError("UNRESOLVED_TARGET_REQUIRES_UNRESOLVED_ENTRY")
        receipt = self.coverage_receipt
        complete_receipts = all((receipt.candidate_reviewed_as_whole, receipt.embedded_propositions_checked,
            receipt.creative_scope_checked, receipt.overlapping_spans_reconciled,
            receipt.integrated_creative_hosts_checked, receipt.factual_return_tests_completed,
            receipt.creative_targets_enumerated, receipt.target_classes_reviewed,
            receipt.target_to_ledger_reconciled)) and not receipt.unresolved_scope_present
        if self.coverage_decision == "COMPLETE":
            if unresolved_target or unresolved_entry or not complete_receipts:
                raise ValueError("COMPLETE_TARGET_COVERAGE_INCOHERENT")
        elif not receipt.unresolved_scope_present or not (unresolved_target or unresolved_entry):
            raise ValueError("INDETERMINATE_WITHOUT_UNRESOLVED_TARGET_OR_ENTRY")
        return self


def validate_creative_target_sources(ledger: CreativeTargetLedgerV1, *, factual_summary: str, candidate: str) -> None:
    positions = {entry.entry_id: _occurrences(candidate, entry.candidate_span) for entry in ledger.entries}
    for entry in ledger.entries:
        if not positions[entry.entry_id]:
            raise ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")
        if entry.authority_support is not None and entry.authority_support not in factual_summary:
            raise ValueError("AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY")
    for audit in ledger.creative_target_audits:
        vehicle = _occurrences(candidate, audit.vehicle_span)
        if not vehicle:
            raise ValueError("AUDIT_VEHICLE_NOT_IN_CANDIDATE")
        if not _any_overlap(vehicle, positions[audit.creative_host_entry_id]):
            raise ValueError("AUDIT_VEHICLE_DOES_NOT_OVERLAP_HOST")
        if audit.proposition_entry_id is not None and not _any_overlap(
                positions[audit.proposition_entry_id], positions[audit.creative_host_entry_id]):
            raise ValueError("TARGET_PROPOSITION_DOES_NOT_OVERLAP_HOST")


__all__ = ("CreativeTargetAuditV1", "CreativeTargetClass", "CreativeTargetCoverageReceiptV1",
           "CreativeTargetLedgerV1", "CreativeTargetResolution", "CreativeTargetSurvivalBasis",
           "validate_creative_target_sources")
