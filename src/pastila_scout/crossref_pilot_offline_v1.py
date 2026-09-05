"""Offline implementation of the frozen bounded Crossref pilot authority."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Protocol, cast

SCHEMA = "pastila-crossref-pilot-offline-v1"
ENDPOINT = "https://api.crossref.org/v1/works"
REQUEST_TARGET = (
    "/v1/works?rows=10&sort=published&order=asc&select="
    "DOI%2Ctitle%2Cpublisher%2Ctype%2Cpublished%2Ccreated%2CURL"
)
USER_AGENT = (
    "PastilaScout-CrossrefPilot "
    "(+https://github.com/acidburn1danny/pastila-news-monitor)"
)
MEDIA_TYPE = "application/vnd.crossref-api-message+json"
MAXIMUM_RESPONSE_BODY_BYTES = 2_097_152
MAXIMUM_RECORDS = 10
READ_CHUNK_BYTES = 65_536


class CrossrefPilotFailure(ValueError):
    """Terminal failure in the one-shot pilot boundary."""


class ResponseBodyLimitExceeded(CrossrefPilotFailure):
    """The response produced a byte beyond the frozen limit."""


class ResponseProfileRejected(CrossrefPilotFailure):
    """The captured HTTP response does not match the frozen profile."""


class NormalizationRejected(CrossrefPilotFailure):
    """The complete response cannot be normalized without coercion or loss."""


@dataclass(frozen=True, slots=True)
class FrozenRequestV1:
    """Exact request bytes and controls passed to the future transport adapter."""

    scheme: str = "https"
    host: str = "api.crossref.org"
    port: int = 443
    method: str = "GET"
    target: str = REQUEST_TARGET
    headers: tuple[tuple[str, str], ...] = (
        ("Accept", MEDIA_TYPE),
        ("Accept-Encoding", "identity"),
        ("User-Agent", USER_AGENT),
    )
    body: None = None
    timeout_seconds: int = 15
    maximum_attempts: int = 1
    maximum_redirects: int = 0
    maximum_pages: int = 1


FROZEN_REQUEST = FrozenRequestV1()


class ResponseStream(Protocol):
    """Minimum response surface; deliberately has no redirect/retry operations."""

    status: int

    def getheaders(self) -> list[tuple[str, str]]: ...

    def read(self, amount: int) -> bytes: ...


TransportOnce = Callable[[FrozenRequestV1], ResponseStream]


@dataclass(frozen=True, slots=True)
class RawResponseCaptureV1:
    """Exact response components retained separately from normalized records."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def __post_init__(self) -> None:
        if type(self.status) is not int:
            raise TypeError("raw status must be an integer")
        if type(self.headers) is not tuple or any(
            type(pair) is not tuple
            or len(pair) != 2
            or any(type(value) is not str for value in pair)
            for pair in self.headers
        ):
            raise TypeError("raw headers must be immutable string pairs")
        if type(self.body) is not bytes:
            raise TypeError("raw body must be immutable bytes")

    @property
    def body_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def headers_sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.headers)).hexdigest()

    @property
    def identity(self) -> str:
        envelope = {
            "body_sha256": self.body_sha256,
            "headers": self.headers,
            "status": self.status,
        }
        return hashlib.sha256(_canonical_json_bytes(envelope)).hexdigest()


@dataclass(frozen=True, slots=True)
class CanonicalJsonObjectV1:
    """Immutable canonical encoding of a JSON object."""

    canonical_bytes: bytes

    def __post_init__(self) -> None:
        try:
            value = json.loads(self.canonical_bytes)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TypeError("canonical object bytes must contain JSON") from exc
        if (
            not isinstance(value, dict)
            or _canonical_json_bytes(value) != self.canonical_bytes
        ):
            raise ValueError("object bytes are not canonical")

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self.canonical_bytes))


@dataclass(frozen=True, slots=True)
class NormalizedRecordV1:
    DOI: str
    title: tuple[str, ...] | None
    publisher: str | None
    type: str | None
    published: CanonicalJsonObjectV1 | None
    created: CanonicalJsonObjectV1 | None
    URL: str | None

    def __post_init__(self) -> None:
        if type(self.DOI) is not str or self.DOI == "":
            raise TypeError("normalized DOI must be a non-empty string")
        if self.title is not None and (
            type(self.title) is not tuple
            or any(type(value) is not str for value in self.title)
        ):
            raise TypeError("normalized title must be an immutable string tuple")
        for name in ("publisher", "type", "URL"):
            value = getattr(self, name)
            if value is not None and type(value) is not str:
                raise TypeError(f"normalized {name} must be a string or null")
        for name in ("published", "created"):
            value = getattr(self, name)
            if value is not None and type(value) is not CanonicalJsonObjectV1:
                raise TypeError(f"normalized {name} must be a canonical object or null")

    def as_dict(self) -> dict[str, object]:
        return {
            "DOI": self.DOI,
            "title": None if self.title is None else list(self.title),
            "publisher": self.publisher,
            "type": self.type,
            "published": None if self.published is None else self.published.as_dict(),
            "created": None if self.created is None else self.created.as_dict(),
            "URL": self.URL,
        }


@dataclass(frozen=True, slots=True)
class NormalizedRecordSetV1:
    raw_capture_identity: str
    records: tuple[NormalizedRecordV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.raw_capture_identity) is not str
            or len(self.raw_capture_identity) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.raw_capture_identity
            )
        ):
            raise ValueError("raw capture identity must be lowercase SHA-256")
        if type(self.records) is not tuple or any(
            type(record) is not NormalizedRecordV1 for record in self.records
        ):
            raise TypeError("normalized records must be an immutable record tuple")

    @property
    def canonical_bytes(self) -> bytes:
        value = {
            "raw_capture_identity": self.raw_capture_identity,
            "records": [record.as_dict() for record in self.records],
            "schema": SCHEMA,
        }
        return _canonical_json_bytes(value)

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


def frozen_request_identity_v1() -> str:
    """Return the identity of the only request accepted by this implementation."""

    return hashlib.sha256(_canonical_json_bytes(asdict(FROZEN_REQUEST))).hexdigest()


def execute_one_shot_capture_v1(transport_once: TransportOnce) -> RawResponseCaptureV1:
    """Invoke one supplied transport exactly once and capture its response bytes."""

    response = transport_once(FROZEN_REQUEST)
    if isinstance(response.status, bool) or not isinstance(response.status, int):
        raise ResponseProfileRejected("HTTP status must be an integer")
    headers = _capture_headers(response.getheaders())
    body = _read_bounded_body(response)
    return RawResponseCaptureV1(response.status, headers, body)


def validate_response_profile_v1(capture: RawResponseCaptureV1) -> None:
    """Require the exact successful response profile before JSON parsing."""

    if capture.status != 200:
        raise ResponseProfileRejected("HTTP status is not 200")
    content_types = [
        value for name, value in capture.headers if name.casefold() == "content-type"
    ]
    if len(content_types) != 1 or content_types[0].strip().casefold() != MEDIA_TYPE:
        raise ResponseProfileRejected("Content-Type is not the frozen media type")


def normalize_capture_v1(capture: RawResponseCaptureV1) -> NormalizedRecordSetV1:
    """Normalize all items atomically; never return a partial record set."""

    validate_response_profile_v1(capture)
    document = _decode_json_object(capture.body)
    message = document.get("message")
    if not isinstance(message, dict):
        raise NormalizationRejected("response.message must be an object")
    items = message.get("items")
    if not isinstance(items, list):
        raise NormalizationRejected("response.message.items must be an array")
    if len(items) > MAXIMUM_RECORDS:
        raise NormalizationRejected("response contains more than 10 items")

    records = tuple(_normalize_item(item, index) for index, item in enumerate(items))
    return NormalizedRecordSetV1(capture.identity, records)


def _capture_headers(values: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, list):
        raise ResponseProfileRejected("response headers must be a list")
    captured: list[tuple[str, str]] = []
    for pair in values:
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or not all(isinstance(value, str) for value in pair)
        ):
            raise ResponseProfileRejected("response header pair is malformed")
        captured.append(pair)
    return tuple(captured)


def _read_bounded_body(response: ResponseStream) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining_with_sentinel = MAXIMUM_RESPONSE_BODY_BYTES - total + 1
        chunk = response.read(min(READ_CHUNK_BYTES, remaining_with_sentinel))
        if not isinstance(chunk, bytes):
            raise ResponseProfileRejected("response stream returned non-bytes")
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAXIMUM_RESPONSE_BODY_BYTES:
            raise ResponseBodyLimitExceeded("response body exceeds 2097152 bytes")
        chunks.append(chunk)


def _decode_json_object(body: bytes) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise NormalizationRejected(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise NormalizationRejected(f"non-finite JSON value: {value}")

    try:
        value = json.loads(
            body.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NormalizationRejected("response is not canonical UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise NormalizationRejected("response root must be an object")
    return value


def _normalize_item(value: object, index: int) -> NormalizedRecordV1:
    if not isinstance(value, Mapping):
        raise NormalizationRejected(f"item {index}: must be an object")

    doi = value.get("DOI")
    if not isinstance(doi, str) or doi == "":
        raise NormalizationRejected(f"item {index}: DOI must be a non-empty string")

    title = _optional_title(value.get("title"), index)
    publisher = _optional_string(value.get("publisher"), "publisher", index)
    work_type = _optional_string(value.get("type"), "type", index)
    published = _optional_object(value.get("published"), "published", index)
    created = _optional_object(value.get("created"), "created", index)
    url = _optional_string(value.get("URL"), "URL", index)
    return NormalizedRecordV1(
        DOI=doi,
        title=title,
        publisher=publisher,
        type=work_type,
        published=published,
        created=created,
        URL=url,
    )


def _optional_title(value: object, index: int) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise NormalizationRejected(
            f"item {index}: title must be array[string] or null"
        )
    return tuple(value)


def _optional_string(value: object, field: str, index: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise NormalizationRejected(f"item {index}: {field} must be string or null")
    return value


def _optional_object(
    value: object, field: str, index: int
) -> CanonicalJsonObjectV1 | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise NormalizationRejected(f"item {index}: {field} must be object or null")
    return CanonicalJsonObjectV1(_canonical_json_bytes(value))


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


__all__ = (
    "ENDPOINT",
    "FROZEN_REQUEST",
    "MAXIMUM_RECORDS",
    "MAXIMUM_RESPONSE_BODY_BYTES",
    "MEDIA_TYPE",
    "REQUEST_TARGET",
    "SCHEMA",
    "USER_AGENT",
    "CanonicalJsonObjectV1",
    "CrossrefPilotFailure",
    "FrozenRequestV1",
    "NormalizationRejected",
    "NormalizedRecordSetV1",
    "NormalizedRecordV1",
    "RawResponseCaptureV1",
    "ResponseBodyLimitExceeded",
    "ResponseProfileRejected",
    "execute_one_shot_capture_v1",
    "frozen_request_identity_v1",
    "normalize_capture_v1",
    "validate_response_profile_v1",
)
