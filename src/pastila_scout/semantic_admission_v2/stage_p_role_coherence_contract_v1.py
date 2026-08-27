"""Evaluation-only Stage P role-coherence schema with no execution edge."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EntryType(StrEnum):
    REAL_WORLD_COMMITMENT = "REAL_WORLD_COMMITMENT"
    CONTAINED_CREATIVE = "CONTAINED_CREATIVE"
    UNRESOLVED_SCOPE = "UNRESOLVED_SCOPE"


class ScopeBasis(StrEnum):
    ASSERTED = "ASSERTED"
    PRESUPPOSED = "PRESUPPOSED"
    ENTAILED = "ENTAILED"
    NECESSARILY_IMPLIED = "NECESSARILY_IMPLIED"
    CREATIVE_CONTAINED = "CREATIVE_CONTAINED"
    UNRESOLVED = "UNRESOLVED"


class EventAlignment(StrEnum):
    GOVERNED_EVENT = "GOVERNED_EVENT"
    NEW_UNSUPPORTED_EVENT = "NEW_UNSUPPORTED_EVENT"
    CREATIVE_VEHICLE_ONLY = "CREATIVE_VEHICLE_ONLY"
    UNRESOLVED = "UNRESOLVED"


class Modality(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    POSSIBLE = "POSSIBLE"
    CONDITIONAL = "CONDITIONAL"
    PROPOSED = "PROPOSED"
    EXPECTED = "EXPECTED"
    CERTAIN_OR_ACTUAL = "CERTAIN_OR_ACTUAL"
    UNRESOLVED = "UNRESOLVED"


class Timing(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PAST = "PAST"
    PRESENT = "PRESENT"
    ONGOING = "ONGOING"
    FUTURE = "FUTURE"
    COMPLETED = "COMPLETED"
    UNDATED = "UNDATED"
    UNRESOLVED = "UNRESOLVED"


class CoverageDecision(StrEnum):
    COMPLETE = "COMPLETE"
    INDETERMINATE = "INDETERMINATE"


class RoleCoherentEntryV1(_Frozen):
    entry_id: str = Field(pattern=r"^P[1-8]$")
    entry_type: EntryType
    candidate_span: str = Field(min_length=1)
    authority_support: str | None
    commitment: str = Field(min_length=1, max_length=500)
    scope_basis: ScopeBasis
    event_alignment: EventAlignment
    authority_modality: Modality
    candidate_modality: Modality
    authority_timing: Timing
    candidate_timing: Timing
    independence_group: str = Field(pattern=r"^G[1-8]$")

    @model_validator(mode="after")
    def role_is_coherent(self):
        if self.entry_type is EntryType.CONTAINED_CREATIVE:
            expected = (
                self.scope_basis is ScopeBasis.CREATIVE_CONTAINED,
                self.event_alignment is EventAlignment.CREATIVE_VEHICLE_ONLY,
                self.authority_modality is Modality.NOT_APPLICABLE,
                self.candidate_modality is Modality.NOT_APPLICABLE,
                self.authority_timing is Timing.NOT_APPLICABLE,
                self.candidate_timing is Timing.NOT_APPLICABLE,
            )
            if not all(expected):
                raise ValueError("CONTAINED_CREATIVE_ROLE_INCOHERENT")
        elif self.entry_type is EntryType.REAL_WORLD_COMMITMENT:
            if self.scope_basis not in {
                ScopeBasis.ASSERTED, ScopeBasis.PRESUPPOSED, ScopeBasis.ENTAILED,
                ScopeBasis.NECESSARILY_IMPLIED,
            }:
                raise ValueError("REAL_WORLD_SCOPE_INCOHERENT")
            if self.event_alignment not in {
                EventAlignment.GOVERNED_EVENT, EventAlignment.NEW_UNSUPPORTED_EVENT,
            }:
                raise ValueError("REAL_WORLD_EVENT_INCOHERENT")
            if self.candidate_modality in {Modality.NOT_APPLICABLE, Modality.UNRESOLVED}:
                raise ValueError("REAL_WORLD_CANDIDATE_MODALITY_INCOHERENT")
            if self.candidate_timing in {Timing.NOT_APPLICABLE, Timing.UNRESOLVED}:
                raise ValueError("REAL_WORLD_CANDIDATE_TIMING_INCOHERENT")
            if self.authority_support is None:
                if self.authority_modality is not Modality.NOT_APPLICABLE or self.authority_timing is not Timing.NOT_APPLICABLE:
                    raise ValueError("NULL_AUTHORITY_AXES_INCOHERENT")
            elif self.authority_modality in {Modality.NOT_APPLICABLE, Modality.UNRESOLVED} or self.authority_timing in {
                Timing.NOT_APPLICABLE, Timing.UNRESOLVED,
            }:
                raise ValueError("SUPPORTED_AUTHORITY_AXES_INCOHERENT")
        else:
            if not (
                self.scope_basis is ScopeBasis.UNRESOLVED
                or self.event_alignment is EventAlignment.UNRESOLVED
                or self.candidate_modality is Modality.UNRESOLVED
                or self.candidate_timing is Timing.UNRESOLVED
            ):
                raise ValueError("UNRESOLVED_SCOPE_WITHOUT_UNRESOLVED_AXIS")
        return self


class CoverageReceiptV1(_Frozen):
    candidate_reviewed_as_whole: bool
    embedded_propositions_checked: bool
    creative_scope_checked: bool
    unresolved_scope_present: bool


class RoleCoherentLedgerV1(_Frozen):
    stage_id: str = Field(pattern=r"^PROPOSITION_LEDGER$")
    entries: tuple[RoleCoherentEntryV1, ...] = Field(min_length=1, max_length=8)
    coverage_receipt: CoverageReceiptV1
    coverage_decision: CoverageDecision

    @model_validator(mode="after")
    def coverage_follows_evidence(self):
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_ENTRY_ID")
        unresolved = any(entry.entry_type is EntryType.UNRESOLVED_SCOPE for entry in self.entries)
        receipt = self.coverage_receipt
        if self.coverage_decision is CoverageDecision.COMPLETE:
            if unresolved or receipt.unresolved_scope_present or not (
                receipt.candidate_reviewed_as_whole
                and receipt.embedded_propositions_checked
                and receipt.creative_scope_checked
            ):
                raise ValueError("COMPLETE_COVERAGE_INCOHERENT")
        elif not unresolved or not receipt.unresolved_scope_present:
            raise ValueError("INDETERMINATE_WITHOUT_UNRESOLVED_SCOPE")
        return self


def validate_role_coherent_source_membership(
    ledger: RoleCoherentLedgerV1, *, factual_summary: str, candidate: str,
) -> None:
    for entry in ledger.entries:
        if entry.candidate_span not in candidate:
            raise ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")
        if entry.authority_support is not None and entry.authority_support not in factual_summary:
            raise ValueError("AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY")


__all__ = ("RoleCoherentLedgerV1", "validate_role_coherent_source_membership")
