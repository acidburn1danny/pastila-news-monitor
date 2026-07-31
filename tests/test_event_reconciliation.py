import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from pastila_scout.cli import main
from pastila_scout.core.event_reconciliation import build_reconciliation_plan
from pastila_scout.database import (
    StaleReconciliationPlanError,
    apply_reconciliation_plan,
    create_event,
    initialize_database,
    insert_article,
    load_reconciliation_snapshot,
    open_database,
    open_database_readonly,
    upsert_source,
)
from pastila_scout.models import (
    ReconciliationArticle,
    ReconciliationEvent,
    ReconciliationSnapshot,
)

NOW = "2026-07-26T12:00:00+00:00"


def _event(event_id: int, title: str) -> ReconciliationEvent:
    return ReconciliationEvent(
        id=event_id,
        canonical_title=title,
        normalized_title=title.lower(),
        summary=None,
        first_seen_at=NOW,
        last_seen_at=NOW,
        article_count=1,
        source_count=1,
        created_at=NOW,
        updated_at=NOW,
    )


def _article(
    article_id: int,
    event_id: int,
    source_id: str,
    title: str,
    *,
    categories: tuple[str, ...] = ("Social",),
    priority: int = 1,
    summary: str | None = None,
    published_at: str | None = NOW,
) -> ReconciliationArticle:
    return ReconciliationArticle(
        id=article_id,
        event_id=event_id,
        source_id=source_id,
        source_name=f"Sursă {source_id}",
        title=title,
        normalized_title=title.lower(),
        summary=summary,
        published_at=published_at,
        discovered_at=NOW,
        raw_payload=None,
        source_categories=categories,
        source_priority=priority,
    )


def test_clean_plan_builds_coherent_multi_event_group_and_metadata() -> None:
    events = (
        _event(1, "Railway theft at Sadu"),
        _event(2, "Sadu railway theft"),
        _event(3, "Railway stolen from Sadu"),
    )
    articles = (
        _article(
            1, 1, "one", "Railway theft at Sadu", categories=("Social", "Politica")
        ),
        _article(
            2,
            2,
            "two",
            "Sadu railway theft",
            categories=("Social", "Economie"),
            priority=2,
            summary="Rezumat complet",
        ),
        _article(3, 3, "three", "Railway stolen from Sadu"),
    )

    plan = build_reconciliation_plan(
        ReconciliationSnapshot(events=events, articles=articles),
        database_path="news.db",
        generated_at=datetime.fromisoformat(NOW),
    )

    assert len(plan.proposals) == 1
    proposal = plan.proposals[0]
    assert proposal.event_ids == (1, 2, 3)
    assert len(proposal.pairwise_similarities) == 3
    assert all(pair.score >= 0.72 for pair in proposal.pairwise_similarities)
    assert proposal.proposed_categories == ("Social", "Politica", "Economie")
    assert proposal.surviving_event_id == 2
    assert proposal.canonical_selection.article_id == 2
    assert "priority-2 source=True" in proposal.canonical_selection.reason
    assert proposal.resulting_article_count == 3
    assert proposal.resulting_source_count == 3


def test_unsafe_transitive_component_is_ambiguous_and_not_proposed() -> None:
    events = (
        _event(1, "alpha beta"),
        _event(2, "alpha beta gamma delta"),
        _event(3, "gamma delta"),
    )
    articles = tuple(
        _article(index, index, str(index), event.canonical_title)
        for index, event in enumerate(events, 1)
    )

    plan = build_reconciliation_plan(
        ReconciliationSnapshot(events=events, articles=articles),
        database_path="news.db",
    )

    assert not plan.proposals
    assert len(plan.ambiguous_groups) == 1
    assert plan.ambiguous_groups[0].event_ids == (1, 2, 3)
    assert {
        (pair.event_id, pair.related_event_id)
        for pair in plan.ambiguous_groups[0].rejected_pairs
    } == {(1, 3)}


def test_canonical_selection_prefers_completeness_then_earliest_publication() -> None:
    events = (_event(1, "Same event title"), _event(2, "Same event title"))
    articles = (
        _article(
            1,
            1,
            "one",
            "Same event title",
            summary="short",
            published_at="2026-07-26T08:00:00+00:00",
        ),
        _article(
            2,
            2,
            "two",
            "Same event title",
            summary="a substantially more complete summary",
            published_at="2026-07-26T09:00:00+00:00",
        ),
    )
    complete_plan = build_reconciliation_plan(
        ReconciliationSnapshot(events=events, articles=articles),
        database_path="news.db",
    )
    assert complete_plan.proposals[0].canonical_selection.article_id == 2

    equal_articles = (
        articles[0].model_copy(
            update={"summary": "equal", "published_at": "2026-07-26T08:00:00+00:00"}
        ),
        articles[1].model_copy(
            update={"summary": "equal", "published_at": "2026-07-26T09:00:00+00:00"}
        ),
    )
    earliest_plan = build_reconciliation_plan(
        ReconciliationSnapshot(events=events, articles=equal_articles),
        database_path="news.db",
    )
    assert earliest_plan.proposals[0].canonical_selection.article_id == 1


def _database_with_matching_events(path: Path) -> tuple[int, int, int, int]:
    with open_database(path) as connection:
        initialize_database(connection)
        for source_id, name in (("one", "Știri Unu"), ("two", "Știri Doi")):
            upsert_source(
                connection,
                source_id=source_id,
                name=name,
                source_type="rss",
                url=f"https://example.com/{source_id}",
                enabled=True,
            )
        first_article = insert_article(
            connection,
            source_id="one",
            url="https://example.com/one",
            normalized_url="https://example.com/one",
            title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            summary="Primul rezumat",
            published_at="2026-07-26T08:00:00+00:00",
        )
        second_article = insert_article(
            connection,
            source_id="two",
            url="https://example.com/two",
            normalized_url="https://example.com/two",
            title="Sadu railway theft",
            normalized_title="sadu railway theft",
            summary="Al doilea rezumat mai complet",
            published_at="2026-07-26T09:00:00+00:00",
        )
        assert first_article and second_article
        first_event = create_event(
            connection,
            article_id=first_article,
            canonical_title="Railway theft at Sadu",
            normalized_title="railway theft at sadu",
            seen_at=NOW,
        )
        second_event = create_event(
            connection,
            article_id=second_article,
            canonical_title="Sadu railway theft",
            normalized_title="sadu railway theft",
            seen_at=NOW,
        )
    return first_article, second_article, first_event, second_event


def _database_plan(path: Path):
    with open_database_readonly(path) as connection:
        snapshot = load_reconciliation_snapshot(
            connection,
            {
                "one": (("Social", "Politica"), 1),
                "two": (("Social", "Economie"), 2),
            },
        )
    return build_reconciliation_plan(snapshot, database_path=str(path.resolve()))


def test_plan_generation_and_cli_are_read_only_and_utf8(tmp_path: Path) -> None:
    database = tmp_path / "știri.db"
    _database_with_matching_events(database)
    config = tmp_path / "sources.yaml"
    config.write_text(
        """sources:
  - id: one
    name: Știri Unu
    type: rss
    url: https://example.com/one
    enabled: true
    categories: [Social, Politica]
  - id: two
    name: Știri Doi
    type: rss
    url: https://example.com/two
    enabled: true
    categories: [Social, Economie]
    priority: 2
""",
        encoding="utf-8",
    )
    before = database.read_bytes()
    output = tmp_path / "planuri"

    assert (
        main(
            [
                "plan-event-reconciliation",
                "--database",
                str(database),
                "--config",
                str(config),
                "--details",
                "--limit",
                "1",
                "--output-directory",
                str(output),
            ]
        )
        == 0
    )

    assert database.read_bytes() == before
    json_path = next(output.glob("*.json"))
    text_path = next(output.glob("*.txt"))
    assert "Știri Doi" in json_path.read_text(encoding="utf-8")
    assert "Al doilea rezumat" in text_path.read_text(encoding="utf-8")


def test_stale_plan_rejection_and_dry_run(tmp_path: Path) -> None:
    database = tmp_path / "stale.db"
    _database_with_matching_events(database)
    plan = _database_plan(database)
    before = database.read_bytes()
    with open_database(database) as connection:
        survivors, merged = apply_reconciliation_plan(connection, plan, dry_run=True)
    assert (survivors, merged) == ((), ())
    assert database.read_bytes() == before

    with open_database(database) as connection:
        connection.execute("UPDATE articles SET title = 'changed' WHERE id = 1")
        connection.commit()
        with pytest.raises(StaleReconciliationPlanError):
            apply_reconciliation_plan(connection, plan)
    with open_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2


def test_apply_cli_requires_plan_and_writes_dry_run_report(tmp_path: Path) -> None:
    database = tmp_path / "cli-apply.db"
    _database_with_matching_events(database)
    plan = _database_plan(database)
    plan_path = tmp_path / "explicit-plan.json"
    plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    before = database.read_bytes()
    reports = tmp_path / "application-reports"

    assert (
        main(
            [
                "apply-event-reconciliation",
                "--plan",
                str(plan_path),
                "--dry-run",
                "--output-directory",
                str(reports),
            ]
        )
        == 0
    )

    assert database.read_bytes() == before
    report = next(reports.glob("*.json")).read_text(encoding="utf-8")
    assert '"status": "dry-run"' in report
    assert '"proposals_validated": 1' in report


def test_apply_preserves_articles_recalculates_counts_and_categories(
    tmp_path: Path,
) -> None:
    database = tmp_path / "apply.db"
    _, _, first_event, second_event = _database_with_matching_events(database)
    plan = _database_plan(database)

    with open_database(database) as connection:
        survivors, merged = apply_reconciliation_plan(connection, plan)
        assert connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 2
        event = connection.execute("SELECT * FROM events").fetchone()
        assert event["article_count"] == 2
        assert event["source_count"] == 2
        assert event["id"] == second_event
        assert event["canonical_article_id"] == 2
        assert event["canonical_selection_reason"]
        assert event["first_published_at"] == "2026-07-26T08:00:00+00:00"
        assert event["last_published_at"] == "2026-07-26T09:00:00+00:00"
        assert event["category"] == "Social"
        assert survivors == (second_event,)
        assert merged == (first_event,)
        assert [
            row["category"]
            for row in connection.execute(
                "SELECT category FROM event_categories ORDER BY position"
            )
        ] == ["Social", "Politica", "Economie"]
        assert (
            connection.execute("SELECT COUNT(*) FROM editorial_queue").fetchone()[0]
            == 2
        )


def test_application_rolls_back_all_proposals_on_failure(tmp_path: Path) -> None:
    database = tmp_path / "rollback.db"
    _, _, first_event, _ = _database_with_matching_events(database)
    plan = _database_plan(database)
    with open_database(database) as connection:
        connection.execute(
            f"""CREATE TRIGGER reject_event_delete BEFORE DELETE ON events
                WHEN OLD.id = {first_event}
                BEGIN SELECT RAISE(ABORT, 'forced rollback'); END"""
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="forced rollback"):
            apply_reconciliation_plan(connection, plan)
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2
        memberships = connection.execute(
            "SELECT COUNT(DISTINCT event_id) FROM articles"
        ).fetchone()[0]
        assert memberships == 2
        assert (
            connection.execute("SELECT COUNT(*) FROM event_categories").fetchone()[0]
            == 0
        )
