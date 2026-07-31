"""Deterministic exact capability and executor-descriptor resolution."""

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanResult,
    validate_execution_plan_result,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import CorrectiveActionExecutorDescriptor
from .registry import (
    CorrectiveActionExecutorRegistry,
    validate_executor_registry,
)

RESOLUTION_VERSION = "1"
RESOLUTION_REPORT_VERSION = "1"


class CapabilityResolutionStatus(StrEnum):
    """Exact resolution cardinality and fail-closed classifications."""

    ZERO_MATCH = "zero_match"
    EXACT_MATCH = "exact_match"
    AMBIGUOUS_MATCH = "ambiguous_match"
    CAPABILITY_NONE = "capability_none"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    UNSUPPORTED_PLAN = "unsupported_plan"
    INVALID_REGISTRY = "invalid_registry"
    INTEGRITY_FAILURE = "integrity_failure"


class CapabilityResolutionDiagnosticCode(StrEnum):
    """Stable safe capability-resolution diagnostics."""

    CAPABILITY_NONE = "capability_none"
    EXECUTOR_NOT_FOUND = "executor_not_found"
    AMBIGUOUS_EXECUTOR_MATCH = "ambiguous_executor_match"
    PLAN_NOT_SUPPORTED = "plan_not_supported"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    INVALID_DESCRIPTOR = "invalid_descriptor"
    INVALID_REGISTRY = "invalid_registry"
    INVALID_PLANNING_RESULT = "invalid_planning_result"


class CapabilityResolutionResult(FrozenModel):
    """Immutable resolution result preserving registry and planning identity."""

    resolution_version: str = RESOLUTION_VERSION
    plan_result: CorrectiveActionExecutionPlanResult
    registry: CorrectiveActionExecutorRegistry
    status: CapabilityResolutionStatus
    required_capability: CorrectiveActionExecutionCapability | None
    matching_descriptor_count: int
    descriptor: CorrectiveActionExecutorDescriptor | None
    diagnostic_code: CapabilityResolutionDiagnosticCode | None
    resolution_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CapabilityResolutionResult:
        values.setdefault("resolution_version", RESOLUTION_VERSION)
        values["resolution_fingerprint"] = fingerprint(_resolution_identity(values))
        return cls.model_validate(values)

    @classmethod
    def build_integrity_failure(cls, **values: Any) -> CapabilityResolutionResult:
        """Preserve corrupt typed input solely for a fail-closed classification."""

        values.setdefault("resolution_version", RESOLUTION_VERSION)
        values["resolution_fingerprint"] = fingerprint(_resolution_identity(values))
        result = cls.model_construct(**values)
        result.invariants()
        return result

    @model_validator(mode="after")
    def invariants(self):
        if self.resolution_version != RESOLUTION_VERSION:
            raise ValueError("unsupported capability resolution version")
        exact = self.status is CapabilityResolutionStatus.EXACT_MATCH
        if exact != (self.descriptor is not None):
            raise ValueError("exact resolution requires exactly one descriptor")
        if exact != (self.diagnostic_code is None):
            raise ValueError("resolution diagnostic presence is inconsistent")
        if exact != (self.matching_descriptor_count == 1):
            raise ValueError("exact resolution count is inconsistent")
        if (
            self.status is CapabilityResolutionStatus.ZERO_MATCH
            and self.matching_descriptor_count != 0
        ):
            raise ValueError("zero-match resolution count is inconsistent")
        if (
            self.status is CapabilityResolutionStatus.AMBIGUOUS_MATCH
            and self.matching_descriptor_count < 2
        ):
            raise ValueError("ambiguous resolution requires multiple matches")
        plan = self.plan_result.plan
        if self.required_capability != (plan.required_capability if plan else None):
            raise ValueError("resolution capability contradicts planning result")
        if (
            self.descriptor is not None
            and self.descriptor not in self.registry.descriptors
        ):
            raise ValueError("resolved descriptor is absent from registry")
        expected = fingerprint(_resolution_identity(self.model_dump(mode="python")))
        if self.resolution_fingerprint != expected:
            raise ValueError("capability resolution fingerprint is inconsistent")
        return self


class CapabilityResolutionReport(FrozenModel):
    """Safe non-authoritative capability-resolution projection."""

    report_version: str = RESOLUTION_REPORT_VERSION
    status: CapabilityResolutionStatus
    required_capability: CorrectiveActionExecutionCapability | None
    matching_descriptor_count: int
    executor_id: str | None
    diagnostic_code: CapabilityResolutionDiagnosticCode | None
    registry_fingerprint: str
    plan_result_fingerprint: str
    plan_fingerprint: str | None
    descriptor_fingerprint: str | None
    resolution_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CapabilityResolutionReport:
        values.setdefault("report_version", RESOLUTION_REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.report_version != RESOLUTION_REPORT_VERSION:
            raise ValueError("unsupported resolution report version")
        return _validate_fingerprint(self, "report_fingerprint")


class CapabilityResolver:
    """Resolve one plan against one immutable registry without invocation."""

    def resolve(
        self,
        plan_result: CorrectiveActionExecutionPlanResult,
        registry: CorrectiveActionExecutorRegistry,
    ) -> CapabilityResolutionResult:
        """Return deterministic zero, exact, ambiguous, or invalid resolution."""

        try:
            validate_executor_registry(registry)
        except (TypeError, ValueError):
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.INVALID_REGISTRY,
                0,
                None,
                CapabilityResolutionDiagnosticCode.INVALID_REGISTRY,
            )
        try:
            validate_execution_plan_result(plan_result)
        except (TypeError, ValueError):
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.INTEGRITY_FAILURE,
                0,
                None,
                CapabilityResolutionDiagnosticCode.INVALID_PLANNING_RESULT,
            )
        if (
            plan_result.operational_outcome
            is not CorrectiveActionExecutionPlanOutcome.COMPLETED
            or plan_result.plan is None
        ):
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.INTEGRITY_FAILURE,
                0,
                None,
                CapabilityResolutionDiagnosticCode.INVALID_PLANNING_RESULT,
            )
        plan = plan_result.plan
        capability = plan.required_capability
        if capability is CorrectiveActionExecutionCapability.NONE:
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.CAPABILITY_NONE,
                0,
                None,
                CapabilityResolutionDiagnosticCode.CAPABILITY_NONE,
            )
        matches = registry.lookup(capability, plan.plan_type)
        if len(matches) == 1:
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.EXACT_MATCH,
                1,
                matches[0],
                None,
            )
        if len(matches) > 1:
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.AMBIGUOUS_MATCH,
                len(matches),
                None,
                CapabilityResolutionDiagnosticCode.AMBIGUOUS_EXECUTOR_MATCH,
            )
        capability_matches = tuple(
            item
            for item in registry.descriptors
            if item.supported_capability is capability
        )
        if capability_matches:
            return _result(
                plan_result,
                registry,
                CapabilityResolutionStatus.UNSUPPORTED_PLAN,
                0,
                None,
                CapabilityResolutionDiagnosticCode.PLAN_NOT_SUPPORTED,
            )
        return _result(
            plan_result,
            registry,
            CapabilityResolutionStatus.ZERO_MATCH,
            0,
            None,
            CapabilityResolutionDiagnosticCode.EXECUTOR_NOT_FOUND,
        )


def build_capability_resolution_report(
    result: CapabilityResolutionResult,
) -> CapabilityResolutionReport:
    """Build a safe deterministic resolution projection."""

    plan = result.plan_result.plan
    return CapabilityResolutionReport.build(
        status=result.status,
        required_capability=result.required_capability,
        matching_descriptor_count=result.matching_descriptor_count,
        executor_id=result.descriptor.executor_id if result.descriptor else None,
        diagnostic_code=result.diagnostic_code,
        registry_fingerprint=result.registry.registry_fingerprint,
        plan_result_fingerprint=result.plan_result.result_fingerprint,
        plan_fingerprint=plan.plan_fingerprint if plan else None,
        descriptor_fingerprint=(
            result.descriptor.descriptor_fingerprint if result.descriptor else None
        ),
        resolution_fingerprint=result.resolution_fingerprint,
    )


def validate_capability_resolution_result(
    result: CapabilityResolutionResult,
) -> None:
    """Validate resolution result shape, identity, and fingerprint."""

    if not isinstance(result, CapabilityResolutionResult):
        raise TypeError("invalid capability resolution result")
    result.invariants()


def _result(plan_result, registry, status, count, descriptor, diagnostic):
    plan = (
        plan_result.plan
        if isinstance(plan_result, CorrectiveActionExecutionPlanResult)
        else None
    )
    builder = (
        CapabilityResolutionResult.build_integrity_failure
        if status
        in {
            CapabilityResolutionStatus.INVALID_REGISTRY,
            CapabilityResolutionStatus.INTEGRITY_FAILURE,
        }
        else CapabilityResolutionResult.build
    )
    return builder(
        plan_result=plan_result,
        registry=registry,
        status=status,
        required_capability=plan.required_capability if plan else None,
        matching_descriptor_count=count,
        descriptor=descriptor,
        diagnostic_code=diagnostic,
    )


def _resolution_identity(values):
    plan_result = values["plan_result"]
    registry = values["registry"]
    plan = _field(plan_result, "plan")
    descriptor = values.get("descriptor")
    return {
        "resolution_version": values["resolution_version"],
        "registry_fingerprint": _field(registry, "registry_fingerprint"),
        "plan_fingerprint": _field(plan, "plan_fingerprint") if plan else None,
        "descriptor_fingerprint": (
            _field(descriptor, "descriptor_fingerprint") if descriptor else None
        ),
        "resolution_status": values["status"],
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
