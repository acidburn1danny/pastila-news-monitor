"""Isolated canonical UTF-8 authority for provider-neutral V2 artifacts."""

import hashlib
import json
import unicodedata
from enum import Enum
from typing import Any


def canonical_semantics(value: Any) -> Any:
    """Return deterministic NFC-normalized JSON semantics."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python", warnings=False)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return {key: canonical_semantics(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [canonical_semantics(item) for item in value]
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize canonical semantics as compact UTF-8-safe JSON text."""

    return json.dumps(
        canonical_semantics(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def semantic_sha256(value: Any) -> str:
    """Hash canonical UTF-8 semantics with SHA-256."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ("canonical_json", "canonical_semantics", "semantic_sha256")
