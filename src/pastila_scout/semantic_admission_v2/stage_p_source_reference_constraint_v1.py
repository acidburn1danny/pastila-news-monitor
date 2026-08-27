"""Request-bound character DFA for copyless V2 provenance references."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from enum import StrEnum

from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1


class ReferenceFieldV1(StrEnum):
    CANDIDATE_SPAN = "candidate_span_ref"
    VEHICLE_SPAN = "vehicle_span_ref"
    AUTHORITY_SUPPORT = "authority_support_ref"


@dataclass(frozen=True, slots=True)
class BoundSourceConstraintV1:
    role: SourceRoleV1
    sha256: str
    byte_length: int
    utf8_boundaries: tuple[int, ...]

    @classmethod
    def from_source(cls, source: ImmutableUtf8SourceV1) -> "BoundSourceConstraintV1":
        text = source.data.decode("utf-8", errors="strict")
        boundaries = [0]; size = 0
        for character in text:
            size += len(character.encode("utf-8")); boundaries.append(size)
        if size != len(source.data):
            raise ValueError("SOURCE_BYTE_LENGTH_DRIFT")
        return cls(source.role, source.sha256, len(source.data), tuple(boundaries))


@dataclass(frozen=True, slots=True)
class SourceReferenceConstraintContextV1:
    candidate: BoundSourceConstraintV1
    factual_authority: BoundSourceConstraintV1
    binding_identity: str

    @classmethod
    def bind(cls, *, candidate: ImmutableUtf8SourceV1,
             factual_authority: ImmutableUtf8SourceV1) -> "SourceReferenceConstraintContextV1":
        if candidate.role is not SourceRoleV1.CANDIDATE:
            raise ValueError("CANDIDATE_SOURCE_ROLE_MISMATCH")
        if factual_authority.role is not SourceRoleV1.FACTUAL_AUTHORITY:
            raise ValueError("FACTUAL_AUTHORITY_SOURCE_ROLE_MISMATCH")
        left = BoundSourceConstraintV1.from_source(candidate)
        right = BoundSourceConstraintV1.from_source(factual_authority)
        parts = (
            "STAGE_P_SOURCE_REFERENCE_CONSTRAINT_CONTEXT_V1",
            left.role.value, left.sha256, str(left.byte_length),
            ",".join(map(str, left.utf8_boundaries)),
            right.role.value, right.sha256, str(right.byte_length),
            ",".join(map(str, right.utf8_boundaries)),
        )
        identity = hashlib.sha256("\n".join(parts).encode()).hexdigest()
        return cls(left, right, identity)

    def source_for(self, field: ReferenceFieldV1) -> BoundSourceConstraintV1:
        if field is ReferenceFieldV1.AUTHORITY_SUPPORT:
            return self.factual_authority
        return self.candidate


class ReferenceConstraintModeV1(StrEnum):
    INITIAL = "INITIAL"
    LITERAL = "LITERAL"
    START_NUMBER = "START_NUMBER"
    END_NUMBER = "END_NUMBER"
    TERMINAL = "TERMINAL"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class StagePSourceReferenceConstraintStateV1:
    context: SourceReferenceConstraintContextV1
    field: ReferenceFieldV1
    mode: ReferenceConstraintModeV1 = ReferenceConstraintModeV1.INITIAL
    remaining: str = ""
    after_literal: ReferenceConstraintModeV1 | None = None
    number_buffer: str = ""
    number_choices: tuple[str, ...] = ()
    selected_start: int | None = None
    characters: int = 0
    failure_reason: str | None = None

    @classmethod
    def for_field(cls, *, context: SourceReferenceConstraintContextV1,
                  field: ReferenceFieldV1) -> "StagePSourceReferenceConstraintStateV1":
        return cls(context=context, field=field)

    @property
    def source(self) -> BoundSourceConstraintV1:
        return self.context.source_for(self.field)

    @property
    def is_terminal(self) -> bool:
        return self.mode is ReferenceConstraintModeV1.TERMINAL

    @property
    def is_failed(self) -> bool:
        return self.mode is ReferenceConstraintModeV1.FAILED

    def allowed_next_characters(self) -> frozenset[str]:
        if self.mode is ReferenceConstraintModeV1.INITIAL:
            return frozenset(("{", "n")) if self.field is ReferenceFieldV1.AUTHORITY_SUPPORT else frozenset(("{",))
        if self.mode is ReferenceConstraintModeV1.LITERAL:
            return frozenset((self.remaining[0],)) if self.remaining else frozenset()
        if self.mode is ReferenceConstraintModeV1.START_NUMBER:
            return self._number_allowed(self.number_choices, delimiter=",")
        if self.mode is ReferenceConstraintModeV1.END_NUMBER:
            return self._number_allowed(self.number_choices, delimiter="}")
        return frozenset()

    def _number_allowed(self, choices: tuple[str, ...], *, delimiter: str) -> frozenset[str]:
        allowed = {choice[len(self.number_buffer)] for choice in choices
                   if choice.startswith(self.number_buffer) and len(choice) > len(self.number_buffer)}
        if self.number_buffer in choices:
            allowed.add(delimiter)
        return frozenset(allowed)

    def feed(self, text: str) -> "StagePSourceReferenceConstraintStateV1":
        state = self
        for character in text:
            state = state._feed_character(character)
        return state

    def _feed_character(self, character: str) -> "StagePSourceReferenceConstraintStateV1":
        if self.mode in {ReferenceConstraintModeV1.TERMINAL, ReferenceConstraintModeV1.FAILED}:
            return self._fail("CHARACTER_AFTER_TERMINAL_OR_FAILURE")
        if character not in self.allowed_next_characters():
            return self._fail("REFERENCE_PREFIX_NOT_IN_LANGUAGE")
        state = replace(self, characters=self.characters + 1)
        if self.mode is ReferenceConstraintModeV1.INITIAL:
            if character == "n":
                return replace(state, mode=ReferenceConstraintModeV1.LITERAL, remaining="ull",
                               after_literal=ReferenceConstraintModeV1.TERMINAL)
            source = self.source
            prefix = (f'"source_role":"{source.role.value}",'
                      f'"source_sha256":"{source.sha256}","start_utf8":')
            return replace(state, mode=ReferenceConstraintModeV1.LITERAL, remaining=prefix,
                           after_literal=ReferenceConstraintModeV1.START_NUMBER)
        if self.mode is ReferenceConstraintModeV1.LITERAL:
            remaining = self.remaining[1:]
            if remaining:
                return replace(state, remaining=remaining)
            choices = self.number_choices
            if self.after_literal is ReferenceConstraintModeV1.START_NUMBER:
                choices = tuple(str(value) for value in self.source.utf8_boundaries[:-1])
            elif self.after_literal is ReferenceConstraintModeV1.END_NUMBER:
                choices = tuple(str(value) for value in self.source.utf8_boundaries
                                if self.selected_start is not None and value > self.selected_start)
            return replace(state, mode=self.after_literal, remaining="", after_literal=None,
                           number_buffer="", number_choices=choices)
        if self.mode is ReferenceConstraintModeV1.START_NUMBER:
            if character != ",":
                return replace(state, number_buffer=self.number_buffer + character)
            selected = int(self.number_buffer)
            return replace(state, mode=ReferenceConstraintModeV1.LITERAL,
                           remaining='"end_utf8":',
                           after_literal=ReferenceConstraintModeV1.END_NUMBER,
                           number_buffer="", number_choices=(), selected_start=selected)
        if self.mode is ReferenceConstraintModeV1.END_NUMBER:
            if character != "}":
                return replace(state, number_buffer=self.number_buffer + character)
            return replace(state, mode=ReferenceConstraintModeV1.TERMINAL,
                           number_buffer="", number_choices=())
        return self._fail("UNREACHABLE_REFERENCE_STATE")

    def _fail(self, reason: str) -> "StagePSourceReferenceConstraintStateV1":
        return replace(self, mode=ReferenceConstraintModeV1.FAILED,
                       failure_reason=self.failure_reason or reason)


def canonical_reference_json_v1(*, context: SourceReferenceConstraintContextV1,
                                field: ReferenceFieldV1, start_utf8: int,
                                end_utf8: int) -> str:
    source = context.source_for(field)
    return (f'{{"source_role":"{source.role.value}",'
            f'"source_sha256":"{source.sha256}","start_utf8":{start_utf8},'
            f'"end_utf8":{end_utf8}}}')


def accepts_reference_json_v1(*, context: SourceReferenceConstraintContextV1,
                              field: ReferenceFieldV1, text: str) -> bool:
    return StagePSourceReferenceConstraintStateV1.for_field(
        context=context, field=field).feed(text).is_terminal


__all__ = (
    "BoundSourceConstraintV1", "ReferenceConstraintModeV1", "ReferenceFieldV1",
    "SourceReferenceConstraintContextV1", "StagePSourceReferenceConstraintStateV1",
    "accepts_reference_json_v1", "canonical_reference_json_v1",
)
