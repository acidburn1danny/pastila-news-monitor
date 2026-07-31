"""Canonical identity helpers isolated from Editorial QA ownership."""

import hashlib
import json
from typing import Any

from pastila_scout.editor.generation.prompt import canonicalize


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def revision_fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def field(value: Any, name: str) -> Any:
    return value[name] if isinstance(value, dict) else getattr(value, name)
