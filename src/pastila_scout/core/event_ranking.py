"""Read-only orchestration for deterministic and advisory event ranking."""

from datetime import UTC, datetime

from pastila_scout.ai.editorial_scoring import EditorialEventScorer
from pastila_scout.config import ScoringConfig
from pastila_scout.core.event_scoring import score_event_deterministically
from pastila_scout.models import (
    EditorialAIResult,
    EditorialScoringRequest,
    EventRankingReport,
    EventSnapshot,
    RankedEvent,
    Recommendation,
    ScoreWeights,
    TokenUsage,
)


def recommendation_for_score(score: float) -> Recommendation:
    """Map a 0-100 score to the approved editorial recommendation bands."""

    if score >= 85:
        return Recommendation.STRONG_PICK
    if score >= 70:
        return Recommendation.POSSIBLE_PICK
    if score >= 55:
        return Recommendation.BACKUP
    return Recommendation.SKIP


def rank_event_snapshots(
    events: tuple[EventSnapshot, ...],
    scorer: EditorialEventScorer,
    scoring_config: ScoringConfig,
    *,
    database_path: str,
    days: int,
    category: str,
    limit: int | None,
    top: int,
    minimum_score: float,
    now: datetime | None = None,
) -> EventRankingReport:
    """Score eligible snapshots deterministically, then enrich with AI advice."""

    current = (now or datetime.now(UTC)).astimezone(UTC)
    scoring_time = current.replace(minute=0, second=0, microsecond=0)
    deterministic = [
        (
            event,
            score_event_deterministically(
                event,
                scoring_config,
                now=scoring_time,
                recency_window_days=days,
            ),
        )
        for event in events
    ]
    deterministic.sort(
        key=lambda item: (
            -item[1].total,
            _descending_timestamp(item[0]),
            item[0].id,
        )
    )
    selected = deterministic[:limit] if limit is not None else deterministic
    unranked: list[RankedEvent] = []
    for event, deterministic_score in selected:
        ai_result = scorer.score(
            EditorialScoringRequest(
                event=event,
                deterministic_score=deterministic_score,
            )
        )
        if ai_result.ai_editorial_score is None:
            final_score = deterministic_score.total
            basis = "deterministic_only"
        else:
            final_score = round(
                deterministic_score.total * scoring_config.deterministic_weight
                + ai_result.ai_editorial_score * scoring_config.ai_weight,
                2,
            )
            basis = "deterministic_and_ai"
        unranked.append(
            RankedEvent(
                rank=1,
                event=event,
                deterministic_score=deterministic_score,
                ai_result=ai_result,
                ai_editorial_score=ai_result.ai_editorial_score,
                final_score=final_score,
                score_basis=basis,
                recommendation=recommendation_for_score(final_score),
                score_weights=ScoreWeights(
                    deterministic=scoring_config.deterministic_weight,
                    ai_editorial=scoring_config.ai_weight,
                ),
            )
        )
    filtered = [item for item in unranked if item.final_score >= minimum_score]
    filtered.sort(
        key=lambda item: (
            -item.final_score,
            -item.deterministic_score.total,
            _descending_timestamp(item.event),
            item.event.id,
        )
    )
    rankings = tuple(
        item.model_copy(update={"rank": index})
        for index, item in enumerate(filtered[:top], start=1)
    )
    results = [item.ai_result for item in unranked]
    return EventRankingReport(
        generated_at=current,
        database_path=database_path,
        days=days,
        category=category,
        events_eligible=len(events),
        events_processed=len(selected),
        events_reported=len(rankings),
        ai_requests=scorer.ai_requests,
        cache_hits=sum(item.status == "cache_hit" for item in results),
        cache_misses=sum(item.cache_status in {"miss", "corrupt"} for item in results),
        failed_requests=sum(
            item.status in {"provider_error", "invalid_response", "retry_exhausted"}
            for item in results
        ),
        retries=sum(item.retry_count for item in results),
        token_usage=_sum_usage(results),
        rankings=rankings,
    )


def _descending_timestamp(event: EventSnapshot) -> float:
    value = event.last_publication_at or event.last_seen_at
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return -parsed.timestamp()


def _sum_usage(results: list[EditorialAIResult]) -> TokenUsage:
    usages = [result.token_usage for result in results if result.status == "success"]

    def total(field: str) -> int | None:
        values = [getattr(usage, field) for usage in usages]
        present = [value for value in values if value is not None]
        return sum(present) if present else None

    costs = [
        usage.estimated_cost for usage in usages if usage.estimated_cost is not None
    ]
    return TokenUsage(
        input_tokens=total("input_tokens"),
        output_tokens=total("output_tokens"),
        total_tokens=total("total_tokens"),
        estimated_cost=round(sum(costs), 8) if costs else None,
        provider_latency_ms=(
            round(
                sum(
                    usage.provider_latency_ms
                    for usage in usages
                    if usage.provider_latency_ms is not None
                ),
                3,
            )
            if any(usage.provider_latency_ms is not None for usage in usages)
            else None
        ),
    )
