"""Immutable persistence for explicitly versioned relationship bindings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_bytes

from .eligibility import ExpressionEligibilityIntegrityError, _sealed
from .eligibility_models import CommentaryRelationBindingV2


class UnknownCommentaryRelationBindingVersionError(ValueError):
    pass


class CommentaryRelationBindingStoreV2:
    def __init__(self, path: Path):
        self.path = path

    def save(self, binding: CommentaryRelationBindingV2) -> None:
        if binding.binding_identity != _sealed(binding, "binding_identity"):
            raise ExpressionEligibilityIntegrityError("binding identity mismatch")
        raw = canonical_bytes(binding)
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

    def load(self) -> CommentaryRelationBindingV2:
        raw = self.path.read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid relationship binding JSON"
            ) from exc
        if not isinstance(value, dict) or value.get("schema_version") != (
            "COMMENTARY_RELATION_BINDING_V2"
        ):
            raise UnknownCommentaryRelationBindingVersionError(
                "unsupported commentary relationship binding version"
            )
        try:
            binding = CommentaryRelationBindingV2.model_validate(value)
        except ValidationError as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid commentary relationship binding"
            ) from exc
        if canonical_bytes(binding) != raw:
            raise ExpressionEligibilityIntegrityError(
                "relationship binding is not canonical"
            )
        if binding.binding_identity != _sealed(binding, "binding_identity"):
            raise ExpressionEligibilityIntegrityError("binding identity mismatch")
        return binding


__all__ = [
    "CommentaryRelationBindingStoreV2",
    "UnknownCommentaryRelationBindingVersionError",
]
