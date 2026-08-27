"""Zero-inference character constraint for the approved Stage P scope graph schema."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_role_coherence_constraint_v2 import StagePRoleCoherenceConstraintStateV2
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1


SCOPE_RELATIONS = ("STANDALONE", "CREATIVE_HOST", "FACTUAL_RETURN_WITHIN_CREATIVE_HOST", "UNRESOLVED_RELATION")
FACTUAL_RETURN_BASES = ("NOT_APPLICABLE", "ASSERTION_SURVIVES", "PRESUPPOSITION_SURVIVES",
                        "ENTAILMENT_SURVIVES", "NECESSARY_IMPLICATION_SURVIVES", "UNRESOLVED")
SURVIVING_BASES = FACTUAL_RETURN_BASES[1:5]


@dataclass(frozen=True)
class StagePScopeGraphConstraintStateV1(StagePRoleCoherenceConstraintStateV2):
    current_entry_id: str | None = None
    current_scope_relation: str | None = None
    current_host_id: str | None = None
    current_return_basis: str | None = None
    graph_entries: tuple[tuple[str, str, str, str | None, str], ...] = ()
    receipt_overlaps: bool | None = None
    receipt_hosts: bool | None = None
    receipt_returns: bool | None = None

    def _advance(self, step: str, value: str | None = None) -> "StagePScopeGraphConstraintStateV1":
        if step == "ENTRY_TYPE_LITERAL":
            return replace(super()._advance(step, value), current_entry_id=value)
        if step == "GROUP":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f"G{i}" for i in range(1, 9)),
                           next_step="SCOPE_REL_LITERAL")
        if step == "SCOPE_REL_LITERAL":
            return replace(self, mode="LITERAL", remaining='","scope_relation":"', next_step="SCOPE_REL")
        if step == "SCOPE_REL":
            return replace(self, mode="CHOICE", buffer="", choices=self._scope_relation_choices(),
                           next_step="HOST_LITERAL")
        if step == "HOST_LITERAL":
            return replace(self, current_scope_relation=value, mode="LITERAL",
                           remaining='","creative_host_entry_id":', next_step="HOST")
        if step == "HOST":
            choices = ("null",) if self.current_scope_relation != "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" else tuple(f'"P{i}"' for i in range(1, 9))
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="RETURN_BASIS_LITERAL")
        if step == "RETURN_BASIS_LITERAL":
            host = None if value == "null" else value.strip('"')
            return replace(self, current_host_id=host, mode="LITERAL",
                           remaining=',"factual_return_basis":"', next_step="RETURN_BASIS")
        if step == "RETURN_BASIS":
            return replace(self, mode="CHOICE", buffer="", choices=self._return_basis_choices(), next_step="ENTRY_END_SCOPE")
        if step == "ENTRY_END_SCOPE":
            state = replace(self, current_return_basis=value)
            state._validate_current_entry()
            state._validate_scope_relation()
            record = (state.current_entry_id, state.current_entry_type, state.current_scope_relation,
                      state.current_host_id, state.current_return_basis)
            return replace(state, graph_entries=state.graph_entries + (record,), mode="LITERAL",
                           remaining='"}', next_step="AFTER_ENTRY")
        if step == "AFTER_RECEIPT_UNRESOLVED":
            return replace(self, receipt_unresolved=value == "true", mode="LITERAL",
                           remaining=',"overlapping_spans_reconciled":', next_step="OVERLAPS")
        if step in {"OVERLAPS", "HOSTS", "RETURNS"}:
            return replace(self, mode="CHOICE", buffer="", choices=("false", "true"), next_step=f"AFTER_{step}")
        if step == "AFTER_OVERLAPS":
            return replace(self, receipt_overlaps=value == "true", mode="LITERAL",
                           remaining=',"integrated_creative_hosts_checked":', next_step="HOSTS")
        if step == "AFTER_HOSTS":
            return replace(self, receipt_hosts=value == "true", mode="LITERAL",
                           remaining=',"factual_return_tests_completed":', next_step="RETURNS")
        if step == "AFTER_RETURNS":
            return replace(self, receipt_returns=value == "true", mode="LITERAL",
                           remaining='},"coverage_decision":"', next_step="COVERAGE")
        if step == "TERMINAL":
            self._validate_graph()
            if self.coverage == "COMPLETE" and not (self.receipt_overlaps and self.receipt_hosts and self.receipt_returns):
                self._fail("INVALID_COMPLETE_SCOPE_RECEIPTS")
        return super()._advance(step, value)

    def _entry_start(self) -> "StagePScopeGraphConstraintStateV1":
        return replace(super()._entry_start(), current_entry_id=None, current_scope_relation=None,
                       current_host_id=None, current_return_basis=None)

    def _scope_relation_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("STANDALONE", "CREATIVE_HOST")
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return ("STANDALONE", "FACTUAL_RETURN_WITHIN_CREATIVE_HOST")
        return ("UNRESOLVED_RELATION",)

    def _return_basis_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("NOT_APPLICABLE",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return SURVIVING_BASES
        return ("UNRESOLVED",)

    def _validate_scope_relation(self) -> None:
        relation, host = self.current_scope_relation, self.current_host_id
        if relation == "FACTUAL_RETURN_WITHIN_CREATIVE_HOST":
            if host is None or host == self.current_entry_id:
                self._fail("INVALID_FACTUAL_RETURN_HOST")
        elif host is not None:
            self._fail("UNEXPECTED_CREATIVE_HOST")

    def _validate_graph(self) -> None:
        ids = [record[0] for record in self.graph_entries]
        if len(ids) != len(set(ids)):
            self._fail("DUPLICATE_ENTRY_ID")
        index = {record[0]: record for record in self.graph_entries}
        for _, _, _, host, _ in self.graph_entries:
            if host is not None:
                target = index.get(host)
                if target is None:
                    self._fail("MISSING_CREATIVE_HOST")
                if target[1] != "CONTAINED_CREATIVE" or target[2] != "CREATIVE_HOST":
                    self._fail("HOST_IS_NOT_CREATIVE_HOST")


__all__ = ("StagePScopeGraphConstraintStateV1", "StagePRoleCoherenceConstraintViolationV1")
