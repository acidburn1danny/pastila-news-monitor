"""Pure deterministic editorial scoring for canonical events."""

import math
import re
from datetime import UTC, datetime

from pastila_scout.config import ScoringConfig, SourceCategory
from pastila_scout.models import DeterministicEventScore, EventSnapshot, ScoreComponent

_NATIONAL_TERMS = {
    "romania",
    "romanesc",
    "roman",
    "bucuresti",
    "guvern",
    "parlament",
    "presedinte",
    "minister",
    "national",
}


def score_event_deterministically(
    event: EventSnapshot,
    config: ScoringConfig,
    *,
    now: datetime | None = None,
    recency_window_days: int = 7,
) -> DeterministicEventScore:
    """Calculate an explainable 0-100 score from confirmed event metadata."""

    current = (now or datetime.now(UTC)).astimezone(UTC)
    article_factor = min(event.article_count / 5, 1.0)
    diversity_factor = min(event.source_count / 4, 1.0)
    priorities = [article.source_priority for article in event.articles]
    credibility_factor = (
        sum(1.0 if priority >= 2 else 0.65 for priority in priorities) / len(priorities)
        if priorities
        else 0.0
    )
    reference = _parse_datetime(event.last_publication_at or event.last_seen_at)
    age_hours = max((current - reference).total_seconds() / 3600, 0.0)
    window_hours = max(recency_window_days * 24, 1)
    recency_factor = (
        1.0
        if age_hours <= 6
        else max(0.0, 1 - ((age_hours - 6) / max(window_hours - 6, 1)))
    )
    normalized_title = event.canonical_title.casefold()
    words = set(re.findall(r"\w+", normalized_title))
    national_factor = (
        1.0
        if words & _NATIONAL_TERMS
        else (
            0.8 if set(event.categories) & {"Politica", "Social", "Economie"} else 0.4
        )
    )
    title_length = len(event.canonical_title.strip())
    length_factor = (
        min(title_length / 60, 1.0)
        if title_length <= 140
        else max(0.5, 1 - ((title_length - 140) / 280))
    )
    specificity_bonus = 0.15 if re.search(r"\d", event.canonical_title) else 0.0
    title_factor = min(1.0, length_factor + specificity_bonus)
    category_factor = max(
        (
            config.category_weights.get(SourceCategory(category), 0.0)
            for category in event.categories
            if category in {item.value for item in SourceCategory}
        ),
        default=0.0,
    )
    definitions = (
        ("supporting_articles", float(event.article_count), article_factor, 15.0),
        ("source_diversity", float(event.source_count), diversity_factor, 20.0),
        ("source_credibility", credibility_factor, credibility_factor, 15.0),
        ("recency", age_hours, recency_factor, 15.0),
        ("national_relevance", national_factor, national_factor, 15.0),
        ("title_strength", float(title_length), title_factor, 10.0),
        ("category_weight", category_factor, category_factor, 10.0),
    )
    components = tuple(
        ScoreComponent(
            name=name,
            raw_value=round(raw, 4),
            normalized_value=round(factor, 4),
            weighted_contribution=round(factor * maximum, 4),
            score=round(factor * maximum, 4),
            maximum=maximum,
            reason=_component_reason(name, raw, factor),
        )
        for name, raw, factor, maximum in definitions
    )
    total = round(min(100.0, math.fsum(item.score for item in components)), 2)
    return DeterministicEventScore(
        total=total,
        schema_version=config.deterministic_schema_version,
        components=components,
    )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _component_reason(name: str, raw: float, factor: float) -> str:
    return f"{name}: observed {raw:.2f}; normalized factor {factor:.3f}"
