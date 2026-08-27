"""Scope Graph V1.1 character constraint with governed-support coherence before emission."""
from __future__ import annotations

from .stage_p_scope_graph_constraint_v1 import StagePScopeGraphConstraintStateV1


class StagePScopeGraphConstraintStateV1_1(StagePScopeGraphConstraintStateV1):
    def _event_choices(self) -> tuple[str, ...]:
        if self.current_entry_type == "REAL_WORLD_COMMITMENT" and self.current_authority_null:
            return ("NEW_UNSUPPORTED_EVENT",)
        return super()._event_choices()


__all__ = ("StagePScopeGraphConstraintStateV1_1",)
