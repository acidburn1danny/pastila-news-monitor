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
MAX_EXACT_CANDIDATES_PER_CALLBACK = 16_384
MAX_EXACT_DECODE_TOKEN_WORK_PER_REQUEST = 64_000_000


@dataclass(frozen=True, slots=True)
class IndexedProjectionStatisticsV2:
    cache_hits: int
    cache_misses: int
    visited_trie_nodes: int
    admitted_terminal_tokens: int


def _build_index(token_pieces, excluded):
    children: list[dict[str, int]] = [{}]
    terminals: list[list[int]] = [[]]
    all_children: list[dict[str, int]] = [{}]
    all_terminals: list[list[int]] = [[]]
    ordinary: dict[int, list[int]] = {}
    for token_id, piece in sorted(token_pieces.items()):
        if type(token_id) is not int or type(piece) is not str:
            raise ValueError("MALFORMED_TOKEN_PIECE")
        if token_id in excluded or not piece or any(
                0xD800 <= ord(character) <= 0xDFFF for character in piece):
            continue
        all_node = 0
        for character in piece:
            child = all_children[all_node].get(character)
            if child is None:
                child = len(all_children)
                all_children[all_node][character] = child
                all_children.append({})
                all_terminals.append([])
            all_node = child
        all_terminals[all_node].append(token_id)
        if all(ord(character) >= 0x20 and character not in {'"', "\\"}
               for character in piece):
            ordinary.setdefault(len(piece), []).append(token_id)
            continue
        node = 0
        for character in piece:
            child = children[node].get(character)
            if child is None:
                child = len(children)
                children[node][character] = child
                children.append({})
                terminals.append([])
            node = child
        terminals[node].append(token_id)
    return children, terminals, all_children, all_terminals, ordinary


class StagePConstructionObligationV2TokenProjectorV2:
    """Traverse only DFA-compatible token-piece trie branches."""

    def __init__(
        self, *, controller: StagePConstructionObligationCharacterControllerV1,
        token_pieces: Mapping[int, str], eos_token_id: int,
        tokenizer_identity: str, decoder_identity: str,
        request_context_identity: str, request_authority_identity: str,
        grammar_identity: str = GRAMMAR_IDENTITY,
        excluded_token_ids: Sequence[int] = (),
        initial_token_pieces: Mapping[int, str] | None = None,
        exact_history_decoder: bool = False,
        decoder_mechanism_identity: str | None = None,
        terminal_admission: Callable[[str], object] | None = None,
        terminal_admission_identity: str | None = None,
        structural_liveness_pruning: bool = False,
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
        if type(structural_liveness_pruning) is not bool:
            raise TypeError("STRUCTURAL_LIVENESS_PRUNING_BOOL_REQUIRED")
        self.structural_liveness_pruning = structural_liveness_pruning
        if type(exact_history_decoder) is not bool:
            raise TypeError("EXACT_HISTORY_DECODER_FLAG_BOOL_REQUIRED")
        self.exact_history_decoder = exact_history_decoder
        self._bound_token_pieces = dict(token_pieces)
        self._bound_initial_token_pieces = dict(
            token_pieces if initial_token_pieces is None else initial_token_pieces)
        if set(self._bound_initial_token_pieces) != set(self._bound_token_pieces):
            raise ValueError("INITIAL_CONTINUATION_TOKEN_DOMAIN_MISMATCH")
        piece_identity = hashlib.sha256("\n".join(
            f"{token_id}:{self._bound_initial_token_pieces[token_id]!r}:"
            f"{self._bound_token_pieces[token_id]!r}"
            for token_id in sorted(self._bound_token_pieces)).encode()).hexdigest()
        (self._children, self._terminals, self._all_children,
         self._all_terminals, self._ordinary_string_tokens_by_length) = (
            _build_index(self._bound_token_pieces, excluded))
        (self._initial_children, self._initial_terminals,
         self._initial_all_children, self._initial_all_terminals,
         self._initial_ordinary_string_tokens_by_length) = _build_index(
            self._bound_initial_token_pieces, excluded)
        special_policy = ",".join(map(str, sorted(excluded)))
        self.cache_domain_identity = hashlib.sha256(
            (PROJECTOR_ALGORITHM_IDENTITY + "\n" + grammar_identity + "\n"
             + request_authority_identity + "\n" + request_context_identity + "\n"
             + tokenizer_identity + "\n" + decoder_identity + "\n"
             + special_policy + "\n" + piece_identity + "\n"
             + f"exact-history-decoder:{exact_history_decoder}\n"
             + f"decoder-mechanism:{decoder_mechanism_identity or 'NONE'}\n"
             + f"structural-liveness-pruning:{structural_liveness_pruning}\n"
             + (terminal_admission_identity or "NONE")).encode()).hexdigest()
        self._cache: dict[str, tuple[int, ...]] = {}
        self._structural_liveness_cache: dict[str, bool] = {}
        self._hits = self._misses = self._visited = self._admitted = 0
        self._exact_decode_token_work = 0

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
            observed_decoded = decode(token_ids)
            if type(observed_decoded) is not str:
                raise TypeError("DECODE_OUTPUT_NOT_STRING")
            observed_sha256 = hashlib.sha256(
                observed_decoded.encode("utf-8")).hexdigest()
        except (UnicodeError, ValueError, TypeError) as exc:
            digest = hashlib.sha256(type(exc).__name__.encode()).hexdigest()
            receipt = TokenProjectionReceiptV1(
                "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt",
                "1.0.0-evaluation.1", self.request_context_identity,
                self.tokenizer_identity, self.decoder_identity, digest, "INVALID",
                False, 0, False, "FAIL_CLOSED", "UNBOUND_OR_INVALID_CHARACTER_PREFIX")
            raise StagePTokenProjectionFailureV1(receipt) from exc
        try:
            character = self.controller.allowed(
                token_ids, lambda _ids: observed_decoded)
        except StagePCharacterLivenessErrorV1 as exc:
            source = exc.receipt
            receipt = TokenProjectionReceiptV1(
                "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt",
                "1.0.0-evaluation.1", self.request_context_identity,
                self.tokenizer_identity, self.decoder_identity,
                source.decoded_sha256, source.dfa_mode, False, 0, False,
                "FAIL_CLOSED", source.reason_code or "STAGE_P_CHARACTER_ALLOWED_SET_EMPTY")
            raise StagePTokenProjectionFailureV1(receipt) from exc
        except (StagePRoleCoherenceConstraintViolationV1,
                UnicodeError, ValueError, TypeError) as exc:
            receipt = TokenProjectionReceiptV1(
                "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt",
                "1.0.0-evaluation.1", self.request_context_identity,
                self.tokenizer_identity, self.decoder_identity,
                observed_sha256, "INVALID", False, 0, False, "FAIL_CLOSED",
                "UNBOUND_OR_INVALID_CHARACTER_PREFIX")
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
            phase = "INITIAL" if not token_ids else "CONTINUATION"
            key = self.cache_domain_identity + ":" + phase + ":" + state_key
            allowed = self._cache.get(key)
            if allowed is not None:
                self._hits += 1
            else:
                self._misses += 1
                allowed = self._project(
                    prefix.state, character.allowance, initial=(phase == "INITIAL"))
                # Recursive look-ahead is advisory.  It may rank every immediate
                # grammar-valid token as eventually dead, but it must not create
                # a false current-state no-token classification.  In that case
                # retain the exact immediate DFA projection and let the next
                # observed state classify any genuine dead end losslessly.
                if (not allowed and self.structural_liveness_pruning
                        and prefix.state.mode == "LITERAL"):
                    allowed = self._project(
                        prefix.state, character.allowance,
                        initial=(phase == "INITIAL"), prune_literals=False)
                self._cache[key] = allowed
            if self.exact_history_decoder:
                allowed = self._exact_candidates(
                    token_ids, decode, prefix, allowed,
                    initial=(phase == "INITIAL"))
        if not allowed:
            receipt = self._receipt(prefix, (), False, "TOKENIZATION_DEAD_NO_VALID_TOKEN")
            raise StagePTokenProjectionFailureV1(receipt)
        return TokenProjectionResultV1(
            allowed, self._receipt(prefix, allowed, self.eos_token_id in allowed, None))

    def _project(self, state, root_allowance, *, initial: bool,
                 prune_literals: bool = True) -> tuple[int, ...]:
        admitted: list[int] = []
        ordinary_string = (
            state.mode == "STRING" and not state.string_escape
            and not state.unicode_remaining)
        if ordinary_string:
            remaining = 16000 - state.characters
            ordinary = (self._initial_ordinary_string_tokens_by_length if initial
                        else self._ordinary_string_tokens_by_length)
            for length, token_ids in ordinary.items():
                if length <= remaining:
                    admitted.extend(token_ids)
        if initial:
            children = (self._initial_children if ordinary_string
                        else self._initial_all_children)
            terminals = (self._initial_terminals if ordinary_string
                         else self._initial_all_terminals)
        else:
            children = self._children if ordinary_string else self._all_children
            terminals = self._terminals if ordinary_string else self._all_terminals
        stack = [(0, state, root_allowance)]
        prune_literal_dead_ends = (
            prune_literals and self.structural_liveness_pruning
            and state.mode == "LITERAL")
        visited = 0
        while stack:
            node, current, allowance = stack.pop()
            visited += 1
            if terminals[node] and (
                    not prune_literal_dead_ends or current.terminal
                    or self._has_structural_successor(current)):
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

    def _has_structural_successor(self, state) -> bool:
        """Reject a structurally valid token that creates an immediate trie dead end."""
        key = hashlib.sha256(repr(state).encode()).hexdigest()
        cached = self._structural_liveness_cache.get(key)
        if cached is not None:
            return cached
        stack = [(0, state, _allowance_for_state(state))]
        seen = set()
        while stack:
            node, current, allowance = stack.pop()
            marker = (node, repr(current))
            if marker in seen:
                continue
            seen.add(marker)
            if self._all_terminals[node] and (
                    current.terminal or current.mode != "LITERAL"
                    or self._has_structural_successor(current)):
                self._structural_liveness_cache[key] = True
                return True
            for character, child in self._all_children[node].items():
                if not allowance.permits(character):
                    continue
                try:
                    advanced = current._feed_char(character)
                except (StagePRoleCoherenceConstraintViolationV1, UnicodeError,
                        ValueError, TypeError):
                    continue
                stack.append((child, advanced, _allowance_for_state(advanced)))
        self._structural_liveness_cache[key] = False
        return False

    def _exact_candidates(
        self, token_ids, decode, prefix, candidates, *, initial: bool,
    ):
        if len(candidates) > MAX_EXACT_CANDIDATES_PER_CALLBACK:
            return ()
        admitted = []
        history = tuple(token_ids)
        required_work = len(candidates) * (len(history) + 1)
        if (self._exact_decode_token_work + required_work
                > MAX_EXACT_DECODE_TOKEN_WORK_PER_REQUEST):
            return ()
        self._exact_decode_token_work += required_work
        base = prefix.decoded
        for token_id in candidates:
            try:
                extended = decode(history + (token_id,))
                if (type(extended) is not str
                        or not extended.startswith(base)):
                    continue
                piece = extended[len(base):]
                expected = (self._bound_initial_token_pieces[token_id] if initial
                            else self._bound_token_pieces[token_id])
                if type(piece) is not str or not piece or piece != expected:
                    continue
                prefix.state.feed(piece)
            except (StagePRoleCoherenceConstraintViolationV1, UnicodeError,
                    ValueError, TypeError, KeyError):
                continue
            admitted.append(token_id)
        return tuple(admitted)

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
