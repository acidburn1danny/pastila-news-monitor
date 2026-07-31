import sqlite3
from pathlib import Path

import pytest

from pastila_scout.cli import main
from pastila_scout.core.event_canonicalization import (
    canonicalize_event,
    derive_categories,
    select_canonical_article,
)
from pastila_scout.database import (
    attach_article_to_event,
    canonicalize_all_events,
    create_event,
    initialize_database,
    insert_article,
    load_event_snapshot,
    open_database,
    upsert_source,
)
from pastila_scout.models import ArticleProvenance, ExistingEventMetadata

NOW = "2026-07-26T12:00:00+00:00"


def _article(
    article_id: int,
    source_id: str,
    *,
    categories: tuple[str, ...] = (),
    priority: int = 1,
    title: str = "Știre românească",
    summary: str | None = "Rezumat",
    published_at: str | None = NOW,
) -> ArticleProvenance:
    return ArticleProvenance(
        id=article_id,
        event_id=1,
        source_id=source_id,
        source_name=f"Sursă {source_id}",
        url=f"https://example.com/{article_id}",
        normalized_url=f"https://example.com/{article_id}",
        title=title,
        normalized_title=title.lower(),
        summary=summary,
        published_at=published_at,
        discovered_at=NOW,
        source_categories=categories,
        source_priority=priority,
    )


def test_category_derivation_frequency_order_limit_and_unresolved() -> None:
    articles = (
        _article(1, "one", categories=("Social", "Diverse", "Politica", "CanCan")),
        _article(2, "two", categories=("Social", "Economie", "Diverse")),
    )

    assert derive_categories(articles) == ("Social", "Diverse", "Politica")
    assert len(derive_categories(articles)) == 3
    assert derive_categories((_article(3, "none"),)) == ()


def test_deterministic_selection_and_valid_summary_preservation() -> None:
    priority_article = _article(
        2,
        "priority",
        priority=2,
        title="Titlu scurt",
        summary=None,
        published_at="2026-07-26T10:00:00+00:00",
    )
    complete_article = _article(
        1,
        "normal",
        title="Titlu foarte complet",
        summary="Un rezumat mult mai complet",
        published_at="2026-07-26T08:00:00+00:00",
    )
    assert select_canonical_article((complete_article, priority_article)).id == 2

    snapshot = canonicalize_event(
        ExistingEventMetadata(
            id=1,
            canonical_title="Anterior",
            summary="Rezumat canonic păstrat",
            first_seen_at=NOW,
            last_seen_at=NOW,
            canonical_article_id=2,
        ),
        (complete_article, priority_article),
    )
    assert snapshot.canonical_title == "Titlu scurt"
    assert snapshot.canonical_summary == "Rezumat canonic păstrat"
    assert snapshot.canonical_article_id == 2


def _configured_database(path: Path) -> int:
    with open_database(path) as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="one",
            name="Știri Unu",
            source_type="rss",
            url="https://example.com/one",
            enabled=True,
            categories=("Social", "Politica"),
        )
        upsert_source(
            connection,
            source_id="two",
            name="Știri Doi",
            source_type="rss",
            url="https://example.com/two",
            enabled=True,
            categories=("Social", "Economie"),
            priority=2,
        )
        first = insert_article(
            connection,
            source_id="one",
            url="https://example.com/first",
            normalized_url="https://example.com/first",
            title="Prima știre",
            normalized_title="prima știre",
            summary="Primul rezumat",
            published_at="2026-07-26T08:00:00+00:00",
        )
        assert first is not None
        return create_event(
            connection,
            article_id=first,
            canonical_title="Prima știre",
            normalized_title="prima știre",
            seen_at=NOW,
        )


def test_metadata_updates_after_article_attachment_and_event_snapshot_is_complete(
    tmp_path: Path,
) -> None:
    database = tmp_path / "automatic.db"
    event_id = _configured_database(database)
    with open_database(database) as connection:
        second = insert_article(
            connection,
            source_id="two",
            url="https://example.com/second",
            normalized_url="https://example.com/second",
            title="A doua știre canonică",
            normalized_title="a doua știre canonică",
            summary="Al doilea rezumat, mai complet",
            published_at="2026-07-26T09:00:00+00:00",
        )
        assert second is not None
        attach_article_to_event(connection, article_id=second, event_id=event_id)
        snapshot = load_event_snapshot(connection, event_id)
        scalar_category = connection.execute(
            "SELECT category FROM events WHERE id = ?", (event_id,)
        ).fetchone()[0]

    assert snapshot.canonical_article_id == second
    assert snapshot.canonical_title == "A doua știre canonică"
    assert snapshot.categories == ("Social", "Politica", "Economie")
    assert scalar_category == "Social"
    assert snapshot.first_publication_at == "2026-07-26T08:00:00+00:00"
    assert snapshot.last_publication_at == "2026-07-26T09:00:00+00:00"
    assert snapshot.article_count == 2
    assert snapshot.source_count == 2
    assert len(snapshot.sources) == 2
    assert len(snapshot.articles) == 2
    assert snapshot.canonical_selection_reason


def _config(path: Path) -> Path:
    path.write_text(
        """sources:
  - id: one
    name: Știri Unu
    type: rss
    url: https://example.com/one
    enabled: true
    categories: [Social, Politica]
""",
        encoding="utf-8",
    )
    return path


def test_canonicalize_cli_dry_run_utf8_report_and_no_merges(tmp_path: Path) -> None:
    database = tmp_path / "istoric.db"
    event_id = _configured_database(database)
    with open_database(database) as connection:
        connection.execute(
            """UPDATE events SET canonical_article_id = NULL,
               canonical_selection_reason = NULL, category = NULL"""
        )
        connection.execute("DELETE FROM event_categories")
        connection.commit()
    before = database.read_bytes()
    reports = tmp_path / "rapoarte"

    assert (
        main(
            [
                "canonicalize-events",
                "--database",
                str(database),
                "--config",
                str(_config(tmp_path / "sources.yaml")),
                "--dry-run",
                "--output-directory",
                str(reports),
            ]
        )
        == 0
    )

    assert database.read_bytes() == before
    text = next(reports.glob("*.txt")).read_text(encoding="utf-8")
    assert "event canonicalization" in text
    assert "Prima știre" in text
    assert "Canonical article" in text
    with open_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT canonical_article_id FROM events WHERE id = ?", (event_id,)
            ).fetchone()[0]
            is None
        )
        assert (
            connection.execute(
                "SELECT categories FROM sources WHERE id = 'one'"
            ).fetchone()[0]
            == '["Social", "Politica"]'
        )


def test_canonicalization_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    database = tmp_path / "rollback.db"
    event_id = _configured_database(database)
    with open_database(database) as connection:
        connection.execute("UPDATE events SET canonical_article_id = NULL")
        connection.execute(
            f"""CREATE TRIGGER reject_canonical_update BEFORE UPDATE ON events
                WHEN OLD.id = {event_id}
                BEGIN SELECT RAISE(ABORT, 'canonical rollback'); END"""
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="canonical rollback"):
            canonicalize_all_events(
                connection,
                database_path=str(database),
                source_metadata={"one": (("Social",), 1)},
                similarity_threshold=0.72,
                lookback_hours=168,
            )
        assert (
            connection.execute(
                "SELECT canonical_article_id FROM events WHERE id = ?", (event_id,)
            ).fetchone()[0]
            is None
        )


def test_canonicalization_reports_remaining_matches_without_merging(
    tmp_path: Path,
) -> None:
    database = tmp_path / "diagnostics.db"
    _configured_database(database)
    with open_database(database) as connection:
        second = insert_article(
            connection,
            source_id="one",
            url="https://example.com/related",
            normalized_url="https://example.com/related",
            title="Prima știre",
            normalized_title="prima știre",
            summary="Rezumat asociat",
            published_at="2026-07-26T09:00:00+00:00",
        )
        assert second is not None
        create_event(
            connection,
            article_id=second,
            canonical_title="Prima știre",
            normalized_title="prima știre",
            seen_at=NOW,
        )
        report = canonicalize_all_events(
            connection,
            database_path=str(database),
            source_metadata={"one": (("Social", "Politica"), 1)},
            similarity_threshold=0.72,
            lookback_hours=168,
        )
        assert report.remaining_historical_matches == 1
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2


def test_historical_backfill_changes_then_leaves_event_unchanged(
    tmp_path: Path,
) -> None:
    database = tmp_path / "backfill.db"
    _configured_database(database)
    with open_database(database) as connection:
        connection.execute(
            """UPDATE events SET canonical_article_id = NULL,
               canonical_selection_reason = NULL, category = NULL"""
        )
        connection.execute("DELETE FROM event_categories")
        connection.commit()
        arguments = {
            "database_path": str(database),
            "source_metadata": {"one": (("Social", "Politica"), 1)},
            "similarity_threshold": 0.72,
            "lookback_hours": 168,
        }
        first = canonicalize_all_events(connection, **arguments)
        second = canonicalize_all_events(connection, **arguments)

        assert first.events_changed == 1
        assert first.categories_added == 2
        assert first.unresolved_categories == 0
        assert second.events_changed == 0
        assert second.unchanged_events == 1
