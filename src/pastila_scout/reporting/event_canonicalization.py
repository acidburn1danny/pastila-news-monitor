"""UTF-8 reports for deterministic event canonicalization."""

from datetime import datetime
from pathlib import Path

from pastila_scout.models import EventCanonicalizationReport


def write_canonicalization_report(
    report: EventCanonicalizationReport, output_directory: Path
) -> tuple[Path, Path]:
    """Write complete JSON and human-readable canonicalization reports."""

    stamp = datetime.fromisoformat(report.generated_at).strftime("%Y-%m-%d_%H%M%S")
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"event_canonicalization_{stamp}"
    json_path = output_directory / f"{stem}.json"
    text_path = output_directory / f"{stem}.txt"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    lines = [
        "Pastila Scout event canonicalization report",
        f"Generated at: {report.generated_at}",
        f"Database: {report.database_path}",
        f"Dry run: {report.dry_run}",
        f"Events checked: {report.events_checked}",
        f"Events changed: {report.events_changed}",
        f"Categories added: {report.categories_added}",
        f"Canonical titles changed: {report.canonical_titles_changed}",
        f"Canonical summaries changed: {report.canonical_summaries_changed}",
        f"Unresolved categories: {report.unresolved_categories}",
        f"Unchanged events: {report.unchanged_events}",
        f"Remaining historical matches: {report.remaining_historical_matches}",
        "Remaining match groups: "
        + ", ".join(
            "[" + ", ".join(map(str, group)) + "]"
            for group in report.remaining_historical_event_groups
        ),
        "",
        "Event changes:",
    ]
    for change in sorted(report.changes, key=lambda item: item.event_id):
        lines.extend(
            (
                f"  Event {change.event_id}: changed={change.changed}",
                f"    Categories: {change.categories_before} -> {change.categories_after}",
                f"    Title changed: {change.title_changed}",
                f"    Summary changed: {change.summary_changed}",
                f"    Canonical title: {change.canonical_title}",
                f"    Canonical summary: {change.canonical_summary or 'none'}",
                (
                    f"    Publication range: {change.first_publication_at} -> "
                    f"{change.last_publication_at}"
                ),
                f"    Canonical article: {change.canonical_article_id}",
                f"    Selection reason: {change.selection_reason}",
            )
        )
    text_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, text_path
