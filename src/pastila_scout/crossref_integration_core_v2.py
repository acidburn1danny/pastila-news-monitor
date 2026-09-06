"""Provider-bound, specimen-neutral Crossref admission semantics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, cast

NORMALIZED_SCHEMA_V1 = "pastila-crossref-pilot-offline-v1"
INTEGRATION_SCHEMA_V2 = "pastila-crossref-capture-integration-v2"
STATE_SCHEMA_V2 = "pastila-crossref-integration-state-v2"
QUARANTINE_SCHEMA_V2 = "pastila-crossref-integration-quarantine-v2"
_RECORD_FIELDS = frozenset(
    {"DOI", "URL", "created", "published", "publisher", "title", "type"}
)


class CrossrefAdmissionRejected(ValueError):
    """The immutable admission boundary itself is invalid."""


@dataclass(frozen=True, slots=True)
class CrossrefAdmissionProfileV2:
    """Owner/profile-layer inputs consumed by the reusable mechanism."""

    normalized_schema: str
    maximum_records: int

    def __post_init__(self) -> None:
        if type(self.normalized_schema) is not str or not self.normalized_schema:
            raise CrossrefAdmissionRejected("normalized schema must be non-empty")
        if type(self.maximum_records) is not int or self.maximum_records < 1:
            raise CrossrefAdmissionRejected("maximum records must be positive")


@dataclass(frozen=True, slots=True)
class CanonicalJsonObjectV2:
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        value = _decode_json(self.canonical_bytes)
        if not isinstance(value, dict) or _canonical(value) != self.canonical_bytes:
            raise CrossrefAdmissionRejected("nested object is not canonical")

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self.canonical_bytes))


@dataclass(frozen=True, slots=True)
class CrossrefIntegratedRecordV2:
    DOI: str
    doi_key: str
    title: tuple[str, ...] | None
    publisher: str | None
    type: str | None
    published: CanonicalJsonObjectV2 | None
    created: CanonicalJsonObjectV2 | None
    URL: str | None
    source_ordinal: int
    raw_capture_identity: str
    normalized_identity: str

    def __post_init__(self) -> None:
        if type(self.DOI) is not str or not self.DOI:
            raise CrossrefAdmissionRejected("DOI must be a non-empty string")
        if type(self.doi_key) is not str or self.doi_key != self.DOI.casefold():
            raise CrossrefAdmissionRejected("DOI key is not canonical")
        if self.title is not None and (
            type(self.title) is not tuple
            or any(type(value) is not str for value in self.title)
        ):
            raise CrossrefAdmissionRejected("title is not immutable strings")
        if any(
            value is not None and type(value) is not str
            for value in (self.publisher, self.type, self.URL)
        ):
            raise CrossrefAdmissionRejected("optional string is invalid")
        if any(
            value is not None and type(value) is not CanonicalJsonObjectV2
            for value in (self.published, self.created)
        ):
            raise CrossrefAdmissionRejected("optional object is invalid")
        if type(self.source_ordinal) is not int or self.source_ordinal < 0:
            raise CrossrefAdmissionRejected("source ordinal is invalid")
        _require_sha256(self.raw_capture_identity, "raw capture identity")
        _require_sha256(self.normalized_identity, "normalized identity")

    def as_dict(self) -> dict[str, object]:
        return {
            "DOI": self.DOI,
            "URL": self.URL,
            "created": None if self.created is None else self.created.as_dict(),
            "doi_key": self.doi_key,
            "normalized_identity": self.normalized_identity,
            "published": None if self.published is None else self.published.as_dict(),
            "publisher": self.publisher,
            "raw_capture_identity": self.raw_capture_identity,
            "source_ordinal": self.source_ordinal,
            "title": None if self.title is None else list(self.title),
            "type": self.type,
        }

    @property
    def identity(self) -> str:
        return hashlib.sha256(_canonical(self.as_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationBatchV2:
    raw_capture_identity: str
    normalized_identity: str
    records: tuple[CrossrefIntegratedRecordV2, ...]

    def __post_init__(self) -> None:
        _require_sha256(self.raw_capture_identity, "raw capture identity")
        _require_sha256(self.normalized_identity, "normalized identity")
        if type(self.records) is not tuple or any(
            type(record) is not CrossrefIntegratedRecordV2 for record in self.records
        ):
            raise CrossrefAdmissionRejected("batch records are not immutable")
        keys = tuple(record.doi_key for record in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise CrossrefAdmissionRejected("batch DOI keys are not canonical")
        if any(
            record.raw_capture_identity != self.raw_capture_identity
            or record.normalized_identity != self.normalized_identity
            for record in self.records
        ):
            raise CrossrefAdmissionRejected("batch provenance is inconsistent")

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "normalized_identity": self.normalized_identity,
                "raw_capture_identity": self.raw_capture_identity,
                "record_identities": [record.identity for record in self.records],
                "records": [record.as_dict() for record in self.records],
                "schema": INTEGRATION_SCHEMA_V2,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationStateV2:
    records: tuple[CrossrefIntegratedRecordV2, ...] = ()
    applied_batch_identities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not CrossrefIntegratedRecordV2 for record in self.records
        ):
            raise CrossrefAdmissionRejected("state records are not immutable")
        keys = tuple(record.doi_key for record in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise CrossrefAdmissionRejected("state DOI keys are not canonical")
        if self.applied_batch_identities != tuple(
            sorted(set(self.applied_batch_identities))
        ):
            raise CrossrefAdmissionRejected("batch identities are not canonical")
        for identity in self.applied_batch_identities:
            _require_sha256(identity, "batch identity")

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "applied_batch_identities": list(self.applied_batch_identities),
                "record_identities": [record.identity for record in self.records],
                "records": [record.as_dict() for record in self.records],
                "schema": STATE_SCHEMA_V2,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationQuarantineV2:
    reason_codes: tuple[str, ...]
    input_sha256: str
    state_identity: str

    def __post_init__(self) -> None:
        if (
            type(self.reason_codes) is not tuple
            or not self.reason_codes
            or any(
                type(reason) is not str or not reason for reason in self.reason_codes
            )
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise CrossrefAdmissionRejected("quarantine reasons are not canonical")
        _require_sha256(self.input_sha256, "input identity")
        _require_sha256(self.state_identity, "state identity")

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "input_sha256": self.input_sha256,
                "reason_codes": list(self.reason_codes),
                "schema": QUARANTINE_SCHEMA_V2,
                "state_after_identity": self.state_identity,
                "state_before_identity": self.state_identity,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationResultV2:
    disposition: Literal["ACCEPTED", "IDEMPOTENT_REPLAY", "QUARANTINED"]
    state: CrossrefIntegrationStateV2
    batch: CrossrefIntegrationBatchV2 | None = None
    quarantine: CrossrefIntegrationQuarantineV2 | None = None

    def __post_init__(self) -> None:
        if self.disposition not in {"ACCEPTED", "IDEMPOTENT_REPLAY", "QUARANTINED"}:
            raise CrossrefAdmissionRejected("result disposition is invalid")
        if type(self.state) is not CrossrefIntegrationStateV2:
            raise CrossrefAdmissionRejected("result state is invalid")
        accepted = self.disposition != "QUARANTINED"
        if accepted != (type(self.batch) is CrossrefIntegrationBatchV2):
            raise CrossrefAdmissionRejected("result batch is inconsistent")
        if accepted == (type(self.quarantine) is CrossrefIntegrationQuarantineV2):
            raise CrossrefAdmissionRejected("result quarantine is inconsistent")
        if accepted and cast(CrossrefIntegrationBatchV2, self.batch).identity not in (
            self.state.applied_batch_identities
        ):
            raise CrossrefAdmissionRejected("accepted batch is absent from state")
        if self.quarantine is not None and (
            self.quarantine.state_identity != self.state.identity
        ):
            raise CrossrefAdmissionRejected("quarantine changed state")


def integrate_crossref_normalized_bytes_v2(
    profile: CrossrefAdmissionProfileV2,
    state: CrossrefIntegrationStateV2,
    payload: bytes,
) -> CrossrefIntegrationResultV2:
    """Admit any canonical specimen satisfying the supplied Crossref profile."""

    if type(profile) is not CrossrefAdmissionProfileV2:
        raise TypeError("profile must be an exact immutable authority")
    if type(state) is not CrossrefIntegrationStateV2 or type(payload) is not bytes:
        raise TypeError("state and payload must be exact immutable boundary types")
    input_identity = hashlib.sha256(payload).hexdigest()
    reasons: set[str] = set()
    document = _decode_document(payload, reasons)
    records: list[CrossrefIntegratedRecordV2] = []
    raw_identity: str | None = None
    if document is not None:
        if document.get("schema") != profile.normalized_schema:
            reasons.add("NORMALIZED_SCHEMA_MISMATCH")
        raw_value = document.get("raw_capture_identity")
        if _is_sha256(raw_value):
            raw_identity = cast(str, raw_value)
        else:
            reasons.add("RAW_CAPTURE_IDENTITY_INVALID")
        values = document.get("records")
        if not isinstance(values, list) or len(values) > profile.maximum_records:
            reasons.add("RECORD_SET_INVALID")
        elif raw_identity is not None:
            for ordinal, value in enumerate(values):
                record = _map_record(
                    value, ordinal, raw_identity, input_identity, reasons
                )
                if record is not None:
                    records.append(record)
    keys = [record.doi_key for record in records]
    if len(keys) != len(set(keys)):
        reasons.add("DUPLICATE_DOI")
    batch = None
    if not reasons and raw_identity is not None:
        batch = CrossrefIntegrationBatchV2(
            raw_identity,
            input_identity,
            tuple(sorted(records, key=lambda record: record.doi_key)),
        )
        if batch.identity in state.applied_batch_identities:
            return CrossrefIntegrationResultV2("IDEMPOTENT_REPLAY", state, batch)
        if set(keys).intersection(record.doi_key for record in state.records):
            reasons.add("DOI_STATE_CONFLICT")
    if reasons:
        quarantine = CrossrefIntegrationQuarantineV2(
            tuple(sorted(reasons)), input_identity, state.identity
        )
        return CrossrefIntegrationResultV2("QUARANTINED", state, quarantine=quarantine)
    assert batch is not None
    next_state = CrossrefIntegrationStateV2(
        tuple(
            sorted((*state.records, *batch.records), key=lambda record: record.doi_key)
        ),
        tuple(sorted((*state.applied_batch_identities, batch.identity))),
    )
    return CrossrefIntegrationResultV2("ACCEPTED", next_state, batch)


def _decode_document(payload: bytes, reasons: set[str]) -> dict[str, object] | None:
    try:
        value = _decode_json(payload)
    except CrossrefAdmissionRejected:
        reasons.add("NORMALIZED_BYTES_MALFORMED")
        return None
    if not isinstance(value, dict) or _canonical(value) != payload:
        reasons.add("NORMALIZED_BYTES_NONCANONICAL")
        return None
    if set(value) != {"raw_capture_identity", "records", "schema"}:
        reasons.add("NORMALIZED_DOCUMENT_SHAPE_INVALID")
    return cast(dict[str, object], value)


def _decode_json(payload: bytes) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate member")
            result[key] = value
        return result

    try:
        return json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid constant {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CrossrefAdmissionRejected("payload is not strict JSON") from error


def _map_record(
    value: object,
    ordinal: int,
    raw_identity: str,
    normalized_identity: str,
    reasons: set[str],
) -> CrossrefIntegratedRecordV2 | None:
    if not isinstance(value, dict) or set(value) != _RECORD_FIELDS:
        reasons.add("RECORD_SHAPE_INVALID")
        return None
    doi = value.get("DOI")
    title = value.get("title")
    strings = (value.get("publisher"), value.get("type"), value.get("URL"))
    objects = (value.get("published"), value.get("created"))
    if not isinstance(doi, str) or not doi:
        reasons.add("DOI_INVALID")
        return None
    if title is not None and (
        not isinstance(title, list) or any(type(item) is not str for item in title)
    ):
        reasons.add("RECORD_FIELD_TYPE_INVALID")
        return None
    if any(item is not None and type(item) is not str for item in strings) or any(
        item is not None and not isinstance(item, dict) for item in objects
    ):
        reasons.add("RECORD_FIELD_TYPE_INVALID")
        return None
    return CrossrefIntegratedRecordV2(
        doi,
        doi.casefold(),
        None if title is None else tuple(title),
        cast(str | None, value.get("publisher")),
        cast(str | None, value.get("type")),
        _optional_object(value.get("published")),
        _optional_object(value.get("created")),
        cast(str | None, value.get("URL")),
        ordinal,
        raw_identity,
        normalized_identity,
    )


def _optional_object(value: object) -> CanonicalJsonObjectV2 | None:
    return None if value is None else CanonicalJsonObjectV2(_canonical(value))


def _canonical(value: object) -> bytes:
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


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_sha256(value: object, field: str) -> None:
    if not _is_sha256(value):
        raise CrossrefAdmissionRejected(f"{field} is not lowercase SHA-256")


__all__ = (
    "NORMALIZED_SCHEMA_V1",
    "CanonicalJsonObjectV2",
    "CrossrefAdmissionProfileV2",
    "CrossrefAdmissionRejected",
    "CrossrefIntegratedRecordV2",
    "CrossrefIntegrationBatchV2",
    "CrossrefIntegrationQuarantineV2",
    "CrossrefIntegrationResultV2",
    "CrossrefIntegrationStateV2",
    "integrate_crossref_normalized_bytes_v2",
)
