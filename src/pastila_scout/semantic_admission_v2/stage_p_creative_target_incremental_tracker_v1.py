"""Incremental prefix tracker bound to Creative Target DFA V1."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_creative_target_constraint_v1 import StagePCreativeTargetConstraintStateV1


@dataclass(frozen=True)
class CreativeTargetPrefixResultV1:
    state: StagePCreativeTargetConstraintStateV1
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePCreativeTargetIncrementalTrackerV1:
    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePCreativeTargetConstraintStateV1()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> CreativeTargetPrefixResultV1:
        ids = tuple(token_ids); decoded = decode(ids)
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]; state = self._last_state.feed(suffix)
            path = "INCREMENTAL"; self.incremental_steps += 1
        else:
            suffix = decoded; state = StagePCreativeTargetConstraintStateV1().feed(decoded)
            path = "FULL_REBUILD"; self.rebuild_steps += 1
        self._last_ids, self._last_decoded, self._last_state = ids, decoded, state
        return CreativeTargetPrefixResultV1(state, decoded, ids, path, len(suffix))


__all__ = ("CreativeTargetPrefixResultV1", "StagePCreativeTargetIncrementalTrackerV1")
