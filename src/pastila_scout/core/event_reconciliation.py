"""Deterministic planning for safe historical event reconciliation."""

import json
from collections import defaultdict, deque
from datetime import UTC, datetime
from hashlib import sha256

from pastila_scout.core.event_canonicalization import (
    ALLOWED_CATEGORIES,
    canonical_selection_reason,
    derive_categories,
    select_canonical_article,
)
from pastila_scout.event_matcher import title_similarity
from pastila_scout.models import (
    AmbiguousReconciliationGroup,
    ArticleProvenance,
    CanonicalSelection,
    EventReconciliationPlan,
    PairwiseSimilarity,
    ReconciliationArticle,
    ReconciliationEvent,
    ReconciliationProposal,
    ReconciliationSnapshot,
)

_CATEGORY_ORDER = {category: index for index, category in enumerate(ALLOWED_CATEGORIES)}


def build_reconciliation_plan(
    snapshot: ReconciliationSnapshot,
    *,
    database_path: str,
    similarity_threshold: float = 0.72,
    lookback_hours: float = 168,
    generated_at: datetime | None = None,
) -> EventReconciliationPlan:
    """Build coherent complete-linkage groups without mutating storage."""

    timestamp = (generated_at or datetime.now(UTC)).astimezone(UTC)
    events = sorted(snapshot.events, key=lambda event: event.id)
    pair_scores: dict[tuple[int, int], float] = {}
    matching_edges: set[tuple[int, int]] = set()
    for index, event in enumerate(events):
        for related in events[index + 1 :]:
            if not _within_lookback(event, related, lookback_hours):
                continue
            pair = (event.id, related.id)
            score = title_similarity(event.canonical_title, related.canonical_title)
            pair_scores[pair] = score
            if score >= similarity_threshold:
                matching_edges.add(pair)

    components = _connected_components(events, matching_edges)
    articles_by_event: dict[int, list[ReconciliationArticle]] = defaultdict(list)
    for article in snapshot.articles:
        articles_by_event[article.event_id].append(article)
    event_by_id = {event.id: event for event in events}
    proposals: list[ReconciliationProposal] = []
    ambiguous: list[AmbiguousReconciliationGroup] = []
    for component in components:
        pairs = [
            (left, right)
            for i, left in enumerate(component)
            for right in component[i + 1 :]
        ]
        accepted = [pair for pair in pairs if pair in matching_edges]
        rejected = [pair for pair in pairs if pair not in matching_edges]
        if rejected:
            ambiguous.append(
                AmbiguousReconciliationGroup(
                    event_ids=tuple(component),
                    matching_pairs=tuple(
                        _score(pair, pair_scores) for pair in accepted
                    ),
                    rejected_pairs=tuple(
                        _score(pair, pair_scores) for pair in rejected
                    ),
                    reason=(
                        "Connected candidate component rejected: not every event pair "
                        "meets the unchanged similarity and lookback rules."
                    ),
                )
            )
            continue
        group_events = [event_by_id[event_id] for event_id in component]
        group_articles = sorted(
            (
                article
                for event_id in component
                for article in articles_by_event[event_id]
            ),
            key=lambda article: article.id,
        )
        proposals.append(_proposal(group_events, group_articles, accepted, pair_scores))

    return EventReconciliationPlan(
        generated_at=timestamp.isoformat(),
        database_path=database_path,
        similarity_threshold=similarity_threshold,
        lookback_hours=lookback_hours,
        proposals=tuple(sorted(proposals, key=lambda item: item.event_ids)),
        ambiguous_groups=tuple(sorted(ambiguous, key=lambda item: item.event_ids)),
    )


def proposal_state_fingerprint(
    snapshot: ReconciliationSnapshot, event_ids: tuple[int, ...]
) -> str:
    """Fingerprint only persisted state relevant to a proposed merge."""

    selected = set(event_ids)
    events = [event for event in snapshot.events if event.id in selected]
    articles = [
        article for article in snapshot.articles if article.event_id in selected
    ]
    payload = {
        "events": [
            {
                "id": event.id,
                "canonical_title": event.canonical_title,
                "normalized_title": event.normalized_title,
                "summary": event.summary,
                "categories": event.categories,
                "first_seen_at": event.first_seen_at,
                "last_seen_at": event.last_seen_at,
                "article_count": event.article_count,
                "source_count": event.source_count,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            }
            for event in sorted(events, key=lambda item: item.id)
        ],
        "articles": [
            {
                "id": article.id,
                "event_id": article.event_id,
                "source_id": article.source_id,
                "source_name": article.source_name,
                "title": article.title,
                "normalized_title": article.normalized_title,
                "summary": article.summary,
                "published_at": article.published_at,
                "discovered_at": article.discovered_at,
                "raw_payload": article.raw_payload,
            }
            for article in sorted(articles, key=lambda item: item.id)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _proposal(
    events: list[ReconciliationEvent],
    articles: list[ReconciliationArticle],
    pairs: list[tuple[int, int]],
    scores: dict[tuple[int, int], float],
) -> ReconciliationProposal:
    provenance = tuple(_to_provenance(article) for article in articles)
    selected = select_canonical_article(provenance)
    canonical = CanonicalSelection(
        article_id=selected.id,
        title=selected.title,
        normalized_title=selected.normalized_title,
        summary=selected.summary,
        reason=canonical_selection_reason(selected),
    )
    event_ids = tuple(event.id for event in events)
    dates = sorted(article.published_at for article in articles if article.published_at)
    categories = derive_categories(provenance)
    current = sorted(
        {category for event in events for category in event.categories},
        key=lambda category: _CATEGORY_ORDER.get(category, len(_CATEGORY_ORDER)),
    )
    snapshot = ReconciliationSnapshot(events=tuple(events), articles=tuple(articles))
    return ReconciliationProposal(
        event_ids=event_ids,
        article_ids=tuple(article.id for article in articles),
        canonical_titles=tuple(event.canonical_title for event in events),
        publication_start=dates[0] if dates else None,
        publication_end=dates[-1] if dates else None,
        sources=tuple(sorted({article.source_name for article in articles})),
        source_ids=tuple(sorted({article.source_id for article in articles})),
        current_categories=tuple(current),
        proposed_categories=categories,
        unresolved_categories=not categories,
        pairwise_similarities=tuple(_score(pair, scores) for pair in pairs),
        surviving_event_id=next(
            article.event_id
            for article in articles
            if article.id == canonical.article_id
        ),
        resulting_article_count=len(articles),
        resulting_source_count=len({article.source_id for article in articles}),
        canonical_selection=canonical,
        reason="All event pairs satisfy complete-linkage matching rules.",
        state_fingerprint=proposal_state_fingerprint(snapshot, event_ids),
    )


def _to_provenance(article: ReconciliationArticle) -> ArticleProvenance:
    return ArticleProvenance(
        id=article.id,
        event_id=article.event_id,
        source_id=article.source_id,
        source_name=article.source_name,
        url=article.url,
        normalized_url=article.normalized_url,
        title=article.title,
        normalized_title=article.normalized_title,
        summary=article.summary,
        published_at=article.published_at,
        discovered_at=article.discovered_at,
        raw_payload=article.raw_payload,
        source_categories=article.source_categories,
        source_priority=article.source_priority,
    )


def _connected_components(
    events: list[ReconciliationEvent], edges: set[tuple[int, int]]
) -> list[list[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    components: list[list[int]] = []
    unseen = set(adjacency)
    while unseen:
        root = min(unseen)
        queue = deque([root])
        component: set[int] = set()
        while queue:
            event_id = queue.popleft()
            if event_id in component:
                continue
            component.add(event_id)
            queue.extend(sorted(adjacency[event_id] - component))
        unseen -= component
        if len(component) >= 2:
            components.append(sorted(component))
    return sorted(components)


def _score(
    pair: tuple[int, int], scores: dict[tuple[int, int], float]
) -> PairwiseSimilarity:
    return PairwiseSimilarity(
        event_id=pair[0], related_event_id=pair[1], score=scores.get(pair, 0.0)
    )


def _within_lookback(
    event: ReconciliationEvent, related: ReconciliationEvent, hours: float
) -> bool:
    left = _parse_date(event.last_seen_at)
    right = _parse_date(related.last_seen_at)
    return bool(left and right and abs((left - right).total_seconds()) <= hours * 3600)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None
