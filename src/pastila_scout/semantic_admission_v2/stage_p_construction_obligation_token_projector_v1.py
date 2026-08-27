"""Evaluation-only request-bound token projector for the V2 ledger DFA."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from .stage_p_construction_obligation_character_controller_v1 import (
    CharacterAllowanceKindV1,
    StagePConstructionObligationCharacterControllerV1,
)
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1


RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-token-projection-receipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class TokenProjectionReceiptV1:
    schema_name: str
    schema_version: str
    tokenizer_identity: str
    decoder_identity: str
    context_identity: str
    exclusion_policy_identity: str
    decoded_prefix_sha256: str
    dfa_mode: str
    allowed_token_count: int
    eos_allowed: bool
    liveness: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class TokenProjectionResultV1:
    allowed_token_ids: tuple[int, ...]
    receipt: TokenProjectionReceiptV1


class StagePTokenProjectionLivenessErrorV1(RuntimeError):
    def __init__(self, receipt: TokenProjectionReceiptV1):
        super().__init__(receipt.reason_code or "STAGE_P_TOKENIZATION_LIVENESS_FAILURE")
        self.receipt = receipt


class StagePConstructionObligationTokenProjectorV1:
    """Project complete context-free token pieces through the frozen character DFA."""

    def __init__(self, *, controller: StagePConstructionObligationCharacterControllerV1,
                 token_pieces: Mapping[int, str], eos_token_id: int,
                 tokenizer_identity: str, decoder_identity: str,
                 excluded_token_ids: Iterable[int] = ()) -> None:
        if not tokenizer_identity or not decoder_identity:
            raise ValueError("TOKENIZER_AND_DECODER_IDENTITIES_REQUIRED")
        if controller.tracker.decoder_identity != decoder_identity:
            raise ValueError("CONTROLLER_DECODER_IDENTITY_MISMATCH")
        self.controller = controller
        self.tokenizer_identity = tokenizer_identity
        self.decoder_identity = decoder_identity
        self.eos_token_id = eos_token_id
        excluded = frozenset(excluded_token_ids) | {eos_token_id}
        policy_rows = [tokenizer_identity, decoder_identity, str(eos_token_id),
                       ",".join(map(str, sorted(excluded)))]
        self.exclusion_policy_identity = hashlib.sha256("\n".join(policy_rows).encode()).hexdigest()
        self._children: list[dict[str, int]] = [{}]
        self._terminals: list[list[int]] = [[]]
        for token_id, piece in sorted(token_pieces.items()):
            if token_id in excluded or not piece:
                continue
            node = 0
            for character in piece:
                node = self._children[node].setdefault(character, len(self._children))
                if node == len(self._children):
                    self._children.append({}); self._terminals.append([])
            self._terminals[node].append(token_id)
        self._cache: dict[tuple[object, ...], tuple[int, ...]] = {}

    @property
    def trie_node_count(self) -> int:
        return len(self._children)

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def project(self, token_ids: Sequence[int],
                decode: Callable[[Sequence[int]], str]) -> TokenProjectionResultV1:
        character = self.controller.allowed(token_ids, decode)
        state = character.prefix.state
        terminal = character.allowance.kind is CharacterAllowanceKindV1.TERMINAL
        key = (self.tokenizer_identity, self.decoder_identity,
               character.prefix.context_identity, self.exclusion_policy_identity,
               character.prefix.decoded_sha256, state)
        allowed = self._cache.get(key)
        if allowed is None:
            allowed = (self.eos_token_id,) if terminal else self._project_state(state)
            self._cache[key] = allowed
        receipt = TokenProjectionReceiptV1(
            RECEIPT_SCHEMA_NAME, RECEIPT_SCHEMA_VERSION, self.tokenizer_identity,
            self.decoder_identity, character.prefix.context_identity,
            self.exclusion_policy_identity, character.prefix.decoded_sha256,
            "TERMINAL" if terminal else state.mode, len(allowed),
            self.eos_token_id in allowed,
            "TOKENIZATION_TERMINAL_EOS_ALLOWED" if terminal else (
                "TOKENIZATION_CONTINUABLE" if allowed else "TOKENIZATION_DEAD_NO_VALID_TOKEN"),
            None if allowed else "STAGE_P_TOKEN_ALLOWED_SET_EMPTY")
        if not allowed:
            raise StagePTokenProjectionLivenessErrorV1(receipt)
        return TokenProjectionResultV1(allowed, receipt)

    def allowed_token_ids(self, token_ids: Sequence[int],
                          decode: Callable[[Sequence[int]], str]) -> tuple[int, ...]:
        return self.project(token_ids, decode).allowed_token_ids

    def _project_state(self, state) -> tuple[int, ...]:
        allowed: list[int] = []
        stack = [(0, state)]
        while stack:
            node, current = stack.pop()
            allowed.extend(self._terminals[node])
            for character, child in self._children[node].items():
                try:
                    advanced = current.feed(character)
                except StagePRoleCoherenceConstraintViolationV1:
                    continue
                stack.append((child, advanced))
        return tuple(sorted(allowed))


def canonical_token_projection_receipt_bytes_v1(receipt: TokenProjectionReceiptV1) -> bytes:
    value = {field: getattr(receipt, field) for field in receipt.__dataclass_fields__}
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "StagePConstructionObligationTokenProjectorV1", "StagePTokenProjectionLivenessErrorV1",
    "TokenProjectionReceiptV1", "TokenProjectionResultV1",
    "canonical_token_projection_receipt_bytes_v1",
)
