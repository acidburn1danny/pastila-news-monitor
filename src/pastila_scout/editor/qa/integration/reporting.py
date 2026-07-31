"""Sanitized application integration reporting."""

import json


def serialize_integration_report(report) -> str:
    """Serialize only the sanitized report using stable UTF-8 JSON semantics."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_integration_report(report):
    return (
        "\n".join(
            (
                f"Integration: {report.integration_id}@{report.integration_version}",
                f"Status: {report.integration_status.value}",
                f"Generation: {'present' if report.generation_present else 'absent'}",
                f"Draft: {'validated' if report.draft_fingerprint else 'absent'}",
                f"Review: {report.review_status or 'not-run'}",
                f"Editorial: {report.editorial_status or 'not-run'}",
                f"Limited completion: {'yes' if report.limited_completion else 'no'}",
            )
        )
        + "\n"
    )
