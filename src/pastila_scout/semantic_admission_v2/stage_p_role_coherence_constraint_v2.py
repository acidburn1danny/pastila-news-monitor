"""Role-conditioned Stage P constraint: illegal tuples are projected out before closure."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .stage_p_role_coherence_constraint_v1 import (
    EVENT_ALIGNMENTS,
    MODALITIES,
    SCOPE_BASES,
    TIMINGS,
    StagePRoleCoherenceConstraintStateV1,
    StagePRoleCoherenceConstraintViolationV1,
)


REAL_SCOPES = ("ASSERTED", "PRESUPPOSED", "ENTAILED", "NECESSARILY_IMPLIED")
REAL_EVENTS = ("GOVERNED_EVENT", "NEW_UNSUPPORTED_EVENT")
REAL_MODALITIES = ("POSSIBLE", "CONDITIONAL", "PROPOSED", "EXPECTED", "CERTAIN_OR_ACTUAL")
REAL_TIMINGS = ("PAST", "PRESENT", "ONGOING", "FUTURE", "COMPLETED", "UNDATED")


@dataclass(frozen=True)
class StagePRoleCoherenceConstraintStateV2(StagePRoleCoherenceConstraintStateV1):
    """V1 field format with role-conditioned enum choices and no late role dead-end."""

    current_axis_unresolved: bool = False

    def _advance(self, step: str, value: str | None = None) -> "StagePRoleCoherenceConstraintStateV2":
        if step == "SCOPE":
            return replace(self, mode="CHOICE", buffer="", choices=self._scope_choices(), next_step="EVENT_LITERAL")
        if step == "EVENT":
            return replace(self, mode="CHOICE", buffer="", choices=self._event_choices(), next_step="AUTH_MODALITY_LITERAL")
        if step == "AUTH_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=self._authority_modality_choices(), next_step="CAND_MODALITY_LITERAL")
        if step == "CAND_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=self._candidate_modality_choices(), next_step="AUTH_TIMING_LITERAL")
        if step == "AUTH_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=self._authority_timing_choices(), next_step="CAND_TIMING_LITERAL")
        if step == "CAND_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=self._candidate_timing_choices(), next_step="GROUP_LITERAL")
        state = super()._advance(step, value)
        if step in {"EVENT_LITERAL", "AUTH_MODALITY_LITERAL", "CAND_MODALITY_LITERAL", "AUTH_TIMING_LITERAL", "GROUP_LITERAL"}:
            state = replace(state, current_axis_unresolved=self.current_axis_unresolved or value == "UNRESOLVED")
        return state

    def _entry_start(self) -> "StagePRoleCoherenceConstraintStateV2":
        return replace(super()._entry_start(), current_axis_unresolved=False)

    def _scope_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("CREATIVE_CONTAINED",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_SCOPES
        return SCOPE_BASES

    def _event_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("CREATIVE_VEHICLE_ONLY",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_EVENTS
        return EVENT_ALIGNMENTS

    def _authority_modality_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE" or self.current_authority_null:
            return ("NOT_APPLICABLE",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_MODALITIES
        return MODALITIES

    def _candidate_modality_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("NOT_APPLICABLE",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_MODALITIES
        return MODALITIES

    def _authority_timing_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE" or self.current_authority_null:
            return ("NOT_APPLICABLE",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_TIMINGS
        return TIMINGS

    def _candidate_timing_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "CONTAINED_CREATIVE":
            return ("NOT_APPLICABLE",)
        if self.current_entry_type == "REAL_WORLD_COMMITMENT":
            return REAL_TIMINGS
        if self.current_entry_type == "UNRESOLVED_SCOPE" and not self.current_axis_unresolved:
            return ("UNRESOLVED",)
        return TIMINGS


__all__ = ("StagePRoleCoherenceConstraintStateV2", "StagePRoleCoherenceConstraintViolationV1")
