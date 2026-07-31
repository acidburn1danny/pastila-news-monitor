"""Focused coverage for the private Scout to public Editor boundary adapter."""

from pathlib import Path

import pytest

from pastila_scout.cli import main
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.io import load_contract
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.exporters.editor_input import (
    EditorInputExportContext,
    export_editor_input,
    select_representative_articles,
)
from pastila_scout.models import ArticleProvenance, EventRankingReport


def article(
    article_id: int,
    source_id: str,
    *,
    priority: int = 1,
    published_at: str | None = "2026-07-26T10:00:00+00:00",
    url_suffix: str | None = None,
) -> dict[str, object]:
    suffix = url_suffix or str(article_id)
    return {
        "id": article_id,
        "event_id": 44,
        "source_id": source_id,
        "source_name": f"Sursa {source_id}",
        "url": f"https://example.ro/{suffix}",
        "normalized_url": f"https://example.ro/{suffix}",
        "title": f"Știrea {article_id}",
        "normalized_title": f"știrea {article_id}",
        "summary": f"Rezumat confirmat {article_id}",
        "published_at": published_at,
        "discovered_at": "2026-07-26T11:00:00+00:00",
        "raw_payload": '{"private": true}',
        "source_categories": ["Politica"],
        "source_priority": priority,
    }


def internal_report(*, ai_enabled: bool = True) -> EventRankingReport:
    articles = [
        article(101, "alpha", priority=2, published_at="2026-07-25T08:00:00Z"),
        article(102, "bravo", priority=2, published_at="2026-07-26T12:00:00Z"),
        article(103, "alpha", priority=3, published_at=None),
        article(104, "charlie", published_at=None),
        article(105, "delta", priority=2, published_at="2026-07-26T11:00:00Z"),
    ]
    component_names = (
        "supporting_articles",
        "source_diversity",
        "source_credibility",
        "recency",
        "national_relevance",
        "category_weight",
        "title_strength",
    )
    components = [
        {
            "name": name,
            "raw_value": float(index),
            "normalized_value": index / 10,
            "weighted_contribution": float(index + 1),
            "score": float(index + 1),
            "maximum": 15.0,
            "reason": f"Explicație {name}",
        }
        for index, name in enumerate(component_names, start=1)
    ]
    decision = (
        {
            "importance": 9,
            "virality": 8,
            "absurdity": 6,
            "satirical_potential": 9,
            "public_interest": 10,
            "emotional_impact": 8,
            "originality": 7,
            "recommendation_reason": "Relevant pentru episod.",
            "editorial_risks": ["Necesită verificare finală."],
        }
        if ai_enabled
        else None
    )
    ai_score = 90.123 if ai_enabled else None
    final_score = 85.271 if ai_enabled else 81.437
    recommendation = "STRONG_PICK" if ai_enabled else "POSSIBLE_PICK"
    return EventRankingReport.model_validate(
        {
            "generated_at": "2026-07-26T18:00:00Z",
            "database_path": "C:/private/news.db",
            "days": 7,
            "category": "all",
            "events_eligible": 20,
            "events_processed": 5,
            "events_reported": 1,
            "ai_requests": 1 if ai_enabled else 0,
            "cache_hits": 0,
            "cache_misses": 1 if ai_enabled else 0,
            "failed_requests": 0,
            "retries": 0,
            "token_usage": {
                "input_tokens": 100 if ai_enabled else None,
                "output_tokens": 50 if ai_enabled else None,
                "total_tokens": 150 if ai_enabled else None,
                "estimated_cost": 0.001 if ai_enabled else None,
                "provider_latency_ms": 123.4 if ai_enabled else None,
            },
            "rankings": [
                {
                    "rank": 7,
                    "event": {
                        "id": 44,
                        "canonical_title": "Guvernul anunță o măsură nouă",
                        "canonical_summary": "Un rezumat canonic verificat.",
                        "categories": ["Politica", "Economie"],
                        "first_publication_at": "2026-07-25T08:00:00Z",
                        "last_publication_at": "2026-07-26T12:00:00Z",
                        "first_seen_at": "2026-07-25T09:00:00Z",
                        "last_seen_at": "2026-07-26T13:00:00Z",
                        "article_count": 5,
                        "source_count": 4,
                        "sources": [
                            {"id": source, "name": f"Sursa {source}", "article_ids": []}
                            for source in ("alpha", "bravo", "charlie", "delta")
                        ],
                        "articles": articles,
                        "canonical_article_id": 101,
                        "canonical_selection_reason": "private database reasoning",
                    },
                    "deterministic_score": {
                        "total": 81.437,
                        "schema_version": "event-score-v1",
                        "components": components,
                    },
                    "ai_result": {
                        "decision": decision,
                        "ai_editorial_score": ai_score,
                        "provider": "private-provider",
                        "model": "private-model",
                        "prompt_version": "private-prompt",
                        "schema_version": "editorial-score-v1",
                        "status": "success" if ai_enabled else "disabled",
                        "requested_at": "2026-07-26T18:00:00Z",
                        "retry_count": 0,
                        "cache_status": "miss" if ai_enabled else "not_checked",
                        "token_usage": {
                            "input_tokens": 100 if ai_enabled else None,
                            "output_tokens": 50 if ai_enabled else None,
                            "total_tokens": 150 if ai_enabled else None,
                            "estimated_cost": 0.001 if ai_enabled else None,
                            "provider_latency_ms": 123.4 if ai_enabled else None,
                        },
                        "error_message": None,
                    },
                    "ai_editorial_score": ai_score,
                    "final_score": final_score,
                    "score_basis": (
                        "deterministic_and_ai" if ai_enabled else "deterministic_only"
                    ),
                    "recommendation": recommendation,
                    "score_weights": {"deterministic": 0.55, "ai_editorial": 0.45},
                }
            ],
        }
    )


def export_context(*, ai_enabled: bool = True) -> EditorInputExportContext:
    return EditorInputExportContext(
        source_run_id=f"snapshot:sha256:{'a' * 64}",
        scout_version="0.1.0",
        ranking_schema_version="event-ranking-v1",
        limit=5,
        top=10,
        minimum_score=55,
        ai_enabled=ai_enabled,
    )


def test_real_internal_report_exports_exact_scores_recommendation_and_ranks() -> None:
    report = internal_report(ai_enabled=True)

    exported = export_editor_input(report, export_context())
    event = exported.ranked_events[0]

    assert event.rank == 1
    assert event.score_rank == 7
    assert event.deterministic_score.score == 81.437
    assert event.ai_editorial_score is not None
    assert event.ai_editorial_score.score == 90.123
    assert event.final_score == 85.271
    assert event.recommendation == "STRONG_PICK"
    assert event.deterministic_score.components.recency.weighted_contribution == 5.0
    verify_scout_input_identity(exported)


def test_export_requires_explicit_valid_source_run_identity() -> None:
    with pytest.raises(ValueError):
        EditorInputExportContext(
            source_run_id="",
            scout_version="0.1.0",
            ranking_schema_version="event-ranking-v1",
            limit=5,
            top=10,
            minimum_score=0,
            ai_enabled=False,
        )


def test_provenance_selection_maximizes_sources_and_has_stable_ties() -> None:
    report = internal_report()
    articles = report.rankings[0].event.articles

    first = select_representative_articles(
        articles, canonical_article_id=101, maximum=3
    )
    second = select_representative_articles(
        articles, canonical_article_id=101, maximum=3
    )

    assert [item.id for item in first] == [103, 102, 105]
    assert len({item.source_id for item in first}) == 3
    assert first == second


def test_provenance_handles_missing_priority_timestamp_and_fewer_articles() -> None:
    values = (
        ArticleProvenance.model_validate(article(1, "a", published_at=None)),
        ArticleProvenance.model_validate(article(2, "b", priority=2)),
    )

    selected = select_representative_articles(values, canonical_article_id=1)

    assert [item.id for item in selected] == [2, 1]


def test_provenance_can_fill_from_one_source_after_maximizing_diversity() -> None:
    values = tuple(
        ArticleProvenance.model_validate(article(index, "only", priority=1))
        for index in range(1, 5)
    )

    selected = select_representative_articles(values, canonical_article_id=1)

    assert len(selected) == 3
    assert {item.source_id for item in selected} == {"only"}
    assert selected[0].id == 1


def test_export_caps_provenance_and_excludes_private_fields() -> None:
    exported = export_editor_input(internal_report(), export_context())
    serialized = exported.model_dump_json()

    assert len(exported.ranked_events[0].source_provenance) == 3
    assert exported.ranked_events[0].provenance_truncated is True
    for private_value in (
        "database_path",
        "C:/private/news.db",
        "normalized_title",
        "normalized_url",
        "raw_payload",
        "private-provider",
        "private-model",
        "private-prompt",
        "canonical_selection_reason",
    ):
        assert private_value not in serialized
    assert '"id":101' not in serialized


def test_deterministic_only_and_ai_enabled_exports_are_distinct() -> None:
    deterministic = export_editor_input(
        internal_report(ai_enabled=False), export_context(ai_enabled=False)
    )
    with_ai = export_editor_input(internal_report(), export_context())

    assert deterministic.ranking_parameters.ai_enabled is False
    assert deterministic.ranked_events[0].ai_editorial_score is None
    assert deterministic.ranked_events[0].final_score == 81.437
    assert deterministic.ranked_events[0].recommendation == "POSSIBLE_PICK"
    assert with_ai.ranked_events[0].ai_editorial_score is not None
    assert deterministic.report_id != with_ai.report_id


def test_export_identity_is_stable() -> None:
    report = internal_report()
    first = export_editor_input(report, export_context())
    second = export_editor_input(report, export_context())

    assert first.report_id == second.report_id
    assert first.content_fingerprint == second.content_fingerprint


def test_exporter_cli_success_and_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "ranking.json"
    report_path.write_text(
        internal_report().model_dump_json(indent=2), encoding="utf-8"
    )
    output_path = tmp_path / "editor-input.json"
    common = [
        "--output",
        str(output_path),
        "--source-run-id",
        f"snapshot:sha256:{'b' * 64}",
        "--scout-version",
        "0.1.0",
        "--ranking-schema-version",
        "event-ranking-v1",
        "--limit",
        "5",
        "--top",
        "10",
        "--minimum-score",
        "55",
        "--ai-enabled",
    ]

    assert main(["export-editor-input", str(report_path), *common]) == 0
    loaded = load_contract(output_path)
    assert isinstance(loaded, ScoutEditorInputV1)
    assert loaded.event_counts.reported == 1
    assert "Editor input exported" in capsys.readouterr().out

    bad = common.copy()
    bad[bad.index(f"snapshot:sha256:{'b' * 64}")] = "unsafe-run-id"
    assert main(["export-editor-input", str(report_path), *bad]) == 2
    assert "Editor input export error" in capsys.readouterr().out


def test_contracts_package_does_not_import_exporter_or_internal_models() -> None:
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pastila_scout/contracts").glob("*.py")
    )

    assert "pastila_scout.exporters" not in contents
    assert "pastila_scout.models" not in contents
