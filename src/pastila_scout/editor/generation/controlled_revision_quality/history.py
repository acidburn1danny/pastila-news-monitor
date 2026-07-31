"""Versioned append-only persistence for provider benchmark history."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class BenchmarkHistoryError(ValueError):
    """Raised when benchmark history cannot be validated or appended safely."""


class BenchmarkHistoryEntry(BaseModel):
    """One immutable comparable provider benchmark result."""

    model_config = ConfigDict(extra="allow", frozen=True)

    benchmark_id: str = Field(
        pattern=r"^\d{8}-\d{6}-[a-z0-9][a-z0-9.-]*-[a-z0-9][a-z0-9.-]*$"
    )
    benchmark_date: str
    benchmark_version: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_version: str = Field(min_length=1)
    scenario_count: int = Field(gt=0)
    category_count: int = Field(gt=0)
    usable_revision_rate: float | None = Field(default=None, ge=0, le=1)
    editorial_acceptance_rate: float | None = Field(default=None, ge=0, le=1)
    dto_pass_rate: float | None = Field(default=None, ge=0, le=1)
    meaning_preservation_rate: float | None = Field(default=None, ge=0, le=1)
    average_latency_ms: float | None = Field(default=None, ge=0)
    p95_latency_ms: float | None = Field(default=None, ge=0)
    average_prompt_tokens: float | None = Field(default=None, ge=0)
    average_completion_tokens: float | None = Field(default=None, ge=0)
    average_reasoning_tokens: float | None = Field(default=None, ge=0)
    average_cost_per_scenario: float | None = Field(default=None, ge=0)
    average_cost_per_usable_revision: float | None = Field(default=None, ge=0)
    total_benchmark_cost: float | None = Field(default=None, ge=0)
    provider_requests: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    root_conclusion: str = Field(min_length=1)

    @field_validator("benchmark_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        try:
            parsed = _parse_date(value)
        except ValueError as exc:
            raise ValueError("benchmark_date must be ISO 8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("benchmark_date must include a timezone")
        return value


class BenchmarkHistory(BaseModel):
    """Explicitly versioned history; unknown root fields support future readers."""

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: int = Field(default=1, ge=1)
    history: tuple[BenchmarkHistoryEntry, ...] = ()

    @field_validator("history")
    @classmethod
    def validate_history(
        cls, entries: tuple[BenchmarkHistoryEntry, ...]
    ) -> tuple[BenchmarkHistoryEntry, ...]:
        identifiers = tuple(item.benchmark_id for item in entries)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("benchmark history contains duplicate IDs")
        dates = tuple(_parse_date(item.benchmark_date) for item in entries)
        if dates != tuple(sorted(dates)):
            raise ValueError("benchmark history is not ordered by benchmark date")
        return entries


def create_benchmark_history(path: Path) -> BenchmarkHistory:
    """Create an empty history only when no artifact exists."""

    if path.exists():
        return load_benchmark_history(path)
    history = BenchmarkHistory()
    _atomic_write(path, history)
    return history


def load_benchmark_history(path: Path) -> BenchmarkHistory:
    """Load and validate one UTF-8 history document."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return BenchmarkHistory.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise BenchmarkHistoryError("invalid benchmark history artifact") from exc


def append_benchmark_history(
    path: Path, entry: BenchmarkHistoryEntry
) -> BenchmarkHistory:
    """Atomically append while proving all prior serialized entries are unchanged."""

    current = load_benchmark_history(path) if path.exists() else BenchmarkHistory()
    if any(item.benchmark_id == entry.benchmark_id for item in current.history):
        raise BenchmarkHistoryError("duplicate benchmark ID")
    if current.history and _parse_date(entry.benchmark_date) < _parse_date(
        current.history[-1].benchmark_date
    ):
        raise BenchmarkHistoryError("benchmark date would violate history ordering")
    previous = tuple(_canonical_entry(item) for item in current.history)
    updated = current.model_copy(update={"history": (*current.history, entry)})
    validated = BenchmarkHistory.model_validate(updated.model_dump(mode="python"))
    if tuple(_canonical_entry(item) for item in validated.history[:-1]) != previous:
        raise BenchmarkHistoryError("historical benchmark entries changed")
    _atomic_write(path, validated)
    return validated


def _canonical_entry(entry: BenchmarkHistoryEntry) -> str:
    return json.dumps(
        entry.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _atomic_write(path: Path, history: BenchmarkHistory) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            history.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise BenchmarkHistoryError("could not write benchmark history") from exc
