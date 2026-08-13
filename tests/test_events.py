import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.cli import main
from pastila_scout.database import (
    attach_article_to_event,
    create_event,
    find_recent_events,
    get_event_articles,
    get_event_sources,
    initialize_database,
    insert_article,
    open_database,
    upsert_source,
)
from pastila_scout.event_matcher import match_event, title_similarity


def _source(connection: sqlite3.Connection, source_id: str, name: str) -> None:
    upsert_source(
        connection,
        source_id=source_id,
        name=name,
        source_type="rss",
        url=f"https://example.com/{source_id}",
        enabled=True,
    )


def _article(connection: sqlite3.Connection, source_id: str, suffix: str) -> int:
    article_id = insert_article(
        connection,
        source_id=source_id,
        url=f"https://example.com/{suffix}",
        normalized_url=f"https://example.com/{suffix}",
        title="Railway theft at Sadu",
        normalized_title="railway theft at sadu",
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
        _source(connection, "digi", "Digi24")
        _source(connection, "hotnews", "HotNews")
        event_id = create_event(
            connection,
            article_id=_article(connection, "digi", "cli-one"),
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            category="Social",
            seen_at=now,
        )
        attach_article_to_event(
            connection,
            article_id=_article(connection, "hotnews", "cli-two"),
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
    assert "Railway theft at Sadu" in output
    assert "Sources: 2 | Articles: 2" in output
    assert "- Digi24" in output and "- HotNews" in output
    assert "Other event" not in output
