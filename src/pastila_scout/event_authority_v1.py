"""Deterministic same-event factual authority projection for Editor handoff."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping
from datetime import datetime

from bs4 import BeautifulSoup

from pastila_scout.contracts.scout_editor import (
    EventAuthorityBundleV1,
    EventAuthoritySegmentV1,
)

EVENT_AUTHORITY_VERSION = "event-authority-bundle-v1"
MAX_MODEL_VISIBLE_AUTHORITY_CHARACTERS = 12_000
_TRUNCATION = re.compile(r"(?:\.\.\.|…|\[(?:…|\.\.\.)\])\s*$")
_SPACE = re.compile(r"\s+")
_ROMANIATV_FEED_FOOTER = re.compile(
    r"\s*Articolul\s+.+?\s+apare\s+prima\s+dată\s+în\s+Romania\s*TV\s*\.?\s*$",
    re.IGNORECASE,
)


def build_event_authority_bundle(
    *, event_id: int, canonical_article_id: int, articles: Iterable[object]
) -> EventAuthorityBundleV1:
    """Project one clean, attributed segment per source without claim synthesis."""
    representatives: dict[str, object] = {}
    ordered = sorted(
        articles,
        key=lambda item: (
            _get(item, "id") != canonical_article_id,
            _get(item, "id"),
        ),
    )
    for article in ordered:
        representatives.setdefault(str(_get(article, "source_id")), article)

    accepted: list[EventAuthoritySegmentV1] = []
    seen: set[str] = set()
    omitted: list[str] = []
    used_characters = 0
    for article in representatives.values():
        title = clean_feed_text(str(_get(article, "title")))
        raw_summary = str(_get(article, "summary") or "")
        summary = clean_feed_text(raw_summary)
        if not title or not summary:
            omitted.append(str(_get(article, "source_id")))
            continue
        fingerprint = _normalize(summary)
        if fingerprint in seen:
            omitted.append(str(_get(article, "source_id")))
            continue
        segment = EventAuthoritySegmentV1(
            article_id=int(_get(article, "id")),
            source_id=str(_get(article, "source_id")),
            source_name=str(_get(article, "source_name")),
            url=str(_get(article, "url")),
            title=title,
            summary=summary,
            published_at=_published_at(_get(article, "published_at")),
            canonical=int(_get(article, "id")) == canonical_article_id,
            truncated=is_truncated_feed_excerpt(raw_summary),
        )
        segment_size = len(title) + len(summary)
        if accepted and used_characters + segment_size > MAX_MODEL_VISIBLE_AUTHORITY_CHARACTERS:
            omitted.append(segment.source_id)
            continue
        accepted.append(segment)
        seen.add(fingerprint)
        used_characters += segment_size

    if not accepted or not accepted[0].canonical:
        raise ValueError("event authority requires its canonical source segment")
    return EventAuthorityBundleV1(
        authority_version=EVENT_AUTHORITY_VERSION,
        event_id=event_id,
        segments=tuple(accepted),
        omitted_source_ids=tuple(omitted),
    )


def clean_feed_text(value: str) -> str:
    """Remove markup/feed footer noise while preserving factual wording."""
    decoded = html.unescape(value)
    text = BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s*©\s+.*$", "", text).strip()
    text = _ROMANIATV_FEED_FOOTER.sub("", text).strip()
    return _SPACE.sub(" ", text)


def is_truncated_feed_excerpt(value: str) -> bool:
    text = clean_feed_text(value)
    return bool(_TRUNCATION.search(text)) or "[…]" in text


def render_authority_segment(segment: EventAuthoritySegmentV1) -> str:
    """Render factual source content without flattening source boundaries."""
    parts = [
        f"Sursa: {segment.source_name}",
        f"Titlu: {segment.title}",
        f"Rezumat: {segment.summary}",
    ]
    if segment.published_at is not None:
        parts.append(f"Publicat: {segment.published_at.isoformat()}")
    if segment.truncated:
        parts.append("Statut extras: trunchiat")
    return "\n".join(parts)


def _normalize(value: str) -> str:
    return _SPACE.sub(" ", value.casefold()).strip(" .")


def _get(value: object, key: str):
    if isinstance(value, Mapping) or hasattr(value, "keys"):
        return value[key]
    return getattr(value, key)


def _published_at(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = (
    "EVENT_AUTHORITY_VERSION",
    "MAX_MODEL_VISIBLE_AUTHORITY_CHARACTERS",
    "build_event_authority_bundle",
    "clean_feed_text",
    "is_truncated_feed_excerpt",
    "render_authority_segment",
)
