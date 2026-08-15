import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from pastila_scout.desktop_scout_v1.targeted_search import (
    _significant_tokens,
    project_targeted_event_ids,
)

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


def _database(tmp_path, articles):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "scout.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE articles (
                   id INTEGER PRIMARY KEY, event_id INTEGER, source_id TEXT,
                   title TEXT, summary TEXT, published_at TEXT)"""
        )
        connection.executemany(
            """INSERT INTO articles
               (id, event_id, source_id, title, summary, published_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            articles,
        )
    return path


def _article(
    article_id,
    event_id,
    title,
    *,
    summary="",
    source="source-a",
    age=timedelta(hours=1),
):
    published = None if age is None else (NOW - age).isoformat()
    return article_id, event_id, source, title, summary, published


def _project(tmp_path, query, articles, *, excluded_source_ids=()):
    return project_targeted_event_ids(
        database_path=_database(tmp_path, articles),
        query=query,
        now=NOW,
        excluded_source_ids=excluded_source_ids,
    )


@pytest.mark.parametrize(
    "value",
    (
        "Donald Trump vizita dezastru in Iran",
        "  DONALD  TRUMP - vizita, dezastru în Iran! ",
        "Donald\tTrump / VIZITA; dezastru IN Iran",
    ),
)
def test_query_normalization_is_case_diacritic_punctuation_and_space_stable(value):
    assert _significant_tokens(value) == ("donald", "trump", "disaster", "iran")


def test_exact_title_and_split_title_summary_evidence_are_included(tmp_path):
    articles = [
        _article(1, 11, "Donald Trump disaster in Iran"),
        _article(
            2,
            12,
            "Donald Trump diplomatic visit",
            summary="Officials call the Tehran trip a disaster",
        ),
    ]

    assert _project(tmp_path, "Donald Trump dezastru Iran", articles) == (11, 12)


def test_alternate_wording_uses_only_small_safe_normalization_map(tmp_path):
    articles = [
        _article(
            1,
            21,
            "Trump faces diplomatic disaster during Tehran trip",
        )
    ]

    assert _project(tmp_path, "Donald Trump vizita dezastru in Iran", articles) == (21,)


@pytest.mark.parametrize(
    ("query", "title"),
    (
        ("breaking live ultima ora", "Breaking live news from Bucharest"),
        ("Donald Trump Iran disaster", "Donald Trump announces tariff policy"),
        ("Donald Trump Iran disaster", "Iran holds unrelated local election"),
        ("Donald Trump Iran disaster", "Very recent breaking sports news"),
    ),
)
def test_weak_or_adjacent_overlap_is_rejected(tmp_path, query, title):
    assert _project(tmp_path, query, [_article(1, 30, title)]) == ()


def test_conservative_fuzzy_support_allows_typo_but_not_weak_fuzzy_only(tmp_path):
    articles = [
        _article(1, 41, "Donald Trump crisis in Iran"),
        _article(2, 42, "Donald sports event in Iran"),
    ]

    assert _project(tmp_path, "Donlad Trump Iran", articles) == (41,)


def test_only_dated_evidence_inside_exact_48_hours_can_qualify(tmp_path):
    articles = [
        _article(
            1, 51, "Donald Trump disaster Iran", age=timedelta(hours=47, minutes=59)
        ),
        _article(
            2, 52, "Donald Trump disaster Iran", age=timedelta(hours=48, seconds=1)
        ),
        _article(3, 53, "Donald Trump disaster Iran", age=None),
        _article(4, 54, "Donald Trump disaster Iran", age=timedelta(hours=49)),
        _article(5, 54, "Unrelated fresh weather report", age=timedelta(minutes=10)),
        _article(6, 55, "Donald Trump disaster Iran", age=timedelta(minutes=-1)),
    ]

    assert _project(tmp_path, "Donald Trump disaster Iran", articles) == (51,)


def test_realistic_drone_query_rejects_adjacent_unrelated_topics(tmp_path):
    articles = [
        _article(1, 56, "Drona a intrat in spatiul aerian al Romaniei"),
        _article(2, 57, "Noua drona comerciala lansata in Romania"),
        _article(3, 58, "Atac cu drona intr-o alta tara"),
        _article(4, 59, "Aeronava civila traverseaza spatiul aerian al Romaniei"),
    ]

    assert _project(
        tmp_path, "drona a intrat in spatiul aerian al Romaniei", articles
    ) == (56,)


def test_one_source_is_eligible_and_only_matching_sources_add_support(tmp_path):
    articles = [
        _article(1, 61, "Donald Trump disaster Iran", source="a"),
        _article(2, 62, "Donald Trump disaster Iran", source="a"),
        _article(3, 62, "Donald Trump disaster Iran", source="b"),
        _article(4, 61, "Unrelated economy report", source="b"),
    ]

    assert _project(tmp_path, "Donald Trump disaster Iran", articles) == (62, 61)


def test_failed_current_source_cannot_contribute_persisted_recent_evidence(tmp_path):
    articles = [
        _article(1, 63, "Donald Trump disaster Iran", source="failed-source"),
        _article(2, 64, "Donald Trump disaster Iran", source="successful-source"),
    ]

    assert _project(
        tmp_path,
        "Donald Trump disaster Iran",
        articles,
        excluded_source_ids=("failed-source",),
    ) == (64,)


def test_duplicate_matching_articles_from_one_source_count_only_once(tmp_path):
    articles = [
        _article(1, 65, "Donald Trump disaster Iran", source="a"),
        _article(2, 65, "Donald Trump disaster Iran update", source="a"),
        _article(3, 66, "Donald Trump disaster Iran", source="a"),
        _article(4, 66, "Donald Trump disaster Iran", source="b"),
    ]

    assert _project(tmp_path, "Donald Trump disaster Iran", articles) == (66, 65)


def test_ranking_is_relevance_then_sources_then_recency_then_event_id(tmp_path):
    articles = [
        _article(1, 70, "Trump disaster Tehran", age=timedelta(minutes=1)),
        _article(2, 71, "Donald Trump disaster Iran", age=timedelta(hours=4)),
        _article(
            3, 72, "Donald Trump disaster Iran", source="a", age=timedelta(hours=3)
        ),
        _article(
            4, 72, "Donald Trump disaster Iran", source="b", age=timedelta(hours=5)
        ),
        _article(5, 73, "Donald Trump disaster Iran", age=timedelta(hours=2)),
        _article(6, 74, "Donald Trump disaster Iran", age=timedelta(hours=2)),
    ]

    assert _project(tmp_path, "Donald Trump disaster Iran", articles) == (
        72,
        73,
        74,
        71,
        70,
    )


@pytest.mark.parametrize(("available", "expected"), ((9, 9), (10, 10), (11, 10)))
def test_result_cap_remains_ten_at_independent_boundaries(
    tmp_path, available, expected
):
    many = [
        _article(index, 100 + index, f"Donald Trump disaster Iran report {index}")
        for index in range(1, available + 1)
    ]

    assert len(_project(tmp_path, "Donald Trump disaster Iran", many)) == expected


def test_result_cap_never_pads_sparse_results(tmp_path):
    sparse = [_article(1, 201, "Donald Trump disaster Iran")]

    assert _project(tmp_path / "sparse", "Donald Trump disaster Iran", sparse) == (201,)


def test_projection_requires_no_provider_or_client_dependency():
    import pastila_scout.desktop_scout_v1.targeted_search as module

    source_names = set(vars(module))
    assert not source_names & {"openai", "ollama", "provider", "client", "httpx"}
