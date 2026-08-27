"""Baseline-language Stage-P projector with diagnostic liveness receipts only."""
from __future__ import annotations

import hashlib

from .stage_p_liveness_trie_projector_v1 import StagePConstraintLivenessReceiptV1
from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


class StagePDiagnosticTokenTrieProjectorV1(StagePTokenTrieProjectorV1):
    """Inherit baseline allowed-token behavior without lookahead or filtering."""

    @staticmethod
    def liveness_receipt(*, decoded: str, state) -> StagePConstraintLivenessReceiptV1:
        raw = decoded.encode("utf-8")
        return StagePConstraintLivenessReceiptV1(
            code="CONSTRAINT_LIVENESS_FAILURE",
            decoded_utf8_bytes=len(raw),
            decoded_sha256=hashlib.sha256(raw).hexdigest(),
            dfa_mode=state.mode,
            dfa_next_step=state.next_step,
            entry_count=state.entry_count,
        )


__all__ = ("StagePDiagnosticTokenTrieProjectorV1",)
