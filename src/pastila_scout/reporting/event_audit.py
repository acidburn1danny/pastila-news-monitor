"""Rendering and UTF-8 file output for event integrity audits."""

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from pastila_scout.models import (
    AuditArticle,
    EventIntegrityFinding,
    EventIntegrityReport,
    EventIntegritySnapshot,
    HistoricalMatchProposal,
)

STRUCTURAL_FINDING_CATEGORIES = (
    "article_count_mismatch",
    "event_without_articles",
    "invalid_event_reference",
    "source_count_mismatch",
)
WARNING_FINDING_CATEGORIES = (
    "likely_historical_match",
    "missing_event_category",
    "missing_event_summary",
    "single_article_event",
    "unassigned_article",
)


def default_audit_report_path(now: datetime | None = None) -> Path:
    """Return the timestamped default path for a detailed audit report."""

    timestamp = now or datetime.now().astimezone()
    return Path("reports") / f"event_audit_{timestamp:%Y-%m-%d_%H%M%S}.txt"


def write_event_audit_report(
    report: EventIntegrityReport,
    snapshot: EventIntegritySnapshot,
    *,
    database_path: Path,
    output_path: Path | None = None,
    generated_at: datetime | None = None,
) -> Path:
    """Write every audit detail as UTF-8 and return the resulting path."""

    timestamp = generated_at or datetime.now().astimezone()
    destination = output_path or default_audit_report_path(timestamp)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_detailed_report(
            report,
            snapshot,
            database_path=database_path,
            generated_at=timestamp,
        ),
        encoding="utf-8",
    )
    return destination


def render_detailed_report(
    report: EventIntegrityReport,
    snapshot: EventIntegritySnapshot,
    *,
    database_path: Path,
    generated_at: datetime,
) -> str:
    """Render complete, deterministically sorted audit information."""

    lines = [
        "Pastila Scout event integrity audit",
        f"Generated at: {generated_at.isoformat()}",
        f"Database: {database_path}",
        f"Articles checked: {report.article_count}",
        f"Events checked: {report.event_count}",
        f"Structural errors: {len(report.errors)}",
        f"Warnings: {len(report.warnings)}",
        f"Historical match proposals: {len(report.historical_matches)}",
        "",
    ]
    lines.extend(
        _render_finding_section("Structural findings", report.errors, snapshot)
    )
    lines.extend(_render_finding_section("Warnings", report.warnings, snapshot))
    lines.extend(_render_proposal_section(report.historical_matches, snapshot))
    return "\n".join(lines).rstrip() + "\n"


def category_counts(
    findings: tuple[EventIntegrityFinding, ...],
    *,
    categories: tuple[str, ...] = (),
) -> list[tuple[str, int]]:
    """Return deterministic finding-category counts."""

    counts = Counter(finding.code for finding in findings)
    return [(code, counts[code]) for code in sorted(set(categories) | counts.keys())]


def render_console_details(
    report: EventIntegrityReport,
    snapshot: EventIntegritySnapshot,
    *,
    limit: int | None = None,
) -> list[str]:
    """Render sorted findings for optional console detail output."""

    lines: list[str] = []
    lines.extend(
        _render_finding_section(
            "Structural findings", report.errors, snapshot, limit=limit
        )
    )
    lines.extend(
        _render_finding_section("Warnings", report.warnings, snapshot, limit=limit)
    )
    lines.extend(
        _render_proposal_section(report.historical_matches, snapshot, limit=limit)
    )
    return lines


def sorted_findings(
    findings: tuple[EventIntegrityFinding, ...],
) -> list[EventIntegrityFinding]:
    """Sort by category and then stable entity identifiers."""

    return sorted(
        findings,
        key=lambda finding: (
            finding.code,
            finding.event_id if finding.event_id is not None else 2**63,
            finding.article_id if finding.article_id is not None else 2**63,
        ),
    )


def sorted_proposals(
    proposals: tuple[HistoricalMatchProposal, ...],
) -> list[HistoricalMatchProposal]:
    """Sort proposals by confidence descending and event IDs ascending."""

    return sorted(
        proposals,
        key=lambda proposal: (
            -proposal.score,
            proposal.event_id,
            proposal.related_event_id,
        ),
    )


def _render_finding_section(
    heading: str,
    findings: tuple[EventIntegrityFinding, ...],
    snapshot: EventIntegritySnapshot,
    *,
    limit: int | None = None,
) -> list[str]:
    """Render findings grouped by category with an optional per-group limit."""

    lines = [f"{heading}:"]
    if not findings:
        return lines + ["  none", ""]
    grouped: dict[str, list[EventIntegrityFinding]] = defaultdict(list)
    for finding in sorted_findings(findings):
        grouped[finding.code].append(finding)
    for code, matching in grouped.items():
        lines.append(f"  {code} ({len(matching)}):")
        selected = matching if limit is None else matching[:limit]
        for finding in selected:
            lines.append(f"    - {_finding_detail(finding, snapshot)}")
        if limit is not None and len(matching) > limit:
            lines.append(f"    ... {len(matching) - limit} more in detailed report")
    lines.append("")
    return lines


def _render_proposal_section(
    proposals: tuple[HistoricalMatchProposal, ...],
    snapshot: EventIntegritySnapshot,
    *,
    limit: int | None = None,
) -> list[str]:
    """Render historical proposals with titles, scores, dates, and sources."""

    lines = ["Historical match proposals:"]
    if not proposals:
        return lines + ["  none", ""]
    ordered = sorted_proposals(proposals)
    selected = ordered if limit is None else ordered[:limit]
    events = {event.id: event for event in snapshot.events}
    by_event = _articles_by_event(snapshot)
    for proposal in selected:
        left = events.get(proposal.event_id)
        right = events.get(proposal.related_event_id)
        lines.append(
            "  - "
            f"score={proposal.score:.4f}; event_id={proposal.event_id}; "
            f"title={left.canonical_title!r}; "
            f"sources={_source_list(by_event[proposal.event_id])}; "
            f"published={_publication_list(by_event[proposal.event_id])}; "
            f"related_event_id={proposal.related_event_id}; "
            f"related_title={right.canonical_title!r}; "
            f"related_sources={_source_list(by_event[proposal.related_event_id])}; "
            f"related_published={_publication_list(by_event[proposal.related_event_id])}"
        )
    if limit is not None and len(ordered) > limit:
        lines.append(f"  ... {len(ordered) - limit} more in detailed report")
    lines.append("")
    return lines


def _finding_detail(
    finding: EventIntegrityFinding, snapshot: EventIntegritySnapshot
) -> str:
    """Enrich a finding with available event and article provenance."""

    events = {event.id: event for event in snapshot.events}
    articles = {article.id: article for article in snapshot.articles}
    parts = [finding.message]
    if finding.event_id is not None:
        parts.append(f"event_id={finding.event_id}")
        event = events.get(finding.event_id)
        if event is not None:
            parts.append(f"canonical_title={event.canonical_title!r}")
            event_articles = _articles_by_event(snapshot)[finding.event_id]
            parts.append(f"sources={_source_list(event_articles)}")
            parts.append(f"published={_publication_list(event_articles)}")
    if finding.article_id is not None:
        parts.append(f"article_id={finding.article_id}")
        article = articles.get(finding.article_id)
        if article is not None:
            parts.extend(
                (
                    f"article_title={article.title!r}",
                    f"source_id={article.source_id}",
                    f"source_name={article.source_name or 'unknown'}",
                    f"published_at={article.published_at or 'unknown'}",
                )
            )
    return "; ".join(parts)


def _articles_by_event(
    snapshot: EventIntegritySnapshot,
) -> dict[int, list[AuditArticle]]:
    """Group assigned audit articles for provenance rendering."""

    grouped: dict[int, list[AuditArticle]] = defaultdict(list)
    for article in snapshot.articles:
        if article.event_id is not None:
            grouped[article.event_id].append(article)
    return grouped


def _source_list(articles: list[AuditArticle]) -> str:
    """Render distinct source IDs in stable order."""

    sources = {
        (
            f"{article.source_name} ({article.source_id})"
            if article.source_name
            else article.source_id
        )
        for article in articles
    }
    return ", ".join(sorted(sources)) or "unknown"


def _publication_list(articles: list[AuditArticle]) -> str:
    """Render available publication dates in stable order."""

    dates = sorted(
        {article.published_at for article in articles if article.published_at}
    )
    return ", ".join(dates) or "unknown"
