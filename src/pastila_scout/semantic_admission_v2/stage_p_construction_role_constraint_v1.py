"""Evaluation-only character DFA for Construction Role Audit V1."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_creative_target_constraint_v1 import StagePCreativeTargetConstraintStateV1


DISPOSITIONS = ("NO_MATERIAL_CREATIVE_CONSTRUCTION", "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS",
                "UNRESOLVED_CONSTRUCTION_ROLE")
ROLES = ("LITERAL_ONLY", "MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD",
         "NON_MATERIAL_RHETORICAL_COLOR", "UNRESOLVED")
RESOLUTION_BY_ROLE = {
    "LITERAL_ONLY": "LITERAL_PATH_RETAINED",
    "MATERIAL_CREATIVE_OR_EDITORIAL": "CREATIVE_HOST_REQUIRED",
    "MIXED_CREATIVE_AND_REAL_WORLD": "MIXED_HOST_AND_RETURNS_REQUIRED",
    "NON_MATERIAL_RHETORICAL_COLOR": "RHETORICAL_COLOR_RETAINED",
    "UNRESOLVED": "FAIL_CLOSED_UNRESOLVED",
}


@dataclass(frozen=True)
class StagePConstructionRoleConstraintStateV1(StagePCreativeTargetConstraintStateV1):
    remaining: str = ('{"stage_id":"PROPOSITION_LEDGER","construction_role_audit":'
                      '{"candidate_reviewed_as_construction":')
    next_step: str = "CONSTRUCTION_REVIEWED"
    construction_disposition: str | None = None
    construction_count: int = 0
    construction_records: tuple[tuple[str, str, str | None, tuple[str, ...]], ...] = ()
    current_construction_id: str | None = None
    current_construction_role: str | None = None
    current_construction_host: str | None = None
    current_construction_links: tuple[str, ...] = ()
    construction_literal_basis_nonnull: bool | None = None
    receipt_construction_roles: bool | None = None
    receipt_construction_reconciled: bool | None = None

    def _feed_char(self, char: str):
        if self.mode == "CONSTRUCTION_RECORD_SEPARATOR":
            state = replace(self, characters=self.characters + 1)
            if char == ",":
                if self.construction_count >= 8:
                    self._fail("CONSTRUCTION_LIMIT")
                return state._construction_start()
            if char == "]":
                if not self._construction_collection_can_close():
                    self._fail("CONSTRUCTION_DISPOSITION_REQUIREMENT_UNSATISFIED")
                return replace(state, mode="LITERAL", remaining=',"literal_path_basis":',
                               next_step="LITERAL_PATH_BASIS")
            self._fail("CONSTRUCTION_SEPARATOR")
        if self.mode == "CONSTRUCTION_LINK_SEPARATOR":
            state = replace(self, characters=self.characters + 1)
            if char == ",":
                return replace(state, mode="LITERAL", remaining='"', next_step="CONSTRUCTION_LINK")
            if char == "]":
                return replace(state, mode="LITERAL", remaining=',"resolution":"',
                               next_step="CONSTRUCTION_RESOLUTION")
            self._fail("CONSTRUCTION_LINK_SEPARATOR")
        if self.mode == "CONSTRUCTION_NULLABLE_STRING_START":
            state = replace(self, characters=self.characters + 1)
            if char == "n":
                if self.construction_disposition == "NO_MATERIAL_CREATIVE_CONSTRUCTION":
                    self._fail("NO_MATERIAL_LITERAL_PATH_REQUIRED")
                return replace(state, mode="LITERAL", remaining="ull", next_step="LITERAL_PATH_NULL")
            if char == '"':
                if self.construction_disposition != "NO_MATERIAL_CREATIVE_CONSTRUCTION":
                    self._fail("MATERIAL_OR_UNRESOLVED_LITERAL_PATH_MUST_BE_NULL")
                return replace(state, mode="STRING", string_characters=0, string_escape=False,
                               unicode_remaining=0, next_step="LITERAL_PATH_STRING")
            self._fail("CONSTRUCTION_NULLABLE_STRING_START")
        return super()._feed_char(char)

    def _advance(self, step: str, value: str | None = None):
        if step == "CONSTRUCTION_REVIEWED":
            return replace(self, mode="CHOICE", buffer="", choices=("true",),
                           next_step="CONSTRUCTION_DISPOSITION_LITERAL")
        if step == "CONSTRUCTION_DISPOSITION_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"overall_disposition":"',
                           next_step="CONSTRUCTION_DISPOSITION")
        if step == "CONSTRUCTION_DISPOSITION":
            return replace(self, mode="CHOICE", buffer="", choices=DISPOSITIONS,
                           next_step="CONSTRUCTION_RECORDS_LITERAL")
        if step == "CONSTRUCTION_RECORDS_LITERAL":
            return replace(self, construction_disposition=value, mode="LITERAL",
                           remaining='","construction_records":[', next_step="CONSTRUCTION_COLLECTION")
        if step == "CONSTRUCTION_COLLECTION":
            if self.construction_disposition == "NO_MATERIAL_CREATIVE_CONSTRUCTION":
                return replace(self, mode="CHOICE", buffer="", choices=("]", "{"),
                               next_step="CONSTRUCTION_COLLECTION_CHOICE")
            return self._construction_start()
        if step == "CONSTRUCTION_COLLECTION_CHOICE":
            if value == "]":
                return replace(self, mode="LITERAL", remaining=',"literal_path_basis":',
                               next_step="LITERAL_PATH_BASIS")
            return replace(self, construction_count=1, mode="LITERAL", remaining='"construction_id":"',
                           next_step="CONSTRUCTION_ID")
        if step == "CONSTRUCTION_ID":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f'C{i}' for i in range(1, 9)),
                           next_step="CONSTRUCTION_SPAN_LITERAL")
        if step == "CONSTRUCTION_SPAN_LITERAL":
            return replace(self, current_construction_id=value, mode="LITERAL",
                           remaining='","candidate_span":', next_step="CONSTRUCTION_SPAN")
        if step == "CONSTRUCTION_SPAN":
            return replace(self, mode="STRING_START", next_step="CONSTRUCTION_ROLE_LITERAL")
        if step == "CONSTRUCTION_ROLE_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"construction_role":"',
                           next_step="CONSTRUCTION_ROLE")
        if step == "CONSTRUCTION_ROLE":
            choices = ROLES
            if self.construction_disposition == "NO_MATERIAL_CREATIVE_CONSTRUCTION":
                choices = ("LITERAL_ONLY", "NON_MATERIAL_RHETORICAL_COLOR")
            elif self.construction_disposition == "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS":
                choices = ROLES[:4]
            elif self.construction_disposition == "UNRESOLVED_CONSTRUCTION_ROLE":
                choices = ROLES
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="CONSTRUCTION_BASIS_LITERAL")
        if step == "CONSTRUCTION_BASIS_LITERAL":
            return replace(self, current_construction_role=value,
                           unresolved_seen=self.unresolved_seen or value == "UNRESOLVED", mode="LITERAL",
                           remaining='","role_basis":', next_step="CONSTRUCTION_BASIS")
        if step == "CONSTRUCTION_BASIS":
            return replace(self, mode="STRING_START", next_step="CONSTRUCTION_HOST_LITERAL")
        if step == "CONSTRUCTION_HOST_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"creative_host_entry_id":',
                           next_step="CONSTRUCTION_HOST")
        if step == "CONSTRUCTION_HOST":
            choices = ("null",)
            if self.current_construction_role in {"MATERIAL_CREATIVE_OR_EDITORIAL",
                                                  "MIXED_CREATIVE_AND_REAL_WORLD"}:
                choices = tuple(f'"P{i}"' for i in range(1, 9))
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="CONSTRUCTION_LINKS_LITERAL")
        if step == "CONSTRUCTION_LINKS_LITERAL":
            host = None if value == "null" else value.strip('"')
            return replace(self, current_construction_host=host, mode="LITERAL",
                           remaining=',"literal_or_return_entry_ids":[', next_step="CONSTRUCTION_LINKS")
        if step == "CONSTRUCTION_LINKS":
            if self.current_construction_role == "MIXED_CREATIVE_AND_REAL_WORLD":
                return replace(self, mode="LITERAL", remaining='"', next_step="CONSTRUCTION_LINK")
            return replace(self, mode="CHOICE", buffer="", choices=("]", '"'),
                           next_step="CONSTRUCTION_LINKS_CHOICE")
        if step == "CONSTRUCTION_LINKS_CHOICE":
            if value == "]":
                return replace(self, mode="LITERAL", remaining=',"resolution":"',
                               next_step="CONSTRUCTION_RESOLUTION")
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f'P{i}"' for i in range(1, 9)),
                           next_step="CONSTRUCTION_LINK_END")
        if step == "CONSTRUCTION_LINK":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f'P{i}"' for i in range(1, 9)),
                           next_step="CONSTRUCTION_LINK_END")
        if step == "CONSTRUCTION_LINK_END":
            link = value[:-1]
            if link in self.current_construction_links:
                self._fail("DUPLICATE_CONSTRUCTION_LINK")
            return replace(self, current_construction_links=self.current_construction_links + (link,),
                           mode="CONSTRUCTION_LINK_SEPARATOR")
        if step == "CONSTRUCTION_LINKS_END":
            return replace(self, mode="LITERAL", remaining=',"resolution":"',
                           next_step="CONSTRUCTION_RESOLUTION")
        if step == "CONSTRUCTION_RESOLUTION":
            return replace(self, mode="CHOICE", buffer="",
                           choices=(RESOLUTION_BY_ROLE[self.current_construction_role],),
                           next_step="CONSTRUCTION_RECORD_END")
        if step == "CONSTRUCTION_RECORD_END":
            record = (self.current_construction_id, self.current_construction_role,
                      self.current_construction_host, self.current_construction_links)
            ids = {item[0] for item in self.construction_records}
            if self.current_construction_id in ids:
                self._fail("DUPLICATE_CONSTRUCTION_ID")
            return replace(self, construction_records=self.construction_records + (record,),
                           mode="LITERAL", remaining='"}', next_step="AFTER_CONSTRUCTION_RECORD")
        if step == "AFTER_CONSTRUCTION_RECORD":
            return replace(self, mode="CONSTRUCTION_RECORD_SEPARATOR")
        if step == "LITERAL_PATH_BASIS":
            return replace(self, mode="CONSTRUCTION_NULLABLE_STRING_START")
        if step == "LITERAL_PATH_NULL":
            return replace(self, construction_literal_basis_nonnull=False, mode="LITERAL",
                           remaining='},"entries":[', next_step="ENTRY_START")
        if step == "LITERAL_PATH_STRING":
            return replace(self, construction_literal_basis_nonnull=True, mode="LITERAL",
                           remaining='},"entries":[', next_step="ENTRY_START")
        if step == "AFTER_TARGET_RECONCILED":
            return replace(self, receipt_target_reconciled=value == "true", mode="LITERAL",
                           remaining=',"construction_roles_reviewed":', next_step="CONSTRUCTION_ROLES_RECEIPT")
        if step in {"CONSTRUCTION_ROLES_RECEIPT", "CONSTRUCTION_RECONCILED_RECEIPT"}:
            return replace(self, mode="CHOICE", buffer="", choices=("false", "true"),
                           next_step=f"AFTER_{step}")
        if step == "AFTER_CONSTRUCTION_ROLES_RECEIPT":
            return replace(self, receipt_construction_roles=value == "true", mode="LITERAL",
                           remaining=',"construction_to_ledger_reconciled":',
                           next_step="CONSTRUCTION_RECONCILED_RECEIPT")
        if step == "AFTER_CONSTRUCTION_RECONCILED_RECEIPT":
            return replace(self, receipt_construction_reconciled=value == "true", mode="LITERAL",
                           remaining='},"coverage_decision":"', next_step="COVERAGE")
        if step == "COVERAGE":
            self._validate_construction_graph()
            if not self.receipt_construction_roles or not self.receipt_construction_reconciled:
                if not self.unresolved_seen or not self.receipt_unresolved:
                    self._fail("NO_COHERENT_CONSTRUCTION_COVERAGE_DECISION")
            return super()._advance(step, value)
        if step == "TERMINAL":
            self._validate_construction_graph()
        return super()._advance(step, value)

    def _construction_start(self):
        return replace(self, construction_count=self.construction_count + 1, mode="LITERAL",
                       remaining='{"construction_id":"', next_step="CONSTRUCTION_ID",
                       current_construction_id=None, current_construction_role=None,
                       current_construction_host=None, current_construction_links=())

    def _construction_collection_can_close(self) -> bool:
        """Do not leave the collection before its bound disposition is satisfiable."""
        roles = {record[1] for record in self.construction_records}
        material = bool(roles & {
            "MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD"})
        unresolved = "UNRESOLVED" in roles
        if self.construction_disposition == "NO_MATERIAL_CREATIVE_CONSTRUCTION":
            return not material and not unresolved
        if self.construction_disposition == "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS":
            return material and not unresolved
        if self.construction_disposition == "UNRESOLVED_CONSTRUCTION_ROLE":
            return unresolved
        return False

    def _validate_construction_graph(self):
        roles = {record[1] for record in self.construction_records}
        material = bool(roles & {"MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD"})
        unresolved = "UNRESOLVED" in roles
        if self.construction_disposition == "NO_MATERIAL_CREATIVE_CONSTRUCTION":
            if material or unresolved or not self.construction_literal_basis_nonnull:
                self._fail("NO_MATERIAL_DISPOSITION_INCOHERENT")
        elif self.construction_disposition == "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS":
            if not material or unresolved or self.construction_literal_basis_nonnull is not False:
                self._fail("MATERIAL_DISPOSITION_INCOHERENT")
        elif not unresolved or self.construction_literal_basis_nonnull is not False:
            self._fail("UNRESOLVED_DISPOSITION_INCOHERENT")
        index = {entry[0]: entry for entry in self.graph_entries}
        creative = {entry[0] for entry in self.graph_entries if entry[1] == "CONTAINED_CREATIVE"}
        mapped = {record[2] for record in self.construction_records if record[2] is not None}
        if creative != mapped:
            self._fail("CONSTRUCTION_CREATIVE_HOST_COVERAGE_MISMATCH")
        for _, role, host_id, links in self.construction_records:
            if host_id is not None and (host_id not in index or index[host_id][1] != "CONTAINED_CREATIVE"):
                self._fail("CONSTRUCTION_HOST_INVALID")
            for link in links:
                entry = index.get(link)
                if entry is None or entry[1] != "REAL_WORLD_COMMITMENT":
                    self._fail("CONSTRUCTION_LITERAL_OR_RETURN_INVALID")
                if role == "MIXED_CREATIVE_AND_REAL_WORLD" and entry[3] != host_id:
                    self._fail("MIXED_RETURN_HOST_MISMATCH")
        if unresolved and not any(entry[1] == "UNRESOLVED_SCOPE" for entry in self.graph_entries):
            self._fail("UNRESOLVED_CONSTRUCTION_REQUIRES_UNRESOLVED_ENTRY")


__all__ = ("StagePConstructionRoleConstraintStateV1",)
