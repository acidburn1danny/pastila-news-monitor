"""Evaluation-only Scope Graph V1.2 DFA with early coverage-decision projection."""
from __future__ import annotations

from dataclasses import replace

from .stage_p_scope_graph_constraint_v1_1 import StagePScopeGraphConstraintStateV1_1


class StagePScopeGraphConstraintStateV1_2(StagePScopeGraphConstraintStateV1_1):
    """Project receipt/ledger coherence before a coverage value is emitted."""

    def _advance(self, step: str, value: str | None = None):
        if step == "COVERAGE":
            complete = (
                not self.unresolved_seen
                and not self.receipt_unresolved
                and bool(self.receipt_whole)
                and bool(self.receipt_embedded)
                and bool(self.receipt_creative)
                and bool(self.receipt_overlaps)
                and bool(self.receipt_hosts)
                and bool(self.receipt_returns)
            )
            indeterminate = bool(self.unresolved_seen) and bool(self.receipt_unresolved)
            if complete:
                choices = ("COMPLETE",)
            elif indeterminate:
                choices = ("INDETERMINATE",)
            else:
                self._fail("NO_COHERENT_COVERAGE_DECISION")
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="COVERAGE_END")
        return super()._advance(step, value)


__all__ = ("StagePScopeGraphConstraintStateV1_2",)
