"""Offline qualification of the bounded Crossref production orchestration path.

This module deliberately exposes no network-capable production entry point.  It
composes the already-qualified one-shot capture and Phase 3 integration
boundaries with a durable, recoverable publication boundary.  A separately
authorized phase may bind the real transport to this orchestration.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pastila_scout.crossref_capture_integration_v1 as _integration_authority
from pastila_scout.crossref_capture_integration_v1 import (
    CrossrefIntegrationResultV1,
    CrossrefIntegrationStateV1,
    integrate_crossref_normalized_bytes_v1,
)

SCHEMA = "pastila-crossref-production-qualification-v1"
EXECUTION_ROOT_RELATIVE = Path(
    ".pastila-runtime/milestone10-crossref-production-qualification-v1"
)
PHASE2_RESPONSE_BODY_SHA256 = (
    "cc8d1989eeb5ade64ef1fc9afee33f6c983174f48fb8d4623ff3d3630b43b2b1"
)
PHASE2_RESPONSE_HEADERS_SHA256 = (
    "c0e3c20148f1a95b658a6ef47a13fd967238cf68375a4f9fbe2fc91f8266796d"
)
PHASE2_RAW_CAPTURE_IDENTITY = (
    "3acbdb9f2e54940f5953b497ace279a5884d0ce607f4e77e868de9a667783281"
)
PHASE2_REQUEST_IDENTITY = (
    "5a7a3d701cb47c05fbe3d76c9a98e2ba3b3c2bca88c2662aec444fc4fe6c6fcc"
)
PHASE2_NORMALIZED_IDENTITY = (
    "bc2dd86d76c89f9e39f4a99a72db87ef57a5835ea92533a02f942ecc1111f4e0"
)
PHASE3_IMPLEMENTATION_SHA256 = (
    "e20a9f48b69ce6200da4493a915de4387dee13542fbc64633f2d3a94633c641b"
)
WIRE_REQUEST_BYTES = (
    "GET /v1/works?rows=10&sort=published&order=asc&select="
    "DOI%2Ctitle%2Cpublisher%2Ctype%2Cpublished%2Ccreated%2CURL HTTP/1.1\r\n"
    "Host: api.crossref.org\r\n"
    "Accept: application/json\r\n"
    "Accept-Encoding: identity\r\n"
    "User-Agent: PastilaScout-CrossrefPilot "
    "(+https://github.com/acidburn1danny/pastila-news-monitor)\r\n\r\n"
).encode("ascii")


class CrossrefProductionQualificationError(ValueError):
    """The offline production orchestration boundary rejected its inputs."""


@dataclass(frozen=True, slots=True)
class OfflineCrossrefResponseV1:
    """The exact previously captured Phase 2 response; never a transport."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def __post_init__(self) -> None:
        if type(self.status) is not int or self.status != 200:
            raise CrossrefProductionQualificationError("offline status is not 200")
        if type(self.headers) is not tuple or any(
            type(pair) is not tuple
            or len(pair) != 2
            or any(type(item) is not str for item in pair)
            for pair in self.headers
        ):
            raise CrossrefProductionQualificationError("offline headers are invalid")
        if type(self.body) is not bytes:
            raise CrossrefProductionQualificationError("offline body is not bytes")
        header_bytes = _canonical_json_bytes(self.headers)
        if hashlib.sha256(header_bytes).hexdigest() != PHASE2_RESPONSE_HEADERS_SHA256:
            raise CrossrefProductionQualificationError(
                "offline headers are not the Phase 2 proof bytes"
            )
        if hashlib.sha256(self.body).hexdigest() != PHASE2_RESPONSE_BODY_SHA256:
            raise CrossrefProductionQualificationError(
                "offline body is not the Phase 2 proof bytes"
            )
        if _raw_capture_identity(self.status, self.headers, self.body) != (
            PHASE2_RAW_CAPTURE_IDENTITY
        ):
            raise CrossrefProductionQualificationError(
                "offline response is not the Phase 2 raw capture"
            )


@dataclass(frozen=True, slots=True)
class CrossrefProductionOutcomeV1:
    """Identity closure published after the complete offline orchestration."""

    disposition: Literal["ACCEPTED", "IDEMPOTENT_REPLAY", "QUARANTINED"]
    request_identity: str
    raw_capture_identity: str
    normalized_identity: str
    state_before_identity: str
    state_after_identity: str
    batch_identity: str | None
    quarantine_identity: str | None

    def __post_init__(self) -> None:
        if self.disposition not in {
            "ACCEPTED",
            "IDEMPOTENT_REPLAY",
            "QUARANTINED",
        }:
            raise CrossrefProductionQualificationError(
                "production disposition is invalid"
            )
        for value, field in (
            (self.request_identity, "request identity"),
            (self.raw_capture_identity, "raw capture identity"),
            (self.normalized_identity, "normalized identity"),
            (self.state_before_identity, "state-before identity"),
            (self.state_after_identity, "state-after identity"),
        ):
            _require_sha256(value, field)
        for value, field in (
            (self.batch_identity, "batch identity"),
            (self.quarantine_identity, "quarantine identity"),
        ):
            if value is not None:
                _require_sha256(value, field)
        accepted = self.disposition in {"ACCEPTED", "IDEMPOTENT_REPLAY"}
        if accepted != (self.batch_identity is not None) or accepted == (
            self.quarantine_identity is not None
        ):
            raise CrossrefProductionQualificationError(
                "production outcome payload is inconsistent"
            )

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(
            {
                "batch_identity": self.batch_identity,
                "disposition": self.disposition,
                "normalized_identity": self.normalized_identity,
                "quarantine_identity": self.quarantine_identity,
                "raw_capture_identity": self.raw_capture_identity,
                "request_identity": self.request_identity,
                "schema": SCHEMA,
                "state_after_identity": self.state_after_identity,
                "state_before_identity": self.state_before_identity,
            }
        )

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


def execute_offline_crossref_production_qualification_v1(
    execution_root: Path,
    response: OfflineCrossrefResponseV1,
) -> CrossrefProductionOutcomeV1:
    """Exercise the complete production path with an explicitly supplied fixture.

    The input is the exact captured Phase 2 snapshot, not a transport seam.
    This module contains no network transport or transport-capable dependency.
    """

    _require_runtime_authority()
    if type(response) is not OfflineCrossrefResponseV1:
        raise CrossrefProductionQualificationError(
            "response must be the exact offline Phase 2 snapshot"
        )
    root = _require_new_execution_root(execution_root)
    raw_root = _consume_attempt(root)
    _record_raw_snapshot(raw_root, response)
    normalized_bytes = _normalize_exact_snapshot(response)
    normalized_path = root / "normalized-records.json"
    _write_durable_new(normalized_path, normalized_bytes)
    return _integrate_and_publish(root, normalized_bytes)


def recover_offline_crossref_production_qualification_v1(
    execution_root: Path,
) -> CrossrefProductionOutcomeV1:
    """Resume only from a complete byte-verified raw capture; never transport."""

    _require_runtime_authority()
    root = _require_existing_execution_root(execution_root)
    completed = root / "completion.json"
    if completed.exists():
        recorded = _load_completed_outcome(completed)
        normalized_bytes = _read_regular_file(root / "normalized-records.json")
        response = _load_complete_raw_capture(root / "raw-capture")
        if _normalize_exact_snapshot(response) != normalized_bytes:
            raise CrossrefProductionQualificationError(
                "normalized bytes do not match the durable raw capture"
            )
        state = _load_qualified_state(root / "integration-state.json", normalized_bytes)
        initial = CrossrefIntegrationStateV1()
        accepted = integrate_crossref_normalized_bytes_v1(initial, normalized_bytes)
        replay = integrate_crossref_normalized_bytes_v1(state, normalized_bytes)
        expected = _outcome_from_result(initial, normalized_bytes, accepted)
        if (
            accepted.disposition != "ACCEPTED"
            or replay.disposition != "IDEMPOTENT_REPLAY"
            or recorded != expected
        ):
            raise CrossrefProductionQualificationError(
                "completion is not closed over the durable production artifacts"
            )
        return recorded

    normalized_path = root / "normalized-records.json"
    if normalized_path.exists():
        normalized_bytes = _read_regular_file(normalized_path)
    else:
        response = _load_complete_raw_capture(root / "raw-capture")
        normalized_bytes = _normalize_exact_snapshot(response)
        _write_durable_new(normalized_path, normalized_bytes)
    return _integrate_and_publish(root, normalized_bytes)


def authorized_qualification_root_v1() -> Path:
    """Return the inert repository-relative qualification root."""

    return Path(__file__).resolve().parents[2] / EXECUTION_ROOT_RELATIVE


def _consume_attempt(root: Path) -> Path:
    _write_durable_new(
        root / "attempt-consumed.json",
        _canonical_json_bytes(
            {
                "request_identity": PHASE2_REQUEST_IDENTITY,
                "schema": "pastila-crossref-pilot-attempt-consumption-v1",
                "state": "CONSUMED_BEFORE_TRANSPORT",
            }
        ),
    )
    return root / "raw-capture"


def _record_raw_snapshot(raw_root: Path, response: OfflineCrossrefResponseV1) -> None:
    raw_root.mkdir(mode=0o700)
    _sync_directory(raw_root.parent)
    headers_bytes = _canonical_json_bytes(response.headers)
    manifest = {
        "body_sha256": hashlib.sha256(response.body).hexdigest(),
        "capture_identity": PHASE2_RAW_CAPTURE_IDENTITY,
        "headers_sha256": hashlib.sha256(headers_bytes).hexdigest(),
        "request_identity": PHASE2_REQUEST_IDENTITY,
        "schema": "pastila-crossref-pilot-raw-capture-v1",
        "status": response.status,
        "wire_request_sha256": hashlib.sha256(WIRE_REQUEST_BYTES).hexdigest(),
    }
    _write_durable_new(raw_root / "request.json", _request_profile_bytes())
    _write_durable_new(raw_root / "wire-request.http", WIRE_REQUEST_BYTES)
    _write_durable_new(raw_root / "response-headers.json", headers_bytes)
    _write_durable_new(raw_root / "response-body.bin", response.body)
    _write_durable_new(raw_root / "manifest.json", _canonical_json_bytes(manifest))


def _normalize_exact_snapshot(response: OfflineCrossrefResponseV1) -> bytes:
    document = _decode_response_json(response.body)
    if document.get("status") != "ok":
        raise CrossrefProductionQualificationError("response status is not ok")
    if document.get("message-type") != "work-list":
        raise CrossrefProductionQualificationError("response type is not work-list")
    version = document.get("message-version")
    message = document.get("message")
    if type(version) is not str or not version or not isinstance(message, dict):
        raise CrossrefProductionQualificationError("response envelope is invalid")
    items = message.get("items")
    if not isinstance(items, list) or len(items) > 10:
        raise CrossrefProductionQualificationError("response item set is invalid")
    records = [_normalize_item(item, index) for index, item in enumerate(items)]
    payload = _canonical_json_bytes(
        {
            "raw_capture_identity": PHASE2_RAW_CAPTURE_IDENTITY,
            "records": records,
            "schema": "pastila-crossref-pilot-offline-v1",
        }
    )
    if hashlib.sha256(payload).hexdigest() != PHASE2_NORMALIZED_IDENTITY:
        raise CrossrefProductionQualificationError(
            "normalized bytes are not the Phase 2 proof bytes"
        )
    return payload


def _normalize_item(value: object, index: int) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CrossrefProductionQualificationError(f"item {index} is not an object")
    doi = value.get("DOI")
    if type(doi) is not str or not doi:
        raise CrossrefProductionQualificationError(f"item {index} DOI is invalid")
    title = value.get("title")
    if title is not None and (
        not isinstance(title, list) or any(type(item) is not str for item in title)
    ):
        raise CrossrefProductionQualificationError(f"item {index} title is invalid")
    for field in ("publisher", "type", "URL"):
        member = value.get(field)
        if member is not None and type(member) is not str:
            raise CrossrefProductionQualificationError(
                f"item {index} {field} is invalid"
            )
    for field in ("published", "created"):
        member = value.get(field)
        if member is not None and not isinstance(member, dict):
            raise CrossrefProductionQualificationError(
                f"item {index} {field} is invalid"
            )
    return {
        "DOI": doi,
        "URL": value.get("URL"),
        "created": value.get("created"),
        "published": value.get("published"),
        "publisher": value.get("publisher"),
        "title": title,
        "type": value.get("type"),
    }


def _decode_response_json(payload: bytes) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate member")
            value[key] = item
        return value

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CrossrefProductionQualificationError(
            "response is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise CrossrefProductionQualificationError("response root is not an object")
    return value


def _request_profile_bytes() -> bytes:
    return _canonical_json_bytes(
        {
            "body": None,
            "headers": [
                ["Accept", "application/json"],
                ["Accept-Encoding", "identity"],
                [
                    "User-Agent",
                    (
                        "PastilaScout-CrossrefPilot "
                        "(+https://github.com/acidburn1danny/pastila-news-monitor)"
                    ),
                ],
            ],
            "host": "api.crossref.org",
            "maximum_attempts": 1,
            "maximum_pages": 1,
            "maximum_redirects": 0,
            "method": "GET",
            "port": 443,
            "scheme": "https",
            "target": (
                "/v1/works?rows=10&sort=published&order=asc&select="
                "DOI%2Ctitle%2Cpublisher%2Ctype%2Cpublished%2Ccreated%2CURL"
            ),
            "timeout_seconds": 15,
        }
    )


def _raw_capture_identity(
    status: int, headers: tuple[tuple[str, str], ...], body: bytes
) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "headers": headers,
                "request_identity": PHASE2_REQUEST_IDENTITY,
                "status": status,
            }
        )
    ).hexdigest()


def _integrate_and_publish(
    root: Path, normalized_bytes: bytes
) -> CrossrefProductionOutcomeV1:
    state_path = root / "integration-state.json"
    state_before = _load_qualified_state(state_path, normalized_bytes)
    result = integrate_crossref_normalized_bytes_v1(state_before, normalized_bytes)
    _publish_result(root, state_path, state_before, result)
    outcome = _outcome_from_result(state_before, normalized_bytes, result)
    _write_durable_new(root / "completion.json", outcome.canonical_bytes)
    return outcome


def _outcome_from_result(
    state_before: CrossrefIntegrationStateV1,
    normalized_bytes: bytes,
    result: CrossrefIntegrationResultV1,
) -> CrossrefProductionOutcomeV1:
    normalized_identity = hashlib.sha256(normalized_bytes).hexdigest()
    raw_identity = _raw_identity_from_normalized(normalized_bytes)
    return CrossrefProductionOutcomeV1(
        disposition=result.disposition,
        request_identity=PHASE2_REQUEST_IDENTITY,
        raw_capture_identity=raw_identity,
        normalized_identity=normalized_identity,
        state_before_identity=state_before.identity,
        state_after_identity=result.state.identity,
        batch_identity=None if result.batch is None else result.batch.identity,
        quarantine_identity=(
            None if result.quarantine is None else result.quarantine.identity
        ),
    )


def _publish_result(
    root: Path,
    state_path: Path,
    state_before: CrossrefIntegrationStateV1,
    result: CrossrefIntegrationResultV1,
) -> None:
    if result.disposition == "QUARANTINED":
        if result.state.identity != state_before.identity or result.quarantine is None:
            raise CrossrefProductionQualificationError(
                "quarantine attempted to mutate accepted state"
            )
        _atomic_publish_or_verify_existing(
            root / "quarantine.json",
            _canonical_json_bytes(result.quarantine.as_dict()),
        )
        return

    if result.batch is None:
        raise CrossrefProductionQualificationError("accepted result has no batch")
    if result.disposition == "IDEMPOTENT_REPLAY":
        if not state_path.exists() or result.state.identity != state_before.identity:
            raise CrossrefProductionQualificationError(
                "idempotent replay changed or lacked durable state"
            )
        return
    if state_path.exists():
        raise CrossrefProductionQualificationError(
            "accepted state destination already exists"
        )
    _atomic_publish_new(state_path, result.state.canonical_bytes)


def _load_qualified_state(
    state_path: Path, normalized_bytes: bytes
) -> CrossrefIntegrationStateV1:
    empty = CrossrefIntegrationStateV1()
    _reconcile_pending_publication(state_path)
    if not state_path.exists():
        return empty
    payload = _read_regular_file(state_path)
    expected = integrate_crossref_normalized_bytes_v1(empty, normalized_bytes)
    if expected.disposition != "ACCEPTED" or payload != expected.state.canonical_bytes:
        raise CrossrefProductionQualificationError(
            "durable state is not the qualified state for this capture"
        )
    return expected.state


def _atomic_publish_or_verify_existing(path: Path, payload: bytes) -> None:
    _reconcile_pending_publication(path)
    if path.exists():
        if path.is_symlink() or _read_regular_file(path) != payload:
            raise CrossrefProductionQualificationError(
                "published artifact differs from qualified bytes"
            )
        return
    _atomic_publish_new(path, payload)


def _reconcile_pending_publication(path: Path) -> None:
    pending = path.with_name(path.name + ".pending")
    if not pending.exists() and not pending.is_symlink():
        return
    if not path.exists() or path.is_symlink() or pending.is_symlink():
        if path.exists():
            raise CrossrefProductionQualificationError(
                "pending artifact is not the published-artifact hard-link"
            )
        return
    if not pending.samefile(path) or _read_regular_file(pending) != (
        _read_regular_file(path)
    ):
        raise CrossrefProductionQualificationError(
            "pending artifact is not the published-artifact hard-link"
        )
    pending.unlink()
    _sync_directory(path.parent)


def _load_complete_raw_capture(raw_root: Path) -> OfflineCrossrefResponseV1:
    if (
        raw_root.is_symlink()
        or not raw_root.is_dir()
        or (
            os.path.normcase(str(raw_root.resolve(strict=True)))
            != os.path.normcase(str(raw_root.absolute()))
        )
    ):
        raise CrossrefProductionQualificationError(
            "raw capture root must be a real contained directory"
        )
    manifest_path = raw_root / "manifest.json"
    manifest_bytes = _read_regular_file(manifest_path)
    manifest = _decode_exact_object(manifest_bytes)
    expected_fields = {
        "body_sha256",
        "capture_identity",
        "headers_sha256",
        "request_identity",
        "schema",
        "status",
        "wire_request_sha256",
    }
    if set(manifest) != expected_fields or manifest.get("schema") != (
        "pastila-crossref-pilot-raw-capture-v1"
    ):
        raise CrossrefProductionQualificationError("raw manifest schema mismatch")
    body = _read_regular_file(raw_root / "response-body.bin")
    header_bytes = _read_regular_file(raw_root / "response-headers.json")
    request_bytes = _read_regular_file(raw_root / "request.json")
    wire_bytes = _read_regular_file(raw_root / "wire-request.http")
    if request_bytes != _request_profile_bytes():
        raise CrossrefProductionQualificationError("raw request bytes mismatch")
    if wire_bytes != WIRE_REQUEST_BYTES or hashlib.sha256(wire_bytes).hexdigest() != (
        manifest.get("wire_request_sha256")
    ):
        raise CrossrefProductionQualificationError("wire request bytes mismatch")
    headers_value = _decode_exact_value(header_bytes)
    if not isinstance(headers_value, list):
        raise CrossrefProductionQualificationError("raw headers are not an array")
    try:
        headers = tuple(tuple(pair) for pair in headers_value)
        if (
            type(manifest["request_identity"]) is not str
            or type(manifest["status"]) is not int
        ):
            raise TypeError("raw manifest field type mismatch")
        response = OfflineCrossrefResponseV1(manifest["status"], headers, body)
    except (TypeError, ValueError) as exc:
        raise CrossrefProductionQualificationError(
            "raw capture reconstruction failed"
        ) from exc
    if (
        manifest["request_identity"] != PHASE2_REQUEST_IDENTITY
        or manifest.get("capture_identity") != PHASE2_RAW_CAPTURE_IDENTITY
        or hashlib.sha256(body).hexdigest() != manifest.get("body_sha256")
        or hashlib.sha256(header_bytes).hexdigest() != manifest.get("headers_sha256")
    ):
        raise CrossrefProductionQualificationError("raw capture identity mismatch")
    return response


def _load_completed_outcome(path: Path) -> CrossrefProductionOutcomeV1:
    value = _decode_exact_object(_read_regular_file(path))
    expected = {
        "batch_identity",
        "disposition",
        "normalized_identity",
        "quarantine_identity",
        "raw_capture_identity",
        "request_identity",
        "schema",
        "state_after_identity",
        "state_before_identity",
    }
    if set(value) != expected or value.get("schema") != SCHEMA:
        raise CrossrefProductionQualificationError("completion schema mismatch")
    try:
        return CrossrefProductionOutcomeV1(
            disposition=value["disposition"],
            request_identity=value["request_identity"],
            raw_capture_identity=value["raw_capture_identity"],
            normalized_identity=value["normalized_identity"],
            state_before_identity=value["state_before_identity"],
            state_after_identity=value["state_after_identity"],
            batch_identity=value["batch_identity"],
            quarantine_identity=value["quarantine_identity"],
        )
    except (TypeError, ValueError) as exc:
        raise CrossrefProductionQualificationError("completion is invalid") from exc


def _raw_identity_from_normalized(payload: bytes) -> str:
    value = _decode_exact_object(payload)
    identity = value.get("raw_capture_identity")
    _require_sha256(identity, "normalized raw capture identity")
    return identity


def _require_new_execution_root(path: Path) -> Path:
    if not isinstance(path, Path) or path.exists() or path.is_symlink():
        raise CrossrefProductionQualificationError("execution root must be a new Path")
    parent = path.parent.resolve(strict=True)
    if not parent.is_dir() or os.path.normcase(str(parent)) != os.path.normcase(
        str(path.parent.absolute())
    ):
        raise CrossrefProductionQualificationError(
            "execution root parent must be a real directory"
        )
    path.mkdir(mode=0o700)
    _sync_directory(parent)
    return path.resolve(strict=True)


def _require_existing_execution_root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_dir() or path.is_symlink():
        raise CrossrefProductionQualificationError(
            "execution root must be an existing real directory"
        )
    resolved = path.resolve(strict=True)
    if os.path.normcase(str(resolved)) != os.path.normcase(str(path.absolute())):
        raise CrossrefProductionQualificationError(
            "execution root must not traverse a symlink"
        )
    return resolved


def _read_regular_file(path: Path) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise CrossrefProductionQualificationError(
            f"required artifact is unavailable: {path.name}"
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise CrossrefProductionQualificationError(
            f"required artifact is not a regular file: {path.name}"
        )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise CrossrefProductionQualificationError(
                f"artifact changed before open: {path.name}"
            )
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65_536))
            if not chunk:
                raise CrossrefProductionQualificationError(
                    f"artifact truncated while being read: {path.name}"
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise CrossrefProductionQualificationError(
                f"artifact grew while being read: {path.name}"
            )
        after = os.fstat(descriptor)
        if (
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise CrossrefProductionQualificationError(
                f"artifact changed while being read: {path.name}"
            )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _atomic_publish_new(path: Path, payload: bytes) -> None:
    pending = path.with_name(path.name + ".pending")
    if pending.exists():
        if pending.is_symlink() or _read_regular_file(pending) != payload:
            raise CrossrefProductionQualificationError(
                "pending publication does not match qualified state"
            )
    else:
        _write_durable_new(pending, payload)
    try:
        os.link(pending, path)
    except FileExistsError as exc:
        raise CrossrefProductionQualificationError(
            "publication target already exists"
        ) from exc
    pending.unlink()
    _sync_directory(path.parent)


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


def _decode_exact_object(payload: bytes) -> dict[str, object]:
    value = _decode_exact_value(payload)
    if not isinstance(value, dict):
        raise CrossrefProductionQualificationError("artifact root is not an object")
    return value


def _decode_exact_value(payload: bytes) -> object:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate member")
            value[key] = item
        return value

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CrossrefProductionQualificationError(
            "artifact is not valid JSON"
        ) from exc
    if _canonical_json_bytes(value) != payload:
        raise CrossrefProductionQualificationError("artifact is not canonical JSON")
    return value


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
        raise CrossrefProductionQualificationError(f"{field} must be lowercase SHA-256")


def _require_runtime_authority() -> None:
    if (
        integrate_crossref_normalized_bytes_v1
        is not _integration_authority.integrate_crossref_normalized_bytes_v1
        or any(
            globals().get(name) is not authority
            for name, authority in _LOCAL_RUNTIME_CLOSURE
        )
    ):
        raise CrossrefProductionQualificationError(
            "Phase 4 runtime authority was rebound"
        )
    source = Path(_integration_authority.__file__).resolve(strict=True)
    if hashlib.sha256(source.read_bytes()).hexdigest() != PHASE3_IMPLEMENTATION_SHA256:
        raise CrossrefProductionQualificationError(
            "Phase 4 dependency source identity mismatch"
        )
    if any(
        getattr(_integration_authority, name, None) is not authority
        for name, authority in _INTEGRATION_RUNTIME_CLOSURE
    ):
        raise CrossrefProductionQualificationError(
            "Phase 4 dependency runtime closure was rebound"
        )


_INTEGRATION_RUNTIME_CLOSURE = tuple(
    (name, getattr(_integration_authority, name))
    for name in (
        "CrossrefIntegratedRecordV1",
        "CrossrefIntegrationBatchV1",
        "CrossrefIntegrationQuarantineV1",
        "CrossrefIntegrationResultV1",
        "CrossrefIntegrationStateV1",
        "_canonical_json_bytes",
        "_decode_document",
        "_map_record",
        "integrate_crossref_normalized_bytes_v1",
    )
)
_LOCAL_RUNTIME_CLOSURE = tuple(
    (name, globals()[name])
    for name in (
        "OfflineCrossrefResponseV1",
        "_atomic_publish_new",
        "_atomic_publish_or_verify_existing",
        "_consume_attempt",
        "_decode_response_json",
        "_load_complete_raw_capture",
        "_normalize_exact_snapshot",
        "_normalize_item",
        "_read_regular_file",
        "_reconcile_pending_publication",
        "_record_raw_snapshot",
        "_request_profile_bytes",
        "_write_durable_new",
    )
)


__all__ = (
    "EXECUTION_ROOT_RELATIVE",
    "SCHEMA",
    "CrossrefProductionOutcomeV1",
    "CrossrefProductionQualificationError",
    "OfflineCrossrefResponseV1",
    "authorized_qualification_root_v1",
    "execute_offline_crossref_production_qualification_v1",
    "recover_offline_crossref_production_qualification_v1",
)
