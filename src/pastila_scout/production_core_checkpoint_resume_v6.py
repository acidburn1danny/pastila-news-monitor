"""Fail-closed checkpoint chain for one resumable qualification attempt."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path


class CheckpointError(ValueError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CheckpointError(f"checkpoint path rejected: {path.name}")
    return path.read_bytes()


def artifact_closure(directory: Path) -> list[dict[str, object]]:
    if directory.is_symlink() or not directory.is_dir():
        raise CheckpointError("checkpoint directory rejected")
    rows = []
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix().encode()):
        if path.is_dir() and not path.is_symlink():
            continue
        raw = _regular_bytes(path)
        rows.append({
            "path": path.relative_to(directory).as_posix(),
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    if not rows:
        raise CheckpointError("empty checkpoint closure")
    return rows


def build_receipt(
    *, attempt_identity: str, execution_authority_identity: str,
    generation_identity: str, checkpoint_ordinal: int,
    previous_checkpoint_identity: str | None, batch: Mapping[str, object],
    directory: Path, directory_binding: str | None = None,
) -> dict[str, object]:
    if checkpoint_ordinal not in range(1, 13):
        raise CheckpointError("checkpoint ordinal rejected")
    rows = batch.get("batch")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) != 200:
        raise CheckpointError("checkpoint batch cardinality mismatch")
    core = {
        "schema": "pastila-production-core-qualification-checkpoint-receipt",
        "schema_version": 6,
        "attempt_identity": attempt_identity,
        "execution_authority_identity": execution_authority_identity,
        "qualification_generation_identity": generation_identity,
        "checkpoint_ordinal": checkpoint_ordinal,
        "previous_checkpoint_identity": previous_checkpoint_identity,
        "batch_coordinates": {key: batch[key] for key in ("materialization", "repetition", "candidate_alias")},
        "batch_sha256": batch["batch_sha256"],
        "batch_directory": directory_binding or directory.name,
        "finalized_rows": 200,
        "first_global_ordinal": batch["first_global_ordinal"],
        "last_global_ordinal": batch["last_global_ordinal"],
        "artifact_closure": artifact_closure(directory),
        "retry_or_redraw": False,
        "same_attempt_resume_only": True,
    }
    return {**core, "checkpoint_identity": identity(core)}


def write_receipt(path: Path, receipt: Mapping[str, object]) -> None:
    raw = canonical(receipt)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise CheckpointError("checkpoint receipt substitution")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_chain(
    root: Path, *, attempt_identity: str, execution_authority_identity: str,
    generation_identity: str, batches: Sequence[Mapping[str, object]],
) -> tuple[int, str | None]:
    if len(batches) != 12:
        raise CheckpointError("exactly twelve checkpoint batches required")
    previous = None
    accepted = 0
    for ordinal, batch in enumerate(batches, 1):
        receipt_path = root / f"checkpoint-{ordinal:02d}.json"
        if not receipt_path.exists():
            if any((root / f"checkpoint-{later:02d}.json").exists() for later in range(ordinal + 1, 13)):
                raise CheckpointError("non-contiguous checkpoint chain")
            break
        try:
            receipt = json.loads(_regular_bytes(receipt_path))
        except json.JSONDecodeError as exc:
            raise CheckpointError("checkpoint receipt malformed") from exc
        core = dict(receipt)
        claimed = core.pop("checkpoint_identity", None)
        if tuple(receipt) != (
            "schema", "schema_version", "attempt_identity", "execution_authority_identity",
            "qualification_generation_identity", "checkpoint_ordinal",
            "previous_checkpoint_identity", "batch_coordinates", "batch_sha256",
            "batch_directory", "finalized_rows", "first_global_ordinal",
            "last_global_ordinal", "artifact_closure", "retry_or_redraw",
            "same_attempt_resume_only", "checkpoint_identity",
        ) or receipt.get("schema") != "pastila-production-core-qualification-checkpoint-receipt" or receipt.get("schema_version") != 6:
            raise CheckpointError("checkpoint receipt shape mismatch")
        directory_name = receipt.get("batch_directory")
        if not isinstance(directory_name, str):
            raise CheckpointError("checkpoint directory binding malformed")
        parts = Path(directory_name).parts
        if not parts or any(part in {"", ".", ".."} for part in parts) or Path(directory_name).is_absolute():
            raise CheckpointError("checkpoint directory binding malformed")
        directory = root.joinpath(*parts)
        expected = {
            "attempt_identity": attempt_identity,
            "execution_authority_identity": execution_authority_identity,
            "qualification_generation_identity": generation_identity,
            "checkpoint_ordinal": ordinal,
            "previous_checkpoint_identity": previous,
            "batch_sha256": batch["batch_sha256"],
            "batch_coordinates": {key: batch[key] for key in ("materialization", "repetition", "candidate_alias")},
            "first_global_ordinal": batch["first_global_ordinal"],
            "last_global_ordinal": batch["last_global_ordinal"],
        }
        if claimed != identity(core) or any(receipt.get(k) != v for k, v in expected.items()):
            raise CheckpointError("checkpoint identity/binding mismatch")
        if receipt.get("finalized_rows") != 200 or receipt.get("retry_or_redraw") is not False or receipt.get("same_attempt_resume_only") is not True:
            raise CheckpointError("checkpoint semantics mismatch")
        closure = receipt.get("artifact_closure")
        if not isinstance(closure, list) or len({row.get("path") for row in closure if isinstance(row, dict)}) != len(closure) or closure != artifact_closure(directory):
            raise CheckpointError("checkpoint artifact closure mismatch")
        previous = str(claimed)
        accepted = ordinal
    return accepted, previous


__all__ = ["CheckpointError", "artifact_closure", "build_receipt", "validate_chain", "write_receipt"]
