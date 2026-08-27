"""Canonical persistence for Voice V2 eligibility and owner selection state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)

from .engine import VoiceEligibilityIntegrityError
from .models import (
    SHA256_PATTERN,
    ZERO_IDENTITY,
    FrozenModel,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)


class UnknownVoiceEligibilityStateVersionError(ValueError):
    pass


class VoiceEligibilityStateV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-eligibility-selection-state"] = (
        "pastilaacida-voice-eligibility-selection-state"
    )
    schema_version: Literal["1"] = "1"
    repetition_snapshot: VoiceRepetitionSnapshotV1
    eligibility_result: VoiceEligibilityResultV1
    selection_receipt: VoiceOwnerSelectionReceiptV1
    state_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256_PATTERN)


def _sealed(value, field: str) -> str:
    return canonical_identity(value.model_copy(update={field: ZERO_IDENTITY}))


def finalize_state_identity(state: VoiceEligibilityStateV1) -> VoiceEligibilityStateV1:
    return state.model_copy(update={"state_identity": _sealed(state, "state_identity")})


def validate_state(state: VoiceEligibilityStateV1) -> None:
    if state.state_identity != _sealed(state, "state_identity"):
        raise VoiceEligibilityIntegrityError("eligibility state identity mismatch")
    result = state.eligibility_result
    receipt = state.selection_receipt
    snapshot = state.repetition_snapshot
    if result.result_identity != _sealed(result, "result_identity"):
        raise VoiceEligibilityIntegrityError("eligibility result identity mismatch")
    if snapshot.snapshot_identity != _sealed(snapshot, "snapshot_identity"):
        raise VoiceEligibilityIntegrityError("repetition snapshot identity mismatch")
    if receipt.receipt_identity != _sealed(receipt, "receipt_identity"):
        raise VoiceEligibilityIntegrityError("selection receipt identity mismatch")
    if receipt.eligibility_result_identity != result.result_identity:
        raise VoiceEligibilityIntegrityError("stored selection/result mismatch")
    if receipt.repetition_snapshot_identity != snapshot.snapshot_identity:
        raise VoiceEligibilityIntegrityError("stored selection/snapshot mismatch")
    if receipt.shortlist_candidate_ids != tuple(
        item.candidate_id for item in result.shortlist
    ):
        raise VoiceEligibilityIntegrityError("stored shortlist mismatch")


class VoiceEligibilityStateStoreV1:
    def __init__(self, path: Path):
        self.path = path

    def save(self, state: VoiceEligibilityStateV1) -> str:
        validate_state(state)
        raw = canonical_bytes(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()
        if self.path.read_bytes() != raw:
            raise VoiceEligibilityIntegrityError("eligibility state read-back mismatch")
        return canonical_identity(state)

    def load(self) -> VoiceEligibilityStateV1:
        raw = self.path.read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VoiceEligibilityIntegrityError(
                "invalid eligibility state JSON"
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_name")
            != "pastilaacida-voice-eligibility-selection-state"
            or value.get("schema_version") != "1"
        ):
            raise UnknownVoiceEligibilityStateVersionError(
                "unsupported Voice eligibility state version"
            )
        try:
            state = VoiceEligibilityStateV1.model_validate(value)
        except ValidationError as exc:
            raise VoiceEligibilityIntegrityError("invalid eligibility state") from exc
        if canonical_bytes(state) != raw:
            raise VoiceEligibilityIntegrityError("eligibility state is not canonical")
        validate_state(state)
        return state


__all__ = [
    "UnknownVoiceEligibilityStateVersionError",
    "VoiceEligibilityStateStoreV1",
    "VoiceEligibilityStateV1",
    "finalize_state_identity",
    "validate_state",
]
