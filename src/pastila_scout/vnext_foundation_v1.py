"""Isolated shared primitives for the VNext modular monolith boundary."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
_LEGACY_PATH_PATTERNS = (
    re.compile(r"(?:^|[\"'])/root/pf9(?:[-_/]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[\"'])/mnt/[cf]/(?:pf9|pt)(?:[/\\]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[\"'])[cf]:\\(?:pf9|pt)(?:\\|$)", re.IGNORECASE),
    re.compile(r"\b(?:from|import)\s+(?:legacy|pf9)(?:\.|\b)", re.IGNORECASE),
    re.compile(r"\bPYTHONPATH\b[^\n]*(?:pf9|legacy)", re.IGNORECASE),
)
_LEGACY_DEPENDENCY_ID = re.compile(r"(?:^|[-_.])(?:legacy|pf9)(?:$|[-_.])", re.IGNORECASE)


class BoundaryError(RuntimeError):
    """Base fail-closed boundary error."""


class ContainmentError(BoundaryError):
    pass


class ImmutableConflict(BoundaryError):
    pass


class DependencyError(BoundaryError):
    pass


def canonical_json(value: object) -> bytes:
    """Return the only canonical JSON representation used by this boundary."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def object_identity(value: object) -> str:
    return sha256_bytes(canonical_json(value))


def validate_schema(value: Mapping[str, object], schema: str, version: int = SCHEMA_VERSION) -> None:
    if value.get("schema") != schema or value.get("schema_version") != version:
        raise BoundaryError(f"schema mismatch: expected {schema}@{version}")


def contained_path(root: Path, candidate: Path, *, allow_missing: bool = True) -> Path:
    root = root.resolve(strict=True)
    absolute = candidate if candidate.is_absolute() else root / candidate
    if not allow_missing and not absolute.exists():
        raise ContainmentError(f"missing path: {absolute}")
    resolved = absolute.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContainmentError(f"path escapes root: {candidate}") from exc
    current = root
    for part in resolved.relative_to(root).parts[:-1]:
        current /= part
        if current.is_symlink():
            target = current.resolve(strict=False)
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ContainmentError(f"symlink escapes root: {current} -> {target}") from exc
    return resolved


def atomic_write(path: Path, payload: bytes, *, root: Path, overwrite: bool = True) -> None:
    """Publish one file with temp -> flush/fsync -> replace semantics."""
    destination = contained_path(root, path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = contained_path(root, destination)
    if destination.exists() and not overwrite:
        raise ImmutableConflict(f"immutable path exists: {destination}")
    temporary = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    temporary = contained_path(root, temporary)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists() and not overwrite:
            raise ImmutableConflict(f"immutable path exists: {destination}")
        os.replace(temporary, destination)
        if hasattr(os, "O_DIRECTORY"):
            directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, value: object, *, root: Path, overwrite: bool = True) -> None:
    atomic_write(path, canonical_json(value) + b"\n", root=root, overwrite=overwrite)


def interrupted_files(root: Path) -> list[Path]:
    root = root.resolve(strict=True)
    return sorted(path for path in root.rglob(".*.tmp-*") if path.is_file())


def recover_interrupted_writes(root: Path) -> list[str]:
    """Remove unpublished temp files; never synthesize or publish state."""
    removed: list[str] = []
    for path in interrupted_files(root):
        safe = contained_path(root, path, allow_missing=False)
        removed.append(safe.relative_to(root.resolve()).as_posix())
        safe.unlink()
    return removed


def write_immutable_receipt(path: Path, receipt: Mapping[str, object], *, root: Path) -> str:
    validate_schema(receipt, "vnext-operational-receipt")
    receipt_identity = object_identity({
        key: value for key, value in receipt.items()
        if key not in {"observed_at", "provenance", "receipt_identity"}
    })
    if receipt.get("receipt_identity") != receipt_identity:
        raise BoundaryError("receipt identity mismatch")
    atomic_json(path, dict(receipt), root=root, overwrite=False)
    return receipt_identity


def tree_identity(root: Path) -> str:
    root = root.resolve(strict=True)
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append({"path": relative, "type": "file", "sha256": sha256_bytes(path.read_bytes()), "size": path.stat().st_size})
    return object_identity(entries)


def legacy_bindings_in_text(text: str) -> list[str]:
    return [pattern.pattern for pattern in _LEGACY_PATH_PATTERNS if pattern.search(text)]


def scan_legacy_dependencies(root: Path, *, maximum_text_bytes: int = 2_000_000) -> list[dict[str, str]]:
    """Scan path/import bindings while ignoring benign prose such as 'legacy reporting'."""
    root = root.resolve(strict=True)
    findings: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            target = os.readlink(path)
            if legacy_bindings_in_text(target):
                findings.append({"kind": "LEGACY_SYMLINK", "path": relative, "binding": target})
            continue
        if not path.is_file() or path.stat().st_size > maximum_text_bytes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in legacy_bindings_in_text(text):
            findings.append({"kind": "LEGACY_TEXT_BINDING", "path": relative, "binding": pattern})
    return findings


@dataclass(frozen=True)
class DependencyReport:
    checked: tuple[str, ...]
    legacy_dependency_count: int
    identity: str


def _relative_lock_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ContainmentError(f"invalid dependency path: {value}")
    return path


def validate_dependency_lock(lock: Mapping[str, object], *, root: Path) -> DependencyReport:
    validate_schema(lock, "vnext-dependency-lock")
    items = lock.get("dependencies")
    if not isinstance(items, list) or not items:
        raise DependencyError("dependencies must be a non-empty list")
    by_id: dict[str, Mapping[str, object]] = {}
    for raw in items:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            raise DependencyError("invalid dependency entry")
        if raw["id"] in by_id:
            raise DependencyError(f"duplicate dependency: {raw['id']}")
        by_id[str(raw["id"])] = raw
    checked: list[str] = []
    legacy_count = 0
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(dependency_id: str) -> None:
        nonlocal legacy_count
        if dependency_id in visited:
            return
        if dependency_id in visiting:
            raise DependencyError(f"dependency cycle: {dependency_id}")
        if dependency_id not in by_id:
            raise DependencyError(f"undeclared dependency: {dependency_id}")
        visiting.add(dependency_id)
        item = by_id[dependency_id]
        if _LEGACY_DEPENDENCY_ID.search(dependency_id):
            legacy_count += 1
        expected_path = item.get("path")
        expected_identity = item.get("identity")
        if not isinstance(expected_path, str) or not isinstance(expected_identity, str):
            raise DependencyError(f"invalid binding: {dependency_id}")
        relative = _relative_lock_path(expected_path)
        if legacy_bindings_in_text(expected_path):
            legacy_count += 1
        bound = contained_path(root, Path(*relative.parts), allow_missing=False)
        if bound.is_symlink():
            target = bound.resolve(strict=True)
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ContainmentError(f"dependency symlink escapes root: {bound}") from exc
        if bound.is_file() and stat.S_ISREG(bound.stat().st_mode) and bound.stat().st_nlink > 1:
            raise ContainmentError(f"hardlinked dependency rejected: {bound}")
        actual_identity = sha256_bytes(bound.read_bytes()) if bound.is_file() else tree_identity(bound)
        if actual_identity != expected_identity:
            raise DependencyError(f"identity mismatch: {dependency_id}")
        declared = item.get("depends_on", [])
        if not isinstance(declared, list) or not all(isinstance(value, str) for value in declared):
            raise DependencyError(f"invalid transitive dependencies: {dependency_id}")
        for child in declared:
            visit(child)
        visiting.remove(dependency_id)
        visited.add(dependency_id)
        checked.append(dependency_id)

    roots = lock.get("roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(value, str) for value in roots):
        raise DependencyError("lock roots required")
    for dependency_id in roots:
        visit(dependency_id)
    if visited != set(by_id):
        missing = sorted(set(by_id) - visited)
        raise DependencyError(f"unreachable dependencies: {missing}")
    forbidden = lock.get("forbidden_dependencies", [])
    if not isinstance(forbidden, list):
        raise DependencyError("forbidden_dependencies must be a list")
    forbidden_ids = {value for value in forbidden if isinstance(value, str)}
    selected_forbidden = sorted(visited & forbidden_ids)
    if selected_forbidden:
        raise DependencyError(f"forbidden dependencies selected: {selected_forbidden}")
    legacy_count += sum(1 for value in forbidden if isinstance(value, str) and legacy_bindings_in_text(value))
    legacy_count += len(scan_legacy_dependencies(root))
    if legacy_count:
        raise DependencyError(f"legacy dependencies found: {legacy_count}")
    payload = {"checked": sorted(checked), "legacy_dependency_count": legacy_count}
    return DependencyReport(tuple(sorted(checked)), legacy_count, object_identity(payload))


def preflight(lock: Mapping[str, object], *, root: Path, required_capabilities: Iterable[str] = ()) -> dict[str, object]:
    report = validate_dependency_lock(lock, root=root)
    capabilities = sorted(set(required_capabilities))
    result = {
        "schema": "vnext-foundation-preflight",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "dependencies": list(report.checked),
        "dependency_report_identity": report.identity,
        "capabilities": capabilities,
        "legacy_dependency_count": report.legacy_dependency_count,
    }
    result["preflight_identity"] = object_identity(result)
    return result
