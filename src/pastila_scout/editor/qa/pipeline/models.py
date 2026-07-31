"""Immutable operational contracts for the M6C.5C reviewer pipeline."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.qa.manifest import EditorialReviewManifest
from pastila_scout.editor.qa.models import (
    EditorialReviewResult,
    ReviewerCapability,
    ReviewScope,
    fingerprint,
)

PIPELINE_ID = "editorial-reviewer-pipeline"
PIPELINE_VERSION = "1.0.0"


class PipelineDiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class PipelineDiagnosticPhase(StrEnum):
    REGISTRY = "registry"
    PLAN = "plan"
    SELECTION = "selection"
    SCHEDULING = "scheduling"
    EXECUTION = "execution"
    STATE = "state"
    FINALIZATION = "finalization"


class ReviewerExecutionStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ReviewerPipelineStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_SKIPS = "completed_with_skips"
    PARTIAL = "partial"
    FAILED = "failed"


class ReviewerPipelineLifecycleStatus(StrEnum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    HALTED = "halted"
    FINALIZED = "finalized"


class PipelineTraceEventType(StrEnum):
    PIPELINE_INITIALIZED = "pipeline_initialized"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_SKIPPED = "execution_skipped"
    DEPENDENCY_PROPAGATION_APPLIED = "dependency_propagation_applied"
    PIPELINE_HALTED = "pipeline_halted"
    PIPELINE_FINALIZED = "pipeline_finalized"


class ReviewerPipelinePolicy(FrozenModel):
    continue_after_required_failure: bool = True
    continue_after_optional_failure: bool = True
    allow_optional_reviewer_skip: bool = True
    allow_partial_selection: bool = True
    maximum_execution_units: int = Field(default=100, gt=0, le=1000)
    maximum_pipeline_failures: int = Field(default=20, gt=0, le=100)
    maximum_diagnostics: int = Field(default=200, gt=0, le=2000)

    @property
    def policy_fingerprint(self) -> str:
        return fingerprint(self)


class ReviewerPipelineRequest(FrozenModel):
    episode_draft: EpisodeDraft
    review_manifest: EditorialReviewManifest
    pipeline_policy: ReviewerPipelinePolicy = ReviewerPipelinePolicy()
    requested_execution_ids: tuple[str, ...] = ()

    @field_validator("requested_execution_ids")
    @classmethod
    def canonical_requested(cls, value):
        if any(not item for item in value) or len(value) != len(set(value)):
            raise ValueError("requested execution IDs must be nonempty and unique")
        return tuple(sorted(value))

    @property
    def request_fingerprint(self) -> str:
        return fingerprint(
            {
                "draft": fingerprint(self.episode_draft),
                "manifest": self.review_manifest.manifest_fingerprint,
                "policy": self.pipeline_policy.policy_fingerprint,
                "requested": self.requested_execution_ids,
            }
        )


class RegisteredReviewerDescriptor(FrozenModel):
    reviewer_id: str = Field(min_length=1)
    reviewer_version: str = Field(min_length=1)
    capabilities: tuple[ReviewerCapability, ...] = Field(min_length=1)
    supported_scopes: tuple[ReviewScope, ...] = Field(min_length=1)
    implementation_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")

    @field_validator("capabilities", "supported_scopes")
    @classmethod
    def canonical_unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("descriptor values must be unique")
        return tuple(sorted(value, key=lambda item: item.value))


class ReviewerExecutionUnit(FrozenModel):
    execution_id: str
    manifest_item_id: str
    manifest_order: int = Field(ge=0)
    reviewer_id: str
    reviewer_version: str
    required: bool
    scope: ReviewScope
    target_component_ids: tuple[str, ...]
    required_capabilities: tuple[ReviewerCapability, ...]
    depends_on_execution_ids: tuple[str, ...]


class ReviewerExecutionPlan(FrozenModel):
    pipeline_id: str = PIPELINE_ID
    pipeline_version: str = PIPELINE_VERSION
    draft_fingerprint: str
    manifest_fingerprint: str
    registry_fingerprint: str
    policy_fingerprint: str
    execution_units: tuple[ReviewerExecutionUnit, ...]
    plan_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("pipeline_id", PIPELINE_ID)
        values.setdefault("pipeline_version", PIPELINE_VERSION)
        values["plan_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "plan_fingerprint")


class ReviewerExecutionSelection(FrozenModel):
    plan_fingerprint: str
    requested_execution_ids: tuple[str, ...]
    selected_execution_ids: tuple[str, ...]
    dependency_execution_ids: tuple[str, ...]
    excluded_execution_ids: tuple[str, ...]
    selection_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["selection_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def partition_valid(self):
        selected, excluded = set(self.selected_execution_ids), set(
            self.excluded_execution_ids
        )
        if selected & excluded or not set(self.requested_execution_ids) <= selected:
            raise ValueError("execution selection partition is inconsistent")
        return _validate_fingerprint(self, "selection_fingerprint")


class PipelineDiagnostic(FrozenModel):
    code: str
    severity: PipelineDiagnosticSeverity
    phase: PipelineDiagnosticPhase
    execution_id: str | None = None
    reviewer_id: str | None = None
    related_execution_ids: tuple[str, ...] = ()
    safe_context: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("execution_id", None)
        values.setdefault("reviewer_id", None)
        values.setdefault("related_execution_ids", ())
        values.setdefault("safe_context", ())
        values["related_execution_ids"] = tuple(
            sorted(values.get("related_execution_ids", ()))
        )
        values["safe_context"] = tuple(sorted(values.get("safe_context", ())))
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class ReviewerExecutionOutcome(FrozenModel):
    execution_id: str
    reviewer_id: str
    required: bool
    status: ReviewerExecutionStatus
    review_result: EditorialReviewResult | None = None
    skip_code: str | None = None
    failure_code: str | None = None
    diagnostics: tuple[PipelineDiagnostic, ...] = ()
    outcome_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("review_result", None)
        values.setdefault("skip_code", None)
        values.setdefault("failure_code", None)
        values.setdefault("diagnostics", ())
        values["outcome_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def terminal_interpretation(self):
        if (self.status is ReviewerExecutionStatus.COMPLETED) != (
            self.review_result is not None
        ):
            raise ValueError("only completed outcomes contain a review result")
        if self.status is ReviewerExecutionStatus.SKIPPED and not self.skip_code:
            raise ValueError("skipped outcome requires skip_code")
        if self.status is ReviewerExecutionStatus.FAILED and not self.failure_code:
            raise ValueError("failed outcome requires failure_code")
        return _validate_fingerprint(self, "outcome_fingerprint")


class PipelineTraceEvent(FrozenModel):
    sequence: int = Field(ge=0)
    event_type: PipelineTraceEventType
    revision: int = Field(ge=0)
    execution_id: str | None = None
    reviewer_id: str | None = None
    related_execution_ids: tuple[str, ...] = ()
    outcome_status: ReviewerExecutionStatus | None = None
    code: str | None = None
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("execution_id", None)
        values.setdefault("reviewer_id", None)
        values.setdefault("related_execution_ids", ())
        values.setdefault("outcome_status", None)
        values.setdefault("code", None)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "event_fingerprint")


class ReviewerPipelineState(FrozenModel):
    pipeline_id: str = PIPELINE_ID
    pipeline_version: str = PIPELINE_VERSION
    draft_fingerprint: str
    plan_fingerprint: str
    registry_fingerprint: str
    policy_fingerprint: str
    selection_fingerprint: str
    revision: int = Field(ge=0)
    lifecycle: ReviewerPipelineLifecycleStatus
    selected_execution_ids: tuple[str, ...]
    pending_execution_ids: tuple[str, ...]
    ready_execution_ids: tuple[str, ...]
    outcomes: tuple[ReviewerExecutionOutcome, ...] = ()
    diagnostics: tuple[PipelineDiagnostic, ...] = ()
    trace: tuple[PipelineTraceEvent, ...] = ()
    halt_code: str | None = None
    state_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("pipeline_id", PIPELINE_ID)
        values.setdefault("pipeline_version", PIPELINE_VERSION)
        values.setdefault("outcomes", ())
        values.setdefault("diagnostics", ())
        values.setdefault("trace", ())
        values.setdefault("halt_code", None)
        values["state_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def partitions_valid(self):
        terminal = {item.execution_id for item in self.outcomes}
        pending, ready, selected = (
            set(self.pending_execution_ids),
            set(self.ready_execution_ids),
            set(self.selected_execution_ids),
        )
        if (
            pending & ready
            or terminal & (pending | ready)
            or pending | ready | terminal != selected
        ):
            raise ValueError("pipeline state partitions are inconsistent")
        return _validate_fingerprint(self, "state_fingerprint")


class ReviewerPipelineCoverage(FrozenModel):
    full_plan_execution_ids: tuple[str, ...]
    selected_execution_ids: tuple[str, ...]
    requested_execution_ids: tuple[str, ...]
    dependency_execution_ids: tuple[str, ...]
    excluded_execution_ids: tuple[str, ...]
    completed_execution_ids: tuple[str, ...]
    skipped_execution_ids: tuple[str, ...]
    failed_execution_ids: tuple[str, ...]
    required_execution_ids: tuple[str, ...]
    optional_execution_ids: tuple[str, ...]
    coverage_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["coverage_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "coverage_fingerprint")


class ReviewerPipelineResult(FrozenModel):
    pipeline_id: str
    pipeline_version: str
    status: ReviewerPipelineStatus
    lifecycle: ReviewerPipelineLifecycleStatus
    request_fingerprint: str
    plan_fingerprint: str
    registry_fingerprint: str
    policy_fingerprint: str
    selection_fingerprint: str
    execution_outcomes: tuple[ReviewerExecutionOutcome, ...]
    accepted_review_results: tuple[EditorialReviewResult, ...]
    coverage: ReviewerPipelineCoverage
    diagnostics: tuple[PipelineDiagnostic, ...]
    trace: tuple[PipelineTraceEvent, ...]
    trace_fingerprint: str
    state_fingerprint: str
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["trace_fingerprint"] = fingerprint(values["trace"])
        values["result_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.trace_fingerprint != fingerprint(self.trace):
            raise ValueError("trace_fingerprint is inconsistent")
        return _validate_fingerprint(self, "result_fingerprint")


class ReviewerPipelineExecutionReport(FrozenModel):
    result: ReviewerPipelineResult
    outcome_counts: tuple[tuple[str, int], ...]
    report_fingerprint: str

    @classmethod
    def from_result(cls, result: ReviewerPipelineResult):
        counts = tuple(
            (
                status.value,
                sum(item.status is status for item in result.execution_outcomes),
            )
            for status in ReviewerExecutionStatus
        )
        return cls(
            result=result,
            outcome_counts=counts,
            report_fingerprint=fingerprint(
                {"result": result, "outcome_counts": counts}
            ),
        )

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "report_fingerprint")


def _validate_fingerprint(model, field_name):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
