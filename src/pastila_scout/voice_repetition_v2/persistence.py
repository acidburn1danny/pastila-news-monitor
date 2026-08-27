"""Canonical persistence primitives for the repetition transaction store."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_bytes

from .ledger import finalize_ledger_v1
from .models import VoiceAcceptanceReceiptV1, VoiceRepetitionLedgerV1


class VoiceAcceptancePersistenceError(ValueError):
    pass


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_canonical[T: BaseModel](
    path: Path, model: type[T], *, name: str, version: str
) -> T:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VoiceAcceptancePersistenceError("invalid canonical JSON") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_name") != name
        or payload.get("schema_version") != version
    ):
        raise VoiceAcceptancePersistenceError("unknown persistence schema/version")
    try:
        value = model.model_validate(payload)
    except ValidationError as exc:
        raise VoiceAcceptancePersistenceError("invalid persisted structure") from exc
    if canonical_bytes(value) != raw:
        raise VoiceAcceptancePersistenceError("persisted bytes are noncanonical")
    return value


def load_ledger(path: Path) -> VoiceRepetitionLedgerV1:
    value = load_canonical(
        path,
        VoiceRepetitionLedgerV1,
        name="pastilaacida-voice-repetition-ledger",
        version="1",
    )
    if finalize_ledger_v1(value) != value:
        raise VoiceAcceptancePersistenceError("ledger identity mismatch")
    return value


def load_receipt(path: Path) -> VoiceAcceptanceReceiptV1:
    return load_canonical(
        path,
        VoiceAcceptanceReceiptV1,
        name="pastilaacida-voice-acceptance-receipt",
        version="1",
    )


__all__ = [
    "VoiceAcceptancePersistenceError",
    "atomic_write",
    "load_canonical",
    "load_ledger",
    "load_receipt",
]
