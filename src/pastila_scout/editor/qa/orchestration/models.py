"""Immutable M6C.5D orchestration contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.qa.manifest import EditorialReviewManifest
from pastila_scout.editor.qa.models import (
    EditorialApprovalPolicy,
    EditorialQAResult,
    fingerprint,
)
from pastila_scout.editor.qa.pipeline.models import (
    ReviewerPipelinePolicy,
    ReviewerPipelineResult,
)

ORCHESTRATOR_ID = "editorial-review-orchestrator"
ORCHESTRATOR_VERSION = "1.0.0"


class OrchestrationLifecycle(StrEnum):
    PREPARED = "prepared"
    PIPELINE_EXECUTED = "pipeline_executed"
    HANDED_OFF = "handed_off"
    FINALIZED = "finalized"
    FAILED = "failed"


class OrchestrationStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_LIMITED_REVIEW = "completed_with_limited_review"
    COMPLETED_WITHOUT_EDITORIAL_OUTCOME = "completed_without_editorial_outcome"
    FAILED_BEFORE_PIPELINE = "failed_before_pipeline"
    FAILED_AFTER_PIPELINE = "failed_after_pipeline"
    FAILED_DURING_EDITORIAL_HANDOFF = "failed_during_editorial_handoff"


class HandoffEligibilityCode(StrEnum):
    ELIGIBLE = "eligible"
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_PARTIAL_NOT_ALLOWED = "pipeline_partial_not_allowed"
    PIPELINE_SKIPS_NOT_ALLOWED = "pipeline_skips_not_allowed"
    NO_ACCEPTED_REVIEW_RESULTS = "no_accepted_review_results"
    IDENTITY_MISMATCH = "identity_mismatch"


class OrchestrationDiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class OrchestrationPhase(StrEnum):
    REQUEST = "request"
    MANIFEST = "manifest"
    PIPELINE = "pipeline"
    HANDOFF = "handoff"
    EDITORIAL = "editorial"
    FINALIZATION = "finalization"


class OrchestrationTraceEventType(StrEnum):
    REQUEST_VALIDATED = "request_validated"
    MANIFEST_RESOLVED = "manifest_resolved"
    PIPELINE_COMPLETED = "pipeline_completed"
    HANDOFF_ELIGIBLE = "handoff_eligible"
    HANDOFF_DENIED = "handoff_denied"
    EDITORIAL_COMPLETED = "editorial_completed"
    FINALIZED = "finalized"


class EditorialReviewOrchestrationPolicy(FrozenModel):
    require_pipeline_completion: bool = True
    permit_completed_with_skips: bool = False
    permit_partial_handoff: bool = False
    require_at_least_one_review_result: bool = True

    @property
    def policy_fingerprint(self):
        return fingerprint(self)


class EditorialReviewOrchestrationRequest(FrozenModel):
    draft: EpisodeDraft
    manifest: EditorialReviewManifest | None = None
    pipeline_policy: ReviewerPipelinePolicy = ReviewerPipelinePolicy()
    orchestration_policy: EditorialReviewOrchestrationPolicy = (
        EditorialReviewOrchestrationPolicy()
    )
    approval_policy: EditorialApprovalPolicy = EditorialApprovalPolicy()
    requested_execution_ids: tuple[str, ...] = ()

    @field_validator("requested_execution_ids")
    @classmethod
    def canonical_requested(cls, value):
        if len(value) != len(set(value)) or any(not item for item in value):
            raise ValueError("requested execution IDs must be nonempty and unique")
        return tuple(sorted(value))

    @property
    def request_fingerprint(self):
        return fingerprint(
            {
                "orchestrator": (ORCHESTRATOR_ID, ORCHESTRATOR_VERSION),
                "draft": fingerprint(self.draft),
                "manifest": (
                    self.manifest.manifest_fingerprint if self.manifest else None
                ),
                "pipeline_policy": self.pipeline_policy.policy_fingerprint,
                "orchestration_policy": self.orchestration_policy.policy_fingerprint,
                "approval_policy": self.approval_policy,
                "requested": self.requested_execution_ids,
            }
        )


class ManifestProviderDescriptor(FrozenModel):
    provider_id: str
    provider_version: str


class ReviewHandoffEligibility(FrozenModel):
    eligible: bool
    code: HandoffEligibilityCode
    accepted_review_result_fingerprints: tuple[str, ...]
    eligibility_fingerprint: str

    @classmethod
    def build(cls, **values):
        values["eligibility_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "eligibility_fingerprint")


class OrchestrationDiagnostic(FrozenModel):
    code: str
    severity: OrchestrationDiagnosticSeverity
    phase: OrchestrationPhase
    safe_context: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values):
        values["safe_context"] = tuple(sorted(values.get("safe_context", ())))
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class OrchestrationTraceEvent(FrozenModel):
    sequence: int = Field(ge=0)
    event_type: OrchestrationTraceEventType
    phase: OrchestrationPhase
    code: str | None = None
    event_fingerprint: str

    @classmethod
    def build(cls, **values):
        values.setdefault("code", None)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "event_fingerprint")


class EditorialReviewCompleteness(FrozenModel):
    requested_execution_count: int = Field(ge=0)
    selected_execution_count: int = Field(ge=0)
    accepted_result_count: int = Field(ge=0)
    failed_execution_count: int = Field(ge=0)
    skipped_execution_count: int = Field(ge=0)
    required_execution_count: int = Field(ge=0)
    completed_required_count: int = Field(ge=0)
    editorial_handoff_performed: bool
    editorial_outcome_present: bool
    limited_review: bool


class EditorialReviewOrchestrationReport(FrozenModel):
    orchestrator_id: str
    orchestrator_version: str
    draft_fingerprint: str
    manifest_fingerprint: str | None
    pipeline_status: str | None
    orchestration_status: OrchestrationStatus
    editorial_status: str | None
    handoff_performed: bool
    completeness: EditorialReviewCompleteness
    diagnostic_codes: tuple[str, ...]
    report_fingerprint: str

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "report_fingerprint")


class EditorialReviewOrchestrationResult(FrozenModel):
    orchestrator_id: str = ORCHESTRATOR_ID
    orchestrator_version: str = ORCHESTRATOR_VERSION
    request_fingerprint: str
    draft_fingerprint: str
    manifest_fingerprint: str | None
    pipeline_result: ReviewerPipelineResult | None
    handoff_eligibility: ReviewHandoffEligibility | None
    editorial_result: EditorialQAResult | None
    status: OrchestrationStatus
    lifecycle: OrchestrationLifecycle
    diagnostics: tuple[OrchestrationDiagnostic, ...]
    trace: tuple[OrchestrationTraceEvent, ...]
    report: EditorialReviewOrchestrationReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("orchestrator_id", ORCHESTRATOR_ID)
        values.setdefault("orchestrator_version", ORCHESTRATOR_VERSION)
        values["result_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"result_fingerprint"}, mode="python")
        )
        if self.result_fingerprint != expected:
            raise ValueError("orchestration result fingerprint is inconsistent")
        return self


def _validate_fingerprint(model, field_name):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
