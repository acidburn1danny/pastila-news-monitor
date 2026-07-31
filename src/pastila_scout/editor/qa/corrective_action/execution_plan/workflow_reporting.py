"""Safe deterministic reporting for M6C.6A production composition."""

import json

from .composition import CorrectiveActionPlanningWorkflowReport


def serialize_corrective_action_planning_workflow_report(
    report: CorrectiveActionPlanningWorkflowReport,
) -> str:
    """Serialize only the non-authoritative safe workflow projection."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_corrective_action_planning_workflow_report(
    report: CorrectiveActionPlanningWorkflowReport,
) -> str:
    """Render a compact content-safe workflow report."""

    return (
        "\n".join(
            (
                f"Workflow status: {report.workflow_status.value}",
                f"Planning outcome: {report.planning_outcome or 'absent'}",
                f"Plan type: {report.plan_type or 'absent'}",
                f"Execution mode: {report.execution_mode or 'absent'}",
                f"Capability: {report.required_capability or 'absent'}",
                f"Source action: {report.source_action or 'absent'}",
                f"Diagnostic: {report.diagnostic_code or 'absent'}",
            )
        )
        + "\n"
    )
