"""Deterministic semantic fingerprints for communication artifacts."""

import hashlib
import json
from typing import Any

_ORDERED_KEYS = {"principles"}


def _normalize(value: Any, key: str = "") -> Any:
    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"), key)
    if isinstance(value, dict):
        return {name: _normalize(item, name) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_normalize(item) for item in value]
        if key in _ORDERED_KEYS:
            return items
        return sorted(
            items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return value


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


communication_engine_fingerprint = _fingerprint
working_memory_fingerprint = _fingerprint
communication_flow_fingerprint = _fingerprint
rhythm_fingerprint = _fingerprint
attention_fingerprint = _fingerprint
orientation_fingerprint = _fingerprint
continuity_fingerprint = _fingerprint
communication_assessment_fingerprint = _fingerprint
communication_risk_collection_fingerprint = _fingerprint
communication_profile_guidance_fingerprint = _fingerprint
