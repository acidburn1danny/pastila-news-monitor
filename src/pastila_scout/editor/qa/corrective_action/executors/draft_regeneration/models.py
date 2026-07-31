"""Immutable capability-specific draft-regeneration contracts."""

import re
from typing import Any

from pydantic import field_validator, model_validator

from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    FrozenModel,
    GenerationPolicy,
)
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRequest,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.integration.models import (
    INTEGRATION_VERSION,
    ControlledGenerationInvocation,
)
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    DraftRegenerationDiagnosticCategory,
    DraftRegenerationDiagnosticCode,
    DraftRegenerationOutcome,
    DraftRegenerationPreconditionCode,
    DraftRegenerationStatus,
)
from .policy import DraftRegenerationPolicy

INPUT_VERSION = "1"
REQUEST_VERSION = "1"
PRECONDITION_VERSION = "1"
DIAGNOSTIC_VERSION = "1"
OUTPUT_REFERENCE_VERSION = "1"
RESULT_VERSION = "1"
REPORT_VERSION = "1"

_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")


class DraftRegenerationPrecondition(FrozenModel):
    """One typed validation observation; it never changes plan preconditions."""

    precondition_version: str = PRECONDITION_VERSION
    code: DraftRegenerationPreconditionCode
    satisfied: bool
    source_fingerprint: str
    precondition_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationPrecondition:
        values.setdefault("precondition_version", PRECONDITION_VERSION)
        values["precondition_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("source_fingerprint")
    @classmethod
    def source_fingerprint_is_valid(cls, value: str) -> str:
        if not _FINGERPRINT.fullmatch(value):
            raise ValueError("precondition source fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.precondition_version != PRECONDITION_VERSION:
            raise ValueError("unsupported regeneration precondition version")
        return _validate_fingerprint(self, "precondition_fingerprint")


class DraftRegenerationInput(FrozenModel):
    """Typed reuse of the existing Controlled Generation invocation boundary."""

    input_version: str = INPUT_VERSION
    controlled_generation_contract_version: str = INTEGRATION_VERSION
    generation_invocation: ControlledGenerationInvocation
    generation_policy: GenerationPolicy
    source_draft: EpisodeDraft | None = None
    constraint_fingerprints: tuple[str, ...] = ()
    input_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationInput:
        values.setdefault("input_version", INPUT_VERSION)
        values.setdefault("controlled_generation_contract_version", INTEGRATION_VERSION)
        values.setdefault("source_draft", None)
        values["constraint_fingerprints"] = tuple(
            sorted(values.get("constraint_fingerprints", ()))
        )
        values["input_fingerprint"] = fingerprint(_input_identity(values))
        return cls.model_validate(values)

    @field_validator("constraint_fingerprints")
    @classmethod
    def constraints_are_canonical(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(value)) != value or len(set(value)) != len(value):
            raise ValueError("constraint fingerprints must be unique and canonical")
        if any(not _FINGERPRINT.fullmatch(item) for item in value):
            raise ValueError("constraint fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.input_version != INPUT_VERSION:
            raise ValueError("unsupported draft-regeneration input version")
        if self.controlled_generation_contract_version != INTEGRATION_VERSION:
            raise ValueError("unsupported Controlled Generation contract version")
        expected = fingerprint(_input_identity(self.model_dump(mode="python")))
        if self.input_fingerprint != expected:
            raise ValueError("draft-regeneration input fingerprint is inconsistent")
        return self


class DraftRegenerationRequest(FrozenModel):
    """Preserve one exact frozen executor request plus regeneration-only inputs."""

    request_version: str = REQUEST_VERSION
    executor_request: CorrectiveActionExecutorRequest
    policy: DraftRegenerationPolicy
    regeneration_input: DraftRegenerationInput
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationRequest:
        values.setdefault("request_version", REQUEST_VERSION)
        values["request_fingerprint"] = fingerprint(_request_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.request_version != REQUEST_VERSION:
            raise ValueError("unsupported draft-regeneration request version")
        plan = self.executor_request.plan
        if plan.plan_type is not CorrectiveActionExecutionPlanType.REGENERATE_DRAFT:
            raise ValueError("draft regeneration requires REGENERATE_DRAFT")
        if (
            plan.required_capability
            is not CorrectiveActionExecutionCapability.DRAFT_REGENERATION
        ):
            raise ValueError("draft regeneration requires DRAFT_REGENERATION")
        if plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE:
            raise ValueError("draft regeneration cannot be non-executable")
        from .descriptor import build_draft_regeneration_executor_descriptor

        if (
            self.executor_request.executor_descriptor
            != build_draft_regeneration_executor_descriptor()
        ):
            raise ValueError("executor request does not use regeneration descriptor")
        expected = fingerprint(_request_identity(self.model_dump(mode="python")))
        if self.request_fingerprint != expected:
            raise ValueError("draft-regeneration request fingerprint is inconsistent")
        return self


class DraftRegenerationDiagnostic(FrozenModel):
    """Stable content-free capability diagnostic."""

    diagnostic_version: str = DIAGNOSTIC_VERSION
    code: DraftRegenerationDiagnosticCode
    category: DraftRegenerationDiagnosticCategory
    safe_message: str
    fingerprint_references: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationDiagnostic:
        values.setdefault("diagnostic_version", DIAGNOSTIC_VERSION)
        values["fingerprint_references"] = tuple(
            sorted(values.get("fingerprint_references", ()))
        )
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_message")
    @classmethod
    def message_is_safe(cls, value: str) -> str:
        forbidden = ("\\", "/", "secret", "token", "prompt", "traceback", "@")
        if not value.strip() or len(value) > 200:
            raise ValueError("regeneration diagnostic message must be concise")
        if any(item in value.casefold() for item in forbidden):
            raise ValueError("regeneration diagnostic contains unsafe content")
        return value

    @field_validator("fingerprint_references")
    @classmethod
    def references_are_safe(
        cls, value: tuple[tuple[str, str], ...]
    ) -> tuple[tuple[str, str], ...]:
        allowed = {
            "executor_request",
            "planning_result",
            "plan",
            "regeneration_policy",
            "regeneration_input",
            "regeneration_request",
            "generation_result",
            "regenerated_draft",
            "output_reference",
        }
        keys = tuple(key for key, _ in value)
        if len(set(keys)) != len(keys) or not set(keys) <= allowed:
            raise ValueError("regeneration diagnostic references are invalid")
        if any(not _FINGERPRINT.fullmatch(item) for _, item in value):
            raise ValueError("regeneration diagnostic fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.diagnostic_version != DIAGNOSTIC_VERSION:
            raise ValueError("unsupported regeneration diagnostic version")
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class DraftRegenerationOutputReference(FrozenModel):
    """Content-free reference to a validated future generation output."""

    output_reference_version: str = OUTPUT_REFERENCE_VERSION
    output_type: str = "episode_draft"
    regeneration_request_fingerprint: str
    regenerated_draft_fingerprint: str
    generation_result_fingerprint: str
    output_reference_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationOutputReference:
        values.setdefault("output_reference_version", OUTPUT_REFERENCE_VERSION)
        values.setdefault("output_type", "episode_draft")
        values["output_reference_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator(
        "regeneration_request_fingerprint",
        "regenerated_draft_fingerprint",
        "generation_result_fingerprint",
    )
    @classmethod
    def lineage_fingerprint_is_valid(cls, value: str) -> str:
        if not _FINGERPRINT.fullmatch(value):
            raise ValueError("output-reference lineage fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.output_reference_version != OUTPUT_REFERENCE_VERSION:
            raise ValueError("unsupported regeneration output-reference version")
        if self.output_type != "episode_draft":
            raise ValueError("unsupported regeneration output type")
        return _validate_fingerprint(self, "output_reference_fingerprint")


class DraftRegenerationResult(FrozenModel):
    """Immutable capability result; no runtime constructs it in Part 1."""

    result_version: str = RESULT_VERSION
    request: DraftRegenerationRequest
    operational_outcome: DraftRegenerationOutcome
    status: DraftRegenerationStatus
    generation_result: ControlledGenerationResult | None
    regenerated_draft: EpisodeDraft | None
    output_reference: DraftRegenerationOutputReference | None
    diagnostic: DraftRegenerationDiagnostic | None
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationResult:
        values.setdefault("result_version", RESULT_VERSION)
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.result_version != RESULT_VERSION:
            raise ValueError("unsupported draft-regeneration result version")
        completed = self.operational_outcome is DraftRegenerationOutcome.COMPLETED
        output_present = all(
            item is not None
            for item in (
                self.generation_result,
                self.regenerated_draft,
                self.output_reference,
            )
        )
        if completed != (self.status is DraftRegenerationStatus.COMPLETED):
            raise ValueError("regeneration outcome and status are inconsistent")
        if completed != output_present or completed == (self.diagnostic is not None):
            raise ValueError("regeneration result shape is inconsistent")
        if completed:
            if self.generation_result.draft is not self.regenerated_draft:
                raise ValueError("regeneration result does not preserve draft identity")
            source = self.request.regeneration_input.source_draft
            if source is not None and self.regenerated_draft is source:
                raise ValueError("regenerated draft reuses source-draft identity")
            _validate_output_lineage(self)
        expected = fingerprint(_result_identity(self.model_dump(mode="python")))
        if self.result_fingerprint != expected:
            raise ValueError("draft-regeneration result fingerprint is inconsistent")
        return self


class DraftRegenerationReport(FrozenModel):
    """Safe projection without draft, prompt, or provider content."""

    report_version: str = REPORT_VERSION
    outcome: DraftRegenerationOutcome
    status: DraftRegenerationStatus
    plan_type: str
    execution_mode: str
    required_capability: str
    executor_id: str
    policy_version: str
    controlled_generation_contract_version: str
    executor_request_fingerprint: str
    planning_result_fingerprint: str
    plan_fingerprint: str
    source_draft_fingerprint: str | None
    regenerated_draft_fingerprint: str | None
    generation_result_fingerprint: str | None
    output_reference_fingerprint: str | None
    diagnostic_code: DraftRegenerationDiagnosticCode | None
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationReport:
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.report_version != REPORT_VERSION:
            raise ValueError("unsupported draft-regeneration report version")
        return _validate_fingerprint(self, "report_fingerprint")


def map_regeneration_outcome(
    outcome: DraftRegenerationOutcome,
) -> tuple[CorrectiveActionExecutorOutcome, CorrectiveActionExecutionStatus]:
    """Define the complete future mapping without constructing executor results."""

    mapping = {
        DraftRegenerationOutcome.COMPLETED: (
            CorrectiveActionExecutorOutcome.COMPLETED,
            CorrectiveActionExecutionStatus.COMPLETED,
        ),
        DraftRegenerationOutcome.FAILED_INVALID_EXECUTOR_REQUEST: (
            CorrectiveActionExecutorOutcome.FAILED_INVALID_REQUEST,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_UNSUPPORTED_CONTRACT: (
            CorrectiveActionExecutorOutcome.FAILED_INVALID_REQUEST,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_PLAN_MISMATCH: (
            CorrectiveActionExecutorOutcome.FAILED_UNSUPPORTED_PLAN,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_CAPABILITY_MISMATCH: (
            CorrectiveActionExecutorOutcome.FAILED_UNSUPPORTED_PLAN,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_EXECUTION_MODE: (
            CorrectiveActionExecutorOutcome.FAILED_INVALID_REQUEST,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_AUTHORIZATION: (
            CorrectiveActionExecutorOutcome.FAILED_AUTHORIZATION,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_PRECONDITION: (
            CorrectiveActionExecutorOutcome.FAILED_PRECONDITION,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_INPUT_VALIDATION: (
            CorrectiveActionExecutorOutcome.FAILED_INVALID_REQUEST,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_GENERATION_CONTRACT: (
            CorrectiveActionExecutorOutcome.FAILED_PRECONDITION,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_OUTPUT_VALIDATION: (
            CorrectiveActionExecutorOutcome.FAILED_INTERNAL,
            CorrectiveActionExecutionStatus.FAILED,
        ),
        DraftRegenerationOutcome.FAILED_INTERNAL: (
            CorrectiveActionExecutorOutcome.FAILED_INTERNAL,
            CorrectiveActionExecutionStatus.FAILED,
        ),
    }
    if not isinstance(outcome, DraftRegenerationOutcome):
        raise TypeError("invalid draft-regeneration outcome")
    return mapping[outcome]


def _input_identity(values):
    invocation = values["generation_invocation"]
    generation_policy = values["generation_policy"]
    source_draft = values.get("source_draft")
    return {
        "input_version": values["input_version"],
        "controlled_generation_contract_version": values[
            "controlled_generation_contract_version"
        ],
        "generation_invocation_fingerprint": _invocation_fingerprint(invocation),
        "generation_policy_fingerprint": fingerprint(generation_policy),
        "source_draft_fingerprint": fingerprint(source_draft) if source_draft else None,
        "constraint_fingerprints": values.get("constraint_fingerprints", ()),
    }


def _request_identity(values):
    return {
        "request_version": values["request_version"],
        "executor_request_fingerprint": _field(
            values["executor_request"], "request_fingerprint"
        ),
        "regeneration_policy_fingerprint": _field(
            values["policy"], "policy_fingerprint"
        ),
        "regeneration_input_fingerprint": _field(
            values["regeneration_input"], "input_fingerprint"
        ),
    }


def _result_identity(values):
    generation_result = values.get("generation_result")
    regenerated_draft = values.get("regenerated_draft")
    output_reference = values.get("output_reference")
    diagnostic = values.get("diagnostic")
    return {
        "result_version": values["result_version"],
        "request_fingerprint": _field(values["request"], "request_fingerprint"),
        "operational_outcome": values["operational_outcome"],
        "status": values["status"],
        "generation_result_fingerprint": (
            fingerprint(generation_result) if generation_result else None
        ),
        "regenerated_draft_fingerprint": (
            fingerprint(regenerated_draft) if regenerated_draft else None
        ),
        "output_reference_fingerprint": (
            _field(output_reference, "output_reference_fingerprint")
            if output_reference
            else None
        ),
        "diagnostic_code": _field(diagnostic, "code") if diagnostic else None,
    }


def _validate_output_lineage(result: DraftRegenerationResult) -> None:
    reference = result.output_reference
    if reference.regeneration_request_fingerprint != result.request.request_fingerprint:
        raise ValueError("output reference request lineage is inconsistent")
    if reference.regenerated_draft_fingerprint != fingerprint(result.regenerated_draft):
        raise ValueError("output reference draft lineage is inconsistent")
    if reference.generation_result_fingerprint != fingerprint(result.generation_result):
        raise ValueError("output reference generation lineage is inconsistent")


def _invocation_fingerprint(value):
    if isinstance(value, dict):
        return ControlledGenerationInvocation.model_validate(
            value
        ).invocation_fingerprint
    return value.invocation_fingerprint


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
