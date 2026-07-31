"""Safe deterministic M6C.5F decision report projections."""

import json


def serialize_corrective_action_decision_report(report) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_corrective_action_decision_report(report) -> str:
    return (
        "\n".join(
            (
                f"Decision engine: {report.engine_id}@{report.contract_version}",
                f"Outcome: {report.operational_outcome.value}",
                f"Action: {report.requested_action.value if report.requested_action else 'absent'}",
                f"Reason: {report.decision_reason.value if report.decision_reason else 'absent'}",
                f"Upstream: {report.source_integration_status or 'absent'}",
                f"Editorial: {report.source_editorial_status or 'absent'}",
            )
        )
        + "\n"
    )
