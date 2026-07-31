"""Immutable M6C.6D Part 3A executor-owned result contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.generation.revision import (
    ControlledRevisionInvocation,
    ControlledRevisionResult,
    RevisionResultStatus,
)
from pastila_scout.editor.qa.models import fingerprint

from ..preparation_models import (
    DraftRevisionPreparationOutcome,
    DraftRevisionPreparationResult,
)

EXECUTION_VERSION = "1"
LIFECYCLE_VERSION = "1"
REPORT_VERSION = "1"


class DraftRevisionExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class DraftRevisionExecutionOutcome(StrEnum):
    COMPLETED = "completed"
    INVALID_PREPARATION = "invalid_preparation"
    PREPARATION_NOT_EXECUTABLE = "preparation_not_executable"
    INVALID_INVOCATION = "invalid_invocation"
    CONTROLLED_REVISION_FAILED = "controlled_revision_failed"
    INVALID_CONTROLLED_REVISION_RESULT = "invalid_controlled_revision_result"
    LINEAGE_MISMATCH = "lineage_mismatch"
    INTERNAL_FAILURE = "internal_failure"


class DraftRevisionExecutionDiagnosticCode(StrEnum):
    INVALID_DRAFT_REVISION_PREPARATION = "invalid_draft_revision_preparation"
    DRAFT_REVISION_PREPARATION_NOT_EXECUTABLE = (
        "draft_revision_preparation_not_executable"
    )
    CONTROLLED_REVISION_INVOCATION_INVALID = "controlled_revision_invocation_invalid"
    CONTROLLED_REVISION_EXECUTION_FAILED = "controlled_revision_execution_failed"
    INVALID_CONTROLLED_REVISION_RESULT = "invalid_controlled_revision_result"
    DRAFT_REVISION_EXECUTION_LINEAGE_MISMATCH = (
        "draft_revision_execution_lineage_mismatch"
    )
    DRAFT_REVISION_OUTPUT_INVALID = "draft_revision_output_invalid"
    DRAFT_REVISION_EXECUTION_LIFECYCLE_INVALID = (
        "draft_revision_execution_lifecycle_invalid"
    )
    INTERNAL_DRAFT_REVISION_EXECUTION_FAILURE = (
        "internal_draft_revision_execution_failure"
    )


class DraftRevisionExecutionPhase(StrEnum):
    CREATED = "created"
    PREPARATION_VALIDATED = "preparation_validated"
    INVOCATION_CREATED = "invocation_created"
    CONTROLLED_REVISION_INVOKED = "controlled_revision_invoked"
    CONTROLLED_REVISION_COMPLETED = "controlled_revision_completed"
    RESULT_VALIDATED = "result_validated"
    COMPLETED = "completed"
    FAILED = "failed"


class DraftRevisionExecutionDiagnostic(FrozenModel):
    code: DraftRevisionExecutionDiagnosticCode
    safe_message: str = Field(min_length=1, max_length=200)
    controlled_revision_diagnostic_code: str | None = None
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("controlled_revision_diagnostic_code", None)
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        lowered = self.safe_message.casefold()
        if any(
            token in lowered
            for token in ("traceback", "api_key", "bearer ", "c:\\", "/home/")
        ):
            raise ValueError("draft-revision execution diagnostic is unsafe")
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class DraftRevisionExecutionLifecycle(FrozenModel):
    lifecycle_version: str = LIFECYCLE_VERSION
    phases: tuple[DraftRevisionExecutionPhase, ...] = Field(min_length=2)
    lifecycle_fingerprint: str

    @classmethod
    def build(cls, phases):
        values = {"lifecycle_version": LIFECYCLE_VERSION, "phases": tuple(phases)}
        values["lifecycle_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.lifecycle_version != LIFECYCLE_VERSION or not _valid_lifecycle(
            self.phases
        ):
            raise ValueError("draft-revision execution lifecycle is invalid")
        return _validate_fingerprint(self, "lifecycle_fingerprint")


class DraftRevisionExecutionResult(FrozenModel):
    contract_version: str = EXECUTION_VERSION
    status: DraftRevisionExecutionStatus
    outcome: DraftRevisionExecutionOutcome
    preparation_result: DraftRevisionPreparationResult | None = Field(
        default=None, repr=False
    )
    controlled_revision_invocation: ControlledRevisionInvocation | None = None
    controlled_revision_result: ControlledRevisionResult | None = Field(
        default=None, repr=False
    )
    revised_draft: EpisodeDraft | None = Field(default=None, repr=False)
    diagnostic: DraftRevisionExecutionDiagnostic | None = None
    lifecycle: DraftRevisionExecutionLifecycle
    input_preparation_fingerprint: str
    execution_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", EXECUTION_VERSION)
        for name in (
            "preparation_result",
            "controlled_revision_invocation",
            "controlled_revision_result",
            "revised_draft",
            "diagnostic",
        ):
            values.setdefault(name, None)
        values["execution_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != EXECUTION_VERSION:
            raise ValueError("unsupported draft-revision execution version")
        success = self.outcome is DraftRevisionExecutionOutcome.COMPLETED
        if success != (self.status is DraftRevisionExecutionStatus.SUCCESS):
            raise ValueError("draft-revision execution status and outcome differ")
        if success:
            if (
                self.preparation_result is None
                or self.controlled_revision_invocation is None
                or self.controlled_revision_result is None
                or self.revised_draft is None
                or self.diagnostic is not None
            ):
                raise ValueError("successful draft-revision execution is incomplete")
            if (
                self.preparation_result.outcome
                is not DraftRevisionPreparationOutcome.PREPARED
                or self.controlled_revision_result.status
                is not RevisionResultStatus.SUCCESS
                or self.controlled_revision_invocation.request
                is not self.preparation_result.generation_request
                or self.revised_draft
                is not self.controlled_revision_result.revised_draft
                or self.lifecycle.phases[-1]
                is not DraftRevisionExecutionPhase.COMPLETED
            ):
                raise ValueError(
                    "successful draft-revision execution lineage is invalid"
                )
        else:
            if self.revised_draft is not None or self.diagnostic is None:
                raise ValueError("failed draft-revision execution shape is invalid")
            if self.lifecycle.phases[-1] is not DraftRevisionExecutionPhase.FAILED:
                raise ValueError("failed draft-revision lifecycle is not terminal")
            if self.preparation_result is None and (
                self.controlled_revision_invocation is not None
                or self.controlled_revision_result is not None
            ):
                raise ValueError("failed execution has orphan runtime artifacts")
            if (
                self.controlled_revision_result is not None
                and self.controlled_revision_invocation is None
            ):
                raise ValueError("controlled revision result lacks invocation")
        if self.input_preparation_fingerprint != (
            self.preparation_result.preparation_fingerprint
            if self.preparation_result
            else self.input_preparation_fingerprint
        ):
            raise ValueError("execution preparation lineage is inconsistent")
        if self.execution_fingerprint != fingerprint(
            _result_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("draft-revision execution fingerprint is inconsistent")
        return self


class DraftRevisionExecutionReport(FrozenModel):
    report_version: str = REPORT_VERSION
    capability: str
    action: str
    status: DraftRevisionExecutionStatus
    outcome: DraftRevisionExecutionOutcome
    target_count: int
    diagnostic_code: DraftRevisionExecutionDiagnosticCode | None
    controlled_revision_diagnostic_code: str | None
    lifecycle: tuple[str, ...]
    executor_request_fingerprint: str | None
    planning_input_fingerprint: str | None
    preparation_fingerprint: str
    revision_request_fingerprint: str | None
    invocation_fingerprint: str | None
    controlled_revision_result_fingerprint: str | None
    source_draft_fingerprint: str | None
    preservation_fingerprint: str | None
    output_contract_fingerprint: str | None
    execution_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)


def _result_identity(values):
    mappings = {
        "preparation_result": "preparation_fingerprint",
        "controlled_revision_invocation": "invocation_fingerprint",
        "controlled_revision_result": "result_fingerprint",
        "diagnostic": "diagnostic_fingerprint",
        "lifecycle": "lifecycle_fingerprint",
    }
    result = {
        "contract_version": values["contract_version"],
        "status": values["status"],
        "outcome": values["outcome"],
        "revised_draft_fingerprint": (
            fingerprint(values["revised_draft"])
            if values.get("revised_draft") is not None
            else None
        ),
        "input_preparation_fingerprint": values["input_preparation_fingerprint"],
    }
    result.update(
        {
            f"{name}_fingerprint": (
                _field(values[name], field_name) if values.get(name) else None
            )
            for name, field_name in mappings.items()
        }
    )
    return result


def _valid_lifecycle(phases):
    normal = tuple(DraftRevisionExecutionPhase)[:7]
    if phases[-1] is DraftRevisionExecutionPhase.COMPLETED:
        return phases == normal
    if phases[-1] is not DraftRevisionExecutionPhase.FAILED:
        return False
    prefix = phases[:-1]
    return bool(prefix) and prefix == normal[: len(prefix)]


def _validate_fingerprint(model, name):
    expected = fingerprint(model.model_dump(exclude={name}, mode="python"))
    if getattr(model, name) != expected:
        raise ValueError(f"{name} is inconsistent")
    return model


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
