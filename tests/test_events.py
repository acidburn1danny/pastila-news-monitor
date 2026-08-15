import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.cli import main
from pastila_scout.database import (
    attach_article_to_event,
    create_event,
    find_recent_events,
    get_event_articles,
    get_event_sources,
    initialize_database,
    insert_article,
    load_reconciliation_snapshot,
    open_database,
    refresh_event_canonical_metadata,
    upsert_source,
)
from pastila_scout.event_matcher import match_event, title_similarity


def _source(
    connection: sqlite3.Connection,
    source_id: str,
    name: str,
    *,
    categories: tuple[str, ...] = (),
) -> None:
    upsert_source(
        connection,
        source_id=source_id,
        name=name,
        source_type="rss",
        url=f"https://example.com/{source_id}",
        enabled=True,
        categories=categories,
    )


def _article(
    connection: sqlite3.Connection,
    source_id: str,
    suffix: str,
    *,
    title: str = "Railway theft at Sadu",
) -> int:
    article_id = insert_article(
        connection,
        source_id=source_id,
        url=f"https://example.com/{suffix}",
        normalized_url=f"https://example.com/{suffix}",
        title=title,
        normalized_title=title.casefold(),
    )
    assert article_id is not None
    return article_id


def test_event_creation_attachment_and_distinct_source_counts(tmp_path: Path) -> None:
    with open_database(tmp_path / "events.db") as connection:
        initialize_database(connection)
        _source(connection, "digi", "Digi24")
        _source(connection, "hotnews", "HotNews")
        _source(connection, "g4media", "G4Media")
        first = _article(connection, "digi", "one")
        event_id = create_event(
            connection,
            article_id=first,
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            category="Social",
        )
        attach_article_to_event(
            connection,
            article_id=_article(connection, "digi", "two"),
            event_id=event_id,
        )
        attach_article_to_event(
            connection,
            article_id=_article(connection, "hotnews", "three"),
            event_id=event_id,
        )
        attach_article_to_event(
            connection,
            article_id=_article(connection, "g4media", "four"),
            event_id=event_id,
        )

        event = connection.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        assert event["article_count"] == 4
        assert event["source_count"] == 3
        assert len(get_event_articles(connection, event_id)) == 4
        assert [row["name"] for row in get_event_sources(connection, event_id)] == [
            "Digi24",
            "G4Media",
            "HotNews",
        ]


def test_scalar_category_mirror_is_idempotent_and_repairs_missing_row(
    tmp_path: Path,
) -> None:
    with open_database(tmp_path / "category-mirror.db") as connection:
        initialize_database(connection)
        _source(connection, "social", "Social", categories=("Social",))
        article_id = _article(connection, "social", "one")
        event_id = create_event(
            connection,
            article_id=article_id,
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            category="Social",
        )

        refresh_event_canonical_metadata(connection, event_id)
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT category, position FROM event_categories WHERE event_id = ?",
                (event_id,),
            )
        ] == [("Social", 0)]

        connection.execute(
            "DELETE FROM event_categories WHERE event_id = ?", (event_id,)
        )
        refresh_event_canonical_metadata(connection, event_id)
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT category, position FROM event_categories WHERE event_id = ?",
                (event_id,),
            )
        ] == [("Social", 0)]


def test_category_mirror_failure_rolls_back_event_creation(tmp_path: Path) -> None:
    with open_database(tmp_path / "category-atomicity.db") as connection:
        initialize_database(connection)
        _source(connection, "social", "Social", categories=("Social",))
        article_id = _article(connection, "social", "one")
        connection.execute(
            """CREATE TRIGGER reject_category_mirror
               BEFORE INSERT ON event_categories
               BEGIN SELECT RAISE(ABORT, 'injected category mirror failure'); END"""
        )

        with pytest.raises(
            sqlite3.IntegrityError, match="injected category mirror failure"
        ):
            create_event(
                connection,
                article_id=article_id,
                canonical_title="Railway theft at Sadu",
                normalized_title="railway theft at sadu",
                category="Social",
            )

        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT event_id FROM articles WHERE id = ?", (article_id,)
            ).fetchone()[0]
            is None
        )


def test_reconciliation_uses_stored_metadata_for_removed_source(
    tmp_path: Path,
) -> None:
    with open_database(tmp_path / "historical-source.db") as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="historical",
            name="Historical Source",
            source_type="rss",
            url="https://example.com/historical",
            enabled=False,
            categories=("Politica", "Social", "Diverse"),
            priority=2,
        )
        article_id = _article(connection, "historical", "archived")
        create_event(
            connection,
            article_id=article_id,
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            category="Social",
        )

        historical = load_reconciliation_snapshot(connection).articles[0]
        connection.execute(
            "UPDATE sources SET categories = 'not-json', priority = 3 "
            "WHERE id = 'historical'"
        )
        malformed = load_reconciliation_snapshot(connection).articles[0]
        current = load_reconciliation_snapshot(
            connection,
            {"historical": (("Externe",), 1)},
        ).articles[0]

    assert historical.source_categories == ("Politica", "Social", "Diverse")
    assert historical.source_priority == 2
    assert malformed.source_categories == ()
    assert malformed.source_priority == 3
    assert current.source_categories == ("Externe",)
    assert current.source_priority == 1


def test_reconciliation_uses_neutral_metadata_when_source_row_is_missing(
    tmp_path: Path,
) -> None:
    with open_database(tmp_path / "missing-source.db") as connection:
        initialize_database(connection)
        _source(connection, "removed", "Removed Source")
        article_id = _article(connection, "removed", "orphaned")
        create_event(
            connection,
            article_id=article_id,
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            category="Social",
        )
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("DELETE FROM sources WHERE id = 'removed'")
        connection.commit()

        article = load_reconciliation_snapshot(connection).articles[0]

    assert article.source_id == "removed"
    assert article.source_name == "removed"
    assert article.source_categories == ()
    assert article.source_priority == 1


def test_initialization_migrates_and_backfills_legacy_articles(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as legacy:
        legacy.executescript(
            """
            CREATE TABLE sources (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
                url TEXT NOT NULL, enabled INTEGER NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
                url TEXT NOT NULL, normalized_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL, normalized_title TEXT NOT NULL,
                summary TEXT, published_at TEXT, discovered_at TEXT NOT NULL,
                raw_payload TEXT, FOREIGN KEY(source_id) REFERENCES sources(id)
            );
            INSERT INTO sources VALUES
                ('old', 'Old', 'rss', 'https://example.com', 1, '2025-01-01', '2025-01-01');
            INSERT INTO articles VALUES
                (1, 'old', 'https://example.com/a', 'https://example.com/a',
                 'Legacy story', 'legacy story', NULL, NULL,
                 '2025-01-01T00:00:00+00:00', NULL);
        """
        )
    with open_database(database_path) as connection:
        initialize_database(connection)
        article = connection.execute("SELECT event_id FROM articles").fetchone()
        event = connection.execute("SELECT * FROM events").fetchone()
        assert article["event_id"] == event["id"]
        assert (event["article_count"], event["source_count"]) == (1, 1)
        initialize_database(connection)
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_matcher_positive_negative_threshold_and_time_window(tmp_path: Path) -> None:
    assert (
        title_similarity(
            "2.4 km of railway stolen", "Investigation after railway theft"
        )
        == 1
    )
    assert title_similarity("Railway stolen from Sadu", "2.4 km of railway stolen") == 1
    assert (
        title_similarity("Railway sabotage with rocks", "2.4 km of railway stolen")
        < 0.72
    )
    assert title_similarity("Știre despre furt", "ŞTIRE DESPRE FURT") == 1

    with open_database(tmp_path / "matcher.db") as connection:
        initialize_database(connection)
        _source(connection, "digi", "Digi24")
        event_id = create_event(
            connection,
            article_id=_article(connection, "digi", "matcher"),
            canonical_title="2.4 km of railway stolen",
            normalized_title="2 4 km of railway stolen",
            seen_at="2025-01-01T00:00:00+00:00",
        )
        recent = find_recent_events(connection, cutoff="2024-12-31T00:00:00+00:00")
        assert (
            match_event(
                "Investigation after railway theft", recent, threshold=0.72
            ).event_id
            == event_id
        )
        assert (
            match_event("Investigation after railway theft", recent, threshold=1.01)
            is None
        )
        assert find_recent_events(connection, cutoff="2025-01-02T00:00:00+00:00") == []


def test_events_cli_filters_and_displays_source_provenance(
    tmp_path: Path, capsys
) -> None:
    database = tmp_path / "cli.db"
    now = datetime.now(UTC).isoformat()
    with open_database(database) as connection:
        initialize_database(connection)
        _source(connection, "digi", "Digi24", categories=("Social",))
        _source(connection, "hotnews", "HotNews", categories=("Social",))
        social_title = "Furt pe calea ferata la Sadu"
        event_id = create_event(
            connection,
            article_id=_article(connection, "digi", "cli-one", title=social_title),
            canonical_title=social_title,
            normalized_title=social_title.casefold(),
            category="Social",
            seen_at=now,
        )
        attach_article_to_event(
            connection,
            article_id=_article(connection, "hotnews", "cli-two", title=social_title),
            event_id=event_id,
            seen_at=now,
        )
        create_event(
            connection,
            article_id=_article(connection, "digi", "other"),
            canonical_title="Other event",
            normalized_title="other event",
            category="Social",
            seen_at=now,
        )

    assert (
        main(
            [
                "events",
                "--database",
                str(database),
                "--limit",
                "1",
                "--min-sources",
                "2",
                "--hours",
                "24",
                "--category",
                "Social",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert social_title in output
    assert "Sources: 2 | Articles: 2" in output
    assert "- Digi24" in output and "- HotNews" in output
    assert "Other event" not in output
