"""UTF-8 serialization for reconciliation plans and application reports."""

from datetime import datetime
from pathlib import Path

from pastila_scout.models import (
    EventReconciliationPlan,
    ReconciliationApplicationReport,
    ReconciliationProposal,
)


def write_reconciliation_plan(
    plan: EventReconciliationPlan, output_directory: Path
) -> tuple[Path, Path]:
    """Write complete deterministic JSON and text plan artifacts."""

    stamp = datetime.fromisoformat(plan.generated_at).strftime("%Y-%m-%d_%H%M%S")
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / f"event_reconciliation_{stamp}.json"
    text_path = output_directory / f"event_reconciliation_{stamp}.txt"
    json_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    text_path.write_text(render_reconciliation_plan(plan), encoding="utf-8")
    return json_path, text_path


def render_reconciliation_plan(plan: EventReconciliationPlan) -> str:
    """Render every proposal and ambiguity in human-readable form."""

    lines = [
        "Pastila Scout historical event reconciliation plan",
        f"Generated at: {plan.generated_at}",
        f"Database: {plan.database_path}",
        f"Similarity threshold: {plan.similarity_threshold}",
        f"Lookback hours: {plan.lookback_hours}",
        f"Safe proposals: {len(plan.proposals)}",
        f"Ambiguous groups: {len(plan.ambiguous_groups)}",
        "",
        "Safe proposals:",
    ]
    if not plan.proposals:
        lines.append("  none")
    for index, proposal in enumerate(plan.proposals, 1):
        lines.extend(_proposal_lines(index, proposal))
    lines.extend(("", "Ambiguous or conflicting groups:"))
    if not plan.ambiguous_groups:
        lines.append("  none")
    for group in plan.ambiguous_groups:
        lines.append(f"  Events: {', '.join(map(str, group.event_ids))}")
        lines.append(f"  Reason: {group.reason}")
        lines.append(
            "  Matching pairs: "
            + ", ".join(
                f"{pair.event_id}-{pair.related_event_id}={pair.score:.4f}"
                for pair in group.matching_pairs
            )
        )
        lines.append(
            "  Rejected pairs: "
            + ", ".join(
                f"{pair.event_id}-{pair.related_event_id}={pair.score:.4f}"
                for pair in group.rejected_pairs
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def render_proposal_console(
    proposals: tuple[ReconciliationProposal, ...], limit: int | None = None
) -> list[str]:
    """Render optional compact proposal details for the console."""

    selected = proposals if limit is None else proposals[:limit]
    lines: list[str] = []
    for index, proposal in enumerate(selected, 1):
        lines.extend(_proposal_lines(index, proposal))
    if limit is not None and len(proposals) > limit:
        lines.append(f"... {len(proposals) - limit} more proposals in plan reports")
    return lines


def write_application_report(
    report: ReconciliationApplicationReport, output_directory: Path
) -> tuple[Path, Path]:
    """Write complete application outcome in JSON and UTF-8 text."""

    stamp = datetime.fromisoformat(report.generated_at).strftime("%Y-%m-%d_%H%M%S")
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"event_reconciliation_application_{stamp}"
    json_path = output_directory / f"{stem}.json"
    text_path = output_directory / f"{stem}.txt"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    text_path.write_text(
        "\n".join(
            (
                "Pastila Scout reconciliation application report",
                f"Generated at: {report.generated_at}",
                f"Database: {report.database_path}",
                f"Plan: {report.plan_path}",
                f"Dry run: {report.dry_run}",
                f"Status: {report.status}",
                f"Proposals validated: {report.proposals_validated}",
                f"Proposals applied: {report.proposals_applied}",
                f"Surviving events: {report.surviving_event_ids}",
                f"Merged events: {report.merged_event_ids}",
                f"Message: {report.message}",
                "",
            )
        ),
        encoding="utf-8",
    )
    return json_path, text_path


def _proposal_lines(index: int, proposal: ReconciliationProposal) -> list[str]:
    """Render all required fields for one proposal."""

    return [
        f"  {index}. Events: {', '.join(map(str, proposal.event_ids))}",
        f"     Articles: {', '.join(map(str, proposal.article_ids))}",
        f"     Titles: {' | '.join(proposal.canonical_titles)}",
        f"     Publication range: {proposal.publication_start} -> {proposal.publication_end}",
        f"     Sources: {', '.join(proposal.sources)}",
        f"     Source IDs: {', '.join(proposal.source_ids)}",
        f"     Current categories: {', '.join(proposal.current_categories) or 'none'}",
        f"     Proposed categories: {', '.join(proposal.proposed_categories) or 'unresolved'}",
        "     Pairwise scores: "
        + ", ".join(
            f"{pair.event_id}-{pair.related_event_id}={pair.score:.4f}"
            for pair in proposal.pairwise_similarities
        ),
        f"     Surviving event: {proposal.surviving_event_id}",
        (
            f"     Result: {proposal.resulting_article_count} articles, "
            f"{proposal.resulting_source_count} distinct sources"
        ),
        f"     Canonical article: {proposal.canonical_selection.article_id}",
        f"     Canonical title: {proposal.canonical_selection.title}",
        f"     Canonical summary: {proposal.canonical_selection.summary or 'none'}",
        f"     Canonical reason: {proposal.canonical_selection.reason}",
        f"     Proposal reason: {proposal.reason}",
        f"     State fingerprint: {proposal.state_fingerprint}",
    ]
