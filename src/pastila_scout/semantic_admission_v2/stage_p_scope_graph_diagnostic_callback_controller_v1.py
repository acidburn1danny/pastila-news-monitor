"""V1.2 scope controller using exact baseline projection plus liveness receipts."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from .stage_p_diagnostic_trie_projector_v1 import StagePDiagnosticTokenTrieProjectorV1
from .stage_p_liveness_trie_projector_v1 import StagePConstraintLivenessErrorV1
from .stage_p_scope_graph_callback_controller_v1_1 import ScopeGraphCallbackReceiptV1_1
from .stage_p_scope_graph_incremental_tracker_v1_2 import StagePScopeGraphIncrementalTrackerV1_2


class StagePScopeGraphDiagnosticCallbackControllerV1:
    def __init__(self, *, projector: StagePDiagnosticTokenTrieProjectorV1) -> None:
        self.projector = projector
        self.tracker = StagePScopeGraphIncrementalTrackerV1_2()

    def allowed(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]) -> ScopeGraphCallbackReceiptV1_1:
        prefix = self.tracker.state_for(token_ids, decode)
        try:
            allowed = self.projector.allowed_token_ids(prefix.state)
        except ValueError as exc:
            if str(exc) != "EMPTY_ALLOWED_TOKEN_SET":
                raise
            receipt = self.projector.liveness_receipt(decoded=prefix.decoded, state=prefix.state)
            raise StagePConstraintLivenessErrorV1(receipt) from exc
        return ScopeGraphCallbackReceiptV1_1(
            allowed, prefix.path, prefix.suffix_characters, len(prefix.decoded), prefix.state.mode,
            prefix.state.entry_count, self.tracker.rebuild_steps, self.tracker.incremental_steps,
            self.projector.cache_size,
        )


__all__ = ("StagePScopeGraphDiagnosticCallbackControllerV1",)
