"""Tests for deterministic and advisory editorial event ranking."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.ai.cache import FileJSONCache
from pastila_scout.ai.editorial_scoring import (
    EditorialEventScorer,
    editorial_cache_key,
)
from pastila_scout.ai.provider import ProviderError, StructuredAIResponse
from pastila_scout.cli import main
from pastila_scout.config import AIConfig, ScoringConfig
from pastila_scout.core.event_ranking import (
    rank_event_snapshots,
    recommendation_for_score,
)
from pastila_scout.core.event_scoring import score_event_deterministically
from pastila_scout.database import (
    create_event,
    initialize_database,
    insert_article,
    open_database,
    upsert_source,
)
from pastila_scout.models import (
    ArticleProvenance,
    EditorialScoringRequest,
    EventSnapshot,
    Recommendation,
    SourceProvenance,
)
from pastila_scout.reporting.event_ranking import write_ranking_reports


class FakeEditorialProvider:
    def __init__(self, responses: list[StructuredAIResponse | Exception]) -> None:
        self.responses = responses
        self.calls = 0

    def complete_structured(self, request) -> StructuredAIResponse:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _decision(**updates: object) -> str:
    payload = {
        "importance": 9,
        "virality": 8,
        "absurdity": 7,
        "satirical_potential": 9,
        "public_interest": 9,
        "emotional_impact": 8,
        "originality": 7,
        "recommendation_reason": "Subiect național puternic și verificabil.",
        "editorial_risks": ["Necesită context juridic"],
    }
    payload.update(updates)
    return json.dumps(payload, ensure_ascii=False)


def _event(
    *, event_id: int = 1, title: str = "Guvernul României anunță 10 măsuri naționale"
) -> EventSnapshot:
    article = ArticleProvenance(
        id=event_id,
        event_id=event_id,
        source_id="source",
        source_name="Sursă credibilă",
        url=f"https://example.com/{event_id}",
        normalized_url=f"https://example.com/{event_id}",
        title=title,
        normalized_title=title.casefold(),
        summary="O descriere completă a evenimentului național.",
        published_at="2026-07-26T10:00:00+00:00",
        discovered_at="2026-07-26T10:05:00+00:00",
        source_categories=("Politica",),
        source_priority=2,
    )
    return EventSnapshot(
        id=event_id,
        canonical_title=title,
        canonical_summary=article.summary,
        categories=("Politica",),
        first_publication_at=article.published_at,
        last_publication_at=article.published_at,
        first_seen_at=article.discovered_at,
        last_seen_at=article.discovered_at,
        article_count=1,
        source_count=1,
        sources=(
            SourceProvenance(
                id="source", name="Sursă credibilă", article_ids=(event_id,)
            ),
        ),
        articles=(article,),
        canonical_article_id=event_id,
        canonical_selection_reason="priority-2 source",
    )


def _ai_config(**updates: object) -> AIConfig:
    return AIConfig(enable_ai=True, retry_delay=0.0, **updates)


def test_deterministic_scoring_has_all_approved_components() -> None:
    score = score_event_deterministically(
        _event(),
        ScoringConfig(),
        now=datetime(2026, 7, 26, 12, tzinfo=UTC),
    )
    assert 0 <= score.total <= 100
    assert {item.name for item in score.components} == {
        "supporting_articles",
        "source_diversity",
        "source_credibility",
        "recency",
        "national_relevance",
        "title_strength",
        "category_weight",
    }
    assert sum(item.maximum for item in score.components) == 100
    assert all(item.normalized_value >= 0 for item in score.components)
    assert all(item.weighted_contribution == item.score for item in score.components)


def test_recommendation_threshold_boundaries() -> None:
    assert recommendation_for_score(85) is Recommendation.STRONG_PICK
    assert recommendation_for_score(84.99) is Recommendation.POSSIBLE_PICK
    assert recommendation_for_score(70) is Recommendation.POSSIBLE_PICK
    assert recommendation_for_score(69.99) is Recommendation.BACKUP
    assert recommendation_for_score(55) is Recommendation.BACKUP
    assert recommendation_for_score(54.99) is Recommendation.SKIP


def test_no_ai_mode_uses_deterministic_score(tmp_path: Path) -> None:
    ai_config = AIConfig(enable_ai=False)
    scorer = EditorialEventScorer(
        ai_config,
        ScoringConfig(),
        FileJSONCache(tmp_path / "cache"),
        None,
        api_key_available=True,
    )
    report = rank_event_snapshots(
        (_event(),),
        scorer,
        ScoringConfig(),
        database_path="readonly.db",
        days=7,
        category="all",
        limit=1,
        top=1,
        minimum_score=0,
        now=datetime(2026, 7, 26, 12, tzinfo=UTC),
    )
    ranked = report.rankings[0]
    assert ranked.ai_result.status == "disabled"
    assert ranked.ai_editorial_score is None
    assert ranked.final_score == ranked.deterministic_score.total
    assert scorer.ai_requests == 0


def test_ai_cache_hit_and_usage(tmp_path: Path) -> None:
    provider = FakeEditorialProvider([StructuredAIResponse(_decision(), 100, 50, 150)])
    config = ScoringConfig(
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=2.0,
    )
    cache = FileJSONCache(tmp_path / "cache")
    scorer = EditorialEventScorer(
        _ai_config(), config, cache, provider, api_key_available=True
    )
    request = EditorialScoringRequest(
        event=_event(),
        deterministic_score=score_event_deterministically(
            _event(), config, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    first = scorer.score(request)
    second = scorer.score(request)
    assert first.status == "success"
    assert second.status == "cache_hit"
    assert provider.calls == 1
    assert first.token_usage.total_tokens == 150
    assert first.token_usage.estimated_cost == 0.0002
    assert first.token_usage.provider_latency_ms is not None
    assert first.cache_diagnostics is not None
    assert first.cache_diagnostics.fingerprint_version == "editorial-v1"


def test_final_score_uses_approved_weighting(tmp_path: Path) -> None:
    provider = FakeEditorialProvider([StructuredAIResponse(_decision())])
    scoring = ScoringConfig()
    scorer = EditorialEventScorer(
        _ai_config(),
        scoring,
        FileJSONCache(tmp_path / "cache"),
        provider,
        api_key_available=True,
    )
    report = rank_event_snapshots(
        (_event(),),
        scorer,
        scoring,
        database_path="readonly.db",
        days=7,
        category="all",
        limit=1,
        top=1,
        minimum_score=0,
        now=datetime(2026, 7, 26, 12, tzinfo=UTC),
    )
    item = report.rankings[0]
    assert item.ai_editorial_score is not None
    assert item.final_score == round(
        item.deterministic_score.total * 0.55 + item.ai_editorial_score * 0.45,
        2,
    )
    assert item.score_weights is not None
    assert item.score_weights.deterministic == 0.55
    assert item.score_weights.ai_editorial == 0.45


def test_cache_key_invalidates_for_content_model_prompt_and_schema(
    tmp_path: Path,
) -> None:
    scoring = ScoringConfig()
    event = _event()
    request = EditorialScoringRequest(
        event=event,
        deterministic_score=score_event_deterministically(
            event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    base = editorial_cache_key(request, _ai_config(), scoring)
    changed_event = request.model_copy(
        update={"event": event.model_copy(update={"canonical_title": "Alt titlu"})}
    )
    assert base != editorial_cache_key(changed_event, _ai_config(), scoring)
    assert base != editorial_cache_key(request, _ai_config(model="other"), scoring)
    assert base != editorial_cache_key(
        request,
        _ai_config(),
        scoring.model_copy(update={"editorial_prompt_version": "v2"}),
    )
    assert base != editorial_cache_key(
        request,
        _ai_config(),
        scoring.model_copy(update={"editorial_schema_version": "v2"}),
    )


def test_malformed_output_and_retry_behavior(tmp_path: Path) -> None:
    event = _event()
    scoring = ScoringConfig()
    request = EditorialScoringRequest(
        event=event,
        deterministic_score=score_event_deterministically(
            event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    malformed = EditorialEventScorer(
        _ai_config(),
        scoring,
        FileJSONCache(tmp_path / "malformed"),
        FakeEditorialProvider([StructuredAIResponse('{"importance": 20}')]),
        api_key_available=True,
    ).score(request)
    provider = FakeEditorialProvider(
        [ProviderError("temporary"), StructuredAIResponse(_decision())]
    )
    retried = EditorialEventScorer(
        _ai_config(),
        scoring,
        FileJSONCache(tmp_path / "retry"),
        provider,
        api_key_available=True,
        sleep=lambda _: None,
    ).score(request)
    assert malformed.status == "invalid_response"
    assert retried.status == "success"
    assert retried.retry_count == 1
    assert provider.calls == 2


def test_force_refresh_bypasses_cache(tmp_path: Path) -> None:
    event = _event()
    scoring = ScoringConfig()
    request = EditorialScoringRequest(
        event=event,
        deterministic_score=score_event_deterministically(
            event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    cache = FileJSONCache(tmp_path / "cache")
    first_provider = FakeEditorialProvider([StructuredAIResponse(_decision())])
    EditorialEventScorer(
        _ai_config(), scoring, cache, first_provider, api_key_available=True
    ).score(request)
    refresh_provider = FakeEditorialProvider(
        [StructuredAIResponse(_decision(importance=1))]
    )
    refreshed = EditorialEventScorer(
        _ai_config(),
        scoring,
        cache,
        refresh_provider,
        api_key_available=True,
        force_refresh=True,
    ).score(request)
    assert refreshed.status == "success"
    assert refresh_provider.calls == 1
    assert refreshed.decision is not None
    assert refreshed.decision.importance == 1


def test_report_generation_is_utf8(tmp_path: Path) -> None:
    scorer = EditorialEventScorer(
        AIConfig(enable_ai=False),
        ScoringConfig(),
        FileJSONCache(tmp_path / "cache"),
        None,
        api_key_available=False,
    )
    report = rank_event_snapshots(
        (_event(),),
        scorer,
        ScoringConfig(),
        database_path="știri.db",
        days=7,
        category="Politica",
        limit=1,
        top=1,
        minimum_score=0,
        now=datetime(2026, 7, 26, 12, tzinfo=UTC),
    )
    json_path, text_path = write_ranking_reports(report, tmp_path / "reports")
    assert "României" in json_path.read_text(encoding="utf-8")
    text_report = text_path.read_text(encoding="utf-8")
    assert "României" in text_report
    assert "Deterministic breakdown" in text_report
    assert "normalized=" in text_report
    assert "AI dimensions" in text_report
    assert "Cache:" in text_report


def test_rank_cli_keeps_database_byte_identical(tmp_path: Path, capsys) -> None:
    database = tmp_path / "news.db"
    with open_database(database) as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="source",
            name="Sursă",
            source_type="rss",
            url="https://example.com/feed",
            enabled=True,
            categories=("Politica",),
            priority=2,
        )
        article_id = insert_article(
            connection,
            source_id="source",
            url="https://example.com/one",
            normalized_url="https://example.com/one",
            title="Guvernul României anunță 10 măsuri naționale",
            normalized_title="guvernul romaniei anunta 10 masuri nationale",
            summary="Descriere completă",
            published_at=datetime.now(UTC).isoformat(),
        )
        assert article_id is not None
        create_event(
            connection,
            article_id=article_id,
            canonical_title="Guvernul României anunță 10 măsuri naționale",
            normalized_title="guvernul romaniei anunta 10 masuri nationale",
            category="Politica",
        )
    before = database.read_bytes()
    config = tmp_path / "config.yaml"
    config.write_text("ai:\n  enable_ai: false\n", encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(
        """sources:
  - id: source
    name: Sursă
    adapter: rss
    url: https://example.com/feed
    enabled: true
    prioritate: 2
    source_category: [Politica]
""",
        encoding="utf-8",
    )
    exit_code = main(
        [
            "rank-events",
            "--database",
            str(database),
            "--config",
            str(config),
            "--days",
            "1",
            "--limit",
            "1",
            "--top",
            "1",
            "--no-ai",
            "--output-directory",
            str(tmp_path / "reports"),
        ]
    )
    assert exit_code == 0
    assert "1 eligible, 1 processed, 1 reported" in capsys.readouterr().out
    assert database.read_bytes() == before
