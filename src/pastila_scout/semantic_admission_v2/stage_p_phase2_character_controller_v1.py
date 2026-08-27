"""Zero-inference character controllers and liveness receipts for Phase 2 audits."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from .stage_p_constraint_v1 import StagePConstraintViolationV1
from .stage_p_phase2_character_dfa_v1 import (
    AuthorityReconciliationCharacterDfaV1,
    CommitmentSpanAuditCharacterDfaV1,
    Phase2IncrementalCharacterTrackerV1,
    Phase2PrefixResultV1,
)
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-phase2-character-liveness-receipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation-candidate.1"
COMMITMENT_DFA_IDENTITY = "2a214b08788ca4fc9f868ef9b3ef5fe1debecd8b79a08692c859fe0de79d64ce"
AUTHORITY_DFA_IDENTITY = "9fb7ba85fe422f89f80640865ad823b325e9a4026f543f03555e84bf0a69e4de"


class Phase2AuditLaneV1(StrEnum):
    COMMITMENT_SPAN = "COMMITMENT_SPAN"
    AUTHORITY_RECONCILIATION = "AUTHORITY_RECONCILIATION"


class CharacterAllowanceKindV1(StrEnum):
    FINITE = "FINITE"
    JSON_STRING_BODY = "JSON_STRING_BODY"
    TERMINAL = "TERMINAL"


@dataclass(frozen=True, slots=True)
class CharacterAllowanceV1:
    kind: CharacterAllowanceKindV1
    finite_characters: tuple[str, ...] = ()
    closing_quote_allowed: bool = False
    backslash_escape_allowed: bool = False
    unescaped_scalar_minimum: int | None = None

    def permits(self, character: str) -> bool:
        if len(character) != 1 or self.kind is CharacterAllowanceKindV1.TERMINAL:
            return False
        if self.kind is CharacterAllowanceKindV1.FINITE:
            return character in self.finite_characters
        if character == '"':
            return self.closing_quote_allowed
        if character == "\\":
            return self.backslash_escape_allowed
        codepoint = ord(character)
        return codepoint >= (self.unescaped_scalar_minimum or 0) and not 0xD800 <= codepoint <= 0xDFFF


@dataclass(frozen=True, slots=True)
class Phase2CharacterLivenessReceiptV1:
    schema_name: str
    schema_version: str
    audit_lane: Phase2AuditLaneV1
    grammar_identity: str
    request_context_identity: str
    decoder_identity: str
    decoded_sha256: str
    decoded_utf8_bytes: int
    decoded_characters: int
    token_count: int
    tracker_path: str
    suffix_characters: int
    dfa_mode: str
    record_index: int
    reference_field: str | None
    reference_mode: str | None
    allowance_kind: CharacterAllowanceKindV1
    finite_character_count: int
    liveness: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class Phase2CharacterControllerResultV1:
    prefix: Phase2PrefixResultV1
    allowance: CharacterAllowanceV1
    receipt: Phase2CharacterLivenessReceiptV1


class Phase2CharacterLivenessErrorV1(RuntimeError):
    def __init__(self, receipt: Phase2CharacterLivenessReceiptV1) -> None:
        super().__init__(receipt.reason_code or "PHASE2_CHARACTER_LIVENESS_FAILURE")
        self.receipt = receipt


class Phase2CharacterControllerV1:
    def __init__(
        self,
        *,
        lane: Phase2AuditLaneV1,
        expected_entry_ids: tuple[str, ...],
        decoder_identity: str,
        source_context: SourceReferenceConstraintContextV1 | None = None,
    ) -> None:
        if not _is_sha256(decoder_identity):
            raise ValueError("PHASE2_DECODER_IDENTITY_INVALID")
        if lane is Phase2AuditLaneV1.COMMITMENT_SPAN:
            if source_context is not None:
                raise ValueError("PHASE2_COMMITMENT_SOURCE_CONTEXT_FORBIDDEN")
            grammar_identity = COMMITMENT_DFA_IDENTITY
            factory: Callable[[], object] = lambda: CommitmentSpanAuditCharacterDfaV1.for_entries(
                expected_entry_ids
            )
            source_identity = "NO_SOURCE_CONTEXT"
        elif lane is Phase2AuditLaneV1.AUTHORITY_RECONCILIATION:
            if source_context is None:
                raise ValueError("PHASE2_AUTHORITY_SOURCE_CONTEXT_REQUIRED")
            grammar_identity = AUTHORITY_DFA_IDENTITY
            factory = lambda: AuthorityReconciliationCharacterDfaV1.for_request(
                entry_ids=expected_entry_ids, context=source_context
            )
            source_identity = source_context.binding_identity
        else:
            raise ValueError("PHASE2_AUDIT_LANE_INVALID")
        self.lane = lane
        self.expected_entry_ids = expected_entry_ids
        self.decoder_identity = decoder_identity
        self.grammar_identity = grammar_identity
        self.request_context_identity = hashlib.sha256(
            "\n".join((lane.value, grammar_identity, ",".join(expected_entry_ids), source_identity)).encode()
        ).hexdigest()
        self.tracker = Phase2IncrementalCharacterTrackerV1(factory)

    def allowed(self, token_ids, decode) -> Phase2CharacterControllerResultV1:
        prefix = self.tracker.state_for(token_ids, decode)
        allowance = _allowance_for_state(prefix.state)
        live = allowance.kind in {
            CharacterAllowanceKindV1.JSON_STRING_BODY,
            CharacterAllowanceKindV1.TERMINAL,
        } or bool(allowance.finite_characters)
        receipt = self._receipt(prefix, allowance, live)
        if not live:
            raise Phase2CharacterLivenessErrorV1(receipt)
        return Phase2CharacterControllerResultV1(prefix, allowance, receipt)

    def _receipt(self, prefix, allowance, live):
        state = prefix.state
        reference = getattr(state, "reference_state", None)
        return Phase2CharacterLivenessReceiptV1(
            schema_name=RECEIPT_SCHEMA_NAME,
            schema_version=RECEIPT_SCHEMA_VERSION,
            audit_lane=self.lane,
            grammar_identity=self.grammar_identity,
            request_context_identity=self.request_context_identity,
            decoder_identity=self.decoder_identity,
            decoded_sha256=prefix.decoded_sha256,
            decoded_utf8_bytes=len(prefix.decoded.encode("utf-8")),
            decoded_characters=len(prefix.decoded),
            token_count=len(prefix.token_ids),
            tracker_path=prefix.path,
            suffix_characters=prefix.suffix_characters,
            dfa_mode=state.mode,
            record_index=state.record_index,
            reference_field=reference.field.value if reference else None,
            reference_mode=reference.mode.value if reference else None,
            allowance_kind=allowance.kind,
            finite_character_count=len(allowance.finite_characters),
            liveness="LIVE" if live else "FAIL_CLOSED",
            reason_code=None if live else "PHASE2_CHARACTER_ALLOWED_SET_EMPTY",
        )


def _accepts_character(state, character: str) -> bool:
    try:
        state._feed_char(character)
    except StagePConstraintViolationV1:
        return False
    return True


def _finite(state, candidates) -> CharacterAllowanceV1:
    accepted = tuple(sorted({item for item in candidates if _accepts_character(state, item)}))
    return CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE, accepted)


def _allowance_for_state(state) -> CharacterAllowanceV1:
    if state.terminal:
        return CharacterAllowanceV1(CharacterAllowanceKindV1.TERMINAL)
    if state.characters >= state.character_limit:
        return CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE)
    if state.mode == "LITERAL":
        return _finite(state, state.remaining[:1])
    if state.mode == "CHOICE":
        offset = len(state.buffer)
        return _finite(state, (
            choice[offset] for choice in state.choices
            if choice.startswith(state.buffer) and len(choice) > offset
        ))
    if state.mode == "STRING_START":
        return _finite(state, ('"',))
    if state.mode == "STRING":
        if state.unicode_remaining:
            return _finite(state, "0123456789ABCDEFabcdef")
        if state.string_escape:
            return _finite(state, '"\\/bfnrtu')
        if state.string_characters >= 500:
            return _finite(state, ('"',))
        return CharacterAllowanceV1(
            CharacterAllowanceKindV1.JSON_STRING_BODY,
            closing_quote_allowed=state.string_characters > 0,
            backslash_escape_allowed=True,
            unescaped_scalar_minimum=0x20,
        )
    if state.mode == "REFERENCE":
        reference = state.reference_state
        return (_finite(state, reference.allowed_next_characters()) if reference else
                CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE))
    if state.mode == "FINDING_LINK_SEPARATOR":
        return _finite(state, (",", "]"))
    return CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE)


def phase2_liveness_receipt_json_value_v1(receipt: Phase2CharacterLivenessReceiptV1):
    return {
        "schema_name": receipt.schema_name,
        "schema_version": receipt.schema_version,
        "audit_lane": receipt.audit_lane.value,
        "grammar_identity": receipt.grammar_identity,
        "request_context_identity": receipt.request_context_identity,
        "decoder_identity": receipt.decoder_identity,
        "decoded_sha256": receipt.decoded_sha256,
        "decoded_utf8_bytes": receipt.decoded_utf8_bytes,
        "decoded_characters": receipt.decoded_characters,
        "token_count": receipt.token_count,
        "tracker_path": receipt.tracker_path,
        "suffix_characters": receipt.suffix_characters,
        "dfa_mode": receipt.dfa_mode,
        "record_index": receipt.record_index,
        "reference_field": receipt.reference_field,
        "reference_mode": receipt.reference_mode,
        "allowance_kind": receipt.allowance_kind.value,
        "finite_character_count": receipt.finite_character_count,
        "liveness": receipt.liveness,
        "reason_code": receipt.reason_code,
    }


def canonical_phase2_liveness_receipt_bytes_v1(receipt: Phase2CharacterLivenessReceiptV1) -> bytes:
    return (json.dumps(phase2_liveness_receipt_json_value_v1(receipt), ensure_ascii=False,
                       sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _is_sha256(value: str) -> bool:
    return type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


__all__ = (
    "CharacterAllowanceKindV1", "CharacterAllowanceV1", "Phase2AuditLaneV1",
    "Phase2CharacterControllerResultV1", "Phase2CharacterControllerV1",
    "Phase2CharacterLivenessErrorV1", "Phase2CharacterLivenessReceiptV1",
    "canonical_phase2_liveness_receipt_bytes_v1", "phase2_liveness_receipt_json_value_v1",
)
