"""Private byte-compatible execution-request fingerprint projection."""

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


def canonical_value(value: object) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return unicodedata.normalize("NFC", value) if type(value) is str else value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError
        return value
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError
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
            raise TypeError
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
    raise TypeError


def tagged_number(value: object) -> dict[str, object]:
    if type(value) is int:
        return {"type": "int", "value": value}
    if type(value) is float and math.isfinite(value):
        return {"type": "float", "value": value}
    raise TypeError


def request_projection(values: tuple[object, ...]) -> dict[str, object]:
    (
        preparation,
        plan,
        flow,
        editorial,
        commentary,
        voice,
        configuration,
        options,
        provider,
        requested_at,
        reference,
        cancellation,
    ) = values
    return {
        "preparation": canonical_value(preparation),
        "plan": canonical_value(plan),
        "flow_result": canonical_value(flow),
        "editorial_blueprint": canonical_value(editorial),
        "commentary_blueprint": canonical_value(commentary),
        "voice_plan": canonical_value(voice),
        "generation_configuration": canonical_value(configuration),
        "runtime_options": {
            "provider": options.provider.value,
            "model_identifier": options.model_identifier,
            "model_revision": options.model_revision,
            "temperature": tagged_number(options.temperature),
            "top_p": tagged_number(options.top_p),
            "max_output_tokens": options.max_output_tokens,
            "seed": options.seed,
            "stop_sequences": options.stop_sequences,
            "structured_output_mode": options.structured_output_mode,
            "timeout_seconds": tagged_number(options.timeout_policy.timeout_seconds),
        },
        "provider": provider.value,
        "requested_at": requested_at,
        "request_reference": reference,
        "cancellation_requested": cancellation.cancellation_requested,
    }


def request_fingerprint(projection: object) -> str:
    payload = json.dumps(
        canonical_value(projection),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()
