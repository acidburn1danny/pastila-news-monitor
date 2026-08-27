"""Zero-inference token projector candidate for the frozen Phase 2 audit DFAs.

This module has no tokenizer-loading, model, evaluator, runner, probe, or Stage C
dependency.  Callers must supply the already identity-bound, context-free decoded
piece for every vocabulary token.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from .stage_p_constraint_v1 import StagePConstraintViolationV1
from .stage_p_phase2_character_controller_v1 import (
    CharacterAllowanceKindV1,
    Phase2CharacterControllerV1,
)

RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-phase2-token-projection-receipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation-candidate.1"


@dataclass(frozen=True, slots=True)
class Phase2TokenProjectionReceiptV1:
    schema_name: str
    schema_version: str
    audit_lane: str
    tokenizer_identity: str
    decoder_identity: str
    grammar_identity: str
    request_context_identity: str
    exclusion_policy_identity: str
    character_receipt_sha256: str
    decoded_prefix_sha256: str
    strategy_class: str
    allowed_token_set_sha256: str
    allowed_token_count: int
    eos_disposition: str
    liveness: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class Phase2TokenProjectionResultV1:
    allowed_token_ids: tuple[int, ...]
    receipt: Phase2TokenProjectionReceiptV1


class Phase2TokenProjectionLivenessErrorV1(RuntimeError):
    def __init__(self, receipt: Phase2TokenProjectionReceiptV1) -> None:
        super().__init__(receipt.reason_code or "PHASE2_TOKENIZATION_LIVENESS_FAILURE")
        self.receipt = receipt


class Phase2TokenProjectorV1:
    """Project complete context-free token pieces through one frozen audit DFA."""

    def __init__(
        self,
        *,
        controller: Phase2CharacterControllerV1,
        token_pieces: Mapping[int, str],
        eos_token_id: int,
        tokenizer_identity: str,
        decoder_identity: str,
        excluded_token_ids: Iterable[int] = (),
    ) -> None:
        if not tokenizer_identity:
            raise ValueError("PHASE2_TOKENIZER_IDENTITY_REQUIRED")
        if decoder_identity != controller.decoder_identity:
            raise ValueError("PHASE2_PROJECTOR_DECODER_IDENTITY_MISMATCH")
        if type(eos_token_id) is not int:
            raise ValueError("PHASE2_EOS_TOKEN_ID_INVALID")
        self.controller = controller
        self.tokenizer_identity = tokenizer_identity
        self.decoder_identity = decoder_identity
        self.eos_token_id = eos_token_id
        excluded = frozenset(excluded_token_ids) | {eos_token_id}
        self.exclusion_policy_identity = hashlib.sha256("\n".join((
            tokenizer_identity, decoder_identity, str(eos_token_id),
            ",".join(map(str, sorted(excluded))),
        )).encode()).hexdigest()
        self._children: list[dict[str, int]] = [{}]
        self._terminals: list[list[int]] = [[]]
        for token_id, piece in sorted(token_pieces.items()):
            if type(token_id) is not int or type(piece) is not str:
                raise ValueError("PHASE2_TOKEN_PIECE_INVALID")
            if token_id in excluded or not piece or "\ufffd" in piece:
                continue
            if any(0xD800 <= ord(character) <= 0xDFFF for character in piece):
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

    @property
    def trie_node_count(self) -> int:
        return len(self._children)

    def project(
        self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]
    ) -> Phase2TokenProjectionResultV1:
        character = self.controller.allowed(token_ids, decode)
        terminal = character.allowance.kind is CharacterAllowanceKindV1.TERMINAL
        allowed = (self.eos_token_id,) if terminal else self._project_state(character.prefix.state)
        character_receipt = _canonical_json_bytes(character.receipt)
        receipt = Phase2TokenProjectionReceiptV1(
            schema_name=RECEIPT_SCHEMA_NAME,
            schema_version=RECEIPT_SCHEMA_VERSION,
            audit_lane=self.controller.lane.value,
            tokenizer_identity=self.tokenizer_identity,
            decoder_identity=self.decoder_identity,
            grammar_identity=self.controller.grammar_identity,
            request_context_identity=self.controller.request_context_identity,
            exclusion_policy_identity=self.exclusion_policy_identity,
            character_receipt_sha256=hashlib.sha256(character_receipt).hexdigest(),
            decoded_prefix_sha256=character.prefix.decoded_sha256,
            strategy_class="CONTEXT_FREE_COMPLETE_TOKEN_PIECE_TRIE_V1",
            allowed_token_set_sha256=_token_set_hash(allowed),
            allowed_token_count=len(allowed),
            eos_disposition="ALLOWED_TERMINAL_ONLY" if terminal else "REJECTED_NONTERMINAL",
            liveness=("TOKENIZATION_TERMINAL_EOS_ALLOWED" if terminal else
                      "TOKENIZATION_CONTINUABLE" if allowed else
                      "TOKENIZATION_DEAD_NO_VALID_TOKEN"),
            reason_code=None if allowed else "PHASE2_TOKEN_ALLOWED_SET_EMPTY",
        )
        if not allowed:
            raise Phase2TokenProjectionLivenessErrorV1(receipt)
        return Phase2TokenProjectionResultV1(allowed, receipt)

    def allowed_token_ids(self, token_ids, decode) -> tuple[int, ...]:
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
                except StagePConstraintViolationV1:
                    continue
                stack.append((child, advanced))
        return tuple(sorted(allowed))


def _token_set_hash(token_ids: Sequence[int]) -> str:
    return hashlib.sha256(",".join(map(str, token_ids)).encode()).hexdigest()


def _json_value(value):
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {name: _json_value(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


def _canonical_json_bytes(value) -> bytes:
    return (json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def canonical_phase2_token_projection_receipt_bytes_v1(
    receipt: Phase2TokenProjectionReceiptV1,
) -> bytes:
    return _canonical_json_bytes(receipt)


__all__ = (
    "Phase2TokenProjectionLivenessErrorV1", "Phase2TokenProjectionReceiptV1",
    "Phase2TokenProjectionResultV1", "Phase2TokenProjectorV1",
    "canonical_phase2_token_projection_receipt_bytes_v1",
)
