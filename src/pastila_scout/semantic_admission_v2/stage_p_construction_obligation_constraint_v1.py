"""Evaluation-only DFA projecting construction declarations into entry obligations."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_construction_role_constraint_v1 import StagePConstructionRoleConstraintStateV1


@dataclass(frozen=True)
class StagePConstructionObligationConstraintStateV1(StagePConstructionRoleConstraintStateV1):
    """Condition later entry roles on earlier construction-record identifiers."""

    def _feed_char(self, char: str):
        if self.mode == "AFTER_ENTRY" and char == "]":
            self._validate_required_entries_present()
        return super()._feed_char(char)

    def _advance(self, step: str, value: str | None = None):
        if step in {"LITERAL_PATH_NULL", "LITERAL_PATH_STRING"}:
            self._compiled_obligations()
            return super()._advance(step, value)
        if step == "ENTRY_ID":
            hosts, returns, literals, _ = self._compiled_obligations()
            emitted = {record[0] for record in self.graph_entries}
            available = [f"P{i}" for i in range(1, 9) if f"P{i}" not in emitted]
            required = (set(hosts) | set(returns) | literals) - emitted
            future_slots_after_current = 8 - self.entry_count
            if len(required) > future_slots_after_current:
                available = [entry_id for entry_id in available if entry_id in required]
            if not available:
                self._fail("NO_VIABLE_ENTRY_ID_FOR_OBLIGATIONS")
            return replace(self, mode="CHOICE", buffer="", choices=tuple(available),
                           next_step="ENTRY_TYPE_LITERAL")
        if step == "ENTRY_TYPE":
            hosts, returns, literals, _ = self._compiled_obligations()
            if self.current_entry_id in hosts:
                choices = ("CONTAINED_CREATIVE",)
            elif self.current_entry_id in returns or self.current_entry_id in literals:
                choices = ("REAL_WORLD_COMMITMENT",)
            else:
                # An undeclared creative host could never satisfy the frozen construction graph.
                choices = ("REAL_WORLD_COMMITMENT", "UNRESOLVED_SCOPE")
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="CANDIDATE_LITERAL")
        if step == "SCOPE_REL":
            hosts, returns, literals, _ = self._compiled_obligations()
            if self.current_entry_id in hosts:
                choices = ("CREATIVE_HOST",)
            elif self.current_entry_id in returns:
                choices = ("FACTUAL_RETURN_WITHIN_CREATIVE_HOST",)
            elif self.current_entry_id in literals:
                choices = ("STANDALONE",)
            else:
                choices = self._scope_relation_choices()
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="HOST_LITERAL")
        if step == "HOST":
            _, returns, _, _ = self._compiled_obligations()
            required_host = returns.get(self.current_entry_id)
            if required_host is not None:
                choices = (f'"{required_host}"',)
            else:
                choices = (("null",) if self.current_scope_relation != "FACTUAL_RETURN_WITHIN_CREATIVE_HOST"
                           else tuple(f'"P{i}"' for i in range(1, 9)))
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="RETURN_BASIS_LITERAL")
        if step == "COVERAGE":
            self._validate_required_entries_present()
        return super()._advance(step, value)

    def _compiled_obligations(self):
        hosts: dict[str, tuple[str, ...]] = {}
        returns: dict[str, str] = {}
        literals: set[str] = set()
        unresolved_required = False
        for construction_id, role, host_id, links in self.construction_records:
            if role in {"MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD"}:
                if host_id is None:
                    self._fail("MATERIAL_OBLIGATION_WITHOUT_HOST")
                hosts[host_id] = hosts.get(host_id, ()) + (construction_id,)
            if role == "MIXED_CREATIVE_AND_REAL_WORLD":
                if not links:
                    self._fail("MIXED_OBLIGATION_WITHOUT_RETURN")
                for entry_id in links:
                    prior = returns.get(entry_id)
                    if prior is not None and prior != host_id:
                        self._fail("RETURN_OBLIGATION_HOST_CONFLICT")
                    returns[entry_id] = host_id
            elif role == "LITERAL_ONLY":
                literals.update(links)
            elif role == "UNRESOLVED":
                unresolved_required = True
        host_ids = set(hosts)
        return_ids = set(returns)
        if host_ids & return_ids or host_ids & literals:
            self._fail("ENTRY_ROLE_OBLIGATION_CONFLICT")
        if return_ids & literals:
            self._fail("RETURN_LITERAL_OBLIGATION_CONFLICT")
        return hosts, returns, frozenset(literals), unresolved_required

    def _validate_required_entries_present(self) -> None:
        hosts, returns, literals, unresolved_required = self._compiled_obligations()
        index = {record[0]: record for record in self.graph_entries}
        required = set(hosts) | set(returns) | set(literals)
        if not required.issubset(index):
            self._fail("REQUIRED_CONSTRUCTION_ENTRY_MISSING")
        for entry_id in hosts:
            entry = index[entry_id]
            if entry[1] != "CONTAINED_CREATIVE" or entry[2] != "CREATIVE_HOST":
                self._fail("HOST_OBLIGATION_NOT_DISCHARGED")
        for entry_id, host_id in returns.items():
            entry = index[entry_id]
            if (entry[1] != "REAL_WORLD_COMMITMENT" or
                    entry[2] != "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" or entry[3] != host_id):
                self._fail("RETURN_OBLIGATION_NOT_DISCHARGED")
        for entry_id in literals:
            entry = index[entry_id]
            if entry[1] != "REAL_WORLD_COMMITMENT" or entry[2] != "STANDALONE":
                self._fail("LITERAL_OBLIGATION_NOT_DISCHARGED")
        if unresolved_required and not any(entry[1] == "UNRESOLVED_SCOPE" for entry in self.graph_entries):
            self._fail("UNRESOLVED_OBLIGATION_NOT_DISCHARGED")


__all__ = ("StagePConstructionObligationConstraintStateV1",)
