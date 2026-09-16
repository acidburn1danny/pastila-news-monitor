"""Strict, non-secret recovery manifest support for the published V12 checkpoint."""
from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SCHEMA = "pastila-production-core-v12-clean-recovery"
SCHEMA_VERSION = 1
IDENTITY_FIELD = "recovery_manifest_identity"


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flat_tar_identity(path: Path) -> tuple[str, int, int]:
    """Return the canonical flat-object identity without extracting the tar."""
    records: list[bytes] = []
    total = 0
    with tarfile.open(path, "r:") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        members.sort(key=lambda member: PurePosixPath(member.name).name.encode())
        names = [PurePosixPath(member.name).name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("duplicate flat archive member")
        for member, name in zip(members, names, strict=True):
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"unreadable archive member: {name}")
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
            records.append(
                name.encode() + b"\0" + member.size.to_bytes(8, "big") + digest.digest()
            )
            total += member.size
    return hashlib.sha256(b"".join(records)).hexdigest(), len(records), total


def seal(core: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(core)
    value[IDENTITY_FIELD] = hashlib.sha256(canonical(value)).hexdigest()
    return value


def validate(value: Mapping[str, Any]) -> None:
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("recovery schema mismatch")
    core = dict(value)
    claimed = core.pop(IDENTITY_FIELD, None)
    if claimed != hashlib.sha256(canonical(core)).hexdigest():
        raise ValueError("recovery manifest seal mismatch")
    repository = value["repository"]
    if repository["canonical_branch"] != "successor/core-v2-v12-runner-binding-remediation":
        raise ValueError("canonical branch mismatch")
    checkpoint = repository["source_checkpoint"]
    if checkpoint != {
        "commit": "2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f",
        "tree": "3c83e9901cbc743f0b83feeeab19e5724206b977",
    }:
        raise ValueError("V12 checkpoint mismatch")
    if value["v12"]["runner_identity"] != "b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29":
        raise ValueError("V12 runner mismatch")
    state = value["execution_state"]
    if state != {
        "successor_authority_built": False,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }:
        raise ValueError("execution state mismatch")
    if value["remaining_blockers"]:
        raise ValueError("recovery manifest contains blockers")


def verify_external_objects(value: Mapping[str, Any], object_root: Path) -> None:
    for item in value["external_objects"]:
        path = object_root / item["backup_name"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing external object: {item['logical_name']}")
        if path.stat().st_size != item["archive_bytes"]:
            raise ValueError(f"external object size mismatch: {item['logical_name']}")
        if sha256_file(path) != item["archive_sha256"]:
            raise ValueError(f"external archive hash mismatch: {item['logical_name']}")
        if item.get("flat_content_identity"):
            identity, files, total = flat_tar_identity(path)
            if (identity, files, total) != (
                item["flat_content_identity"], item["content_files"], item["content_bytes"]
            ):
                raise ValueError(f"external content mismatch: {item['logical_name']}")
