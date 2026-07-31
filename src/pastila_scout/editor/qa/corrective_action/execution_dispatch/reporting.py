"""Safe deterministic reporting for M6C.6B dispatch contracts."""

import json

from .enums import (
    CorrectiveActionExecutionDispatchOutcome,
    CorrectiveActionExecutionDispatchStatus,
)
from .models import (
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchReport,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
)


def build_execution_dispatch_report(
    *,
    request: CorrectiveActionExecutionDispatchRequest,
    operational_outcome: CorrectiveActionExecutionDispatchOutcome,
    dispatch_status: CorrectiveActionExecutionDispatchStatus,
    executor_descriptor: CorrectiveActionExecutorDescriptor | None,
    executor_request: CorrectiveActionExecutorRequest | None,
    executor_result: CorrectiveActionExecutorResult | None,
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic | None,
) -> CorrectiveActionExecutionDispatchReport:
    """Project authoritative components without copying upstream content."""

    planning_result = request.planning_result
    plan = planning_result.plan
    effective_diagnostic = diagnostic or (
        executor_result.diagnostic if executor_result else None
    )
    executable = bool(
        plan
        and plan.execution_mode.value != "non_executable"
        and plan.required_capability.value != "none"
    )
    invoked = dispatch_status in {
        CorrectiveActionExecutionDispatchStatus.DISPATCHED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
    }
    return CorrectiveActionExecutionDispatchReport.build(
        operational_outcome=operational_outcome,
        dispatch_status=dispatch_status,
        planning_outcome=planning_result.operational_outcome,
        plan_type=plan.plan_type if plan else None,
        execution_mode=plan.execution_mode if plan else None,
        required_capability=plan.required_capability if plan else None,
        authorization_state=request.execution_context.authorization_state,
        executor_id=(executor_descriptor.executor_id if executor_descriptor else None),
        executor_contract_version=(
            executor_descriptor.executor_contract_version
            if executor_descriptor
            else None
        ),
        executor_outcome=(
            executor_result.operational_outcome if executor_result else None
        ),
        execution_status=(
            executor_result.execution_status if executor_result else None
        ),
        diagnostic_code=(effective_diagnostic.code if effective_diagnostic else None),
        dispatch_request_fingerprint=request.request_fingerprint,
        planning_result_fingerprint=planning_result.result_fingerprint,
        plan_fingerprint=plan.plan_fingerprint if plan else None,
        executor_descriptor_fingerprint=(
            executor_descriptor.descriptor_fingerprint if executor_descriptor else None
        ),
        executor_request_fingerprint=(
            executor_request.request_fingerprint if executor_request else None
        ),
        executor_result_fingerprint=(
            executor_result.result_fingerprint if executor_result else None
        ),
        planning_result_validated=True,
        dispatch_eligible=executable
        and dispatch_status
        not in {
            CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
            CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION,
            CorrectiveActionExecutionDispatchStatus.NOT_ATTEMPTED,
        },
        executor_resolved=executor_descriptor is not None,
        executor_invoked=invoked,
    )


def serialize_execution_dispatch_report(
    report: CorrectiveActionExecutionDispatchReport,
) -> str:
    """Serialize only the safe report with deterministic UTF-8 JSON semantics."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_execution_dispatch_report(
    report: CorrectiveActionExecutionDispatchReport,
) -> str:
    """Render a compact safe non-authoritative dispatch report."""

    return (
        "\n".join(
            (
                f"Dispatch outcome: {report.operational_outcome.value}",
                f"Dispatch status: {report.dispatch_status.value}",
                f"Planning outcome: {report.planning_outcome.value}",
                f"Plan type: {report.plan_type.value if report.plan_type else 'absent'}",
                f"Execution mode: {report.execution_mode.value if report.execution_mode else 'absent'}",
                f"Capability: {report.required_capability.value if report.required_capability else 'absent'}",
                f"Authorization: {report.authorization_state.value}",
                f"Executor: {report.executor_id or 'absent'}",
                f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}",
            )
        )
        + "\n"
    )
