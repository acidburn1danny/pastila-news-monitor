"""Evaluation-only composition of incremental Stage P state and canonicalized trie cache."""
from __future__ import annotations

from collections.abc import Callable,Sequence
from dataclasses import dataclass

from .stage_p_incremental_tracker_v1 import StagePIncrementalPrefixTrackerV1
from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


@dataclass(frozen=True)
class StagePCallbackReceiptV1:
    allowed_token_ids: tuple[int,...]
    tracking_path: str
    suffix_characters: int
    decoded_characters: int
    dfa_mode: str
    entry_count: int
    tracker_rebuilds: int
    tracker_incremental_steps: int
    trie_cache_size: int


class StagePCallbackControllerV1:
    def __init__(self,*,projector:StagePTokenTrieProjectorV1)->None:
        self.projector=projector;self.tracker=StagePIncrementalPrefixTrackerV1()

    def allowed(self,token_ids:Sequence[int],decode:Callable[[Sequence[int]],str])->StagePCallbackReceiptV1:
        prefix=self.tracker.state_for(token_ids,decode);allowed=self.projector.allowed_token_ids(prefix.state)
        return StagePCallbackReceiptV1(allowed_token_ids=allowed,tracking_path=prefix.path,
            suffix_characters=prefix.suffix_characters,decoded_characters=len(prefix.decoded),dfa_mode=prefix.state.mode,
            entry_count=prefix.state.entry_count,tracker_rebuilds=self.tracker.rebuild_steps,
            tracker_incremental_steps=self.tracker.incremental_steps,trie_cache_size=self.projector.cache_size)


__all__=("StagePCallbackControllerV1","StagePCallbackReceiptV1")
