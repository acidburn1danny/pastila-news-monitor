"""Trie callback controller bound to the Stage P role-coherence tracker."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_role_coherence_incremental_tracker_v1 import StagePRoleCoherenceIncrementalTrackerV1
from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


@dataclass(frozen=True)
class RoleCoherenceCallbackReceiptV1:
    allowed_token_ids: tuple[int, ...]
    tracking_path: str
    suffix_characters: int
    decoded_characters: int
    dfa_mode: str
    entry_count: int
    tracker_rebuilds: int
    tracker_incremental_steps: int
    trie_cache_size: int


class StagePRoleCoherenceCallbackControllerV1:
    def __init__(self, *, projector: StagePTokenTrieProjectorV1) -> None:
        self.projector = projector
        self.tracker = StagePRoleCoherenceIncrementalTrackerV1()

    def allowed(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> RoleCoherenceCallbackReceiptV1:
        prefix = self.tracker.state_for(token_ids, decode)
        allowed = self.projector.allowed_token_ids(prefix.state)
        return RoleCoherenceCallbackReceiptV1(
            allowed_token_ids=allowed, tracking_path=prefix.path, suffix_characters=prefix.suffix_characters,
            decoded_characters=len(prefix.decoded), dfa_mode=prefix.state.mode, entry_count=prefix.state.entry_count,
            tracker_rebuilds=self.tracker.rebuild_steps, tracker_incremental_steps=self.tracker.incremental_steps,
            trie_cache_size=self.projector.cache_size,
        )


__all__ = ("RoleCoherenceCallbackReceiptV1", "StagePRoleCoherenceCallbackControllerV1")
