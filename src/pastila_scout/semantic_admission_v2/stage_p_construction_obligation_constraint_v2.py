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

    def __post_init__(self) -> None:
        if self.context is None:
            raise ValueError("SOURCE_REFERENCE_CONTEXT_REQUIRED")

    @classmethod
    def for_context(cls, context: SourceReferenceConstraintContextV1):
        return cls(context=context)

    def _feed_char(self, char: str):
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
