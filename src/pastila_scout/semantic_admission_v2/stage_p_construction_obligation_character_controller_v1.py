"""Character-level controller and liveness receipts for the request-bound V2 DFA."""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from .stage_p_construction_obligation_constraint_v2 import (
    StagePConstructionObligationConstraintStateV2,
)
from .stage_p_construction_obligation_incremental_tracker_v2 import (
    ConstructionObligationPrefixResultV2,
    StagePConstructionObligationIncrementalTrackerV2,
)
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


RECEIPT_SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-character-liveness-receipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-evaluation.1"


class CharacterAllowanceKindV1(StrEnum):
    FINITE = "FINITE"
    JSON_STRING_BODY = "JSON_STRING_BODY"
    TERMINAL = "TERMINAL"


@dataclass(frozen=True, slots=True)
class CharacterAllowanceV1:
    kind: CharacterAllowanceKindV1
    finite_characters: tuple[str, ...] = ()
    unescaped_scalar_minimum: int | None = None
    unescaped_scalar_exclusions: tuple[str, ...] = ()
    backslash_escape_allowed: bool = False
    closing_quote_allowed: bool = False

    def permits(self, character: str) -> bool:
        if len(character) != 1:
            return False
        if self.kind is CharacterAllowanceKindV1.FINITE:
            return character in self.finite_characters
        if self.kind is CharacterAllowanceKindV1.TERMINAL:
            return False
        if character == '"':
            return self.closing_quote_allowed
        if character == "\\":
            return self.backslash_escape_allowed
        codepoint = ord(character)
        return (codepoint >= (self.unescaped_scalar_minimum or 0) and
                not 0xD800 <= codepoint <= 0xDFFF and
                character not in self.unescaped_scalar_exclusions)


@dataclass(frozen=True, slots=True)
class CharacterLivenessReceiptV1:
    schema_name: str
    schema_version: str
    context_identity: str
    decoder_identity: str
    decoded_sha256: str
    decoded_utf8_bytes: int
    decoded_characters: int
    token_count: int
    tracker_path: str
    suffix_characters: int
    dfa_mode: str
    entry_count: int
    construction_count: int
    audit_count: int
    reference_field: str | None
    reference_mode: str | None
    allowance_kind: CharacterAllowanceKindV1
    finite_character_count: int
    liveness: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class CharacterControllerResultV1:
    prefix: ConstructionObligationPrefixResultV2
    allowance: CharacterAllowanceV1
    receipt: CharacterLivenessReceiptV1


class StagePCharacterLivenessErrorV1(RuntimeError):
    def __init__(self, receipt: CharacterLivenessReceiptV1):
        super().__init__(receipt.reason_code or "STAGE_P_CHARACTER_LIVENESS_FAILURE")
        self.receipt = receipt


class StagePConstructionObligationCharacterControllerV1:
    def __init__(self, *, context: SourceReferenceConstraintContextV1,
                 decoder_identity: str) -> None:
        self.tracker = StagePConstructionObligationIncrementalTrackerV2(
            context=context, decoder_identity=decoder_identity)

    def allowed(self, token_ids, decode) -> CharacterControllerResultV1:
        prefix = self.tracker.state_for(token_ids, decode)
        allowance = _allowance_for_state(prefix.state)
        live = (allowance.kind in {CharacterAllowanceKindV1.JSON_STRING_BODY,
                                   CharacterAllowanceKindV1.TERMINAL} or
                bool(allowance.finite_characters))
        receipt = _receipt(prefix, allowance, live=live)
        if not live:
            raise StagePCharacterLivenessErrorV1(receipt)
        return CharacterControllerResultV1(prefix, allowance, receipt)


def _accepts_character(state: StagePConstructionObligationConstraintStateV2,
                       character: str) -> bool:
    try:
        state._feed_char(character)
    except StagePRoleCoherenceConstraintViolationV1:
        return False
    return True


def _finite(state, candidates) -> CharacterAllowanceV1:
    accepted = tuple(sorted({character for character in candidates
                             if _accepts_character(state, character)}))
    return CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE, accepted)


def _allowance_for_state(state: StagePConstructionObligationConstraintStateV2) -> CharacterAllowanceV1:
    if state.terminal:
        return CharacterAllowanceV1(CharacterAllowanceKindV1.TERMINAL)
    if state.mode == "LITERAL":
        return _finite(state, state.remaining[:1])
    if state.mode == "CHOICE":
        offset = len(state.buffer)
        return _finite(state, (choice[offset] for choice in state.choices
                               if len(choice) > offset and choice.startswith(state.buffer)))
    if state.mode == "STRING_START":
        return _finite(state, ('"',))
    if state.mode in {"NULLABLE_STRING_START", "CONSTRUCTION_NULLABLE_STRING_START"}:
        return _finite(state, ('"', "n"))
    if state.mode == "STRING":
        if state.unicode_remaining:
            return _finite(state, "0123456789ABCDEFabcdef")
        if state.string_escape:
            return _finite(state, '"\\/bfnrtu')
        return CharacterAllowanceV1(
            CharacterAllowanceKindV1.JSON_STRING_BODY,
            unescaped_scalar_minimum=0x20,
            unescaped_scalar_exclusions=('"', "\\"),
            backslash_escape_allowed=True,
            closing_quote_allowed=state.string_characters > 0,
        )
    if state.mode == "V2_REFERENCE":
        if state.reference_state is None:
            return CharacterAllowanceV1(CharacterAllowanceKindV1.FINITE)
        return _finite(state, state.reference_state.allowed_next_characters())
    candidates = {
        "AFTER_ENTRY": (",", "]"),
        "AFTER_AUDIT": (",", "]"),
        "CONSTRUCTION_RECORD_SEPARATOR": (",", "]"),
        "CONSTRUCTION_LINK_SEPARATOR": (",", "]"),
    }.get(state.mode, ())
    return _finite(state, candidates)


def _receipt(prefix: ConstructionObligationPrefixResultV2,
             allowance: CharacterAllowanceV1, *, live: bool) -> CharacterLivenessReceiptV1:
    state = prefix.state
    reference = state.reference_state
    return CharacterLivenessReceiptV1(
        schema_name=RECEIPT_SCHEMA_NAME, schema_version=RECEIPT_SCHEMA_VERSION,
        context_identity=prefix.context_identity, decoder_identity=prefix.decoder_identity,
        decoded_sha256=prefix.decoded_sha256,
        decoded_utf8_bytes=len(prefix.decoded.encode("utf-8")),
        decoded_characters=len(prefix.decoded), token_count=len(prefix.token_ids),
        tracker_path=prefix.path, suffix_characters=prefix.suffix_characters,
        dfa_mode=state.mode, entry_count=state.entry_count,
        construction_count=state.construction_count, audit_count=state.audit_count,
        reference_field=reference.field.value if reference else None,
        reference_mode=reference.mode.value if reference else None,
        allowance_kind=allowance.kind,
        finite_character_count=len(allowance.finite_characters),
        liveness="LIVE" if live else "FAIL_CLOSED",
        reason_code=None if live else "STAGE_P_CHARACTER_ALLOWED_SET_EMPTY",
    )


def character_liveness_receipt_json_value_v1(receipt: CharacterLivenessReceiptV1) -> dict[str, object]:
    return {
        "schema_name": receipt.schema_name,
        "schema_version": receipt.schema_version,
        "context_identity": receipt.context_identity,
        "decoder_identity": receipt.decoder_identity,
        "decoded_sha256": receipt.decoded_sha256,
        "decoded_utf8_bytes": receipt.decoded_utf8_bytes,
        "decoded_characters": receipt.decoded_characters,
        "token_count": receipt.token_count,
        "tracker_path": receipt.tracker_path,
        "suffix_characters": receipt.suffix_characters,
        "dfa_mode": receipt.dfa_mode,
        "entry_count": receipt.entry_count,
        "construction_count": receipt.construction_count,
        "audit_count": receipt.audit_count,
        "reference_field": receipt.reference_field,
        "reference_mode": receipt.reference_mode,
        "allowance_kind": receipt.allowance_kind.value,
        "finite_character_count": receipt.finite_character_count,
        "liveness": receipt.liveness,
        "reason_code": receipt.reason_code,
    }


def canonical_character_liveness_receipt_bytes_v1(receipt: CharacterLivenessReceiptV1) -> bytes:
    return (json.dumps(character_liveness_receipt_json_value_v1(receipt),
                       ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


__all__ = (
    "CharacterAllowanceKindV1", "CharacterAllowanceV1", "CharacterControllerResultV1",
    "CharacterLivenessReceiptV1", "StagePCharacterLivenessErrorV1",
    "StagePConstructionObligationCharacterControllerV1",
    "canonical_character_liveness_receipt_bytes_v1",
    "character_liveness_receipt_json_value_v1",
)
