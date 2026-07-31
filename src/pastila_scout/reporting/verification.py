"""UTF-8 reports for advisory AI event verification."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.models.ai import VerificationRunReport


def write_verification_reports(
    report: VerificationRunReport, output_directory: Path
) -> tuple[Path, Path]:
    """Write complete deterministic JSON and human-readable text reports."""

    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    json_path = output_directory / f"event_verification_{stamp}.json"
    text_path = output_directory / f"event_verification_{stamp}.txt"
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = _summary_lines(report)
    lines.append("")
    lines.append("Verification details:")
    for record in report.records:
        request, result = record.request, record.result
        lines.extend(
            [
                f"Events {request.left.event_id} / {request.right.event_id}",
                f"  Articles {request.left.article_id} / {request.right.article_id}",
                f"  Deterministic similarity: {request.deterministic_similarity:.4f}",
                f"  AI status: {result.status}; score: {result.ai_similarity_score}",
                f"  Confirmed: {record.confirmed_same_event}",
                f"  Decision: {record.decision.model_dump(mode='json') if record.decision else None}",
                f"  Verification fields: same_event={result.same_event}, same_people={result.same_people}, same_institution={result.same_institution}, same_location={result.same_location}, same_context={result.same_context}",
                f"  Reasoning: {result.reasoning}",
                f"  Usage: {result.usage.model_dump(mode='json')}",
                f"  Cache: {result.cache_diagnostics.model_dump(mode='json') if result.cache_diagnostics else None}",
            ]
        )
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, text_path


def render_verification_console(
    report: VerificationRunReport, *, details: bool
) -> list[str]:
    lines = _summary_lines(report)
    if details:
        for record in report.records:
            result = record.result
            lines.extend(
                [
                    f"Events {record.request.left.event_id}/{record.request.right.event_id}: {result.status}, score={result.ai_similarity_score}, confirmed={record.confirmed_same_event}",
                    f"  Decision: reason={record.decision.reason if record.decision else 'unavailable'}, threshold={record.decision.threshold if record.decision else 85}, score={record.decision.score if record.decision else result.ai_similarity_score}",
                    f"  Fields: same_event={result.same_event}, people={result.same_people}, institution={result.same_institution}, location={result.same_location}, context={result.same_context}",
                    f"  Reasoning: {result.reasoning}",
                    f"  Usage: input={result.usage.input_tokens}, output={result.usage.output_tokens}, total={result.usage.total_tokens}, latency_ms={result.usage.provider_latency_ms}, retries={result.retry_count}, cost={result.usage.estimated_cost}",
                    f"  Cache: {_cache_summary(result)}",
                ]
            )
    return lines


def _summary_lines(report: VerificationRunReport) -> list[str]:
    return [
        f"Candidate pairs: {report.candidate_pairs}",
        f"AI requests: {report.ai_requests}",
        f"Cache: {report.cache_hits} hits, {report.cache_misses} misses",
        f"Decisions: {report.confirmed_same_event_pairs} confirmed, {report.rejected_pairs} rejected",
        f"Unavailable: {report.unavailable_results}; failed: {report.failed_requests}; retries: {report.retries}",
        f"Usage: {report.usage.input_tokens} input, {report.usage.output_tokens} output, {report.usage.total_tokens} total, {report.usage.provider_latency_ms} ms, cost {report.usage.estimated_cost if report.usage.estimated_cost is not None else 'unavailable'}",
    ]


def _cache_summary(result: object) -> str:
    diagnostic = result.cache_diagnostics
    if diagnostic is None:
        return f"status={result.cache_status}; diagnostics unavailable"
    return (
        f"status={diagnostic.status}, fingerprint={diagnostic.fingerprint_version}, "
        f"prompt={diagnostic.prompt_version}, schema={diagnostic.schema_version}, "
        f"provider={diagnostic.provider}, model={diagnostic.model}, "
        f"created_at={diagnostic.created_at}, age_seconds={diagnostic.cache_age_seconds}"
    )
