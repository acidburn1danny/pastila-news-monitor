"""SQLite persistence helpers for Scout sources and articles."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.models import (
    ArticleProvenance,
    AuditArticle,
    AuditEvent,
    EventCanonicalizationChange,
    EventCanonicalizationReport,
    EventIntegritySnapshot,
    EventReconciliationPlan,
    EventSnapshot,
    ExistingEventMetadata,
    ReconciliationArticle,
    ReconciliationEvent,
    ReconciliationSnapshot,
)


def utc_now() -> str:
    """Return the current time as a UTC ISO 8601 string."""

    return datetime.now(UTC).isoformat()


def open_database(path: Path) -> sqlite3.Connection:
    """Open a SQLite database with named rows and foreign keys enabled."""

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def open_database_readonly(path: Path) -> sqlite3.Connection:
    """Open an existing SQLite database in enforced read-only mode."""

    database_uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def load_event_integrity_snapshot(
    connection: sqlite3.Connection,
) -> EventIntegritySnapshot:
    """Load the minimal immutable state required by the event audit."""

    articles = tuple(
        AuditArticle(
            id=int(row["id"]),
            event_id=int(row["event_id"]) if row["event_id"] is not None else None,
            source_id=str(row["source_id"]),
            source_name=row["source_name"],
            title=str(row["title"]),
            published_at=row["published_at"],
        )
        for row in connection.execute(
            """SELECT a.id, a.event_id, a.source_id, s.name AS source_name,
                      a.title, a.published_at
               FROM articles AS a
               LEFT JOIN sources AS s ON s.id = a.source_id
               ORDER BY a.id"""
        ).fetchall()
    )
    events = tuple(
        AuditEvent(
            id=int(row["id"]),
            canonical_title=str(row["canonical_title"]),
            summary=row["summary"],
            category=row["category"],
            first_seen_at=str(row["first_seen_at"]),
            last_seen_at=str(row["last_seen_at"]),
            article_count=int(row["article_count"]),
            source_count=int(row["source_count"]),
        )
        for row in connection.execute(
            """SELECT id, canonical_title, summary, category, first_seen_at,
                      last_seen_at, article_count, source_count
               FROM events ORDER BY id"""
        ).fetchall()
    )
    return EventIntegritySnapshot(articles=articles, events=events)


class StaleReconciliationPlanError(ValueError):
    """Raised when persisted event state no longer matches a plan."""


def load_reconciliation_snapshot(
    connection: sqlite3.Connection,
    source_metadata: dict[str, tuple[tuple[str, ...], int]] | None = None,
) -> ReconciliationSnapshot:
    """Load reconciliation state without modifying the connection."""

    metadata = source_metadata or {}
    has_categories = connection.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type = 'table' AND name = 'event_categories'"""
    ).fetchone()
    categories_by_event: dict[int, list[str]] = {}
    if has_categories:
        for row in connection.execute(
            "SELECT event_id, category FROM event_categories ORDER BY position"
        ):
            categories_by_event.setdefault(int(row["event_id"]), []).append(
                str(row["category"])
            )
    events = tuple(
        ReconciliationEvent(
            id=int(row["id"]),
            canonical_title=str(row["canonical_title"]),
            normalized_title=str(row["normalized_title"]),
            summary=row["summary"],
            categories=tuple(
                categories_by_event.get(int(row["id"]))
                or ([str(row["category"])] if row["category"] else [])
            ),
            first_seen_at=str(row["first_seen_at"]),
            last_seen_at=str(row["last_seen_at"]),
            article_count=int(row["article_count"]),
            source_count=int(row["source_count"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            canonical_article_id=(
                int(row["canonical_article_id"])
                if row["canonical_article_id"] is not None
                else None
            ),
        )
        for row in connection.execute("SELECT * FROM events ORDER BY id")
    )
    articles: list[ReconciliationArticle] = []
    for row in connection.execute(
        """SELECT a.*, s.name AS source_name FROM articles AS a
           LEFT JOIN sources AS s ON s.id = a.source_id
           WHERE a.event_id IS NOT NULL ORDER BY a.id"""
    ):
        source_id = str(row["source_id"])
        source_categories, priority = metadata.get(source_id, ((), 1))
        articles.append(
            ReconciliationArticle(
                id=int(row["id"]),
                event_id=int(row["event_id"]),
                source_id=source_id,
                source_name=str(row["source_name"] or source_id),
                url=str(row["url"]),
                normalized_url=str(row["normalized_url"]),
                title=str(row["title"]),
                normalized_title=str(row["normalized_title"]),
                summary=row["summary"],
                published_at=row["published_at"],
                discovered_at=str(row["discovered_at"]),
                raw_payload=row["raw_payload"],
                source_categories=source_categories,
                source_priority=priority,
            )
        )
    return ReconciliationSnapshot(events=events, articles=tuple(articles))


def apply_reconciliation_plan(
    connection: sqlite3.Connection,
    plan: EventReconciliationPlan,
    *,
    dry_run: bool = False,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Validate and atomically apply every proposal in an explicit plan."""

    from pastila_scout.core.event_reconciliation import proposal_state_fingerprint

    connection.execute("BEGIN IMMEDIATE")
    try:
        _ensure_canonical_schema(connection)
        snapshot = load_reconciliation_snapshot(connection)
        for proposal in plan.proposals:
            current = proposal_state_fingerprint(snapshot, proposal.event_ids)
            if current != proposal.state_fingerprint:
                raise StaleReconciliationPlanError(
                    f"Event group {proposal.event_ids} changed after plan generation"
                )
            relevant_articles = tuple(
                article
                for article in snapshot.articles
                if article.event_id in set(proposal.event_ids)
            )
            if (
                tuple(article.id for article in relevant_articles)
                != proposal.article_ids
            ):
                raise StaleReconciliationPlanError(
                    f"Article membership changed for event group {proposal.event_ids}"
                )
            if proposal.resulting_article_count != len(relevant_articles):
                raise ValueError("Plan contains an invalid resulting article count")
            if proposal.resulting_source_count != len(
                {article.source_id for article in relevant_articles}
            ):
                raise ValueError("Plan contains an invalid resulting source count")
        if dry_run:
            connection.rollback()
            return (), ()

        connection.execute(
            """CREATE TABLE IF NOT EXISTS event_categories (
                   event_id INTEGER NOT NULL,
                   category TEXT NOT NULL CHECK (category IN (
                       'Politica', 'Social', 'Conspiratii', 'Economie',
                       'CanCan', 'Externe', 'Diverse'
                   )),
                   position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 2),
                   PRIMARY KEY (event_id, category),
                   UNIQUE (event_id, position),
                   FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
               )"""
        )
        survivors: list[int] = []
        merged: list[int] = []
        timestamp = utc_now()
        for proposal in plan.proposals:
            survivor = proposal.surviving_event_id
            removed = [
                event_id for event_id in proposal.event_ids if event_id != survivor
            ]
            placeholders = ",".join("?" for _ in proposal.event_ids)
            connection.execute(
                f"UPDATE articles SET event_id = ? WHERE event_id IN ({placeholders})",
                (survivor, *proposal.event_ids),
            )
            bounds = connection.execute(
                f"""SELECT MIN(first_seen_at), MAX(last_seen_at), MIN(created_at)
                    FROM events WHERE id IN ({placeholders})""",
                proposal.event_ids,
            ).fetchone()
            selection = proposal.canonical_selection
            connection.execute(
                """UPDATE events SET canonical_title = ?, normalized_title = ?,
                       summary = ?, category = ?, first_seen_at = ?, last_seen_at = ?,
                       created_at = ?, updated_at = ?, canonical_article_id = ?,
                       canonical_selection_reason = ?, first_published_at = ?,
                       last_published_at = ?,
                       article_count = (SELECT COUNT(*) FROM articles WHERE event_id = ?),
                       source_count = (SELECT COUNT(DISTINCT source_id)
                                       FROM articles WHERE event_id = ?)
                   WHERE id = ?""",
                (
                    selection.title,
                    selection.normalized_title,
                    selection.summary,
                    (
                        proposal.proposed_categories[0]
                        if proposal.proposed_categories
                        else None
                    ),
                    bounds[0],
                    bounds[1],
                    bounds[2],
                    timestamp,
                    selection.article_id,
                    selection.reason,
                    proposal.publication_start,
                    proposal.publication_end,
                    survivor,
                    survivor,
                    survivor,
                ),
            )
            connection.execute(
                "DELETE FROM event_categories WHERE event_id = ?", (survivor,)
            )
            connection.executemany(
                """INSERT INTO event_categories (event_id, category, position)
                   VALUES (?, ?, ?)""",
                [
                    (survivor, category, position)
                    for position, category in enumerate(proposal.proposed_categories)
                ],
            )
            for event_id in removed:
                cursor = connection.execute(
                    """DELETE FROM events WHERE id = ?
                       AND NOT EXISTS (SELECT 1 FROM articles WHERE event_id = ?)""",
                    (event_id, event_id),
                )
                if cursor.rowcount != 1:
                    raise sqlite3.IntegrityError(
                        f"Merged event {event_id} remains referenced"
                    )
            survivors.append(survivor)
            merged.extend(removed)
        connection.commit()
        return tuple(survivors), tuple(merged)
    except Exception:
        connection.rollback()
        raise


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the Scout schema and indexes if they do not already exist."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            url TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
            ,categories TEXT NOT NULL DEFAULT '[]'
            ,priority INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            summary TEXT,
            category TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            article_count INTEGER NOT NULL DEFAULT 0,
            source_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
            ,canonical_article_id INTEGER
            ,canonical_selection_reason TEXT
            ,first_published_at TEXT
            ,last_published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            url TEXT NOT NULL,
            normalized_url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            summary TEXT,
            published_at TEXT,
            discovered_at TEXT NOT NULL,
            raw_payload TEXT,
            event_id INTEGER,
            FOREIGN KEY(source_id) REFERENCES sources(id),
            FOREIGN KEY(event_id) REFERENCES events(id)
        );

        CREATE TABLE IF NOT EXISTS poll_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            sources_checked INTEGER NOT NULL DEFAULT 0,
            articles_found INTEGER NOT NULL DEFAULT 0,
            articles_inserted INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS editorial_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK (
                status IN ('pending', 'claimed', 'reviewed', 'rejected')
            ),
            priority INTEGER NOT NULL DEFAULT 0,
            queued_at TEXT NOT NULL,
            claimed_at TEXT,
            reviewed_at TEXT,
            reviewer TEXT,
            decision TEXT CHECK (
                decision IS NULL OR decision IN ('keep', 'reject', 'backup')
            ),
            notes TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS event_categories (
            event_id INTEGER NOT NULL,
            category TEXT NOT NULL CHECK (category IN (
                'Politica', 'Social', 'Conspiratii', 'Economie',
                'CanCan', 'Externe', 'Diverse'
            )),
            position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 2),
            PRIMARY KEY (event_id, category),
            UNIQUE (event_id, position),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_articles_source_id
            ON articles(source_id);
        CREATE INDEX IF NOT EXISTS idx_articles_published_at
            ON articles(published_at);
        CREATE INDEX IF NOT EXISTS idx_articles_normalized_title
            ON articles(normalized_title);
        CREATE INDEX IF NOT EXISTS idx_events_last_seen_at
            ON events(last_seen_at);
        CREATE INDEX IF NOT EXISTS idx_poll_runs_started_at
            ON poll_runs(started_at);
        CREATE INDEX IF NOT EXISTS idx_editorial_queue_status_priority
            ON editorial_queue(status, priority DESC);
        """
    )
    article_columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(articles)").fetchall()
    }
    if "event_id" not in article_columns:
        connection.execute(
            "ALTER TABLE articles ADD COLUMN event_id INTEGER REFERENCES events(id)"
        )
    _add_column_if_missing(
        connection, "sources", "categories", "TEXT NOT NULL DEFAULT '[]'"
    )
    _add_column_if_missing(
        connection, "sources", "priority", "INTEGER NOT NULL DEFAULT 1"
    )
    _add_column_if_missing(connection, "events", "canonical_article_id", "INTEGER")
    _add_column_if_missing(connection, "events", "canonical_selection_reason", "TEXT")
    _add_column_if_missing(connection, "events", "first_published_at", "TEXT")
    _add_column_if_missing(connection, "events", "last_published_at", "TEXT")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_event_id ON articles(event_id)"
    )
    _backfill_article_events(connection)
    connection.commit()


def _add_column_if_missing(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def canonicalize_all_events(
    connection: sqlite3.Connection,
    *,
    database_path: str,
    source_metadata: dict[str, tuple[tuple[str, ...], int]],
    similarity_threshold: float,
    lookback_hours: float,
    dry_run: bool = False,
) -> EventCanonicalizationReport:
    """Canonicalize every event atomically and return complete counters."""

    from pastila_scout.core.event_reconciliation import build_reconciliation_plan

    connection.execute("BEGIN IMMEDIATE")
    try:
        _ensure_canonical_schema(connection)
        for source_id, (categories, priority) in source_metadata.items():
            connection.execute(
                "UPDATE sources SET categories = ?, priority = ? WHERE id = ?",
                (json.dumps(categories, ensure_ascii=False), priority, source_id),
            )
        changes: list[EventCanonicalizationChange] = []
        for row in connection.execute("SELECT * FROM events ORDER BY id").fetchall():
            event_id = int(row["id"])
            before_categories = tuple(
                str(item["category"])
                for item in connection.execute(
                    """SELECT category FROM event_categories
                       WHERE event_id = ? ORDER BY position""",
                    (event_id,),
                )
            )
            if not before_categories and row["category"]:
                before_categories = (str(row["category"]),)
            snapshot = refresh_event_canonical_metadata(
                connection, event_id, source_metadata=source_metadata
            )
            title_changed = str(row["canonical_title"]) != snapshot.canonical_title
            summary_changed = row["summary"] != snapshot.canonical_summary
            changed = any(
                (
                    title_changed,
                    summary_changed,
                    before_categories != snapshot.categories,
                    row["canonical_article_id"] != snapshot.canonical_article_id,
                    row["first_published_at"] != snapshot.first_publication_at,
                    row["last_published_at"] != snapshot.last_publication_at,
                    int(row["article_count"]) != snapshot.article_count,
                    int(row["source_count"]) != snapshot.source_count,
                )
            )
            changes.append(
                EventCanonicalizationChange(
                    event_id=event_id,
                    changed=changed,
                    categories_before=before_categories,
                    categories_after=snapshot.categories,
                    title_changed=title_changed,
                    summary_changed=summary_changed,
                    canonical_title=snapshot.canonical_title,
                    canonical_summary=snapshot.canonical_summary,
                    first_publication_at=snapshot.first_publication_at,
                    last_publication_at=snapshot.last_publication_at,
                    canonical_article_id=snapshot.canonical_article_id,
                    selection_reason=snapshot.canonical_selection_reason,
                )
            )
        reconciliation = build_reconciliation_plan(
            load_reconciliation_snapshot(connection, source_metadata),
            database_path=database_path,
            similarity_threshold=similarity_threshold,
            lookback_hours=lookback_hours,
        )
        report = EventCanonicalizationReport(
            generated_at=utc_now(),
            database_path=database_path,
            dry_run=dry_run,
            events_checked=len(changes),
            events_changed=sum(change.changed for change in changes),
            categories_added=sum(
                len(set(change.categories_after) - set(change.categories_before))
                for change in changes
            ),
            canonical_titles_changed=sum(change.title_changed for change in changes),
            canonical_summaries_changed=sum(
                change.summary_changed for change in changes
            ),
            unresolved_categories=sum(
                not change.categories_after for change in changes
            ),
            unchanged_events=sum(not change.changed for change in changes),
            remaining_historical_matches=len(reconciliation.proposals),
            remaining_historical_event_groups=tuple(
                proposal.event_ids for proposal in reconciliation.proposals
            ),
            changes=tuple(changes),
        )
        if dry_run:
            connection.rollback()
        else:
            connection.commit()
        return report
    except Exception:
        connection.rollback()
        raise


def _ensure_canonical_schema(connection: sqlite3.Connection) -> None:
    """Create only metadata storage required by explicit canonicalization."""

    _add_column_if_missing(
        connection, "sources", "categories", "TEXT NOT NULL DEFAULT '[]'"
    )
    _add_column_if_missing(
        connection, "sources", "priority", "INTEGER NOT NULL DEFAULT 1"
    )
    _add_column_if_missing(connection, "events", "canonical_article_id", "INTEGER")
    _add_column_if_missing(connection, "events", "canonical_selection_reason", "TEXT")
    _add_column_if_missing(connection, "events", "first_published_at", "TEXT")
    _add_column_if_missing(connection, "events", "last_published_at", "TEXT")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS event_categories (
               event_id INTEGER NOT NULL,
               category TEXT NOT NULL CHECK (category IN (
                   'Politica', 'Social', 'Conspiratii', 'Economie',
                   'CanCan', 'Externe', 'Diverse'
               )),
               position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 2),
               PRIMARY KEY (event_id, category), UNIQUE (event_id, position),
               FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
           )"""
    )


def create_event(
    connection: sqlite3.Connection,
    *,
    article_id: int,
    canonical_title: str,
    normalized_title: str,
    summary: str | None = None,
    category: str | None = None,
    seen_at: str | None = None,
) -> int:
    """Create an event for an article and return the new event ID."""

    timestamp = seen_at or utc_now()
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO events (
                canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                canonical_title,
                normalized_title,
                summary,
                category,
                timestamp,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        event_id = int(cursor.lastrowid)
        _set_article_event(connection, article_id, event_id)
        refresh_event_canonical_metadata(connection, event_id)
    return event_id


def find_recent_events(
    connection: sqlite3.Connection, *, cutoff: str
) -> list[sqlite3.Row]:
    """Return events seen at or after an ISO 8601 UTC cutoff."""

    return list(
        connection.execute(
            """SELECT id, canonical_title, normalized_title, summary, category,
                      first_seen_at, last_seen_at, article_count, source_count
               FROM events WHERE last_seen_at >= ? ORDER BY last_seen_at DESC, id ASC""",
            (cutoff,),
        ).fetchall()
    )


def attach_article_to_event(
    connection: sqlite3.Connection,
    *,
    article_id: int,
    event_id: int,
    seen_at: str | None = None,
) -> None:
    """Attach an unassigned article and refresh the event's aggregate counts."""

    with connection:
        _set_article_event(connection, article_id, event_id)
        if seen_at is not None:
            connection.execute(
                "UPDATE events SET last_seen_at = MAX(last_seen_at, ?) WHERE id = ?",
                (seen_at, event_id),
            )
        refresh_event_canonical_metadata(connection, event_id)


def refresh_event_canonical_metadata(
    connection: sqlite3.Connection,
    event_id: int,
    *,
    source_metadata: dict[str, tuple[tuple[str, ...], int]] | None = None,
) -> EventSnapshot:
    """Canonicalize and persist one event using the shared pure service."""

    from pastila_scout.core.event_canonicalization import canonicalize_event

    event_row = connection.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if event_row is None:
        raise ValueError(f"Event {event_id} does not exist")
    existing_categories = tuple(
        str(row["category"])
        for row in connection.execute(
            """SELECT category FROM event_categories
               WHERE event_id = ? ORDER BY position""",
            (event_id,),
        )
    )
    if not existing_categories and event_row["category"]:
        existing_categories = (str(event_row["category"]),)
    metadata = source_metadata or {}
    articles: list[ArticleProvenance] = []
    for row in connection.execute(
        """SELECT a.*, s.name AS source_name, s.categories AS stored_categories,
                  s.priority AS stored_priority
           FROM articles AS a JOIN sources AS s ON s.id = a.source_id
           WHERE a.event_id = ? ORDER BY a.id""",
        (event_id,),
    ):
        source_id = str(row["source_id"])
        if source_id in metadata:
            categories, priority = metadata[source_id]
        else:
            categories = _decode_categories(row["stored_categories"])
            priority = int(row["stored_priority"])
        articles.append(
            ArticleProvenance(
                id=int(row["id"]),
                event_id=event_id,
                source_id=source_id,
                source_name=str(row["source_name"]),
                url=str(row["url"]),
                normalized_url=str(row["normalized_url"]),
                title=str(row["title"]),
                normalized_title=str(row["normalized_title"]),
                summary=row["summary"],
                published_at=row["published_at"],
                discovered_at=str(row["discovered_at"]),
                raw_payload=row["raw_payload"],
                source_categories=categories,
                source_priority=priority,
            )
        )
    snapshot = canonicalize_event(
        ExistingEventMetadata(
            id=event_id,
            canonical_title=str(event_row["canonical_title"]),
            summary=event_row["summary"],
            categories=existing_categories,
            first_seen_at=str(event_row["first_seen_at"]),
            last_seen_at=str(event_row["last_seen_at"]),
            canonical_article_id=event_row["canonical_article_id"],
        ),
        articles,
    )
    normalized_title = next(
        article.normalized_title
        for article in snapshot.articles
        if article.id == snapshot.canonical_article_id
    )
    desired = (
        snapshot.canonical_title,
        normalized_title,
        snapshot.canonical_summary,
        snapshot.categories[0] if snapshot.categories else None,
        snapshot.first_publication_at,
        snapshot.last_publication_at,
        snapshot.article_count,
        snapshot.source_count,
        snapshot.canonical_article_id,
        snapshot.canonical_selection_reason,
    )
    current = (
        event_row["canonical_title"],
        event_row["normalized_title"],
        event_row["summary"],
        event_row["category"],
        event_row["first_published_at"],
        event_row["last_published_at"],
        event_row["article_count"],
        event_row["source_count"],
        event_row["canonical_article_id"],
        event_row["canonical_selection_reason"],
    )
    if desired != current:
        connection.execute(
            """UPDATE events SET canonical_title = ?, normalized_title = ?,
               summary = ?, category = ?,
               first_published_at = ?, last_published_at = ?, article_count = ?,
               source_count = ?, canonical_article_id = ?,
               canonical_selection_reason = ?, updated_at = ? WHERE id = ?""",
            (*desired, utc_now(), event_id),
        )
    if existing_categories != snapshot.categories:
        connection.execute(
            "DELETE FROM event_categories WHERE event_id = ?", (event_id,)
        )
        connection.executemany(
            "INSERT INTO event_categories (event_id, category, position) VALUES (?, ?, ?)",
            [
                (event_id, category, position)
                for position, category in enumerate(snapshot.categories)
            ],
        )
    return snapshot


def _decode_categories(value: str | None) -> tuple[str, ...]:
    try:
        decoded = json.loads(value or "[]")
    except TypeError, ValueError:
        return ()
    return tuple(str(item) for item in decoded) if isinstance(decoded, list) else ()


def load_event_snapshot(
    connection: sqlite3.Connection,
    event_id: int,
    source_metadata: dict[str, tuple[tuple[str, ...], int]] | None = None,
) -> EventSnapshot:
    """Load one complete pipeline-ready event without modifying storage."""

    event = connection.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if event is None:
        raise ValueError(f"Event {event_id} does not exist")
    canonical_article_id = event["canonical_article_id"]
    reason = event["canonical_selection_reason"]
    if canonical_article_id is None or not reason:
        raise ValueError(f"Event {event_id} has incomplete canonical metadata")
    categories = tuple(
        str(row["category"])
        for row in connection.execute(
            "SELECT category FROM event_categories WHERE event_id = ? ORDER BY position",
            (event_id,),
        )
    )
    metadata = source_metadata or {}
    articles: list[ArticleProvenance] = []
    for row in connection.execute(
        """SELECT a.*, s.name AS source_name, s.categories, s.priority
           FROM articles AS a JOIN sources AS s ON s.id = a.source_id
           WHERE a.event_id = ? ORDER BY a.id""",
        (event_id,),
    ):
        source_id = str(row["source_id"])
        source_categories, priority = metadata.get(
            source_id,
            (_decode_categories(row["categories"]), int(row["priority"])),
        )
        articles.append(
            ArticleProvenance(
                id=int(row["id"]),
                event_id=event_id,
                source_id=source_id,
                source_name=str(row["source_name"]),
                url=str(row["url"]),
                normalized_url=str(row["normalized_url"]),
                title=str(row["title"]),
                normalized_title=str(row["normalized_title"]),
                summary=row["summary"],
                published_at=row["published_at"],
                discovered_at=str(row["discovered_at"]),
                raw_payload=row["raw_payload"],
                source_categories=source_categories,
                source_priority=priority,
            )
        )
    by_source: dict[tuple[str, str], list[int]] = {}
    for article in articles:
        by_source.setdefault((article.source_id, article.source_name), []).append(
            article.id
        )
    from pastila_scout.models import SourceProvenance

    return EventSnapshot(
        id=event_id,
        canonical_title=str(event["canonical_title"]),
        canonical_summary=event["summary"],
        categories=categories,
        first_publication_at=event["first_published_at"],
        last_publication_at=event["last_published_at"],
        first_seen_at=str(event["first_seen_at"]),
        last_seen_at=str(event["last_seen_at"]),
        article_count=int(event["article_count"]),
        source_count=int(event["source_count"]),
        sources=tuple(
            SourceProvenance(id=key[0], name=key[1], article_ids=tuple(ids))
            for key, ids in sorted(by_source.items())
        ),
        articles=tuple(articles),
        canonical_article_id=int(canonical_article_id),
        canonical_selection_reason=str(reason),
    )


def update_event_counts(
    connection: sqlite3.Connection, event_id: int, *, seen_at: str | None = None
) -> None:
    """Recalculate article and distinct-source counts for an event."""

    cursor = connection.execute(
        """
        UPDATE events
        SET article_count = (SELECT COUNT(*) FROM articles WHERE event_id = ?),
            source_count = (
                SELECT COUNT(DISTINCT source_id) FROM articles WHERE event_id = ?
            ),
            last_seen_at = MAX(last_seen_at, ?), updated_at = ?
        WHERE id = ?
        """,
        (event_id, event_id, seen_at or utc_now(), utc_now(), event_id),
    )
    if cursor.rowcount != 1:
        raise ValueError(f"Event {event_id} does not exist")


def get_event_articles(
    connection: sqlite3.Connection, event_id: int
) -> list[sqlite3.Row]:
    """Return every article attached to an event."""

    return list(
        connection.execute(
            "SELECT * FROM articles WHERE event_id = ? ORDER BY id ASC", (event_id,)
        ).fetchall()
    )


def get_event_sources(
    connection: sqlite3.Connection, event_id: int
) -> list[sqlite3.Row]:
    """Return distinct confirming source IDs and names for an event."""

    return list(
        connection.execute(
            """SELECT DISTINCT s.id, s.name FROM articles AS a
               JOIN sources AS s ON s.id = a.source_id
               WHERE a.event_id = ? ORDER BY s.name COLLATE NOCASE, s.id""",
            (event_id,),
        ).fetchall()
    )


def list_recent_events(
    connection: sqlite3.Connection,
    *,
    cutoff: str,
    limit: int = 20,
    min_sources: int = 1,
    category: str | None = None,
) -> list[sqlite3.Row]:
    """List recent events ordered by confidence and recency."""

    if limit <= 0 or min_sources <= 0:
        raise ValueError("Event limit and minimum sources must be positive")
    has_category_table = connection.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type = 'table' AND name = 'event_categories'"""
    ).fetchone()
    category_clause = ""
    parameters: tuple[object, ...] = (cutoff, min_sources)
    if category is not None:
        if has_category_table:
            category_clause = (
                "AND (category = ? OR EXISTS (SELECT 1 FROM event_categories AS ec "
                "WHERE ec.event_id = events.id AND ec.category = ?))"
            )
            parameters += (category, category)
        else:
            category_clause = "AND category = ?"
            parameters += (category,)
    parameters += (limit,)
    return list(
        connection.execute(
            f"""SELECT * FROM events
                WHERE last_seen_at >= ? AND source_count >= ? {category_clause}
                ORDER BY source_count DESC, article_count DESC,
                         last_seen_at DESC, id ASC LIMIT ?""",
            parameters,
        ).fetchall()
    )


def list_event_ids_for_ranking(
    connection: sqlite3.Connection,
    *,
    cutoff: str,
    category: str | None = None,
) -> tuple[int, ...]:
    """Return eligible event IDs without mutating or imposing a score order."""

    parameters: list[object] = [cutoff]
    category_clause = ""
    if category is not None:
        category_clause = (
            "AND (e.category = ? OR EXISTS (SELECT 1 FROM event_categories ec "
            "WHERE ec.event_id = e.id AND ec.category = ?))"
        )
        parameters.extend((category, category))
    return tuple(
        int(row["id"])
        for row in connection.execute(
            f"""SELECT e.id FROM events e
                WHERE COALESCE(e.last_published_at, e.last_seen_at) >= ?
                {category_clause}
                ORDER BY e.id""",
            tuple(parameters),
        )
    )


def _set_article_event(
    connection: sqlite3.Connection, article_id: int, event_id: int
) -> None:
    """Assign an article once, rejecting missing or already assigned rows."""

    cursor = connection.execute(
        "UPDATE articles SET event_id = ? WHERE id = ? AND event_id IS NULL",
        (event_id, article_id),
    )
    if cursor.rowcount != 1:
        raise ValueError(f"Article {article_id} does not exist or already has an event")


def _backfill_article_events(connection: sqlite3.Connection) -> None:
    """Create one conservative event for every legacy unassigned article."""

    rows = connection.execute(
        """SELECT id, title, normalized_title, summary, discovered_at
           FROM articles WHERE event_id IS NULL ORDER BY id"""
    ).fetchall()
    for row in rows:
        create_event(
            connection,
            article_id=int(row["id"]),
            canonical_title=str(row["title"]),
            normalized_title=str(row["normalized_title"]),
            summary=row["summary"],
            seen_at=str(row["discovered_at"]),
        )


def upsert_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    name: str,
    source_type: str,
    url: str,
    enabled: bool,
    categories: tuple[str, ...] = (),
    priority: int = 1,
) -> None:
    """Insert a source or update its mutable fields while preserving creation time."""

    timestamp = utc_now()
    connection.execute(
        """
        INSERT INTO sources (
            id, name, type, url, enabled, created_at, updated_at, categories, priority
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            url = excluded.url,
            enabled = excluded.enabled,
            categories = excluded.categories,
            priority = excluded.priority,
            updated_at = excluded.updated_at
        """,
        (
            source_id,
            name,
            source_type,
            url,
            int(enabled),
            timestamp,
            timestamp,
            json.dumps(categories, ensure_ascii=False),
            priority,
        ),
    )
    connection.commit()


def normalized_url_exists(connection: sqlite3.Connection, normalized_url: str) -> bool:
    """Return whether an article with the normalized URL is already stored."""

    row = connection.execute(
        "SELECT 1 FROM articles WHERE normalized_url = ? LIMIT 1",
        (normalized_url,),
    ).fetchone()
    return row is not None


def insert_article(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    url: str,
    normalized_url: str,
    title: str,
    normalized_title: str,
    summary: str | None = None,
    published_at: str | None = None,
    raw_payload: str | None = None,
) -> int | None:
    """Insert an article, returning its ID or ``None`` for a duplicate URL."""

    timestamp = utc_now()
    with connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO articles (
                source_id,
                url,
                normalized_url,
                title,
                normalized_title,
                summary,
                published_at,
                discovered_at,
                raw_payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                url,
                normalized_url,
                title,
                normalized_title,
                summary,
                published_at,
                timestamp,
                raw_payload,
            ),
        )
        if cursor.rowcount != 1:
            return None
        article_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO editorial_queue (article_id, status, queued_at)
            VALUES (?, 'pending', ?)
            """,
            (article_id, timestamp),
        )
    return article_id


def get_source_counts(connection: sqlite3.Connection) -> tuple[int, int]:
    """Return total and enabled source counts from an initialized database."""

    row = connection.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(enabled), 0) AS enabled FROM sources"
    ).fetchone()
    return int(row["total"]), int(row["enabled"])


def get_article_count(connection: sqlite3.Connection) -> int:
    """Return the number of persisted articles."""

    row = connection.execute("SELECT COUNT(*) AS count FROM articles").fetchone()
    return int(row["count"])


def get_poll_run_count(connection: sqlite3.Connection) -> int:
    """Return the number of recorded polling runs."""

    row = connection.execute("SELECT COUNT(*) AS count FROM poll_runs").fetchone()
    return int(row["count"])


def get_latest_poll_run(connection: sqlite3.Connection) -> sqlite3.Row | None:
    """Return the most recently inserted poll run, if one exists."""

    return connection.execute(
        "SELECT * FROM poll_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()


def get_latest_articles(
    connection: sqlite3.Connection, limit: int = 10
) -> list[sqlite3.Row]:
    """Return the most recently inserted articles in descending ID order."""

    if limit <= 0:
        raise ValueError("Article limit must be a positive integer")
    return list(
        connection.execute(
            """
            SELECT id, source_id, published_at, title, normalized_url, url
            FROM articles
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    )


class QueueStateError(ValueError):
    """Raised when an editorial queue item cannot make a requested transition."""


def get_pending_queue_count(connection: sqlite3.Connection) -> int:
    """Return the number of queue items awaiting review."""

    row = connection.execute(
        "SELECT COUNT(*) AS count FROM editorial_queue WHERE status = 'pending'"
    ).fetchone()
    return int(row["count"])


def get_queue_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return editorial queue counts for every supported status."""

    counts = {status: 0 for status in ("pending", "claimed", "reviewed", "rejected")}
    rows = connection.execute(
        "SELECT status, COUNT(*) AS count FROM editorial_queue GROUP BY status"
    ).fetchall()
    for row in rows:
        counts[str(row["status"])] = int(row["count"])
    return counts


def list_queue_items(
    connection: sqlite3.Connection,
    *,
    status: str = "pending",
    limit: int = 20,
) -> list[sqlite3.Row]:
    """List queue items in deterministic editorial order."""

    allowed_statuses = {"pending", "claimed", "reviewed", "rejected", "all"}
    if status not in allowed_statuses:
        raise ValueError(f"Unsupported queue status: {status!r}")
    if limit <= 0:
        raise ValueError("Queue limit must be a positive integer")

    where_clause = "" if status == "all" else "WHERE q.status = ?"
    parameters: tuple[object, ...]
    if status == "all":
        parameters = (limit,)
    else:
        parameters = (status, limit)
    return list(
        connection.execute(
            f"""
            SELECT q.id AS queue_id, q.article_id, a.source_id, a.title,
                   a.normalized_url, a.url, a.published_at, a.discovered_at,
                   q.priority, q.status, q.queued_at, q.claimed_at,
                   q.reviewed_at, q.reviewer, q.decision, q.notes
            FROM editorial_queue AS q
            JOIN articles AS a ON a.id = q.article_id
            {where_clause}
            ORDER BY q.priority DESC,
                     a.published_at IS NULL ASC,
                     a.published_at DESC,
                     a.discovered_at DESC,
                     q.id ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    )


def claim_queue_item(
    connection: sqlite3.Connection, queue_id: int, reviewer: str
) -> None:
    """Atomically claim a pending queue item for a reviewer."""

    with connection:
        cursor = connection.execute(
            """
            UPDATE editorial_queue
            SET status = 'claimed', claimed_at = ?, reviewer = ?
            WHERE id = ? AND status = 'pending'
            """,
            (utc_now(), reviewer, queue_id),
        )
        if cursor.rowcount != 1:
            _raise_queue_transition_error(connection, queue_id, "claim")


def review_queue_item(
    connection: sqlite3.Connection,
    queue_id: int,
    decision: str,
    *,
    reviewer: str | None = None,
    notes: str | None = None,
) -> None:
    """Record an editorial decision for a pending or claimed queue item."""

    if decision not in {"keep", "reject", "backup"}:
        raise ValueError(f"Unsupported review decision: {decision!r}")
    status = "rejected" if decision == "reject" else "reviewed"
    with connection:
        cursor = connection.execute(
            """
            UPDATE editorial_queue
            SET status = ?, decision = ?, notes = ?, reviewed_at = ?,
                reviewer = COALESCE(?, reviewer)
            WHERE id = ? AND status IN ('pending', 'claimed')
            """,
            (status, decision, notes, utc_now(), reviewer, queue_id),
        )
        if cursor.rowcount != 1:
            _raise_queue_transition_error(connection, queue_id, "review")


def backfill_editorial_queue(connection: sqlite3.Connection) -> int:
    """Queue all articles that do not already have an editorial item."""

    with connection:
        cursor = connection.execute(
            """
            INSERT INTO editorial_queue (article_id, status, queued_at)
            SELECT a.id, 'pending', ?
            FROM articles AS a
            LEFT JOIN editorial_queue AS q ON q.article_id = a.id
            WHERE q.id IS NULL
            """,
            (utc_now(),),
        )
    return cursor.rowcount


def _raise_queue_transition_error(
    connection: sqlite3.Connection, queue_id: int, action: str
) -> None:
    """Raise a precise missing-item or invalid-state transition error."""

    row = connection.execute(
        "SELECT status FROM editorial_queue WHERE id = ?", (queue_id,)
    ).fetchone()
    if row is None:
        raise QueueStateError(f"Editorial queue item {queue_id} does not exist")
    raise QueueStateError(
        f"Cannot {action} editorial queue item {queue_id} from status {row['status']!r}"
    )
