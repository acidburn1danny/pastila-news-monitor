"""Evaluation-only character DFA extending Scope Graph V1.2 with target audits."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_scope_graph_constraint_v1_2 import StagePScopeGraphConstraintStateV1_2


TARGET_CLASSES = ("NONFACTUAL_EDITORIAL_OR_CREATIVE", "REAL_WORLD_PROPOSITION", "UNRESOLVED_TARGET")
SURVIVAL_BASES = ("DOES_NOT_SURVIVE_AS_FACT", "ASSERTION_SURVIVES", "PRESUPPOSITION_SURVIVES",
                  "ENTAILMENT_SURVIVES", "NECESSARY_IMPLICATION_SURVIVES", "UNRESOLVED")
RESOLUTIONS = ("RETAINED_NONFACTUAL", "RECONCILED_TO_LEDGER", "FAIL_CLOSED_UNRESOLVED")


@dataclass(frozen=True)
class StagePCreativeTargetConstraintStateV1(StagePScopeGraphConstraintStateV1_2):
    audit_count: int = 0
    target_audits: tuple[tuple[str, str, str, str | None, str], ...] = ()
    current_audit_id: str | None = None
    current_audit_host: str | None = None
    current_target_class: str | None = None
    current_survival: str | None = None
    current_proposition_id: str | None = None
    receipt_targets_enumerated: bool | None = None
    receipt_target_classes: bool | None = None
    receipt_target_reconciled: bool | None = None

    def _feed_char(self, char: str):
        if self.mode == "AFTER_ENTRY" and char == "]":
            state = replace(self, characters=self.characters + 1, mode="LITERAL",
                            remaining=',"creative_target_audits":[', next_step="AUDIT_COLLECTION_START")
            return state
        if self.mode == "AFTER_AUDIT":
            state = replace(self, characters=self.characters + 1)
            if char == ",":
                if self.audit_count >= 16:
                    self._fail("AUDIT_LIMIT")
                return state._audit_start()
            if char == "]":
                return replace(state, mode="LITERAL",
                    remaining=',"coverage_receipt":{"candidate_reviewed_as_whole":', next_step="WHOLE")
            self._fail("AUDIT_SEPARATOR")
        return super()._feed_char(char)

    def _advance(self, step: str, value: str | None = None):
        if step == "AUDIT_COLLECTION_START":
            creative = [entry for entry in self.graph_entries if entry[1] == "CONTAINED_CREATIVE"]
            if not creative:
                return replace(self, mode="LITERAL", remaining="]", next_step="AUDIT_COLLECTION_EMPTY_END")
            return self._audit_start()
        if step == "AUDIT_COLLECTION_EMPTY_END":
            return replace(self, mode="LITERAL",
                remaining=',"coverage_receipt":{"candidate_reviewed_as_whole":', next_step="WHOLE")
        if step == "AUDIT_ID":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f'T{i}"' for i in range(1, 17)),
                           next_step="AUDIT_HOST_LITERAL")
        if step == "AUDIT_HOST_LITERAL":
            return replace(self, current_audit_id=value[:-1], mode="LITERAL",
                           remaining=',"creative_host_entry_id":"', next_step="AUDIT_HOST")
        if step == "AUDIT_HOST":
            hosts = tuple(entry[0] for entry in self.graph_entries if entry[1] == "CONTAINED_CREATIVE")
            return replace(self, mode="CHOICE", buffer="", choices=hosts, next_step="VEHICLE_LITERAL")
        if step == "VEHICLE_LITERAL":
            return replace(self, current_audit_host=value, mode="LITERAL",
                           remaining='","vehicle_span":', next_step="VEHICLE")
        if step == "VEHICLE":
            return replace(self, mode="STRING_START", next_step="TARGET_LITERAL")
        if step == "TARGET_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"semantic_target":', next_step="TARGET")
        if step == "TARGET":
            return replace(self, mode="STRING_START", next_step="TARGET_CLASS_LITERAL")
        if step == "TARGET_CLASS_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"target_class":"', next_step="TARGET_CLASS")
        if step == "TARGET_CLASS":
            return replace(self, mode="CHOICE", buffer="", choices=TARGET_CLASSES, next_step="SURVIVAL_LITERAL")
        if step == "SURVIVAL_LITERAL":
            return replace(self, current_target_class=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED_TARGET",
                           mode="LITERAL", remaining='","survival_basis":"', next_step="SURVIVAL")
        if step == "SURVIVAL":
            choices = self._survival_choices()
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="PROPOSITION_LITERAL_TARGET")
        if step == "PROPOSITION_LITERAL_TARGET":
            return replace(self, current_survival=value, mode="LITERAL",
                           remaining='","proposition_entry_id":', next_step="PROPOSITION_TARGET")
        if step == "PROPOSITION_TARGET":
            choices = ("null",)
            if self.current_target_class == "REAL_WORLD_PROPOSITION":
                choices = tuple(f'"{entry[0]}"' for entry in self.graph_entries if entry[1] == "REAL_WORLD_COMMITMENT")
                if not choices:
                    self._fail("NO_REAL_WORLD_PROPOSITION_FOR_TARGET")
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="RESOLUTION_LITERAL")
        if step == "RESOLUTION_LITERAL":
            proposition = None if value == "null" else value.strip('"')
            return replace(self, current_proposition_id=proposition, mode="LITERAL",
                           remaining=',"resolution":"', next_step="RESOLUTION")
        if step == "RESOLUTION":
            choices = {"NONFACTUAL_EDITORIAL_OR_CREATIVE": ("RETAINED_NONFACTUAL",),
                       "REAL_WORLD_PROPOSITION": ("RECONCILED_TO_LEDGER",),
                       "UNRESOLVED_TARGET": ("FAIL_CLOSED_UNRESOLVED",)}[self.current_target_class]
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="AUDIT_END")
        if step == "AUDIT_END":
            state = replace(self)
            state._validate_target_link()
            record = (state.current_audit_id, state.current_audit_host, state.current_target_class,
                      state.current_proposition_id, value)
            return replace(state, target_audits=state.target_audits + (record,), mode="LITERAL",
                           remaining='"}', next_step="AFTER_AUDIT")
        if step == "AFTER_AUDIT":
            return replace(self, mode="AFTER_AUDIT")
        if step == "AFTER_RETURNS":
            return replace(self, receipt_returns=value == "true", mode="LITERAL",
                           remaining=',"creative_targets_enumerated":', next_step="TARGETS_ENUMERATED")
        if step in {"TARGETS_ENUMERATED", "TARGET_CLASSES_REVIEWED", "TARGET_RECONCILED"}:
            return replace(self, mode="CHOICE", buffer="", choices=("false", "true"), next_step=f"AFTER_{step}")
        if step == "AFTER_TARGETS_ENUMERATED":
            return replace(self, receipt_targets_enumerated=value == "true", mode="LITERAL",
                           remaining=',"target_classes_reviewed":', next_step="TARGET_CLASSES_REVIEWED")
        if step == "AFTER_TARGET_CLASSES_REVIEWED":
            return replace(self, receipt_target_classes=value == "true", mode="LITERAL",
                           remaining=',"target_to_ledger_reconciled":', next_step="TARGET_RECONCILED")
        if step == "AFTER_TARGET_RECONCILED":
            return replace(self, receipt_target_reconciled=value == "true", mode="LITERAL",
                           remaining='},"coverage_decision":"', next_step="COVERAGE")
        if step == "COVERAGE":
            complete = (not self.unresolved_seen and not self.receipt_unresolved and bool(self.receipt_whole)
                and bool(self.receipt_embedded) and bool(self.receipt_creative) and bool(self.receipt_overlaps)
                and bool(self.receipt_hosts) and bool(self.receipt_returns) and bool(self.receipt_targets_enumerated)
                and bool(self.receipt_target_classes) and bool(self.receipt_target_reconciled))
            indeterminate = bool(self.unresolved_seen) and bool(self.receipt_unresolved)
            if complete:
                choices = ("COMPLETE",)
            elif indeterminate:
                choices = ("INDETERMINATE",)
            else:
                self._fail("NO_COHERENT_TARGET_COVERAGE_DECISION")
            return replace(self, mode="CHOICE", buffer="", choices=choices, next_step="COVERAGE_END")
        if step == "TERMINAL":
            self._validate_target_graph()
        return super()._advance(step, value)

    def _audit_start(self):
        return replace(self, audit_count=self.audit_count + 1, mode="LITERAL", remaining='{"audit_id":"',
                       next_step="AUDIT_ID", current_audit_id=None, current_audit_host=None,
                       current_target_class=None, current_survival=None, current_proposition_id=None)

    def _survival_choices(self):
        if self.current_target_class == "NONFACTUAL_EDITORIAL_OR_CREATIVE":
            return ("DOES_NOT_SURVIVE_AS_FACT",)
        if self.current_target_class == "REAL_WORLD_PROPOSITION":
            return SURVIVAL_BASES[1:5]
        return ("UNRESOLVED",)

    def _validate_target_link(self):
        if self.current_target_class != "REAL_WORLD_PROPOSITION":
            if self.current_proposition_id is not None:
                self._fail("UNEXPECTED_TARGET_PROPOSITION")
            return
        index = {entry[0]: entry for entry in self.graph_entries}
        host = index.get(self.current_audit_host)
        proposition = index.get(self.current_proposition_id)
        if (host is None or host[1] != "CONTAINED_CREATIVE" or host[2] != "CREATIVE_HOST" or
                proposition is None or proposition[1] != "REAL_WORLD_COMMITMENT" or
                proposition[2] != "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" or proposition[3] != host[0]):
            self._fail("TARGET_PROPOSITION_LINK_INVALID")

    def _validate_target_graph(self):
        creative = {entry[0] for entry in self.graph_entries if entry[1] == "CONTAINED_CREATIVE"}
        audited = {audit[1] for audit in self.target_audits}
        if creative != audited:
            self._fail("CREATIVE_HOST_AUDIT_COVERAGE_MISMATCH")
        ids = [audit[0] for audit in self.target_audits]
        if len(ids) != len(set(ids)):
            self._fail("DUPLICATE_AUDIT_ID")
        if (any(audit[2] == "UNRESOLVED_TARGET" for audit in self.target_audits) and
                not any(entry[1] == "UNRESOLVED_SCOPE" for entry in self.graph_entries)):
            self._fail("UNRESOLVED_TARGET_REQUIRES_UNRESOLVED_ENTRY")


__all__ = ("StagePCreativeTargetConstraintStateV1",)
