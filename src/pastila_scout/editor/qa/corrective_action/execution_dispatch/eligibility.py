"""Authoritative deterministic dispatch eligibility evaluation."""

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanResult,
    validate_execution_plan_result,
)
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
)
from .models import (
    CONTEXT_VERSION,
    POLICY_VERSION,
    CorrectiveActionExecutionContext,
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchPolicy,
)
from .validation import (
    validate_execution_context,
    validate_execution_dispatch_policy,
)

ELIGIBILITY_VERSION = "1"
ELIGIBILITY_REPORT_VERSION = "1"


class DispatchEligibilityStatus(StrEnum):
    """Explicit dispatch eligibility classification; never a boolean."""

    ELIGIBLE = "eligible"
    NOT_EXECUTABLE = "not_executable"
    AUTHORIZATION_REQUIRED = "authorization_required"
    POLICY_BLOCKED = "policy_blocked"
    INVALID_PLAN = "invalid_plan"
    INVALID_CONTEXT = "invalid_context"
    INVALID_POLICY = "invalid_policy"
    INTEGRITY_FAILURE = "integrity_failure"


class DispatchEligibilityResult(FrozenModel):
    """Immutable eligibility result preserving authoritative planning identity."""

    eligibility_version: str = ELIGIBILITY_VERSION
    plan_result: CorrectiveActionExecutionPlanResult
    policy: CorrectiveActionExecutionDispatchPolicy
    execution_context: CorrectiveActionExecutionContext
    status: DispatchEligibilityStatus
    required_capability: CorrectiveActionExecutionCapability | None
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic | None
    eligibility_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DispatchEligibilityResult:
        values.setdefault("eligibility_version", ELIGIBILITY_VERSION)
        values["eligibility_fingerprint"] = fingerprint(_eligibility_identity(values))
        return cls.model_validate(values)

    @classmethod
    def build_integrity_failure(cls, **values: Any) -> DispatchEligibilityResult:
        """Preserve a typed but corrupt input while classifying it as unsafe."""

        values.setdefault("eligibility_version", ELIGIBILITY_VERSION)
        values["eligibility_fingerprint"] = fingerprint(_eligibility_identity(values))
        result = cls.model_construct(**values)
        result.invariants()
        return result

    @model_validator(mode="after")
    def invariants(self):
        if self.eligibility_version != ELIGIBILITY_VERSION:
            raise ValueError("unsupported dispatch eligibility version")
        if (self.status is DispatchEligibilityStatus.ELIGIBLE) == (
            self.diagnostic is not None
        ):
            raise ValueError("eligibility diagnostic presence is inconsistent")
        plan = self.plan_result.plan
        if self.required_capability != (plan.required_capability if plan else None):
            raise ValueError("eligibility capability contradicts planning result")
        expected = fingerprint(_eligibility_identity(self.model_dump(mode="python")))
        if self.eligibility_fingerprint != expected:
            raise ValueError("eligibility fingerprint is inconsistent")
        return self


class DispatchEligibilityReport(FrozenModel):
    """Safe projection of eligibility status and lineage."""

    report_version: str = ELIGIBILITY_REPORT_VERSION
    status: DispatchEligibilityStatus
    required_capability: CorrectiveActionExecutionCapability | None
    diagnostic_code: CorrectiveActionExecutionDispatchDiagnosticCode | None
    plan_result_fingerprint: str
    plan_fingerprint: str | None
    policy_fingerprint: str
    context_fingerprint: str
    eligibility_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DispatchEligibilityReport:
        values.setdefault("report_version", ELIGIBILITY_REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.report_version != ELIGIBILITY_REPORT_VERSION:
            raise ValueError("unsupported eligibility report version")
        return _validate_fingerprint(self, "report_fingerprint")


class DispatchEligibilityEvaluator:
    """Classify dispatch eligibility without registry lookup or invocation."""

    def evaluate(
        self,
        plan_result: CorrectiveActionExecutionPlanResult,
        policy: CorrectiveActionExecutionDispatchPolicy,
        execution_context: CorrectiveActionExecutionContext,
    ) -> DispatchEligibilityResult:
        """Return one deterministic classification for the supplied contracts."""

        policy_failure = _policy_failure(policy)
        if policy_failure is not None:
            return _result(
                plan_result,
                policy,
                execution_context,
                *policy_failure,
            )
        context_failure = _context_failure(execution_context)
        if context_failure is not None:
            return _result(
                plan_result,
                policy,
                execution_context,
                *context_failure,
            )
        try:
            validate_execution_plan_result(plan_result)
        except (TypeError, ValueError):
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.INTEGRITY_FAILURE,
                CorrectiveActionExecutionDispatchDiagnosticCode.PLANNING_RESULT_FINGERPRINT_MISMATCH,
                CorrectiveActionExecutionDispatchDiagnosticCategory.VALIDATION,
            )
        if (
            plan_result.operational_outcome
            is not CorrectiveActionExecutionPlanOutcome.COMPLETED
            or plan_result.plan is None
        ):
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.INVALID_PLAN,
                CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_PLANNING_RESULT,
                CorrectiveActionExecutionDispatchDiagnosticCategory.ELIGIBILITY,
            )
        plan = plan_result.plan
        if (
            plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE
            or plan.required_capability is CorrectiveActionExecutionCapability.NONE
        ):
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.NOT_EXECUTABLE,
                CorrectiveActionExecutionDispatchDiagnosticCode.PLAN_NOT_DISPATCHABLE,
                CorrectiveActionExecutionDispatchDiagnosticCategory.ELIGIBILITY,
            )
        if plan.execution_mode is CorrectiveActionExecutionMode.AUTOMATIC:
            if not policy.allow_automatic_dispatch:
                return _result(
                    plan_result,
                    policy,
                    execution_context,
                    DispatchEligibilityStatus.POLICY_BLOCKED,
                    CorrectiveActionExecutionDispatchDiagnosticCode.AUTOMATIC_DISPATCH_DISABLED,
                    CorrectiveActionExecutionDispatchDiagnosticCategory.POLICY,
                )
            if (
                execution_context.authorization_state
                is not CorrectiveActionAuthorizationState.NOT_REQUIRED
            ):
                return _result(
                    plan_result,
                    policy,
                    execution_context,
                    DispatchEligibilityStatus.INVALID_CONTEXT,
                    CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_REQUEST,
                    CorrectiveActionExecutionDispatchDiagnosticCategory.AUTHORIZATION,
                )
            return _eligible(plan_result, policy, execution_context)
        if not policy.allow_human_gated_dispatch_request:
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.POLICY_BLOCKED,
                CorrectiveActionExecutionDispatchDiagnosticCode.HUMAN_AUTHORIZATION_REQUIRED,
                CorrectiveActionExecutionDispatchDiagnosticCategory.POLICY,
            )
        authorization = execution_context.authorization_state
        if authorization is CorrectiveActionAuthorizationState.GRANTED:
            return _eligible(plan_result, policy, execution_context)
        if authorization is CorrectiveActionAuthorizationState.DENIED:
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.POLICY_BLOCKED,
                CorrectiveActionExecutionDispatchDiagnosticCode.HUMAN_AUTHORIZATION_DENIED,
                CorrectiveActionExecutionDispatchDiagnosticCategory.AUTHORIZATION,
            )
        if authorization in {
            CorrectiveActionAuthorizationState.REQUIRED_NOT_GRANTED,
            CorrectiveActionAuthorizationState.UNKNOWN,
        }:
            return _result(
                plan_result,
                policy,
                execution_context,
                DispatchEligibilityStatus.AUTHORIZATION_REQUIRED,
                CorrectiveActionExecutionDispatchDiagnosticCode.HUMAN_AUTHORIZATION_REQUIRED,
                CorrectiveActionExecutionDispatchDiagnosticCategory.AUTHORIZATION,
            )
        return _result(
            plan_result,
            policy,
            execution_context,
            DispatchEligibilityStatus.INVALID_CONTEXT,
            CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_REQUEST,
            CorrectiveActionExecutionDispatchDiagnosticCategory.AUTHORIZATION,
        )


def build_dispatch_eligibility_report(
    result: DispatchEligibilityResult,
) -> DispatchEligibilityReport:
    """Build a safe deterministic eligibility projection."""

    plan = result.plan_result.plan
    return DispatchEligibilityReport.build(
        status=result.status,
        required_capability=result.required_capability,
        diagnostic_code=result.diagnostic.code if result.diagnostic else None,
        plan_result_fingerprint=result.plan_result.result_fingerprint,
        plan_fingerprint=plan.plan_fingerprint if plan else None,
        policy_fingerprint=result.policy.policy_fingerprint,
        context_fingerprint=result.execution_context.context_fingerprint,
        eligibility_fingerprint=result.eligibility_fingerprint,
    )


def validate_dispatch_eligibility_result(result: DispatchEligibilityResult) -> None:
    """Validate eligibility shape, identity fields, and deterministic fingerprint."""

    if not isinstance(result, DispatchEligibilityResult):
        raise TypeError("invalid dispatch eligibility result")
    result.invariants()


def _eligible(plan_result, policy, context):
    return DispatchEligibilityResult.build(
        plan_result=plan_result,
        policy=policy,
        execution_context=context,
        status=DispatchEligibilityStatus.ELIGIBLE,
        required_capability=plan_result.plan.required_capability,
        diagnostic=None,
    )


def _result(plan_result, policy, context, status, code, category):
    plan = (
        plan_result.plan
        if isinstance(plan_result, CorrectiveActionExecutionPlanResult)
        else None
    )
    diagnostic = CorrectiveActionExecutionDispatchDiagnostic.build(
        code=code,
        category=category,
        safe_message="Dispatch eligibility requirements were not satisfied.",
    )
    builder = (
        DispatchEligibilityResult.build_integrity_failure
        if status is DispatchEligibilityStatus.INTEGRITY_FAILURE
        else DispatchEligibilityResult.build
    )
    return builder(
        plan_result=plan_result,
        policy=policy,
        execution_context=context,
        status=status,
        required_capability=plan.required_capability if plan else None,
        diagnostic=diagnostic,
    )


def _policy_failure(policy):
    if (
        not isinstance(policy, CorrectiveActionExecutionDispatchPolicy)
        or policy.policy_version != POLICY_VERSION
    ):
        return (
            DispatchEligibilityStatus.INVALID_POLICY,
            CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_POLICY,
            CorrectiveActionExecutionDispatchDiagnosticCategory.POLICY,
        )
    try:
        validate_execution_dispatch_policy(policy)
    except (TypeError, ValueError):
        return (
            DispatchEligibilityStatus.INTEGRITY_FAILURE,
            CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_POLICY,
            CorrectiveActionExecutionDispatchDiagnosticCategory.POLICY,
        )
    return None


def _context_failure(context):
    if (
        not isinstance(context, CorrectiveActionExecutionContext)
        or context.context_version != CONTEXT_VERSION
    ):
        return (
            DispatchEligibilityStatus.INVALID_CONTEXT,
            CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_REQUEST,
            CorrectiveActionExecutionDispatchDiagnosticCategory.VALIDATION,
        )
    try:
        validate_execution_context(context)
    except (TypeError, ValueError):
        return (
            DispatchEligibilityStatus.INTEGRITY_FAILURE,
            CorrectiveActionExecutionDispatchDiagnosticCode.INVALID_DISPATCH_REQUEST,
            CorrectiveActionExecutionDispatchDiagnosticCategory.VALIDATION,
        )
    return None


def _eligibility_identity(values):
    plan_result = values["plan_result"]
    policy = values["policy"]
    context = values["execution_context"]
    plan = _field(plan_result, "plan")
    return {
        "eligibility_version": values["eligibility_version"],
        "plan_result_fingerprint": _field(plan_result, "result_fingerprint"),
        "plan_fingerprint": _field(plan, "plan_fingerprint") if plan else None,
        "policy_fingerprint": _field(policy, "policy_fingerprint"),
        "context_fingerprint": _field(context, "context_fingerprint"),
        "eligibility_status": values["status"],
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
