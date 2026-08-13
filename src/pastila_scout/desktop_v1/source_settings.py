"""Focused persistence for user-added generic Scout feeds."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from pastila_scout.config import SourceConfig, load_sources_config
from pastila_scout.http_client import HTTPClient
from pastila_scout.rss import parse_feed

_PRE_TASK_10B_CANONICAL_IDS = frozenset(
    {
        "adevarul",
        "antena3",
        "ap",
        "bbc_world",
        "cnn",
        "digi24",
        "economica",
        "europalibera",
        "g4media",
        "hotnews",
        "libertatea",
        "msnow",
        "newsro",
        "observatornews",
        "politico_europe",
        "pressone",
        "profit",
        "recorder",
        "reuters",
        "rfi",
        "ziare",
    }
)


def _rebase_scout_sources_override_v1(
    *, canonical_path: Path, override_path: Path
) -> Path:
    if not override_path.is_file():
        return canonical_path
    canonical = load_sources_config(canonical_path)
    override = load_sources_config(override_path)
    canonical_ids = {item.id for item in canonical.sources}
    additions = tuple(
        item
        for item in override.sources
        if item.id not in _PRE_TASK_10B_CANONICAL_IDS and item.id not in canonical_ids
    )
    payload = {
        "sources": [
            item.model_dump(mode="json") for item in (*canonical.sources, *additions)
        ]
    }
    _write_sources_override(payload=payload, override_path=override_path)
    return override_path


def _add_scout_source_v1(*, url: str, current_path: Path, override_path: Path) -> str:
    value = url.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "invalid"
    current = load_sources_config(current_path)
    if any(item.url.casefold() == value.casefold() for item in current.sources):
        return "duplicate"
    source_id = _source_id(parsed.netloc, {item.id for item in current.sources})
    try:
        with HTTPClient() as client:
            candidates = parse_feed(source_id, client.fetch(value))
        if not candidates:
            return "unsupported"
        added = SourceConfig(
            id=source_id,
            name=parsed.netloc,
            type="rss",
            url=value,
            enabled=True,
            categories=("Diverse",),
        )
        payload = {
            "sources": [
                item.model_dump(mode="json") for item in (*current.sources, added)
            ]
        }
        _write_sources_override(payload=payload, override_path=override_path)
    except Exception:  # noqa: BLE001 - GUI exposes one safe unsupported result
        return "unsupported"
    return "saved"


def _write_sources_override(*, payload: dict[str, object], override_path: Path) -> None:
    override_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=override_path.parent, suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            yaml.safe_dump(payload, stream, allow_unicode=True, sort_keys=False)
        load_sources_config(Path(temporary))
        os.replace(temporary, override_path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _source_id(host: str, existing: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", host.casefold()).strip("-") or "sursa"
    candidate = base
    number = 2
    while candidate in existing:
        candidate = f"{base}-{number}"
        number += 1
    return candidate
