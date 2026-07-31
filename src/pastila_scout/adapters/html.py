"""Configurable HTML source adapter."""

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from pastila_scout.config import SourceConfig
from pastila_scout.http_client import HTTPClient
from pastila_scout.models import ArticleCandidate
from pastila_scout.normalization import normalize_title, normalize_url

logger = logging.getLogger(__name__)


class HTMLAdapter:
    """Extract article candidates from configured static HTML selectors."""

    def fetch(
        self, source: SourceConfig, http_client: HTTPClient
    ) -> list[ArticleCandidate]:
        """Download and extract valid, unique candidates from an HTML page."""

        if not source.list_selector or not source.link_selector:
            raise ValueError(
                f"HTML source {source.id!r} requires list_selector and link_selector"
            )

        content = http_client.fetch(source.url)
        soup = BeautifulSoup(content, "html.parser")
        containers = soup.select(source.list_selector)
        logger.info(
            "HTML containers selected source=%s count=%d", source.id, len(containers)
        )
        candidates: list[ArticleCandidate] = []
        seen_urls: set[str] = set()
        malformed_entries = 0
        duplicate_entries = 0
        truncated = False

        for position, container in enumerate(containers):
            try:
                candidate = self._extract_candidate(source, container)
            except (TypeError, ValueError) as exc:
                malformed_entries += 1
                logger.warning(
                    "Skipping invalid HTML entry %d for source %s: %s",
                    position,
                    source.id,
                    exc,
                )
                continue

            if candidate.url in seen_urls:
                duplicate_entries += 1
                logger.info(
                    "Skipping duplicate HTML entry URL for source %s: %s",
                    source.id,
                    candidate.url,
                )
                continue
            seen_urls.add(candidate.url)
            candidates.append(candidate)
            if source.max_items is not None and len(candidates) >= source.max_items:
                truncated = position < len(containers) - 1
                break

        logger.info(
            "HTML extraction completed source=%s valid=%d malformed=%d duplicates=%d",
            source.id,
            len(candidates),
            malformed_entries,
            duplicate_entries,
        )
        if truncated:
            logger.info(
                "HTML max_items truncation source=%s max_items=%d",
                source.id,
                source.max_items,
            )
        return candidates

    def _extract_candidate(
        self, source: SourceConfig, container: Tag
    ) -> ArticleCandidate:
        """Extract and validate one configured article container."""

        link = container.select_one(source.link_selector or "")
        if link is None:
            raise ValueError("entry has no matching link")
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            raise ValueError("entry link has no href")

        title_element = (
            container.select_one(source.title_selector)
            if source.title_selector
            else link
        )
        if title_element is None:
            raise ValueError("entry has no matching title")
        title_text = title_element.get_text(" ", strip=True)
        if not title_text:
            raise ValueError("entry title is empty")

        summary_text = _optional_text(container, source.summary_selector)
        date_text, published_at = _extract_date(container, source.date_selector)
        resolved_url = urljoin(source.base_url or source.url, href.strip())
        normalized_url = normalize_url(resolved_url)
        normalized_title = normalize_title(title_text)
        if not normalized_title:
            raise ValueError("entry title is empty after normalization")

        raw_payload: dict[str, object] = {
            "href": href,
            "title": title_text,
        }
        if summary_text is not None:
            raw_payload["summary"] = summary_text
        if date_text is not None:
            raw_payload["date"] = date_text

        return ArticleCandidate(
            source_id=source.id,
            url=normalized_url,
            title=normalized_title,
            summary=summary_text,
            published_at=published_at,
            raw_payload=raw_payload,
        )


def _optional_text(container: Tag, selector: str | None) -> str | None:
    """Extract optional visible text selected within a container."""

    if not selector:
        return None
    element = container.select_one(selector)
    if element is None:
        return None
    text = element.get_text(" ", strip=True)
    return text or None


def _extract_date(
    container: Tag, selector: str | None
) -> tuple[str | None, str | None]:
    """Extract raw date text and a parsed UTC timestamp when recognized."""

    if not selector:
        return None, None
    element = container.select_one(selector)
    if element is None:
        return None, None
    datetime_attribute = element.get("datetime")
    raw_date = (
        datetime_attribute
        if isinstance(datetime_attribute, str) and datetime_attribute.strip()
        else element.get_text(" ", strip=True)
    )
    if not raw_date:
        return None, None
    return raw_date, _parse_publication_date(raw_date)


def _parse_publication_date(value: str) -> str | None:
    """Parse ISO 8601 or RFC 2822 input and convert it to UTC ISO 8601."""

    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(candidate)
        except (TypeError, ValueError, OverflowError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()
