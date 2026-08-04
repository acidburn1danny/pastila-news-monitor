"""Canonical UTF-8 serialization for Producer compatibility contracts."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


def canonical_semantics(value: object) -> object:
    """Return strict deterministic JSON semantics without implicit coercion."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python", warnings=False)
    elif is_dataclass(value) and not isinstance(value, type):
        value = {item.name: getattr(value, item.name) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if type(value) is str:
        if value != unicodedata.normalize("NFC", value):
            raise ValueError("canonical strings must already use NFC")
        return value
    if value is None or type(value) in {bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value) or (value == 0 and math.copysign(1, value) < 0):
            raise ValueError("canonical floats must be finite and not negative zero")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("canonical decimals must be finite")
        return _decimal_text(value)
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical datetimes must be timezone-aware")
        utc = value.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError("canonical mapping keys must be exact strings")
        return {
            key: canonical_semantics(item)
            for key, item in sorted(value.items(), key=lambda pair: pair[0])
        }
    if type(value) in {tuple, list}:
        return [canonical_semantics(item) for item in value]
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: object) -> str:
    """Return compact deterministic Unicode JSON."""

    return json.dumps(
        canonical_semantics(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical UTF-8 bytes."""

    return canonical_json(value).encode("utf-8")


def semantic_sha256(value: object) -> str:
    """Hash canonical semantics without salt or runtime state."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def semantic_payload(value: BaseModel, excluded: tuple[str, str]) -> dict[str, Any]:
    """Return a model payload after exact self-field exclusion."""

    payload = value.model_dump(mode="python", warnings=False)
    if any(field not in payload for field in excluded):
        raise ValueError("canonical exclusion field is absent")
    return {key: item for key, item in payload.items() if key not in excluded}


def reference_for(kind: str, fingerprint: str) -> str:
    """Build the exact compatibility reference form."""

    return f"scout:producer-compat:{kind}:{fingerprint}"


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


__all__ = ()
