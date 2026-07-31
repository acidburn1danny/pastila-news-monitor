from pathlib import Path
from typing import Self

import pytest

from pastila_scout.cli import _select_poll_days, build_parser, main
from pastila_scout.database import (
    initialize_database,
    insert_article,
    open_database,
    upsert_source,
)
from pastila_scout.models import ArticleCandidate
from pastila_scout.poller import PollResult


def test_cli_success_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "pastila_scout.cli.poll_once",
        lambda config, database, timeout, **kwargs: PollResult(
            1,
            "partial",
            2,
            3,
            1,
            "bad: offline",
            sources_succeeded=1,
            sources_failed=1,
            duplicates_skipped=2,
            source_failures=("bad: offline",),
        ),
    )

    exit_code = main(
        [
            "poll-once",
            "--config",
            "custom.yaml",
            "--database",
            "custom.db",
            "--timeout",
            "5",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr()
    assert "Poll status: partial" in output.out
    assert "Sources: 2 checked, 1 succeeded, 1 failed" in output.out
    assert "Articles: 3 found, 1 inserted, 2 duplicates" in output.out
    assert "Filtered: 0 old, 0 future, 0 undated, 0 over limit" in output.out
    assert "Source failure: bad: offline" in output.out
    assert output.err == ""


def test_cli_full_success_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pastila_scout.cli.poll_once",
        lambda config, database, timeout, **kwargs: PollResult(
            1,
            "success",
            1,
            1,
            1,
            None,
            sources_succeeded=1,
        ),
    )

    assert main(["poll-once"]) == 0


def test_cli_failure_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "pastila_scout.cli.poll_once",
        lambda config, database, timeout, **kwargs: PollResult(
            1,
            "failed",
            1,
            0,
            0,
            "bad: offline",
            sources_failed=1,
            source_failures=("bad: offline",),
        ),
    )

    exit_code = main(["poll-once"])

    assert exit_code != 0
    assert "Poll status: failed" in capsys.readouterr().out


def test_cli_help_is_not_rss_specific() -> None:
    help_text = build_parser().format_help()

    assert "poll enabled sources once" in help_text
    assert "RSS feeds" not in help_text
    assert "validate-config" in help_text
    assert "status" in help_text
    assert "queue" in help_text
    assert "review" in help_text
    assert "queue-backfill" in help_text
    assert "audit-events" in help_text
    assert "plan-event-reconciliation" in help_text
    assert "apply-event-reconciliation" in help_text
    assert "canonicalize-events" in help_text


class FakeValidationClient:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeValidationAdapter:
    def __init__(self, failure_id: str | None = None) -> None:
        self.failure_id = failure_id

    def fetch(self, source: object, client: object) -> list[ArticleCandidate]:
        source_id = source.id
        if source_id == self.failure_id:
            raise RuntimeError("unreachable")
        return [
            ArticleCandidate(
                source_id=source_id,
                url=f"https://example.com/{source_id}",
                title="article",
                summary=None,
                published_at=None,
                raw_payload=None,
            )
        ]


def validation_config(path: Path, second: bool = False) -> Path:
    extra = (
        """
  - id: second
    name: Second
    type: rss
    url: https://example.com/second
    enabled: true
    categories: [Social]
"""
        if second
        else ""
    )
    path.write_text(
        """sources:
  - id: first
    name: First
    type: rss
    url: https://example.com/first
    enabled: true
    categories: [Politica, Social]
"""
        + extra,
        encoding="utf-8",
    )
    return path


def test_validate_config_success_without_database_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = validation_config(tmp_path / "sources.yaml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pastila_scout.cli.HTTPClient", FakeValidationClient)
    monkeypatch.setattr(
        "pastila_scout.cli.get_adapter", lambda source_type: FakeValidationAdapter()
    )

    exit_code = main(["validate-config", "--config", str(config)])

    assert exit_code == 0
    assert "Source first: ok" in capsys.readouterr().out
    assert not (tmp_path / "data" / "news_monitor.db").exists()


def test_validate_config_isolates_source_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = validation_config(tmp_path / "sources.yaml", second=True)
    monkeypatch.setattr("pastila_scout.cli.HTTPClient", FakeValidationClient)
    monkeypatch.setattr(
        "pastila_scout.cli.get_adapter",
        lambda source_type: FakeValidationAdapter(failure_id="second"),
    )

    exit_code = main(["validate-config", "--config", str(config)])

    output = capsys.readouterr().out
    assert exit_code != 0
    assert "Source first: ok" in output
    assert "Source second: failed (unreachable)" in output
    assert "1 succeeded, 1 failed" in output


def test_validate_config_reports_configuration_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("sources: invalid", encoding="utf-8")

    exit_code = main(["validate-config", "--config", str(invalid)])

    assert exit_code != 0
    assert "Configuration error:" in capsys.readouterr().out


def test_status_handles_missing_and_initialized_empty_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing.db"
    assert main(["status", "--database", str(missing)]) == 0
    assert "Database not found" in capsys.readouterr().out

    empty = tmp_path / "empty.db"
    with open_database(empty) as connection:
        initialize_database(connection)

    assert main(["status", "--database", str(empty)]) == 0
    output = capsys.readouterr().out
    assert "Sources: 0 total, 0 enabled" in output
    assert "Articles: 0" in output
    assert "Latest poll run: none" in output
    assert "Editorial queue: 0 total, 0 pending" in output


def test_status_displays_counts_latest_run_and_article_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "status.db"
    with open_database(database) as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="news",
            name="News",
            source_type="rss",
            url="https://example.com/feed",
            enabled=True,
        )
        connection.execute(
            "INSERT INTO poll_runs (started_at, finished_at, status) VALUES (?, ?, ?)",
            ("2025-01-01T00:00:00+00:00", "2025-01-01T00:01:00+00:00", "success"),
        )
        connection.commit()
        for number in range(3):
            insert_article(
                connection,
                source_id="news",
                url=f"https://example.com/{number}",
                normalized_url=f"https://example.com/{number}",
                title=f"Article {number}",
                normalized_title=f"article {number}",
            )

    assert main(["status", "--database", str(database), "--limit", "2"]) == 0
    output = capsys.readouterr().out
    assert "Sources: 1 total, 1 enabled" in output
    assert "Articles: 3" in output
    assert "Poll runs: 1" in output
    assert "Editorial queue: 3 total, 3 pending" in output
    assert "Latest poll run: success at 2025-01-01T00:01:00+00:00" in output
    assert output.index("Article 2") < output.index("Article 1")
    assert "Article 0" not in output


def test_status_rejects_nonpositive_limit() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["status", "--limit", "0"])

    assert exc_info.value.code != 0


def queue_database(path: Path) -> tuple[Path, int]:
    with open_database(path) as connection:
        initialize_database(connection)
        upsert_source(
            connection,
            source_id="news",
            name="News",
            source_type="rss",
            url="https://example.com/feed",
            enabled=True,
        )
        article_id = insert_article(
            connection,
            source_id="news",
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            title="Queue Article",
            normalized_title="queue article",
            published_at="2025-01-01T00:00:00+00:00",
        )
        assert article_id is not None
        queue_id = connection.execute(
            "SELECT id FROM editorial_queue WHERE article_id = ?", (article_id,)
        ).fetchone()[0]
    return path, queue_id


def test_queue_cli_prints_counts_and_items(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database, queue_id = queue_database(tmp_path / "queue.db")

    exit_code = main(["queue", "--database", str(database), "--status", "all"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Queue counts: 1 pending, 0 claimed, 0 reviewed, 0 rejected" in output
    assert f"#{queue_id}" in output
    assert "Queue Article" in output


def test_review_cli_success_and_invalid_transition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database, queue_id = queue_database(tmp_path / "review.db")

    exit_code = main(
        [
            "review",
            str(queue_id),
            "--database",
            str(database),
            "--decision",
            "keep",
            "--reviewer",
            "ana",
            "--notes",
            "use this",
        ]
    )

    assert exit_code == 0
    assert "decision keep recorded" in capsys.readouterr().out
    with open_database(database) as connection:
        item = connection.execute(
            "SELECT * FROM editorial_queue WHERE id = ?", (queue_id,)
        ).fetchone()
        assert item["status"] == "reviewed"
        assert item["reviewer"] == "ana"

    assert (
        main(
            [
                "review",
                str(queue_id),
                "--database",
                str(database),
                "--decision",
                "reject",
            ]
        )
        != 0
    )
    assert "Review error:" in capsys.readouterr().out


def test_queue_backfill_cli_is_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database, _ = queue_database(tmp_path / "backfill.db")
    with open_database(database) as connection:
        connection.execute("DELETE FROM editorial_queue")
        connection.commit()

    assert main(["queue-backfill", "--database", str(database)]) == 0
    assert "rows created: 1" in capsys.readouterr().out
    assert main(["queue-backfill", "--database", str(database)]) == 0
    assert "rows created: 0" in capsys.readouterr().out


def test_review_cli_rejects_missing_queue_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "empty.db"
    with open_database(database) as connection:
        initialize_database(connection)

    exit_code = main(
        [
            "review",
            "999",
            "--database",
            str(database),
            "--decision",
            "backup",
        ]
    )

    assert exit_code != 0
    assert "does not exist" in capsys.readouterr().out


class TTYInput:
    def isatty(self) -> bool:
        return True


class NonTTYInput:
    def isatty(self) -> bool:
        return False

    def read(self, *args: object) -> str:
        raise AssertionError("non-interactive stdin must not be read")


@pytest.mark.parametrize("days", [1, 3, 7, 14, 30])
def test_poll_once_accepts_supported_days_and_passes_hours(
    days: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict[str, object] = {}

    def fake_poll(
        config: Path, database: Path, timeout: float, **kwargs: object
    ) -> PollResult:
        received.update(kwargs)
        return PollResult(1, "success", 0, 0, 0, None)

    monkeypatch.setattr("pastila_scout.cli.poll_once", fake_poll)
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (_ for _ in ()).throw(AssertionError("must not prompt")),
    )

    assert main(["poll-once", "--days", str(days)]) == 0
    assert received["max_article_age_hours_override"] == float(days * 24)


@pytest.mark.parametrize("value", ["0", "5", "31", "invalid"])
def test_poll_once_rejects_unsupported_days(value: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["poll-once", "--days", value])

    assert exc_info.value.code != 0


@pytest.mark.parametrize(
    ("selection", "days"),
    [("", 7), ("1", 1), ("2", 3), ("3", 7), ("4", 14), ("5", 30)],
)
def test_interactive_poll_period_mapping(
    selection: str,
    days: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("pastila_scout.cli.sys.stdin", TTYInput())
    monkeypatch.setattr("builtins.input", lambda prompt: selection)

    assert _select_poll_days(None) == days
    assert "Select maximum article age:" in capsys.readouterr().out


def test_invalid_interactive_selection_prompts_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    responses = iter(["9", "2"])
    monkeypatch.setattr("pastila_scout.cli.sys.stdin", TTYInput())
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert _select_poll_days(None) == 3
    output = capsys.readouterr().out
    assert output.count("Select maximum article age:") == 2
    assert "Invalid selection" in output


def test_invalid_text_then_enter_selects_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["seven", ""])
    monkeypatch.setattr("pastila_scout.cli.sys.stdin", TTYInput())
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert _select_poll_days(None) == 7


def test_non_tty_default_never_reads_or_prompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pastila_scout.cli.sys.stdin", NonTTYInput())
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (_ for _ in ()).throw(AssertionError("must not prompt")),
    )

    assert _select_poll_days(None) == 7


def test_non_tty_poll_uses_seven_day_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    monkeypatch.setattr("pastila_scout.cli.sys.stdin", NonTTYInput())
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (_ for _ in ()).throw(AssertionError("must not prompt")),
    )

    def fake_poll(
        config: Path, database: Path, timeout: float, **kwargs: object
    ) -> PollResult:
        received.update(kwargs)
        return PollResult(1, "success", 0, 0, 0, None)

    monkeypatch.setattr("pastila_scout.cli.poll_once", fake_poll)

    assert main(["poll-once"]) == 0
    assert received["max_article_age_hours_override"] == 168.0


def test_poll_help_documents_day_choices(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["poll-once", "--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "--days {1,3,7,14,30}" in help_text
    assert "maximum article age" in help_text
    assert "--category" in help_text
    assert "Politica" in help_text
    assert "Conspiratii" in help_text


@pytest.mark.parametrize(
    "category",
    [
        "all",
        "Politica",
        "Social",
        "Conspiratii",
        "Economie",
        "CanCan",
        "Externe",
        "Diverse",
    ],
)
def test_poll_category_choices_work_with_days(
    category: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict[str, object] = {}

    def fake_poll(
        config: Path, database: Path, timeout: float, **kwargs: object
    ) -> PollResult:
        received.update(kwargs)
        return PollResult(1, "success", 0, 0, 0, None, category=category)

    monkeypatch.setattr("pastila_scout.cli.poll_once", fake_poll)

    assert main(["poll-once", "--days", "14", "--category", category]) == 0
    assert received["category"] == category
    assert received["max_article_age_hours_override"] == 336.0


def test_invalid_poll_category_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["poll-once", "--category", "politica"])

    assert exc_info.value.code != 0


def test_validate_config_filters_by_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = validation_config(tmp_path / "sources.yaml", second=True)
    monkeypatch.setattr("pastila_scout.cli.HTTPClient", FakeValidationClient)
    monkeypatch.setattr(
        "pastila_scout.cli.get_adapter",
        lambda source_type: FakeValidationAdapter(failure_id="second"),
    )

    exit_code = main(
        ["validate-config", "--config", str(config), "--category", "Politica"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Category: Politica" in output
    assert "Configured sources: 2" in output
    assert "Enabled sources: 2" in output
    assert "Selected sources: 1" in output
    assert "Source first: ok" in output
    assert "Source second" not in output


def test_validate_config_reports_disabled_matching_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text(
        """sources:
  - id: enabled-world
    name: Enabled World
    type: rss
    url: https://example.com/world.xml
    enabled: true
    categories: [Externe]
  - id: disabled-world
    name: Disabled World
    type: rss
    url: https://example.com/disabled.xml
    enabled: false
    disabled_reason: Endpoint requires authentication.
    categories: [Externe]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("pastila_scout.cli.HTTPClient", FakeValidationClient)
    monkeypatch.setattr(
        "pastila_scout.cli.get_adapter", lambda source_type: FakeValidationAdapter()
    )

    exit_code = main(
        ["validate-config", "--config", str(config), "--category", "Externe"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Source enabled-world: ok" in output
    assert (
        "Source disabled-world: disabled (Endpoint requires authentication.)" in output
    )
    assert "1 succeeded, 0 failed, 1 disabled" in output
