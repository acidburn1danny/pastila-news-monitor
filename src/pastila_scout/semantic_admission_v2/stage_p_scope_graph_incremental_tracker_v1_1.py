"""Incremental prefix tracker bound to the Scope Graph V1.1 DFA."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_scope_graph_constraint_v1_1 import StagePScopeGraphConstraintStateV1_1


@dataclass(frozen=True)
class ScopeGraphPrefixResultV1_1:
    state: StagePScopeGraphConstraintStateV1_1
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePScopeGraphIncrementalTrackerV1_1:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePScopeGraphConstraintStateV1_1()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> ScopeGraphPrefixResultV1_1:
        ids = tuple(token_ids); decoded = decode(ids)
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]; state = self._last_state.feed(suffix); path = "INCREMENTAL"
            self.incremental_steps += 1
        else:
            suffix = decoded; state = StagePScopeGraphConstraintStateV1_1().feed(decoded); path = "FULL_REBUILD"
            self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return ScopeGraphPrefixResultV1_1(state, decoded, ids, path, len(suffix))


__all__ = ("ScopeGraphPrefixResultV1_1", "StagePScopeGraphIncrementalTrackerV1_1")
