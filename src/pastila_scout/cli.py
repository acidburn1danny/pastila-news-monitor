"""Command-line interface for Pastila Scout."""

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pastila_scout.adapters.registry import get_adapter
from pastila_scout.ai.cache import FileJSONCache, FileVerificationCache
from pastila_scout.ai.editorial_scoring import EditorialEventScorer
from pastila_scout.ai.openai_provider import OpenAIProvider
from pastila_scout.ai.provider import ProviderError, resolve_openai_api_key
from pastila_scout.ai.verification import EventVerifier
from pastila_scout.config import (
    ConfigError,
    SourceCategory,
    SourceConfig,
    load_config,
    load_configuration,
)
from pastila_scout.console import configure_unicode_console
from pastila_scout.contracts import (
    EditorAgentOutputV1,
    EpisodeContextV1,
    ScoutEditorInputV1,
    SelectionProfileV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.io import ContractFileError, load_contract, write_contract
from pastila_scout.contracts.samples import write_sample_contracts
from pastila_scout.contracts.schemas import write_json_schemas
from pastila_scout.core.event_integrity import audit_event_integrity
from pastila_scout.core.event_ranking import rank_event_snapshots
from pastila_scout.core.event_reconciliation import build_reconciliation_plan
from pastila_scout.core.event_verification import (
    build_verification_requests,
    run_event_verification,
)
from pastila_scout.database import (
    QueueStateError,
    StaleReconciliationPlanError,
    apply_reconciliation_plan,
    backfill_editorial_queue,
    canonicalize_all_events,
    get_article_count,
    get_event_sources,
    get_latest_articles,
    get_latest_poll_run,
    get_poll_run_count,
    get_queue_counts,
    get_source_counts,
    initialize_database,
    list_event_ids_for_ranking,
    list_queue_items,
    list_recent_events,
    load_event_integrity_snapshot,
    load_event_snapshot,
    load_reconciliation_snapshot,
    open_database,
    open_database_readonly,
    review_queue_item,
)
from pastila_scout.exporters.editor_input import (
    EditorInputExportContext,
    export_editor_input,
)
from pastila_scout.http_client import HTTPClient
from pastila_scout.logging_config import configure_logging
from pastila_scout.models import (
    EventRankingReport,
    EventReconciliationPlan,
    ReconciliationApplicationReport,
)
from pastila_scout.poller import poll_once
from pastila_scout.reporting.event_audit import (
    STRUCTURAL_FINDING_CATEGORIES,
    WARNING_FINDING_CATEGORIES,
    category_counts,
    render_console_details,
    write_event_audit_report,
)
from pastila_scout.reporting.event_canonicalization import write_canonicalization_report
from pastila_scout.reporting.event_ranking import render_ranking, write_ranking_reports
from pastila_scout.reporting.event_reconciliation import (
    render_proposal_console,
    write_application_report,
    write_reconciliation_plan,
)
from pastila_scout.reporting.verification import (
    render_verification_console,
    write_verification_reports,
)

POLL_DAY_CHOICES = (1, 3, 7, 14, 30)
CATEGORY_CHOICES = tuple(category.value for category in SourceCategory) + ("all",)


def build_parser() -> argparse.ArgumentParser:
    """Build the Pastila Scout command-line parser."""

    parser = argparse.ArgumentParser(prog="pastila-scout")
    subparsers = parser.add_subparsers(dest="command", required=True)
    poll_parser = subparsers.add_parser("poll-once", help="poll enabled sources once")
    poll_parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    poll_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    poll_parser.add_argument("--timeout", type=float, default=20.0)
    poll_parser.add_argument("--verbose", action="store_true")
    poll_parser.add_argument(
        "--days",
        type=int,
        choices=POLL_DAY_CHOICES,
        help="maximum article age in days for this run",
    )
    poll_parser.add_argument(
        "--category",
        choices=CATEGORY_CHOICES,
        default="all",
        help="select sources by broad Romanian coverage category",
    )

    validate_parser = subparsers.add_parser(
        "validate-config", help="validate configured sources without persistence"
    )
    validate_parser.add_argument(
        "--config", type=Path, default=Path("config/sources.yaml")
    )
    validate_parser.add_argument("--timeout", type=float, default=20.0)
    validate_parser.add_argument("--verbose", action="store_true")
    validate_parser.add_argument(
        "--category",
        choices=CATEGORY_CHOICES,
        default="all",
        help="validate only enabled sources in this category",
    )

    status_parser = subparsers.add_parser("status", help="show persisted Scout status")
    status_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    status_parser.add_argument("--limit", type=_positive_integer, default=10)

    queue_parser = subparsers.add_parser("queue", help="list editorial queue items")
    queue_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    queue_parser.add_argument("--limit", type=_positive_integer, default=20)
    queue_parser.add_argument(
        "--status",
        choices=("pending", "claimed", "reviewed", "rejected", "all"),
        default="pending",
    )

    review_parser = subparsers.add_parser(
        "review", help="record an editorial queue decision"
    )
    review_parser.add_argument("queue_id", type=_positive_integer, metavar="QUEUE_ID")
    review_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    review_parser.add_argument(
        "--decision", choices=("keep", "reject", "backup"), required=True
    )
    review_parser.add_argument("--reviewer")
    review_parser.add_argument("--notes")

    backfill_parser = subparsers.add_parser(
        "queue-backfill", help="queue existing articles"
    )
    backfill_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    events_parser = subparsers.add_parser(
        "events", help="list recent editorial events and confirming sources"
    )
    events_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    events_parser.add_argument("--limit", type=_positive_integer, default=20)
    events_parser.add_argument("--min-sources", type=_positive_integer, default=1)
    events_parser.add_argument("--hours", type=_positive_float, default=168.0)
    events_parser.add_argument("--category", choices=CATEGORY_CHOICES, default="all")
    audit_parser = subparsers.add_parser(
        "audit-events", help="audit event integrity without modifying the database"
    )
    audit_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    audit_parser.add_argument(
        "--details", action="store_true", help="print individual audit findings"
    )
    audit_parser.add_argument(
        "--limit",
        type=_positive_integer,
        help="maximum console findings per category; implies detail output",
    )
    audit_parser.add_argument(
        "--output", type=Path, help="path for the complete UTF-8 audit report"
    )
    plan_parser = subparsers.add_parser(
        "plan-event-reconciliation",
        help="create a read-only historical event reconciliation plan",
    )
    plan_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    plan_parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    plan_parser.add_argument("--details", action="store_true")
    plan_parser.add_argument("--limit", type=_positive_integer)
    plan_parser.add_argument("--output-directory", type=Path, default=Path("reports"))
    apply_parser = subparsers.add_parser(
        "apply-event-reconciliation",
        help="atomically apply an explicit reconciliation plan",
    )
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument("--output-directory", type=Path, default=Path("reports"))
    canonical_parser = subparsers.add_parser(
        "canonicalize-events",
        help="complete deterministic canonical metadata for every event",
    )
    canonical_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    canonical_parser.add_argument(
        "--config", type=Path, default=Path("config/sources.yaml")
    )
    canonical_parser.add_argument("--dry-run", action="store_true")
    canonical_parser.add_argument(
        "--output-directory", type=Path, default=Path("reports")
    )
    verification_parser = subparsers.add_parser(
        "verify-event-candidates",
        help="advisory AI verification of deterministic event candidates",
    )
    verification_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    verification_parser.add_argument(
        "--config", type=Path, default=Path("config/config.yaml")
    )
    verification_parser.add_argument("--event-id", type=_positive_integer)
    verification_parser.add_argument("--limit", type=_positive_integer)
    verification_parser.add_argument("--details", action="store_true")
    verification_parser.add_argument(
        "--output-directory", type=Path, default=Path("reports")
    )
    verification_parser.add_argument(
        "--no-ai", action="store_true", help="use cache only; make no AI requests"
    )
    ranking_parser = subparsers.add_parser(
        "rank-events", help="rank recent canonical events for editorial review"
    )
    ranking_parser.add_argument(
        "--database", type=Path, default=Path("data/news_monitor.db")
    )
    ranking_parser.add_argument(
        "--config", type=Path, default=Path("config/config.yaml")
    )
    ranking_parser.add_argument("--days", type=_positive_integer, default=7)
    ranking_parser.add_argument("--limit", type=_positive_integer)
    ranking_parser.add_argument("--top", type=_positive_integer, default=10)
    ranking_parser.add_argument("--category", choices=CATEGORY_CHOICES, default="all")
    ranking_parser.add_argument("--minimum-score", type=_score_float, default=0.0)
    ranking_parser.add_argument("--details", action="store_true")
    ranking_parser.add_argument(
        "--output-directory", type=Path, default=Path("reports")
    )
    ranking_parser.add_argument("--no-ai", action="store_true")
    ranking_parser.add_argument("--force-refresh", action="store_true")
    contract_validate_parser = subparsers.add_parser(
        "validate-contract", help="validate a local Scout or Editor contract"
    )
    contract_validate_parser.add_argument("path", type=Path, metavar="PATH")
    contract_validate_parser.add_argument(
        "--source-input",
        type=Path,
        help="Scout input used for cross-validating an Editor output",
    )
    contract_validate_parser.add_argument(
        "--selection-profile", type=Path, help="selection profile linkage to verify"
    )
    contract_validate_parser.add_argument(
        "--episode-context", type=Path, help="episode context linkage to verify"
    )
    contract_export_parser = subparsers.add_parser(
        "export-contract", help="validate and write canonical contract JSON"
    )
    contract_export_parser.add_argument("path", type=Path, metavar="PATH")
    contract_export_parser.add_argument("--output", type=Path, required=True)
    artifacts_parser = subparsers.add_parser(
        "generate-contract-artifacts",
        help="generate frozen JSON Schemas and realistic sample contracts",
    )
    artifacts_parser.add_argument(
        "--output-directory", type=Path, default=Path("contracts")
    )
    editor_export_parser = subparsers.add_parser(
        "export-editor-input",
        help="construct a public Editor input from an internal Scout ranking report",
    )
    editor_export_parser.add_argument("ranking_report", type=Path, metavar="REPORT")
    editor_export_parser.add_argument("--output", type=Path, required=True)
    editor_export_parser.add_argument("--source-run-id", required=True)
    editor_export_parser.add_argument("--scout-version", required=True)
    editor_export_parser.add_argument("--ranking-schema-version", required=True)
    editor_export_parser.add_argument("--top", type=_positive_integer, required=True)
    editor_export_parser.add_argument(
        "--minimum-score", type=_score_float, required=True
    )
    limit_group = editor_export_parser.add_mutually_exclusive_group(required=True)
    limit_group.add_argument("--limit", type=_positive_integer)
    limit_group.add_argument("--no-limit", action="store_true")
    ai_group = editor_export_parser.add_mutually_exclusive_group(required=True)
    ai_group.add_argument("--ai-enabled", action="store_true")
    ai_group.add_argument("--no-ai", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    configure_unicode_console()
    arguments = build_parser().parse_args(argv)
    configure_logging(verbose=getattr(arguments, "verbose", False))

    if arguments.command == "validate-config":
        return _validate_config(arguments.config, arguments.timeout, arguments.category)
    if arguments.command == "status":
        return _show_status(arguments.database, arguments.limit)
    if arguments.command == "queue":
        return _show_queue(arguments.database, arguments.status, arguments.limit)
    if arguments.command == "review":
        return _review_queue_item(
            arguments.database,
            arguments.queue_id,
            arguments.decision,
            arguments.reviewer,
            arguments.notes,
        )
    if arguments.command == "queue-backfill":
        return _backfill_queue(arguments.database)
    if arguments.command == "events":
        return _show_events(
            arguments.database,
            arguments.limit,
            arguments.category,
            arguments.min_sources,
            arguments.hours,
        )
    if arguments.command == "audit-events":
        return _show_event_audit(
            arguments.database,
            details=arguments.details,
            limit=arguments.limit,
            output_path=arguments.output,
        )
    if arguments.command == "plan-event-reconciliation":
        return _plan_event_reconciliation(
            arguments.database,
            arguments.config,
            details=arguments.details,
            limit=arguments.limit,
            output_directory=arguments.output_directory,
        )
    if arguments.command == "apply-event-reconciliation":
        return _apply_event_reconciliation(
            arguments.plan,
            dry_run=arguments.dry_run,
            output_directory=arguments.output_directory,
        )
    if arguments.command == "canonicalize-events":
        return _canonicalize_events(
            arguments.database,
            arguments.config,
            dry_run=arguments.dry_run,
            output_directory=arguments.output_directory,
        )
    if arguments.command == "verify-event-candidates":
        return _verify_event_candidates(
            arguments.database,
            arguments.config,
            event_id=arguments.event_id,
            limit=arguments.limit,
            details=arguments.details,
            output_directory=arguments.output_directory,
            no_ai=arguments.no_ai,
        )
    if arguments.command == "rank-events":
        return _rank_events(
            arguments.database,
            arguments.config,
            days=arguments.days,
            limit=arguments.limit,
            top=arguments.top,
            category=arguments.category,
            minimum_score=arguments.minimum_score,
            details=arguments.details,
            output_directory=arguments.output_directory,
            no_ai=arguments.no_ai,
            force_refresh=arguments.force_refresh,
        )
    if arguments.command == "validate-contract":
        return _validate_contract(
            arguments.path,
            arguments.source_input,
            arguments.selection_profile,
            arguments.episode_context,
        )
    if arguments.command == "export-contract":
        return _export_contract(arguments.path, arguments.output)
    if arguments.command == "generate-contract-artifacts":
        return _generate_contract_artifacts(arguments.output_directory)
    if arguments.command == "export-editor-input":
        return _export_editor_input(
            arguments.ranking_report,
            arguments.output,
            source_run_id=arguments.source_run_id,
            scout_version=arguments.scout_version,
            ranking_schema_version=arguments.ranking_schema_version,
            limit=arguments.limit,
            top=arguments.top,
            minimum_score=arguments.minimum_score,
            ai_enabled=arguments.ai_enabled,
        )

    selected_days = _select_poll_days(arguments.days)

    try:
        result = poll_once(
            arguments.config,
            arguments.database,
            arguments.timeout,
            max_article_age_hours_override=float(selected_days * 24),
            category=arguments.category,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except (OSError, sqlite3.Error) as exc:
        print(f"Polling error: {exc}")
        return 2

    print(f"Category: {result.category}")
    print(f"Poll status: {result.status}")
    print(
        f"Sources: {result.sources_checked} checked, "
        f"{result.sources_succeeded} succeeded, {result.sources_failed} failed"
    )
    print(
        f"Articles: {result.articles_found} found, "
        f"{result.articles_inserted} inserted, "
        f"{result.duplicates_skipped} duplicates"
    )
    print(
        f"Filtered: {result.articles_filtered_old} old, "
        f"{result.articles_filtered_future} future, "
        f"{result.articles_filtered_undated} undated, "
        f"{result.articles_filtered_limit} over limit"
    )
    for failure in result.source_failures:
        print(f"Source failure: {failure}")
    if result.sources_checked == 0 and result.category != "all":
        print(f"No enabled sources matched category {result.category}.")
    return 1 if result.status == "failed" else 0


def _validate_contract(
    path: Path,
    source_input: Path | None,
    selection_profile_path: Path | None,
    episode_context_path: Path | None,
) -> int:
    """Validate a public contract and optional Editor-to-Scout linkage."""

    try:
        contract = load_contract(path)
        if any(
            value is not None
            for value in (
                source_input,
                selection_profile_path,
                episode_context_path,
            )
        ):
            if source_input is None:
                raise ContractFileError("linked validation requires --source-input")
            source = load_contract(source_input)
            if not isinstance(contract, EditorAgentOutputV1):
                raise ContractFileError("--source-input requires an Editor output")
            if not isinstance(source, ScoutEditorInputV1):
                raise ContractFileError("--source-input must be a Scout input contract")
            profile = (
                load_contract(selection_profile_path)
                if selection_profile_path is not None
                else None
            )
            context = (
                load_contract(episode_context_path)
                if episode_context_path is not None
                else None
            )
            if profile is not None and not isinstance(profile, SelectionProfileV1):
                raise ContractFileError(
                    "--selection-profile has the wrong contract type"
                )
            if context is not None and not isinstance(context, EpisodeContextV1):
                raise ContractFileError("--episode-context has the wrong contract type")
            validate_editor_output_against_input(
                contract,
                source,
                selection_profile=profile,
                episode_context=context,
            )
    except (OSError, ValueError) as exc:
        print(f"Contract validation error: {exc}")
        return 2
    print(f"Contract valid: {contract.contract_version}")
    print(f"Path: {path.resolve()}")
    if source_input is not None:
        print("Source linkage: valid")
    if selection_profile_path is not None:
        print("Selection profile linkage: valid")
    if episode_context_path is not None:
        print("Episode context linkage: valid")
    return 0


def _export_contract(path: Path, output_path: Path) -> int:
    """Import a valid contract and atomically export canonical JSON."""

    try:
        contract = load_contract(path)
        written = write_contract(contract, output_path)
    except (OSError, ValueError) as exc:
        print(f"Contract export error: {exc}")
        return 2
    print(f"Contract exported: {written}")
    return 0


def _generate_contract_artifacts(output_directory: Path) -> int:
    """Generate schemas and samples without invoking editorial logic."""

    try:
        schema_paths = write_json_schemas(output_directory / "schemas")
        sample_paths = write_sample_contracts(output_directory / "samples")
    except (OSError, ValueError) as exc:
        print(f"Contract artifact error: {exc}")
        return 2
    print(f"JSON Schemas generated: {len(schema_paths)}")
    print(f"Sample contracts generated: {len(sample_paths)}")
    print(f"Output directory: {output_directory.resolve()}")
    return 0


def _export_editor_input(
    ranking_report_path: Path,
    output_path: Path,
    *,
    source_run_id: str,
    scout_version: str,
    ranking_schema_version: str,
    limit: int | None,
    top: int,
    minimum_score: float,
    ai_enabled: bool,
) -> int:
    """Load a private ranking artifact and export the frozen public boundary."""

    try:
        if not ranking_report_path.is_file() or ranking_report_path.is_symlink():
            raise ValueError("ranking report must be a regular local file")
        if ranking_report_path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError("ranking report exceeds the 25 MiB limit")
        report_text = ranking_report_path.read_text(encoding="utf-8")
        report = EventRankingReport.model_validate_json(report_text)
        context = EditorInputExportContext(
            source_run_id=source_run_id,
            scout_version=scout_version,
            ranking_schema_version=ranking_schema_version,
            limit=limit,
            top=top,
            minimum_score=minimum_score,
            ai_enabled=ai_enabled,
        )
        contract = export_editor_input(report, context)
        written = write_contract(contract, output_path)
    except (OSError, ValueError) as exc:
        print(f"Editor input export error: {exc}")
        return 2
    print(f"Editor input exported: {written}")
    print(f"Report ID: {contract.report_id}")
    print(f"Events exported: {contract.event_counts.reported}")
    return 0


def _select_poll_days(days: int | None) -> int:
    """Resolve explicit, interactive, or automation-safe polling days."""

    if days is not None:
        return days
    if not sys.stdin.isatty():
        return 7

    choices = {"1": 1, "2": 3, "3": 7, "4": 14, "5": 30}
    menu = (
        "Select maximum article age:\n\n"
        "1) 1 day\n"
        "2) 3 days\n"
        "3) 7 days (default)\n"
        "4) 14 days\n"
        "5) 30 days\n"
    )
    while True:
        print(menu)
        selection = input("Press Enter for default (7 days): ").strip()
        if not selection:
            return 7
        if selection in choices:
            return choices[selection]
        print("Invalid selection; choose 1, 2, 3, 4, or 5.")


def _validate_config(config_path: Path, timeout: float, category: str = "all") -> int:
    """Validate configuration and fetch each enabled source without persistence."""

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2

    matching_sources = [
        source
        for source in config.sources
        if category == "all" or category in source.categories
    ]
    enabled_sources = [source for source in config.sources if source.enabled]
    selected_sources = [source for source in matching_sources if source.enabled]
    disabled_sources = [source for source in matching_sources if not source.enabled]
    print(f"Category: {category}")
    print(f"Configured sources: {len(config.sources)}")
    print(f"Enabled sources: {len(enabled_sources)}")
    print(f"Selected sources: {len(selected_sources)}")
    failures: list[str] = []
    validation_results: list[tuple[int, SourceConfig, int, Exception | None]] = []

    if selected_sources:
        with HTTPClient(timeout=timeout) as client, ThreadPoolExecutor(
            max_workers=config.polling.concurrency,
            thread_name_prefix="pastila-validation",
        ) as executor:
            futures = {
                executor.submit(_validate_source, index, source, client): index
                for index, source in enumerate(selected_sources)
            }
            for future in as_completed(futures):
                validation_results.append(future.result())

    validation_results.sort(key=lambda result: result[0])
    for _, source, candidate_count, error in validation_results:
        if error is None:
            print(f"Source {source.id}: ok ({candidate_count} candidates)")
        else:
            failure = f"{source.id}: {error}"
            failures.append(failure)
            print(f"Source {source.id}: failed ({error})")

    for source in disabled_sources:
        reason = source.disabled_reason or "disabled in configuration"
        print(f"Source {source.id}: disabled ({reason})")

    succeeded = len(selected_sources) - len(failures)
    status = "success" if not failures else "failed"
    print(
        f"Validation status: {status}; {succeeded} succeeded, "
        f"{len(failures)} failed, {len(disabled_sources)} disabled"
    )
    return 0 if not failures else 1


def _validate_source(
    index: int, source: SourceConfig, client: HTTPClient
) -> tuple[int, SourceConfig, int, Exception | None]:
    """Validate one source in a worker without persistence."""

    try:
        candidates = get_adapter(source.type).fetch(source, client)
        if not candidates:
            raise ValueError("no valid article candidates produced")
        return index, source, len(candidates), None
    except Exception as exc:  # noqa: BLE001 - isolate failures from individual sources
        return index, source, 0, exc


def _show_status(database_path: Path, limit: int) -> int:
    """Print aggregate and recent state from an existing Scout database."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 0

    try:
        with open_database(database_path) as connection:
            total_sources, enabled_sources = get_source_counts(connection)
            article_count = get_article_count(connection)
            poll_run_count = get_poll_run_count(connection)
            latest_run = get_latest_poll_run(connection)
            articles = get_latest_articles(connection, limit)
            try:
                queue_counts = get_queue_counts(connection)
            except sqlite3.OperationalError:
                queue_counts = {
                    "pending": 0,
                    "claimed": 0,
                    "reviewed": 0,
                    "rejected": 0,
                }
    except sqlite3.Error:
        print(f"Database is not initialized: {database_path}")
        return 0

    print(f"Sources: {total_sources} total, {enabled_sources} enabled")
    print(f"Articles: {article_count}")
    print(f"Poll runs: {poll_run_count}")
    print(
        f"Editorial queue: {sum(queue_counts.values())} total, "
        f"{queue_counts['pending']} pending, {queue_counts['claimed']} claimed, "
        f"{queue_counts['reviewed']} reviewed, {queue_counts['rejected']} rejected"
    )
    if latest_run is None:
        print("Latest poll run: none")
    else:
        timestamp = latest_run["finished_at"] or latest_run["started_at"]
        print(f"Latest poll run: {latest_run['status']} at {timestamp}")

    print("Latest articles:")
    if not articles:
        print("  none")
    for article in articles:
        published = article["published_at"] or "unknown date"
        url = article["normalized_url"] or article["url"]
        print(
            f"  {article['source_id']} | {published} | " f"{article['title']} | {url}"
        )
    return 0


def _show_queue(database_path: Path, status: str, limit: int) -> int:
    """Print queue counts and matching items in editorial order."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2
    try:
        with open_database(database_path) as connection:
            initialize_database(connection)
            counts = get_queue_counts(connection)
            items = list_queue_items(connection, status=status, limit=limit)
    except (sqlite3.Error, ValueError) as exc:
        print(f"Queue error: {exc}")
        return 2

    print(
        f"Queue counts: {counts['pending']} pending, {counts['claimed']} claimed, "
        f"{counts['reviewed']} reviewed, {counts['rejected']} rejected"
    )
    print(f"Queue items ({status}):")
    if not items:
        print("  none")
    for item in items:
        published = item["published_at"] or "unknown date"
        url = item["normalized_url"] or item["url"]
        print(
            f"  #{item['queue_id']} article={item['article_id']} "
            f"priority={item['priority']} status={item['status']} | "
            f"{item['source_id']} | {published} | {item['title']} | {url}"
        )
    return 0


def _review_queue_item(
    database_path: Path,
    queue_id: int,
    decision: str,
    reviewer: str | None,
    notes: str | None,
) -> int:
    """Record one non-interactive editorial decision."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2
    try:
        with open_database(database_path) as connection:
            initialize_database(connection)
            review_queue_item(
                connection,
                queue_id,
                decision,
                reviewer=reviewer,
                notes=notes,
            )
    except (sqlite3.Error, QueueStateError, ValueError) as exc:
        print(f"Review error: {exc}")
        return 2

    print(f"Queue item {queue_id}: decision {decision} recorded")
    return 0


def _backfill_queue(database_path: Path) -> int:
    """Create missing queue rows for articles in an existing database."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2
    try:
        with open_database(database_path) as connection:
            initialize_database(connection)
            created = backfill_editorial_queue(connection)
    except sqlite3.Error as exc:
        print(f"Queue backfill error: {exc}")
        return 2

    print(f"Editorial queue rows created: {created}")
    return 0


def _positive_integer(value: str) -> int:
    """Parse a positive integer for argparse."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    """Parse a positive floating-point number for argparse."""

    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return parsed


def _score_float(value: str) -> float:
    """Parse an inclusive 0-100 score."""

    parsed = float(value)
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return parsed


def _show_events(
    database_path: Path,
    limit: int,
    category: str,
    min_sources: int,
    hours: float,
) -> int:
    """Print recent events with complete source provenance."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with open_database(database_path) as connection:
            initialize_database(connection)
            events = list_recent_events(
                connection,
                cutoff=cutoff,
                limit=limit,
                min_sources=min_sources,
                category=None if category == "all" else category,
            )
            event_sources = {
                int(event["id"]): get_event_sources(connection, int(event["id"]))
                for event in events
            }
    except (sqlite3.Error, ValueError) as exc:
        print(f"Events error: {exc}")
        return 2

    print(f"Recent events ({category}, last {hours:g} hours):")
    if not events:
        print("  none")
        return 0
    for position, event in enumerate(events, start=1):
        print(f"{position}. {event['canonical_title']}")
        print(
            f"   Sources: {event['source_count']} | Articles: {event['article_count']}"
        )
        print("   Confirmed by:")
        for source in event_sources[int(event["id"])]:
            print(f"   - {source['name']}")
        print(f"   First seen: {event['first_seen_at']}")
        print(f"   Last seen: {event['last_seen_at']}")
    return 0


def _show_event_audit(
    database_path: Path,
    *,
    details: bool,
    limit: int | None,
    output_path: Path | None,
) -> int:
    """Invoke the read-only event audit and present grouped findings."""

    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2
    try:
        with open_database_readonly(database_path) as connection:
            snapshot = load_event_integrity_snapshot(connection)
        report = audit_event_integrity(snapshot)
        report_path = write_event_audit_report(
            report,
            snapshot,
            database_path=database_path,
            output_path=output_path,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Event audit error: {exc}")
        return 2

    exit_code = 1 if report.errors else 0
    print(f"Database: {database_path}")
    print(f"Articles checked: {report.article_count}")
    print(f"Events checked: {report.event_count}")
    print(f"Structural errors: {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    print("Finding category counts:")
    counts = [
        (f"structural/{code}", count)
        for code, count in category_counts(
            report.errors, categories=STRUCTURAL_FINDING_CATEGORIES
        )
    ] + [
        (f"warning/{code}", count)
        for code, count in category_counts(
            report.warnings, categories=WARNING_FINDING_CATEGORIES
        )
    ]
    if not counts:
        print("  none")
    for code, count in counts:
        print(f"  {code}: {count}")
    print(f"Historical match proposals: {len(report.historical_matches)}")
    print(
        f"Exit code: {exit_code} "
        f"({'structural errors detected' if exit_code else 'no structural errors; warnings are non-blocking'})"
    )
    print(f"Detailed report: {report_path}")
    if details or limit is not None:
        for line in render_console_details(report, snapshot, limit=limit):
            print(line)
    return exit_code


def _plan_event_reconciliation(
    database_path: Path,
    config_path: Path,
    *,
    details: bool,
    limit: int | None,
    output_directory: Path,
) -> int:
    """Invoke read-only planning and present compact plan metadata."""

    try:
        config = load_config(config_path)
        source_metadata = {
            source.id: (
                tuple(category.value for category in source.categories),
                source.priority,
            )
            for source in config.sources
        }
        with open_database_readonly(database_path) as connection:
            snapshot = load_reconciliation_snapshot(connection, source_metadata)
        plan = build_reconciliation_plan(
            snapshot,
            database_path=str(database_path.resolve()),
            similarity_threshold=config.event_matching.similarity_threshold,
            lookback_hours=config.event_matching.lookback_hours,
        )
        json_path, text_path = write_reconciliation_plan(plan, output_directory)
    except (ConfigError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"Reconciliation planning error: {exc}")
        return 2

    print(f"Database: {database_path}")
    print(f"Events checked: {len(snapshot.events)}")
    print(f"Articles checked: {len(snapshot.articles)}")
    print(f"Safe proposals: {len(plan.proposals)}")
    print(f"Ambiguous groups: {len(plan.ambiguous_groups)}")
    print(f"JSON plan: {json_path}")
    print(f"Text report: {text_path}")
    if details or limit is not None:
        for line in render_proposal_console(plan.proposals, limit=limit):
            print(line)
    return 0


def _apply_event_reconciliation(
    plan_path: Path,
    *,
    dry_run: bool,
    output_directory: Path,
) -> int:
    """Validate and invoke atomic application of an explicit JSON plan."""

    timestamp = datetime.now(UTC).isoformat()
    plan: EventReconciliationPlan | None = None
    survivors: tuple[int, ...] = ()
    merged: tuple[int, ...] = ()
    status = "failed"
    message = "Plan could not be loaded"
    try:
        plan = EventReconciliationPlan.model_validate_json(
            plan_path.read_text(encoding="utf-8")
        )
        database_path = Path(plan.database_path)
        with open_database(database_path) as connection:
            survivors, merged = apply_reconciliation_plan(
                connection, plan, dry_run=dry_run
            )
        status = "dry-run" if dry_run else "success"
        message = (
            "Plan validated; no database changes were made."
            if dry_run
            else "Plan applied atomically."
        )
    except (OSError, sqlite3.Error, StaleReconciliationPlanError, ValueError) as exc:
        database_path = Path(plan.database_path) if plan else Path("unknown")
        message = str(exc)

    report = ReconciliationApplicationReport(
        generated_at=timestamp,
        database_path=str(database_path),
        plan_path=str(plan_path),
        dry_run=dry_run,
        status=status,
        proposals_validated=len(plan.proposals) if plan and status != "failed" else 0,
        proposals_applied=len(survivors),
        surviving_event_ids=survivors,
        merged_event_ids=merged,
        message=message,
    )
    try:
        json_path, text_path = write_application_report(report, output_directory)
    except OSError as exc:
        print(f"Reconciliation application report error: {exc}")
        return 2
    print(f"Application status: {status}")
    print(f"Message: {message}")
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 0 if status in {"success", "dry-run"} else 1


def _canonicalize_events(
    database_path: Path,
    config_path: Path,
    *,
    dry_run: bool,
    output_directory: Path,
) -> int:
    """Invoke atomic deterministic event metadata completion."""

    try:
        config = load_config(config_path)
        source_metadata = {
            source.id: (
                tuple(category.value for category in source.categories),
                source.priority,
            )
            for source in config.sources
        }
        with open_database(database_path) as connection:
            report = canonicalize_all_events(
                connection,
                database_path=str(database_path.resolve()),
                source_metadata=source_metadata,
                similarity_threshold=config.event_matching.similarity_threshold,
                lookback_hours=config.event_matching.lookback_hours,
                dry_run=dry_run,
            )
        json_path, text_path = write_canonicalization_report(report, output_directory)
    except (ConfigError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"Event canonicalization error: {exc}")
        return 2
    print(f"Database: {database_path}")
    print(f"Dry run: {dry_run}")
    print(f"Events checked: {report.events_checked}")
    print(f"Events changed: {report.events_changed}")
    print(f"Categories added: {report.categories_added}")
    print(f"Canonical titles changed: {report.canonical_titles_changed}")
    print(f"Canonical summaries changed: {report.canonical_summaries_changed}")
    print(f"Unresolved categories: {report.unresolved_categories}")
    print(f"Unchanged events: {report.unchanged_events}")
    print(
        "Remaining historical matches (diagnostic only): "
        f"{report.remaining_historical_matches}"
    )
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 0


def _verify_event_candidates(
    database_path: Path,
    config_path: Path,
    *,
    event_id: int | None,
    limit: int | None,
    details: bool,
    output_directory: Path,
    no_ai: bool,
) -> int:
    """Wire read-only candidate loading to the provider-neutral verifier."""

    try:
        config = load_configuration(config_path)
        ai_config = (
            config.ai.model_copy(update={"enable_ai": False}) if no_ai else config.ai
        )
        source_metadata = {
            source.id: (
                tuple(category.value for category in source.categories),
                source.priority,
            )
            for source in config.sources
        }
        with open_database_readonly(database_path) as connection:
            snapshot = load_reconciliation_snapshot(connection, source_metadata)
        requests = build_verification_requests(
            snapshot,
            similarity_threshold=config.event_matching.similarity_threshold,
            lookback_hours=config.event_matching.lookback_hours,
            event_id=event_id,
        )
        api_key = resolve_openai_api_key()
        provider = None
        if ai_config.enable_ai and api_key:
            provider = OpenAIProvider(ai_config, api_key)
        verifier = EventVerifier(
            ai_config,
            FileVerificationCache(config.cache.ai_verification_directory),
            provider,
            api_key_available=bool(api_key),
            input_cost_per_million_tokens=(
                config.scoring.input_cost_per_million_tokens
            ),
            output_cost_per_million_tokens=(
                config.scoring.output_cost_per_million_tokens
            ),
        )
        report = run_event_verification(
            requests,
            verifier,
            database_path=str(database_path.resolve()),
            limit=limit,
        )
        json_path, text_path = write_verification_reports(report, output_directory)
    except (ConfigError, OSError, sqlite3.Error, ProviderError, ValueError) as exc:
        print(f"Event verification error: {exc}")
        return 2

    print(f"Database: {database_path}")
    for line in render_verification_console(report, details=details):
        print(line)
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 0


def _rank_events(
    database_path: Path,
    config_path: Path,
    *,
    days: int,
    limit: int | None,
    top: int,
    category: str,
    minimum_score: float,
    details: bool,
    output_directory: Path,
    no_ai: bool,
    force_refresh: bool,
) -> int:
    """Rank canonical events while enforcing read-only database access."""

    try:
        config = load_configuration(config_path)
        ai_config = (
            config.ai.model_copy(update={"enable_ai": False}) if no_ai else config.ai
        )
        source_metadata = {
            source.id: (
                tuple(category.value for category in source.categories),
                source.priority,
            )
            for source in config.sources
        }
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with open_database_readonly(database_path) as connection:
            event_ids = list_event_ids_for_ranking(
                connection,
                cutoff=cutoff,
                category=None if category == "all" else category,
            )
            snapshots = tuple(
                load_event_snapshot(connection, event_id, source_metadata)
                for event_id in event_ids
            )
        api_key = resolve_openai_api_key()
        provider = None
        if ai_config.enable_ai and api_key:
            provider = OpenAIProvider(ai_config, api_key)
        scorer = EditorialEventScorer(
            ai_config,
            config.scoring,
            FileJSONCache(config.cache.ai_editorial_directory),
            provider,
            api_key_available=bool(api_key),
            force_refresh=force_refresh,
        )
        report = rank_event_snapshots(
            snapshots,
            scorer,
            config.scoring,
            database_path=str(database_path.resolve()),
            days=days,
            category=category,
            limit=limit,
            top=top,
            minimum_score=minimum_score,
        )
        json_path, text_path = write_ranking_reports(report, output_directory)
    except (ConfigError, OSError, sqlite3.Error, ProviderError, ValueError) as exc:
        print(f"Event ranking error: {exc}")
        return 2

    print(f"Database: {database_path}")
    for line in render_ranking(report, details=details):
        print(line)
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
