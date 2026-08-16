import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.cli import main
from pastila_scout.core.event_integrity import audit_event_integrity
from pastila_scout.database import (
    create_event,
    initialize_database,
    insert_article,
    load_event_integrity_snapshot,
    open_database,
    open_database_readonly,
    upsert_source,
)
from pastila_scout.models import (
    AuditArticle,
    AuditEvent,
    EventIntegrityFinding,
    EventIntegritySnapshot,
    HistoricalMatchProposal,
    PipelineDiagnostic,
    PipelineStageResult,
)
from pastila_scout.reporting.event_audit import sorted_findings, sorted_proposals

NOW = "2026-07-26T12:00:00+00:00"


def test_pipeline_contracts_are_typed_and_storage_independent() -> None:
    result = PipelineStageResult(
        stage="deduplication",
        status="success",
        started_at=datetime.fromisoformat(NOW),
        processed_count=3,
        diagnostics=(
            PipelineDiagnostic(
                code="events_audited",
                message="Three events audited.",
                severity="info",
            ),
        ),
    )

    assert result.stage == "deduplication"
    assert result.diagnostics[0].code == "events_audited"


def _event(
    event_id: int,
    title: str,
    *,
    article_count: int = 1,
    source_count: int = 1,
    summary: str | None = "Summary",
    category: str | None = "Social",
) -> AuditEvent:
    return AuditEvent(
        id=event_id,
        canonical_title=title,
        summary=summary,
        category=category,
        first_seen_at=NOW,
        last_seen_at=NOW,
        article_count=article_count,
        source_count=source_count,
    )


def test_audit_classifies_every_structural_error_and_warning() -> None:
    snapshot = EventIntegritySnapshot(
        articles=(
            AuditArticle(id=1, event_id=1, source_id="one", title="Railway theft"),
            AuditArticle(id=2, event_id=3, source_id="two", title="Railway stolen"),
            AuditArticle(id=3, event_id=None, source_id="one", title="Unassigned"),
            AuditArticle(id=4, event_id=99, source_id="one", title="Invalid"),
        ),
        events=(
            _event(
                1,
                "2.4 km of railway stolen",
                article_count=2,
                source_count=2,
                summary=None,
                category=None,
            ),
            _event(2, "Empty event", article_count=0, source_count=0),
            _event(3, "Investigation after railway theft"),
        ),
    )

    report = audit_event_integrity(snapshot)

    error_codes = {finding.code for finding in report.errors}
    warning_codes = {finding.code for finding in report.warnings}
    assert error_codes == {
        "invalid_event_reference",
        "event_without_articles",
        "article_count_mismatch",
        "source_count_mismatch",
    }
    assert {
        "unassigned_article",
        "missing_event_category",
        "missing_event_summary",
        "single_article_event",
        "likely_historical_match",
    } <= warning_codes
    assert report.historical_matches[0].event_id == 1
    assert report.historical_matches[0].related_event_id == 3


def test_historical_proposals_respect_matcher_threshold_and_lookback() -> None:
    old = _event(2, "Railway theft reported today").model_copy(
        update={"last_seen_at": "2025-01-01T00:00:00+00:00"}
    )
    snapshot = EventIntegritySnapshot(
        articles=(
            AuditArticle(id=1, event_id=1, source_id="one", title="First"),
            AuditArticle(id=2, event_id=2, source_id="two", title="Second"),
        ),
        events=(_event(1, "Major railway theft reported"), old),
    )

    assert not audit_event_integrity(snapshot).historical_matches
    recent_snapshot = snapshot.model_copy(
        update={
            "events": (
                snapshot.events[0],
                old.model_copy(update={"last_seen_at": NOW}),
            )
        }
    )
    assert audit_event_integrity(recent_snapshot).historical_matches
    assert not audit_event_integrity(
        recent_snapshot, similarity_threshold=1
    ).historical_matches


def _create_warning_only_database(path: Path, article_total: int = 1) -> None:
    with open_database(path) as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="sursa",
            name="Sursă Românească",
            source_type="rss",
            url="https://example.com/feed",
            enabled=True,
        )
        for index in range(article_total):
            suffix = index + 1
            article_id = insert_article(
                connection,
                source_id="sursa",
                url=f"https://example.com/story-{suffix}",
                normalized_url=f"https://example.com/story-{suffix}",
                title=f"Știre românească {suffix}",
                normalized_title=f"știre românească {suffix}",
                published_at=f"2026-07-{20 + suffix:02d}T12:00:00+00:00",
            )
            assert article_id is not None
            create_event(
                connection,
                article_id=article_id,
                canonical_title=f"Știre românească {suffix}",
                normalized_title=f"știre românească {suffix}",
                seen_at=datetime.now(UTC).isoformat(),
            )


def test_snapshot_loading_and_audit_are_strictly_read_only(tmp_path: Path) -> None:
    database = tmp_path / "audit.db"
    _create_warning_only_database(database)
    before = database.read_bytes()

    with open_database_readonly(database) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        snapshot = load_event_integrity_snapshot(connection)
        report = audit_event_integrity(snapshot)
        assert connection.total_changes == 0

    assert not report.errors
    assert database.read_bytes() == before


def test_audit_cli_default_is_compact_and_writes_utf8_report(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    database = tmp_path / "unicode.db"
    _create_warning_only_database(database)
    before = database.read_bytes()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["audit-events", "--database", str(database)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Database: {database}" in output
    assert "Articles checked: 1" in output
    assert "Events checked: 1" in output
    assert "Structural errors: 0" in output
    assert "warning/single_article_event: 1" in output
    assert "Historical match proposals: 0" in output
    assert "Exit code: 0" in output
    assert "Detailed report: reports" in output
    assert "contains one article" not in output
    reports = list((tmp_path / "reports").glob("event_audit_*.txt"))
    assert len(reports) == 1
    report_text = reports[0].read_text(encoding="utf-8")
    assert "Știre românească 1" in report_text
    assert "source_id=sursa" not in report_text
    assert "sources=Sursă Românească (sursa)" in report_text
    assert "published=2026-07-21T12:00:00+00:00" in report_text
    assert database.read_bytes() == before


def test_audit_cli_details_and_limit_affect_console_only(
    tmp_path: Path, capsys
) -> None:
    database = tmp_path / "details.db"
    report_path = tmp_path / "complete.txt"
    _create_warning_only_database(database, article_total=2)

    exit_code = main(
        [
            "audit-events",
            "--database",
            str(database),
            "--details",
            "--limit",
            "1",
            "--output",
            str(report_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "single_article_event (2):" in output
    assert "... 1 more in detailed report" in output
    assert output.count("contains one article") == 1
    report_text = report_path.read_text(encoding="utf-8")
    assert report_text.count("contains one article") == 2
    assert "Detailed report: " + str(report_path) in output


def test_audit_cli_limit_implies_console_details(tmp_path: Path, capsys) -> None:
    database = tmp_path / "limit.db"
    _create_warning_only_database(database, article_total=2)

    main(
        [
            "audit-events",
            "--database",
            str(database),
            "--limit",
            "1",
            "--output",
            str(tmp_path / "limit-report.txt"),
        ]
    )

    assert "... 1 more in detailed report" in capsys.readouterr().out


def test_report_sorting_helpers_are_deterministic() -> None:
    findings = (
        EventIntegrityFinding(severity="warning", code="zeta", message="z", event_id=2),
        EventIntegrityFinding(
            severity="warning", code="alpha", message="two", article_id=3
        ),
        EventIntegrityFinding(
            severity="warning", code="alpha", message="one", article_id=1
        ),
    )
    proposals = (
        HistoricalMatchProposal(event_id=3, related_event_id=4, score=0.9),
        HistoricalMatchProposal(event_id=1, related_event_id=2, score=0.9),
        HistoricalMatchProposal(event_id=5, related_event_id=6, score=0.95),
    )

    assert [finding.message for finding in sorted_findings(findings)] == [
        "one",
        "two",
        "z",
    ]
    assert [proposal.event_id for proposal in sorted_proposals(proposals)] == [5, 1, 3]


def test_audit_cli_structural_errors_exit_nonzero(tmp_path: Path, capsys) -> None:
    database = tmp_path / "broken.db"
    _create_warning_only_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE events SET article_count = 9")

    exit_code = main(
        [
            "audit-events",
            "--database",
            str(database),
            "--output",
            str(tmp_path / "broken-report.txt"),
        ]
    )

    assert exit_code != 0
    assert "article_count_mismatch" in capsys.readouterr().out
