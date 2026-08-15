import copy
import inspect
import json
import pickle
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self

import pytest

from pastila_scout import poller
from pastila_scout.config import SourceConfig
from pastila_scout.database import open_database
from pastila_scout.logging_config import configure_logging
from pastila_scout.models import ArticleCandidate
from pastila_scout.poller import PollResult, poll_once

RSS = b"""<rss version="2.0"><channel>
  <title>News</title><link>https://example.com</link><description>News</description>
  <item><title>  Original   TITLE!!! </title>
  <link>HTTPS://Example.com:443//story/?utm_source=feed&amp;id=1</link>
  <description>Summary</description></item>
</channel></rss>"""

HTML = b"""<main>
  <article><a class="story" href="/html-story">HTML Story</a></article>
</main>"""


class FakeHTTPClient:
    def __init__(self, responses: dict[str, bytes | Exception]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def fetch(self, url: str) -> bytes:
        self.requested.append(url)
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


def write_config(path: Path, sources: str) -> Path:
    content = f"sources:\n{sources}" if sources else "sources: []\n"
    path.write_text(content, encoding="utf-8")
    return path


def install_client(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, bytes | Exception],
) -> FakeHTTPClient:
    client = FakeHTTPClient(responses)
    monkeypatch.setattr("pastila_scout.poller.HTTPClient", lambda timeout: client)
    return client


def rss_source(source_id: str, url: str, enabled: bool = True) -> str:
    return f"""  - id: {source_id}
    name: {source_id}
    type: rss
    url: {url}
    enabled: {str(enabled).lower()}
    categories: [Politica, Social]
"""


def html_source(source_id: str, url: str, enabled: bool = True) -> str:
    return f"""  - id: {source_id}
    name: {source_id}
    type: html
    url: {url}
    enabled: {str(enabled).lower()}
    categories: [Social, CanCan]
    list_selector: article
    link_selector: a.story
"""


def fetch_run(database_path: Path, run_id: int) -> sqlite3.Row:
    with open_database(database_path) as connection:
        return connection.execute(
            "SELECT * FROM poll_runs WHERE id = ?", (run_id,)
        ).fetchone()


class CandidateAdapter:
    def __init__(self, candidates: list[ArticleCandidate]) -> None:
        self.candidates = candidates

    def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
        return self.candidates


def candidate(name: str, published_at: datetime | None) -> ArticleCandidate:
    return ArticleCandidate(
        source_id="news",
        url=f"https://example.com/{name}",
        title=name,
        summary=None,
        published_at=published_at.isoformat() if published_at else None,
        raw_payload=None,
    )


def test_explicit_sources_path_is_forwarded_unchanged_to_configuration_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.yaml"
    sources_path = tmp_path / "explicit-sources.yaml"
    database_path = tmp_path / "news.db"
    failure = RuntimeError("configuration authority failure")
    calls: list[tuple[Path, Path]] = []

    def load_configuration(config: Path, *, sources_path: Path):
        calls.append((config, sources_path))
        raise failure

    monkeypatch.setattr(poller, "load_configuration", load_configuration)
    monkeypatch.setattr(
        poller,
        "load_config",
        lambda path: pytest.fail(f"legacy loader used for explicit path: {path}"),
    )
    with pytest.raises(RuntimeError) as caught:
        poll_once(config_path, database_path, sources_path=sources_path)
    assert caught.value is failure
    assert calls == [(config_path, sources_path)]
    assert not database_path.exists()


def test_omitted_sources_path_preserves_legacy_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.yaml"
    failure = RuntimeError("legacy configuration failure")
    calls: list[Path] = []

    def load_config(path: Path):
        calls.append(path)
        raise failure

    monkeypatch.setattr(poller, "load_config", load_config)
    monkeypatch.setattr(
        poller,
        "load_configuration",
        lambda *args, **kwargs: pytest.fail(
            "explicit loader used without sources_path"
        ),
    )
    with pytest.raises(RuntimeError) as caught:
        poll_once(config_path, tmp_path / "news.db")
    assert caught.value is failure
    assert calls == [config_path]


def test_sources_path_is_keyword_only_and_poller_owns_no_selection_policy() -> None:
    parameter = inspect.signature(poll_once).parameters["sources_path"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None
    with pytest.raises(TypeError):
        poll_once(Path("config.yaml"), Path("news.db"), 20.0, Path("sources.yaml"))
    source = inspect.getsource(poller)
    assert "source_override_path" not in source
    assert "bundled_source_path" not in source
    assert "load_sources_config" not in source


def test_poll_groups_matching_articles_and_keeps_distinct_source_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = write_config(
        tmp_path / "sources.yaml",
        rss_source("digi", "https://example.com/digi")
        + rss_source("hotnews", "https://example.com/hotnews"),
    )
    install_client(monkeypatch, {})

    class EventAdapter:
        def fetch(
            self, source: SourceConfig, http_client: object
        ) -> list[ArticleCandidate]:
            source_id = source.id
            title = (
                "2.4 km of railway stolen"
                if source_id == "digi"
                else "Investigation after railway theft"
            )
            return [
                ArticleCandidate(
                    source_id=source_id,
                    url=f"https://example.com/{source_id}/story",
                    title=title,
                    summary=None,
                    published_at=None,
                    raw_payload=None,
                )
            ]

    monkeypatch.setattr("pastila_scout.poller.get_adapter", lambda kind: EventAdapter())
    database = tmp_path / "events.db"

    result = poll_once(database_path=database, config_path=config)

    assert result.status == "success"
    assert result.failed_source_ids == ()
    with open_database(database) as connection:
        events = connection.execute("SELECT * FROM events").fetchall()
        articles = connection.execute("SELECT * FROM articles").fetchall()
        assert len(events) == 1
        assert (events[0]["article_count"], events[0]["source_count"]) == (2, 2)
        assert {article["event_id"] for article in articles} == {events[0]["id"]}


def test_matching_failure_creates_fallback_event_without_aborting_poll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_config(
        tmp_path / "sources.yaml", rss_source("news", "https://example.com/feed")
    )
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda kind: CandidateAdapter([candidate("story", None)]),
    )
    monkeypatch.setattr(
        "pastila_scout.poller.match_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("matcher broke")),
    )
    configure_logging()
    database = tmp_path / "failure.db"

    result = poll_once(config, database)

    assert result.status == "success"
    with open_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert "Matching failed article_id=" in capsys.readouterr().err


def policy_config(
    path: Path,
    *,
    max_age: float = 24,
    max_articles: int = 100,
    accept_undated: bool = True,
    future_tolerance: float = 60,
    source_overrides: str = "",
) -> Path:
    path.write_text(
        f"""polling:
  max_article_age_hours: {max_age}
  max_articles_per_source: {max_articles}
  accept_articles_without_date: {str(accept_undated).lower()}
  future_date_tolerance_minutes: {future_tolerance}
sources:
  - id: news
    name: News
    type: rss
    url: https://example.com/feed
    enabled: true
    categories: [Politica, Social]
{source_overrides}""",
        encoding="utf-8",
    )
    return path


def test_successful_poll_persists_article_counters_and_raw_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    feed_url = "https://example.com/feed"
    config = write_config(tmp_path / "sources.yaml", rss_source("news", feed_url))
    database = tmp_path / "news.db"
    install_client(monkeypatch, {feed_url: RSS})
    configure_logging()

    result = poll_once(config, database)

    assert result.status == "success"
    assert (
        result.sources_checked,
        result.articles_found,
        result.articles_inserted,
    ) == (
        1,
        1,
        1,
    )
    with open_database(database) as connection:
        article = connection.execute("SELECT * FROM articles").fetchone()
        assert article["url"].startswith("HTTPS://Example.com:443")
        assert article["normalized_url"] == "https://example.com/story?id=1"
        assert article["title"].strip() == "Original   TITLE!!!"
        assert article["normalized_title"] == "original title"
        assert json.loads(article["raw_payload"])["description"] == "Summary"
        event = connection.execute("SELECT * FROM events").fetchone()
        assert event["canonical_title"].strip() == "Original   TITLE!!!"
        assert event["normalized_title"] == "original title"
    run = fetch_run(database, result.run_id)
    assert run["status"] == "success"
    assert run["finished_at"] is not None
    assert (
        run["sources_checked"],
        run["articles_found"],
        run["articles_inserted"],
    ) == (
        1,
        1,
        1,
    )
    logs = capsys.readouterr().err
    assert "Poll started" in logs
    assert f"config={config}" in logs
    assert f"database={database}" in logs
    assert "Source task started id=news type=rss" in logs
    assert "Poll completed status=success" in logs


def test_duplicate_article_is_prevented_across_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed_url = "https://example.com/feed"
    config = write_config(tmp_path / "sources.yaml", rss_source("news", feed_url))
    database = tmp_path / "news.db"
    install_client(monkeypatch, {feed_url: RSS})

    first = poll_once(config, database)
    second = poll_once(config, database)

    assert first.articles_inserted == 1
    assert second.articles_found == 1
    assert second.articles_inserted == 0
    assert second.duplicates_skipped == 1
    with open_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


def test_disabled_html_source_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = write_config(
        tmp_path / "sources.yaml",
        """  - id: disabled
    name: Disabled webpage
    type: html
    url: https://example.com/disabled
    enabled: false
    categories: [Social]
""",
    )
    client = install_client(monkeypatch, {})

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "success"
    assert result.sources_checked == 0
    assert client.requested == []


def test_successful_html_poll(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    page_url = "https://example.com/news"
    config = write_config(
        tmp_path / "sources.yaml",
        html_source("webpage", page_url),
    )
    client = install_client(monkeypatch, {page_url: HTML})

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "success"
    assert result.sources_checked == 1
    assert result.articles_found == result.articles_inserted == 1
    assert result.error_message is None
    assert client.requested == [page_url]


def test_mixed_rss_and_html_polling_updates_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed_url = "https://example.com/feed"
    page_url = "https://example.com/news"
    config = write_config(
        tmp_path / "sources.yaml",
        rss_source("feed", feed_url) + html_source("page", page_url),
    )
    install_client(monkeypatch, {feed_url: RSS, page_url: HTML})

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "success"
    assert (
        result.sources_checked,
        result.articles_found,
        result.articles_inserted,
    ) == (
        2,
        2,
        2,
    )


def test_poller_uses_adapter_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed_url = "https://example.com/feed"
    config = write_config(tmp_path / "sources.yaml", rss_source("news", feed_url))
    client = install_client(monkeypatch, {})
    requested_types: list[str] = []

    class EmptyAdapter:
        def fetch(self, source: object, http_client: object) -> list[object]:
            assert http_client is client
            return []

    def fake_get_adapter(source_type: str) -> EmptyAdapter:
        requested_types.append(source_type)
        return EmptyAdapter()

    monkeypatch.setattr("pastila_scout.poller.get_adapter", fake_get_adapter)

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "success"
    assert result.sources_checked == 1
    assert requested_types == ["rss"]


def test_one_failed_source_produces_partial_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    good_url = "https://example.com/good"
    bad_url = "https://example.com/bad"
    config = write_config(
        tmp_path / "sources.yaml",
        rss_source("good", good_url) + html_source("bad", bad_url),
    )
    install_client(monkeypatch, {good_url: RSS, bad_url: RuntimeError("offline")})
    configure_logging()

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "partial"
    assert result.sources_checked == 2
    assert result.articles_found == 1
    assert result.articles_inserted == 1
    assert result.error_message is not None
    assert result.error_message == "bad: offline"
    assert "Source task failed id=bad reason=offline" in capsys.readouterr().err


def test_all_sources_failing_records_failed_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed_url = "https://example.com/bad"
    config = write_config(tmp_path / "sources.yaml", rss_source("bad", feed_url))
    database = tmp_path / "news.db"
    install_client(monkeypatch, {feed_url: RuntimeError("offline")})

    result = poll_once(config, database)

    assert result.status == "failed"
    assert result.sources_checked == 1
    assert result.articles_found == result.articles_inserted == 0
    assert fetch_run(database, result.run_id)["status"] == "failed"


def test_no_enabled_rss_sources_records_zero_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = write_config(tmp_path / "sources.yaml", "")
    install_client(monkeypatch, {})

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "success"
    assert (
        result.sources_checked,
        result.articles_found,
        result.articles_inserted,
    ) == (
        0,
        0,
        0,
    )


def test_freshness_filters_and_exact_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    candidates = [
        candidate("too-old", now - timedelta(hours=24, seconds=1)),
        candidate("age-boundary", now - timedelta(hours=24)),
        candidate("future-boundary", now + timedelta(minutes=60)),
        candidate("too-future", now + timedelta(minutes=60, seconds=1)),
        candidate("undated", None),
    ]
    config = policy_config(tmp_path / "sources.yaml", accept_undated=False)
    database = tmp_path / "news.db"
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(candidates),
    )

    result = poll_once(config, database, now=now)

    assert result.articles_found == 5
    assert result.articles_inserted == 2
    assert result.articles_filtered_old == 1
    assert result.articles_filtered_future == 1
    assert result.articles_filtered_undated == 1
    assert result.articles_filtered_limit == 0
    with open_database(database) as connection:
        titles = [
            row["title"]
            for row in connection.execute("SELECT title FROM articles ORDER BY id")
        ]
    assert titles == ["future-boundary", "age-boundary"]


def test_newest_first_limit_preserves_equal_and_undated_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    same_time = now - timedelta(hours=2)
    candidates = [
        candidate("equal-first", same_time),
        candidate("undated-first", None),
        candidate("newest", now - timedelta(hours=1)),
        candidate("equal-second", same_time),
        candidate("undated-second", None),
    ]
    config = policy_config(tmp_path / "sources.yaml", max_articles=4)
    database = tmp_path / "news.db"
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(candidates),
    )

    result = poll_once(config, database, now=now)

    assert result.articles_filtered_limit == 1
    with open_database(database) as connection:
        titles = [
            row["title"]
            for row in connection.execute("SELECT title FROM articles ORDER BY id")
        ]
    assert titles == ["newest", "equal-first", "equal-second", "undated-first"]


def test_per_source_policy_overrides_global_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    candidates = [
        candidate("newest", now - timedelta(hours=1)),
        candidate("older", now - timedelta(hours=2)),
        candidate("undated", None),
    ]
    config = policy_config(
        tmp_path / "sources.yaml",
        max_age=48,
        max_articles=10,
        accept_undated=True,
        source_overrides=(
            "    max_article_age_hours: 12\n"
            "    max_articles_per_poll: 1\n"
            "    accept_articles_without_date: false\n"
        ),
    )
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(candidates),
    )

    result = poll_once(config, tmp_path / "news.db", now=now)

    assert result.articles_inserted == 1
    assert result.articles_filtered_undated == 1
    assert result.articles_filtered_limit == 1


@pytest.mark.parametrize(
    ("override_hours", "expected_inserted", "expected_old"),
    [(24.0, 0, 1), (720.0, 1, 0)],
)
def test_runtime_age_override_changes_filtering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override_hours: float,
    expected_inserted: int,
    expected_old: int,
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    config = policy_config(
        tmp_path / "sources.yaml",
        max_age=168,
        source_overrides="    max_article_age_hours: 72\n",
    )
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(
            [candidate("article", now - timedelta(hours=25))]
        ),
    )

    result = poll_once(
        config,
        tmp_path / "news.db",
        now=now,
        max_article_age_hours_override=override_hours,
    )

    assert result.articles_inserted == expected_inserted
    assert result.articles_filtered_old == expected_old


def test_runtime_override_accepts_exact_age_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    config = policy_config(tmp_path / "sources.yaml")
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(
            [candidate("boundary", now - timedelta(hours=24))]
        ),
    )

    result = poll_once(
        config,
        tmp_path / "news.db",
        now=now,
        max_article_age_hours_override=24,
    )

    assert result.articles_inserted == 1
    assert result.articles_filtered_old == 0


def test_runtime_override_applies_to_every_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    config = tmp_path / "sources.yaml"
    config.write_text(
        """polling:
  max_article_age_hours: 168
sources:
  - id: first
    name: First
    type: rss
    url: https://example.com/first
    enabled: true
    categories: [Politica]
    max_article_age_hours: 72
  - id: second
    name: Second
    type: rss
    url: https://example.com/second
    enabled: true
    categories: [Social]
    max_article_age_hours: 336
""",
        encoding="utf-8",
    )
    install_client(monkeypatch, {})

    class PerSourceAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            source_id = source.id
            return [
                ArticleCandidate(
                    source_id=source_id,
                    url=f"https://example.com/{source_id}/article",
                    title=f"{source_id} article",
                    summary=None,
                    published_at=(now - timedelta(hours=25)).isoformat(),
                    raw_payload=None,
                )
            ]

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: PerSourceAdapter()
    )

    result = poll_once(
        config,
        tmp_path / "news.db",
        now=now,
        max_article_age_hours_override=24,
    )

    assert result.sources_succeeded == 2
    assert result.articles_found == 2
    assert result.articles_inserted == 0
    assert result.articles_filtered_old == 2


def test_runtime_override_does_not_mutate_config_or_leak_between_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)
    config = policy_config(
        tmp_path / "sources.yaml",
        max_age=168,
        source_overrides="    max_article_age_hours: 72\n",
    )
    original_config = config.read_bytes()
    database = tmp_path / "news.db"
    install_client(monkeypatch, {})
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter(
            [candidate("article", now - timedelta(hours=48))]
        ),
    )
    configure_logging()

    first = poll_once(
        config,
        database,
        now=now,
        max_article_age_hours_override=24,
    )
    second = poll_once(config, database, now=now)

    assert first.articles_filtered_old == 1
    assert second.articles_filtered_old == 0
    assert second.articles_inserted == 1
    assert config.read_bytes() == original_config
    logs = capsys.readouterr()
    assert "Selected article age window: 1 day (24 hours)" in logs.err
    assert logs.out == ""


def multi_source_config(
    path: Path,
    source_count: int,
    *,
    concurrency: int = 3,
    categories: str = "[Politica, Social]",
) -> Path:
    sources = "".join(
        f"""  - id: source{index}
    name: Source {index}
    type: rss
    url: https://example.com/feed{index}
    enabled: true
    categories: {categories}
"""
        for index in range(source_count)
    )
    path.write_text(
        f"polling:\n  concurrency: {concurrency}\nsources:\n{sources}",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("concurrency", [1, 2, 3])
def test_source_work_respects_configured_concurrency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, concurrency: int
) -> None:
    config = multi_source_config(
        tmp_path / "sources.yaml", concurrency + 1, concurrency=concurrency
    )
    database = tmp_path / "news.db"
    install_client(monkeypatch, {})

    class BoundedAdapter:
        def __init__(self) -> None:
            self.lock = threading.Lock()
            self.release = threading.Event()
            self.limit_reached = threading.Event()
            self.active = 0
            self.maximum_active = 0
            self.started = 0

        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            source_id = source.id
            with self.lock:
                self.active += 1
                self.started += 1
                self.maximum_active = max(self.maximum_active, self.active)
                if self.active == concurrency:
                    self.limit_reached.set()
            assert self.release.wait(5), "test did not release blocked adapters"
            with self.lock:
                self.active -= 1
            return [
                ArticleCandidate(
                    source_id=source_id,
                    url=f"https://example.com/{source_id}",
                    title=source_id,
                    summary=None,
                    published_at=None,
                    raw_payload=None,
                )
            ]

    adapter = BoundedAdapter()
    monkeypatch.setattr("pastila_scout.poller.get_adapter", lambda source_type: adapter)
    outcome: dict[str, object] = {}

    def run_poll() -> None:
        try:
            outcome["result"] = poll_once(config, database)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            outcome["error"] = exc

    thread = threading.Thread(target=run_poll)
    thread.start()
    assert adapter.limit_reached.wait(5)
    with adapter.lock:
        assert adapter.maximum_active == concurrency
        assert adapter.started == concurrency
    adapter.release.set()
    thread.join(10)

    assert not thread.is_alive()
    assert "error" not in outcome
    result = outcome["result"]
    assert result.articles_inserted == concurrency + 1
    with open_database(database) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            == concurrency + 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM editorial_queue").fetchone()[0]
            == concurrency + 1
        )


def test_category_filtering_and_zero_match_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text(
        """sources:
  - id: politics
    name: Politics
    type: rss
    url: https://example.com/politics
    enabled: true
    categories: [Politica, Social]
  - id: social
    name: Social
    type: rss
    url: https://example.com/social
    enabled: true
    categories: [Social]
  - id: disabled
    name: Disabled
    type: rss
    url: https://example.com/disabled
    enabled: false
    categories: [Conspiratii]
""",
        encoding="utf-8",
    )
    install_client(monkeypatch, {})
    seen: list[str] = []
    lock = threading.Lock()

    class RecordingAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            with lock:
                seen.append(source.id)
            return []

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: RecordingAdapter()
    )

    politics = poll_once(config, tmp_path / "politics.db", category="Politica")
    no_match = poll_once(config, tmp_path / "none.db", category="Conspiratii")

    assert politics.status == "success"
    assert politics.sources_checked == 1
    assert seen == ["politics"]
    assert no_match.status == "success"
    assert no_match.sources_checked == 0
    assert no_match.category == "Conspiratii"


def test_category_filtered_poll_persists_single_category_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = write_config(
        tmp_path / "sources.yaml",
        """  - id: news
    name: Social
    type: rss
    url: https://example.com/social
    enabled: true
    categories: [Social]
""",
    )
    install_client(monkeypatch, {})
    now = datetime(2026, 8, 14, 23, 28, 40, tzinfo=UTC)
    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter",
        lambda source_type: CandidateAdapter([candidate("social-story", now)]),
    )
    database = tmp_path / "social.db"

    result = poll_once(config, database, category="Social", now=now)

    assert result.articles_inserted == 1
    with open_database(database) as connection:
        event = connection.execute("SELECT id, category FROM events").fetchone()
        categories = connection.execute(
            "SELECT category, position FROM event_categories WHERE event_id = ?",
            (event["id"],),
        ).fetchall()
    assert event["category"] == "Social"
    assert [tuple(row) for row in categories] == [("Social", 0)]


@pytest.mark.parametrize(
    ("category", "expected_ids"),
    [
        ("Politica", {"politica", "multi"}),
        ("Social", {"social"}),
        ("Conspiratii", {"conspiratii"}),
        ("Economie", {"economie", "multi"}),
        ("CanCan", {"cancan"}),
        ("Externe", {"externe"}),
        ("Diverse", {"diverse"}),
        (
            "all",
            {
                "politica",
                "social",
                "conspiratii",
                "economie",
                "cancan",
                "externe",
                "diverse",
                "multi",
            },
        ),
    ],
)
def test_each_category_selects_matching_enabled_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    expected_ids: set[str],
) -> None:
    definitions = [
        ("politica", "[Politica]", True),
        ("social", "[Social]", True),
        ("conspiratii", "[Conspiratii]", True),
        ("economie", "[Economie]", True),
        ("cancan", "[CanCan]", True),
        ("externe", "[Externe]", True),
        ("diverse", "[Diverse]", True),
        ("multi", "[Politica, Economie]", True),
        ("disabled", "[Politica]", False),
    ]
    source_yaml = "".join(
        f"""  - id: {source_id}
    name: {source_id}
    type: rss
    url: https://example.com/{source_id}
    enabled: {str(enabled).lower()}
    categories: {categories}
"""
        for source_id, categories, enabled in definitions
    )
    config = tmp_path / "sources.yaml"
    config.write_text(f"sources:\n{source_yaml}", encoding="utf-8")
    install_client(monkeypatch, {})
    seen: set[str] = set()
    lock = threading.Lock()

    class RecordingAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            with lock:
                seen.add(source.id)
            return []

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: RecordingAdapter()
    )

    result = poll_once(config, tmp_path / f"{category}.db", category=category)

    assert result.status == "success"
    assert result.sources_checked == len(expected_ids)
    assert seen == expected_ids


def test_failure_order_is_deterministic_despite_worker_completion_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = multi_source_config(tmp_path / "sources.yaml", 2, concurrency=2)
    install_client(monkeypatch, {})
    release_first = threading.Event()

    class OrderedFailureAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            source_id = source.id
            if source_id == "source0":
                assert release_first.wait(5)
                raise RuntimeError("first failed later")
            release_first.set()
            raise RuntimeError("second failed first")

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: OrderedFailureAdapter()
    )

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "failed"
    assert result.source_failures == (
        "source0: first failed later",
        "source1: second failed first",
    )
    assert result.failed_source_ids == ("source0", "source1")


@pytest.mark.parametrize(
    "source_id",
    (
        "plain-ascii",
        "id with spaces",
        "id:colon",
        "id::multiple::colons",
        "id: offline: delimiter-like",
        "path/segment",
        r"path\segment",
        "punctuation.!@#$%^&*()[]{}",
        "știri-românești",
    ),
)
def test_failed_source_identity_is_lossless_and_diagnostic_is_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_id: str,
) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": source_id,
                        "name": "Adversarial source",
                        "type": "rss",
                        "url": "https://example.com/feed",
                        "enabled": True,
                        "categories": ["Politica"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    install_client(monkeypatch, {})

    class FailingAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            raise RuntimeError("offline: retry later")

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: FailingAdapter()
    )

    result = poll_once(config, tmp_path / "news.db")

    assert result.failed_source_ids == (source_id,)
    assert result.source_failures == (f"{source_id}: offline: retry later",)
    assert result.sources_failed == 1


def test_poll_result_appended_identity_field_preserves_constructor_protocols() -> None:
    legacy = PollResult(1, "success", 0, 0, 0, None)
    structured = PollResult(
        2,
        "failed",
        1,
        0,
        0,
        "source: offline",
        sources_failed=1,
        source_failures=("source: offline",),
        failed_source_ids=("source",),
    )

    assert legacy.failed_source_ids == ()
    assert copy.copy(structured) == structured
    assert copy.deepcopy(structured) == structured
    assert pickle.loads(pickle.dumps(structured)) == structured
    assert "failed_source_ids=('source',)" in repr(structured)


def test_structured_failure_ids_cover_interleaved_and_persistence_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_ids = ("first:failure", "success", "persist\\failure")
    config = tmp_path / "sources.yaml"
    config.write_text(
        json.dumps(
            {
                "polling": {"concurrency": 3},
                "sources": [
                    {
                        "id": source_id,
                        "name": source_id,
                        "type": "rss",
                        "url": f"https://example.com/{index}",
                        "enabled": True,
                        "categories": ["Politica"],
                    }
                    for index, source_id in enumerate(source_ids)
                ],
            }
        ),
        encoding="utf-8",
    )
    install_client(monkeypatch, {})

    class MixedAdapter:
        def fetch(
            self, source: SourceConfig, http_client: object
        ) -> list[ArticleCandidate]:
            if source.id == "first:failure":
                raise RuntimeError("fetch failed")
            if source.id == "success":
                return []
            return [
                ArticleCandidate(
                    source_id=source.id,
                    url="https://example.com/persistence-candidate",
                    title="candidate",
                    summary=None,
                    published_at=None,
                    raw_payload=None,
                )
            ]

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: MixedAdapter()
    )
    monkeypatch.setattr(
        "pastila_scout.poller._insert_candidate",
        lambda connection, candidate: (_ for _ in ()).throw(
            RuntimeError("persistence failed")
        ),
    )

    result = poll_once(config, tmp_path / "news.db")

    assert result.status == "partial"
    assert result.sources_succeeded == 1
    assert result.sources_failed == 2
    assert result.failed_source_ids == ("first:failure", "persist\\failure")
    assert result.source_failures == (
        "first:failure: fetch failed",
        "persist\\failure: persistence failed",
    )


def test_cross_source_duplicates_persist_and_queue_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = multi_source_config(tmp_path / "sources.yaml", 2, concurrency=2)
    database = tmp_path / "news.db"
    install_client(monkeypatch, {})

    class DuplicateAdapter:
        def fetch(self, source: object, http_client: object) -> list[ArticleCandidate]:
            return [
                ArticleCandidate(
                    source_id=source.id,
                    url="https://example.com/shared",
                    title="shared",
                    summary=None,
                    published_at=None,
                    raw_payload=None,
                )
            ]

    monkeypatch.setattr(
        "pastila_scout.poller.get_adapter", lambda source_type: DuplicateAdapter()
    )

    result = poll_once(config, database)

    assert result.articles_found == 2
    assert result.articles_inserted == 1
    assert result.duplicates_skipped == 1
    with open_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1
        assert (
            connection.execute("SELECT COUNT(*) FROM editorial_queue").fetchone()[0]
            == 1
        )
