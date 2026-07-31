"""Semantic fingerprints for editorial language learning artifacts."""

import hashlib
import json
from typing import Any

_ORDERED = {
    "ordered_operations",
    "chronological_references",
    "principles",
    "allowed_transitions",
}
_SELF_FINGERPRINT_FIELDS = {
    "graph_fingerprint",
    "profile_fingerprint",
    "fingerprint",
}
_VOLATILE_FIELDS = {
    "provenance_timestamp",
    "runtime_id",
    "runtime_identifier",
}


def _norm(v: Any, key: str = "") -> Any:
    if hasattr(v, "model_dump"):
        return _norm(v.model_dump(mode="json"), key)
    if isinstance(v, dict):
        return {k: _norm(x, k) for k, x in v.items() if k not in _VOLATILE_FIELDS}
    if isinstance(v, (list, tuple)):
        items = [_norm(x) for x in v]
        return (
            items
            if key in _ORDERED
            else sorted(
                items, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)
            )
        )
    return v


def semantic_fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _norm(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def canonical_semantics(value: Any) -> Any:
    """Return deterministic semantic data with volatile metadata removed."""
    excluded: set[str] = set()
    if hasattr(value, "model_dump"):
        excluded = set(_SELF_FINGERPRINT_FIELDS)
        if value.__class__.__name__ == "EditorialObservation":
            excluded.add("semantic_fingerprint")
        value = value.model_dump(mode="json", exclude=excluded)
    return _norm(value)


def artifact_fingerprint(value: Any) -> str:
    """Fingerprint an artifact without including its stored self-fingerprint."""
    return semantic_fingerprint(canonical_semantics(value))


graph_fingerprint = artifact_fingerprint
observation_fingerprint = artifact_fingerprint
aggregation_fingerprint = artifact_fingerprint
evidence_fingerprint = artifact_fingerprint
counter_evidence_fingerprint = artifact_fingerprint
confidence_fingerprint = artifact_fingerprint
candidate_fingerprint = artifact_fingerprint
preference_fingerprint = artifact_fingerprint
conflict_fingerprint = artifact_fingerprint
decay_fingerprint = artifact_fingerprint
supersession_fingerprint = artifact_fingerprint
profile_fingerprint = artifact_fingerprint
guidance_fingerprint = artifact_fingerprint
explanation_fingerprint = artifact_fingerprint
session_fingerprint = artifact_fingerprint
