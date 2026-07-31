"""Privacy-safe projections for Controlled Revision contracts."""

from typing import Any

from pastila_scout.editor.generation.models import FrozenModel

from .contracts import (
    REPORT_VERSION,
    ControlledRevisionInvocation,
    ControlledRevisionRequest,
    ControlledRevisionResult,
)
from .enums import ControlledGenerationOperation, RevisionResultStatus
from .identity import revision_fingerprint


class ControlledRevisionRequestReport(FrozenModel):
    report_version: str = REPORT_VERSION
    operation: ControlledGenerationOperation
    target_count: int
    source_draft_fingerprint: str
    planning_input_fingerprint: str
    executor_request_fingerprint: str
    instructions_fingerprint: str
    policy_fingerprint: str
    preservation_fingerprint: str
    output_contract_fingerprint: str
    revision_request_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)


class ControlledRevisionExecutionReport(FrozenModel):
    report_version: str = REPORT_VERSION
    operation: ControlledGenerationOperation
    status: RevisionResultStatus
    lifecycle: tuple[str, ...]
    diagnostic_code: str | None
    source_draft_fingerprint: str
    revision_request_fingerprint: str
    invocation_fingerprint: str
    gateway_result_fingerprint: str
    output_contract_fingerprint: str
    preservation_fingerprint: str
    result_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)


def build_revision_request_report(
    request: ControlledRevisionRequest,
) -> ControlledRevisionRequestReport:
    return ControlledRevisionRequestReport.build(
        operation=request.operation,
        target_count=len(request.revision_targets),
        source_draft_fingerprint=request.preservation_requirements.source_draft_fingerprint,
        planning_input_fingerprint=request.planning_input_fingerprint,
        executor_request_fingerprint=request.executor_request_fingerprint,
        instructions_fingerprint=request.revision_instructions.instructions_fingerprint,
        policy_fingerprint=request.revision_policy.policy_fingerprint,
        preservation_fingerprint=request.preservation_requirements.preservation_fingerprint,
        output_contract_fingerprint=request.expected_output_contract.output_contract_fingerprint,
        revision_request_fingerprint=request.revision_request_fingerprint,
    )


def build_revision_execution_report(
    invocation: ControlledRevisionInvocation,
    result: ControlledRevisionResult,
) -> ControlledRevisionExecutionReport:
    return ControlledRevisionExecutionReport.build(
        operation=invocation.operation,
        status=result.status,
        lifecycle=tuple(item.value for item in result.lifecycle.phases),
        diagnostic_code=result.diagnostic.code.value if result.diagnostic else None,
        source_draft_fingerprint=result.source_draft_fingerprint,
        revision_request_fingerprint=result.revision_request_fingerprint,
        invocation_fingerprint=result.invocation_fingerprint,
        gateway_result_fingerprint=result.gateway_result_fingerprint,
        output_contract_fingerprint=result.output_contract_fingerprint,
        preservation_fingerprint=result.preservation_fingerprint,
        result_fingerprint=result.result_fingerprint,
    )
