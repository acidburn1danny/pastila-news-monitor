"""Immutable M6C.5E generation-to-review integration contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.blueprint_models import EditorialBlueprint
from pastila_scout.editor.commentary_models import EpisodeCommentaryBlueprint
from pastila_scout.editor.flow_models import FlowOptimizationResult
from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    FrozenModel,
    TeleprompterProfile,
)
from pastila_scout.editor.qa.manifest import EditorialReviewManifest
from pastila_scout.editor.qa.models import EditorialApprovalPolicy, fingerprint
from pastila_scout.editor.qa.orchestration.models import (
    EditorialReviewOrchestrationPolicy,
    EditorialReviewOrchestrationResult,
)
from pastila_scout.editor.qa.pipeline.models import ReviewerPipelinePolicy
from pastila_scout.editor.voice_models import EpisodeVoicePlan

INTEGRATION_ID = "editorial-review-integration"
INTEGRATION_VERSION = "1.0.0"


class EditorialReviewIntegrationDescriptor(FrozenModel):
    integration_id: str = INTEGRATION_ID
    integration_version: str = INTEGRATION_VERSION

    @property
    def descriptor_fingerprint(self) -> str:
        return fingerprint(self)


class IntegrationStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITHOUT_REVIEW = "completed_without_review"
    FAILED_DURING_GENERATION = "failed_during_generation"
    FAILED_BEFORE_REVIEW = "failed_before_review"
    FAILED_DURING_REVIEW = "failed_during_review"


class IntegrationLifecycle(StrEnum):
    PREPARED = "prepared"
    GENERATION_COMPLETED = "generation_completed"
    REVIEW_COMPLETED = "review_completed"
    FINALIZED = "finalized"
    FAILED = "failed"


class IntegrationPhase(StrEnum):
    REQUEST = "request"
    GENERATION = "generation"
    DRAFT_VALIDATION = "draft_validation"
    REVIEW_PREPARATION = "review_preparation"
    REVIEW = "review"
    FINALIZATION = "finalization"


class IntegrationTraceEventType(StrEnum):
    REQUEST_VALIDATED = "request_validated"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"
    DRAFT_VALIDATED = "draft_validated"
    DRAFT_REJECTED = "draft_rejected"
    REVIEW_REQUEST_PREPARED = "review_request_prepared"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_FAILED = "review_failed"
    FINALIZED = "finalized"


class IntegrationDiagnosticSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class EditorialReviewIntegrationPolicy(FrozenModel):
    require_valid_generation_result: bool = True
    require_review_after_generation: bool = True
    preserve_generation_failure_result: bool = True

    @property
    def policy_fingerprint(self) -> str:
        return fingerprint(self)


class ControlledGenerationInvocation(FrozenModel):
    scout_input: ScoutEditorInputV1
    selection_profile: SelectionProfileV1
    episode_context: EpisodeContextV1
    flow_result: FlowOptimizationResult
    editorial_blueprint: EditorialBlueprint
    commentary_blueprint: EpisodeCommentaryBlueprint
    voice_plan: EpisodeVoicePlan
    static_cta_content: str = Field(default="", exclude=True)
    teleprompter_profile: TeleprompterProfile | None = None

    @property
    def invocation_fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))

    def keyword_arguments(self) -> dict[str, Any]:
        """Return the original typed inputs expected by ``ControlledGenerator``."""

        return {
            "scout_input": self.scout_input,
            "selection_profile": self.selection_profile,
            "episode_context": self.episode_context,
            "flow_result": self.flow_result,
            "editorial_blueprint": self.editorial_blueprint,
            "commentary_blueprint": self.commentary_blueprint,
            "voice_plan": self.voice_plan,
            "static_cta_content": self.static_cta_content,
            "teleprompter_profile": self.teleprompter_profile,
        }


class EditorialReviewIntegrationRequest(FrozenModel):
    generation: ControlledGenerationInvocation
    review_manifest: EditorialReviewManifest | None = None
    requested_execution_ids: tuple[str, ...] = ()
    pipeline_policy: ReviewerPipelinePolicy = ReviewerPipelinePolicy()
    orchestration_policy: EditorialReviewOrchestrationPolicy = (
        EditorialReviewOrchestrationPolicy()
    )
    approval_policy: EditorialApprovalPolicy = EditorialApprovalPolicy()
    integration_policy: EditorialReviewIntegrationPolicy = (
        EditorialReviewIntegrationPolicy()
    )

    @field_validator("requested_execution_ids")
    @classmethod
    def canonical_requested(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or any(not item for item in value):
            raise ValueError("requested execution IDs must be nonempty and unique")
        return tuple(sorted(value))

    @property
    def request_fingerprint(self) -> str:
        return fingerprint(
            {
                "integration": (INTEGRATION_ID, INTEGRATION_VERSION),
                "generation": self.generation.invocation_fingerprint,
                "manifest": (
                    self.review_manifest.manifest_fingerprint
                    if self.review_manifest
                    else None
                ),
                "requested": self.requested_execution_ids,
                "pipeline_policy": self.pipeline_policy,
                "orchestration_policy": self.orchestration_policy,
                "approval_policy": self.approval_policy,
                "integration_policy": self.integration_policy,
            }
        )


class IntegrationDiagnostic(FrozenModel):
    code: str
    severity: IntegrationDiagnosticSeverity
    phase: IntegrationPhase
    safe_context: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> IntegrationDiagnostic:
        values["safe_context"] = tuple(sorted(values.get("safe_context", ())))
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self) -> IntegrationDiagnostic:
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class IntegrationTraceEvent(FrozenModel):
    sequence: int = Field(ge=0)
    event_type: IntegrationTraceEventType
    phase: IntegrationPhase
    code: str | None = None
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> IntegrationTraceEvent:
        values.setdefault("code", None)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self) -> IntegrationTraceEvent:
        return _validate_fingerprint(self, "event_fingerprint")


class IntegrationCompleteness(FrozenModel):
    generation_requested: bool
    generation_completed: bool
    generation_succeeded: bool
    draft_validated: bool
    review_required: bool
    review_eligible: bool
    review_invoked: bool
    review_completed: bool
    editorial_outcome_present: bool
    limited_completion: bool

    @property
    def completeness_fingerprint(self) -> str:
        return fingerprint(self)


class EditorialReviewIntegrationOutcome(FrozenModel):
    generation_succeeded: bool
    review_performed: bool
    review_completed_operationally: bool
    editorial_outcome_present: bool
    integration_completed: bool
    limited_completion: bool
    outcome_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> EditorialReviewIntegrationOutcome:
        values["outcome_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self) -> EditorialReviewIntegrationOutcome:
        return _validate_fingerprint(self, "outcome_fingerprint")


class EditorialReviewIntegrationReport(FrozenModel):
    integration_id: str
    integration_version: str
    request_fingerprint: str
    generation_request_fingerprint: str
    generation_present: bool
    generation_result_fingerprint: str | None
    draft_fingerprint: str | None
    review_required: bool
    review_status: str | None
    review_result_fingerprint: str | None
    editorial_status: str | None
    integration_status: IntegrationStatus
    review_performed: bool
    limited_completion: bool
    diagnostic_codes: tuple[str, ...]
    completeness: IntegrationCompleteness
    report_fingerprint: str

    @model_validator(mode="after")
    def identity_valid(self) -> EditorialReviewIntegrationReport:
        return _validate_fingerprint(self, "report_fingerprint")


class EditorialReviewIntegrationResult(FrozenModel):
    integration_id: str = INTEGRATION_ID
    integration_version: str = INTEGRATION_VERSION
    request_fingerprint: str
    generation_result: ControlledGenerationResult | None
    draft_fingerprint: str | None
    review_result: EditorialReviewOrchestrationResult | None
    status: IntegrationStatus
    lifecycle: IntegrationLifecycle
    diagnostics: tuple[IntegrationDiagnostic, ...]
    trace: tuple[IntegrationTraceEvent, ...]
    outcome: EditorialReviewIntegrationOutcome
    report: EditorialReviewIntegrationReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> EditorialReviewIntegrationResult:
        values.setdefault("integration_id", INTEGRATION_ID)
        values.setdefault("integration_version", INTEGRATION_VERSION)
        values["result_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self) -> EditorialReviewIntegrationResult:
        if self.review_result is not None and (
            self.generation_result is None or self.draft_fingerprint is None
        ):
            raise ValueError(
                "review result requires generation result and draft identity"
            )
        if self.status is IntegrationStatus.COMPLETED and self.review_result is None:
            raise ValueError("completed integration requires a review result")
        if (
            self.status is IntegrationStatus.FAILED_DURING_GENERATION
            and self.review_result is not None
        ):
            raise ValueError("generation failure cannot contain a review result")
        expected = fingerprint(
            self.model_dump(exclude={"result_fingerprint"}, mode="python")
        )
        if self.result_fingerprint != expected:
            raise ValueError("integration result fingerprint is inconsistent")
        return self


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
