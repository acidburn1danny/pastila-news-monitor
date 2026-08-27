"""Evaluation-only one-token viability projector for Stage-P constrained decoding."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


@dataclass(frozen=True)
class StagePConstraintLivenessReceiptV1:
    code: str
    decoded_utf8_bytes: int
    decoded_sha256: str
    dfa_mode: str
    dfa_next_step: str
    entry_count: int

    def as_json_value(self) -> dict[str, object]:
        return {
            "code": self.code,
            "decoded_utf8_bytes": self.decoded_utf8_bytes,
            "decoded_sha256": self.decoded_sha256,
            "dfa_mode": self.dfa_mode,
            "dfa_next_step": self.dfa_next_step,
            "entry_count": self.entry_count,
        }


class StagePConstraintLivenessErrorV1(ValueError):
    def __init__(self, receipt: StagePConstraintLivenessReceiptV1) -> None:
        super().__init__(json.dumps(receipt.as_json_value(), sort_keys=True, separators=(",", ":")))
        self.receipt = receipt


class StagePLivenessTokenTrieProjectorV1(StagePTokenTrieProjectorV1):
    """Prune tokens whose resulting DFA state has no next token or legal EOS.

    This is a tokenization-liveness filter only. Character-DFA language and EOS
    policy remain unchanged.
    """

    def allowed_token_ids(self, state: Any) -> tuple[int, ...]:
        if state.can_eos:
            return (self._eos,)
        key = ("viable", self._cache_key(state))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        allowed: list[int] = []
        stack: list[tuple[int, Any]] = [(0, state)]
        while stack:
            node, current = stack.pop()
            if self._terminals[node] and self._has_next_token_or_eos(current):
                allowed.extend(self._terminals[node])
            for char, child in self._children[node].items():
                try:
                    advanced = current.feed(char)
                except ValueError:
                    continue
                stack.append((child, advanced))
        if not allowed:
            raise ValueError("EMPTY_ALLOWED_TOKEN_SET")
        result = tuple(sorted(allowed))
        self._cache[key] = result
        return result

    def _has_next_token_or_eos(self, state: Any) -> bool:
        if state.can_eos:
            return True
        stack: list[tuple[int, Any]] = [(0, state)]
        while stack:
            node, current = stack.pop()
            if self._terminals[node]:
                return True
            for char, child in self._children[node].items():
                try:
                    advanced = current.feed(char)
                except ValueError:
                    continue
                stack.append((child, advanced))
        return False

    @staticmethod
    def liveness_receipt(*, decoded: str, state: Any) -> StagePConstraintLivenessReceiptV1:
        raw = decoded.encode("utf-8")
        return StagePConstraintLivenessReceiptV1(
            code="CONSTRAINT_LIVENESS_FAILURE",
            decoded_utf8_bytes=len(raw),
            decoded_sha256=hashlib.sha256(raw).hexdigest(),
            dfa_mode=state.mode,
            dfa_next_step=state.next_step,
            entry_count=state.entry_count,
        )


__all__ = (
    "StagePConstraintLivenessErrorV1",
    "StagePConstraintLivenessReceiptV1",
    "StagePLivenessTokenTrieProjectorV1",
)
