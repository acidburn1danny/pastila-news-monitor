"""Export private Scout rankings through the frozen public Editor boundary."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.contracts.identity import assign_scout_input_identity
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.models import ArticleProvenance, EventRankingReport

COMPONENT_NAMES = (
    "supporting_articles",
    "source_diversity",
    "source_credibility",
    "recency",
    "national_relevance",
    "category_weight",
    "title_strength",
)


class EditorInputExportContext(BaseModel):
    """Caller-supplied metadata that an internal report cannot prove itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_run_id: str = Field(
        pattern=r"^(poll-run:[1-9][0-9]*|snapshot:sha256:[0-9a-f]{64})$"
    )
    scout_version: str = Field(min_length=1)
    ranking_schema_version: str = Field(min_length=1)
    limit: int | None = Field(default=None, gt=0)
    top: int = Field(gt=0)
    minimum_score: float = Field(ge=0, le=100)
    ai_enabled: bool


def export_editor_input(
    report: EventRankingReport, context: EditorInputExportContext
) -> ScoutEditorInputV1:
    """Convert an internal ranking report without recalculating any Scout score."""

    _validate_context_against_report(report, context)
    public_events = tuple(
        _export_ranked_event(item, rank=index)
        for index, item in enumerate(report.rankings, start=1)
    )
    data = {
        "contract_version": "scout-editor-input-v1",
        "editorial_contract_version": "scout-editorial-semantics-v1",
        "generated_at": report.generated_at,
        "report_id": "",
        "content_fingerprint": "",
        "scout_version": context.scout_version,
        "ranking_schema_version": context.ranking_schema_version,
        "source_run_id": context.source_run_id,
        "ranking_parameters": {
            "days": report.days,
            "category_filter": None if report.category == "all" else report.category,
            "limit": context.limit,
            "top": context.top,
            "minimum_score": context.minimum_score,
            "ai_enabled": context.ai_enabled,
        },
        "event_counts": {
            "eligible": report.events_eligible,
            "processed": report.events_processed,
            "reported": len(public_events),
        },
        "ranked_events": public_events,
        "extensions": {},
    }
    return assign_scout_input_identity(data)


def select_representative_articles(
    articles: tuple[ArticleProvenance, ...],
    *,
    canonical_article_id: int,
    maximum: int = 3,
) -> tuple[ArticleProvenance, ...]:
    """Select provenance with source diversity first and stable editorial ties.

    Missing priorities use the internal model's neutral default of one. Missing
    publication timestamps sort after dated articles. Stable input order is the
    final fallback when all frozen public tie-break fields are identical.
    """

    if maximum <= 0:
        return ()
    by_source: dict[str, list[ArticleProvenance]] = {}
    for article in articles:
        by_source.setdefault(article.source_id, []).append(article)
    winners = [
        min(
            source_articles,
            key=lambda article: _provenance_key(article, canonical_article_id),
        )
        for source_articles in by_source.values()
    ]
    winners.sort(key=lambda article: _provenance_key(article, canonical_article_id))
    selected = winners[:maximum]
    if len(selected) < maximum:
        selected_urls = {article.url for article in selected}
        remaining = sorted(
            (article for article in articles if article.url not in selected_urls),
            key=lambda article: _provenance_key(article, canonical_article_id),
        )
        selected.extend(remaining[: maximum - len(selected)])
    return tuple(selected)


def _provenance_key(
    article: ArticleProvenance, canonical_article_id: int
) -> tuple[object, ...]:
    priority = getattr(article, "source_priority", 1) or 1
    timestamp = _timestamp(article.published_at)
    return (
        -priority,
        article.id != canonical_article_id,
        timestamp is None,
        -timestamp if timestamp is not None else 0.0,
        article.source_id,
        article.url,
        article.title,
    )


def _timestamp(value: str | None) -> float | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _validate_context_against_report(
    report: EventRankingReport, context: EditorInputExportContext
) -> None:
    if context.top < report.events_reported:
        raise ValueError("top cannot be smaller than the report's reported event count")
    if context.limit is not None and context.limit < report.events_processed:
        raise ValueError(
            "limit cannot be smaller than the report's processed event count"
        )
    if any(item.final_score < context.minimum_score for item in report.rankings):
        raise ValueError("minimum_score conflicts with a reported event")
    if report.events_reported != len(report.rankings):
        raise ValueError("internal report count does not match its rankings")


def _export_ranked_event(item: object, *, rank: int) -> dict[str, object]:
    event = item.event
    if not event.canonical_summary or not event.canonical_summary.strip():
        raise ValueError(f"event {event.id} has no canonical summary")
    components = {
        component.name: component for component in item.deterministic_score.components
    }
    if set(components) != set(COMPONENT_NAMES):
        raise ValueError(f"event {event.id} has incomplete deterministic components")
    provenance = select_representative_articles(
        event.articles,
        canonical_article_id=event.canonical_article_id,
    )
    if not provenance:
        raise ValueError(f"event {event.id} has no article provenance")
    decision = item.ai_result.decision
    ai_score = None
    if decision is not None and item.ai_editorial_score is not None:
        ai_score = {
            "score": item.ai_editorial_score,
            "dimensions": {
                "importance": decision.importance,
                "virality": decision.virality,
                "absurdity": decision.absurdity,
                "satirical_potential": decision.satirical_potential,
                "public_interest": decision.public_interest,
                "emotional_impact": decision.emotional_impact,
                "originality": decision.originality,
            },
        }
    recommendation_reason = (
        decision.recommendation_reason
        if decision is not None
        else item.ai_result.error_message
        or "Scout produced a deterministic-only ranking."
    )
    editorial_risks = decision.editorial_risks if decision is not None else ()
    return {
        "rank": rank,
        "score_rank": item.rank,
        "event_id": event.id,
        "canonical_title": event.canonical_title,
        "canonical_summary": event.canonical_summary,
        "publication_bounds": {
            "first_published_at": event.first_publication_at,
            "last_published_at": event.last_publication_at,
        },
        "categories": event.categories,
        "source_count": event.source_count,
        "article_count": event.article_count,
        "source_provenance": tuple(
            {
                "source_id": article.source_id,
                "source_name": article.source_name,
                "url": article.url,
                "title": article.title,
                "published_at": article.published_at,
            }
            for article in provenance
        ),
        "provenance_truncated": event.article_count > len(provenance),
        "deterministic_score": {
            "score": item.deterministic_score.total,
            "schema_version": item.deterministic_score.schema_version,
            "components": {
                name: {
                    "raw_input": components[name].raw_value,
                    "normalized_value": components[name].normalized_value,
                    "weighted_contribution": components[name].weighted_contribution,
                    "maximum_contribution": components[name].maximum,
                    "explanation": components[name].reason,
                }
                for name in COMPONENT_NAMES
            },
        },
        "ai_editorial_score": ai_score,
        "final_score": item.final_score,
        "recommendation": item.recommendation.value,
        "scout_recommendation_reason": recommendation_reason,
        "editorial_risks": editorial_risks,
        "score_basis": item.score_basis,
        "extensions": {},
    }
