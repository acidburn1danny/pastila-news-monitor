"""Zero-inference incremental Stage P prefix tracker with exact rebuild fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .stage_p_constraint_v1 import StagePConstraintStateV1


@dataclass(frozen=True)
class IncrementalPrefixResultV1:
    state: StagePConstraintStateV1
    decoded: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class StagePIncrementalPrefixTrackerV1:
    """Feed only an exact decoded suffix; rebuild whenever decoding is not prefix-stable."""

    def __init__(self) -> None:
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePConstraintStateV1()
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> IncrementalPrefixResultV1:
        ids = tuple(token_ids)
        decoded = decode(ids)
        extends_ids = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        extends_bytes = decoded.startswith(self._last_decoded)
        if extends_ids and extends_bytes:
            suffix = decoded[len(self._last_decoded):]
            state = self._last_state.feed(suffix)
            path = "INCREMENTAL"
            self.incremental_steps += 1
        else:
            suffix = decoded
            state = StagePConstraintStateV1().feed(decoded)
            path = "FULL_REBUILD"
            self.rebuild_steps += 1
        self._last_ids,self._last_decoded,self._last_state=ids,decoded,state
        return IncrementalPrefixResultV1(state=state,decoded=decoded,token_ids=ids,path=path,suffix_characters=len(suffix))


__all__=("IncrementalPrefixResultV1","StagePIncrementalPrefixTrackerV1")
