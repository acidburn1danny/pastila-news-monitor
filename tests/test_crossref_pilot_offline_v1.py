"""Adversarial offline tests for the bounded Crossref pilot implementation."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from pastila_scout.crossref_pilot_offline_v1 import (
    FROZEN_REQUEST,
    MAXIMUM_RESPONSE_BODY_BYTES,
    MEDIA_TYPE,
    DirectCrossrefHttpsTransportV1,
    NormalizationRejected,
    NormalizedRecordSetV1,
    NormalizedRecordV1,
    RawResponseCaptureV1,
    ResponseBodyLimitExceeded,
    ResponseProfileRejected,
    execute_one_shot_capture_v1,
    execute_record_then_normalize_v1,
    frozen_request_identity_v1,
    normalize_capture_v1,
    record_raw_capture_v1,
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
        self.closed = False

    def getheaders(self) -> list[tuple[str, str]]:
        return list(self._headers)

    def read(self, amount: int) -> bytes:
        self.read_amounts.append(amount)
        chunk = self._body[self._offset : self._offset + amount]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


def body(items: list[object]) -> bytes:
    return json.dumps(
        {
            "status": "ok",
            "message-type": "work-list",
            "message-version": "1.0.0",
            "message": {"items": items},
        },
        separators=(",", ":"),
    ).encode()


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
    return RawResponseCaptureV1(
        frozen_request_identity_v1(),
        status,
        (("Content-Type", content_type),),
        payload,
    )


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
    assert response.closed is True


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
        frozen_request_identity_v1(),
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
    encoded = RawResponseCaptureV1(
        frozen_request_identity_v1(),
        200,
        (("Content-Type", MEDIA_TYPE), ("Content-Encoding", "gzip")),
        body([]),
    )
    with pytest.raises(ResponseProfileRejected, match="Content-Encoding"):
        normalize_capture_v1(encoded)


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
        RawResponseCaptureV1(
            frozen_request_identity_v1(),
            200,
            (("Content-Type", MEDIA_TYPE),),
            bytearray(b"{}"),
        )
    with pytest.raises(TypeError, match="immutable string pairs"):
        RawResponseCaptureV1(
            frozen_request_identity_v1(), 200, [["Content-Type", MEDIA_TYPE]], b"{}"
        )
    with pytest.raises(TypeError, match="immutable string tuple"):
        NormalizedRecordV1("10.1/x", ["mutable"], None, None, None, None, None)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        NormalizedRecordSetV1("not-an-identity", ())


def test_module_request_binding_replacement_cannot_redirect_transport(
    monkeypatch,
) -> None:
    import pastila_scout.crossref_pilot_offline_v1 as module

    monkeypatch.setattr(
        module, "FROZEN_REQUEST", module.FrozenRequestV1(host="example.invalid")
    )
    seen = []
    execute_one_shot_capture_v1(
        lambda request: seen.append(request) or FakeResponse(body([]))
    )
    assert seen == [module.FrozenRequestV1()]


def test_capture_request_binding_and_public_record_ceiling_fail_closed() -> None:
    wrong = RawResponseCaptureV1(
        "0" * 64, 200, (("Content-Type", MEDIA_TYPE),), body([])
    )
    with pytest.raises(ResponseProfileRejected, match="frozen request"):
        normalize_capture_v1(wrong)
    record = NormalizedRecordV1("10.1/x", None, None, None, None, None, None)
    with pytest.raises(ValueError, match="more than 10"):
        NormalizedRecordSetV1("0" * 64, (record,) * 11)


@pytest.mark.parametrize(
    "updates",
    [
        {"status": "error"},
        {"message-type": "wrong"},
        {"message-version": ""},
        {"message-version": None},
    ],
)
def test_crossref_envelope_authority_is_exact(updates: dict[str, object]) -> None:
    document = json.loads(body([]))
    document.update(updates)
    with pytest.raises(NormalizationRejected):
        normalize_capture_v1(capture(json.dumps(document).encode()))


def test_direct_https_adapter_is_single_use_exact_and_closes(monkeypatch) -> None:
    import pastila_scout.crossref_pilot_offline_v1 as module

    events = []

    class Connection:
        def __init__(self, host, port, *, timeout, context):
            events.append(
                (
                    "connect",
                    host,
                    port,
                    timeout,
                    context.check_hostname,
                    context.verify_mode,
                )
            )

        def putrequest(self, method, target, *, skip_accept_encoding):
            events.append(("request", method, target, skip_accept_encoding))

        def putheader(self, name, value):
            events.append(("header", name, value))

        def endheaders(self):
            events.append(("end",))

        def getresponse(self):
            response = FakeResponse(body([]))
            response._headers = [("Content-Type", MEDIA_TYPE)]
            return response

        def close(self):
            events.append(("close",))

    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    adapter = DirectCrossrefHttpsTransportV1()
    raw = execute_one_shot_capture_v1(adapter)
    assert raw.request_identity == frozen_request_identity_v1()
    assert events[0][0:4] == ("connect", "api.crossref.org", 443, 15)
    assert events[1] == ("request", "GET", FROZEN_REQUEST.target, True)
    assert [event[1:] for event in events if event[0] == "header"] == list(
        FROZEN_REQUEST.headers
    )
    assert events[-1] == ("close",)
    with pytest.raises(Exception, match="single-use"):
        adapter(FROZEN_REQUEST)


def test_raw_capture_is_durably_recorded_before_normalization(tmp_path: Path) -> None:
    raw = capture(body([item()]))
    destination = tmp_path / "raw-capture"
    assert record_raw_capture_v1(destination, raw) == raw.identity
    assert (destination / "response-body.bin").read_bytes() == raw.body
    manifest = json.loads((destination / "manifest.json").read_bytes())
    assert manifest["capture_identity"] == raw.identity
    assert manifest["request_identity"] == frozen_request_identity_v1()
    with pytest.raises(Exception, match="new Path"):
        record_raw_capture_v1(destination, raw)


def test_closed_lifecycle_records_raw_before_terminal_normalization_failure(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "failed-normalization-raw"
    response = FakeResponse(body([{"DOI": 7}]))
    with pytest.raises(NormalizationRejected):
        execute_record_then_normalize_v1(lambda _request: response, destination)
    assert (destination / "response-body.bin").read_bytes() == body([{"DOI": 7}])
    assert response.closed is True


def test_writer_rejects_capture_from_another_request(tmp_path: Path) -> None:
    wrong = RawResponseCaptureV1(
        "0" * 64,
        200,
        (("Content-Type", MEDIA_TYPE),),
        body([]),
    )
    with pytest.raises(Exception, match="frozen request"):
        record_raw_capture_v1(tmp_path / "wrong", wrong)
    assert not (tmp_path / "wrong").exists()


def test_module_has_no_default_network_client_or_execution_on_import() -> None:
    import pastila_scout.crossref_pilot_offline_v1 as module

    assert "httpx" not in module.__dict__
    assert "requests" not in module.__dict__
    assert "urllib" not in module.__dict__
    assert module.DirectCrossrefHttpsTransportV1 is DirectCrossrefHttpsTransportV1
