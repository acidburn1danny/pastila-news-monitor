"""Evaluation-only character constraint for the Stage P proposition ledger."""
from __future__ import annotations

from dataclasses import dataclass, replace


class StagePConstraintViolationV1(ValueError):
    pass


ENTRY_TYPES = ("REAL_WORLD_COMMITMENT", "CONTAINED_CREATIVE", "UNRESOLVED_SCOPE")
SCOPE_BASES = ("ASSERTED", "PRESUPPOSED", "ENTAILED", "NECESSARILY_IMPLIED", "CREATIVE_CONTAINED", "UNRESOLVED")
EVENT_ALIGNMENTS = ("GOVERNED_EVENT", "NEW_UNSUPPORTED_EVENT", "CREATIVE_VEHICLE_ONLY", "UNRESOLVED")
MODALITIES = ("NOT_APPLICABLE", "POSSIBLE", "CONDITIONAL", "PROPOSED", "EXPECTED", "CERTAIN_OR_ACTUAL", "UNRESOLVED")
TIMINGS = ("NOT_APPLICABLE", "PAST", "PRESENT", "ONGOING", "FUTURE", "COMPLETED", "UNDATED", "UNRESOLVED")


@dataclass(frozen=True)
class StagePConstraintStateV1:
    mode: str = "LITERAL"
    remaining: str = '{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"'
    next_step: str = "COVERAGE"
    buffer: str = ""
    choices: tuple[str, ...] = ()
    coverage: str | None = None
    entry_count: int = 0
    unresolved_seen: bool = False
    string_escape: bool = False
    unicode_remaining: int = 0
    string_characters: int = 0
    receipt_whole: bool | None = None
    receipt_embedded: bool | None = None
    receipt_creative: bool | None = None
    receipt_unresolved: bool | None = None
    terminal: bool = False
    characters: int = 0

    @property
    def can_eos(self) -> bool:
        return self.terminal

    def feed(self, text: str) -> "StagePConstraintStateV1":
        state = self
        for char in text:
            state = state._feed_char(char)
        return state

    def _feed_char(self, char: str) -> "StagePConstraintStateV1":
        if self.terminal:
            raise StagePConstraintViolationV1("TRAILING_BYTES")
        if self.characters >= 16000:
            raise StagePConstraintViolationV1("CHARACTER_LIMIT")
        state = replace(self, characters=self.characters + 1)
        if state.mode == "LITERAL":
            if not state.remaining or char != state.remaining[0]:
                raise StagePConstraintViolationV1("LITERAL_MISMATCH")
            remaining = state.remaining[1:]
            state = replace(state, remaining=remaining)
            return state._advance(state.next_step) if not remaining else state
        if state.mode == "CHOICE":
            candidate = state.buffer + char
            viable = tuple(item for item in state.choices if item.startswith(candidate))
            if not viable:
                raise StagePConstraintViolationV1("ENUM_MISMATCH")
            state = replace(state, buffer=candidate, choices=viable)
            if len(viable) == 1 and candidate == viable[0]:
                return state._advance(state.next_step, candidate)
            return state
        if state.mode == "STRING_START":
            if char != '"':
                raise StagePConstraintViolationV1("STRING_START")
            return replace(state, mode="STRING", string_characters=0, string_escape=False, unicode_remaining=0)
        if state.mode == "NULLABLE_STRING_START":
            if char == "n":
                return replace(state, mode="LITERAL", remaining="ull", next_step=state.next_step)
            if char == '"':
                return replace(state, mode="STRING", string_characters=0, string_escape=False, unicode_remaining=0)
            raise StagePConstraintViolationV1("NULLABLE_STRING_START")
        if state.mode == "STRING":
            if state.unicode_remaining:
                if char not in "0123456789abcdefABCDEF":
                    raise StagePConstraintViolationV1("UNICODE_ESCAPE")
                left = state.unicode_remaining - 1
                return replace(state, unicode_remaining=left, string_characters=state.string_characters + (1 if left == 0 else 0))
            if state.string_escape:
                if char == "u":
                    return replace(state, string_escape=False, unicode_remaining=4)
                if char not in '"\\/bfnrt':
                    raise StagePConstraintViolationV1("JSON_ESCAPE")
                return replace(state, string_escape=False, string_characters=state.string_characters + 1)
            if char == "\\":
                return replace(state, string_escape=True)
            if char == '"':
                if state.string_characters == 0:
                    raise StagePConstraintViolationV1("EMPTY_REQUIRED_STRING")
                return state._advance(state.next_step)
            if ord(char) < 0x20:
                raise StagePConstraintViolationV1("UNESCAPED_CONTROL")
            return replace(state, string_characters=state.string_characters + 1)
        if state.mode == "AFTER_ENTRY":
            if char == ",":
                if state.entry_count >= 8:
                    raise StagePConstraintViolationV1("ENTRY_LIMIT")
                return state._entry_start()
            if char == "]":
                return replace(state, mode="LITERAL", remaining=',"coverage_receipt":{"candidate_reviewed_as_whole":', next_step="WHOLE")
            raise StagePConstraintViolationV1("ENTRY_SEPARATOR")
        raise StagePConstraintViolationV1("UNKNOWN_STATE")

    def _advance(self, step: str, value: str | None = None) -> "StagePConstraintStateV1":
        if step == "COVERAGE":
            return replace(self, mode="CHOICE", buffer="", choices=("COMPLETE", "INDETERMINATE"), next_step="AFTER_COVERAGE")
        if step == "AFTER_COVERAGE":
            return replace(self, coverage=value, mode="LITERAL", remaining='","entries":[', next_step="ENTRY_START")
        if step == "ENTRY_START":
            return self._entry_start()
        if step == "ENTRY_ID":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f"P{i}" for i in range(1, 9)), next_step="ENTRY_TYPE_LITERAL")
        if step == "ENTRY_TYPE_LITERAL":
            return replace(self, mode="LITERAL", remaining='","entry_type":"', next_step="ENTRY_TYPE")
        if step == "ENTRY_TYPE":
            return replace(self, mode="CHOICE", buffer="", choices=ENTRY_TYPES, next_step="CANDIDATE_LITERAL")
        if step == "CANDIDATE_LITERAL":
            return replace(self, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED_SCOPE", mode="LITERAL", remaining='","candidate_span":', next_step="CANDIDATE")
        if step == "CANDIDATE":
            return replace(self, mode="STRING_START", next_step="AUTHORITY_LITERAL")
        if step == "AUTHORITY_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"authority_support":', next_step="AUTHORITY")
        if step == "AUTHORITY":
            return replace(self, mode="NULLABLE_STRING_START", next_step="COMMITMENT_LITERAL")
        if step == "COMMITMENT_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"commitment":', next_step="COMMITMENT")
        if step == "COMMITMENT":
            return replace(self, mode="STRING_START", next_step="SCOPE_LITERAL")
        if step == "SCOPE_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"scope_basis":"', next_step="SCOPE")
        if step == "SCOPE":
            return replace(self, mode="CHOICE", buffer="", choices=SCOPE_BASES, next_step="EVENT_LITERAL")
        if step == "EVENT_LITERAL":
            return replace(self, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED", mode="LITERAL", remaining='","event_alignment":"', next_step="EVENT")
        if step == "EVENT":
            return replace(self, mode="CHOICE", buffer="", choices=EVENT_ALIGNMENTS, next_step="AUTH_MODALITY_LITERAL")
        if step == "AUTH_MODALITY_LITERAL":
            return self._enum_literal(value, '","authority_modality":"', "AUTH_MODALITY")
        if step == "AUTH_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=MODALITIES, next_step="CAND_MODALITY_LITERAL")
        if step == "CAND_MODALITY_LITERAL":
            return self._enum_literal(value, '","candidate_modality":"', "CAND_MODALITY")
        if step == "CAND_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=MODALITIES, next_step="AUTH_TIMING_LITERAL")
        if step == "AUTH_TIMING_LITERAL":
            return self._enum_literal(value, '","authority_timing":"', "AUTH_TIMING")
        if step == "AUTH_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=TIMINGS, next_step="CAND_TIMING_LITERAL")
        if step == "CAND_TIMING_LITERAL":
            return self._enum_literal(value, '","candidate_timing":"', "CAND_TIMING")
        if step == "CAND_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=TIMINGS, next_step="GROUP_LITERAL")
        if step == "GROUP_LITERAL":
            return self._enum_literal(value, '","independence_group":"', "GROUP")
        if step == "GROUP":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f"G{i}" for i in range(1, 9)), next_step="ENTRY_END")
        if step == "ENTRY_END":
            return replace(self, mode="LITERAL", remaining='"}', next_step="AFTER_ENTRY")
        if step == "AFTER_ENTRY":
            return replace(self, mode="AFTER_ENTRY")
        if step in {"WHOLE", "EMBEDDED", "CREATIVE", "RECEIPT_UNRESOLVED"}:
            return replace(self, mode="CHOICE", buffer="", choices=("false", "true"), next_step=f"AFTER_{step}")
        if step == "AFTER_WHOLE":
            return replace(self, receipt_whole=value == "true", mode="LITERAL", remaining=',"embedded_propositions_checked":', next_step="EMBEDDED")
        if step == "AFTER_EMBEDDED":
            return replace(self, receipt_embedded=value == "true", mode="LITERAL", remaining=',"creative_scope_checked":', next_step="CREATIVE")
        if step == "AFTER_CREATIVE":
            return replace(self, receipt_creative=value == "true", mode="LITERAL", remaining=',"unresolved_scope_present":', next_step="RECEIPT_UNRESOLVED")
        if step == "AFTER_RECEIPT_UNRESOLVED":
            return replace(self, receipt_unresolved=value == "true", mode="LITERAL", remaining="}}", next_step="TERMINAL")
        if step == "TERMINAL":
            if self.entry_count < 1:
                raise StagePConstraintViolationV1("EMPTY_ENTRIES")
            if self.coverage == "COMPLETE" and (
                self.unresolved_seen or self.receipt_unresolved
                or not self.receipt_whole or not self.receipt_embedded or not self.receipt_creative
            ):
                raise StagePConstraintViolationV1("INVALID_COMPLETE_INVARIANTS")
            return replace(self, mode="TERMINAL", terminal=True, remaining="")
        raise StagePConstraintViolationV1("UNKNOWN_ADVANCE")

    def _entry_start(self) -> "StagePConstraintStateV1":
        return replace(self, entry_count=self.entry_count + 1, mode="LITERAL", remaining='{"entry_id":"', next_step="ENTRY_ID")

    def _enum_literal(self, value: str | None, literal: str, next_step: str) -> "StagePConstraintStateV1":
        return replace(self, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED", mode="LITERAL", remaining=literal, next_step=next_step)


__all__ = ("StagePConstraintStateV1", "StagePConstraintViolationV1")
