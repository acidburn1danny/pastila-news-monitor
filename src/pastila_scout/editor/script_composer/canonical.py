"""Canonical UTF-8 serialization and semantic SHA-256 fingerprints."""

import hashlib
import json
import unicodedata
from enum import Enum
from typing import Any

from .defaults import (
    MEANINGFULLY_ORDERED_FIELDS,
    SELF_FINGERPRINT_FIELDS,
    TRANSIENT_FIELDS,
)


class CanonicalSerializationError(ValueError):
    """Raised when a value cannot participate in canonical domain rendering."""


def canonical_semantics(value: Any, key: str = "") -> Any:
    """Normalize supported semantic values recursively."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for name, item in sorted(value.items()):
            if not isinstance(name, str):
                raise CanonicalSerializationError(
                    "canonical mapping keys must be strings"
                )
            if name in SELF_FINGERPRINT_FIELDS or name in TRANSIENT_FIELDS:
                continue
            if name == "delivery_annotations" and isinstance(item, (list, tuple)):
                item = tuple(
                    annotation
                    for annotation in item
                    if _semantic_annotation(annotation)
                )
            normalized[name] = canonical_semantics(item, name)
        return normalized
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [canonical_semantics(item) for item in value]
        if key in MEANINGFULLY_ORDERED_FIELDS:
            return items
        return sorted(items, key=_canonical_sort_key)
    raise CanonicalSerializationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json(value: Any, *, indent: int | None = None) -> str:
    """Return deterministic NFC-normalized JSON."""
    return json.dumps(
        canonical_semantics(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
        allow_nan=False,
    )


def canonical_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 bytes."""
    return canonical_json(value).encode("utf-8")


def semantic_fingerprint(value: Any) -> str:
    """Return the semantic SHA-256 fingerprint for a supported artifact."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _canonical_sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _semantic_annotation(value: Any) -> bool:
    if hasattr(value, "semantic_effect"):
        effect = value.semantic_effect
    elif isinstance(value, dict):
        effect = value.get("semantic_effect")
    else:
        return True
    return getattr(effect, "value", effect) == "semantic"


__all__ = (
    "CanonicalSerializationError",
    "canonical_bytes",
    "canonical_json",
    "canonical_semantics",
    "semantic_fingerprint",
)
