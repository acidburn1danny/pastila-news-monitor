"""Pure deterministic canonicalization of event metadata."""

import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from pastila_scout.models import (
    ArticleProvenance,
    EventSnapshot,
    ExistingEventMetadata,
    SourceProvenance,
)

ALLOWED_CATEGORIES = (
    "Politica",
    "Social",
    "Conspiratii",
    "Economie",
    "CanCan",
    "Externe",
    "Diverse",
)
_CATEGORY_ORDER = {category: index for index, category in enumerate(ALLOWED_CATEGORIES)}


def canonicalize_event(
    event: ExistingEventMetadata,
    articles: Sequence[ArticleProvenance],
) -> EventSnapshot:
    """Return complete canonical metadata from existing article provenance."""

    if not articles:
        raise ValueError(f"Event {event.id} has no articles to canonicalize")
    ordered_articles = tuple(sorted(articles, key=lambda article: article.id))
    selected = select_canonical_article(ordered_articles)
    categories = derive_categories(ordered_articles)
    if not categories:
        categories = tuple(
            category for category in event.categories if category in _CATEGORY_ORDER
        )[:3]
    summary = selected.summary
    if (
        event.canonical_article_id == selected.id
        and _valid_text(event.summary)
        or not _valid_text(summary)
        and _valid_text(event.summary)
    ):
        summary = event.summary
    publications = sorted(
        (parsed, article.published_at)
        for article in ordered_articles
        if (parsed := _parse_date(article.published_at)) is not None
    )
    by_source: dict[tuple[str, str], list[int]] = defaultdict(list)
    for article in ordered_articles:
        by_source[(article.source_id, article.source_name)].append(article.id)
    sources = tuple(
        SourceProvenance(id=source_id, name=name, article_ids=tuple(article_ids))
        for (source_id, name), article_ids in sorted(by_source.items())
    )
    reason = canonical_selection_reason(selected)
    return EventSnapshot(
        id=event.id,
        canonical_title=selected.title,
        canonical_summary=summary,
        categories=categories,
        first_publication_at=publications[0][1] if publications else None,
        last_publication_at=publications[-1][1] if publications else None,
        first_seen_at=event.first_seen_at,
        last_seen_at=event.last_seen_at,
        article_count=len(ordered_articles),
        source_count=len(by_source),
        sources=sources,
        articles=ordered_articles,
        canonical_article_id=selected.id,
        canonical_selection_reason=reason,
    )


def select_canonical_article(
    articles: Sequence[ArticleProvenance],
) -> ArticleProvenance:
    """Select one article by priority, completeness, publication, and ID."""

    def key(article: ArticleProvenance) -> tuple[object, ...]:
        completeness = len(article.title.strip()) + len((article.summary or "").strip())
        return (
            0 if article.source_priority == 2 else 1,
            -completeness,
            _parse_date(article.published_at) or datetime.max.replace(tzinfo=UTC),
            article.id,
        )

    return min(articles, key=key)


def derive_categories(articles: Sequence[ArticleProvenance]) -> tuple[str, ...]:
    """Derive up to three categories by article frequency and vocabulary order."""

    counts: Counter[str] = Counter()
    for article in articles:
        candidates = set(article.source_categories) | _raw_categories(
            article.raw_payload
        )
        counts.update(
            category for category in candidates if category in _CATEGORY_ORDER
        )
    ranked = sorted(
        counts, key=lambda category: (-counts[category], _CATEGORY_ORDER[category])
    )
    return tuple(ranked[:3])


def canonical_selection_reason(article: ArticleProvenance) -> str:
    """Explain the deterministic canonical-article selection inputs."""

    completeness = len(article.title.strip()) + len((article.summary or "").strip())
    return (
        f"article {article.id} selected: priority-2 source="
        f"{article.source_priority == 2}; completeness={completeness}; "
        f"publication={article.published_at or 'unknown'}; deterministic ID fallback"
    )


def _raw_categories(raw_payload: str | None) -> set[str]:
    if not raw_payload:
        return set()
    try:
        payload = json.loads(raw_payload)
    except (TypeError, ValueError):
        return set()
    values: list[object] = []
    if isinstance(payload, dict):
        for key in ("category", "categories", "tags"):
            value = payload.get(key)
            values.extend(value if isinstance(value, list) else [value])
    return {str(value) for value in values if value is not None}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def _valid_text(value: str | None) -> bool:
    return bool(value and value.strip())
