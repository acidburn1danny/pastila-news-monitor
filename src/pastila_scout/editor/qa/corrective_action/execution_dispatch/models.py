"""Immutable public contracts for M6C.6B execution dispatch."""

import re
from typing import Any

from pydantic import field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanResult,
    CorrectiveActionExecutionPlanType,
    validate_execution_plan_result,
)
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionDispatchOutcome,
    CorrectiveActionExecutionDispatchStatus,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
)

CONTRACT_VERSION = "1"
POLICY_VERSION = "1"
CONTEXT_VERSION = "1"
EXECUTOR_DESCRIPTOR_VERSION = "1"
EXECUTOR_CONTRACT_VERSION = "1"
EXECUTOR_REQUEST_VERSION = "1"
EXECUTOR_RESULT_VERSION = "1"
EXECUTOR_RESULT_OUTPUT_VERSION = "2"
OUTPUT_REFERENCE_VERSION = "1"
DIAGNOSTIC_VERSION = "1"
DISPATCH_RESULT_VERSION = "1"
REPORT_VERSION = "1"

_IDENTIFIER = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,78}[a-z0-9])?$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_BANNED_IDENTIFIER_PARTS = ("secret", "token", "password", "api-key", "api.key")


class CorrectiveActionExecutionDispatchPolicy(FrozenModel):
    """Dispatch-only policy that cannot reinterpret an upstream plan."""

    policy_id: str = "standard-corrective-action-execution-dispatch"
    policy_version: str = POLICY_VERSION
    allow_automatic_dispatch: bool = True
    require_registered_executor: bool = True
    require_exact_capability_match: bool = True
    allow_human_gated_dispatch_request: bool = True
    treat_non_executable_as_completed: bool = True
    required_executor_contract_version: str = EXECUTOR_CONTRACT_VERSION
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchPolicy:
        allowed = {
            "policy_id",
            "policy_version",
            "allow_automatic_dispatch",
            "require_registered_executor",
            "require_exact_capability_match",
            "allow_human_gated_dispatch_request",
            "treat_non_executable_as_completed",
            "required_executor_contract_version",
        }
        if set(values) - allowed:
            raise ValueError("unsupported dispatch policy option")
        payload = {
            "policy_id": values.get(
                "policy_id", "standard-corrective-action-execution-dispatch"
            ),
            "policy_version": values.get("policy_version", POLICY_VERSION),
            "allow_automatic_dispatch": values.get("allow_automatic_dispatch", True),
            "require_registered_executor": values.get(
                "require_registered_executor", True
            ),
            "require_exact_capability_match": values.get(
                "require_exact_capability_match", True
            ),
            "allow_human_gated_dispatch_request": values.get(
                "allow_human_gated_dispatch_request", True
            ),
            "treat_non_executable_as_completed": values.get(
                "treat_non_executable_as_completed", True
            ),
            "required_executor_contract_version": values.get(
                "required_executor_contract_version", EXECUTOR_CONTRACT_VERSION
            ),
        }
        return cls(**payload, policy_fingerprint=fingerprint(payload))

    @field_validator("policy_id")
    @classmethod
    def policy_id_valid(cls, value: str) -> str:
        return _validated_identifier(value, "policy ID")

    @field_validator("policy_version")
    @classmethod
    def policy_version_supported(cls, value: str) -> str:
        if value != POLICY_VERSION:
            raise ValueError("unsupported dispatch policy version")
        return value

    @field_validator("required_executor_contract_version")
    @classmethod
    def executor_version_supported(cls, value: str) -> str:
        if value != EXECUTOR_CONTRACT_VERSION:
            raise ValueError("unsupported required executor contract version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if not self.require_registered_executor:
            raise ValueError("dispatch requires one registered executor")
        if not self.require_exact_capability_match:
            raise ValueError("dispatch requires exact capability matching")
        if not self.treat_non_executable_as_completed:
            raise ValueError("non-executable plans must complete without dispatch")
        return _validate_fingerprint(self, "policy_fingerprint")


class CorrectiveActionExecutionContext(FrozenModel):
    """Narrow safe metadata for a future dispatch attempt."""

    context_version: str = CONTEXT_VERSION
    authorization_state: CorrectiveActionAuthorizationState
    requested_executor_contract_version: str = EXECUTOR_CONTRACT_VERSION
    dispatch_attempt_id: str
    correlation_fingerprint: str | None = None
    approved_environment_id: str | None = None
    context_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionContext:
        values.setdefault("context_version", CONTEXT_VERSION)
        values.setdefault(
            "requested_executor_contract_version", EXECUTOR_CONTRACT_VERSION
        )
        values.setdefault("correlation_fingerprint", None)
        values.setdefault("approved_environment_id", None)
        values["context_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("context_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != CONTEXT_VERSION:
            raise ValueError("unsupported execution-context version")
        return value

    @field_validator("requested_executor_contract_version")
    @classmethod
    def executor_version_supported(cls, value: str) -> str:
        if value != EXECUTOR_CONTRACT_VERSION:
            raise ValueError("unsupported requested executor contract version")
        return value

    @field_validator("dispatch_attempt_id")
    @classmethod
    def attempt_id_valid(cls, value: str) -> str:
        return _validated_identifier(value, "dispatch-attempt ID")

    @field_validator("approved_environment_id")
    @classmethod
    def environment_id_valid(cls, value: str | None) -> str | None:
        return (
            _validated_identifier(value, "environment ID")
            if value is not None
            else None
        )

    @field_validator("correlation_fingerprint")
    @classmethod
    def correlation_valid(cls, value: str | None) -> str | None:
        if value is not None and not _FINGERPRINT.fullmatch(value):
            raise ValueError("correlation fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "context_fingerprint")


class CorrectiveActionExecutionDispatchRequest(FrozenModel):
    """Complete authoritative planning result plus dispatch-only inputs."""

    contract_version: str = CONTRACT_VERSION
    planning_result: CorrectiveActionExecutionPlanResult
    policy: CorrectiveActionExecutionDispatchPolicy
    execution_context: CorrectiveActionExecutionContext
    request_fingerprint: str

    @classmethod
    def build(
        cls,
        planning_result: CorrectiveActionExecutionPlanResult,
        policy: CorrectiveActionExecutionDispatchPolicy,
        execution_context: CorrectiveActionExecutionContext,
    ) -> CorrectiveActionExecutionDispatchRequest:
        values = _dispatch_request_identity(
            planning_result, policy, execution_context, CONTRACT_VERSION
        )
        return cls(
            planning_result=planning_result,
            policy=policy,
            execution_context=execution_context,
            request_fingerprint=fingerprint(values),
        )

    @field_validator("contract_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported execution-dispatch request version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        validate_execution_plan_result(self.planning_result)
        expected = fingerprint(
            _dispatch_request_identity(
                self.planning_result,
                self.policy,
                self.execution_context,
                self.contract_version,
            )
        )
        if self.request_fingerprint != expected:
            raise ValueError("dispatch request fingerprint is inconsistent")
        return self


class CorrectiveActionExecutorDescriptor(FrozenModel):
    """One immutable exact-capability executor declaration."""

    descriptor_version: str = EXECUTOR_DESCRIPTOR_VERSION
    executor_id: str
    executor_contract_version: str = EXECUTOR_CONTRACT_VERSION
    supported_capability: CorrectiveActionExecutionCapability
    supported_plan_types: tuple[CorrectiveActionExecutionPlanType, ...]
    supports_automatic_invocation: bool
    supports_human_gated_invocation: bool
    descriptor_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutorDescriptor:
        values.setdefault("descriptor_version", EXECUTOR_DESCRIPTOR_VERSION)
        values.setdefault("executor_contract_version", EXECUTOR_CONTRACT_VERSION)
        values["supported_plan_types"] = tuple(
            sorted(values["supported_plan_types"], key=lambda item: item.value)
        )
        values["descriptor_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("descriptor_version")
    @classmethod
    def descriptor_version_supported(cls, value: str) -> str:
        if value != EXECUTOR_DESCRIPTOR_VERSION:
            raise ValueError("unsupported executor descriptor version")
        return value

    @field_validator("executor_contract_version")
    @classmethod
    def executor_version_supported(cls, value: str) -> str:
        if value != EXECUTOR_CONTRACT_VERSION:
            raise ValueError("unsupported executor contract version")
        return value

    @field_validator("executor_id")
    @classmethod
    def executor_id_valid(cls, value: str) -> str:
        return _validated_identifier(value, "executor ID")

    @model_validator(mode="after")
    def invariants(self):
        if self.supported_capability is CorrectiveActionExecutionCapability.NONE:
            raise ValueError("executor cannot advertise NONE capability")
        if not self.supported_plan_types:
            raise ValueError("executor must advertise at least one plan type")
        canonical = tuple(
            sorted(self.supported_plan_types, key=lambda item: item.value)
        )
        if canonical != self.supported_plan_types or len(set(canonical)) != len(
            canonical
        ):
            raise ValueError("supported plan types must be unique and canonical")
        if any(
            _required_capability(plan_type) is not self.supported_capability
            for plan_type in self.supported_plan_types
        ):
            raise ValueError("executor capability and plan types are incompatible")
        if not (
            self.supports_automatic_invocation or self.supports_human_gated_invocation
        ):
            raise ValueError("executor must support at least one invocation mode")
        return _validate_fingerprint(self, "descriptor_fingerprint")


class CorrectiveActionExecutorRequest(FrozenModel):
    """Immutable generic request preserving the authoritative plan identity."""

    request_version: str = EXECUTOR_REQUEST_VERSION
    planning_result: CorrectiveActionExecutionPlanResult
    plan: CorrectiveActionExecutionPlan
    executor_descriptor: CorrectiveActionExecutorDescriptor
    execution_context: CorrectiveActionExecutionContext
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutorRequest:
        values.setdefault("request_version", EXECUTOR_REQUEST_VERSION)
        values["request_fingerprint"] = fingerprint(_executor_request_identity(values))
        return cls.model_validate(values)

    @field_validator("request_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != EXECUTOR_REQUEST_VERSION:
            raise ValueError("unsupported executor request version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        validate_execution_plan_result(self.planning_result)
        if self.planning_result.plan is not self.plan:
            raise ValueError("executor request does not preserve plan identity")
        descriptor = self.executor_descriptor
        if descriptor.supported_capability is not self.plan.required_capability:
            raise ValueError("executor capability does not match plan capability")
        if self.plan.plan_type not in descriptor.supported_plan_types:
            raise ValueError("executor does not support plan type")
        if self.plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE:
            raise ValueError("non-executable plan cannot reach an executor")
        if self.plan.execution_mode is CorrectiveActionExecutionMode.AUTOMATIC:
            if not descriptor.supports_automatic_invocation:
                raise ValueError("executor does not support automatic invocation")
            if (
                self.execution_context.authorization_state
                is not CorrectiveActionAuthorizationState.NOT_REQUIRED
            ):
                raise ValueError("automatic plan requires NOT_REQUIRED authorization")
        if self.plan.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED:
            if not descriptor.supports_human_gated_invocation:
                raise ValueError("executor does not support human-gated invocation")
            if (
                self.execution_context.authorization_state
                is not CorrectiveActionAuthorizationState.GRANTED
            ):
                raise ValueError("human-gated plan requires granted authorization")
        expected = fingerprint(
            _executor_request_identity(self.model_dump(mode="python"))
        )
        if self.request_fingerprint != expected:
            raise ValueError("executor request fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionDispatchDiagnostic(FrozenModel):
    """Immutable content-safe dispatch or generic executor diagnostic."""

    diagnostic_version: str = DIAGNOSTIC_VERSION
    code: CorrectiveActionExecutionDispatchDiagnosticCode
    category: CorrectiveActionExecutionDispatchDiagnosticCategory
    safe_message: str
    fingerprint_references: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchDiagnostic:
        values.setdefault("diagnostic_version", DIAGNOSTIC_VERSION)
        values["fingerprint_references"] = tuple(
            sorted(values.get("fingerprint_references", ()))
        )
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("diagnostic_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != DIAGNOSTIC_VERSION:
            raise ValueError("unsupported dispatch diagnostic version")
        return value

    @field_validator("safe_message")
    @classmethod
    def safe_message_valid(cls, value: str) -> str:
        if not value.strip() or len(value) > 240:
            raise ValueError("diagnostic message must be concise and nonempty")
        forbidden = (
            "\\",
            "/",
            "api_key",
            "secret",
            "token",
            "traceback",
            "prompt",
            "@",
        )
        if any(item in value.casefold() for item in forbidden):
            raise ValueError("diagnostic message contains unsafe content")
        return value

    @field_validator("fingerprint_references")
    @classmethod
    def references_valid(cls, value):
        allowed = {
            "planning_result",
            "plan",
            "dispatch_request",
            "policy",
            "execution_context",
            "executor_descriptor",
            "executor_request",
            "executor_result",
        }
        keys = tuple(key for key, _ in value)
        if len(keys) != len(set(keys)) or not set(keys) <= allowed:
            raise ValueError("diagnostic fingerprint references are not canonical")
        if any(not _FINGERPRINT.fullmatch(reference) for _, reference in value):
            raise ValueError("diagnostic fingerprint reference is invalid")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class CorrectiveActionOutputReference(FrozenModel):
    """Immutable capability-neutral reference to an executor-owned output."""

    reference_version: str = OUTPUT_REFERENCE_VERSION
    output_type: str
    capability: CorrectiveActionExecutionCapability
    output_fingerprint: str
    capability_result_fingerprint: str
    reference_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionOutputReference:
        values.setdefault("reference_version", OUTPUT_REFERENCE_VERSION)
        values["reference_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("output_type")
    @classmethod
    def output_type_valid(cls, value: str) -> str:
        return _validated_identifier(value, "output type")

    @field_validator("output_fingerprint", "capability_result_fingerprint")
    @classmethod
    def output_fingerprint_valid(cls, value: str) -> str:
        if not _FINGERPRINT.fullmatch(value):
            raise ValueError("output-reference fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        if self.reference_version != OUTPUT_REFERENCE_VERSION:
            raise ValueError("unsupported output-reference version")
        if self.capability is CorrectiveActionExecutionCapability.NONE:
            raise ValueError("output reference requires an executable capability")
        return _validate_fingerprint(self, "reference_fingerprint")


class CorrectiveActionExecutorResult(FrozenModel):
    """Capability-neutral immutable executor result without output payload."""

    result_version: str = EXECUTOR_RESULT_VERSION
    executor_descriptor: CorrectiveActionExecutorDescriptor
    request: CorrectiveActionExecutorRequest
    operational_outcome: CorrectiveActionExecutorOutcome
    execution_status: CorrectiveActionExecutionStatus
    output_reference: CorrectiveActionOutputReference | None = None
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic | None
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutorResult:
        values.setdefault(
            "result_version",
            (
                EXECUTOR_RESULT_OUTPUT_VERSION
                if values.get("output_reference") is not None
                else EXECUTOR_RESULT_VERSION
            ),
        )
        values["result_fingerprint"] = fingerprint(_executor_result_identity(values))
        return cls.model_validate(values)

    @field_validator("result_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value not in {EXECUTOR_RESULT_VERSION, EXECUTOR_RESULT_OUTPUT_VERSION}:
            raise ValueError("unsupported executor result version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.request.executor_descriptor is not self.executor_descriptor:
            raise ValueError("executor result does not preserve descriptor identity")
        completed = (
            self.operational_outcome is CorrectiveActionExecutorOutcome.COMPLETED
        )
        if completed != (
            self.execution_status is CorrectiveActionExecutionStatus.COMPLETED
        ):
            raise ValueError("executor outcome and execution status are inconsistent")
        if completed == (self.diagnostic is not None):
            raise ValueError("executor diagnostic presence is inconsistent")
        if self.result_version == EXECUTOR_RESULT_VERSION and self.output_reference:
            raise ValueError(
                "version 1 executor result cannot contain output reference"
            )
        if (
            self.result_version == EXECUTOR_RESULT_OUTPUT_VERSION
            and self.output_reference is None
        ):
            raise ValueError("version 2 executor result requires output reference")
        if self.output_reference is not None:
            if not completed:
                raise ValueError(
                    "failed executor result cannot contain output reference"
                )
            if self.output_reference.capability is not self.plan_capability:
                raise ValueError("executor output capability is inconsistent")
        expected = fingerprint(
            _executor_result_identity(self.model_dump(mode="python"))
        )
        if self.result_fingerprint != expected:
            raise ValueError("executor result fingerprint is inconsistent")
        return self

    @property
    def plan_capability(self) -> CorrectiveActionExecutionCapability:
        return self.request.plan.required_capability


class CorrectiveActionExecutionDispatchReport(FrozenModel):
    """Non-authoritative safe dispatch projection."""

    report_version: str = REPORT_VERSION
    operational_outcome: CorrectiveActionExecutionDispatchOutcome
    dispatch_status: CorrectiveActionExecutionDispatchStatus
    planning_outcome: CorrectiveActionExecutionPlanOutcome
    plan_type: CorrectiveActionExecutionPlanType | None
    execution_mode: CorrectiveActionExecutionMode | None
    required_capability: CorrectiveActionExecutionCapability | None
    authorization_state: CorrectiveActionAuthorizationState
    executor_id: str | None
    executor_contract_version: str | None
    executor_outcome: CorrectiveActionExecutorOutcome | None
    execution_status: CorrectiveActionExecutionStatus | None
    diagnostic_code: CorrectiveActionExecutionDispatchDiagnosticCode | None
    dispatch_request_fingerprint: str
    planning_result_fingerprint: str
    plan_fingerprint: str | None
    executor_descriptor_fingerprint: str | None
    executor_request_fingerprint: str | None
    executor_result_fingerprint: str | None
    planning_result_validated: bool
    dispatch_eligible: bool
    executor_resolved: bool
    executor_invoked: bool
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchReport:
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("report_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != REPORT_VERSION:
            raise ValueError("unsupported dispatch report version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "report_fingerprint")


class CorrectiveActionExecutionDispatchResult(FrozenModel):
    """Authoritative immutable dispatch result contract."""

    result_version: str = DISPATCH_RESULT_VERSION
    request: CorrectiveActionExecutionDispatchRequest
    operational_outcome: CorrectiveActionExecutionDispatchOutcome
    dispatch_status: CorrectiveActionExecutionDispatchStatus
    executor_descriptor: CorrectiveActionExecutorDescriptor | None
    executor_request: CorrectiveActionExecutorRequest | None
    executor_result: CorrectiveActionExecutorResult | None
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic | None
    report: CorrectiveActionExecutionDispatchReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchResult:
        values.setdefault("result_version", DISPATCH_RESULT_VERSION)
        values["result_fingerprint"] = fingerprint(_dispatch_result_identity(values))
        return cls.model_validate(values)

    @field_validator("result_version")
    @classmethod
    def version_supported(cls, value: str) -> str:
        if value != DISPATCH_RESULT_VERSION:
            raise ValueError("unsupported dispatch result version")
        return value

    @model_validator(mode="after")
    def invariants(self):
        _validate_dispatch_result_shape(self)
        _validate_dispatch_report(self)
        expected = fingerprint(
            _dispatch_result_identity(self.model_dump(mode="python"))
        )
        if self.result_fingerprint != expected:
            raise ValueError("dispatch result fingerprint is inconsistent")
        return self


def _required_capability(
    plan_type: CorrectiveActionExecutionPlanType,
) -> CorrectiveActionExecutionCapability:
    return {
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
    }[plan_type]


def _validate_dispatch_result_shape(
    result: CorrectiveActionExecutionDispatchResult,
) -> None:
    status = result.dispatch_status
    descriptor = result.executor_descriptor
    executor_request = result.executor_request
    executor_result = result.executor_result
    diagnostic = result.diagnostic
    completed = (
        result.operational_outcome is CorrectiveActionExecutionDispatchOutcome.COMPLETED
    )
    planning_completed = (
        result.request.planning_result.operational_outcome
        is CorrectiveActionExecutionPlanOutcome.COMPLETED
    )
    plan = result.request.planning_result.plan
    if not planning_completed and (
        completed
        or any(
            item is not None for item in (descriptor, executor_request, executor_result)
        )
    ):
        raise ValueError("failed planning result cannot become dispatchable")
    if (
        plan is not None
        and plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE
        and status is not CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE
    ):
        raise ValueError("non-executable plan must remain non-dispatchable")
    completed_statuses = {
        CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
        CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION,
        CorrectiveActionExecutionDispatchStatus.DISPATCHED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
    }
    if completed != (status in completed_statuses):
        raise ValueError("dispatch outcome and status are inconsistent")
    if status is CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE:
        if any(
            item is not None
            for item in (descriptor, executor_request, executor_result, diagnostic)
        ):
            raise ValueError("non-dispatchable result must not contain executor state")
    elif status is CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION:
        if (
            executor_request is not None
            or executor_result is not None
            or diagnostic is None
        ):
            raise ValueError("authorization-gated result shape is inconsistent")
        if (
            plan is None
            or plan.execution_mode is not CorrectiveActionExecutionMode.HUMAN_GATED
        ):
            raise ValueError("only human-gated plans may await authorization")
        if (
            result.request.execution_context.authorization_state
            is CorrectiveActionAuthorizationState.GRANTED
        ):
            raise ValueError("authorized plan cannot await authorization")
    elif status is CorrectiveActionExecutionDispatchStatus.DISPATCHED:
        if (
            descriptor is None
            or executor_request is None
            or executor_result is not None
            or diagnostic is not None
        ):
            raise ValueError("dispatched result shape is inconsistent")
    elif status in {
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
    }:
        if (
            descriptor is None
            or executor_request is None
            or executor_result is None
            or diagnostic is not None
        ):
            raise ValueError("executor terminal result shape is inconsistent")
        executor_completed = (
            executor_result.operational_outcome
            is CorrectiveActionExecutorOutcome.COMPLETED
        )
        if executor_completed != (
            status is CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED
        ):
            raise ValueError("dispatch status contradicts executor outcome")
    elif status in {
        CorrectiveActionExecutionDispatchStatus.NOT_ATTEMPTED,
        CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
    }:
        if executor_result is not None or diagnostic is None:
            raise ValueError(
                "dispatch failure requires a diagnostic and no executor result"
            )
        if executor_request is not None and descriptor is None:
            raise ValueError("executor request requires its descriptor")
    if executor_request is not None:
        if executor_request.executor_descriptor is not descriptor:
            raise ValueError("dispatch result does not preserve descriptor identity")
        if executor_request.planning_result is not result.request.planning_result:
            raise ValueError("dispatch result does not preserve planning identity")
    invoked = status in {
        CorrectiveActionExecutionDispatchStatus.DISPATCHED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
    }
    if invoked and plan is not None:
        if (
            plan.execution_mode is CorrectiveActionExecutionMode.AUTOMATIC
            and not result.request.policy.allow_automatic_dispatch
        ):
            raise ValueError("automatic dispatch is disabled by policy")
        if (
            plan.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
            and not result.request.policy.allow_human_gated_dispatch_request
        ):
            raise ValueError("human-gated dispatch is disabled by policy")
    if executor_result is not None and executor_result.request is not executor_request:
        raise ValueError("dispatch result does not preserve executor request identity")


def _validate_dispatch_report(result: CorrectiveActionExecutionDispatchResult) -> None:
    report = result.report
    planning_result = result.request.planning_result
    plan = planning_result.plan
    descriptor = result.executor_descriptor
    executor_result = result.executor_result
    effective_diagnostic = result.diagnostic or (
        executor_result.diagnostic if executor_result else None
    )
    executable = bool(
        plan
        and plan.execution_mode is not CorrectiveActionExecutionMode.NON_EXECUTABLE
        and plan.required_capability is not CorrectiveActionExecutionCapability.NONE
    )
    invoked = result.dispatch_status in {
        CorrectiveActionExecutionDispatchStatus.DISPATCHED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
    }
    expected = {
        "operational_outcome": result.operational_outcome,
        "dispatch_status": result.dispatch_status,
        "planning_outcome": planning_result.operational_outcome,
        "plan_type": plan.plan_type if plan else None,
        "execution_mode": plan.execution_mode if plan else None,
        "required_capability": plan.required_capability if plan else None,
        "authorization_state": result.request.execution_context.authorization_state,
        "executor_id": descriptor.executor_id if descriptor else None,
        "executor_contract_version": (
            descriptor.executor_contract_version if descriptor else None
        ),
        "executor_outcome": (
            executor_result.operational_outcome if executor_result else None
        ),
        "execution_status": (
            executor_result.execution_status if executor_result else None
        ),
        "diagnostic_code": effective_diagnostic.code if effective_diagnostic else None,
        "dispatch_request_fingerprint": result.request.request_fingerprint,
        "planning_result_fingerprint": planning_result.result_fingerprint,
        "plan_fingerprint": plan.plan_fingerprint if plan else None,
        "executor_descriptor_fingerprint": (
            descriptor.descriptor_fingerprint if descriptor else None
        ),
        "executor_request_fingerprint": (
            result.executor_request.request_fingerprint
            if result.executor_request
            else None
        ),
        "executor_result_fingerprint": (
            executor_result.result_fingerprint if executor_result else None
        ),
        "planning_result_validated": True,
        "dispatch_eligible": executable
        and result.dispatch_status
        not in {
            CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
            CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION,
            CorrectiveActionExecutionDispatchStatus.NOT_ATTEMPTED,
        },
        "executor_resolved": descriptor is not None,
        "executor_invoked": invoked,
    }
    if any(getattr(report, field) != value for field, value in expected.items()):
        raise ValueError("dispatch report contradicts authoritative result")


def _dispatch_request_identity(planning_result, policy, context, version):
    return {
        "contract_version": version,
        "planning_result_fingerprint": planning_result.result_fingerprint,
        "policy_fingerprint": policy.policy_fingerprint,
        "execution_context_fingerprint": context.context_fingerprint,
    }


def _executor_request_identity(values):
    planning_result = values["planning_result"]
    plan = values["plan"]
    descriptor = values["executor_descriptor"]
    context = values["execution_context"]
    return {
        "request_version": values["request_version"],
        "planning_result_fingerprint": _field(planning_result, "result_fingerprint"),
        "plan_fingerprint": _field(plan, "plan_fingerprint"),
        "executor_descriptor_fingerprint": _field(descriptor, "descriptor_fingerprint"),
        "execution_context_fingerprint": _field(context, "context_fingerprint"),
    }


def _executor_result_identity(values):
    request = values["request"]
    diagnostic = values.get("diagnostic")
    identity = {
        "result_version": values["result_version"],
        "executor_request_fingerprint": _field(request, "request_fingerprint"),
        "operational_outcome": values["operational_outcome"],
        "execution_status": values["execution_status"],
        "diagnostic_code": _field(diagnostic, "code") if diagnostic else None,
    }
    version = values.get("result_version", EXECUTOR_RESULT_VERSION)
    if version == EXECUTOR_RESULT_OUTPUT_VERSION:
        output_reference = values.get("output_reference")
        identity["output_reference_fingerprint"] = (
            _field(output_reference, "reference_fingerprint")
            if output_reference
            else None
        )
    return identity


def _dispatch_result_identity(values):
    request = values["request"]
    descriptor = values.get("executor_descriptor")
    executor_request = values.get("executor_request")
    executor_result = values.get("executor_result")
    diagnostic = values.get("diagnostic")
    return {
        "result_version": values["result_version"],
        "dispatch_request_fingerprint": _field(request, "request_fingerprint"),
        "operational_outcome": values["operational_outcome"],
        "dispatch_status": values["dispatch_status"],
        "executor_descriptor_fingerprint": (
            _field(descriptor, "descriptor_fingerprint") if descriptor else None
        ),
        "executor_request_fingerprint": (
            _field(executor_request, "request_fingerprint")
            if executor_request
            else None
        ),
        "executor_result_fingerprint": (
            _field(executor_result, "result_fingerprint") if executor_result else None
        ),
        "diagnostic_code": _field(diagnostic, "code") if diagnostic else None,
    }


def _validated_identifier(value: str, label: str) -> str:
    if not _IDENTIFIER.fullmatch(value) or any(
        item in value for item in _BANNED_IDENTIFIER_PARTS
    ):
        raise ValueError(f"{label} is invalid")
    return value


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
