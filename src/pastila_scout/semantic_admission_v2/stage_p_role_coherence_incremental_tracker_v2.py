"""Incremental tracker bound to the role-conditioned V2 constraint."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_role_coherence_constraint_v2 import StagePRoleCoherenceConstraintStateV2


@dataclass(frozen=True)
class RoleCoherencePrefixResultV2:
    state: StagePRoleCoherenceConstraintStateV2
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePRoleCoherenceIncrementalTrackerV2:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePRoleCoherenceConstraintStateV2()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> RoleCoherencePrefixResultV2:
        ids = tuple(token_ids)
        decoded = decode(ids)
        if len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]
            state = self._last_state.feed(suffix)
            path = "INCREMENTAL"
            self.incremental_steps += 1
        else:
            suffix = decoded
            state = StagePRoleCoherenceConstraintStateV2().feed(decoded)
            path = "FULL_REBUILD"
            self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return RoleCoherencePrefixResultV2(state=state, decoded=decoded, token_ids=ids, path=path, suffix_characters=len(suffix))


__all__ = ("RoleCoherencePrefixResultV2", "StagePRoleCoherenceIncrementalTrackerV2")
