from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.category_integrity import is_clearly_english_title
from pastila_scout.core.event_canonicalization import (
    canonicalize_event,
    derive_categories,
)
from pastila_scout.database import initialize_database
from pastila_scout.models import ArticleProvenance, ExistingEventMetadata


@pytest.mark.parametrize(
    "title",
    (
        "Trump announces new tariffs after talks with allies",
        "Lance Bass reveals why he kept the secret for years",
        "How this family found hope after the devastating storm",
        "Biden says new plan will help 10 million families",
        "Instagram introduces a redesigned wordmark",
        "Who really needs a cocktail robot?",
        "Taylor Swift Debuts Chic Haircut After Travis Kelce Wedding",
        "Romanian prime minister says Călin Georgescu will face inquiry",
        "Trump's plan isn't working as voters turn against him",
        'APPLE WILL OPEN A NEW FACTORY AFTER TALKS WITH "EU OFFICIALS"',
        'Trump says "new plan will help voters after election',
    ),
)
def test_clearly_english_news_titles_are_detected(title: str) -> None:
    assert is_clearly_english_title(title)


@pytest.mark.parametrize(
    "title",
    (
        'Filmul "The Odyssey" al lui Christopher Nolan ajunge in cinematografe',
        "Donald Trump vine la Bucuresti pentru summitul NATO",
        "Netflix lanseaza un nou serial produs in Romania",
        'Artistul a cantat piesa "Love Me Again" la festival',
        "CEO-ul IBM anunta investitii noi in Romania",
        "Breaking news",
        "The Odyssey",
        "Șoc total la Hollywood: Star is dead",
        "OpenAI are un new model pentru Europa",
        'Filmul "The Best New Story Of Our Time" ajunge la cinema',
        "TRUMP VINE LA BUCURESTI PENTRU SUMMITUL NATO",
        "AI GPT-5.6 MSFT Q3",
    ),
)
def test_romanian_or_ambiguous_titles_are_not_forced_to_externe(title: str) -> None:
    assert not is_clearly_english_title(title)


def _article(
    article_id: int, title: str, categories: tuple[str, ...]
) -> ArticleProvenance:
    return ArticleProvenance(
        id=article_id,
        event_id=1,
        source_id=f"source-{article_id}",
        source_name=f"Source {article_id}",
        url=f"https://example.test/{article_id}",
        normalized_url=f"https://example.test/{article_id}",
        title=title,
        normalized_title=title.casefold(),
        summary="Summary",
        published_at="2026-08-14T10:00:00+00:00",
        discovered_at="2026-08-14T10:01:00+00:00",
        source_categories=categories,
    )


def test_english_domestic_article_is_authoritatively_externe() -> None:
    article = _article(
        1,
        "Lance Bass reveals why he kept the secret for years",
        ("CanCan", "Social"),
    )

    assert derive_categories((article,)) == ("Externe",)


def test_mixed_domestic_event_remains_domestic_independent_of_arrival_order() -> None:
    romanian = _article(
        1,
        "Guvernul Romaniei anunta un nou program pentru elevi",
        ("Politica", "Social"),
    )
    english = _article(
        2,
        "Government announces new program for Romanian students",
        ("Externe",),
    )

    assert derive_categories((romanian, english)) == (
        "Politica",
        "Social",
        "Externe",
    )
    assert derive_categories((english, romanian)) == (
        "Politica",
        "Social",
        "Externe",
    )


def test_cross_source_category_vote_tracks_corroboration_not_arrival_order() -> None:
    romanian = tuple(
        _article(
            article_id,
            f"Guvernul anunta masuri noi pentru orasul {article_id}",
            ("Politica",),
        )
        for article_id in (1, 2, 3)
    )
    english = tuple(
        _article(
            article_id,
            f"Government announces new measures for city {article_id}",
            ("CanCan",),
        )
        for article_id in (4, 5, 6)
    )

    assert derive_categories((*romanian, english[0])) == ("Politica", "Externe")
    assert derive_categories((english[0], *reversed(romanian))) == (
        "Politica",
        "Externe",
    )
    assert derive_categories((romanian[0], *english)) == ("Externe", "Politica")
    assert derive_categories((*reversed(english), romanian[0])) == (
        "Externe",
        "Politica",
    )
    assert derive_categories((romanian[0], english[0])) == (
        "Politica",
        "Externe",
    )


def test_english_canonical_title_requires_strict_domestic_majority() -> None:
    domestic = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Politica",),
    )
    english = _article(
        2,
        "Government announces comprehensive new measures for Romanian students",
        ("Externe",),
    )
    broad_domestic = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Politica", "Social", "Economie", "Diverse"),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title="Anterior",
        summary="Rezumat",
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    equal = canonicalize_event(existing, (broad_domestic, english))
    domestic_majority = canonicalize_event(
        existing,
        (
            domestic,
            english,
            _article(
                3,
                "Parlamentul discuta masurile pentru elevii din Romania",
                ("Politica",),
            ),
        ),
    )

    assert equal.canonical_article_id == 2
    assert equal.categories == ("Externe", "Politica", "Social")
    assert domestic_majority.categories == ("Politica", "Externe")


def _candidate_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        rows = (
            (91, "Titlu duplicat", "Politica", 2, "2026-08-14T09:00:00+00:00"),
            (3, "Social 8", "Social", 8, "2026-08-14T08:00:00+00:00"),
            (8, "Politic 5", "Politica", 5, "2026-08-14T07:00:00+00:00"),
            (2, "Titlu duplicat", "Politica", 8, "2026-08-14T06:00:00+00:00"),
            (7, "Externe 9", "Externe", 9, "2026-08-14T10:00:00+00:00"),
            (6, "Necunoscut", "Viitor", 99, "2026-08-14T11:00:00+00:00"),
            (10, "Necunoscut doi", "Alta", 99, "2026-08-14T11:00:00+00:00"),
            (4, "Politic tie recent", "Politica", 5, "2026-08-14T08:00:00+00:00"),
            (5, "Politic tie same", "Politica", 5, "2026-08-14T08:00:00+00:00"),
        )
        connection.executemany(
            """INSERT INTO events
               (id, canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at)
               VALUES (?, ?, LOWER(?), 'Rezumat', ?, ?, ?, ?, ?, ?, ?)""",
            (
                (
                    event_id,
                    title,
                    title,
                    category,
                    seen,
                    seen,
                    source_count,
                    source_count,
                    seen,
                    seen,
                )
                for event_id, title, category, source_count, seen in rows
            ),
        )


def test_normal_candidates_group_by_category_then_sources_and_stable_ties(
    tmp_path: Path,
) -> None:
    database = tmp_path / "scout.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates()
    repeated = store.list_candidates()

    assert [item.event_id for item in candidates] == [2, 4, 5, 8, 91, 3, 7, 6, 10]
    assert [item.source_count for item in candidates[:5]] == [8, 5, 5, 5, 2]
    assert repeated == candidates

    limited = store.list_candidates(limit=2)
    assert [item.event_id for item in limited] == [6, 10]


def test_targeted_candidate_ids_preserve_relevance_order(tmp_path: Path) -> None:
    database = tmp_path / "scout.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates_by_ids(event_ids=(7, 3, 2))

    assert [item.event_id for item in candidates] == [7, 3, 2]
    assert [item.source_count for item in candidates] == [9, 8, 8]
