from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.category_integrity import (
    CATEGORY_ORDER,
    is_clearly_english_title,
    normalize_category,
)
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
        "Rivian's 2027 changes include its No. 1 most-requested feature",
        "Terabytes of credentials leaked in massive supply-chain attack",
        "US boosts drone surveillance as flesh-eating screwworms spread in Texas",
        "Researchers found a way to hijack devices through Zoom screen sharing",
        "DEF CON crowd suspected in fake-hotspot attack on Delta flight",
        "Trump wants Big Pharma to split MMR vaccine; Big Pharma thinks it's idiotic",
        "Ukrainian drones wipe out entire US tank brigade in live war game",
        "Pet owners say smart pet feeder outage led to furry ones going unfed",
        'Kourtney Kardashian, Travis Barker Detail Rocky\'s "Terrifying" Surgery',
        "Netflix cancels popular series after three seasons",
        "Netflix cancels beloved show",
        "Pizza, pasta, potatoes, protein - how Italian children became so overweight",
        "Trump orders Smithsonian to post warnings about inaccurate US history",
        "Nigeria's president approves largest military expansion in recent times",
        "Romania blames Russia as military shoots down third drone",
        "Romanian airspace violated by drones twice in 2 days",
        "Trump orders content warnings installed outside Smithsonian museum",
        "They Gave MAGA a Safe Haven. Now They're in Retreat.",
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
        "Netflix lanseaza un show nou in Romania",
        "Donald Trump spune ca noul plan va fi prezentat maine",
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


@pytest.mark.parametrize("fallback", ("CanCan", "Diverse", "Economie"))
def test_english_article_ignores_domestic_fallback(fallback: str) -> None:
    article = _article(
        1,
        "Researchers found a way to hijack devices through screen sharing",
        (fallback,),
    )

    assert derive_categories((article,)) == ("Externe",)


@pytest.mark.parametrize(
    "title",
    (
        "Guvernul Romaniei anunta masuri noi pentru elevi",
        "Breaking news",
        "Recipe: Amish Peanut Butter Pie",
    ),
)
def test_externe_source_authority_is_independent_of_title_language(title: str) -> None:
    article = _article(1, title, ("Externe", "Diverse"))

    assert derive_categories((article,)) == ("Externe",)


@pytest.mark.parametrize(
    ("source_id", "categories", "title", "expected"),
    (
        (
            "cancan",
            ("CanCan", "Social", "Diverse"),
            "O vedeta din Romania vorbeste despre familie",
            "CanCan",
        ),
        (
            "cancan",
            ("CanCan", "Social", "Diverse"),
            "Celebrity reveals new relationship after wedding",
            "Externe",
        ),
    ),
)
def test_specialized_source_authority(
    source_id: str,
    categories: tuple[str, ...],
    title: str,
    expected: str,
) -> None:
    article = _article(1, title, categories).model_copy(update={"source_id": source_id})

    assert derive_categories((article,)) == (expected,)


def test_final_five_category_contract_and_legacy_mapping() -> None:
    assert CATEGORY_ORDER == ("Politica", "Social", "CanCan", "Diverse", "Externe")
    assert normalize_category("Economie") == "Diverse"
    assert normalize_category("Conspiratii") == "CanCan"
    assert normalize_category("Toate") is None
    assert normalize_category("all") is None


def test_click_is_authoritative_cancan_but_english_still_wins() -> None:
    romanian = _article(
        1, "Subiect local fara semnal semantic", ("CanCan", "Social", "Diverse")
    ).model_copy(update={"source_id": "click"})
    english = romanian.model_copy(
        update={"title": "Celebrity reveals new relationship after wedding"}
    )

    assert derive_categories((romanian,)) == ("CanCan",)
    assert derive_categories((english,)) == ("Externe",)


def test_feed_tag_does_not_impersonate_externe_source_authority() -> None:
    article = _article(
        1,
        "Guvernul Romaniei anunta masuri noi pentru elevi",
        ("Social",),
    ).model_copy(update={"raw_payload": '{"category": "Externe"}'})

    assert derive_categories((article,)) == ("Social",)


def test_romanian_and_unknown_articles_resolve_one_category() -> None:
    romanian = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Social", "Politica"),
    )
    unknown = _article(2, "Titlu local ambiguu", ("CategorieViitoare",))

    assert derive_categories((romanian,)) == ("Politica",)
    assert derive_categories((unknown,)) == ()


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Guvernul aproba o decizie propusa de ministru", "Politica"),
        ("Candidatul partidului intra in alegeri", "Politica"),
        ("Report urias la Loto 6 din 49", "Social"),
        ("Angajat concediat primeste despagubiri", "Social"),
        ("Festivalul aduce un flux mare de vizitatori", "Social"),
        ("Elev ranit intr-un accident langa scoala", "Social"),
        ("Compania raporteaza profit dupa o investitie", "Diverse"),
        ("Vedeta confirma o noua relatie", "CanCan"),
        ("Dezinformare si conspiratie distribuite online", "CanCan"),
        ("Material local incategorizabil", "Diverse"),
    ),
)
def test_broad_domestic_scope_uses_title_semantics(title: str, expected: str) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "Economie", "Conspiratii", "CanCan", "Diverse"),
    )

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    "titles",
    (
        (
            "Loto 6 din 49 are un report de milioane de euro",
            "Loteria anunta reportul pentru extragerea de duminica",
            "Report mare la Loto",
        ),
        (
            "Angajat concediat pentru trei cafele primeste despagubiri",
            "Compania plateste despagubiri unui angajat concediat",
        ),
        (
            "Festivalul UNTOLD aduce un flux mare de vizitatori",
            "Flux de vizitatori in oras in saptamana festivalului",
        ),
    ),
)
def test_real_defect_families_resolve_social(titles: tuple[str, ...]) -> None:
    broad = ("Politica", "Social", "Economie", "CanCan", "Diverse")
    articles = tuple(
        _article(article_id, title, broad)
        for article_id, title in enumerate(titles, start=1)
    )

    assert derive_categories(articles) == ("Social",)


def test_domestic_event_tie_does_not_use_presentation_order() -> None:
    political = _article(1, "Guvernul aproba o decizie", ("Politica", "Social"))
    social = _article(
        2, "Angajat concediat primeste despagubiri", ("Politica", "Social")
    )

    assert derive_categories((political, social)) == ("Diverse",)
    assert derive_categories((social, political)) == ("Diverse",)


def test_externe_half_threshold_and_domestic_majority_are_order_independent() -> None:
    domestic = (
        _article(1, "Guvernul aproba o decizie", ("Politica",)),
        _article(2, "Parlamentul voteaza decizia", ("Politica",)),
    )
    external = (
        _article(3, "Government approves a major decision after talks", ("Externe",)),
        _article(4, "Parliament votes on the decision after debate", ("Externe",)),
    )

    assert derive_categories((*domestic, *external)) == ("Externe",)
    assert derive_categories((external[1], domestic[0], external[0], domestic[1])) == (
        "Externe",
    )
    assert derive_categories((*domestic, external[0])) == ("Politica",)
    assert derive_categories((external[0], *reversed(domestic))) == ("Politica",)


def test_specialized_source_tie_yields_to_unanimous_event_semantics() -> None:
    click = _article(
        1,
        "Angajat concediat primeste despagubiri",
        ("CanCan", "Social", "Diverse"),
    ).model_copy(update={"source_id": "click"})
    generalist = _article(
        2,
        "Compania plateste despagubiri angajatului concediat",
        ("Politica", "Social", "Diverse"),
    )

    assert derive_categories((click, generalist)) == ("Social",)
    assert derive_categories((generalist, click)) == ("Social",)


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

    assert derive_categories((romanian, english)) == ("Externe",)
    assert derive_categories((english, romanian)) == ("Externe",)


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

    assert derive_categories((*romanian, english[0])) == ("Politica",)
    assert derive_categories((english[0], *reversed(romanian))) == ("Politica",)
    assert derive_categories((romanian[0], *english)) == ("Externe",)
    assert derive_categories((*reversed(english), romanian[0])) == ("Externe",)
    assert derive_categories((romanian[0], english[0])) == ("Externe",)


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
    assert equal.categories == ("Externe",)
    assert domestic_majority.categories == ("Politica",)


def test_legacy_multi_category_state_does_not_override_diverse_fallback() -> None:
    article = _article(1, "Titlu local ambiguu", ())
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=("Social", "Politica", "Diverse"),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    projected = canonicalize_event(existing, (article,))

    assert projected.categories == ("Diverse",)


@pytest.mark.parametrize(
    ("persisted", "current", "expected"),
    (
        ("Politica", "Social", "Social"),
        ("Social", "Economie", "Diverse"),
        ("Externe", "Social", "Social"),
    ),
)
def test_current_unanimous_evidence_overrides_legacy_category(
    persisted: str, current: str, expected: str
) -> None:
    article = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        (current,),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=(persisted,),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    assert canonicalize_event(existing, (article,)).categories == (expected,)


def test_english_evidence_overrides_legacy_cancan_category() -> None:
    article = _article(
        1,
        "Trump announces new tariffs after talks with allies",
        ("CanCan",),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=("CanCan",),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    assert canonicalize_event(existing, (article,)).categories == ("Externe",)


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
    assert [item.event_id for item in limited] == [2, 4]


def test_targeted_candidate_ids_preserve_relevance_order(tmp_path: Path) -> None:
    database = tmp_path / "scout.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates_by_ids(event_ids=(7, 3, 2))

    assert [item.event_id for item in candidates] == [7, 3, 2]
    assert [item.source_count for item in candidates] == [9, 8, 8]
