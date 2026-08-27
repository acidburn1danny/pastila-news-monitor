"""Evaluation-only Scope Graph V1.1 contract with governed-support coherence."""
from __future__ import annotations

from pydantic import Field, model_validator

from .stage_p_role_coherence_contract_v1 import EventAlignment
from .stage_p_scope_graph_contract_v1 import (
    ScopeGraphCoverageReceiptV1,
    ScopeGraphEntryV1,
    ScopeGraphLedgerV1,
    validate_scope_graph_sources,
)


class ScopeGraphEntryV1_1(ScopeGraphEntryV1):
    @model_validator(mode="after")
    def governed_event_has_cited_authority(self):
        if self.event_alignment is EventAlignment.GOVERNED_EVENT and self.authority_support is None:
            raise ValueError("GOVERNED_EVENT_REQUIRES_AUTHORITY_SUPPORT")
        return self


class ScopeGraphLedgerV1_1(ScopeGraphLedgerV1):
    entries: tuple[ScopeGraphEntryV1_1, ...] = Field(min_length=1, max_length=8)


__all__ = ("ScopeGraphCoverageReceiptV1", "ScopeGraphEntryV1_1", "ScopeGraphLedgerV1_1",
           "validate_scope_graph_sources")
