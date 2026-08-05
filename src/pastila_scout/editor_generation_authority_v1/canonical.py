"""Canonical semantic identity helpers without runtime behavior."""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel


def canonical_json(value: object) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def semantic_fingerprint(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def tagged_number(value: object) -> dict[str, object]:
    if type(value) is int:
        return {"type": "int", "value": value}
    if type(value) is float and math.isfinite(value):
        return {"type": "float", "value": value}
    raise TypeError("invalid canonical number")


def canonical_value(value: object) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return unicodedata.normalize("NFC", value) if type(value) is str else value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError("invalid canonical value")
        return value
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError("invalid canonical value")
        return (
            value.astimezone(UTC)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if type(value) in {tuple, list}:
        return [canonical_value(item) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("invalid canonical value")
        return {
            canonical_value(key): canonical_value(item) for key, item in value.items()
        }
    if isinstance(value, BaseModel):
        return canonical_value(value.model_dump(mode="python", warnings=False))
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: canonical_value(object.__getattribute__(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
    raise TypeError("invalid canonical value")


def canonical_schema(value: object) -> tuple[str, str]:
    canonical = canonical_json(value)
    parsed = json.loads(canonical)
    if type(parsed) is not dict:
        raise TypeError("schema must be an object")
    return canonical, sha256(canonical.encode("utf-8")).hexdigest()


__all__ = (
    "canonical_json",
    "canonical_schema",
    "canonical_value",
    "semantic_fingerprint",
    "tagged_number",
)
