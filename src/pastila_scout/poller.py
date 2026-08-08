"""One-shot RSS polling orchestration."""

import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pastila_scout.adapters.registry import get_adapter
from pastila_scout.config import (
    SourceCategory,
    SourceConfig,
    load_config,
    load_configuration,
)
from pastila_scout.database import (
    attach_article_to_event,
    create_event,
    find_recent_events,
    initialize_database,
    insert_article,
    normalized_url_exists,
    open_database,
    upsert_source,
    utc_now,
)
from pastila_scout.event_matcher import match_event
from pastila_scout.http_client import HTTPClient
from pastila_scout.models import ArticleCandidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PollResult:
    """Final status and counters for one polling execution."""

    run_id: int
    status: str
    sources_checked: int
    articles_found: int
    articles_inserted: int
    error_message: str | None
    sources_succeeded: int = 0
    sources_failed: int = 0
    duplicates_skipped: int = 0
    source_failures: tuple[str, ...] = ()
    articles_filtered_old: int = 0
    articles_filtered_future: int = 0
    articles_filtered_undated: int = 0
    articles_filtered_limit: int = 0
    category: str = "all"
    failed_source_ids: tuple[str, ...] = ()


def poll_once(
    config_path: Path,
    database_path: Path,
    timeout: float = 20.0,
    *,
    sources_path: Path | None = None,
    now: datetime | None = None,
    max_article_age_hours_override: float | None = None,
    category: str = "all",
) -> PollResult:
    """Run one RSS polling cycle and persist its result."""

    logger.info("Poll started config=%s database=%s", config_path, database_path)
    if sources_path is None:
        config = load_config(config_path)
    else:
        if type(sources_path) is not type(Path()) or not sources_path.is_absolute():
            raise TypeError("sources_path must be an absolute concrete Path")
        config = load_configuration(config_path, sources_path=sources_path)
    allowed_categories = {item.value for item in SourceCategory} | {"all"}
    if category not in allowed_categories:
        raise ValueError(f"Unsupported source category: {category!r}")
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise ValueError("Injected polling time must include timezone information")
    current_time = current_time.astimezone(UTC)
    if (
        max_article_age_hours_override is not None
        and max_article_age_hours_override <= 0
    ):
        raise ValueError("Article age override must be positive")
    selected_age_hours = (
        max_article_age_hours_override
        if max_article_age_hours_override is not None
        else config.polling.max_article_age_hours
    )
    selected_days = selected_age_hours / 24
    logger.info(
        "Selected article age window: %g %s (%g hours)",
        selected_days,
        "day" if selected_days == 1 else "days",
        selected_age_hours,
    )
    logger.info("Configuration loaded sources=%d", len(config.sources))
    logger.info("Selected source category: %s", category)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with open_database(database_path) as connection:
        initialize_database(connection)
        for source in config.sources:
            upsert_source(
                connection,
                source_id=source.id,
                name=source.name,
                source_type=source.type,
                url=source.url,
                enabled=source.enabled,
                categories=tuple(category.value for category in source.categories),
                priority=source.priority,
            )

        run_id = _start_run(connection)
        enabled_sources = [source for source in config.sources if source.enabled]
        selected_sources = [
            source
            for source in enabled_sources
            if category == "all" or category in source.categories
        ]
        logger.info(
            "Enabled sources before category filtering: %d", len(enabled_sources)
        )
        logger.info(
            "Sources selected after category filtering: %d", len(selected_sources)
        )
        logger.info("Source concurrency limit: %d", config.polling.concurrency)
        sources_checked = len(selected_sources)
        articles_found = 0
        articles_inserted = 0
        duplicates_skipped = 0
        filtered_old = 0
        filtered_future = 0
        filtered_undated = 0
        filtered_limit = 0
        successful_sources = 0
        failures: list[str] = []
        failed_source_ids: list[str] = []

        work_results = _collect_source_results(
            selected_sources,
            timeout=timeout,
            concurrency=config.polling.concurrency,
            now=current_time,
            max_article_age_hours_override=max_article_age_hours_override,
            global_max_age_hours=config.polling.max_article_age_hours,
            global_max_articles=config.polling.max_articles_per_source,
            global_accept_undated=config.polling.accept_articles_without_date,
            future_tolerance_minutes=config.polling.future_date_tolerance_minutes,
        )
        for work in work_results:
            source = work.source
            if work.error is not None:
                logger.error(
                    "Source task failed id=%s reason=%s", source.id, work.error
                )
                failures.append(f"{source.id}: {work.error}")
                failed_source_ids.append(source.id)
                continue

            articles_found += work.extracted_count
            filtered_old += work.filtered.old
            filtered_future += work.filtered.future
            filtered_undated += work.filtered.undated
            filtered_limit += work.filtered.over_limit
            source_inserted = 0
            source_duplicates = 0
            logger.info("Source persistence started id=%s", source.id)
            try:
                for candidate in work.filtered.candidates:
                    if normalized_url_exists(connection, candidate.url):
                        duplicates_skipped += 1
                        source_duplicates += 1
                        continue
                    article_id = _insert_candidate(connection, candidate)
                    if article_id is not None:
                        articles_inserted += 1
                        source_inserted += 1
                        try:
                            _assign_event(
                                connection,
                                article_id=article_id,
                                candidate=candidate,
                                now=current_time,
                                enabled=config.event_matching.enabled,
                                lookback_hours=config.event_matching.lookback_hours,
                                threshold=config.event_matching.similarity_threshold,
                                category=None if category == "all" else category,
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.error(
                                "Matching failed article_id=%s reason=%s",
                                article_id,
                                exc,
                            )
                            try:
                                event_id = create_event(
                                    connection,
                                    article_id=article_id,
                                    canonical_title=_candidate_original_title(
                                        candidate
                                    ),
                                    normalized_title=candidate.title,
                                    summary=candidate.summary,
                                    category=None if category == "all" else category,
                                    seen_at=current_time.isoformat(),
                                )
                                logger.info(
                                    "Event created event_id=%s article_id=%s fallback=true",
                                    event_id,
                                    article_id,
                                )
                            except Exception as fallback_exc:  # noqa: BLE001
                                logger.error(
                                    "Event fallback failed article_id=%s reason=%s",
                                    article_id,
                                    fallback_exc,
                                )
                    else:
                        duplicates_skipped += 1
                        source_duplicates += 1
                successful_sources += 1
                logger.info(
                    "Source persistence completed id=%s inserted=%d duplicates=%d",
                    source.id,
                    source_inserted,
                    source_duplicates,
                )
            except Exception as exc:  # noqa: BLE001 - isolate source persistence
                logger.error(
                    "Source persistence failed id=%s reason=%s", source.id, exc
                )
                failures.append(f"{source.id}: {exc}")
                failed_source_ids.append(source.id)

        status = _run_status(successful_sources, failures)
        error_message = "; ".join(failures) or None
        _finish_run(
            connection,
            run_id=run_id,
            status=status,
            sources_checked=sources_checked,
            articles_found=articles_found,
            articles_inserted=articles_inserted,
            error_message=error_message,
        )
        result = PollResult(
            run_id=run_id,
            status=status,
            sources_checked=sources_checked,
            articles_found=articles_found,
            articles_inserted=articles_inserted,
            error_message=error_message,
            sources_succeeded=successful_sources,
            sources_failed=len(failures),
            duplicates_skipped=duplicates_skipped,
            source_failures=tuple(failures),
            articles_filtered_old=filtered_old,
            articles_filtered_future=filtered_future,
            articles_filtered_undated=filtered_undated,
            articles_filtered_limit=filtered_limit,
            category=category,
            failed_source_ids=tuple(failed_source_ids),
        )
        logger.info(
            "Poll completed status=%s sources_checked=%d sources_succeeded=%d "
            "sources_failed=%d articles_found=%d articles_inserted=%d duplicates=%d "
            "filtered_old=%d filtered_future=%d filtered_undated=%d filtered_limit=%d",
            result.status,
            result.sources_checked,
            result.sources_succeeded,
            result.sources_failed,
            result.articles_found,
            result.articles_inserted,
            result.duplicates_skipped,
            result.articles_filtered_old,
            result.articles_filtered_future,
            result.articles_filtered_undated,
            result.articles_filtered_limit,
        )
        return result


@dataclass(frozen=True, slots=True)
class _FilteredCandidates:
    """Candidates retained after freshness checks plus rejection counters."""

    candidates: tuple[ArticleCandidate, ...]
    old: int
    future: int
    undated: int
    over_limit: int


@dataclass(frozen=True, slots=True)
class _SourceWorkResult:
    """Thread-produced source result containing no database state."""

    index: int
    source: SourceConfig
    extracted_count: int
    filtered: _FilteredCandidates
    error: Exception | None = None


def _collect_source_results(
    sources: list[SourceConfig],
    *,
    timeout: float,
    concurrency: int,
    now: datetime,
    max_article_age_hours_override: float | None,
    global_max_age_hours: float,
    global_max_articles: int,
    global_accept_undated: bool,
    future_tolerance_minutes: float,
) -> list[_SourceWorkResult]:
    """Fetch, parse, and filter sources concurrently without touching SQLite."""

    if not sources:
        return []

    results: list[_SourceWorkResult] = []
    with (
        HTTPClient(timeout=timeout) as client,
        ThreadPoolExecutor(
            max_workers=concurrency, thread_name_prefix="pastila-source"
        ) as executor,
    ):
        futures = {
            executor.submit(
                _process_source,
                index,
                source,
                client,
                now=now,
                max_age_hours=(
                    max_article_age_hours_override
                    if max_article_age_hours_override is not None
                    else source.max_article_age_hours or global_max_age_hours
                ),
                max_articles=(source.max_articles_per_poll or global_max_articles),
                accept_undated=(
                    source.accept_articles_without_date
                    if source.accept_articles_without_date is not None
                    else global_accept_undated
                ),
                future_tolerance_minutes=future_tolerance_minutes,
            ): index
            for index, source in enumerate(sources)
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda result: result.index)
    return results


def _process_source(
    index: int,
    source: SourceConfig,
    http_client: HTTPClient,
    *,
    now: datetime,
    max_age_hours: float,
    max_articles: int,
    accept_undated: bool,
    future_tolerance_minutes: float,
) -> _SourceWorkResult:
    """Run one adapter and freshness policy in a worker thread."""

    logger.info("Source task started id=%s type=%s", source.id, source.type)
    try:
        candidates = get_adapter(source.type).fetch(source, http_client)
        filtered = _filter_candidates(
            candidates,
            now=now,
            max_age_hours=max_age_hours,
            max_articles=max_articles,
            accept_undated=accept_undated,
            future_tolerance_minutes=future_tolerance_minutes,
        )
    except Exception as exc:  # noqa: BLE001 - isolate individual source tasks
        logger.error("Source task failed id=%s reason=%s", source.id, exc)
        return _SourceWorkResult(
            index=index,
            source=source,
            extracted_count=0,
            filtered=_FilteredCandidates((), 0, 0, 0, 0),
            error=exc,
        )

    logger.info(
        "Source task completed id=%s candidates=%d retained=%d",
        source.id,
        len(candidates),
        len(filtered.candidates),
    )
    return _SourceWorkResult(
        index=index,
        source=source,
        extracted_count=len(candidates),
        filtered=filtered,
    )


def _filter_candidates(
    candidates: list[ArticleCandidate],
    *,
    now: datetime,
    max_age_hours: float,
    max_articles: int,
    accept_undated: bool,
    future_tolerance_minutes: float,
) -> _FilteredCandidates:
    """Filter candidates by freshness, order them, and apply a source limit."""

    oldest_allowed = now - timedelta(hours=max_age_hours)
    newest_allowed = now + timedelta(minutes=future_tolerance_minutes)
    dated: list[tuple[ArticleCandidate, datetime]] = []
    undated_candidates: list[ArticleCandidate] = []
    old = 0
    future = 0
    undated = 0

    for candidate in candidates:
        published_at = _candidate_date(candidate)
        if published_at is None:
            if accept_undated:
                undated_candidates.append(candidate)
            else:
                undated += 1
            continue
        if published_at < oldest_allowed:
            old += 1
            continue
        if published_at > newest_allowed:
            future += 1
            continue
        dated.append((candidate, published_at))

    dated.sort(key=lambda item: item[1], reverse=True)
    ordered = [candidate for candidate, _ in dated] + undated_candidates
    over_limit = max(0, len(ordered) - max_articles)
    return _FilteredCandidates(
        candidates=tuple(ordered[:max_articles]),
        old=old,
        future=future,
        undated=undated,
        over_limit=over_limit,
    )


def _candidate_date(candidate: ArticleCandidate) -> datetime | None:
    """Parse a candidate timestamp as UTC, treating invalid values as undated."""

    if candidate.published_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(candidate.published_at)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _start_run(connection: sqlite3.Connection) -> int:
    """Insert and return a running poll record."""

    cursor = connection.execute(
        "INSERT INTO poll_runs (started_at, status) VALUES (?, 'running')",
        (utc_now(),),
    )
    connection.commit()
    return int(cursor.lastrowid)


def _finish_run(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    status: str,
    sources_checked: int,
    articles_found: int,
    articles_inserted: int,
    error_message: str | None,
) -> None:
    """Finalize a poll record with its outcome and counters."""

    connection.execute(
        """
        UPDATE poll_runs
        SET finished_at = ?, status = ?, sources_checked = ?,
            articles_found = ?, articles_inserted = ?, error_message = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            status,
            sources_checked,
            articles_found,
            articles_inserted,
            error_message,
            run_id,
        ),
    )
    connection.commit()


def _run_status(successful_sources: int, failures: list[str]) -> str:
    """Derive the final run status from source outcomes."""

    if not failures:
        return "success"
    if successful_sources:
        return "partial"
    return "failed"


def _insert_candidate(
    connection: sqlite3.Connection, candidate: ArticleCandidate
) -> int | None:
    """Persist a candidate while retaining raw link and title values."""

    payload = candidate.raw_payload or {}
    original_url = payload.get("link", candidate.url)
    original_title = payload.get("title", candidate.title)
    return insert_article(
        connection,
        source_id=candidate.source_id,
        url=original_url if isinstance(original_url, str) else candidate.url,
        normalized_url=candidate.url,
        title=original_title if isinstance(original_title, str) else candidate.title,
        normalized_title=candidate.title,
        summary=candidate.summary,
        published_at=candidate.published_at,
        raw_payload=(
            json.dumps(candidate.raw_payload, ensure_ascii=False)
            if candidate.raw_payload is not None
            else None
        ),
    )


def _assign_event(
    connection: sqlite3.Connection,
    *,
    article_id: int,
    candidate: ArticleCandidate,
    now: datetime,
    enabled: bool,
    lookback_hours: float,
    threshold: float,
    category: str | None,
) -> None:
    """Match an inserted article or create its new canonical event."""

    match = None
    if enabled:
        cutoff = (now - timedelta(hours=lookback_hours)).isoformat()
        match = match_event(
            candidate.title,
            find_recent_events(connection, cutoff=cutoff),
            threshold=threshold,
        )
    if match is None:
        event_id = create_event(
            connection,
            article_id=article_id,
            canonical_title=_candidate_original_title(candidate),
            normalized_title=candidate.title,
            summary=candidate.summary,
            category=category,
            seen_at=now.isoformat(),
        )
        logger.info("Event created event_id=%s article_id=%s", event_id, article_id)
        return
    attach_article_to_event(
        connection,
        article_id=article_id,
        event_id=match.event_id,
        seen_at=now.isoformat(),
    )
    logger.info(
        "Article matched event_id=%s article_id=%s score=%.2f",
        match.event_id,
        article_id,
        match.score,
    )


def _candidate_original_title(candidate: ArticleCandidate) -> str:
    """Return the parser-preserved title when available."""

    if candidate.raw_payload is not None:
        title = candidate.raw_payload.get("title")
        if isinstance(title, str):
            return title
    return candidate.title
