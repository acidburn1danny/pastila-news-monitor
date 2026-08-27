"""Identity-bound, context-free token projection for the request-bound V2 DFA."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .stage_p_construction_obligation_character_controller_v1 import (
    CharacterAllowanceKindV1,
    StagePCharacterLivenessErrorV1,
    StagePConstructionObligationCharacterControllerV1,
)
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1


RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-token-projection-receipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class TokenProjectionReceiptV1:
    schema_name: str
    schema_version: str
    request_context_identity: str
    tokenizer_identity: str
    decoder_identity: str
    decoded_sha256: str
    dfa_mode: str
    terminal: bool
    legal_token_count: int
    eos_allowed: bool
    result: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class TokenProjectionResultV1:
    token_ids: tuple[int, ...]
    receipt: TokenProjectionReceiptV1


class StagePTokenProjectionFailureV1(RuntimeError):
    def __init__(self, receipt: TokenProjectionReceiptV1):
        super().__init__(receipt.reason_code or "STAGE_P_TOKEN_PROJECTION_FAILURE")
        self.receipt = receipt


class StagePConstructionObligationV2TokenProjectorV1:
    """Project context-free decoded token pieces without loading a tokenizer."""

    def __init__(
        self, *, controller: StagePConstructionObligationCharacterControllerV1,
        token_pieces: Mapping[int, str], eos_token_id: int,
        tokenizer_identity: str, decoder_identity: str,
        request_context_identity: str, excluded_token_ids: Sequence[int] = (),
    ) -> None:
        bound_context = controller.tracker.context.binding_identity
        if not tokenizer_identity:
            raise ValueError("TOKENIZER_IDENTITY_REQUIRED")
        if not decoder_identity or decoder_identity != controller.tracker.decoder_identity:
            raise ValueError("DECODER_IDENTITY_MISMATCH")
        if request_context_identity != bound_context:
            raise ValueError("REQUEST_CONTEXT_IDENTITY_MISMATCH")
        if eos_token_id in token_pieces and token_pieces[eos_token_id]:
            raise ValueError("EOS_MUST_NOT_HAVE_ORDINARY_DECODED_PIECE")
        pieces: dict[int, str] = {}
        for token_id, piece in token_pieces.items():
            if type(token_id) is not int or type(piece) is not str:
                raise ValueError("MALFORMED_TOKEN_PIECE")
            pieces[token_id] = piece
        self.controller = controller
        self.token_pieces = pieces
        self.eos_token_id = eos_token_id
        self.tokenizer_identity = tokenizer_identity
        self.decoder_identity = decoder_identity
        self.request_context_identity = request_context_identity
        self.excluded_token_ids = frozenset(excluded_token_ids) | {eos_token_id}
        self._cache: dict[tuple[str, str, str, str, str], tuple[int, ...]] = {}

    def allowed_token_ids(
        self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str],
    ) -> TokenProjectionResultV1:
        try:
            character = self.controller.allowed(token_ids, decode)
        except (StagePCharacterLivenessErrorV1, StagePRoleCoherenceConstraintViolationV1,
                UnicodeError, ValueError, TypeError) as exc:
            receipt = self._failure_receipt("UNBOUND_OR_INVALID_CHARACTER_PREFIX", exc)
            raise StagePTokenProjectionFailureV1(receipt) from exc
        prefix = character.prefix
        if prefix.context_identity != self.request_context_identity:
            raise StagePTokenProjectionFailureV1(
                self._receipt(prefix, (), False, "CONTEXT_IDENTITY_DRIFT"))
        if prefix.decoder_identity != self.decoder_identity:
            raise StagePTokenProjectionFailureV1(
                self._receipt(prefix, (), False, "DECODER_IDENTITY_DRIFT"))
        if character.allowance.kind is CharacterAllowanceKindV1.TERMINAL:
            allowed = (self.eos_token_id,)
        else:
            state_fingerprint = hashlib.sha256(repr(prefix.state).encode()).hexdigest()
            key = (self.request_context_identity, self.tokenizer_identity,
                   self.decoder_identity, prefix.decoded_sha256, state_fingerprint)
            allowed = self._cache.get(key)
            if allowed is None:
                accepted = []
                for token_id, piece in sorted(self.token_pieces.items()):
                    if token_id in self.excluded_token_ids or not piece:
                        continue
                    if any(0xD800 <= ord(character) <= 0xDFFF for character in piece):
                        continue
                    try:
                        prefix.state.feed(piece)
                    except (StagePRoleCoherenceConstraintViolationV1, UnicodeError,
                            ValueError, TypeError):
                        continue
                    accepted.append(token_id)
                allowed = tuple(accepted)
                self._cache[key] = allowed
        if not allowed:
            raise StagePTokenProjectionFailureV1(
                self._receipt(prefix, (), False, "TOKENIZATION_DEAD_NO_VALID_TOKEN"))
        return TokenProjectionResultV1(
            allowed, self._receipt(prefix, allowed, self.eos_token_id in allowed, None))

    def _receipt(self, prefix, allowed: tuple[int, ...], eos: bool,
                 reason: str | None) -> TokenProjectionReceiptV1:
        return TokenProjectionReceiptV1(
            RECEIPT_SCHEMA_NAME, RECEIPT_SCHEMA_VERSION,
            self.request_context_identity, self.tokenizer_identity,
            self.decoder_identity, prefix.decoded_sha256, prefix.state.mode,
            prefix.state.terminal, len(allowed), eos,
            "FAIL_CLOSED" if reason else ("TOKENIZATION_TERMINAL_EOS_ALLOWED" if eos
                                           else "TOKENIZATION_CONTINUABLE"), reason)

    def _failure_receipt(self, reason: str, exc: BaseException) -> TokenProjectionReceiptV1:
        digest = hashlib.sha256(type(exc).__name__.encode()).hexdigest()
        return TokenProjectionReceiptV1(
            RECEIPT_SCHEMA_NAME, RECEIPT_SCHEMA_VERSION,
            self.request_context_identity, self.tokenizer_identity,
            self.decoder_identity, digest, "INVALID", False, 0, False,
            "FAIL_CLOSED", reason)


def canonical_token_projection_receipt_bytes_v1(receipt: TokenProjectionReceiptV1) -> bytes:
    value = {field: getattr(receipt, field) for field in receipt.__dataclass_fields__}
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "StagePConstructionObligationV2TokenProjectorV1", "StagePTokenProjectionFailureV1",
    "TokenProjectionReceiptV1", "TokenProjectionResultV1",
    "canonical_token_projection_receipt_bytes_v1",
)
