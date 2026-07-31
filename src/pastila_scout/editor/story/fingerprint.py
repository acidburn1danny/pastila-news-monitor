"""Semantic fingerprints for Story Architecture artifacts."""

import hashlib
import json

_ORDERED_KEYS = {"principles", "stage_order", "ordered_unit_ids", "transitions"}


def _normalize(value, key=""):
    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"), key)
    if isinstance(value, dict):
        return {k: _normalize(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_normalize(item) for item in value]
        if key in _ORDERED_KEYS:
            return items
        return sorted(
            items, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)
        )
    return value


def _fingerprint(value) -> str:
    encoded = json.dumps(
        _normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


architecture_fingerprint = _fingerprint
pattern_collection_fingerprint = _fingerprint
pattern_selection_fingerprint = _fingerprint
unit_collection_fingerprint = _fingerprint
story_plan_fingerprint = _fingerprint
risk_collection_fingerprint = _fingerprint
profile_guidance_fingerprint = _fingerprint
