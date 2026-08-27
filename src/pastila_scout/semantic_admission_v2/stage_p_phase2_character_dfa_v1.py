"""Request-bound character DFAs for the two Phase 2 audit responses.

Character-only evaluation candidates: no tokenizer, token projector, prompt,
provider, model, evaluator, runner, or filesystem dependency.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from .stage_p_constraint_v1 import StagePConstraintStateV1, StagePConstraintViolationV1
from .stage_p_phase2_audit_contracts_v1 import FSEM_CODES
from .stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    StagePSourceReferenceConstraintStateV1,
)


COMMITMENT_DECISIONS = (
    "SPAN_SUPPORTS_COMPLETE_COMMITMENT", "COMMITMENT_EXCEEDS_SPAN",
    "SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING", "ENTRY_ROLE_MISCLASSIFIED",
    "UNRESOLVED_FAIL_CLOSED",
)
COMMITMENT_REASONS = {
    "SPAN_SUPPORTS_COMPLETE_COMMITMENT": "null",
    "COMMITMENT_EXCEEDS_SPAN": '"CSPAN_COMMITMENT_EXCEEDS_PROJECTED_SPAN"',
    "SPAN_CONTAINS_MATERIAL_UNRECONCILED_MEANING": '"CSPAN_MATERIAL_MEANING_UNRECONCILED"',
    "ENTRY_ROLE_MISCLASSIFIED": '"CSPAN_ENTRY_ROLE_MISCLASSIFIED"',
    "UNRESOLVED_FAIL_CLOSED": '"CSPAN_SCOPE_OR_SUPPORT_UNRESOLVED"',
}
AUTHORITY_DECISIONS = (
    "GOVERNED_SUPPORTED", "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION",
    "NOT_A_REAL_WORLD_COMMITMENT", "UNRESOLVED_FAIL_CLOSED",
)
AXES = ("MATCH", "MUTATION", "NOT_APPLICABLE", "UNRESOLVED")


@dataclass(frozen=True)
class CommitmentSpanAuditCharacterDfaV1(StagePConstraintStateV1):
    expected_entry_ids: tuple[str, ...] = ()
    remaining: str = (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-commitment-span-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"COMMITMENT_SPAN_AUDIT","records":[')
    next_step: str = "START_RECORD"
    record_index: int = 0
    current_decision: str | None = None
    character_limit: int = 12_000

    def __post_init__(self) -> None:
        _validate_entry_ids(self.expected_entry_ids, allow_empty=False)

    @classmethod
    def for_entries(cls, entry_ids: tuple[str, ...]) -> "CommitmentSpanAuditCharacterDfaV1":
        return cls(expected_entry_ids=entry_ids)

    def _feed_char(self, char: str):
        if self.characters >= self.character_limit:
            raise StagePConstraintViolationV1("PHASE2_COMMITMENT_CHARACTER_LIMIT")
        if self.mode == "STRING" and self.string_characters >= 500 and char != '"':
            raise StagePConstraintViolationV1("PHASE2_COMMITMENT_BASIS_LIMIT")
        return super()._feed_char(char)

    def _advance(self, step: str, value: str | None = None):
        if step == "START_RECORD":
            entry_id = self.expected_entry_ids[self.record_index]
            return replace(self, mode="LITERAL", remaining=f'{{"entry_id":"{entry_id}","decision":"',
                           next_step="DECISION")
        if step == "DECISION":
            return replace(self, mode="CHOICE", buffer="", choices=COMMITMENT_DECISIONS,
                           next_step="AFTER_DECISION")
        if step == "AFTER_DECISION":
            return replace(self, current_decision=value, mode="LITERAL", remaining=(
                '","assertion_checked":true,"presupposition_checked":true,'
                '"entailment_checked":true,"necessary_implication_checked":true,'
                '"reason_code":'), next_step="REASON")
        if step == "REASON":
            return replace(self, mode="LITERAL", remaining=COMMITMENT_REASONS[self.current_decision],
                           next_step="BASIS_LITERAL")
        if step == "BASIS_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"basis":', next_step="BASIS")
        if step == "BASIS":
            return replace(self, mode="STRING_START", next_step="END_RECORD")
        if step == "END_RECORD":
            last = self.record_index + 1 == len(self.expected_entry_ids)
            return replace(self, mode="LITERAL", remaining="}]" if last else "},{",
                           next_step="TERMINAL" if last else "NEXT_RECORD")
        if step == "NEXT_RECORD":
            next_index = self.record_index + 1
            entry_id = self.expected_entry_ids[next_index]
            return replace(self, record_index=next_index, current_decision=None, mode="LITERAL",
                           remaining=f'"entry_id":"{entry_id}","decision":"', next_step="DECISION")
        if step == "TERMINAL":
            return replace(self, mode="LITERAL", remaining="}", next_step="FINAL")
        if step == "FINAL":
            return replace(self, mode="TERMINAL", terminal=True, remaining="")
        raise StagePConstraintViolationV1(f"PHASE2_COMMITMENT_UNKNOWN_STEP:{step}")


def _axis_choices(decision: str) -> tuple[str, ...]:
    def rendered(values):
        left, middle, right = values
        return f'{left}","modality_axis":"{middle}","timing_axis":"{right}'
    if decision == "GOVERNED_SUPPORTED":
        return (rendered(("MATCH", "MATCH", "MATCH")),)
    if decision == "NOT_A_REAL_WORLD_COMMITMENT":
        return (rendered(("NOT_APPLICABLE",) * 3),)
    if decision == "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION":
        return tuple(rendered(values) for values in _product(AXES[:3], repeat=3))
    return tuple(rendered(values) for values in _product(AXES, repeat=3)
                 if "UNRESOLVED" in values)


@dataclass(frozen=True)
class AuthorityReconciliationCharacterDfaV1(StagePConstraintStateV1):
    expected_entry_ids: tuple[str, ...] = ()
    context: SourceReferenceConstraintContextV1 | None = None
    remaining: str = (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":[')
    next_step: str = "START_RECORD"
    record_index: int = 0
    current_decision: str | None = None
    current_finding_ids: tuple[str, ...] = ()
    records_with_findings: tuple[tuple[str, tuple[str, ...]], ...] = ()
    next_finding_number: int = 1
    finding_index: int = 0
    decisive_entries: frozenset[str] = frozenset()
    current_finding_entry: str | None = None
    current_finding_status: str | None = None
    reference_state: StagePSourceReferenceConstraintStateV1 | None = None
    reference_return_step: str | None = None
    reference_must_be_nonnull: bool = False
    # The inherited character engine has a hard 16,000-character ceiling.
    # Keep the request-bound candidate explicit and truthful about that limit.
    character_limit: int = 16_000

    def __post_init__(self) -> None:
        _validate_entry_ids(self.expected_entry_ids, allow_empty=False)
        if self.context is None:
            raise ValueError("PHASE2_AUTHORITY_SOURCE_CONTEXT_REQUIRED")

    @classmethod
    def for_request(cls, *, entry_ids: tuple[str, ...],
                    context: SourceReferenceConstraintContextV1):
        return cls(expected_entry_ids=entry_ids, context=context)

    def _feed_char(self, char: str):
        if self.characters >= self.character_limit:
            raise StagePConstraintViolationV1("PHASE2_AUTHORITY_CHARACTER_LIMIT")
        if self.mode == "STRING" and self.string_characters >= 500 and char != '"':
            raise StagePConstraintViolationV1("PHASE2_AUTHORITY_BASIS_LIMIT")
        if self.mode == "REFERENCE":
            if self.reference_state is None or self.reference_return_step is None:
                raise StagePConstraintViolationV1("PHASE2_AUTHORITY_REFERENCE_STATE_MISSING")
            reference = self.reference_state.feed(char)
            if reference.is_failed:
                raise StagePConstraintViolationV1(reference.failure_reason or "REFERENCE_FAILURE")
            state = replace(self, characters=self.characters + 1, reference_state=reference)
            if not reference.is_terminal:
                return state
            if state.reference_must_be_nonnull and reference.selected_start is None:
                raise StagePConstraintViolationV1("PHASE2_AUTHORITY_SUPPORT_NULL_FOR_SUPPORTED")
            return replace(state, mode="REFERENCE_COMPLETE", reference_state=None,
                           reference_return_step=None)._advance(state.reference_return_step)
        if self.mode == "FINDING_LINK_SEPARATOR":
            state = replace(self, characters=self.characters + 1)
            if char == "]":
                return state._advance("AFTER_FINDING_LINKS")
            if char == ",":
                if self.next_finding_number > 16:
                    raise StagePConstraintViolationV1("PHASE2_AUTHORITY_FINDING_LIMIT")
                finding_id = f"F{self.next_finding_number}"
                return replace(state, mode="LITERAL", remaining=f'"{finding_id}"',
                               next_step="ADDED_FINDING_LINK")
            raise StagePConstraintViolationV1("PHASE2_AUTHORITY_FINDING_LINK_SEPARATOR")
        return super()._feed_char(char)

    def _start_reference(self, field: ReferenceFieldV1, return_step: str, *, nonnull: bool):
        return replace(self, mode="REFERENCE",
                       reference_state=StagePSourceReferenceConstraintStateV1.for_field(
                           context=self.context, field=field),
                       reference_return_step=return_step, reference_must_be_nonnull=nonnull)

    def _advance(self, step: str, value: str | None = None):
        if step == "START_RECORD":
            entry_id = self.expected_entry_ids[self.record_index]
            return replace(self, mode="LITERAL", remaining=(
                f'{{"entry_id":"{entry_id}","full_authority_compared":true,"decision":"'),
                next_step="DECISION")
        if step == "DECISION":
            return replace(self, mode="CHOICE", buffer="", choices=AUTHORITY_DECISIONS,
                           next_step="AFTER_DECISION")
        if step == "AFTER_DECISION":
            return replace(self, current_decision=value, current_finding_ids=(), mode="LITERAL",
                           remaining='","authority_support_ref":', next_step="SUPPORT")
        if step == "SUPPORT":
            if self.current_decision == "GOVERNED_SUPPORTED":
                return self._start_reference(ReferenceFieldV1.AUTHORITY_SUPPORT,
                                             "AXES_LITERAL", nonnull=True)
            return replace(self, mode="LITERAL", remaining="null", next_step="AXES_LITERAL")
        if step == "AXES_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"event_axis":"', next_step="AXES")
        if step == "AXES":
            return replace(self, mode="CHOICE", buffer="", choices=_axis_choices(self.current_decision),
                           next_step="FINDING_LINKS_LITERAL")
        if step == "FINDING_LINKS_LITERAL":
            return replace(self, mode="LITERAL", remaining='","unsupported_finding_ids":',
                           next_step="FINDING_LINKS")
        if step == "FINDING_LINKS":
            if self.current_decision != "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION":
                return replace(self, mode="LITERAL", remaining="[]", next_step="AFTER_FINDING_LINKS")
            finding_id = f"F{self.next_finding_number}"
            return replace(self, mode="LITERAL", remaining=f'["{finding_id}"',
                           next_step="ADDED_FINDING_LINK")
        if step == "ADDED_FINDING_LINK":
            finding_id = f"F{self.next_finding_number}"
            return replace(self, current_finding_ids=self.current_finding_ids + (finding_id,),
                           next_finding_number=self.next_finding_number + 1,
                           mode="FINDING_LINK_SEPARATOR")
        if step == "AFTER_FINDING_LINKS":
            records = self.records_with_findings
            if self.current_finding_ids:
                records += ((self.expected_entry_ids[self.record_index], self.current_finding_ids),)
            return replace(self, records_with_findings=records, mode="LITERAL",
                           remaining=',"basis":', next_step="BASIS")
        if step == "BASIS":
            return replace(self, mode="STRING_START", next_step="END_RECORD")
        if step == "END_RECORD":
            last = self.record_index + 1 == len(self.expected_entry_ids)
            return replace(self, mode="LITERAL", remaining="}]" if last else "},{",
                           next_step="FINDINGS_START" if last else "NEXT_RECORD")
        if step == "NEXT_RECORD":
            index = self.record_index + 1
            entry_id = self.expected_entry_ids[index]
            return replace(self, record_index=index, current_decision=None,
                           current_finding_ids=(), mode="LITERAL", remaining=(
                               f'"entry_id":"{entry_id}","full_authority_compared":true,"decision":"'),
                           next_step="DECISION")
        if step == "FINDINGS_START":
            if not self.records_with_findings:
                return replace(self, mode="LITERAL", remaining=',"unsupported_findings":[]}',
                               next_step="FINAL")
            return replace(self, mode="LITERAL", remaining=',"unsupported_findings":[',
                           next_step="START_FINDING")
        if step == "START_FINDING":
            finding_id, entry_id = self._finding_at(self.finding_index)
            return replace(self, current_finding_entry=entry_id, mode="LITERAL", remaining=(
                f'{{"finding_id":"{finding_id}","entry_id":"{entry_id}",'
                '"candidate_proposition_ref":'), next_step="FINDING_REFERENCE")
        if step == "FINDING_REFERENCE":
            return self._start_reference(ReferenceFieldV1.CANDIDATE_SPAN,
                                         "FINDING_REASON_LITERAL", nonnull=True)
        if step == "FINDING_REASON_LITERAL":
            return replace(self, mode="LITERAL", remaining=',"reason_code":"',
                           next_step="FINDING_REASON")
        if step == "FINDING_REASON":
            return replace(self, mode="CHOICE", buffer="", choices=tuple(sorted(FSEM_CODES)),
                           next_step="FINDING_STATUS_LITERAL")
        if step == "FINDING_STATUS_LITERAL":
            return replace(self, mode="LITERAL", remaining='","reason_status":"',
                           next_step="FINDING_STATUS")
        if step == "FINDING_STATUS":
            _, entry_id = self._finding_at(self.finding_index)
            last_for_entry = not any(item[1] == entry_id for item in
                                     (self._finding_at(i) for i in range(self.finding_index + 1,
                                                                         self._finding_count())))
            choices = (("DECISIVE",) if last_for_entry and entry_id not in self.decisive_entries
                       else ("DECISIVE", "SUPPORTING"))
            return replace(self, mode="CHOICE", buffer="", choices=choices,
                           next_step="FINDING_BASIS_LITERAL")
        if step == "FINDING_BASIS_LITERAL":
            decisive = self.decisive_entries
            if value == "DECISIVE":
                decisive = decisive | {self.current_finding_entry}
            return replace(self, decisive_entries=frozenset(decisive),
                           current_finding_status=value, mode="LITERAL",
                           remaining='","basis":', next_step="FINDING_BASIS")
        if step == "FINDING_BASIS":
            return replace(self, mode="STRING_START", next_step="END_FINDING")
        if step == "END_FINDING":
            last = self.finding_index + 1 == self._finding_count()
            return replace(self, mode="LITERAL", remaining="}]}" if last else "},{",
                           next_step="FINAL" if last else "NEXT_FINDING")
        if step == "NEXT_FINDING":
            index = self.finding_index + 1
            finding_id, entry_id = self._finding_at(index)
            return replace(self, finding_index=index, current_finding_entry=entry_id,
                           current_finding_status=None, mode="LITERAL", remaining=(
                               f'"finding_id":"{finding_id}","entry_id":"{entry_id}",'
                               '"candidate_proposition_ref":'), next_step="FINDING_REFERENCE")
        if step == "FINAL":
            required = {entry_id for entry_id, _ in self.records_with_findings}
            if not required.issubset(self.decisive_entries):
                raise StagePConstraintViolationV1("PHASE2_AUTHORITY_DECISIVE_FINDING_MISSING")
            return replace(self, mode="TERMINAL", terminal=True, remaining="")
        raise StagePConstraintViolationV1(f"PHASE2_AUTHORITY_UNKNOWN_STEP:{step}")

    def _finding_count(self) -> int:
        return sum(len(ids) for _, ids in self.records_with_findings)

    def _finding_at(self, index: int) -> tuple[str, str]:
        flattened = tuple((finding_id, entry_id) for entry_id, ids in self.records_with_findings
                          for finding_id in ids)
        return flattened[index]


def _product(values: tuple[str, ...], *, repeat: int):
    rows = [()]
    for _ in range(repeat):
        rows = [row + (value,) for row in rows for value in values]
    return tuple(rows)


def _validate_entry_ids(entry_ids: tuple[str, ...], *, allow_empty: bool) -> None:
    if type(entry_ids) is not tuple or (not entry_ids and not allow_empty) or len(entry_ids) > 8:
        raise ValueError("PHASE2_DFA_ENTRY_SET_INVALID")
    if len(entry_ids) != len(set(entry_ids)) or any(
            type(item) is not str or len(item) != 2 or item[0] != "P" or item[1] not in "12345678"
            for item in entry_ids):
        raise ValueError("PHASE2_DFA_ENTRY_SET_INVALID")


@dataclass(frozen=True, slots=True)
class Phase2PrefixResultV1:
    state: object
    decoded: str
    decoded_sha256: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int


class Phase2IncrementalCharacterTrackerV1:
    def __init__(self, factory: Callable[[], object]) -> None:
        self.factory = factory
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = factory()

    def state_for(self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str]):
        ids = tuple(token_ids); decoded = decode(ids)
        if type(decoded) is not str:
            raise ValueError("PHASE2_DFA_DECODE_OUTPUT_INVALID")
        if ids == self._last_ids and decoded != self._last_decoded:
            raise ValueError("PHASE2_DFA_DECODE_INSTABILITY")
        extends = len(ids) >= len(self._last_ids) and ids[:len(self._last_ids)] == self._last_ids
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]
            state = self._last_state.feed(suffix); path = "INCREMENTAL"
        else:
            suffix = decoded; state = self.factory().feed(decoded); path = "FULL_REBUILD"
        self._last_ids=ids; self._last_decoded=decoded; self._last_state=state
        return Phase2PrefixResultV1(
            state, decoded, hashlib.sha256(decoded.encode()).hexdigest(), ids, path, len(suffix))


__all__ = (
    "AuthorityReconciliationCharacterDfaV1", "CommitmentSpanAuditCharacterDfaV1",
    "Phase2IncrementalCharacterTrackerV1", "Phase2PrefixResultV1",
)
