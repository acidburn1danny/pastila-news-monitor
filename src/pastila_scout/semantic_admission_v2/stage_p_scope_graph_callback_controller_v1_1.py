"""Trie callback controller bound to the Scope Graph V1.1 tracker."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_scope_graph_incremental_tracker_v1_1 import StagePScopeGraphIncrementalTrackerV1_1
from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


@dataclass(frozen=True)
class ScopeGraphCallbackReceiptV1_1:
    allowed_token_ids: tuple[int, ...]
    tracking_path: str
    suffix_characters: int
    decoded_characters: int
    dfa_mode: str
    entry_count: int
    tracker_rebuilds: int
    tracker_incremental_steps: int
    trie_cache_size: int


class StagePScopeGraphCallbackControllerV1_1:
    def __init__(self, *, projector: StagePTokenTrieProjectorV1) -> None:
        self.projector = projector; self.tracker = StagePScopeGraphIncrementalTrackerV1_1()

    def allowed(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> ScopeGraphCallbackReceiptV1_1:
        prefix = self.tracker.state_for(token_ids, decode); allowed = self.projector.allowed_token_ids(prefix.state)
        return ScopeGraphCallbackReceiptV1_1(allowed, prefix.path, prefix.suffix_characters, len(prefix.decoded),
            prefix.state.mode, prefix.state.entry_count, self.tracker.rebuild_steps, self.tracker.incremental_steps,
            self.projector.cache_size)


__all__ = ("ScopeGraphCallbackReceiptV1_1", "StagePScopeGraphCallbackControllerV1_1")
