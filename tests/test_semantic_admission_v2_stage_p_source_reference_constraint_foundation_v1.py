from __future__ import annotations

import itertools

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    StagePSourceReferenceConstraintStateV1,
    accepts_reference_json_v1,
    canonical_reference_json_v1,
)


def _context(candidate="ăb", authority="🙂x"):
    return SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data=candidate.encode()
        ),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data=authority.encode()
        ),
    )


def _valid_outputs(context, field):
    source = context.source_for(field)
    values = {
        canonical_reference_json_v1(
            context=context, field=field, start_utf8=start, end_utf8=end
        )
        for start, end in itertools.combinations(source.utf8_boundaries, 2)
    }
    if field is ReferenceFieldV1.AUTHORITY_SUPPORT:
        values.add("null")
    return values


def test_exhaustive_small_unicode_language_and_single_character_mutations():
    context = _context()
    alphabet = '{}":,null0123456789abcdefCANDITEF_UHORSPV'
    for field in ReferenceFieldV1:
        expected = _valid_outputs(context, field)
        for output in expected:
            assert accepts_reference_json_v1(context=context, field=field, text=output)
            for index, original in enumerate(output):
                for replacement in alphabet:
                    if replacement == original:
                        continue
                    mutated = output[:index] + replacement + output[index + 1 :]
                    assert accepts_reference_json_v1(
                        context=context, field=field, text=mutated
                    ) == (mutated in expected)


def test_every_valid_prefix_is_live_and_incremental_equals_full_rebuild():
    context = _context()
    for field in ReferenceFieldV1:
        for output in _valid_outputs(context, field):
            state = StagePSourceReferenceConstraintStateV1.for_field(
                context=context, field=field
            )
            for index, character in enumerate(output):
                assert character in state.allowed_next_characters()
                state = state.feed(character)
                rebuilt = StagePSourceReferenceConstraintStateV1.for_field(
                    context=context, field=field
                ).feed(output[: index + 1])
                assert state == rebuilt
            assert state.is_terminal and not state.allowed_next_characters()


def test_breadth_first_exhaustion_matches_exact_small_fixture_language():
    context = _context()
    for field in ReferenceFieldV1:
        frontier = [
            (
                "",
                StagePSourceReferenceConstraintStateV1.for_field(
                    context=context, field=field
                ),
            )
        ]
        terminal = set()
        while frontier:
            prefix, state = frontier.pop()
            if state.is_terminal:
                terminal.add(prefix)
                continue
            for character in state.allowed_next_characters():
                frontier.append((prefix + character, state.feed(character)))
        assert terminal == _valid_outputs(context, field)


def test_wrong_role_hash_offsets_leading_zero_and_null_fail():
    context = _context()
    field = ReferenceFieldV1.CANDIDATE_SPAN
    valid = canonical_reference_json_v1(
        context=context, field=field, start_utf8=0, end_utf8=2
    )
    invalid = {
        valid.replace('"CANDIDATE"', '"FACTUAL_AUTHORITY"'),
        valid.replace(context.candidate.sha256, "0" * 64),
        valid.replace('"start_utf8":0', '"start_utf8":1'),
        valid.replace('"start_utf8":0', '"start_utf8":00'),
        valid.replace('"end_utf8":2', '"end_utf8":0'),
        valid.replace('"end_utf8":2', '"end_utf8":1'),
        "null",
    }
    assert all(
        not accepts_reference_json_v1(context=context, field=field, text=item)
        for item in invalid
    )


def test_context_identity_separates_same_lengths_with_different_bytes():
    first = _context(candidate="ab", authority="cd")
    second = _context(candidate="xy", authority="zw")
    assert first.binding_identity != second.binding_identity
    output = canonical_reference_json_v1(
        context=first,
        field=ReferenceFieldV1.CANDIDATE_SPAN,
        start_utf8=0,
        end_utf8=1,
    )
    assert accepts_reference_json_v1(
        context=first, field=ReferenceFieldV1.CANDIDATE_SPAN, text=output
    )
    assert not accepts_reference_json_v1(
        context=second, field=ReferenceFieldV1.CANDIDATE_SPAN, text=output
    )
