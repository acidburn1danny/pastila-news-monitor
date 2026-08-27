"""Incremental prefix tracker for Construction Obligation Projection V1."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_construction_obligation_constraint_v1 import StagePConstructionObligationConstraintStateV1


@dataclass(frozen=True)
class ConstructionObligationPrefixResultV1:
    state: StagePConstructionObligationConstraintStateV1
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePConstructionObligationIncrementalTrackerV1:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePConstructionObligationConstraintStateV1()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int],
                  decode: Callable[[Sequence[int]], str]) -> ConstructionObligationPrefixResultV1:
        ids = tuple(token_ids); decoded = decode(ids)
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]; state = self._last_state.feed(suffix)
            path = "INCREMENTAL"; self.incremental_steps += 1
        else:
            suffix = decoded; state = StagePConstructionObligationConstraintStateV1().feed(decoded)
            path = "FULL_REBUILD"; self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return ConstructionObligationPrefixResultV1(state, decoded, ids, path, len(suffix))


__all__ = ("ConstructionObligationPrefixResultV1", "StagePConstructionObligationIncrementalTrackerV1")
