"""Safe deterministic workflow and lifecycle reporting."""

import json
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

from .composition import CorrectiveActionExecutionDispatchWorkflowResult

RUNTIME_REPORT_VERSION = "1"


class CorrectiveActionExecutionDispatchRuntimeReport(FrozenModel):
    """Content-safe projection of one complete workflow run."""

    report_version: str = RUNTIME_REPORT_VERSION
    workflow_outcome: str
    dispatch_outcome: str
    dispatch_status: str
    executor_id: str | None
    executor_outcome: str | None
    lifecycle_phase: str
    lifecycle_revision: int
    workflow_request_fingerprint: str
    dispatch_request_fingerprint: str
    dispatch_result_fingerprint: str
    state_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchRuntimeReport:
        values.setdefault("report_version", RUNTIME_REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.report_version != RUNTIME_REPORT_VERSION:
            raise ValueError("unsupported runtime report version")
        expected = fingerprint(
            self.model_dump(exclude={"report_fingerprint"}, mode="python")
        )
        if self.report_fingerprint != expected:
            raise ValueError("runtime report fingerprint is inconsistent")
        return self


def build_execution_dispatch_runtime_report(
    result: CorrectiveActionExecutionDispatchWorkflowResult,
) -> CorrectiveActionExecutionDispatchRuntimeReport:
    """Project only authoritative workflow and nested dispatch data."""

    dispatch = result.dispatch_result
    executor_result = dispatch.executor_result
    return CorrectiveActionExecutionDispatchRuntimeReport.build(
        workflow_outcome=result.operational_outcome.value,
        dispatch_outcome=dispatch.operational_outcome.value,
        dispatch_status=dispatch.dispatch_status.value,
        executor_id=(
            dispatch.executor_descriptor.executor_id
            if dispatch.executor_descriptor
            else None
        ),
        executor_outcome=(
            executor_result.operational_outcome.value if executor_result else None
        ),
        lifecycle_phase=result.dispatch_state.phase.value,
        lifecycle_revision=result.dispatch_state.revision,
        workflow_request_fingerprint=result.request.request_fingerprint,
        dispatch_request_fingerprint=result.dispatch_request.request_fingerprint,
        dispatch_result_fingerprint=dispatch.result_fingerprint,
        state_fingerprint=result.dispatch_state.state_fingerprint,
    )


def serialize_execution_dispatch_runtime_report(
    report: CorrectiveActionExecutionDispatchRuntimeReport,
) -> str:
    """Serialize a safe report with stable keys and explicit nulls."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_execution_dispatch_runtime_report(
    report: CorrectiveActionExecutionDispatchRuntimeReport,
) -> str:
    """Render a compact content-safe workflow summary."""

    return (
        f"Workflow outcome: {report.workflow_outcome}\n"
        f"Dispatch outcome: {report.dispatch_outcome}\n"
        f"Dispatch status: {report.dispatch_status}\n"
        f"Executor: {report.executor_id or 'absent'}\n"
        f"Lifecycle: {report.lifecycle_phase} ({report.lifecycle_revision})\n"
    )
