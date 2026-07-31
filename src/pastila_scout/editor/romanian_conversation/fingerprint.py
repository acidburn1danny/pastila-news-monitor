"""Semantic SHA-256 fingerprints for Romanian conversational contracts."""

import hashlib
import json
from typing import Any

_ORDERED = {
    "principles",
    "preferred_registers",
    "context_dependent_registers",
    "discouraged_registers",
    "conversational_patterns",
}


def _normalize(value: Any, key: str = "") -> Any:
    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"), key)
    if isinstance(value, dict):
        return {name: _normalize(item, name) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_normalize(item) for item in value]
        return (
            items
            if key in _ORDERED
            else sorted(
                items,
                key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
            )
        )
    return value


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        _normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


engine_fingerprint = _fingerprint


def principle_collection_fingerprint(value: Any) -> str:
    return _fingerprint({"principles": value})


authenticity_model_fingerprint = _fingerprint
register_model_fingerprint = _fingerprint
policy_fingerprint = _fingerprint


def pattern_collection_fingerprint(value: Any) -> str:
    return _fingerprint({"conversational_patterns": value})


reference_catalogue_fingerprint = _fingerprint
ai_indicator_collection_fingerprint = _fingerprint
correction_integration_fingerprint = _fingerprint
profile_guidance_fingerprint = _fingerprint
assessment_fingerprint = _fingerprint
risk_collection_fingerprint = _fingerprint
