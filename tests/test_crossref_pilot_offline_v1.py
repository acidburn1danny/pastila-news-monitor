"""Adversarial offline tests for the bounded Crossref pilot implementation."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from pastila_scout.crossref_pilot_offline_v1 import (
    FROZEN_REQUEST,
    MAXIMUM_RESPONSE_BODY_BYTES,
    MEDIA_TYPE,
    NormalizationRejected,
    NormalizedRecordSetV1,
    NormalizedRecordV1,
    RawResponseCaptureV1,
    ResponseBodyLimitExceeded,
    ResponseProfileRejected,
    execute_one_shot_capture_v1,
    frozen_request_identity_v1,
    normalize_capture_v1,
)


class FakeResponse:
    def __init__(
        self, body: bytes, *, status: int = 200, content_type: str = MEDIA_TYPE
    ):
        self.status = status
        self._body = body
        self._offset = 0
        self._headers = [("Content-Type", content_type), ("X-Test", "offline")]
        self.read_amounts: list[int] = []

    def getheaders(self) -> list[tuple[str, str]]:
        return list(self._headers)

    def read(self, amount: int) -> bytes:
        self.read_amounts.append(amount)
        chunk = self._body[self._offset : self._offset + amount]
        self._offset += len(chunk)
        return chunk


def body(items: list[object]) -> bytes:
    return json.dumps({"message": {"items": items}}, separators=(",", ":")).encode()


def item(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "DOI": "10.1234/example",
        "title": ["Title"],
        "publisher": "Publisher",
        "type": "journal-article",
        "published": {"date-parts": [[2000, 1, 1]]},
        "created": {"date-time": "2000-01-01T00:00:00Z"},
        "URL": "https://doi.org/10.1234/example",
    }
    value.update(updates)
    return value


def capture(payload: bytes, *, status: int = 200, content_type: str = MEDIA_TYPE):
    return RawResponseCaptureV1(status, (("Content-Type", content_type),), payload)


def test_frozen_request_is_exact_and_has_no_retry_redirect_pagination_or_body() -> None:
    assert asdict(FROZEN_REQUEST) == {
        "scheme": "https",
        "host": "api.crossref.org",
        "port": 443,
        "method": "GET",
        "target": "/v1/works?rows=10&sort=published&order=asc&select=DOI%2Ctitle%2Cpublisher%2Ctype%2Cpublished%2Ccreated%2CURL",
        "headers": (
            ("Accept", MEDIA_TYPE),
            ("Accept-Encoding", "identity"),
            (
                "User-Agent",
                "PastilaScout-CrossrefPilot (+https://github.com/acidburn1danny/pastila-news-monitor)",
            ),
        ),
        "body": None,
        "timeout_seconds": 15,
        "maximum_attempts": 1,
        "maximum_redirects": 0,
        "maximum_pages": 1,
    }
    assert len(frozen_request_identity_v1()) == 64


def test_transport_is_called_exactly_once_and_raw_components_are_identity_bound() -> (
    None
):
    calls = []
    response = FakeResponse(body([item()]))

    def transport(request):
        calls.append(request)
        return response

    raw = execute_one_shot_capture_v1(transport)
    assert calls == [FROZEN_REQUEST]
    assert raw.body == body([item()])
    assert len(raw.body_sha256) == len(raw.headers_sha256) == len(raw.identity) == 64
    assert response.read_amounts[-1] > 0


def test_body_limit_is_enforced_during_read_at_first_excess_byte() -> None:
    response = FakeResponse(b"x" * (MAXIMUM_RESPONSE_BODY_BYTES + 1))
    calls = 0

    def transport(_request):
        nonlocal calls
        calls += 1
        return response

    with pytest.raises(ResponseBodyLimitExceeded, match="2097152"):
        execute_one_shot_capture_v1(transport)
    assert calls == 1
    assert sum(response.read_amounts) >= MAXIMUM_RESPONSE_BODY_BYTES + 1


@pytest.mark.parametrize(
    ("status", "content_type"),
    [
        (301, MEDIA_TYPE),
        (429, MEDIA_TYPE),
        (500, MEDIA_TYPE),
        (200, "application/json"),
    ],
)
def test_status_redirect_rate_limit_server_error_and_media_type_fail_closed(
    status: int, content_type: str
) -> None:
    with pytest.raises(ResponseProfileRejected):
        normalize_capture_v1(
            capture(body([]), status=status, content_type=content_type)
        )


def test_duplicate_or_parameterized_content_type_is_rejected() -> None:
    duplicate = RawResponseCaptureV1(
        200,
        (("Content-Type", MEDIA_TYPE), ("content-type", MEDIA_TYPE)),
        body([]),
    )
    with pytest.raises(ResponseProfileRejected):
        normalize_capture_v1(duplicate)
    with pytest.raises(ResponseProfileRejected):
        normalize_capture_v1(
            capture(body([]), content_type=f"{MEDIA_TYPE}; charset=utf-8")
        )


def test_normalization_fills_absent_optional_fields_with_explicit_null() -> None:
    result = normalize_capture_v1(capture(body([{"DOI": "10.1234/minimal"}])))
    assert result.records[0].as_dict() == {
        "DOI": "10.1234/minimal",
        "title": None,
        "publisher": None,
        "type": None,
        "published": None,
        "created": None,
        "URL": None,
    }
    assert (
        result.raw_capture_identity
        == capture(body([{"DOI": "10.1234/minimal"}])).identity
    )


@pytest.mark.parametrize(
    "invalid",
    [
        {},
        {"DOI": ""},
        {"DOI": 7},
        item(title="Title"),
        item(title=["ok", 7]),
        item(publisher=7),
        item(type=[]),
        item(published=[]),
        item(created="yesterday"),
        item(URL=7),
    ],
)
def test_wrong_types_or_missing_doi_reject_entire_normalization(invalid) -> None:
    valid = item(DOI="10.1234/valid")
    raw = capture(body([valid, invalid]))
    with pytest.raises(NormalizationRejected, match="item 1"):
        normalize_capture_v1(raw)
    assert raw.body == body([valid, invalid])
    assert len(raw.identity) == 64


def test_more_than_ten_items_rejects_entire_set_without_partial_output() -> None:
    with pytest.raises(NormalizationRejected, match="more than 10"):
        normalize_capture_v1(capture(body([item(DOI=f"10.1/{n}") for n in range(11)])))


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"[]",
        b'{"message":null}',
        b'{"message":{"items":null}}',
        b'{"message":{"items":[],"items":[]}}',
        b'{"message":{"items":[]},"value":NaN}',
        b"\xff",
    ],
)
def test_malformed_utf8_json_envelope_duplicates_and_nonfinite_values_fail_closed(
    payload: bytes,
) -> None:
    with pytest.raises(NormalizationRejected):
        normalize_capture_v1(capture(payload))


def test_raw_and_normalized_identity_domains_are_separate_and_deterministic() -> None:
    raw = capture(body([item()]))
    first = normalize_capture_v1(raw)
    second = normalize_capture_v1(raw)
    assert first.canonical_bytes == second.canonical_bytes
    assert first.identity == second.identity
    assert first.identity != raw.identity != raw.body_sha256


def test_nested_normalized_values_cannot_mutate_the_accepted_identity() -> None:
    result = normalize_capture_v1(capture(body([item()])))
    identity = result.identity
    projected = result.records[0].as_dict()
    projected["title"].append("substitution")
    projected["published"]["date-parts"][0][0] = 1900
    assert result.identity == identity
    assert result.records[0].as_dict()["title"] == ["Title"]
    assert result.records[0].as_dict()["published"] == {"date-parts": [[2000, 1, 1]]}


def test_public_identity_objects_reject_mutable_or_forged_components() -> None:
    with pytest.raises(TypeError, match="immutable bytes"):
        RawResponseCaptureV1(200, (("Content-Type", MEDIA_TYPE),), bytearray(b"{}"))
    with pytest.raises(TypeError, match="immutable string pairs"):
        RawResponseCaptureV1(200, [["Content-Type", MEDIA_TYPE]], b"{}")
    with pytest.raises(TypeError, match="immutable string tuple"):
        NormalizedRecordV1("10.1/x", ["mutable"], None, None, None, None, None)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        NormalizedRecordSetV1("not-an-identity", ())


def test_module_has_no_default_network_client_or_execution_on_import() -> None:
    import pastila_scout.crossref_pilot_offline_v1 as module

    assert "httpx" not in module.__dict__
    assert "requests" not in module.__dict__
    assert "http" not in module.__dict__
    assert "urllib" not in module.__dict__
