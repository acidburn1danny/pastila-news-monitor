import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from pastila_scout.database import (
    QueueStateError,
    backfill_editorial_queue,
    claim_queue_item,
    get_article_count,
    get_latest_articles,
    get_latest_poll_run,
    get_pending_queue_count,
    get_poll_run_count,
    get_queue_counts,
    get_source_counts,
    initialize_database,
    insert_article,
    list_queue_items,
    normalized_url_exists,
    open_database,
    review_queue_item,
    upsert_source,
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    database = open_database(tmp_path / "scout.db")
    initialize_database(database)
    yield database
    database.close()


def test_database_file_and_tables_are_created(tmp_path: Path) -> None:
    database_path = tmp_path / "scout.db"

    with open_database(database_path) as database:
        initialize_database(database)
        tables = {
            row["name"]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert database_path.is_file()
    assert {"sources", "articles", "poll_runs"} <= tables


def test_initialization_is_idempotent(connection: sqlite3.Connection) -> None:
    upsert_source(
        connection,
        source_id="source-1",
        name="Original",
        source_type="rss",
        url="https://example.com/feed.xml",
        enabled=True,
    )

    initialize_database(connection)

    count = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert count == 1


def test_source_upsert(connection: sqlite3.Connection) -> None:
    upsert_source(
        connection,
        source_id="source-1",
        name="Original",
        source_type="rss",
        url="https://example.com/feed.xml",
        enabled=True,
    )
    original = connection.execute(
        "SELECT * FROM sources WHERE id = 'source-1'"
    ).fetchone()

    upsert_source(
        connection,
        source_id="source-1",
        name="Updated",
        source_type="html",
        url="https://example.com/news",
        enabled=False,
    )
    updated = connection.execute(
        "SELECT * FROM sources WHERE id = 'source-1'"
    ).fetchone()

    assert updated["name"] == "Updated"
    assert updated["type"] == "html"
    assert updated["enabled"] == 0
    assert updated["created_at"] == original["created_at"]
    assert datetime.fromisoformat(updated["updated_at"]).utcoffset() is not None


def test_article_insertion_and_duplicate_prevention(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="source-1",
        name="Source",
        source_type="rss",
        url="https://example.com/feed.xml",
        enabled=True,
    )

    article_id = insert_article(
        connection,
        source_id="source-1",
        url="https://example.com/article?tracking=1",
        normalized_url="https://example.com/article",
        title="An Article",
        normalized_title="an article",
    )
    duplicate_id = insert_article(
        connection,
        source_id="source-1",
        url="https://example.com/article?tracking=2",
        normalized_url="https://example.com/article",
        title="The Same Article",
        normalized_title="the same article",
    )

    row = connection.execute("SELECT * FROM articles").fetchone()
    assert article_id == row["id"]
    assert duplicate_id is None
    assert normalized_url_exists(connection, "https://example.com/article")
    assert not normalized_url_exists(connection, "https://example.com/other")
    assert connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1
    assert datetime.fromisoformat(row["discovered_at"]).utcoffset() is not None


def test_foreign_keys_are_enforced(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        insert_article(
            connection,
            source_id="missing-source",
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            title="An Article",
            normalized_title="an article",
        )


def test_read_only_count_and_latest_run_helpers(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="enabled",
        name="Enabled",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    upsert_source(
        connection,
        source_id="disabled",
        name="Disabled",
        source_type="rss",
        url="https://example.com/other",
        enabled=False,
    )
    connection.execute(
        "INSERT INTO poll_runs (started_at, status) VALUES (?, ?)",
        ("2025-01-01T00:00:00+00:00", "success"),
    )
    connection.commit()

    assert get_source_counts(connection) == (2, 1)
    assert get_article_count(connection) == 0
    assert get_poll_run_count(connection) == 1
    assert get_latest_poll_run(connection)["status"] == "success"


def test_latest_articles_are_ordered_and_limited(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    for number in range(3):
        insert_article(
            connection,
            source_id="source",
            url=f"https://example.com/{number}",
            normalized_url=f"https://example.com/{number}",
            title=f"Article {number}",
            normalized_title=f"article {number}",
        )

    articles = get_latest_articles(connection, limit=2)

    assert [article["title"] for article in articles] == ["Article 2", "Article 1"]
    with pytest.raises(ValueError, match="positive"):
        get_latest_articles(connection, limit=0)


def test_editorial_queue_creation_is_migration_safe_and_idempotent(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as legacy:
        legacy.execute("CREATE TABLE legacy_data (id INTEGER PRIMARY KEY)")

    with open_database(database_path) as connection:
        initialize_database(connection)
        initialize_database(connection)
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'editorial_queue'"
        ).fetchone()

    assert table is not None


def test_article_insertion_automatically_queues_once(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )

    article_id = insert_article(
        connection,
        source_id="source",
        url="https://example.com/article",
        normalized_url="https://example.com/article",
        title="Article",
        normalized_title="article",
    )
    duplicate_id = insert_article(
        connection,
        source_id="source",
        url="https://example.com/article?duplicate",
        normalized_url="https://example.com/article",
        title="Duplicate",
        normalized_title="duplicate",
    )

    queue_item = connection.execute("SELECT * FROM editorial_queue").fetchone()
    assert queue_item["article_id"] == article_id
    assert queue_item["status"] == "pending"
    assert queue_item["queued_at"] is not None
    assert duplicate_id is None
    assert get_pending_queue_count(connection) == 1


def test_article_and_queue_insertion_are_atomic(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    connection.execute(
        """
        CREATE TRIGGER reject_queue_insert
        BEFORE INSERT ON editorial_queue
        BEGIN
            SELECT RAISE(ABORT, 'queue unavailable');
        END
        """
    )
    connection.commit()

    with pytest.raises(sqlite3.IntegrityError, match="queue unavailable"):
        insert_article(
            connection,
            source_id="source",
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            title="Article",
            normalized_title="article",
        )

    assert get_article_count(connection) == 0
    assert get_pending_queue_count(connection) == 0


def _insert_queue_article(
    connection: sqlite3.Connection,
    name: str,
    published_at: str | None = None,
) -> int:
    article_id = insert_article(
        connection,
        source_id="source",
        url=f"https://example.com/{name}",
        normalized_url=f"https://example.com/{name}",
        title=name,
        normalized_title=name.lower(),
        published_at=published_at,
    )
    assert article_id is not None
    return article_id


def test_pending_queue_editorial_order(connection: sqlite3.Connection) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    older_id = _insert_queue_article(connection, "Older", "2025-01-01T00:00:00+00:00")
    newer_id = _insert_queue_article(connection, "Newer", "2025-01-02T00:00:00+00:00")
    priority_id = _insert_queue_article(connection, "Priority", None)
    connection.execute(
        "UPDATE editorial_queue SET priority = 5 WHERE article_id = ?",
        (priority_id,),
    )
    connection.commit()

    items = list_queue_items(connection)

    assert [item["article_id"] for item in items] == [
        priority_id,
        newer_id,
        older_id,
    ]


def test_claim_success_and_double_claim_rejection(
    connection: sqlite3.Connection,
) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    _insert_queue_article(connection, "Article")
    queue_id = connection.execute("SELECT id FROM editorial_queue").fetchone()[0]

    claim_queue_item(connection, queue_id, "ana")

    item = connection.execute(
        "SELECT * FROM editorial_queue WHERE id = ?", (queue_id,)
    ).fetchone()
    assert item["status"] == "claimed"
    assert item["reviewer"] == "ana"
    assert item["claimed_at"] is not None
    with pytest.raises(QueueStateError, match="Cannot claim"):
        claim_queue_item(connection, queue_id, "ion")


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("keep", "reviewed"), ("backup", "reviewed"), ("reject", "rejected")],
)
def test_review_decisions(
    connection: sqlite3.Connection, decision: str, expected_status: str
) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    _insert_queue_article(connection, decision)
    queue_id = connection.execute("SELECT id FROM editorial_queue").fetchone()[0]

    review_queue_item(
        connection,
        queue_id,
        decision,
        reviewer="editor",
        notes="reviewed note",
    )

    item = connection.execute(
        "SELECT * FROM editorial_queue WHERE id = ?", (queue_id,)
    ).fetchone()
    assert item["status"] == expected_status
    assert item["decision"] == decision
    assert item["reviewer"] == "editor"
    assert item["notes"] == "reviewed note"
    assert item["reviewed_at"] is not None


def test_invalid_review_decision_is_rejected(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="Unsupported review decision"):
        review_queue_item(connection, 1, "maybe")


def test_queue_backfill_is_idempotent(connection: sqlite3.Connection) -> None:
    upsert_source(
        connection,
        source_id="source",
        name="Source",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    )
    connection.execute(
        """
        INSERT INTO articles (
            source_id, url, normalized_url, title, normalized_title, discovered_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "source",
            "https://example.com/legacy",
            "https://example.com/legacy",
            "Legacy",
            "legacy",
            "2025-01-01T00:00:00+00:00",
        ),
    )
    connection.commit()

    assert backfill_editorial_queue(connection) == 1
    assert backfill_editorial_queue(connection) == 0
    assert get_queue_counts(connection)["pending"] == 1
