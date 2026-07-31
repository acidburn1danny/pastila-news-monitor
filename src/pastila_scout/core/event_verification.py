"""Read-only orchestration for deterministic event candidates and AI advice."""

from datetime import UTC, datetime

from pastila_scout.ai.verification import EventVerifier, confirms_same_event
from pastila_scout.core.event_reconciliation import build_reconciliation_plan
from pastila_scout.models.ai import (
    AIUsageDiagnostics,
    EventVerificationRequest,
    VerificationArticle,
    VerificationDecisionMetadata,
    VerificationRecord,
    VerificationRunReport,
)
from pastila_scout.models.reconciliation import (
    ReconciliationArticle,
    ReconciliationSnapshot,
)


def build_verification_requests(
    snapshot: ReconciliationSnapshot,
    *,
    similarity_threshold: float,
    lookback_hours: float,
    event_id: int | None = None,
) -> tuple[EventVerificationRequest, ...]:
    """Reuse reconciliation matching to expose each deterministic candidate edge."""

    plan = build_reconciliation_plan(
        snapshot,
        database_path="read-only",
        similarity_threshold=similarity_threshold,
        lookback_hours=lookback_hours,
    )
    scores = {
        (score.event_id, score.related_event_id): score.score
        for proposal in plan.proposals
        for score in proposal.pairwise_similarities
    }
    scores.update(
        {
            (score.event_id, score.related_event_id): score.score
            for group in plan.ambiguous_groups
            for score in group.matching_pairs
        }
    )
    events = {item.id: item for item in snapshot.events}
    articles_by_event: dict[int, list[ReconciliationArticle]] = {}
    for article in snapshot.articles:
        articles_by_event.setdefault(article.event_id, []).append(article)
    requests: list[EventVerificationRequest] = []
    for (left_id, right_id), score in sorted(scores.items()):
        if event_id is not None and event_id not in (left_id, right_id):
            continue
        left_event, right_event = events[left_id], events[right_id]
        left = _canonical_article(
            left_event.canonical_article_id, articles_by_event[left_id]
        )
        right = _canonical_article(
            right_event.canonical_article_id, articles_by_event[right_id]
        )
        requests.append(
            EventVerificationRequest(
                left=_verification_article(left, left_event.categories),
                right=_verification_article(right, right_event.categories),
                deterministic_similarity=score,
            )
        )
    return tuple(requests)


def run_event_verification(
    requests: tuple[EventVerificationRequest, ...],
    verifier: EventVerifier,
    *,
    database_path: str,
    limit: int | None = None,
) -> VerificationRunReport:
    """Continue across individual failures and aggregate diagnostic counters."""

    selected = requests[:limit] if limit is not None else requests
    records: list[VerificationRecord] = []
    for request in selected:
        result = verifier.verify(request)
        records.append(
            VerificationRecord(
                request=request,
                result=result,
                confirmed_same_event=confirms_same_event(result),
                decision=_decision_metadata(result),
            )
        )
    failed = {"provider_error", "invalid_response", "retry_exhausted"}
    unavailable = {"disabled", "missing_api_key"}
    return VerificationRunReport(
        generated_at=datetime.now(UTC),
        database_path=database_path,
        candidate_pairs=len(selected),
        ai_requests=verifier.ai_requests,
        cache_hits=sum(item.result.status == "cache_hit" for item in records),
        cache_misses=sum(
            item.result.cache_status in {"miss", "corrupt"} for item in records
        ),
        confirmed_same_event_pairs=sum(item.confirmed_same_event for item in records),
        rejected_pairs=sum(
            item.result.status in {"success", "cache_hit"}
            and not item.confirmed_same_event
            for item in records
        ),
        unavailable_results=sum(item.result.status in unavailable for item in records),
        failed_requests=sum(item.result.status in failed for item in records),
        retries=sum(item.result.retry_count for item in records),
        usage=_aggregate_usage(records),
        records=tuple(records),
    )


def _decision_metadata(result) -> VerificationDecisionMetadata:
    confirmed = confirms_same_event(result)
    if confirmed:
        reason = "verified"
    elif result.status in {"disabled", "missing_api_key"}:
        reason = "provider_unavailable"
    elif result.status == "invalid_response":
        reason = "schema_validation_failed"
    elif result.status in {"provider_error", "retry_exhausted"}:
        reason = "provider_failed"
    elif result.ai_similarity_score < 85:
        reason = "score_below_threshold"
    else:
        reason = "insufficient_context"
    return VerificationDecisionMetadata(
        confirmed=confirmed,
        reason=reason,
        threshold=85,
        score=result.ai_similarity_score,
    )


def _aggregate_usage(records: list[VerificationRecord]) -> AIUsageDiagnostics:
    current = [item.result for item in records if item.result.status != "cache_hit"]

    def total(field: str) -> int | None:
        values = [getattr(item.usage, field) for item in current]
        present = [value for value in values if value is not None]
        return sum(present) if present else None

    latencies = [
        item.usage.provider_latency_ms
        for item in current
        if item.usage.provider_latency_ms is not None
    ]
    costs = [
        item.usage.estimated_cost
        for item in current
        if item.usage.estimated_cost is not None
    ]
    return AIUsageDiagnostics(
        input_tokens=total("input_tokens"),
        output_tokens=total("output_tokens"),
        total_tokens=total("total_tokens"),
        provider_latency_ms=round(sum(latencies), 3) if latencies else None,
        estimated_cost=round(sum(costs), 8) if costs else None,
    )


def _canonical_article(
    canonical_id: int | None, articles: list[ReconciliationArticle]
) -> ReconciliationArticle:
    for article in articles:
        if article.id == canonical_id:
            return article
    return min(articles, key=lambda article: article.id)


def _verification_article(
    article: ReconciliationArticle, categories: tuple[str, ...]
) -> VerificationArticle:
    return VerificationArticle(
        article_id=article.id,
        event_id=article.event_id,
        normalized_title=article.normalized_title,
        summary=article.summary,
        published_at=article.published_at,
        source_id=article.source_id,
        source_name=article.source_name,
        url=article.url,
        categories=categories,
    )
