"""Incremental prefix tracker bound to Construction Role Audit DFA V1."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_construction_role_constraint_v1 import StagePConstructionRoleConstraintStateV1


@dataclass(frozen=True)
class ConstructionRolePrefixResultV1:
    state: StagePConstructionRoleConstraintStateV1
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePConstructionRoleIncrementalTrackerV1:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePConstructionRoleConstraintStateV1()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int],
                  decode: Callable[[Sequence[int]], str]) -> ConstructionRolePrefixResultV1:
        ids = tuple(token_ids); decoded = decode(ids)
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]; state = self._last_state.feed(suffix)
            path = "INCREMENTAL"; self.incremental_steps += 1
        else:
            suffix = decoded; state = StagePConstructionRoleConstraintStateV1().feed(decoded)
            path = "FULL_REBUILD"; self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return ConstructionRolePrefixResultV1(state, decoded, ids, path, len(suffix))


__all__ = ("ConstructionRolePrefixResultV1", "StagePConstructionRoleIncrementalTrackerV1")
