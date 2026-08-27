"""Incremental prefix tracker bound to the Scope Graph V1.2 liveness DFA."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_scope_graph_constraint_v1_2 import StagePScopeGraphConstraintStateV1_2


@dataclass(frozen=True)
class ScopeGraphPrefixResultV1_2:
    state: StagePScopeGraphConstraintStateV1_2
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePScopeGraphIncrementalTrackerV1_2:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePScopeGraphConstraintStateV1_2()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> ScopeGraphPrefixResultV1_2:
        ids = tuple(token_ids)
        decoded = decode(ids)
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]
            state = self._last_state.feed(suffix)
            path = "INCREMENTAL"
            self.incremental_steps += 1
        else:
            suffix = decoded
            state = StagePScopeGraphConstraintStateV1_2().feed(decoded)
            path = "FULL_REBUILD"
            self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return ScopeGraphPrefixResultV1_2(state, decoded, ids, path, len(suffix))


__all__ = ("ScopeGraphPrefixResultV1_2", "StagePScopeGraphIncrementalTrackerV1_2")
