"""Optimized evaluation-only trie projection over the frozen Gate-F DFA."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping


class GateFTokenTrieProjectorOptimizedV1:
    def __init__(self, *, token_pieces: Mapping[int, str], eos_token_id: int, excluded_token_ids: Iterable[int] = ()) -> None:
        excluded = frozenset(excluded_token_ids) | {eos_token_id}
        self._eos = eos_token_id
        self._children: list[dict[str, int]] = [{}]
        self._terminals: list[list[int]] = [[]]
        retained = []
        for token_id, piece in sorted(token_pieces.items()):
            if token_id in excluded or not piece:
                continue
            retained.append(piece)
            node = 0
            for char in piece:
                child = self._children[node].get(char)
                if child is None:
                    child = len(self._children)
                    self._children[node][char] = child
                    self._children.append({})
                    self._terminals.append([])
                node = child
            self._terminals[node].append(token_id)
        self._maximum_piece_characters = max(map(len, retained), default=0)
        self._cache: dict[Any, tuple[int, ...]] = {}

    @property
    def trie_node_count(self) -> int:
        return len(self._children)

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def allowed_token_ids(self, state: Any) -> tuple[int, ...]:
        if state.can_eos:
            return (self._eos,)
        key = self._cache_key(state)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        allowed: list[int] = []
        stack: list[tuple[int, Any]] = [(0, state)]
        while stack:
            node, current = stack.pop()
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

    def prewarm(self, states: Iterable[Any]) -> None:
        for state in states:
            self.allowed_token_ids(state)

    def _cache_key(self, state: Any) -> Any:
        characters = state.characters
        if characters <= 8000 - self._maximum_piece_characters:
            characters = 0
        buffer = "" if state.mode in {"STRING", "VALUE_START", "LITERAL", "AFTER_RECORD"} else state.buffer
        return replace(state, characters=characters, buffer=buffer)


__all__ = ("GateFTokenTrieProjectorOptimizedV1",)
