"""Pure read-only analysis of article-to-event integrity."""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Literal

from pastila_scout.event_matcher import title_similarity
from pastila_scout.models import (
    AuditEvent,
    EventIntegrityFinding,
    EventIntegrityReport,
    EventIntegritySnapshot,
    HistoricalMatchProposal,
)


def audit_event_integrity(
    snapshot: EventIntegritySnapshot,
    *,
    similarity_threshold: float = 0.72,
    lookback_hours: float = 168,
) -> EventIntegrityReport:
    """Analyze a snapshot without mutating its source or any persisted state."""

    if not 0 <= similarity_threshold <= 1:
        raise ValueError("Similarity threshold must be between zero and one")
    if lookback_hours <= 0:
        raise ValueError("Historical match lookback must be positive")

    errors: list[EventIntegrityFinding] = []
    warnings: list[EventIntegrityFinding] = []
    event_by_id = {event.id: event for event in snapshot.events}
    article_counts: Counter[int] = Counter()
    event_sources: dict[int, set[str]] = defaultdict(set)

    for article in snapshot.articles:
        if article.event_id is None:
            warnings.append(
                _finding(
                    "warning",
                    "unassigned_article",
                    f"Article {article.id} has no event assignment.",
                    article_id=article.id,
                )
            )
        elif article.event_id not in event_by_id:
            errors.append(
                _finding(
                    "error",
                    "invalid_event_reference",
                    f"Article {article.id} references missing event {article.event_id}.",
                    article_id=article.id,
                    event_id=article.event_id,
                )
            )
        else:
            article_counts[article.event_id] += 1
            event_sources[article.event_id].add(article.source_id)

    for event in snapshot.events:
        actual_articles = article_counts[event.id]
        actual_sources = len(event_sources[event.id])
        if actual_articles == 0:
            errors.append(
                _finding(
                    "error",
                    "event_without_articles",
                    f"Event {event.id} has no attached articles.",
                    event_id=event.id,
                )
            )
        if event.article_count != actual_articles:
            errors.append(
                _finding(
                    "error",
                    "article_count_mismatch",
                    f"Event {event.id} stores {event.article_count} articles; "
                    f"actual count is {actual_articles}.",
                    event_id=event.id,
                )
            )
        if event.source_count != actual_sources:
            errors.append(
                _finding(
                    "error",
                    "source_count_mismatch",
                    f"Event {event.id} stores {event.source_count} sources; "
                    f"actual distinct count is {actual_sources}.",
                    event_id=event.id,
                )
            )
        if not event.category or not event.category.strip():
            warnings.append(
                _finding(
                    "warning",
                    "missing_event_category",
                    f"Event {event.id} ({event.canonical_title!r}) has no category.",
                    event_id=event.id,
                )
            )
        if not event.summary or not event.summary.strip():
            warnings.append(
                _finding(
                    "warning",
                    "missing_event_summary",
                    f"Event {event.id} ({event.canonical_title!r}) has no summary.",
                    event_id=event.id,
                )
            )
        if actual_articles == 1:
            warnings.append(
                _finding(
                    "warning",
                    "single_article_event",
                    f"Event {event.id} contains one article and may be a legacy event.",
                    event_id=event.id,
                )
            )

    proposals = _historical_match_proposals(
        snapshot.events,
        article_counts,
        threshold=similarity_threshold,
        lookback_hours=lookback_hours,
    )
    for proposal in proposals:
        warnings.append(
            _finding(
                "warning",
                "likely_historical_match",
                f"Events {proposal.event_id} and {proposal.related_event_id} "
                f"may match (score {proposal.score:.2f}).",
                event_id=proposal.event_id,
            )
        )

    return EventIntegrityReport(
        article_count=len(snapshot.articles),
        event_count=len(snapshot.events),
        errors=tuple(errors),
        warnings=tuple(warnings),
        historical_matches=tuple(proposals),
    )


def _historical_match_proposals(
    events: tuple[AuditEvent, ...],
    article_counts: Counter[int],
    *,
    threshold: float,
    lookback_hours: float,
) -> list[HistoricalMatchProposal]:
    """Propose likely matches among single-article events without applying them."""

    eligible = [event for event in events if article_counts[event.id] == 1]
    proposals: list[HistoricalMatchProposal] = []
    for index, event in enumerate(eligible):
        for related in eligible[index + 1 :]:
            if not _within_lookback(event, related, lookback_hours):
                continue
            score = title_similarity(event.canonical_title, related.canonical_title)
            if score >= threshold:
                proposals.append(
                    HistoricalMatchProposal(
                        event_id=event.id,
                        related_event_id=related.id,
                        score=score,
                    )
                )
    return proposals


def _within_lookback(
    event: AuditEvent, related: AuditEvent, lookback_hours: float
) -> bool:
    """Return whether two event timestamps can be compared reliably."""

    try:
        left = datetime.fromisoformat(event.last_seen_at)
        right = datetime.fromisoformat(related.last_seen_at)
    except ValueError:
        return False
    if left.tzinfo is None or right.tzinfo is None:
        return False
    return abs((left - right).total_seconds()) <= lookback_hours * 3600


def _finding(
    severity: Literal["error", "warning"],
    code: str,
    message: str,
    *,
    event_id: int | None = None,
    article_id: int | None = None,
) -> EventIntegrityFinding:
    """Build a typed finding while keeping analysis branches concise."""

    return EventIntegrityFinding(
        severity=severity,
        code=code,
        message=message,
        event_id=event_id,
        article_id=article_id,
    )
