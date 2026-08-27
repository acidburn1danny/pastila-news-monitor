"""Stage-P-specific trie cache canonicalization; evaluation-only candidate."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .gate_f_trie_projector_v1 import GateFTokenTrieProjectorOptimizedV1


class StagePTokenTrieProjectorV1(GateFTokenTrieProjectorOptimizedV1):
    """Reuse a STRING continuation cache after preserving empty/nonempty semantics."""

    def _cache_key(self,state:Any)->Any:
        key=super()._cache_key(state)
        if key.mode=="STRING" and key.string_characters>0:
            key=replace(key,string_characters=1)
        return key


__all__=("StagePTokenTrieProjectorV1",)
