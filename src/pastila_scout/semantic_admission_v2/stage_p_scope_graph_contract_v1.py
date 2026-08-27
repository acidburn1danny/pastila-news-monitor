"""Evaluation-only Stage P scope-graph schema and deterministic validators."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel,ConfigDict,Field,model_validator

from .stage_p_role_coherence_contract_v1 import (
    CoverageDecision, CoverageReceiptV1, EntryType, RoleCoherentEntryV1,
)


class _Frozen(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True,strict=True)


class ScopeRelation(StrEnum):
    STANDALONE="STANDALONE"
    CREATIVE_HOST="CREATIVE_HOST"
    FACTUAL_RETURN_WITHIN_CREATIVE_HOST="FACTUAL_RETURN_WITHIN_CREATIVE_HOST"
    UNRESOLVED_RELATION="UNRESOLVED_RELATION"


class FactualReturnBasis(StrEnum):
    NOT_APPLICABLE="NOT_APPLICABLE"
    ASSERTION_SURVIVES="ASSERTION_SURVIVES"
    PRESUPPOSITION_SURVIVES="PRESUPPOSITION_SURVIVES"
    ENTAILMENT_SURVIVES="ENTAILMENT_SURVIVES"
    NECESSARY_IMPLICATION_SURVIVES="NECESSARY_IMPLICATION_SURVIVES"
    UNRESOLVED="UNRESOLVED"


SURVIVING_BASES={
    FactualReturnBasis.ASSERTION_SURVIVES,FactualReturnBasis.PRESUPPOSITION_SURVIVES,
    FactualReturnBasis.ENTAILMENT_SURVIVES,FactualReturnBasis.NECESSARY_IMPLICATION_SURVIVES,
}


class ScopeGraphEntryV1(RoleCoherentEntryV1):
    scope_relation:ScopeRelation
    creative_host_entry_id:str|None=Field(default=None,pattern=r"^P[1-8]$")
    factual_return_basis:FactualReturnBasis

    @model_validator(mode="after")
    def relation_is_locally_coherent(self):
        if self.scope_relation is ScopeRelation.CREATIVE_HOST:
            if self.entry_type is not EntryType.CONTAINED_CREATIVE or self.creative_host_entry_id is not None or self.factual_return_basis is not FactualReturnBasis.NOT_APPLICABLE:
                raise ValueError("CREATIVE_HOST_RELATION_INCOHERENT")
        elif self.scope_relation is ScopeRelation.FACTUAL_RETURN_WITHIN_CREATIVE_HOST:
            if self.entry_type is not EntryType.REAL_WORLD_COMMITMENT or self.creative_host_entry_id is None or self.factual_return_basis not in SURVIVING_BASES:
                raise ValueError("FACTUAL_RETURN_RELATION_INCOHERENT")
            if self.creative_host_entry_id==self.entry_id: raise ValueError("SELF_HOST_REFERENCE")
        elif self.scope_relation is ScopeRelation.STANDALONE:
            if self.creative_host_entry_id is not None: raise ValueError("STANDALONE_HAS_HOST")
            if self.entry_type is EntryType.CONTAINED_CREATIVE:
                if self.factual_return_basis is not FactualReturnBasis.NOT_APPLICABLE: raise ValueError("STANDALONE_CREATIVE_BASIS")
            elif self.entry_type is EntryType.REAL_WORLD_COMMITMENT:
                if self.factual_return_basis not in SURVIVING_BASES: raise ValueError("STANDALONE_REAL_BASIS")
            else: raise ValueError("UNRESOLVED_ENTRY_CANNOT_BE_STANDALONE")
        else:
            if self.entry_type is not EntryType.UNRESOLVED_SCOPE or self.factual_return_basis is not FactualReturnBasis.UNRESOLVED:
                raise ValueError("UNRESOLVED_RELATION_INCOHERENT")
        return self


class ScopeGraphCoverageReceiptV1(CoverageReceiptV1):
    overlapping_spans_reconciled:bool
    integrated_creative_hosts_checked:bool
    factual_return_tests_completed:bool


class ScopeGraphLedgerV1(_Frozen):
    stage_id:str=Field(pattern=r"^PROPOSITION_LEDGER$")
    entries:tuple[ScopeGraphEntryV1,...]=Field(min_length=1,max_length=8)
    coverage_receipt:ScopeGraphCoverageReceiptV1
    coverage_decision:CoverageDecision

    @model_validator(mode="after")
    def graph_and_coverage_are_coherent(self):
        ids=[entry.entry_id for entry in self.entries]
        if len(ids)!=len(set(ids)): raise ValueError("DUPLICATE_ENTRY_ID")
        index={entry.entry_id:entry for entry in self.entries}
        for entry in self.entries:
            host_id=entry.creative_host_entry_id
            if host_id is not None:
                host=index.get(host_id)
                if host is None: raise ValueError("MISSING_CREATIVE_HOST")
                if host.entry_type is not EntryType.CONTAINED_CREATIVE or host.scope_relation is not ScopeRelation.CREATIVE_HOST:
                    raise ValueError("HOST_IS_NOT_CREATIVE_HOST")
        _assert_acyclic(index)
        unresolved=any(entry.entry_type is EntryType.UNRESOLVED_SCOPE or entry.scope_relation is ScopeRelation.UNRESOLVED_RELATION
                       or entry.factual_return_basis is FactualReturnBasis.UNRESOLVED for entry in self.entries)
        receipt=self.coverage_receipt
        complete_receipts=(receipt.candidate_reviewed_as_whole and receipt.embedded_propositions_checked
            and receipt.creative_scope_checked and receipt.overlapping_spans_reconciled
            and receipt.integrated_creative_hosts_checked and receipt.factual_return_tests_completed
            and not receipt.unresolved_scope_present)
        if self.coverage_decision is CoverageDecision.COMPLETE:
            if unresolved or not complete_receipts: raise ValueError("COMPLETE_SCOPE_GRAPH_INCOHERENT")
        elif not unresolved or not receipt.unresolved_scope_present:
            raise ValueError("INDETERMINATE_SCOPE_GRAPH_WITHOUT_UNRESOLVED")
        return self


def _assert_acyclic(index:dict[str,ScopeGraphEntryV1])->None:
    for start in index:
        seen=set();current=start
        while current is not None:
            if current in seen: raise ValueError("CYCLIC_CREATIVE_HOST_REFERENCE")
            seen.add(current);entry=index.get(current);current=entry.creative_host_entry_id if entry else None


def validate_scope_graph_sources(ledger:ScopeGraphLedgerV1,*,factual_summary:str,candidate:str)->None:
    index={entry.entry_id:entry for entry in ledger.entries}
    positions={entry.entry_id:_occurrences(candidate,entry.candidate_span) for entry in ledger.entries}
    for entry in ledger.entries:
        if not positions[entry.entry_id]: raise ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")
        if entry.authority_support is not None and entry.authority_support not in factual_summary:
            raise ValueError("AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY")
        if entry.creative_host_entry_id is not None:
            host=index[entry.creative_host_entry_id]
            if not _any_overlap(positions[entry.entry_id],positions[host.entry_id]):
                raise ValueError("FACTUAL_RETURN_DOES_NOT_OVERLAP_CREATIVE_HOST")


def _occurrences(text:str,span:str)->tuple[tuple[int,int],...]:
    found=[];start=0
    while True:
        position=text.find(span,start)
        if position<0: return tuple(found)
        found.append((position,position+len(span)));start=position+1


def _any_overlap(left,right)->bool:
    return any(a0<b1 and b0<a1 for a0,a1 in left for b0,b1 in right)


__all__=("FactualReturnBasis","ScopeGraphEntryV1","ScopeGraphLedgerV1","ScopeRelation","validate_scope_graph_sources")
