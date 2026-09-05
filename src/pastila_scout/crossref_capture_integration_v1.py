"""Offline, atomic integration of a qualified Crossref capture into Core V2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, cast

INTEGRATION_SCHEMA = "pastila-crossref-capture-integration-v1"
STATE_SCHEMA = "pastila-crossref-integration-state-v1"
QUARANTINE_SCHEMA = "pastila-crossref-integration-quarantine-v1"
_NORMALIZED_SCHEMA = "pastila-crossref-pilot-offline-v1"
PHASE2_PROOF_COMMIT = "82f1cf1c681e014e73208fa32e5e4ed78d3f963a"
PHASE2_RAW_CAPTURE_IDENTITY = (
    "3acbdb9f2e54940f5953b497ace279a5884d0ce607f4e77e868de9a667783281"
)
PHASE2_NORMALIZED_IDENTITY = (
    "bc2dd86d76c89f9e39f4a99a72db87ef57a5835ea92533a02f942ecc1111f4e0"
)
PHASE3_EMPTY_STATE_IDENTITY = (
    "62846329a1f032711c76f5120705b4c9a1237b92d5de6e9e273da8f25b41475b"
)
PHASE3_ACCEPTED_STATE_IDENTITY = (
    "768ac0572117e39a3cc0f9f4b7d0a255ed116f33b4fd6f5653e09c091ac804d5"
)
_RECORD_FIELDS = {
    "DOI",
    "URL",
    "created",
    "published",
    "publisher",
    "title",
    "type",
}


class CrossrefIntegrationInputRejected(ValueError):
    """The supplied object is not a usable immutable input boundary."""


@dataclass(frozen=True, slots=True)
class _CanonicalJsonObjectV1:
    """Local immutable JSON object without importing the transport module."""

    canonical_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.canonical_bytes) is not bytes:
            raise CrossrefIntegrationInputRejected("canonical object is not bytes")
        try:
            value = json.loads(self.canonical_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CrossrefIntegrationInputRejected(
                "canonical object is not JSON"
            ) from error
        if (
            not isinstance(value, dict)
            or _canonical_json_bytes(value) != self.canonical_bytes
        ):
            raise CrossrefIntegrationInputRejected("canonical object is not canonical")

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self.canonical_bytes))


@dataclass(frozen=True, slots=True)
class CrossrefIntegratedRecordV1:
    """Provider-bound metadata record retaining exact capture provenance."""

    DOI: str
    doi_key: str
    title: tuple[str, ...] | None
    publisher: str | None
    type: str | None
    published: _CanonicalJsonObjectV1 | None
    created: _CanonicalJsonObjectV1 | None
    URL: str | None
    source_ordinal: int
    raw_capture_identity: str
    normalized_identity: str

    def __post_init__(self) -> None:
        if (
            type(self.DOI) is not str
            or not self.DOI
            or type(self.doi_key) is not str
            or self.doi_key != self.DOI.casefold()
        ):
            raise CrossrefIntegrationInputRejected("DOI key is not canonical")
        if self.title is not None and (
            type(self.title) is not tuple
            or any(type(value) is not str for value in self.title)
        ):
            raise CrossrefIntegrationInputRejected("title is not immutable strings")
        if any(
            value is not None and type(value) is not str
            for value in (self.publisher, self.type, self.URL)
        ):
            raise CrossrefIntegrationInputRejected("optional string is invalid")
        if any(
            value is not None and type(value) is not _CanonicalJsonObjectV1
            for value in (self.published, self.created)
        ):
            raise CrossrefIntegrationInputRejected("canonical object is invalid")
        if type(self.source_ordinal) is not int or self.source_ordinal < 0:
            raise CrossrefIntegrationInputRejected("source ordinal is negative")
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
        from hashlib import sha256

        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationBatchV1:
    """A complete capture mapped into deterministic Core V2 order."""

    raw_capture_identity: str
    normalized_identity: str
    records: tuple[CrossrefIntegratedRecordV1, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not CrossrefIntegratedRecordV1 for record in self.records
        ):
            raise CrossrefIntegrationInputRejected("batch records are not immutable")
        if len(self.records) > 10:
            raise CrossrefIntegrationInputRejected("batch exceeds record limit")
        _require_sha256(self.raw_capture_identity, "raw capture identity")
        _require_sha256(self.normalized_identity, "normalized identity")
        keys = tuple(record.doi_key for record in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise CrossrefIntegrationInputRejected(
                "integration records are not uniquely sorted by DOI"
            )
        if any(
            record.raw_capture_identity != self.raw_capture_identity
            or record.normalized_identity != self.normalized_identity
            for record in self.records
        ):
            raise CrossrefIntegrationInputRejected("record provenance is inconsistent")

    def as_dict(self) -> dict[str, object]:
        return {
            "normalized_identity": self.normalized_identity,
            "raw_capture_identity": self.raw_capture_identity,
            "record_identities": [record.identity for record in self.records],
            "records": [record.as_dict() for record in self.records],
            "schema": "pastila-crossref-capture-integration-v1",
        }

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.as_dict())

    @property
    def identity(self) -> str:
        from hashlib import sha256

        return sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationStateV1:
    """Immutable accepted Crossref metadata state."""

    records: tuple[CrossrefIntegratedRecordV1, ...] = ()
    applied_batch_identities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not CrossrefIntegratedRecordV1 for record in self.records
        ):
            raise CrossrefIntegrationInputRejected("state records are not immutable")
        if type(self.applied_batch_identities) is not tuple:
            raise CrossrefIntegrationInputRejected("batch identities are not immutable")
        keys = tuple(record.doi_key for record in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise CrossrefIntegrationInputRejected(
                "state records are not uniquely sorted by DOI"
            )
        if self.applied_batch_identities != tuple(
            sorted(set(self.applied_batch_identities))
        ):
            raise CrossrefIntegrationInputRejected(
                "applied batch identities are not canonical"
            )
        for identity in self.applied_batch_identities:
            _require_sha256(identity, "batch identity")

    def as_dict(self) -> dict[str, object]:
        return {
            "applied_batch_identities": list(self.applied_batch_identities),
            "record_identities": [record.identity for record in self.records],
            "records": [record.as_dict() for record in self.records],
            "schema": "pastila-crossref-integration-state-v1",
        }

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.as_dict())

    @property
    def identity(self) -> str:
        from hashlib import sha256

        return sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationQuarantineV1:
    """Deterministic evidence that a rejected integration changed no state."""

    reason_codes: tuple[str, ...]
    input_sha256: str
    expected_raw_capture_identity: str
    expected_normalized_identity: str
    state_before_identity: str
    state_after_identity: str

    def __post_init__(self) -> None:
        if (
            type(self.reason_codes) is not tuple
            or not self.reason_codes
            or any(
                type(reason) is not str or not reason for reason in self.reason_codes
            )
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise CrossrefIntegrationInputRejected(
                "quarantine reasons are not canonical"
            )
        for value, field in (
            (self.input_sha256, "input identity"),
            (self.expected_raw_capture_identity, "raw capture identity"),
            (self.expected_normalized_identity, "normalized identity"),
            (self.state_before_identity, "state-before identity"),
            (self.state_after_identity, "state-after identity"),
        ):
            _require_sha256(value, field)
        if self.state_before_identity != self.state_after_identity:
            raise CrossrefIntegrationInputRejected("quarantine changed state")

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_normalized_identity": self.expected_normalized_identity,
            "expected_raw_capture_identity": self.expected_raw_capture_identity,
            "input_sha256": self.input_sha256,
            "reason_codes": list(self.reason_codes),
            "schema": "pastila-crossref-integration-quarantine-v1",
            "state_after_identity": self.state_after_identity,
            "state_before_identity": self.state_before_identity,
        }

    @property
    def identity(self) -> str:
        from hashlib import sha256

        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossrefIntegrationResultV1:
    disposition: Literal["ACCEPTED", "IDEMPOTENT_REPLAY", "QUARANTINED"]
    state: CrossrefIntegrationStateV1
    batch: CrossrefIntegrationBatchV1 | None = None
    quarantine: CrossrefIntegrationQuarantineV1 | None = None

    def __post_init__(self) -> None:
        if self.disposition not in {"ACCEPTED", "IDEMPOTENT_REPLAY", "QUARANTINED"}:
            raise CrossrefIntegrationInputRejected("result disposition is invalid")
        if type(self.state) is not CrossrefIntegrationStateV1:
            raise CrossrefIntegrationInputRejected("result state type is invalid")
        if (
            self.batch is not None
            and type(self.batch) is not CrossrefIntegrationBatchV1
        ):
            raise CrossrefIntegrationInputRejected("result batch type is invalid")
        if (
            self.quarantine is not None
            and type(self.quarantine) is not CrossrefIntegrationQuarantineV1
        ):
            raise CrossrefIntegrationInputRejected("result quarantine type is invalid")
        accepted = self.disposition in {"ACCEPTED", "IDEMPOTENT_REPLAY"}
        if accepted != (self.batch is not None) or accepted == (
            self.quarantine is not None
        ):
            raise CrossrefIntegrationInputRejected("result payload is inconsistent")
        if accepted and cast(CrossrefIntegrationBatchV1, self.batch).identity not in (
            self.state.applied_batch_identities
        ):
            raise CrossrefIntegrationInputRejected(
                "accepted batch is absent from result state"
            )
        if (
            self.quarantine is not None
            and self.quarantine.state_after_identity != self.state.identity
        ):
            raise CrossrefIntegrationInputRejected(
                "quarantine receipt is not bound to result state"
            )


def integrate_crossref_normalized_bytes_v1(
    state: CrossrefIntegrationStateV1,
    payload: bytes,
) -> CrossrefIntegrationResultV1:
    """Integrate only the immutable, qualified Phase 2 capture authority."""

    if type(state) is not CrossrefIntegrationStateV1 or type(payload) is not bytes:
        raise TypeError("state and payload must be exact immutable boundary types")
    from hashlib import sha256 as local_sha256
    from json import dumps as local_json_dumps
    from json import loads as local_json_loads

    def local_canonical(value: object) -> bytes:
        return (
            local_json_dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")

    def local_record_dict(record: CrossrefIntegratedRecordV1) -> dict[str, object]:
        return {
            "DOI": record.DOI,
            "URL": record.URL,
            "created": (
                None
                if record.created is None
                else local_json_loads(record.created.canonical_bytes)
            ),
            "doi_key": record.doi_key,
            "normalized_identity": record.normalized_identity,
            "published": (
                None
                if record.published is None
                else local_json_loads(record.published.canonical_bytes)
            ),
            "publisher": record.publisher,
            "raw_capture_identity": record.raw_capture_identity,
            "source_ordinal": record.source_ordinal,
            "title": None if record.title is None else list(record.title),
            "type": record.type,
        }

    local_records = [local_record_dict(record) for record in state.records]
    local_record_identities = [
        local_sha256(local_canonical(record)).hexdigest() for record in local_records
    ]
    trusted_state_identity = local_sha256(
        local_canonical(
            {
                "applied_batch_identities": list(state.applied_batch_identities),
                "record_identities": local_record_identities,
                "records": local_records,
                "schema": "pastila-crossref-integration-state-v1",
            }
        )
    ).hexdigest()
    # These values are deliberately reconstructed in the consuming frame. Public
    # module constants are evidence labels, never runtime admission authority.
    empty_state_identity = (
        "62846329a1f032711c76f5120705b4c9a1237b92d5de6e9e273da8f25b41475b"
    )
    accepted_state_identity = (
        "768ac0572117e39a3cc0f9f4b7d0a255ed116f33b4fd6f5653e09c091ac804d5"
    )
    if trusted_state_identity not in {
        empty_state_identity,
        accepted_state_identity,
    }:
        raise CrossrefIntegrationInputRejected("state is not a qualified Phase 3 state")
    expected_raw_capture_identity = (
        "3acbdb9f2e54940f5953b497ace279a5884d0ce607f4e77e868de9a667783281"
    )
    expected_normalized_identity = (
        "bc2dd86d76c89f9e39f4a99a72db87ef57a5835ea92533a02f942ecc1111f4e0"
    )
    input_sha256 = local_sha256(payload).hexdigest()
    reasons: set[str] = set()
    if input_sha256 != expected_normalized_identity:
        reasons.add("NORMALIZED_IDENTITY_MISMATCH")

    document = _decode_document(payload, reasons)
    records: list[CrossrefIntegratedRecordV1] = []
    if document is not None:
        if document.get("schema") != "pastila-crossref-pilot-offline-v1":
            reasons.add("NORMALIZED_SCHEMA_MISMATCH")
        if document.get("raw_capture_identity") != expected_raw_capture_identity:
            reasons.add("RAW_CAPTURE_IDENTITY_MISMATCH")
        values = document.get("records")
        if not isinstance(values, list) or len(values) > 10:
            reasons.add("RECORD_SET_INVALID")
        else:
            for ordinal, value in enumerate(values):
                record = _map_record(
                    value,
                    ordinal,
                    expected_raw_capture_identity,
                    expected_normalized_identity,
                    reasons,
                )
                if record is not None:
                    records.append(record)

    doi_keys = [record.doi_key for record in records]
    if len(doi_keys) != len(set(doi_keys)):
        reasons.add("DUPLICATE_DOI")
    batch: CrossrefIntegrationBatchV1 | None = None
    if not reasons:
        batch = CrossrefIntegrationBatchV1(
            expected_raw_capture_identity,
            expected_normalized_identity,
            tuple(sorted(records, key=lambda record: record.doi_key)),
        )
        if batch.identity in state.applied_batch_identities:
            return CrossrefIntegrationResultV1("IDEMPOTENT_REPLAY", state, batch=batch)
        existing = {record.doi_key for record in state.records}
        if existing.intersection(doi_keys):
            reasons.add("DOI_STATE_CONFLICT")

    if reasons:
        quarantine = CrossrefIntegrationQuarantineV1(
            tuple(sorted(reasons)),
            input_sha256,
            expected_raw_capture_identity,
            expected_normalized_identity,
            state.identity,
            state.identity,
        )
        return CrossrefIntegrationResultV1("QUARANTINED", state, quarantine=quarantine)

    assert batch is not None
    next_state = CrossrefIntegrationStateV1(
        tuple(
            sorted((*state.records, *batch.records), key=lambda record: record.doi_key)
        ),
        tuple(sorted((*state.applied_batch_identities, batch.identity))),
    )
    return CrossrefIntegrationResultV1("ACCEPTED", next_state, batch=batch)


def _decode_document(payload: bytes, reasons: set[str]) -> dict[str, object] | None:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate member")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid constant {value}")
            ),
        )
    except UnicodeDecodeError, json.JSONDecodeError, ValueError:
        reasons.add("NORMALIZED_BYTES_MALFORMED")
        return None
    if not isinstance(value, dict) or _canonical_json_bytes(value) != payload:
        reasons.add("NORMALIZED_BYTES_NONCANONICAL")
        return None
    if set(value) != {"raw_capture_identity", "records", "schema"}:
        reasons.add("NORMALIZED_DOCUMENT_SHAPE_INVALID")
    return cast(dict[str, object], value)


def _map_record(
    value: object,
    ordinal: int,
    raw_identity: str,
    normalized_identity: str,
    reasons: set[str],
) -> CrossrefIntegratedRecordV1 | None:
    record_fields = {
        "DOI",
        "URL",
        "created",
        "published",
        "publisher",
        "title",
        "type",
    }
    if not isinstance(value, dict) or set(value) != record_fields:
        reasons.add("RECORD_SHAPE_INVALID")
        return None
    doi = value.get("DOI")
    title = value.get("title")
    optional_strings = (value.get("publisher"), value.get("type"), value.get("URL"))
    optional_objects = (value.get("published"), value.get("created"))
    if not isinstance(doi, str) or not doi:
        reasons.add("DOI_INVALID")
        return None
    if title is not None and (
        not isinstance(title, list) or any(not isinstance(item, str) for item in title)
    ):
        reasons.add("RECORD_FIELD_TYPE_INVALID")
        return None
    if any(item is not None and not isinstance(item, str) for item in optional_strings):
        reasons.add("RECORD_FIELD_TYPE_INVALID")
        return None
    if any(
        item is not None and not isinstance(item, dict) for item in optional_objects
    ):
        reasons.add("RECORD_FIELD_TYPE_INVALID")
        return None
    return CrossrefIntegratedRecordV1(
        DOI=doi,
        doi_key=doi.casefold(),
        title=None if title is None else tuple(title),
        publisher=cast(str | None, value.get("publisher")),
        type=cast(str | None, value.get("type")),
        published=(
            None
            if value.get("published") is None
            else _CanonicalJsonObjectV1(_canonical_json_bytes(value["published"]))
        ),
        created=(
            None
            if value.get("created") is None
            else _CanonicalJsonObjectV1(_canonical_json_bytes(value["created"]))
        ),
        URL=cast(str | None, value.get("URL")),
        source_ordinal=ordinal,
        raw_capture_identity=raw_identity,
        normalized_identity=normalized_identity,
    )


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


def _require_sha256(value: object, field: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CrossrefIntegrationInputRejected(f"{field} is not lowercase SHA-256")


__all__ = (
    "PHASE2_NORMALIZED_IDENTITY",
    "PHASE2_PROOF_COMMIT",
    "PHASE2_RAW_CAPTURE_IDENTITY",
    "PHASE3_ACCEPTED_STATE_IDENTITY",
    "PHASE3_EMPTY_STATE_IDENTITY",
    "CrossrefIntegratedRecordV1",
    "CrossrefIntegrationBatchV1",
    "CrossrefIntegrationInputRejected",
    "CrossrefIntegrationQuarantineV1",
    "CrossrefIntegrationResultV1",
    "CrossrefIntegrationStateV1",
    "integrate_crossref_normalized_bytes_v1",
)
