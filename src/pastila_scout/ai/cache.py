"""Persistent, atomic, provider-independent AI verification cache."""

import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from pastila_scout.config import AIConfig
from pastila_scout.models.ai import AIVerificationResult, EventVerificationRequest


@dataclass(frozen=True)
class CacheLookup:
    result: AIVerificationResult | None
    status: str


class VerificationCache(Protocol):
    def get(self, key: str) -> CacheLookup: ...
    def put(self, key: str, result: AIVerificationResult) -> None: ...


def verification_cache_key(request: EventVerificationRequest, config: AIConfig) -> str:
    """Build an order-independent semantic cache key without secrets."""

    articles = [
        request.left.model_dump(mode="json"),
        request.right.model_dump(mode="json"),
    ]
    articles.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    payload = {
        "articles": articles,
        "deterministic_similarity": request.deterministic_similarity,
        "prompt_version": config.prompt_version,
        "provider": config.provider,
        "model": config.model,
        "temperature": config.temperature,
        "schema_version": 1,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class FileVerificationCache:
    """Store one UTF-8 JSON document per key with atomic replacement."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.hits = 0
        self.misses = 0
        self.corrupt = 0

    def get(self, key: str) -> CacheLookup:
        path = self.directory / f"{key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("key") != key:
                raise ValueError("cache key mismatch")
            result = AIVerificationResult.model_validate(payload["result"])
        except FileNotFoundError:
            self.misses += 1
            return CacheLookup(None, "miss")
        except (OSError, KeyError, TypeError, ValueError, ValidationError):
            self.misses += 1
            self.corrupt += 1
            return CacheLookup(None, "corrupt")
        self.hits += 1
        return CacheLookup(result, "hit")

    def put(self, key: str, result: AIVerificationResult) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{key}.json"
        temporary = self.directory / f".{key}.{os.getpid()}.tmp"
        payload = {"key": key, "result": result.model_dump(mode="json")}
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class FileJSONCache:
    """Generic permanent JSON cache using the same atomic storage semantics."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.hits = 0
        self.misses = 0
        self.corrupt = 0

    def get(self, key: str) -> tuple[dict[str, object] | None, str]:
        path = self.directory / f"{key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("key") != key:
                raise ValueError("cache key mismatch")
            value = payload["value"]
            if not isinstance(value, dict):
                raise TypeError("cache value is not an object")
        except FileNotFoundError:
            self.misses += 1
            return None, "miss"
        except (OSError, KeyError, TypeError, ValueError):
            self.misses += 1
            self.corrupt += 1
            return None, "corrupt"
        self.hits += 1
        return value, "hit"

    def put(self, key: str, value: dict[str, object]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{key}.json"
        temporary = self.directory / f".{key}.{os.getpid()}.tmp"
        payload = {"key": key, "value": value}
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
