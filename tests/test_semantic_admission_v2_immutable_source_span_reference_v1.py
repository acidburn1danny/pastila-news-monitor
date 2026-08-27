from __future__ import annotations

import hashlib
import random

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    SourceProjectionErrorV1,
    SourceProjectionFailureCodeV1,
    SourceRoleV1,
    SourceSpanReferenceV1,
    resolve_source_span_v1,
)


def _ref(source, start, end, *, role=None, sha=None):
    return SourceSpanReferenceV1(
        source_role=role or source.role,
        source_sha256=sha or source.sha256,
        start_utf8=start,
        end_utf8=end,
    )


def _assert_code(code, call):
    with pytest.raises(SourceProjectionErrorV1) as caught:
        call()
    assert caught.value.code is code


def test_schema_is_versioned_frozen_strict_and_forbids_extra_fields():
    source = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE, data=b"abc")
    value = _ref(source, 0, 3)
    assert value.schema_name == SCHEMA_NAME
    assert value.schema_version == SCHEMA_VERSION
    with pytest.raises(ValidationError):
        SourceSpanReferenceV1.model_validate({
            **value.model_dump(), "start_utf8": "0", "unexpected": True,
        }, strict=True)
    with pytest.raises(ValidationError):
        SourceSpanReferenceV1(**{**value.model_dump(), "end_utf8": 0})


def test_case01_diacritic_is_projected_exactly_and_typo_cannot_enter_evidence():
    text = "Când banii se ascund în umbră, iar angajații rămân la lumină."
    source = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data=text.encode("utf-8")
    )
    start = source.data.index("angajații".encode())
    resolved = resolve_source_span_v1(
        _ref(source, start, start + len("angajații".encode())),
        expected_role=SourceRoleV1.CANDIDATE,
        sources={source.role: source},
    )
    assert resolved.projected_bytes == "angajații".encode()
    assert resolved.projected_text == "angajații"
    assert resolved.projected_text != "angazații"
    assert resolved.projected_sha256 == hashlib.sha256(resolved.projected_bytes).hexdigest()


def test_repeated_text_is_unambiguous_by_coordinates():
    source = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data="ecou — ecou — ecou".encode()
    )
    starts = [index for index in range(len(source.data)) if source.data.startswith(b"ecou", index)]
    assert starts == [0, 9, 18]
    values = [resolve_source_span_v1(
        _ref(source, index, index + 4), expected_role=source.role,
        sources={source.role: source}) for index in starts]
    assert [item.start_utf8 for item in values] == starts
    assert all(item.projected_bytes == b"ecou" for item in values)


def test_utf8_boundaries_cover_emoji_and_combining_sequences():
    source = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data="A🙂e\u0301Z".encode()
    )
    emoji_start = source.data.index("🙂".encode())
    resolved = resolve_source_span_v1(
        _ref(source, emoji_start, emoji_start + len("🙂".encode())),
        expected_role=source.role, sources={source.role: source})
    assert resolved.projected_text == "🙂"
    _assert_code(SourceProjectionFailureCodeV1.UTF8_BOUNDARY_INVALID, lambda:
        resolve_source_span_v1(_ref(source, emoji_start + 1, emoji_start + 4),
                               expected_role=source.role, sources={source.role: source}))
    combining = "e\u0301".encode()
    start = source.data.index(combining)
    assert resolve_source_span_v1(
        _ref(source, start, start + len(combining)), expected_role=source.role,
        sources={source.role: source}).projected_text == "e\u0301"


def test_role_identity_range_and_missing_source_fail_closed():
    candidate = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE, data=b"candidate")
    authority = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.FACTUAL_AUTHORITY, data=b"authority")
    sources = {candidate.role: candidate, authority.role: authority}
    _assert_code(SourceProjectionFailureCodeV1.ROLE_MISMATCH, lambda:
        resolve_source_span_v1(_ref(candidate, 0, 1), expected_role=authority.role, sources=sources))
    _assert_code(SourceProjectionFailureCodeV1.IDENTITY_DRIFT, lambda:
        resolve_source_span_v1(_ref(candidate, 0, 1, sha="0" * 64), expected_role=candidate.role, sources=sources))
    _assert_code(SourceProjectionFailureCodeV1.RANGE_INVALID, lambda:
        resolve_source_span_v1(_ref(candidate, 0, 99), expected_role=candidate.role, sources=sources))
    _assert_code(SourceProjectionFailureCodeV1.SOURCE_UNAVAILABLE, lambda:
        resolve_source_span_v1(_ref(candidate, 0, 1), expected_role=candidate.role, sources={}))


def test_randomized_every_accepted_projection_is_exact_source_slice():
    rng = random.Random(0xC0FFEE)
    alphabet = ["a", "Z", " ", "ă", "ț", "🙂", "e\u0301", "—", "\n"]
    for _ in range(500):
        units = [rng.choice(alphabet) for _ in range(rng.randint(1, 40))]
        text = "".join(units)
        source = ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data=text.encode("utf-8"))
        boundaries = [0]
        size = 0
        for character in text:
            size += len(character.encode("utf-8"))
            boundaries.append(size)
        left_index = rng.randrange(len(boundaries) - 1)
        right_index = rng.randrange(left_index + 1, len(boundaries))
        start, end = boundaries[left_index], boundaries[right_index]
        resolved = resolve_source_span_v1(
            _ref(source, start, end), expected_role=source.role,
            sources={source.role: source})
        assert resolved.projected_bytes == source.data[start:end]
        assert resolved.projected_text.encode("utf-8") == source.data[start:end]


def test_source_binding_rejects_non_utf8_bytes():
    with pytest.raises(UnicodeDecodeError):
        ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE, data=b"\xff")
