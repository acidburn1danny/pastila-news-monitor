"""Production composition for M6C.6A corrective-action planning."""

from enum import StrEnum
from typing import Any

from pydantic import field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionResult,
)
from pastila_scout.editor.qa.models import fingerprint

from .evaluation import CorrectiveActionExecutionPlanEvaluator
from .models import (
    CorrectiveActionExecutionPlanPolicy,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanResult,
)
from .policy import build_standard_corrective_action_execution_plan_policy
from .service import CorrectiveActionExecutionPlanService

WORKFLOW_CONTRACT_VERSION = "1"
WORKFLOW_REPORT_VERSION = "1"
WORKFLOW_ID = "m6c6a.corrective_action_planning_workflow"


class CorrectiveActionPlanningWorkflowStatus(StrEnum):
    """Operational status of composition, not planning semantics."""

    COMPLETED = "completed"
    FAILED_INVALID_INPUT = "failed_invalid_input"
    FAILED_INTERNAL = "failed_internal"


class CorrectiveActionPlanningWorkflowDiagnosticCode(StrEnum):
    """Stable safe composition failure codes."""

    INVALID_WORKFLOW_REQUEST = "invalid_workflow_request"
    INTERNAL_WORKFLOW_FAILURE = "internal_workflow_failure"


class CorrectiveActionPlanningWorkflowDescriptor(FrozenModel):
    """Immutable production-composition architecture descriptor."""

    workflow_id: str = WORKFLOW_ID
    contract_version: str = WORKFLOW_CONTRACT_VERSION
    milestone: str = "M6C.6A"
    authoritative_input: str = "CorrectiveActionDecisionResult"
    authoritative_output: str = "CorrectiveActionExecutionPlanResult"
    ownership: str = "planning_validation_reporting"
    non_responsibilities: tuple[str, ...] = (
        "execution",
        "dispatch",
        "routing",
        "publication",
        "notification",
        "persistence",
    )
    descriptor_fingerprint: str

    @classmethod
    def build(cls) -> CorrectiveActionPlanningWorkflowDescriptor:
        values = {
            "workflow_id": WORKFLOW_ID,
            "contract_version": WORKFLOW_CONTRACT_VERSION,
            "milestone": "M6C.6A",
            "authoritative_input": "CorrectiveActionDecisionResult",
            "authoritative_output": "CorrectiveActionExecutionPlanResult",
            "ownership": "planning_validation_reporting",
            "non_responsibilities": (
                "execution",
                "dispatch",
                "routing",
                "publication",
                "notification",
                "persistence",
            ),
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        if (
            self.workflow_id != WORKFLOW_ID
            or self.contract_version != WORKFLOW_CONTRACT_VERSION
        ):
            raise ValueError("unsupported planning workflow descriptor")
        return _validate_fingerprint(self, "descriptor_fingerprint")


class CorrectiveActionPlanningWorkflowRequest(FrozenModel):
    """Complete frozen decision result and explicit planning policy."""

    decision_result: CorrectiveActionDecisionResult
    planning_policy: CorrectiveActionExecutionPlanPolicy
    contract_version: str = WORKFLOW_CONTRACT_VERSION
    request_fingerprint: str

    @classmethod
    def build(
        cls,
        decision_result: CorrectiveActionDecisionResult,
        planning_policy: CorrectiveActionExecutionPlanPolicy,
    ) -> CorrectiveActionPlanningWorkflowRequest:
        values = {
            "contract_version": WORKFLOW_CONTRACT_VERSION,
            "decision_result_fingerprint": decision_result.result_fingerprint,
            "planning_policy_fingerprint": planning_policy.policy_fingerprint,
        }
        return cls(
            decision_result=decision_result,
            planning_policy=planning_policy,
            request_fingerprint=fingerprint(values),
        )

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != WORKFLOW_CONTRACT_VERSION:
            raise ValueError("unsupported planning workflow request version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            {
                "contract_version": self.contract_version,
                "decision_result_fingerprint": (
                    self.decision_result.result_fingerprint
                ),
                "planning_policy_fingerprint": (
                    self.planning_policy.policy_fingerprint
                ),
            }
        )
        if self.request_fingerprint != expected:
            raise ValueError("planning workflow request fingerprint is inconsistent")
        return self


class CorrectiveActionPlanningWorkflowDiagnostic(FrozenModel):
    """Content-safe workflow failure diagnostic."""

    code: CorrectiveActionPlanningWorkflowDiagnosticCode
    safe_message: str
    contract_version: str = WORKFLOW_CONTRACT_VERSION
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionPlanningWorkflowDiagnostic:
        values.setdefault("contract_version", WORKFLOW_CONTRACT_VERSION)
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_message")
    @classmethod
    def message_is_safe(cls, value: str) -> str:
        if not value.strip() or len(value) > 200:
            raise ValueError("workflow diagnostic must be concise and nonempty")
        forbidden = (
            "\\",
            "/",
            "api_key",
            "secret",
            "token",
            "traceback",
            "prompt",
        )
        if any(token in value.casefold() for token in forbidden):
            raise ValueError("workflow diagnostic contains unsafe content")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class CorrectiveActionPlanningWorkflowReport(FrozenModel):
    """Non-authoritative safe projection of production composition."""

    report_version: str = WORKFLOW_REPORT_VERSION
    workflow_status: CorrectiveActionPlanningWorkflowStatus
    planning_outcome: str | None
    plan_type: str | None
    execution_mode: str | None
    required_capability: str | None
    source_action: str | None
    source_reason: str | None
    diagnostic_code: str | None
    workflow_request_fingerprint: str | None
    decision_result_fingerprint: str | None
    planning_policy_fingerprint: str | None
    plan_result_fingerprint: str | None
    plan_fingerprint: str | None
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionPlanningWorkflowReport:
        values.setdefault("report_version", WORKFLOW_REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.report_version != WORKFLOW_REPORT_VERSION:
            raise ValueError("unsupported planning workflow report version")
        return _validate_fingerprint(self, "report_fingerprint")


class CorrectiveActionPlanningWorkflowResult(FrozenModel):
    """Immutable production result preserving all authoritative identities."""

    descriptor: CorrectiveActionPlanningWorkflowDescriptor
    workflow_status: CorrectiveActionPlanningWorkflowStatus
    decision_result: CorrectiveActionDecisionResult | None
    plan_result: CorrectiveActionExecutionPlanResult | None
    diagnostic: CorrectiveActionPlanningWorkflowDiagnostic | None
    report: CorrectiveActionPlanningWorkflowReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionPlanningWorkflowResult:
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        completed = (
            self.workflow_status is CorrectiveActionPlanningWorkflowStatus.COMPLETED
        )
        if completed != (self.plan_result is not None):
            raise ValueError("completed workflow requires one planning result")
        if completed != (self.decision_result is not None):
            raise ValueError("completed workflow requires its decision result")
        if completed == (self.diagnostic is not None):
            raise ValueError("workflow diagnostic presence is inconsistent")
        if self.report.workflow_status is not self.workflow_status:
            raise ValueError("workflow report status is inconsistent")
        if self.report.plan_result_fingerprint != (
            self.plan_result.result_fingerprint if self.plan_result else None
        ):
            raise ValueError("workflow report planning identity is inconsistent")
        if self.diagnostic is not None and (
            self.report.diagnostic_code != self.diagnostic.code.value
        ):
            raise ValueError("workflow report diagnostic is inconsistent")
        _validate_workflow_report(self)
        expected = fingerprint(_result_identity(self.model_dump(mode="python")))
        if self.result_fingerprint != expected:
            raise ValueError("planning workflow result fingerprint is inconsistent")
        return self


class CorrectiveActionPlanningWorkflowService:
    """Compose one supplied decision result with one planning-service call."""

    def __init__(
        self,
        *,
        planning_service: CorrectiveActionExecutionPlanService,
    ) -> None:
        self._planning_service = planning_service

    def execute(self, request: object) -> CorrectiveActionPlanningWorkflowResult:
        """Transport one planning result without executing its plan."""

        if not _valid_workflow_request(request):
            return _workflow_failure(
                CorrectiveActionPlanningWorkflowStatus.FAILED_INVALID_INPUT,
                CorrectiveActionPlanningWorkflowDiagnosticCode.INVALID_WORKFLOW_REQUEST,
                "Corrective-action planning workflow request is invalid.",
            )
        planning_request = CorrectiveActionExecutionPlanRequest.build(
            request.decision_result, request.planning_policy
        )
        try:
            plan_result = self._planning_service.plan(planning_request)
        except Exception:  # noqa: BLE001 - sanitize at composition boundary
            return _workflow_failure(
                CorrectiveActionPlanningWorkflowStatus.FAILED_INTERNAL,
                CorrectiveActionPlanningWorkflowDiagnosticCode.INTERNAL_WORKFLOW_FAILURE,
                "Corrective-action planning workflow failed internally.",
            )
        report = _build_workflow_report(request, plan_result)
        return CorrectiveActionPlanningWorkflowResult.build(
            descriptor=CorrectiveActionPlanningWorkflowDescriptor.build(),
            workflow_status=CorrectiveActionPlanningWorkflowStatus.COMPLETED,
            decision_result=request.decision_result,
            plan_result=plan_result,
            diagnostic=None,
            report=report,
        )


def build_standard_corrective_action_execution_planning_service() -> (
    CorrectiveActionPlanningWorkflowService
):
    """Build one evaluator, planning service, and production workflow."""

    evaluator = CorrectiveActionExecutionPlanEvaluator()
    planning_service = CorrectiveActionExecutionPlanService(evaluator)
    return CorrectiveActionPlanningWorkflowService(planning_service=planning_service)


def generate_execution_plan(
    decision_result: CorrectiveActionDecisionResult,
    *,
    planning_policy: CorrectiveActionExecutionPlanPolicy | None = None,
    workflow_service: CorrectiveActionPlanningWorkflowService | None = None,
) -> CorrectiveActionPlanningWorkflowResult:
    """Delegate a supplied authoritative result to production composition."""

    policy = planning_policy or build_standard_corrective_action_execution_plan_policy()
    service = (
        workflow_service
        or build_standard_corrective_action_execution_planning_service()
    )
    request = CorrectiveActionPlanningWorkflowRequest.build(decision_result, policy)
    return service.execute(request)


def _valid_workflow_request(request: object) -> bool:
    if not isinstance(request, CorrectiveActionPlanningWorkflowRequest):
        return False
    try:
        CorrectiveActionPlanningWorkflowRequest.model_validate(
            request.model_dump(mode="python")
        )
    except ValueError:
        return False
    return True


def _build_workflow_report(request, plan_result):
    plan = plan_result.plan
    return CorrectiveActionPlanningWorkflowReport.build(
        workflow_status=CorrectiveActionPlanningWorkflowStatus.COMPLETED,
        planning_outcome=plan_result.operational_outcome.value,
        plan_type=plan.plan_type.value if plan else None,
        execution_mode=plan.execution_mode.value if plan else None,
        required_capability=plan.required_capability.value if plan else None,
        source_action=plan.source_action.value if plan else None,
        source_reason=plan.source_reason.value if plan else None,
        diagnostic_code=(
            plan_result.diagnostic.code.value if plan_result.diagnostic else None
        ),
        workflow_request_fingerprint=request.request_fingerprint,
        decision_result_fingerprint=request.decision_result.result_fingerprint,
        planning_policy_fingerprint=request.planning_policy.policy_fingerprint,
        plan_result_fingerprint=plan_result.result_fingerprint,
        plan_fingerprint=plan.plan_fingerprint if plan else None,
    )


def _workflow_failure(status, code, message):
    diagnostic = CorrectiveActionPlanningWorkflowDiagnostic.build(
        code=code, safe_message=message
    )
    report = CorrectiveActionPlanningWorkflowReport.build(
        workflow_status=status,
        planning_outcome=None,
        plan_type=None,
        execution_mode=None,
        required_capability=None,
        source_action=None,
        source_reason=None,
        diagnostic_code=code.value,
        workflow_request_fingerprint=None,
        decision_result_fingerprint=None,
        planning_policy_fingerprint=None,
        plan_result_fingerprint=None,
        plan_fingerprint=None,
    )
    return CorrectiveActionPlanningWorkflowResult.build(
        descriptor=CorrectiveActionPlanningWorkflowDescriptor.build(),
        workflow_status=status,
        decision_result=None,
        plan_result=None,
        diagnostic=diagnostic,
        report=report,
    )


def _result_identity(values):
    descriptor = values["descriptor"]
    decision_result = values.get("decision_result")
    plan_result = values.get("plan_result")
    diagnostic = values.get("diagnostic")
    report = values["report"]
    return {
        "descriptor_fingerprint": _field(descriptor, "descriptor_fingerprint"),
        "workflow_status": values["workflow_status"],
        "decision_result_fingerprint": (
            _field(decision_result, "result_fingerprint") if decision_result else None
        ),
        "plan_result_fingerprint": (
            _field(plan_result, "result_fingerprint") if plan_result else None
        ),
        "diagnostic_fingerprint": (
            _field(diagnostic, "diagnostic_fingerprint") if diagnostic else None
        ),
        "report_fingerprint": _field(report, "report_fingerprint"),
    }


def _validate_workflow_report(result: CorrectiveActionPlanningWorkflowResult) -> None:
    report = result.report
    plan_result = result.plan_result
    plan = plan_result.plan if plan_result else None
    expected = {
        "planning_outcome": (
            plan_result.operational_outcome.value if plan_result else None
        ),
        "plan_type": plan.plan_type.value if plan else None,
        "execution_mode": plan.execution_mode.value if plan else None,
        "required_capability": plan.required_capability.value if plan else None,
        "source_action": plan.source_action.value if plan else None,
        "source_reason": plan.source_reason.value if plan else None,
        "diagnostic_code": (
            plan_result.diagnostic.code.value
            if plan_result and plan_result.diagnostic
            else result.diagnostic.code.value if result.diagnostic else None
        ),
        "decision_result_fingerprint": (
            result.decision_result.result_fingerprint
            if result.decision_result
            else None
        ),
        "planning_policy_fingerprint": (
            plan.policy_fingerprint
            if plan
            else plan_result.report.policy_fingerprint if plan_result else None
        ),
        "plan_result_fingerprint": (
            plan_result.result_fingerprint if plan_result else None
        ),
        "plan_fingerprint": plan.plan_fingerprint if plan else None,
    }
    if any(getattr(report, field) != value for field, value in expected.items()):
        raise ValueError("workflow report contradicts authoritative result")


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
