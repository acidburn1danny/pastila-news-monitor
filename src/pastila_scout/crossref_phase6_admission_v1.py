"""Offline admission of the exact committed Phase 5 Crossref capture."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pastila_scout.crossref_capture_integration_v1 as _integration
import pastila_scout.crossref_production_qualification_v1 as _durability
from pastila_scout.crossref_capture_integration_v1 import (
    CrossrefIntegrationBatchV1,
    CrossrefIntegrationStateV1,
)

SCHEMA = "pastila-crossref-phase6-admission-v1"
CAPTURE_COMMIT = "a5a13dd2d2f4dde5ed5ec8a2df20c05fea6727c5"
CAPTURE_TREE = "5a028101ebc3afe8dd34b76e8f345e55af989dc0"
PROOF_TIP = "04205ccb73542f3360b3811e31c2caef7adec1dc"
PROOF_TREE = "df152acda529ad8bda2949fb479b0559b0a25fc5"
REQUEST_IDENTITY = "5a7a3d701cb47c05fbe3d76c9a98e2ba3b3c2bca88c2662aec444fc4fe6c6fcc"
RAW_CAPTURE_IDENTITY = (
    "f9e876c21b2c33bcbc6148c4db36d7b5e50f1cb2d3c6bc6fbd435a011e155c67"
)
NORMALIZED_IDENTITY = "d7483467570531be0008206b955b2f9f903ed6fbc569309286ff563f5e7a8291"
EXECUTION_QUALIFICATION_SHA256 = (
    "f1145b2b5c26ba09cdf35bebe5687ccfec2bbc6ba1e14da672e882b5ea172ed8"
)
PHASE3_IMPLEMENTATION_SHA256 = (
    "e20a9f48b69ce6200da4493a915de4387dee13542fbc64633f2d3a94633c641b"
)
PHASE4_IMPLEMENTATION_SHA256 = (
    "7ed74e844b8a35b56da3bb3752aad8cbd44ed2d7f5709f1e77d5fb3024d6a06c"
)
PROOF_ROOT_RELATIVE = Path(
    ".pastila-runtime/milestone10-crossref-production-capture-v1"
)
ARTIFACT_SHA256 = (
    (
        "attempt-consumed.json",
        "eba2034006bf0317492c5b453e21b897878ef4292146a5f5eed17d86c8486bc5",
    ),
    (
        "completion.json",
        "f9cc2acac3c5df2f8c7d0b5124bdb12237eaf77f9a683fe0096ba8f4d78732c6",
    ),
    (
        "raw-capture/manifest.json",
        "e5e3c6608e6b76f0bfaadb1a85b463c16cd8d8166a073f0b0377e058d250025e",
    ),
    (
        "raw-capture/request.json",
        "b34ecc203014226eba2188700876630060b0c5da719b1f88ac2b29579051744b",
    ),
    (
        "raw-capture/response-body.bin",
        "5fee9b617bb9ae59eea01eb5953a3328e7bccb07b1b286d61eb351331b83e36c",
    ),
    (
        "raw-capture/response-headers.json",
        "aa435b09b1f6088f8110fb7db425fb0652d5ecd06d3c85ca8982bed3788afbff",
    ),
    (
        "raw-capture/wire-request.http",
        "3a12fd685d9efd30afcd5fda04f8e1f5034ebc1144a224265ba0b18dfe70a4c1",
    ),
)


class CrossrefPhase6AdmissionError(ValueError):
    """The fixed Phase 6 admission boundary rejected its local evidence."""


@dataclass(frozen=True, slots=True)
class CrossrefPhase6OutcomeV1:
    normalized_identity: str
    batch_identity: str
    state_before_identity: str
    state_after_identity: str
    record_count: int

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "batch_identity": self.batch_identity,
                "capture_commit": CAPTURE_COMMIT,
                "disposition": "ACCEPTED",
                "normalized_identity": self.normalized_identity,
                "proof_tip": PROOF_TIP,
                "raw_capture_identity": RAW_CAPTURE_IDENTITY,
                "record_count": self.record_count,
                "request_identity": REQUEST_IDENTITY,
                "schema": SCHEMA,
                "state_after_identity": self.state_after_identity,
                "state_before_identity": self.state_before_identity,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


def execute_phase6_offline_admission_v1(
    execution_root: Path,
) -> CrossrefPhase6OutcomeV1:
    """Admit the exact committed Phase 5 capture into a new local state root."""

    _require_runtime_authority()
    normalized, batch, _state_before, state_after, outcome = _derive_admission()
    root = _durability._require_new_execution_root(execution_root)
    _durability._write_durable_new(
        root / "attempt-consumed.json",
        _canonical(
            {
                "capture_commit": CAPTURE_COMMIT,
                "maximum_attempts": 1,
                "proof_tip": PROOF_TIP,
                "schema": "pastila-crossref-phase6-attempt-v1",
                "state": "CONSUMED_BEFORE_ADMISSION",
            }
        ),
    )
    _durability._atomic_publish_or_verify_existing(
        root / "normalized-records.json", normalized
    )
    _durability._atomic_publish_or_verify_existing(
        root / "integration-batch.json", batch.canonical_bytes
    )
    _durability._atomic_publish_or_verify_existing(
        root / "integration-state.json", state_after.canonical_bytes
    )
    _durability._atomic_publish_or_verify_existing(
        root / "completion.json", outcome.canonical_bytes
    )
    return outcome


def recover_phase6_offline_admission_v1(
    execution_root: Path,
) -> CrossrefPhase6OutcomeV1:
    """Complete only the deterministic admission already consumed at this root."""

    _require_runtime_authority()
    normalized, batch, _state_before, state_after, outcome = _derive_admission()
    root = _durability._require_existing_execution_root(execution_root)
    expected_attempt = _canonical(
        {
            "capture_commit": CAPTURE_COMMIT,
            "maximum_attempts": 1,
            "proof_tip": PROOF_TIP,
            "schema": "pastila-crossref-phase6-attempt-v1",
            "state": "CONSUMED_BEFORE_ADMISSION",
        }
    )
    if (
        _durability._read_regular_file(root / "attempt-consumed.json")
        != expected_attempt
    ):
        raise CrossrefPhase6AdmissionError("Phase 6 attempt authority mismatch")
    for name, payload in (
        ("normalized-records.json", normalized),
        ("integration-batch.json", batch.canonical_bytes),
        ("integration-state.json", state_after.canonical_bytes),
        ("completion.json", outcome.canonical_bytes),
    ):
        _durability._atomic_publish_or_verify_existing(root / name, payload)
    return outcome


def _derive_admission() -> tuple[
    bytes,
    CrossrefIntegrationBatchV1,
    CrossrefIntegrationStateV1,
    CrossrefIntegrationStateV1,
    CrossrefPhase6OutcomeV1,
]:
    snapshot = _snapshot_and_validate_proof()
    normalized = _normalize(snapshot["raw-capture/response-body.bin"])
    state_before = CrossrefIntegrationStateV1()
    batch, state_after = _integrate(normalized, state_before)
    outcome = CrossrefPhase6OutcomeV1(
        NORMALIZED_IDENTITY,
        batch.identity,
        state_before.identity,
        state_after.identity,
        len(batch.records),
    )
    return normalized, batch, state_before, state_after, outcome


def _proof_root() -> Path:
    return Path(__file__).resolve().parents[2] / PROOF_ROOT_RELATIVE


def _snapshot_and_validate_proof() -> dict[str, bytes]:
    root = _proof_root()
    if root.is_symlink() or not root.is_dir() or root.resolve() != root.absolute():
        raise CrossrefPhase6AdmissionError("Phase 5 proof root is not a real directory")
    snapshot = {
        name: _durability._read_regular_file(root / name)
        for name, _identity in ARTIFACT_SHA256
    }
    if {
        name: hashlib.sha256(payload).hexdigest() for name, payload in snapshot.items()
    } != dict(ARTIFACT_SHA256):
        raise CrossrefPhase6AdmissionError("Phase 5 proof artifact identity mismatch")
    manifest = _decode(snapshot["raw-capture/manifest.json"])
    completion = _decode(snapshot["completion.json"])
    if (
        manifest.get("capture_identity") != RAW_CAPTURE_IDENTITY
        or manifest.get("request_identity") != REQUEST_IDENTITY
        or completion.get("raw_capture_identity") != RAW_CAPTURE_IDENTITY
        or completion.get("request_identity") != REQUEST_IDENTITY
        or completion.get("record_count") != 10
        or completion.get("transport_mode") != "PRODUCTION_DIRECT_HTTPS"
    ):
        raise CrossrefPhase6AdmissionError("Phase 5 semantic proof closure mismatch")
    return snapshot


def _normalize(body: bytes) -> bytes:
    document = _durability._decode_response_json(body)
    if document.get("status") != "ok" or document.get("message-type") != "work-list":
        raise CrossrefPhase6AdmissionError("Crossref response envelope mismatch")
    message = document.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise CrossrefPhase6AdmissionError("Crossref response items are unavailable")
    items = message["items"]
    if len(items) > 10:
        raise CrossrefPhase6AdmissionError("Crossref response exceeds record limit")
    records = [
        _durability._normalize_item(value, index) for index, value in enumerate(items)
    ]
    payload = _canonical(
        {
            "raw_capture_identity": RAW_CAPTURE_IDENTITY,
            "records": records,
            "schema": "pastila-crossref-pilot-offline-v1",
        }
    )
    if hashlib.sha256(payload).hexdigest() != NORMALIZED_IDENTITY:
        raise CrossrefPhase6AdmissionError("normalized Phase 5 identity mismatch")
    return payload


def _integrate(
    normalized: bytes, state: CrossrefIntegrationStateV1
) -> tuple[CrossrefIntegrationBatchV1, CrossrefIntegrationStateV1]:
    reasons: set[str] = set()
    document = _integration._decode_document(normalized, reasons)
    records = []
    if document is not None:
        values = document.get("records")
        if not isinstance(values, list) or len(values) > 10:
            reasons.add("RECORD_SET_INVALID")
        else:
            for ordinal, value in enumerate(values):
                record = _integration._map_record(
                    value, ordinal, RAW_CAPTURE_IDENTITY, NORMALIZED_IDENTITY, reasons
                )
                if record is not None:
                    records.append(record)
    keys = [record.doi_key for record in records]
    if len(keys) != len(set(keys)):
        reasons.add("DUPLICATE_DOI")
    if reasons:
        raise CrossrefPhase6AdmissionError(
            "Phase 5 normalized capture rejected: " + ",".join(sorted(reasons))
        )
    batch = CrossrefIntegrationBatchV1(
        RAW_CAPTURE_IDENTITY,
        NORMALIZED_IDENTITY,
        tuple(sorted(records, key=lambda record: record.doi_key)),
    )
    state_after = CrossrefIntegrationStateV1(batch.records, (batch.identity,))
    if state != CrossrefIntegrationStateV1():
        raise CrossrefPhase6AdmissionError("Phase 6 state must begin empty")
    return batch, state_after


def _decode(payload: bytes) -> dict[str, object]:
    value = _durability._decode_exact_object(payload)
    return value


def _canonical(value: object) -> bytes:
    return _durability._canonical_json_bytes(value)


def _require_runtime_authority() -> None:
    dependencies = (
        (_integration, PHASE3_IMPLEMENTATION_SHA256),
        (_durability, PHASE4_IMPLEMENTATION_SHA256),
    )
    if any(
        hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != identity
        for module, identity in dependencies
    ):
        raise CrossrefPhase6AdmissionError("Phase 6 dependency source mismatch")
    if any(
        globals().get(name) is not authority for name, authority in _LOCAL_CLOSURE
    ) or any(
        getattr(module, name, None) is not authority
        for module, name, authority in _DEPENDENCY_CLOSURE
    ):
        raise CrossrefPhase6AdmissionError("Phase 6 runtime authority was rebound")


_LOCAL_CLOSURE = tuple(
    (name, globals()[name])
    for name in (
        "CrossrefIntegrationBatchV1",
        "CrossrefIntegrationStateV1",
        "CrossrefPhase6OutcomeV1",
        "ARTIFACT_SHA256",
        "CAPTURE_COMMIT",
        "CAPTURE_TREE",
        "EXECUTION_QUALIFICATION_SHA256",
        "NORMALIZED_IDENTITY",
        "PROOF_TIP",
        "PROOF_TREE",
        "RAW_CAPTURE_IDENTITY",
        "REQUEST_IDENTITY",
        "_canonical",
        "_decode",
        "_derive_admission",
        "_integrate",
        "_normalize",
        "_proof_root",
        "_snapshot_and_validate_proof",
        "execute_phase6_offline_admission_v1",
        "recover_phase6_offline_admission_v1",
    )
)

_DEPENDENCY_CLOSURE = (
    (
        _integration,
        "CrossrefIntegrationBatchV1",
        _integration.CrossrefIntegrationBatchV1,
    ),
    (
        _integration,
        "CrossrefIntegrationStateV1",
        _integration.CrossrefIntegrationStateV1,
    ),
    (_integration, "_decode_document", _integration._decode_document),
    (_integration, "_map_record", _integration._map_record),
    (
        _durability,
        "_atomic_publish_or_verify_existing",
        _durability._atomic_publish_or_verify_existing,
    ),
    (_durability, "_canonical_json_bytes", _durability._canonical_json_bytes),
    (_durability, "_decode_exact_object", _durability._decode_exact_object),
    (_durability, "_decode_response_json", _durability._decode_response_json),
    (_durability, "_normalize_item", _durability._normalize_item),
    (_durability, "_read_regular_file", _durability._read_regular_file),
    (
        _durability,
        "_require_existing_execution_root",
        _durability._require_existing_execution_root,
    ),
    (
        _durability,
        "_require_new_execution_root",
        _durability._require_new_execution_root,
    ),
    (_durability, "_write_durable_new", _durability._write_durable_new),
)


__all__ = (
    "CrossrefPhase6AdmissionError",
    "CrossrefPhase6OutcomeV1",
    "execute_phase6_offline_admission_v1",
    "recover_phase6_offline_admission_v1",
)
