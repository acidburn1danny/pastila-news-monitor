"""Indexed, request-bound V2 token projection with V1 as the oracle."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .stage_p_construction_obligation_character_controller_v1 import (
    CharacterAllowanceKindV1,
    StagePCharacterLivenessErrorV1,
    StagePConstructionObligationCharacterControllerV1,
    _allowance_for_state,
)
from .stage_p_construction_obligation_v2_token_projector_v1 import (
    TokenProjectionReceiptV1,
    TokenProjectionResultV1,
    StagePTokenProjectionFailureV1,
)
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1


PROJECTOR_ALGORITHM_IDENTITY = "REQUEST_BOUND_TOKEN_PIECE_TRIE_V2"
GRAMMAR_IDENTITY = "CONSTRUCTION_OBLIGATION_DFA_V2"


@dataclass(frozen=True, slots=True)
class IndexedProjectionStatisticsV2:
    cache_hits: int
    cache_misses: int
    visited_trie_nodes: int
    admitted_terminal_tokens: int


class StagePConstructionObligationV2TokenProjectorV2:
    """Traverse only DFA-compatible token-piece trie branches."""

    def __init__(
        self, *, controller: StagePConstructionObligationCharacterControllerV1,
        token_pieces: Mapping[int, str], eos_token_id: int,
        tokenizer_identity: str, decoder_identity: str,
        request_context_identity: str, request_authority_identity: str,
        grammar_identity: str = GRAMMAR_IDENTITY,
        excluded_token_ids: Sequence[int] = (),
        terminal_admission: Callable[[str], object] | None = None,
        terminal_admission_identity: str | None = None,
    ) -> None:
        if controller.tracker.context.binding_identity != request_context_identity:
            raise ValueError("REQUEST_CONTEXT_IDENTITY_MISMATCH")
        if controller.tracker.decoder_identity != decoder_identity:
            raise ValueError("DECODER_IDENTITY_MISMATCH")
        if not tokenizer_identity or not request_authority_identity or not grammar_identity:
            raise ValueError("PROJECTOR_SEMANTIC_IDENTITY_REQUIRED")
        if (terminal_admission is None) != (terminal_admission_identity is None):
            raise ValueError("TERMINAL_ADMISSION_BINDING_INCOMPLETE")
        excluded = frozenset(excluded_token_ids) | {eos_token_id}
        self.controller = controller
        self.eos_token_id = eos_token_id
        self.tokenizer_identity = tokenizer_identity
        self.decoder_identity = decoder_identity
        self.request_context_identity = request_context_identity
        self.request_authority_identity = request_authority_identity
        self.excluded_token_ids = excluded
        self._terminal_admission = terminal_admission
        self.terminal_admission_identity = terminal_admission_identity
        self._bound_token_pieces = dict(token_pieces)
        self._children: list[dict[str, int]] = [{}]
        self._terminals: list[list[int]] = [[]]
        self._all_children: list[dict[str, int]] = [{}]
        self._all_terminals: list[list[int]] = [[]]
        self._ordinary_string_tokens_by_length: dict[int, list[int]] = {}
        for token_id, piece in sorted(token_pieces.items()):
            if type(token_id) is not int or type(piece) is not str:
                raise ValueError("MALFORMED_TOKEN_PIECE")
            if token_id in excluded or not piece:
                continue
            if any(0xD800 <= ord(character) <= 0xDFFF for character in piece):
                continue
            all_node = 0
            for character in piece:
                all_child = self._all_children[all_node].get(character)
                if all_child is None:
                    all_child = len(self._all_children)
                    self._all_children[all_node][character] = all_child
                    self._all_children.append({})
                    self._all_terminals.append([])
                all_node = all_child
            self._all_terminals[all_node].append(token_id)
            if all(ord(character) >= 0x20 and character not in {'"', "\\"}
                   for character in piece):
                self._ordinary_string_tokens_by_length.setdefault(
                    len(piece), []).append(token_id)
                continue
            node = 0
            for character in piece:
                child = self._children[node].get(character)
                if child is None:
                    child = len(self._children)
                    self._children[node][character] = child
                    self._children.append({})
                    self._terminals.append([])
                node = child
            self._terminals[node].append(token_id)
        special_policy = ",".join(map(str, sorted(excluded)))
        self.cache_domain_identity = hashlib.sha256(
            (PROJECTOR_ALGORITHM_IDENTITY + "\n" + grammar_identity + "\n"
             + request_authority_identity + "\n" + request_context_identity + "\n"
             + tokenizer_identity + "\n" + decoder_identity + "\n"
             + special_policy + "\n" + (terminal_admission_identity or "NONE")).encode()).hexdigest()
        self._cache: dict[str, tuple[int, ...]] = {}
        self._hits = self._misses = self._visited = self._admitted = 0

    @property
    def trie_node_count(self) -> int:
        return len(self._children)

    @property
    def statistics(self) -> IndexedProjectionStatisticsV2:
        return IndexedProjectionStatisticsV2(
            self._hits, self._misses, self._visited, self._admitted)

    def allowed_token_ids(
        self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str],
    ) -> TokenProjectionResultV1:
        try:
            character = self.controller.allowed(token_ids, decode)
        except (StagePCharacterLivenessErrorV1, StagePRoleCoherenceConstraintViolationV1,
                UnicodeError, ValueError, TypeError) as exc:
            digest = hashlib.sha256(type(exc).__name__.encode()).hexdigest()
            receipt = TokenProjectionReceiptV1(
                "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt",
                "1.0.0-evaluation.1", self.request_context_identity,
                self.tokenizer_identity, self.decoder_identity, digest, "INVALID",
                False, 0, False, "FAIL_CLOSED", "UNBOUND_OR_INVALID_CHARACTER_PREFIX")
            raise StagePTokenProjectionFailureV1(receipt) from exc
        prefix = character.prefix
        if prefix.context_identity != self.request_context_identity:
            raise ValueError("CONTEXT_IDENTITY_DRIFT")
        if prefix.decoder_identity != self.decoder_identity:
            raise ValueError("DECODER_IDENTITY_DRIFT")
        if character.allowance.kind is CharacterAllowanceKindV1.TERMINAL:
            if self._terminal_admission is not None:
                try:
                    self._terminal_admission(decode(token_ids))
                except (ValueError, TypeError) as exc:
                    receipt = self._receipt(
                        prefix, (), False, str(exc) or "SEMANTIC_COMPLETENESS_REJECTED")
                    raise StagePTokenProjectionFailureV1(receipt) from exc
            allowed = (self.eos_token_id,)
        else:
            state_key = hashlib.sha256(repr(prefix.state).encode()).hexdigest()
            key = self.cache_domain_identity + ":" + state_key
            allowed = self._cache.get(key)
            if allowed is not None:
                self._hits += 1
            else:
                self._misses += 1
                allowed = self._project(prefix.state, character.allowance)
                self._cache[key] = allowed
        if not allowed:
            receipt = self._receipt(prefix, (), False, "TOKENIZATION_DEAD_NO_VALID_TOKEN")
            raise StagePTokenProjectionFailureV1(receipt)
        return TokenProjectionResultV1(
            allowed, self._receipt(prefix, allowed, self.eos_token_id in allowed, None))

    def _project(self, state, root_allowance) -> tuple[int, ...]:
        admitted: list[int] = []
        ordinary_string = (
            state.mode == "STRING" and not state.string_escape
            and not state.unicode_remaining)
        if ordinary_string:
            remaining = 16000 - state.characters
            for length, token_ids in self._ordinary_string_tokens_by_length.items():
                if length <= remaining:
                    admitted.extend(token_ids)
        children = self._children if ordinary_string else self._all_children
        terminals = self._terminals if ordinary_string else self._all_terminals
        stack = [(0, state, root_allowance)]
        visited = 0
        while stack:
            node, current, allowance = stack.pop()
            visited += 1
            admitted.extend(terminals[node])
            for character, child in children[node].items():
                if not allowance.permits(character):
                    continue
                try:
                    advanced = current._feed_char(character)
                except (StagePRoleCoherenceConstraintViolationV1, UnicodeError,
                        ValueError, TypeError):
                    continue
                stack.append((child, advanced, _allowance_for_state(advanced)))
        result = tuple(sorted(admitted))
        self._visited += visited
        self._admitted += len(result)
        return result

    def _receipt(self, prefix, allowed, eos, reason):
        return TokenProjectionReceiptV1(
            "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt",
            "1.0.0-evaluation.1", self.request_context_identity,
            self.tokenizer_identity, self.decoder_identity, prefix.decoded_sha256,
            prefix.state.mode, prefix.state.terminal, len(allowed), eos,
            "FAIL_CLOSED" if reason else ("TOKENIZATION_TERMINAL_EOS_ALLOWED" if eos
                                           else "TOKENIZATION_CONTINUABLE"), reason)


__all__ = (
    "GRAMMAR_IDENTITY", "IndexedProjectionStatisticsV2", "PROJECTOR_ALGORITHM_IDENTITY",
    "StagePConstructionObligationV2TokenProjectorV2",
)
