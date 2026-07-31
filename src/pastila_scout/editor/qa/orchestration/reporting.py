"""Sanitized human-readable orchestration summary."""


def render_orchestration_report(report):
    return (
        "\n".join(
            (
                f"Orchestrator: {report.orchestrator_id}@{report.orchestrator_version}",
                f"Status: {report.orchestration_status.value}",
                f"Pipeline: {report.pipeline_status or 'not-run'}",
                f"Editorial: {report.editorial_status or 'not-run'}",
                f"Handoff: {'yes' if report.handoff_performed else 'no'}",
                f"Accepted results: {report.completeness.accepted_result_count}",
            )
        )
        + "\n"
    )
