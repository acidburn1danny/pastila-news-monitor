"""Immutable public contracts for M6C.6A execution planning."""

from typing import Any

from pydantic import field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.models import (
    CONTRACT_VERSION as DECISION_CONTRACT_VERSION,
)
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveAction,
    CorrectiveActionDecisionOutcome,
    CorrectiveActionDecisionReason,
    CorrectiveActionDecisionResult,
)
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanDiagnosticCode,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanStage,
    CorrectiveActionExecutionPlanType,
)

ENGINE_ID = "m6c6a.corrective_action_execution_plan"
CONTRACT_VERSION = "1"
POLICY_VERSION = "1"
REPORT_VERSION = "1"
SUPPORTED_INPUT = "m6c5f.corrective_action_decision_result@1"


class CorrectiveActionExecutionPlanDescriptor(FrozenModel):
    """Static architectural identity without service construction."""

    engine_id: str = ENGINE_ID
    contract_version: str = CONTRACT_VERSION
    authoritative_input: str = SUPPORTED_INPUT
    authoritative_output: str = "CorrectiveActionExecutionPlanResult"
    ownership: str = "execution_planning_only"
    non_responsibilities: tuple[str, ...] = (
        "decision",
        "dispatch",
        "execution",
        "publication",
        "persistence",
    )
    descriptor_fingerprint: str

    @classmethod
    def build(cls) -> CorrectiveActionExecutionPlanDescriptor:
        values = {
            "engine_id": ENGINE_ID,
            "contract_version": CONTRACT_VERSION,
            "authoritative_input": SUPPORTED_INPUT,
            "authoritative_output": "CorrectiveActionExecutionPlanResult",
            "ownership": "execution_planning_only",
            "non_responsibilities": (
                "decision",
                "dispatch",
                "execution",
                "publication",
                "persistence",
            ),
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        if (
            self.engine_id != ENGINE_ID
            or self.contract_version != CONTRACT_VERSION
            or self.authoritative_input != SUPPORTED_INPUT
        ):
            raise ValueError("unsupported execution-plan descriptor")
        return _validate_fingerprint(self, "descriptor_fingerprint")


class CorrectiveActionExecutionPlanPolicy(FrozenModel):
    """Versioned execution-characteristics policy; it cannot change decisions."""

    policy_id: str = "standard_corrective_action_execution_plan"
    policy_version: str = POLICY_VERSION
    regeneration_automatic_allowed: bool = False
    revision_requires_human_authorization: bool = True
    manual_review_requires_human_authorization: bool = True
    halt_is_non_executable: bool = True
    unify_continue_and_no_action_plan_type: bool = True
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlanPolicy:
        allowed = {
            "policy_id",
            "policy_version",
            "regeneration_automatic_allowed",
            "revision_requires_human_authorization",
            "manual_review_requires_human_authorization",
            "halt_is_non_executable",
            "unify_continue_and_no_action_plan_type",
        }
        if set(values) - allowed:
            raise ValueError("unsupported execution-plan policy option")
        payload = {
            "policy_id": values.get(
                "policy_id", "standard_corrective_action_execution_plan"
            ),
            "policy_version": values.get("policy_version", POLICY_VERSION),
            "regeneration_automatic_allowed": values.get(
                "regeneration_automatic_allowed", False
            ),
            "revision_requires_human_authorization": values.get(
                "revision_requires_human_authorization", True
            ),
            "manual_review_requires_human_authorization": values.get(
                "manual_review_requires_human_authorization", True
            ),
            "halt_is_non_executable": values.get("halt_is_non_executable", True),
            "unify_continue_and_no_action_plan_type": values.get(
                "unify_continue_and_no_action_plan_type", True
            ),
        }
        return cls(**payload, policy_fingerprint=fingerprint(payload))

    @field_validator("policy_id")
    @classmethod
    def nonempty_policy_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("policy ID must be nonempty")
        return value

    @field_validator("policy_version")
    @classmethod
    def supported_policy_version(cls, value: str) -> str:
        if value != POLICY_VERSION:
            raise ValueError("unsupported execution-plan policy version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "policy_fingerprint")


class CorrectiveActionExecutionPlanRequest(FrozenModel):
    """A complete authoritative decision result plus planning policy."""

    decision_result: CorrectiveActionDecisionResult
    planning_policy: CorrectiveActionExecutionPlanPolicy
    contract_version: str = CONTRACT_VERSION
    request_fingerprint: str

    @classmethod
    def build(
        cls,
        decision_result: CorrectiveActionDecisionResult,
        planning_policy: CorrectiveActionExecutionPlanPolicy,
    ) -> CorrectiveActionExecutionPlanRequest:
        identity = _request_identity(decision_result, planning_policy, CONTRACT_VERSION)
        return cls(
            decision_result=decision_result,
            planning_policy=planning_policy,
            request_fingerprint=fingerprint(identity),
        )

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported execution-plan request version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            _request_identity(
                self.decision_result,
                self.planning_policy,
                self.contract_version,
            )
        )
        if self.request_fingerprint != expected:
            raise ValueError("request fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionPreconditions(FrozenModel):
    """Provider-independent prerequisites declared by a plan."""

    requires_valid_decision_result: bool = True
    requires_supported_action: bool = True
    requires_executor_capability: bool = False
    requires_human_authorization: bool = False
    requires_original_draft: bool = False
    requires_generation_context: bool = False
    requires_manual_review_destination: bool = False


def _canonical_preconditions(
    plan_type: CorrectiveActionExecutionPlanType,
    execution_mode: CorrectiveActionExecutionMode,
) -> CorrectiveActionExecutionPreconditions:
    """Return the one canonical typed precondition set for a plan."""

    human_gated = execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
    if plan_type is CorrectiveActionExecutionPlanType.REVISE_DRAFT:
        return CorrectiveActionExecutionPreconditions(
            requires_executor_capability=True,
            requires_human_authorization=human_gated,
            requires_original_draft=True,
        )
    if plan_type is CorrectiveActionExecutionPlanType.REGENERATE_DRAFT:
        return CorrectiveActionExecutionPreconditions(
            requires_executor_capability=True,
            requires_human_authorization=human_gated,
            requires_generation_context=True,
        )
    if plan_type is CorrectiveActionExecutionPlanType.CREATE_MANUAL_REVIEW_REQUEST:
        return CorrectiveActionExecutionPreconditions(
            requires_executor_capability=True,
            requires_human_authorization=human_gated,
            requires_manual_review_destination=True,
        )
    return CorrectiveActionExecutionPreconditions()


class CorrectiveActionExecutionPlan(FrozenModel):
    """Immutable plan for a future executor; not evidence of execution."""

    contract_version: str = CONTRACT_VERSION
    plan_type: CorrectiveActionExecutionPlanType
    execution_mode: CorrectiveActionExecutionMode
    required_capability: CorrectiveActionExecutionCapability
    source_action: CorrectiveAction
    source_reason: CorrectiveActionDecisionReason
    automatic_execution_allowed: bool
    human_authorization_required: bool
    preconditions: CorrectiveActionExecutionPreconditions
    decision_result: CorrectiveActionDecisionResult
    policy_fingerprint: str
    request_fingerprint: str
    plan_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlan:
        mode = values["execution_mode"]
        values.setdefault(
            "automatic_execution_allowed",
            mode is CorrectiveActionExecutionMode.AUTOMATIC,
        )
        values.setdefault(
            "human_authorization_required",
            mode is CorrectiveActionExecutionMode.HUMAN_GATED,
        )
        values.setdefault("contract_version", CONTRACT_VERSION)
        values["plan_fingerprint"] = fingerprint(_plan_identity(values))
        return cls.model_validate(values)

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported execution-plan contract version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        automatic = self.execution_mode is CorrectiveActionExecutionMode.AUTOMATIC
        human_gated = self.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
        if self.automatic_execution_allowed is not automatic:
            raise ValueError("automatic-execution flag contradicts execution mode")
        if self.human_authorization_required is not human_gated:
            raise ValueError("human-authorization flag contradicts execution mode")
        if (
            self.preconditions.requires_human_authorization
            is not self.human_authorization_required
        ):
            raise ValueError("authorization precondition contradicts execution mode")
        _validate_plan_characteristics(
            self.plan_type, self.execution_mode, self.required_capability
        )
        if self.preconditions != _canonical_preconditions(
            self.plan_type, self.execution_mode
        ):
            raise ValueError("plan preconditions are not canonical")
        _validate_completed_decision(self.decision_result)
        decision = self.decision_result.decision
        if decision is None or (
            self.source_action is not decision.action
            or self.source_reason is not decision.reason
        ):
            raise ValueError("plan does not preserve source decision semantics")
        expected = fingerprint(_plan_identity(self.model_dump(mode="python")))
        if self.plan_fingerprint != expected:
            raise ValueError("plan fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionPlanDiagnostic(FrozenModel):
    """Safe planning failure metadata without raw source content."""

    code: CorrectiveActionExecutionPlanDiagnosticCode
    safe_message: str
    stage: CorrectiveActionExecutionPlanStage
    contract_version: str = CONTRACT_VERSION
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlanDiagnostic:
        values.setdefault("contract_version", CONTRACT_VERSION)
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_message")
    @classmethod
    def safe_message_valid(cls, value: str) -> str:
        if not value.strip() or len(value) > 240:
            raise ValueError("diagnostic message must be concise and nonempty")
        forbidden = ("\\", "/", "traceback", "api_key", "prompt", "evidence")
        if any(token in value.casefold() for token in forbidden):
            raise ValueError("diagnostic message contains unsafe content")
        return value

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported diagnostic contract version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class CorrectiveActionExecutionPlanReport(FrozenModel):
    """Non-authoritative, content-safe projection of a planning result."""

    report_version: str = REPORT_VERSION
    operational_outcome: CorrectiveActionExecutionPlanOutcome
    plan_type: CorrectiveActionExecutionPlanType | None
    execution_mode: CorrectiveActionExecutionMode | None
    required_capability: CorrectiveActionExecutionCapability | None
    source_action: CorrectiveAction | None
    source_reason: CorrectiveActionDecisionReason | None
    automatic_execution_allowed: bool | None
    human_authorization_required: bool | None
    diagnostic_code: CorrectiveActionExecutionPlanDiagnosticCode | None
    request_fingerprint: str | None
    policy_fingerprint: str | None
    plan_fingerprint: str | None
    input_complete: bool
    plan_complete: bool
    decision_result_fingerprint: str | None = None
    final_lifecycle_phase: str | None = None
    lifecycle_revision: int | None = None
    state_fingerprint: str | None = None
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlanReport:
        values.setdefault("report_version", REPORT_VERSION)
        values.setdefault("decision_result_fingerprint", None)
        values.setdefault("final_lifecycle_phase", None)
        values.setdefault("lifecycle_revision", None)
        values.setdefault("state_fingerprint", None)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("report_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != REPORT_VERSION:
            raise ValueError("unsupported execution-plan report version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "report_fingerprint")


class CorrectiveActionExecutionPlanResult(FrozenModel):
    """Planning operation result with mutually exclusive plan/diagnostic."""

    contract_version: str = CONTRACT_VERSION
    operational_outcome: CorrectiveActionExecutionPlanOutcome
    plan: CorrectiveActionExecutionPlan | None
    diagnostic: CorrectiveActionExecutionPlanDiagnostic | None
    report: CorrectiveActionExecutionPlanReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlanResult:
        values.setdefault("contract_version", CONTRACT_VERSION)
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported execution-plan result version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        completed = (
            self.operational_outcome is CorrectiveActionExecutionPlanOutcome.COMPLETED
        )
        if completed != (self.plan is not None):
            raise ValueError("completed planning requires exactly one plan")
        if completed and self.diagnostic is not None:
            raise ValueError("completed planning forbids an error diagnostic")
        if not completed and self.diagnostic is None:
            raise ValueError("failed planning requires a safe diagnostic")
        if self.report.operational_outcome is not self.operational_outcome:
            raise ValueError("report operational outcome is inconsistent")
        if self.report.plan_fingerprint != (
            self.plan.plan_fingerprint if self.plan else None
        ):
            raise ValueError("report plan identity is inconsistent")
        if self.report.diagnostic_code != (
            self.diagnostic.code if self.diagnostic else None
        ):
            raise ValueError("report diagnostic is inconsistent")
        _validate_result_report(self)
        expected = fingerprint(_result_identity(self.model_dump(mode="python")))
        if self.result_fingerprint != expected:
            raise ValueError("result fingerprint is inconsistent")
        return self


def _validate_completed_decision(result: CorrectiveActionDecisionResult) -> None:
    if result.descriptor.contract_version != DECISION_CONTRACT_VERSION:
        raise ValueError("unsupported corrective-action decision contract version")
    if result.operational_outcome is not CorrectiveActionDecisionOutcome.COMPLETED:
        raise ValueError("execution plan requires a completed decision result")
    if result.decision is None:
        raise ValueError("completed decision result has no decision")


def _validate_plan_characteristics(plan_type, execution_mode, capability) -> None:
    expected_capability = {
        CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION: (
            CorrectiveActionExecutionCapability.NONE
        ),
        CorrectiveActionExecutionPlanType.REVISE_DRAFT: (
            CorrectiveActionExecutionCapability.DRAFT_REVISION
        ),
        CorrectiveActionExecutionPlanType.REGENERATE_DRAFT: (
            CorrectiveActionExecutionCapability.DRAFT_REGENERATION
        ),
        CorrectiveActionExecutionPlanType.CREATE_MANUAL_REVIEW_REQUEST: (
            CorrectiveActionExecutionCapability.MANUAL_REVIEW_ROUTING
        ),
        CorrectiveActionExecutionPlanType.BLOCK_AUTOMATIC_CONTINUATION: (
            CorrectiveActionExecutionCapability.WORKFLOW_CONTINUATION_BLOCK
        ),
    }
    if capability is not expected_capability[plan_type]:
        raise ValueError("plan type and required capability are inconsistent")
    non_executable = {
        CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION,
        CorrectiveActionExecutionPlanType.BLOCK_AUTOMATIC_CONTINUATION,
    }
    if (plan_type in non_executable) is not (
        execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE
    ):
        raise ValueError("plan type and execution mode are inconsistent")


def _validate_result_report(result: CorrectiveActionExecutionPlanResult) -> None:
    report = result.report
    plan = result.plan
    if report.plan_complete is not (plan is not None):
        raise ValueError("report plan completeness is inconsistent")
    expected = {
        "input_complete": True if plan else report.input_complete,
        "plan_type": plan.plan_type if plan else None,
        "execution_mode": plan.execution_mode if plan else None,
        "required_capability": plan.required_capability if plan else None,
        "source_action": plan.source_action if plan else None,
        "source_reason": plan.source_reason if plan else None,
        "automatic_execution_allowed": (
            plan.automatic_execution_allowed if plan else None
        ),
        "human_authorization_required": (
            plan.human_authorization_required if plan else None
        ),
        "request_fingerprint": (
            plan.request_fingerprint if plan else report.request_fingerprint
        ),
        "policy_fingerprint": (
            plan.policy_fingerprint if plan else report.policy_fingerprint
        ),
        "plan_fingerprint": plan.plan_fingerprint if plan else None,
        "decision_result_fingerprint": (
            plan.decision_result.result_fingerprint
            if plan
            else report.decision_result_fingerprint
        ),
    }
    if any(getattr(report, field) != value for field, value in expected.items()):
        raise ValueError("report projection contradicts planning result")


def _request_identity(decision_result, policy, contract_version):
    return {
        "contract_version": contract_version,
        "decision_result_fingerprint": decision_result.result_fingerprint,
        "planning_policy_fingerprint": policy.policy_fingerprint,
    }


def _plan_identity(values):
    decision_result = values["decision_result"]
    preconditions = values["preconditions"]
    return {
        "contract_version": values["contract_version"],
        "decision_result_fingerprint": _field(decision_result, "result_fingerprint"),
        "source_action": values["source_action"],
        "source_reason": values["source_reason"],
        "plan_type": values["plan_type"],
        "execution_mode": values["execution_mode"],
        "required_capability": values["required_capability"],
        "policy_fingerprint": values["policy_fingerprint"],
        "request_fingerprint": values["request_fingerprint"],
        "preconditions": (
            preconditions.model_dump(mode="python")
            if isinstance(preconditions, FrozenModel)
            else preconditions
        ),
    }


def _result_identity(values):
    plan = values.get("plan")
    diagnostic = values.get("diagnostic")
    report = values["report"]
    return {
        "contract_version": values["contract_version"],
        "operational_outcome": values["operational_outcome"],
        "plan_fingerprint": _field(plan, "plan_fingerprint") if plan else None,
        "diagnostic_fingerprint": (
            _field(diagnostic, "diagnostic_fingerprint") if diagnostic else None
        ),
        "report_fingerprint": _field(report, "report_fingerprint"),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
