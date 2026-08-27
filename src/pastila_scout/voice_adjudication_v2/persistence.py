"""Immutable current-pointer persistence inside the canonical Voice root."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from pastila_scout.voice_repetition_v2.persistence import atomic_write

from .models import ZERO, VoiceStoryAdjudicationState, VoiceStoryAdjudicationStateV1

_STATE_ADAPTER = TypeAdapter(VoiceStoryAdjudicationState)


class VoiceAdjudicationPersistenceError(ValueError):
    pass


class VoiceAdjudicationStoreV1:
    def __init__(self, canonical_voice_root: Path):
        self.root = canonical_voice_root

    def _root(self, event_id: int) -> Path:
        if type(event_id) is not int or event_id <= 0:
            raise VoiceAdjudicationPersistenceError("invalid event identity")
        return self.root / "stories" / str(event_id) / "adjudication"

    def save(self, state: VoiceStoryAdjudicationStateV1):
        sealed = state.model_copy(
            update={
                "state_identity": canonical_identity(
                    state.model_copy(update={"state_identity": ZERO})
                )
            }
        )
        root = self._root(state.binding.event_id)
        relative = Path("revisions") / f"{sealed.state_identity[7:]}.json"
        atomic_write(root / relative, canonical_bytes(sealed))
        payload = {
            "schema_name": "pastilaacida-voice-adjudication-current-pointer",
            "schema_version": "1",
            "event_id": state.binding.event_id,
            "state_identity": sealed.state_identity,
            "state_relative_path": relative.as_posix(),
        }
        payload["pointer_identity"] = canonical_identity(payload)
        atomic_write(
            root / "current.json",
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            + b"\n",
        )
        return sealed

    def load(self, event_id: int) -> VoiceStoryAdjudicationStateV1 | None:
        root = self._root(event_id)
        pointer_path = root / "current.json"
        if not pointer_path.exists():
            return None
        try:
            raw_pointer = pointer_path.read_bytes()
            pointer = json.loads(raw_pointer.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VoiceAdjudicationPersistenceError("invalid pointer") from exc
        identity = pointer.pop("pointer_identity", None)
        if (
            pointer.get("schema_name")
            != "pastilaacida-voice-adjudication-current-pointer"
            or pointer.get("schema_version") != "1"
            or pointer.get("event_id") != event_id
            or identity != canonical_identity(pointer)
        ):
            raise VoiceAdjudicationPersistenceError("pointer identity mismatch")
        relative = Path(pointer.get("state_relative_path", ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise VoiceAdjudicationPersistenceError("unsafe pointer")
        try:
            raw = (root / relative).read_bytes()
            state = _STATE_ADAPTER.validate_json(raw)
        except (OSError, ValidationError) as exc:
            raise VoiceAdjudicationPersistenceError(
                "invalid adjudication state"
            ) from exc
        if (
            canonical_bytes(state) != raw
            or state.state_identity != pointer["state_identity"]
            or state.state_identity
            != canonical_identity(state.model_copy(update={"state_identity": ZERO}))
        ):
            raise VoiceAdjudicationPersistenceError("orphan adjudication pointer")
        return state


__all__ = ["VoiceAdjudicationPersistenceError", "VoiceAdjudicationStoreV1"]
