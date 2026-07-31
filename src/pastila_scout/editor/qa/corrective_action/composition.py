"""M6C.5F Part 3 production composition of frozen M6C.5E and M6C.5F."""

import json
from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.models import (
    CONTRACT_VERSION,
    CorrectiveActionDecisionOutcome,
    CorrectiveActionDecisionPolicy,
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionResult,
)
from pastila_scout.editor.qa.corrective_action.service import (
    CorrectiveActionDecisionService,
)
from pastila_scout.editor.qa.integration import (
    EditorialReviewIntegrationRequest,
    EditorialReviewIntegrationResult,
    build_standard_editorial_review_integration_service,
)
from pastila_scout.editor.qa.models import fingerprint

WORKFLOW_ID = "m6c5f.editorial_decision_workflow"
WORKFLOW_VERSION = "1.0.0"


class EditorialDecisionWorkflowStatus(StrEnum):
    COMPLETED = "completed"
    FAILED_DURING_INTEGRATION = "failed_during_integration"
    FAILED_DURING_DECISION = "failed_during_decision"


class EditorialDecisionWorkflowDescriptor(FrozenModel):
    workflow_id: str = WORKFLOW_ID
    workflow_version: str = WORKFLOW_VERSION
    descriptor_fingerprint: str

    @classmethod
    def build(cls):
        values = {"workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION}
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("workflow descriptor fingerprint is inconsistent")
        return self


class EditorialDecisionWorkflowDiagnostic(FrozenModel):
    code: str
    phase: str
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, *, code, phase):
        values = {"code": code, "phase": phase}
        return cls(**values, diagnostic_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"diagnostic_fingerprint"}, mode="python")
        )
        if self.diagnostic_fingerprint != expected:
            raise ValueError("workflow diagnostic fingerprint is inconsistent")
        return self


class EditorialDecisionWorkflowTraceEvent(FrozenModel):
    sequence: int
    event_type: str
    event_fingerprint: str

    @classmethod
    def build(cls, sequence, event_type):
        values = {"sequence": sequence, "event_type": event_type}
        return cls(**values, event_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"event_fingerprint"}, mode="python")
        )
        if self.event_fingerprint != expected:
            raise ValueError("workflow trace fingerprint is inconsistent")
        return self


class EditorialDecisionWorkflowRequest(FrozenModel):
    integration_request: EditorialReviewIntegrationRequest
    decision_policy: CorrectiveActionDecisionPolicy
    request_fingerprint: str

    @classmethod
    def build(cls, integration_request, decision_policy):
        payload = {
            "workflow": (WORKFLOW_ID, WORKFLOW_VERSION),
            "integration_request": integration_request.request_fingerprint,
            "decision_policy": decision_policy.policy_fingerprint,
        }
        return cls(
            integration_request=integration_request,
            decision_policy=decision_policy,
            request_fingerprint=fingerprint(payload),
        )

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            {
                "workflow": (WORKFLOW_ID, WORKFLOW_VERSION),
                "integration_request": self.integration_request.request_fingerprint,
                "decision_policy": self.decision_policy.policy_fingerprint,
            }
        )
        if self.request_fingerprint != expected:
            raise ValueError("workflow request fingerprint is inconsistent")
        return self


class EditorialDecisionWorkflowReport(FrozenModel):
    workflow_id: str
    workflow_version: str
    request_fingerprint: str
    integration_result_fingerprint: str | None
    decision_result_fingerprint: str | None
    integration_status: str | None
    decision_outcome: str | None
    requested_action: str | None
    workflow_status: EditorialDecisionWorkflowStatus
    report_fingerprint: str

    @classmethod
    def build(cls, **values):
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"report_fingerprint"}, mode="python")
        )
        if self.report_fingerprint != expected:
            raise ValueError("workflow report fingerprint is inconsistent")
        return self


class EditorialDecisionWorkflowResult(FrozenModel):
    descriptor: EditorialDecisionWorkflowDescriptor
    request_fingerprint: str
    integration_result: EditorialReviewIntegrationResult | None
    decision_result: CorrectiveActionDecisionResult | None
    status: EditorialDecisionWorkflowStatus
    diagnostics: tuple[EditorialDecisionWorkflowDiagnostic, ...]
    trace: tuple[EditorialDecisionWorkflowTraceEvent, ...]
    report: EditorialDecisionWorkflowReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values):
        values["result_fingerprint"] = fingerprint(_workflow_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(_workflow_identity(self.model_dump(mode="python")))
        if self.result_fingerprint != expected:
            raise ValueError("workflow result fingerprint is inconsistent")
        if self.decision_result and (
            self.integration_result is None
            or self.decision_result.integration_result != self.integration_result
        ):
            raise ValueError("workflow source identity is inconsistent")
        if tuple(item.sequence for item in self.trace) != tuple(range(len(self.trace))):
            raise ValueError("workflow trace sequence is inconsistent")
        return self


class EditorialDecisionWorkflowService:
    """Invoke M6C.5E once, then M6C.5F once, without executing the action."""

    def __init__(self, *, integration_service: Any, decision_service: Any) -> None:
        self.integration_service = integration_service
        self.decision_service = decision_service

    def execute(self, request: EditorialDecisionWorkflowRequest):
        trace = ["request_validated", "integration_started"]
        try:
            integration_result = self.integration_service.execute(
                request.integration_request
            )
        except Exception:  # noqa: BLE001 - application integration boundary
            return _workflow_result(
                request,
                integration_result=None,
                decision_result=None,
                status=EditorialDecisionWorkflowStatus.FAILED_DURING_INTEGRATION,
                diagnostics=(("INTEGRATION_INVOCATION_FAILED", "integration"),),
                trace=(*trace, "integration_failed", "finalized"),
            )
        trace.extend(("integration_completed", "decision_started"))
        try:
            decision_result = self.decision_service.decide(
                CorrectiveActionDecisionRequest.build(
                    integration_result, request.decision_policy
                )
            )
        except Exception:  # noqa: BLE001 - application decision boundary
            return _workflow_result(
                request,
                integration_result=integration_result,
                decision_result=None,
                status=EditorialDecisionWorkflowStatus.FAILED_DURING_DECISION,
                diagnostics=(("DECISION_INVOCATION_FAILED", "decision"),),
                trace=(*trace, "decision_failed", "finalized"),
            )
        status = (
            EditorialDecisionWorkflowStatus.COMPLETED
            if decision_result.operational_outcome
            is CorrectiveActionDecisionOutcome.COMPLETED
            else EditorialDecisionWorkflowStatus.FAILED_DURING_DECISION
        )
        return _workflow_result(
            request,
            integration_result=integration_result,
            decision_result=decision_result,
            status=status,
            diagnostics=(),
            trace=(*trace, "decision_completed", "finalized"),
        )


def build_standard_editorial_decision_workflow_service(
    *, generator, review_orchestrator=None, decision_service=None
):
    return EditorialDecisionWorkflowService(
        integration_service=build_standard_editorial_review_integration_service(
            generator=generator, review_orchestrator=review_orchestrator
        ),
        decision_service=decision_service or CorrectiveActionDecisionService(),
    )


def generate_review_and_decide(*, generator, integration_request, decision_policy):
    request = EditorialDecisionWorkflowRequest.build(
        integration_request, decision_policy
    )
    return build_standard_editorial_decision_workflow_service(
        generator=generator
    ).execute(request)


def serialize_editorial_decision_workflow_report(report) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_editorial_decision_workflow_report(report) -> str:
    return (
        "\n".join(
            (
                f"Workflow: {report.workflow_id}@{report.workflow_version}",
                f"Status: {report.workflow_status.value}",
                f"Integration: {report.integration_status or 'absent'}",
                f"Decision: {report.decision_outcome or 'absent'}",
                f"Action: {report.requested_action or 'absent'}",
            )
        )
        + "\n"
    )


def _workflow_result(
    request, *, integration_result, decision_result, status, diagnostics, trace
):
    report = EditorialDecisionWorkflowReport.build(
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        request_fingerprint=request.request_fingerprint,
        integration_result_fingerprint=(
            integration_result.result_fingerprint if integration_result else None
        ),
        decision_result_fingerprint=(
            decision_result.result_fingerprint if decision_result else None
        ),
        integration_status=(
            integration_result.status.value if integration_result else None
        ),
        decision_outcome=(
            decision_result.operational_outcome.value if decision_result else None
        ),
        requested_action=(
            decision_result.decision.action.value
            if decision_result and decision_result.decision
            else None
        ),
        workflow_status=status,
    )
    diagnostic_models = tuple(
        EditorialDecisionWorkflowDiagnostic.build(code=code, phase=phase)
        for code, phase in diagnostics
    )
    trace_models = tuple(
        EditorialDecisionWorkflowTraceEvent.build(index, event)
        for index, event in enumerate(trace)
    )
    return EditorialDecisionWorkflowResult.build(
        descriptor=EditorialDecisionWorkflowDescriptor.build(),
        request_fingerprint=request.request_fingerprint,
        integration_result=integration_result,
        decision_result=decision_result,
        status=status,
        diagnostics=diagnostic_models,
        trace=trace_models,
        report=report,
    )


def _workflow_identity(values):
    integration = values.get("integration_result")
    decision = values.get("decision_result")
    report = values["report"]
    return {
        "contract_version": CONTRACT_VERSION,
        "descriptor_fingerprint": _value(
            values["descriptor"], "descriptor_fingerprint"
        ),
        "request_fingerprint": values["request_fingerprint"],
        "integration_result_fingerprint": _value(integration, "result_fingerprint"),
        "decision_result_fingerprint": _value(decision, "result_fingerprint"),
        "status": values["status"],
        "diagnostic_fingerprints": tuple(
            _value(item, "diagnostic_fingerprint") for item in values["diagnostics"]
        ),
        "trace_fingerprints": tuple(
            _value(item, "event_fingerprint") for item in values["trace"]
        ),
        "report_fingerprint": _value(report, "report_fingerprint"),
    }


def _value(value, name):
    if value is None:
        return None
    return value[name] if isinstance(value, dict) else getattr(value, name)
