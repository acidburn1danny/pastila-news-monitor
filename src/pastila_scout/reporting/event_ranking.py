"""UTF-8 JSON, text, and console presentation for event rankings."""

from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.models import EventRankingReport


def write_ranking_reports(
    report: EventRankingReport, output_directory: Path
) -> tuple[Path, Path]:
    """Write the complete ranked result in machine and human-readable forms."""

    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    stem = f"event_ranking_{stamp}"
    json_path = output_directory / f"{stem}.json"
    text_path = output_directory / f"{stem}.txt"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    text_path.write_text(
        "\n".join(render_ranking(report, details=True)) + "\n", encoding="utf-8"
    )
    return json_path, text_path


def render_ranking(report: EventRankingReport, *, details: bool) -> list[str]:
    """Render compact totals and optionally full ranked-event diagnostics."""

    usage = report.token_usage
    lines = [
        f"Events: {report.events_eligible} eligible, {report.events_processed} processed, {report.events_reported} reported",
        f"AI: {report.ai_requests} requests, {report.cache_hits} cache hits, {report.cache_misses} cache misses, {report.failed_requests} failed, {report.retries} retries",
        f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output, {usage.total_tokens} total",
        f"Provider latency: {usage.provider_latency_ms if usage.provider_latency_ms is not None else 'unavailable'} ms",
        f"Estimated API cost: {usage.estimated_cost if usage.estimated_cost is not None else 'unavailable'}",
        "Ranking:",
    ]
    if not report.rankings:
        lines.append("  none")
    for item in report.rankings:
        lines.append(
            f"  {item.rank}. [{item.recommendation}] {item.final_score:.2f} | "
            f"{item.event.canonical_title} (event {item.event.id})"
        )
        if details:
            lines.extend(_ranking_details(item))
    return lines


def _ranking_details(item: object) -> list[str]:
    ai = item.ai_result
    decision = ai.decision
    weights = item.score_weights
    lines = [
        f"     Deterministic: {item.deterministic_score.total:.2f}",
        "     Deterministic breakdown:",
    ]
    for component in item.deterministic_score.components:
        lines.append(
            f"       - {component.name}: raw={component.raw_value}, normalized={component.normalized_value}, contribution={component.weighted_contribution}/{component.maximum}; {component.reason}"
        )
    lines.extend(
        [
            f"     AI editorial: {item.ai_editorial_score if item.ai_editorial_score is not None else 'unavailable'} ({ai.status})",
            f"     AI dimensions: importance={decision.importance if decision else None}, virality={decision.virality if decision else None}, absurdity={decision.absurdity if decision else None}, satirical_potential={decision.satirical_potential if decision else None}, public_interest={decision.public_interest if decision else None}, emotional_impact={decision.emotional_impact if decision else None}, originality={decision.originality if decision else None}",
            f"     Score weights: deterministic={weights.deterministic if weights else None}, AI={weights.ai_editorial if weights else None}",
            f"     Final weighted score: {item.final_score:.2f}",
            f"     Recommendation: {item.recommendation}",
            f"     Basis: {item.score_basis}",
            f"     Categories: {', '.join(item.event.categories)}",
            f"     Sources/articles: {item.event.source_count}/{item.event.article_count}",
            f"     Reason: {decision.recommendation_reason if decision else ai.error_message}",
            f"     Editorial risks: {', '.join(decision.editorial_risks) if decision and decision.editorial_risks else 'none'}",
            f"     Usage: input={ai.token_usage.input_tokens}, output={ai.token_usage.output_tokens}, total={ai.token_usage.total_tokens}, latency_ms={ai.token_usage.provider_latency_ms}, retries={ai.retry_count}, cost={ai.token_usage.estimated_cost}",
            f"     Cache: {_editorial_cache_summary(ai)}",
        ]
    )
    return lines


def _editorial_cache_summary(ai: object) -> str:
    diagnostic = ai.cache_diagnostics
    if diagnostic is None:
        return f"status={ai.cache_status}; diagnostics unavailable"
    return (
        f"status={diagnostic.status}, fingerprint={diagnostic.fingerprint_version}, "
        f"prompt={diagnostic.prompt_version}, schema={diagnostic.schema_version}, "
        f"provider={diagnostic.provider}, model={diagnostic.model}, "
        f"created_at={diagnostic.created_at}, age_seconds={diagnostic.cache_age_seconds}"
    )
