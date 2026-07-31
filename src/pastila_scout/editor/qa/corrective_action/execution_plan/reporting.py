"""Safe, non-authoritative M6C.6A reporting projections."""

import json

from .enums import CorrectiveActionExecutionPlanOutcome
from .models import (
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanDiagnostic,
    CorrectiveActionExecutionPlanReport,
    CorrectiveActionExecutionPlanResult,
)


def build_execution_plan_report(
    *,
    operational_outcome: CorrectiveActionExecutionPlanOutcome,
    plan: CorrectiveActionExecutionPlan | None,
    diagnostic: CorrectiveActionExecutionPlanDiagnostic | None,
    request_fingerprint: str | None,
    policy_fingerprint: str | None,
    input_complete: bool,
    decision_result_fingerprint: str | None = None,
    final_lifecycle_phase: str | None = None,
    lifecycle_revision: int | None = None,
    state_fingerprint: str | None = None,
) -> CorrectiveActionExecutionPlanReport:
    """Build a safe projection without copying upstream editorial content."""

    return CorrectiveActionExecutionPlanReport.build(
        operational_outcome=operational_outcome,
        plan_type=plan.plan_type if plan else None,
        execution_mode=plan.execution_mode if plan else None,
        required_capability=plan.required_capability if plan else None,
        source_action=plan.source_action if plan else None,
        source_reason=plan.source_reason if plan else None,
        automatic_execution_allowed=(
            plan.automatic_execution_allowed if plan else None
        ),
        human_authorization_required=(
            plan.human_authorization_required if plan else None
        ),
        diagnostic_code=diagnostic.code if diagnostic else None,
        request_fingerprint=request_fingerprint,
        policy_fingerprint=policy_fingerprint,
        plan_fingerprint=plan.plan_fingerprint if plan else None,
        input_complete=input_complete,
        plan_complete=plan is not None,
        decision_result_fingerprint=decision_result_fingerprint,
        final_lifecycle_phase=final_lifecycle_phase,
        lifecycle_revision=lifecycle_revision,
        state_fingerprint=state_fingerprint,
    )


def serialize_execution_plan_report(
    report: CorrectiveActionExecutionPlanReport,
) -> str:
    """Serialize only the safe report projection deterministically."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def serialize_execution_plan_result(
    result: CorrectiveActionExecutionPlanResult,
) -> str:
    """Serialize a safe result projection, never its authoritative object graph."""

    projection = result.report.model_dump(mode="json")
    projection["result_fingerprint"] = result.result_fingerprint
    return json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_execution_plan_report(
    report: CorrectiveActionExecutionPlanReport,
) -> str:
    """Render a compact safe report without authoritative source content."""

    return (
        "\n".join(
            (
                f"Planning outcome: {report.operational_outcome.value}",
                f"Plan type: {report.plan_type.value if report.plan_type else 'absent'}",
                f"Execution mode: {report.execution_mode.value if report.execution_mode else 'absent'}",
                f"Capability: {report.required_capability.value if report.required_capability else 'absent'}",
                f"Source action: {report.source_action.value if report.source_action else 'absent'}",
                f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}",
                f"Lifecycle: {report.final_lifecycle_phase or 'absent'}",
                f"Revision: {report.lifecycle_revision if report.lifecycle_revision is not None else 'absent'}",
            )
        )
        + "\n"
    )
