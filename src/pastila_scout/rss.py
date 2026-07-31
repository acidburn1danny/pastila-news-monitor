"""RSS and Atom parsing without network access."""

import calendar
import logging
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser
from pydantic import ValidationError

from pastila_scout.models import ArticleCandidate
from pastila_scout.normalization import normalize_title, normalize_url

logger = logging.getLogger(__name__)

_RAW_ENTRY_FIELDS = (
    "id",
    "link",
    "title",
    "summary",
    "description",
    "published",
    "updated",
)


class FeedParseError(ValueError):
    """Raised when content is not a well-formed RSS or Atom feed."""


def parse_feed(source_id: str, feed_content: bytes | str) -> list[ArticleCandidate]:
    """Parse RSS or Atom content into normalized article candidates.

    Individual entries that lack required fields or fail validation are logged
    and skipped. A malformed or unrecognized feed raises :class:`FeedParseError`.
    """

    parsed = feedparser.parse(feed_content)
    if parsed.bozo:
        exception = getattr(parsed, "bozo_exception", "unknown parser error")
        raise FeedParseError(f"Malformed RSS or Atom feed: {exception}")
    if not parsed.version or not parsed.version.startswith(("rss", "atom")):
        raise FeedParseError("Content is not a recognizable RSS or Atom feed")

    candidates: list[ArticleCandidate] = []
    seen_urls: set[str] = set()
    invalid_entries = 0
    duplicate_entries = 0
    for position, entry in enumerate(parsed.entries):
        try:
            candidate = _parse_entry(source_id, entry)
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            invalid_entries += 1
            logger.warning(
                "Skipping invalid feed entry %d for source %s: %s",
                position,
                source_id,
                exc,
            )
            continue

        if candidate.url in seen_urls:
            duplicate_entries += 1
            logger.info(
                "Skipping duplicate feed entry URL for source %s: %s",
                source_id,
                candidate.url,
            )
            continue
        seen_urls.add(candidate.url)
        candidates.append(candidate)

    logger.info(
        "RSS entries processed source=%s entries=%d valid=%d invalid=%d duplicates=%d",
        source_id,
        len(parsed.entries),
        len(candidates),
        invalid_entries,
        duplicate_entries,
    )
    return candidates


def _parse_entry(source_id: str, entry: Any) -> ArticleCandidate:
    """Convert one feedparser entry into a validated candidate."""

    link = entry.get("link")
    if not isinstance(link, str) or not link.strip():
        raise ValueError("entry has no URL")

    title = entry.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("entry has no title")

    normalized_url = normalize_url(link)
    normalized_title = normalize_title(title)
    if not normalized_title:
        raise ValueError("entry title is empty after normalization")

    summary = entry.get("summary") or entry.get("description")
    if summary is not None and not isinstance(summary, str):
        summary = str(summary)

    published_at = _publication_date(entry)
    return ArticleCandidate(
        source_id=source_id,
        url=normalized_url,
        title=normalized_title,
        summary=summary,
        published_at=published_at,
        raw_payload=_raw_payload(entry),
    )


def _publication_date(entry: Any) -> str | None:
    """Return an entry's published or updated timestamp in UTC."""

    parsed_date: struct_time | None = entry.get("published_parsed")
    if parsed_date is None:
        parsed_date = entry.get("updated_parsed")
    if parsed_date is None:
        return None

    timestamp = calendar.timegm(parsed_date)
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def _raw_payload(entry: Any) -> dict[str, object]:
    """Select scalar raw fields that can be serialized directly as JSON."""

    payload: dict[str, object] = {}
    for field in _RAW_ENTRY_FIELDS:
        if field not in entry:
            continue
        value = entry[field]
        if value is not None and isinstance(value, (str, int, float, bool)):
            payload[field] = value
    return payload
