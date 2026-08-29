"""Fail-closed durable filesystem sink for Construction-Obligation V2.

This module creates and writes only a newly created, caller-bound evidence
root.  It contains no process, WSL, model, tokenizer, or generation surface.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

DURABLE_FILESYSTEM_SINK_IDENTITY = (
    "3fa09e642eb256daeae03622e133b48fe717ec640e4b2dc52a74407de573f14e"
)
SUPERVISOR_CANDIDATE_IDENTITY = (
    "ce43ed32836005bcd471da40f9003e3d9ba66e090e57fbf66cdf77d0c8b95391"
)
SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1 = (
    "b2b0c3c72d7fe8bc7b34c247361f50f18991e2b17d296c4ecc7a92ac6f4025c1"
)
CLEANUP_EXTENSION_IDENTITY = (
    "4636f0937ebc620f3fe086e9ae69ee5e21884cbf6e73cbee69a90962dab1c136"
)
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_COUNT = 256

_LABEL = re.compile(r"[a-z0-9][a-z0-9.-]{0,119}\Z")
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _identity(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class DurableEvidenceRootBindingV1:
    provider_request_id: str
    source_context_identity: str
    authority_receipt_identity: str
    supervisor_candidate_identity: str


@dataclass(frozen=True, slots=True)
class DurableArtifactReceiptV1:
    sink_identity: str
    sink_instance_identity: str
    label: str
    byte_count: int
    sha256: str
    receipt_identity: str
    canonical_receipt: bytes


class DurableFilesystemSinkV1:
    """Exclusive, atomic publisher into one immutable caller-bound root."""

    __slots__ = (
        "_labels",
        "_root",
        "_root_resolved",
        "binding",
        "sink_instance_identity",
    )

    def __init__(
        self,
        *,
        root: Path,
        root_resolved: Path,
        binding: DurableEvidenceRootBindingV1,
        sink_instance_identity: str,
    ) -> None:
        self._root = root
        self._root_resolved = root_resolved
        self.binding = binding
        self.sink_instance_identity = sink_instance_identity
        self._labels: set[str] = set()

    @property
    def root(self) -> Path:
        return self._root

    def persist(self, label: str, raw: bytes) -> DurableArtifactReceiptV1:
        if type(label) is not str or _LABEL.fullmatch(label) is None:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_LABEL_INVALID")
        if type(raw) is not bytes:
            raise TypeError(
                "CONSTRUCTION_OBLIGATION_V2_DURABLE_BYTES_EXACT_TYPE_REQUIRED"
            )
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ARTIFACT_TOO_LARGE")
        if label in self._labels:
            raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_DURABLE_LABEL_DUPLICATE")
        if len(self._labels) >= MAX_ARTIFACT_COUNT:
            raise ValueError(
                "CONSTRUCTION_OBLIGATION_V2_DURABLE_ARTIFACT_COUNT_EXCEEDED"
            )
        self._verify_root()

        target = self._root / label
        if target.exists() or target.is_symlink():
            raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_DURABLE_TARGET_EXISTS")
        pending = self._root / (".pending-" + uuid.uuid4().hex)
        descriptor: int | None = None
        published = False
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = os.open(pending, flags, 0o600)
            view = memoryview(raw)
            written = 0
            while written < len(view):
                count = os.write(descriptor, view[written:])
                if count <= 0:
                    raise OSError("CONSTRUCTION_OBLIGATION_V2_DURABLE_SHORT_WRITE")
                written += count
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            self._verify_root()
            os.link(pending, target)
            published = True
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            raise
        finally:
            try:
                pending.unlink(missing_ok=True)
            except OSError:
                if not published:
                    pass

        self._verify_published(target=target, raw=raw)
        self._labels.add(label)
        digest = hashlib.sha256(raw).hexdigest()
        body = {
            "artifact_byte_count": len(raw),
            "artifact_label": label,
            "artifact_sha256": digest,
            "sink_identity": DURABLE_FILESYSTEM_SINK_IDENTITY,
            "sink_instance_identity": self.sink_instance_identity,
        }
        receipt_identity = _identity(body)
        receipt = {**body, "receipt_identity": receipt_identity}
        return DurableArtifactReceiptV1(
            DURABLE_FILESYSTEM_SINK_IDENTITY,
            self.sink_instance_identity,
            label,
            len(raw),
            digest,
            receipt_identity,
            _canonical(receipt),
        )

    def _verify_root(self) -> None:
        if _is_link_or_reparse(self._root):
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_REPARSE_FORBIDDEN"
            )
        if not self._root.is_dir():
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_MISSING")
        if self._root.resolve(strict=True) != self._root_resolved:
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_IDENTITY_CHANGED"
            )

    @staticmethod
    def _verify_published(*, target: Path, raw: bytes) -> None:
        if _is_link_or_reparse(target):
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_DURABLE_TARGET_REPARSE_FORBIDDEN"
            )
        metadata = target.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_TARGET_NOT_REGULAR")
        observed = target.read_bytes()
        if (
            len(observed) != len(raw)
            or hashlib.sha256(observed).digest() != hashlib.sha256(raw).digest()
        ):
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_POST_WRITE_MISMATCH")


def create_durable_filesystem_sink_v1(
    *,
    root: Path,
    binding: DurableEvidenceRootBindingV1,
) -> DurableFilesystemSinkV1:
    if not isinstance(root, Path):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_PATH_REQUIRED")
    if type(binding) is not DurableEvidenceRootBindingV1:
        raise TypeError(
            "CONSTRUCTION_OBLIGATION_V2_DURABLE_BINDING_EXACT_TYPE_REQUIRED"
        )
    return _create_durable_filesystem_sink(
        root=root,
        binding=binding,
        expected_supervisor_candidate_identity=SUPERVISOR_CANDIDATE_IDENTITY,
    )


def create_durable_filesystem_sink_v1_2_1(
    *,
    root: Path,
    binding: DurableEvidenceRootBindingV1,
) -> DurableFilesystemSinkV1:
    """Create a sink admitted only for the exact V1.2.1 supervisor."""
    if not isinstance(root, Path):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_PATH_REQUIRED")
    if type(binding) is not DurableEvidenceRootBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_BINDING_EXACT_TYPE_REQUIRED")
    return _create_durable_filesystem_sink(
        root=root,
        binding=binding,
        expected_supervisor_candidate_identity=SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1,
    )


def _create_durable_filesystem_sink(
    *, root: Path, binding: DurableEvidenceRootBindingV1,
    expected_supervisor_candidate_identity: str,
) -> DurableFilesystemSinkV1:
    _validate_binding(
        binding,
        expected_supervisor_candidate_identity=expected_supervisor_candidate_identity,
    )
    if not root.name or root.name in {".", ".."} or not root.is_absolute():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_INVALID")
    if root.exists() or root.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_ALREADY_EXISTS")
    parent = root.parent
    if _is_link_or_reparse(parent) or not parent.is_dir():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_PARENT_INVALID")
    parent_resolved = parent.resolve(strict=True)
    if parent_resolved != parent:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_PARENT_NOT_CANONICAL")
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    if _is_link_or_reparse(root) or not root.is_dir() or any(root.iterdir()):
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_ROOT_CREATION_INVALID")
    root_resolved = root.resolve(strict=True)
    body = {
        "authority_receipt_identity": binding.authority_receipt_identity,
        "provider_request_id": binding.provider_request_id,
        "root": os.path.normcase(str(root_resolved)),
        "sink_identity": DURABLE_FILESYSTEM_SINK_IDENTITY,
        "source_context_identity": binding.source_context_identity,
        "supervisor_candidate_identity": binding.supervisor_candidate_identity,
    }
    return DurableFilesystemSinkV1(
        root=root,
        root_resolved=root_resolved,
        binding=binding,
        sink_instance_identity=_identity(body),
    )


def _validate_binding(
    binding: DurableEvidenceRootBindingV1,
    *,
    expected_supervisor_candidate_identity: str = SUPERVISOR_CANDIDATE_IDENTITY,
) -> None:
    if (
        type(binding.provider_request_id) is not str
        or not binding.provider_request_id
        or len(binding.provider_request_id) > 256
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_REQUEST_ID_INVALID")
    if (
        _HEX_64.fullmatch(binding.source_context_identity) is None
        or _HEX_64.fullmatch(binding.authority_receipt_identity) is None
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DURABLE_BINDING_IDENTITY_INVALID")
    if binding.supervisor_candidate_identity != expected_supervisor_candidate_identity:
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_DURABLE_SUPERVISOR_IDENTITY_MISMATCH"
        )


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.stat().st_file_attributes
    except (AttributeError, FileNotFoundError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


__all__ = [
    "CLEANUP_EXTENSION_IDENTITY",
    "DURABLE_FILESYSTEM_SINK_IDENTITY",
    "MAX_ARTIFACT_BYTES",
    "MAX_ARTIFACT_COUNT",
    "SUPERVISOR_CANDIDATE_IDENTITY",
    "SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1",
    "DurableArtifactReceiptV1",
    "DurableEvidenceRootBindingV1",
    "DurableFilesystemSinkV1",
    "create_durable_filesystem_sink_v1",
    "create_durable_filesystem_sink_v1_2_1",
]
