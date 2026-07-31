"""Canonical semantic SHA-256 fingerprints for composition artifacts."""

import hashlib
import json
from enum import Enum
from typing import Any

from .defaults import (
    MEANINGFULLY_ORDERED_FIELDS,
    SELF_FINGERPRINT_FIELDS,
    VOLATILE_FIELDS,
)


def canonical_semantics(value: Any, key: str = "") -> Any:
    """Recursively normalize semantic data and remove volatile metadata."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {
            name: canonical_semantics(item, name)
            for name, item in sorted(value.items())
            if name not in VOLATILE_FIELDS and name not in SELF_FINGERPRINT_FIELDS
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [canonical_semantics(item) for item in value]
        if key in MEANINGFULLY_ORDERED_FIELDS:
            return items
        return sorted(
            items,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    return value


def canonical_json(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        canonical_semantics(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
    )


def artifact_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ("artifact_fingerprint", "canonical_json", "canonical_semantics")
