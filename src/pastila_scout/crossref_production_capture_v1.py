"""Bounded one-shot Crossref production capture boundary.

The public entry is network-capable but is never invoked by qualification.  It
performs one exact Phase 2 HTTPS request, durably preserves the raw response,
and publishes a receipt only after response-profile and record-count validation.
It deliberately performs no integration or downstream publication.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import pastila_scout.crossref_pilot_offline_v1 as _capture_authority
from pastila_scout.crossref_pilot_offline_v1 import (
    FROZEN_REQUEST,
    DirectCrossrefHttpsTransportV1,
    RawResponseCaptureV1,
    TransportOnce,
    execute_one_shot_capture_v1,
    frozen_request_identity_v1,
    normalize_capture_v1,
    validate_response_profile_v1,
)

SCHEMA = "pastila-crossref-production-capture-v1"
EXECUTION_ROOT_RELATIVE = Path(
    ".pastila-runtime/milestone10-crossref-production-capture-v1"
)
CAPTURE_AUTHORITY_SHA256 = (
    "76ab57347dcc0fd5774d34ff999481afb2f6cb8b5e33c6d301e0d05d3e9e70a0"
)
PHASE4_COMMIT = "54037f907f16ecb3aefe4fd7128b948d4f862d4c"
PHASE4_TREE = "87e9ce4619223bc9ba216ce5c96aa85c3386d70f"
PHASE4_QUALIFICATION_SHA256 = (
    "53a465a2983ea9f32cbd8c54ac9fc12c470e3c82d4e896f1690627c03a86f10b"
)


class CrossrefProductionCaptureError(ValueError):
    """The bounded production-capture boundary rejected execution state."""


@dataclass(frozen=True, slots=True)
class CrossrefProductionCaptureReceiptV1:
    request_identity: str
    raw_capture_identity: str
    record_count: int
    transport_mode: Literal["PRODUCTION_DIRECT_HTTPS", "OFFLINE_QUALIFICATION"]

    def __post_init__(self) -> None:
        _require_sha256(self.request_identity, "request identity")
        _require_sha256(self.raw_capture_identity, "raw capture identity")
        if type(self.record_count) is not int or not 0 <= self.record_count <= 10:
            raise CrossrefProductionCaptureError(
                "record count must be between 0 and 10"
            )
        if self.transport_mode not in {
            "PRODUCTION_DIRECT_HTTPS",
            "OFFLINE_QUALIFICATION",
        }:
            raise CrossrefProductionCaptureError("transport mode is invalid")

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(
            {
                "raw_capture_identity": self.raw_capture_identity,
                "record_count": self.record_count,
                "request_identity": self.request_identity,
                "schema": SCHEMA,
                "state": "RAW_CAPTURED_AND_PROFILE_VALIDATED",
                "transport_mode": self.transport_mode,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


def execute_bounded_crossref_production_capture_v1() -> (
    CrossrefProductionCaptureReceiptV1
):
    """Perform the sole production request; owner authorization is external."""

    _require_runtime_authority()
    root = _create_and_consume_attempt(authorized_execution_root_v1())
    capture = execute_one_shot_capture_v1(DirectCrossrefHttpsTransportV1())
    _record_raw_capture(root / "raw-capture", capture)
    return _validate_and_complete(
        root, capture, transport_mode="PRODUCTION_DIRECT_HTTPS"
    )


def _execute_with_transport_once_v1(
    execution_root: Path,
    transport_once: TransportOnce,
) -> CrossrefProductionCaptureReceiptV1:
    """Qualification seam; production always supplies the frozen direct adapter."""

    _require_runtime_authority()
    root = _create_and_consume_attempt(execution_root)
    capture = execute_one_shot_capture_v1(transport_once)
    _record_raw_capture(root / "raw-capture", capture)
    return _validate_and_complete(root, capture, transport_mode="OFFLINE_QUALIFICATION")


def _validate_and_complete(
    root: Path,
    capture: RawResponseCaptureV1,
    *,
    transport_mode: Literal["PRODUCTION_DIRECT_HTTPS", "OFFLINE_QUALIFICATION"],
) -> CrossrefProductionCaptureReceiptV1:
    validate_response_profile_v1(capture)
    normalized = normalize_capture_v1(capture)
    receipt = CrossrefProductionCaptureReceiptV1(
        request_identity=frozen_request_identity_v1(),
        raw_capture_identity=capture.identity,
        record_count=len(normalized.records),
        transport_mode=transport_mode,
    )
    _atomic_publish_or_verify_existing(
        root / "completion.json", receipt.canonical_bytes
    )
    return receipt


def authorized_execution_root_v1() -> Path:
    return Path(__file__).resolve().parents[2] / EXECUTION_ROOT_RELATIVE


def _create_and_consume_attempt(path: Path) -> Path:
    if not isinstance(path, Path) or path.exists() or path.is_symlink():
        raise CrossrefProductionCaptureError("execution root must be a new Path")
    unresolved_parent = path.parent.absolute()
    repository_root = path.parent.parent.resolve(strict=True)
    if os.path.normcase(str(repository_root)) != os.path.normcase(
        str(path.parent.parent.absolute())
    ):
        raise CrossrefProductionCaptureError("repository root must be a real directory")
    if path.parent.exists() or path.parent.is_symlink():
        if path.parent.is_symlink() or not path.parent.is_dir():
            raise CrossrefProductionCaptureError(
                "execution root parent must be a real directory"
            )
    else:
        path.parent.mkdir(mode=0o700)
        _sync_directory(repository_root)
    parent = path.parent.resolve(strict=True)
    if os.path.normcase(str(parent)) != os.path.normcase(str(unresolved_parent)):
        raise CrossrefProductionCaptureError(
            "execution root parent must be a real directory"
        )
    path.mkdir(mode=0o700)
    root = path.resolve(strict=True)
    _sync_directory(parent)
    _write_durable_new(
        root / "attempt-consumed.json",
        _canonical_json_bytes(
            {
                "maximum_attempts": 1,
                "request_identity": frozen_request_identity_v1(),
                "schema": "pastila-crossref-production-attempt-v1",
                "state": "CONSUMED_BEFORE_TRANSPORT",
            }
        ),
    )
    return root


def _record_raw_capture(destination: Path, capture: RawResponseCaptureV1) -> None:
    if type(capture) is not RawResponseCaptureV1 or capture.request_identity != (
        frozen_request_identity_v1()
    ):
        raise CrossrefProductionCaptureError("capture is not bound to the request")
    destination.mkdir(mode=0o700)
    _sync_directory(destination.parent)
    request_bytes = _canonical_json_bytes(asdict(FROZEN_REQUEST))
    headers_bytes = _canonical_json_bytes(capture.headers)
    wire_bytes = _capture_authority.WIRE_REQUEST_BYTES
    manifest = _canonical_json_bytes(
        {
            "body_sha256": hashlib.sha256(capture.body).hexdigest(),
            "capture_identity": capture.identity,
            "headers_sha256": hashlib.sha256(headers_bytes).hexdigest(),
            "request_identity": capture.request_identity,
            "schema": "pastila-crossref-production-raw-capture-v1",
            "status": capture.status,
            "wire_request_sha256": hashlib.sha256(wire_bytes).hexdigest(),
        }
    )
    _write_durable_new(destination / "request.json", request_bytes)
    _write_durable_new(destination / "wire-request.http", wire_bytes)
    _write_durable_new(destination / "response-headers.json", headers_bytes)
    _write_durable_new(destination / "response-body.bin", capture.body)
    _atomic_publish_or_verify_existing(destination / "manifest.json", manifest)


def _atomic_publish_or_verify_existing(path: Path, payload: bytes) -> None:
    pending = path.with_name(path.name + ".pending")
    if pending.exists():
        if pending.is_symlink() or _read_regular_file(pending) != payload:
            raise CrossrefProductionCaptureError(
                "pending publication differs from qualified bytes"
            )
    else:
        _write_durable_new(pending, payload)
    try:
        os.link(pending, path)
    except FileExistsError:
        if path.is_symlink() or _read_regular_file(path) != payload:
            raise CrossrefProductionCaptureError(
                "published artifact differs from qualified bytes"
            )
        if not pending.samefile(path):
            raise CrossrefProductionCaptureError(
                "pending artifact is not the published hard-link"
            )
    pending.unlink()
    _sync_directory(path.parent)


def _read_regular_file(path: Path) -> bytes:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise CrossrefProductionCaptureError("artifact must be a regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise CrossrefProductionCaptureError("artifact changed before open")
        payload = os.read(descriptor, opened.st_size + 1)
        if len(payload) != opened.st_size:
            raise CrossrefProductionCaptureError("artifact changed during read")
        return payload
    finally:
        os.close(descriptor)


def _write_durable_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    _sync_directory(path.parent)


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
        raise CrossrefProductionCaptureError(f"{field} must be lowercase SHA-256")


_CAPTURE_RUNTIME_CLOSURE = tuple(
    (name, getattr(_capture_authority, name))
    for name in (
        "CA_BUNDLE_SHA256",
        "DirectCrossrefHttpsTransportV1",
        "FROZEN_REQUEST",
        "FrozenRequestV1",
        "MAXIMUM_RECORDS",
        "MAXIMUM_RESPONSE_BODY_BYTES",
        "READ_CHUNK_BYTES",
        "REQUEST_ACCEPT_MEDIA_TYPE",
        "RESPONSE_MEDIA_TYPE",
        "RawResponseCaptureV1",
        "_ConnectionBoundResponseV1",
        "_build_frozen_request_v1",
        "_canonical_json_bytes",
        "_capture_headers",
        "_decode_json_object",
        "_normalize_item",
        "_optional_object",
        "_optional_string",
        "_optional_title",
        "_read_bounded_body",
        "_remaining_seconds",
        "_require_deadline",
        "execute_one_shot_capture_v1",
        "frozen_request_identity_v1",
        "normalize_capture_v1",
        "validate_response_profile_v1",
    )
)
_EXTERNAL_RUNTIME_CLOSURE = (
    (
        _capture_authority.http.client,
        "HTTPSConnection",
        _capture_authority.http.client.HTTPSConnection,
    ),
    (
        _capture_authority.ssl,
        "create_default_context",
        _capture_authority.ssl.create_default_context,
    ),
    (_capture_authority.time, "monotonic", _capture_authority.time.monotonic),
    (_capture_authority.certifi, "where", _capture_authority.certifi.where),
)
_LOCAL_CLOSURE = tuple(
    (name, globals()[name])
    for name in (
        "CrossrefProductionCaptureReceiptV1",
        "CAPTURE_AUTHORITY_SHA256",
        "DirectCrossrefHttpsTransportV1",
        "EXECUTION_ROOT_RELATIVE",
        "FROZEN_REQUEST",
        "RawResponseCaptureV1",
        "_atomic_publish_or_verify_existing",
        "_canonical_json_bytes",
        "_create_and_consume_attempt",
        "_execute_with_transport_once_v1",
        "_read_regular_file",
        "_record_raw_capture",
        "_require_sha256",
        "_sync_directory",
        "_validate_and_complete",
        "_write_durable_new",
        "authorized_execution_root_v1",
        "execute_one_shot_capture_v1",
        "frozen_request_identity_v1",
        "normalize_capture_v1",
        "validate_response_profile_v1",
    )
)


def _require_runtime_authority(
    capture_closure: tuple[tuple[str, object], ...] = _CAPTURE_RUNTIME_CLOSURE,
    external_closure: tuple[tuple[object, str, object], ...] = (
        _EXTERNAL_RUNTIME_CLOSURE
    ),
    local_closure: tuple[tuple[str, object], ...] = _LOCAL_CLOSURE,
) -> None:
    source = Path(_capture_authority.__file__).resolve(strict=True)
    if hashlib.sha256(source.read_bytes()).hexdigest() != CAPTURE_AUTHORITY_SHA256:
        raise CrossrefProductionCaptureError("capture authority source mismatch")
    if (
        any(
            getattr(_capture_authority, name, None) is not authority
            for name, authority in capture_closure
        )
        or any(
            getattr(owner, name, None) is not authority
            for owner, name, authority in external_closure
        )
        or any(
            globals().get(name) is not authority for name, authority in local_closure
        )
    ):
        raise CrossrefProductionCaptureError("production capture authority was rebound")


__all__ = (
    "EXECUTION_ROOT_RELATIVE",
    "SCHEMA",
    "CrossrefProductionCaptureError",
    "CrossrefProductionCaptureReceiptV1",
    "authorized_execution_root_v1",
    "execute_bounded_crossref_production_capture_v1",
)
