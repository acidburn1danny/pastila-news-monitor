"""Evaluation-only streaming grammar for governed Gate-F JSON responses."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Iterable, Sequence

GATE_F_CODES = (
    "FSEM_CERTAINTY_MUTATION", "FSEM_FICTION_RETURN_TO_FACT",
    "FSEM_INVENTED_SPEECH_OR_ROLE_KNOWLEDGE", "FSEM_TIMING_MUTATION",
    "FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY", "FSEM_UNSUPPORTED_CAPACITY",
    "FSEM_UNSUPPORTED_CAUSALITY", "FSEM_UNSUPPORTED_EMOTION_OR_REACTION",
    "FSEM_UNSUPPORTED_LIFE_STAKES", "FSEM_UNSUPPORTED_MOTIVE_OR_INTENT",
    "FSEM_UNSUPPORTED_OUTCOME_OR_STATUS", "FSEM_UNSUPPORTED_PREMISE_TO_DIRECTIVE",
    "ADMISSION_INDETERMINATE",
)
STATUSES = ("DECISIVE", "SUPPORTING", "DEFENSE_IN_DEPTH_ONLY")
DECISIONS = ("PASS", "FAIL", "INDETERMINATE")


class ConstraintViolation(ValueError):
    pass


@dataclass(frozen=True)
class GateFConstraintStateV1:
    mode: str = "LITERAL"
    remaining: str = '{"gate_id":"FACTUAL_SEMANTIC","decision":"'
    buffer: str = ""
    choices: tuple[str, ...] = ()
    next_step: str = "DECISION"
    decision: str | None = None
    record_count: int = 0
    decisive_seen: bool = False
    current_status: str | None = None
    string_escape: bool = False
    unicode_remaining: int = 0
    number_dot: bool = False
    number_fraction_digits: int = 0
    terminal: bool = False
    characters: int = 0

    def feed(self, text: str) -> "GateFConstraintStateV1":
        state = self
        for char in text:
            state = state._feed_char(char)
        return state

    @property
    def can_eos(self) -> bool:
        return self.terminal

    def _feed_char(self, char: str) -> "GateFConstraintStateV1":
        if self.terminal:
            raise ConstraintViolation("TRAILING_BYTES")
        if self.characters >= 8000:
            raise ConstraintViolation("CHARACTER_LIMIT")
        state = replace(self, characters=self.characters + 1)
        if state.mode == "LITERAL":
            if not state.remaining or char != state.remaining[0]:
                raise ConstraintViolation("LITERAL_MISMATCH")
            remaining = state.remaining[1:]
            state = replace(state, remaining=remaining)
            return state._advance(state.next_step) if not remaining else state
        if state.mode == "CHOICE":
            candidate = state.buffer + char
            viable = tuple(item for item in state.choices if item.startswith(candidate))
            if not viable:
                raise ConstraintViolation("ENUM_MISMATCH")
            state = replace(state, buffer=candidate, choices=viable)
            if len(viable) == 1 and candidate == viable[0]:
                return state._advance(state.next_step, candidate)
            return state
        if state.mode == "VALUE_START":
            if char == "n":
                return replace(state, mode="LITERAL", remaining="ull", next_step=state.next_step)
            if char == '"':
                return replace(state, mode="STRING", buffer="", string_escape=False, unicode_remaining=0)
            raise ConstraintViolation("NULLABLE_STRING_START")
        if state.mode == "STRING":
            if state.unicode_remaining:
                if char not in "0123456789abcdefABCDEF":
                    raise ConstraintViolation("UNICODE_ESCAPE")
                remaining = state.unicode_remaining - 1
                return replace(state, unicode_remaining=remaining, string_escape=False if remaining == 0 else state.string_escape)
            if state.string_escape:
                if char == "u":
                    return replace(state, unicode_remaining=4)
                if char not in '"\\/bfnrt':
                    raise ConstraintViolation("JSON_ESCAPE")
                return replace(state, string_escape=False)
            if char == "\\":
                return replace(state, string_escape=True)
            if char == '"':
                return state._advance(state.next_step)
            if ord(char) < 0x20:
                raise ConstraintViolation("UNESCAPED_CONTROL")
            return state
        if state.mode == "NUMBER_START":
            if char not in "01":
                raise ConstraintViolation("CONFIDENCE_RANGE")
            return replace(state, mode="NUMBER", buffer=char)
        if state.mode == "NUMBER":
            if char == "." and not state.number_dot:
                return replace(state, number_dot=True)
            if char.isdigit() and state.number_dot:
                if state.buffer == "1" and char != "0":
                    raise ConstraintViolation("CONFIDENCE_RANGE")
                return replace(state, number_fraction_digits=state.number_fraction_digits + 1)
            if char == "}" and (not state.number_dot or state.number_fraction_digits > 0):
                return state._after_record()
            raise ConstraintViolation("CONFIDENCE_FORMAT")
        if state.mode == "AFTER_RECORD":
            if char == ",":
                if state.record_count >= 8:
                    raise ConstraintViolation("RECORD_LIMIT")
                return state._record_start()
            if char == "]":
                return replace(state, mode="LITERAL", remaining="}", next_step="TERMINAL")
            raise ConstraintViolation("RECORD_SEPARATOR")
        raise ConstraintViolation("UNKNOWN_STATE")

    def _advance(self, step: str, value: str | None = None) -> "GateFConstraintStateV1":
        if step == "DECISION":
            return replace(self, mode="CHOICE", buffer="", choices=DECISIONS, next_step="AFTER_DECISION")
        if step == "AFTER_DECISION":
            decision = value
            suffix = '","reason_records":[]}' if decision == "PASS" else '","reason_records":['
            return replace(self, decision=decision, mode="LITERAL", remaining=suffix, next_step="TERMINAL" if decision == "PASS" else "RECORD_START")
        if step == "RECORD_START":
            return self._record_start()
        if step == "CODE":
            return replace(self, mode="CHOICE", buffer="", choices=GATE_F_CODES, next_step="AFTER_CODE")
        if step == "AFTER_CODE":
            return replace(self, mode="LITERAL", remaining='","status":"', next_step="STATUS")
        if step == "STATUS":
            return replace(self, mode="CHOICE", buffer="", choices=STATUSES, next_step="AFTER_STATUS")
        if step == "AFTER_STATUS":
            return replace(self, current_status=value, mode="LITERAL", remaining='","candidate_span":', next_step="CANDIDATE")
        if step == "CANDIDATE":
            return replace(self, mode="VALUE_START", next_step="AUTHORITY_LITERAL")
        if step == "AUTHORITY_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"authority_support":', next_step="AUTHORITY")
        if step == "AUTHORITY":
            return replace(self, mode="VALUE_START", next_step="PROPOSITION_LITERAL")
        if step == "PROPOSITION_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"unsupported_proposition":', next_step="PROPOSITION")
        if step == "PROPOSITION":
            return replace(self, mode="VALUE_START", next_step="CONFIDENCE_LITERAL")
        if step == "CONFIDENCE_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"confidence":', next_step="CONFIDENCE")
        if step == "CONFIDENCE":
            return replace(self, mode="NUMBER_START", buffer="", number_dot=False, number_fraction_digits=0)
        if step == "TERMINAL":
            if self.decision != "PASS" and not self.decisive_seen:
                raise ConstraintViolation("NONPASS_WITHOUT_DECISIVE_REASON")
            return replace(self, mode="TERMINAL", terminal=True, remaining="")
        raise ConstraintViolation("UNKNOWN_ADVANCE")

    def _record_start(self) -> "GateFConstraintStateV1":
        return replace(self, record_count=self.record_count + 1, current_status=None, mode="LITERAL", remaining='{"code":"', next_step="CODE")

    def _after_record(self) -> "GateFConstraintStateV1":
        decisive = self.decisive_seen or self.current_status == "DECISIVE"
        return replace(self, decisive_seen=decisive, mode="AFTER_RECORD", buffer="", number_dot=False, number_fraction_digits=0)


class GateFTokenProjectorV1:
    """Project a character DFA onto tokenizer IDs using full-prefix decoding."""

    def __init__(self, *, vocabulary_ids: Iterable[int], eos_token_id: int, decode: Callable[[Sequence[int]], str]) -> None:
        self._vocabulary = tuple(vocabulary_ids)
        self._eos = eos_token_id
        self._decode = decode

    def allowed_token_ids(self, prefix_ids: Sequence[int], state: GateFConstraintStateV1) -> tuple[int, ...]:
        if state.can_eos:
            return (self._eos,)
        baseline = self._decode(prefix_ids)
        allowed: list[int] = []
        for token_id in self._vocabulary:
            if token_id == self._eos:
                continue
            combined = self._decode((*prefix_ids, token_id))
            if not combined.startswith(baseline):
                continue
            extension = combined[len(baseline):]
            if not extension:
                continue
            try:
                state.feed(extension)
            except ConstraintViolation:
                continue
            allowed.append(token_id)
        if not allowed:
            raise ConstraintViolation("EMPTY_ALLOWED_TOKEN_SET")
        return tuple(allowed)


__all__ = ("ConstraintViolation", "GateFConstraintStateV1", "GateFTokenProjectorV1")
