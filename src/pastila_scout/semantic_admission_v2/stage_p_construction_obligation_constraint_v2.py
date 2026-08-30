"""Complete V2 ledger character DFA composing request-bound source references."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_construction_obligation_constraint_v1 import (
    StagePConstructionObligationConstraintStateV1,
)
from .stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    StagePSourceReferenceConstraintStateV1,
)
from .stage_p_construction_obligation_semantic_completeness_v1 import (
    CASE01_AUTHORITY_SHA256, CASE01_CANDIDATE_SHA256,
    CASE01_CANONICAL_POLICY_IDENTITY, SemanticCompletenessPolicyV1,
    seal_semantic_completeness_policy_v1,
)


_INITIAL = (
    '{"schema_name":"pastila-semantic-admission-v2-stage-p-construction-obligation-ledger",'
    '"schema_version":"2.0.0-evaluation.1","stage_id":"PROPOSITION_LEDGER",'
    '"construction_role_audit":{"candidate_reviewed_as_construction":'
)


@dataclass(frozen=True)
class StagePConstructionObligationConstraintStateV2(
        StagePConstructionObligationConstraintStateV1):
    """V1 semantic obligations with V2 copyless provenance transitions."""

    remaining: str = _INITIAL
    context: SourceReferenceConstraintContextV1 | None = None
    reference_state: StagePSourceReferenceConstraintStateV1 | None = None
    reference_return_step: str | None = None
    reference_was_null: bool | None = None
    semantic_policy: SemanticCompletenessPolicyV1 | None = None

    def __post_init__(self) -> None:
        if self.context is None:
            raise ValueError("SOURCE_REFERENCE_CONTEXT_REQUIRED")

    @classmethod
    def for_context(cls, context: SourceReferenceConstraintContextV1,
                    semantic_policy: SemanticCompletenessPolicyV1 | None = None):
        if semantic_policy is not None:
            if type(semantic_policy) is not SemanticCompletenessPolicyV1:
                raise TypeError("SEMANTIC_COMPLETENESS_POLICY_EXACT_TYPE_REQUIRED")
            if (semantic_policy.identity !=
                    seal_semantic_completeness_policy_v1(semantic_policy).identity):
                raise ValueError("SEMANTIC_COMPLETENESS_POLICY_IDENTITY_MISMATCH")
            if (semantic_policy.candidate_sha256 != context.candidate.sha256 or
                    semantic_policy.authority_sha256 != context.factual_authority.sha256):
                raise ValueError("SEMANTIC_COMPLETENESS_POLICY_CONTEXT_MISMATCH")
            if (context.candidate.sha256 == CASE01_CANDIDATE_SHA256 and
                    context.factual_authority.sha256 == CASE01_AUTHORITY_SHA256 and
                    semantic_policy.identity != CASE01_CANONICAL_POLICY_IDENTITY):
                raise ValueError("CASE01_CANONICAL_SEMANTIC_POLICY_IDENTITY_MISMATCH")
        return cls(context=context, semantic_policy=semantic_policy)

    def _feed_char(self, char: str):
        topology = self.semantic_policy.required_topology if self.semantic_policy else None
        if topology is not None and self.mode == "CONSTRUCTION_RECORD_SEPARATOR":
            expected = len(topology.construction_ids)
            if char == "," and self.construction_count >= expected:
                self._fail("SEMANTIC_POLICY_EXTRA_CONSTRUCTION_FORBIDDEN")
            if char == "]" and self.construction_count != expected:
                self._fail("SEMANTIC_POLICY_CONSTRUCTION_TOPOLOGY_INCOMPLETE")
        if topology is not None and self.mode == "AFTER_ENTRY":
            expected = len(topology.entry_ids)
            if char == "," and self.entry_count >= expected:
                self._fail("SEMANTIC_POLICY_EXTRA_ENTRY_FORBIDDEN")
            if char == "]" and self.entry_count != expected:
                self._fail("SEMANTIC_POLICY_ENTRY_TOPOLOGY_INCOMPLETE")
        if topology is not None and self.mode == "AFTER_AUDIT":
            expected = len(topology.creative_audit_ids)
            if char == "," and self.audit_count >= expected:
                self._fail("SEMANTIC_POLICY_EXTRA_AUDIT_FORBIDDEN")
            if char == "]" and self.audit_count != expected:
                self._fail("SEMANTIC_POLICY_AUDIT_TOPOLOGY_INCOMPLETE")
        if self.mode != "V2_REFERENCE":
            return super()._feed_char(char)
        if self.terminal:
            self._fail("TRAILING_BYTES")
        if self.characters >= 16000:
            self._fail("CHARACTER_LIMIT")
        if self.reference_state is None or self.reference_return_step is None:
            self._fail("V2_REFERENCE_STATE_MISSING")
        reference = self.reference_state.feed(char)
        if reference.is_failed:
            self._fail(reference.failure_reason or "V2_REFERENCE_FAILURE")
        state = replace(self, characters=self.characters + 1, reference_state=reference)
        if not reference.is_terminal:
            return state
        return_step = state.reference_return_step
        was_null = reference.selected_start is None
        state = replace(state, mode="V2_REFERENCE_COMPLETE", reference_state=None,
                        reference_return_step=None, reference_was_null=was_null)
        return state._advance(return_step)

    def _start_reference(self, field: ReferenceFieldV1, return_step: str):
        if self.context is None:
            self._fail("SOURCE_REFERENCE_CONTEXT_REQUIRED")
        reference = StagePSourceReferenceConstraintStateV1.for_field(
            context=self.context, field=field)
        return replace(self, mode="V2_REFERENCE", reference_state=reference,
                       reference_return_step=return_step, reference_was_null=None)

    def _advance(self, step: str, value: str | None = None):
        policy = self.semantic_policy
        topology = policy.required_topology if policy else None
        if topology is not None:
            if step == "CONSTRUCTION_DISPOSITION":
                required_roles = {item.construction_role for item in policy.required_constructions}
                disposition = ("UNRESOLVED_CONSTRUCTION_ROLE" if "UNRESOLVED" in required_roles
                               else "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS" if required_roles & {
                                   "MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD"}
                               else "NO_MATERIAL_CREATIVE_CONSTRUCTION")
                return replace(self, mode="CHOICE", buffer="", choices=(disposition,),
                               next_step="CONSTRUCTION_RECORDS_LITERAL")
            if step == "CONSTRUCTION_ID":
                index = self.construction_count - 1
                if index >= len(topology.construction_ids):
                    self._fail("SEMANTIC_POLICY_EXTRA_CONSTRUCTION_FORBIDDEN")
                return replace(self, mode="CHOICE", buffer="",
                               choices=(topology.construction_ids[index],),
                               next_step="CONSTRUCTION_SPAN_LITERAL")
            if step == "CONSTRUCTION_ROLE":
                required = {item.construction_id: item.construction_role
                            for item in policy.required_constructions}
                role = required.get(self.current_construction_id)
                if role is None:
                    self._fail("SEMANTIC_POLICY_CONSTRUCTION_ROLE_UNBOUND")
                return replace(self, mode="CHOICE", buffer="", choices=(role,),
                               next_step="CONSTRUCTION_BASIS_LITERAL")
            if step == "ENTRY_ID":
                index = self.entry_count - 1
                if index >= len(topology.entry_ids):
                    self._fail("SEMANTIC_POLICY_EXTRA_ENTRY_FORBIDDEN")
                return replace(self, mode="CHOICE", buffer="",
                               choices=(topology.entry_ids[index],),
                               next_step="ENTRY_TYPE_LITERAL")
            if step == "ENTRY_TYPE":
                entry_id = topology.entry_ids[self.entry_count - 1]
                creative = {item.entry_id for item in policy.required_creative}
                returns = {item.entry_id for item in policy.required_returns}
                entry_type = ("CONTAINED_CREATIVE" if entry_id in creative
                              else "REAL_WORLD_COMMITMENT" if entry_id in returns else None)
                if entry_type is None:
                    self._fail("SEMANTIC_POLICY_ENTRY_TYPE_UNBOUND")
                return replace(self, mode="CHOICE", buffer="", choices=(entry_type,),
                               next_step="CANDIDATE_LITERAL")
            if step == "AUDIT_ID":
                index = self.audit_count - 1
                if index >= len(topology.creative_audit_ids):
                    self._fail("SEMANTIC_POLICY_EXTRA_AUDIT_FORBIDDEN")
                return replace(self, mode="CHOICE", buffer="",
                               choices=(topology.creative_audit_ids[index] + '"',),
                               next_step="AUDIT_HOST_LITERAL")
            required_true = {
                "WHOLE", "EMBEDDED", "CREATIVE", "OVERLAPS", "HOSTS", "RETURNS",
                "TARGETS_ENUMERATED", "TARGET_CLASSES_REVIEWED", "TARGET_RECONCILED",
                "CONSTRUCTION_ROLES_RECEIPT", "CONSTRUCTION_RECONCILED_RECEIPT",
            }
            if step in required_true:
                return replace(self, mode="CHOICE", buffer="", choices=("true",),
                               next_step=f"AFTER_{step}")
            if step == "RECEIPT_UNRESOLVED":
                observed = "true" if self.unresolved_seen else "false"
                return replace(self, mode="CHOICE", buffer="", choices=(observed,),
                               next_step="AFTER_RECEIPT_UNRESOLVED")
        if step == "CONSTRUCTION_SPAN_LITERAL":
            return replace(self, current_construction_id=value, mode="LITERAL",
                           remaining='","candidate_span_ref":', next_step="CONSTRUCTION_SPAN")
        if step == "CONSTRUCTION_SPAN":
            return self._start_reference(
                ReferenceFieldV1.CANDIDATE_SPAN, "CONSTRUCTION_ROLE_LITERAL")
        if step == "CANDIDATE_LITERAL":
            return replace(
                self, current_entry_type=value,
                unresolved_seen=self.unresolved_seen or value == "UNRESOLVED_SCOPE",
                mode="LITERAL", remaining='","candidate_span_ref":', next_step="CANDIDATE")
        if step == "CANDIDATE":
            return self._start_reference(
                ReferenceFieldV1.CANDIDATE_SPAN, "AUTHORITY_LITERAL")
        if step == "AUTHORITY_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"authority_support_ref":',
                           next_step="AUTHORITY")
        if step == "AUTHORITY":
            return self._start_reference(
                ReferenceFieldV1.AUTHORITY_SUPPORT, "V2_AUTHORITY_COMPLETE")
        if step == "V2_AUTHORITY_COMPLETE":
            return replace(self, current_authority_null=bool(self.reference_was_null),
                           reference_was_null=None, mode="LITERAL",
                           remaining=',"commitment":', next_step="COMMITMENT")
        if step == "VEHICLE_LITERAL":
            return replace(self, current_audit_host=value, mode="LITERAL",
                           remaining='","vehicle_span_ref":', next_step="VEHICLE")
        if step == "VEHICLE":
            return self._start_reference(
                ReferenceFieldV1.VEHICLE_SPAN, "TARGET_LITERAL")
        return super()._advance(step, value)


__all__ = ("StagePConstructionObligationConstraintStateV2",)
