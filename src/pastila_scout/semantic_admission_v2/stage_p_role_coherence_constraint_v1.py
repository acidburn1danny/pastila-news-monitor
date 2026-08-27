"""Evaluation-only character constraint for the role-coherent Stage P ledger."""
from __future__ import annotations

from dataclasses import dataclass, replace


class StagePRoleCoherenceConstraintViolationV1(ValueError):
    pass


ENTRY_TYPES = ("REAL_WORLD_COMMITMENT", "CONTAINED_CREATIVE", "UNRESOLVED_SCOPE")
SCOPE_BASES = ("ASSERTED", "PRESUPPOSED", "ENTAILED", "NECESSARILY_IMPLIED", "CREATIVE_CONTAINED", "UNRESOLVED")
EVENT_ALIGNMENTS = ("GOVERNED_EVENT", "NEW_UNSUPPORTED_EVENT", "CREATIVE_VEHICLE_ONLY", "UNRESOLVED")
MODALITIES = ("NOT_APPLICABLE", "POSSIBLE", "CONDITIONAL", "PROPOSED", "EXPECTED", "CERTAIN_OR_ACTUAL", "UNRESOLVED")
TIMINGS = ("NOT_APPLICABLE", "PAST", "PRESENT", "ONGOING", "FUTURE", "COMPLETED", "UNDATED", "UNRESOLVED")


@dataclass(frozen=True)
class StagePRoleCoherenceConstraintStateV1:
    mode: str = "LITERAL"
    remaining: str = '{"stage_id":"PROPOSITION_LEDGER","entries":['
    next_step: str = "ENTRY_START"
    buffer: str = ""
    choices: tuple[str, ...] = ()
    entry_count: int = 0
    unresolved_seen: bool = False
    string_escape: bool = False
    unicode_remaining: int = 0
    string_characters: int = 0
    receipt_whole: bool | None = None
    receipt_embedded: bool | None = None
    receipt_creative: bool | None = None
    receipt_unresolved: bool | None = None
    coverage: str | None = None
    terminal: bool = False
    characters: int = 0
    current_entry_type: str | None = None
    current_authority_null: bool | None = None
    current_scope: str | None = None
    current_event: str | None = None
    current_authority_modality: str | None = None
    current_candidate_modality: str | None = None
    current_authority_timing: str | None = None
    current_candidate_timing: str | None = None

    @property
    def can_eos(self) -> bool:
        return self.terminal

    def feed(self, text: str) -> "StagePRoleCoherenceConstraintStateV1":
        state = self
        for char in text:
            state = state._feed_char(char)
        return state

    def _fail(self, code: str):
        raise StagePRoleCoherenceConstraintViolationV1(code)

    def _feed_char(self, char: str) -> "StagePRoleCoherenceConstraintStateV1":
        if self.terminal:
            self._fail("TRAILING_BYTES")
        if self.characters >= 16000:
            self._fail("CHARACTER_LIMIT")
        state = replace(self, characters=self.characters + 1)
        if state.mode == "LITERAL":
            if not state.remaining or char != state.remaining[0]:
                state._fail("LITERAL_MISMATCH")
            remaining = state.remaining[1:]
            state = replace(state, remaining=remaining)
            return state._advance(state.next_step) if not remaining else state
        if state.mode == "CHOICE":
            candidate = state.buffer + char
            viable = tuple(item for item in state.choices if item.startswith(candidate))
            if not viable:
                state._fail("ENUM_MISMATCH")
            state = replace(state, buffer=candidate, choices=viable)
            if len(viable) == 1 and candidate == viable[0]:
                return state._advance(state.next_step, candidate)
            return state
        if state.mode == "STRING_START":
            if char != '"':
                state._fail("STRING_START")
            return replace(state, mode="STRING", string_characters=0, string_escape=False, unicode_remaining=0)
        if state.mode == "NULLABLE_STRING_START":
            if char == "n":
                return replace(state, mode="LITERAL", remaining="ull", next_step="AUTHORITY_NULL")
            if char == '"':
                return replace(state, mode="STRING", string_characters=0, string_escape=False, unicode_remaining=0)
            state._fail("NULLABLE_STRING_START")
        if state.mode == "STRING":
            if state.unicode_remaining:
                if char not in "0123456789abcdefABCDEF":
                    state._fail("UNICODE_ESCAPE")
                left = state.unicode_remaining - 1
                return replace(state, unicode_remaining=left, string_characters=state.string_characters + (1 if left == 0 else 0))
            if state.string_escape:
                if char == "u":
                    return replace(state, string_escape=False, unicode_remaining=4)
                if char not in '"\\/bfnrt':
                    state._fail("JSON_ESCAPE")
                return replace(state, string_escape=False, string_characters=state.string_characters + 1)
            if char == "\\":
                return replace(state, string_escape=True)
            if char == '"':
                if state.string_characters == 0:
                    state._fail("EMPTY_REQUIRED_STRING")
                return state._advance(state.next_step)
            if ord(char) < 0x20:
                state._fail("UNESCAPED_CONTROL")
            return replace(state, string_characters=state.string_characters + 1)
        if state.mode == "AFTER_ENTRY":
            if char == ",":
                if state.entry_count >= 8:
                    state._fail("ENTRY_LIMIT")
                return state._entry_start()
            if char == "]":
                return replace(state, mode="LITERAL", remaining=',"coverage_receipt":{"candidate_reviewed_as_whole":', next_step="WHOLE")
            state._fail("ENTRY_SEPARATOR")
        state._fail("UNKNOWN_STATE")

    def _advance(self, step: str, value: str | None = None) -> "StagePRoleCoherenceConstraintStateV1":
        if step == "ENTRY_START":
            return self._entry_start()
        if step == "ENTRY_ID":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f"P{i}" for i in range(1, 9)), next_step="ENTRY_TYPE_LITERAL")
        if step == "ENTRY_TYPE_LITERAL":
            return replace(self, mode="LITERAL", remaining='","entry_type":"', next_step="ENTRY_TYPE")
        if step == "ENTRY_TYPE":
            return replace(self, mode="CHOICE", buffer="", choices=ENTRY_TYPES, next_step="CANDIDATE_LITERAL")
        if step == "CANDIDATE_LITERAL":
            return replace(self, current_entry_type=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED_SCOPE",
                           mode="LITERAL", remaining='","candidate_span":', next_step="CANDIDATE")
        if step == "CANDIDATE":
            return replace(self, mode="STRING_START", next_step="AUTHORITY_LITERAL")
        if step == "AUTHORITY_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"authority_support":', next_step="AUTHORITY")
        if step == "AUTHORITY":
            return replace(self, mode="NULLABLE_STRING_START", next_step="AUTHORITY_STRING")
        if step == "AUTHORITY_NULL":
            return replace(self, current_authority_null=True, mode="LITERAL", remaining=',"commitment":', next_step="COMMITMENT")
        if step == "AUTHORITY_STRING":
            return replace(self, current_authority_null=False, mode="LITERAL", remaining=',"commitment":', next_step="COMMITMENT")
        if step == "COMMITMENT":
            return replace(self, mode="STRING_START", next_step="SCOPE_LITERAL")
        if step == "SCOPE_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"scope_basis":"', next_step="SCOPE")
        if step == "SCOPE":
            return replace(self, mode="CHOICE", buffer="", choices=SCOPE_BASES, next_step="EVENT_LITERAL")
        if step == "EVENT_LITERAL":
            return replace(self, current_scope=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","event_alignment":"', next_step="EVENT")
        if step == "EVENT":
            return replace(self, mode="CHOICE", buffer="", choices=EVENT_ALIGNMENTS, next_step="AUTH_MODALITY_LITERAL")
        if step == "AUTH_MODALITY_LITERAL":
            return replace(self, current_event=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","authority_modality":"', next_step="AUTH_MODALITY")
        if step == "AUTH_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=MODALITIES, next_step="CAND_MODALITY_LITERAL")
        if step == "CAND_MODALITY_LITERAL":
            return replace(self, current_authority_modality=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","candidate_modality":"', next_step="CAND_MODALITY")
        if step == "CAND_MODALITY":
            return replace(self, mode="CHOICE", buffer="", choices=MODALITIES, next_step="AUTH_TIMING_LITERAL")
        if step == "AUTH_TIMING_LITERAL":
            return replace(self, current_candidate_modality=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","authority_timing":"', next_step="AUTH_TIMING")
        if step == "AUTH_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=TIMINGS, next_step="CAND_TIMING_LITERAL")
        if step == "CAND_TIMING_LITERAL":
            return replace(self, current_authority_timing=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","candidate_timing":"', next_step="CAND_TIMING")
        if step == "CAND_TIMING":
            return replace(self, mode="CHOICE", buffer="", choices=TIMINGS, next_step="GROUP_LITERAL")
        if step == "GROUP_LITERAL":
            return replace(self, current_candidate_timing=value, unresolved_seen=self.unresolved_seen or value == "UNRESOLVED",
                           mode="LITERAL", remaining='","independence_group":"', next_step="GROUP")
        if step == "GROUP":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(f"G{i}" for i in range(1, 9)), next_step="ENTRY_END")
        if step == "ENTRY_END":
            self._validate_current_entry()
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
            return replace(self, receipt_unresolved=value == "true", mode="LITERAL", remaining='},"coverage_decision":"', next_step="COVERAGE")
        if step == "COVERAGE":
            return replace(self, mode="CHOICE", buffer="", choices=("COMPLETE", "INDETERMINATE"), next_step="COVERAGE_END")
        if step == "COVERAGE_END":
            return replace(self, coverage=value, mode="LITERAL", remaining='"}', next_step="TERMINAL")
        if step == "TERMINAL":
            if self.entry_count < 1:
                self._fail("EMPTY_ENTRIES")
            if self.coverage == "COMPLETE":
                if self.unresolved_seen or self.receipt_unresolved or not self.receipt_whole or not self.receipt_embedded or not self.receipt_creative:
                    self._fail("INVALID_COMPLETE_INVARIANTS")
            elif not self.unresolved_seen or not self.receipt_unresolved:
                self._fail("INVALID_INDETERMINATE_INVARIANTS")
            return replace(self, mode="TERMINAL", terminal=True, remaining="")
        self._fail("UNKNOWN_ADVANCE")

    def _entry_start(self) -> "StagePRoleCoherenceConstraintStateV1":
        return replace(
            self, entry_count=self.entry_count + 1, mode="LITERAL", remaining='{"entry_id":"', next_step="ENTRY_ID",
            current_entry_type=None, current_authority_null=None, current_scope=None, current_event=None,
            current_authority_modality=None, current_candidate_modality=None,
            current_authority_timing=None, current_candidate_timing=None,
        )

    def _validate_current_entry(self) -> None:
        t, scope, event = self.current_entry_type, self.current_scope, self.current_event
        am, cm = self.current_authority_modality, self.current_candidate_modality
        at, ct = self.current_authority_timing, self.current_candidate_timing
        if t == "CONTAINED_CREATIVE":
            if (scope, event, am, cm, at, ct) != (
                "CREATIVE_CONTAINED", "CREATIVE_VEHICLE_ONLY", "NOT_APPLICABLE",
                "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE",
            ):
                self._fail("CONTAINED_CREATIVE_ROLE_INCOHERENT")
        elif t == "REAL_WORLD_COMMITMENT":
            if scope not in {"ASSERTED", "PRESUPPOSED", "ENTAILED", "NECESSARILY_IMPLIED"}:
                self._fail("REAL_WORLD_SCOPE_INCOHERENT")
            if event not in {"GOVERNED_EVENT", "NEW_UNSUPPORTED_EVENT"}:
                self._fail("REAL_WORLD_EVENT_INCOHERENT")
            if cm in {"NOT_APPLICABLE", "UNRESOLVED"} or ct in {"NOT_APPLICABLE", "UNRESOLVED"}:
                self._fail("REAL_WORLD_CANDIDATE_AXES_INCOHERENT")
            if self.current_authority_null:
                if am != "NOT_APPLICABLE" or at != "NOT_APPLICABLE":
                    self._fail("NULL_AUTHORITY_AXES_INCOHERENT")
            elif am in {"NOT_APPLICABLE", "UNRESOLVED"} or at in {"NOT_APPLICABLE", "UNRESOLVED"}:
                self._fail("SUPPORTED_AUTHORITY_AXES_INCOHERENT")
        elif t == "UNRESOLVED_SCOPE":
            if "UNRESOLVED" not in {scope, event, cm, ct}:
                self._fail("UNRESOLVED_SCOPE_WITHOUT_UNRESOLVED_AXIS")
        else:
            self._fail("UNKNOWN_ENTRY_TYPE")


__all__ = ("StagePRoleCoherenceConstraintStateV1", "StagePRoleCoherenceConstraintViolationV1")
