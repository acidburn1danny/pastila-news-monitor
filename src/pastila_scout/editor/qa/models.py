"""Private immutable contracts for Editorial QA architecture."""

import hashlib
import json
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.generation.prompt import canonicalize


def canonical_json(value: Any) -> str:
    """Return strict deterministic UTF-8-compatible JSON."""

    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class EditorialIssueFamily(StrEnum):
    STRUCTURE = "structure"
    FACTUALITY = "factuality"
    VOICE = "voice"
    HUMOR = "humor"
    SENSITIVITY = "sensitivity"
    RUNTIME = "runtime"
    CALLBACK = "callback"
    TRANSITION = "transition"
    OPENING = "opening"
    CLOSING = "closing"
    CTA = "cta"
    REPETITION = "repetition"
    LANGUAGE = "language"
    FLOW = "flow"
    COMPLIANCE = "compliance"


class EditorialSeverity(IntEnum):
    INFO = 10
    WARNING = 20
    ERROR = 30
    CRITICAL = 40


class EditorialConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewScope(StrEnum):
    EPISODE = "episode"
    OPENING = "opening"
    STORY = "story"
    TRANSITION = "transition"
    CLOSING = "closing"
    CTA = "cta"
    TELEPROMPTER = "teleprompter"


class ReviewerCapability(StrEnum):
    STRUCTURE = "structure"
    VOICE = "voice"
    HUMOR = "humor"
    SENSITIVITY = "sensitivity"
    RUNTIME = "runtime"
    CALLBACK = "callback"
    TRANSITION = "transition"
    FACTUAL_DECLARATION = "factual_declaration"
    LANGUAGE = "language"


class ReviewExecutionStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"
    SKIPPED = "skipped"


class ManifestStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AggregationStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REQUIRES_REGENERATION = "requires_regeneration"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REJECTED = "rejected"


class RequiredAction(StrEnum):
    NONE = "none"
    REVIEW_MANUALLY = "review_manually"
    REGENERATE_COMPONENTS = "regenerate_components"
    REJECT_EPISODE = "reject_episode"


class TraceEventType(StrEnum):
    MANIFEST_CREATED = "manifest_created"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_FAILED = "review_failed"
    RESULT_VALIDATED = "result_validated"
    RESULT_REJECTED = "result_rejected"
    STATE_ADVANCED = "state_advanced"
    FINDINGS_AGGREGATED = "findings_aggregated"
    APPROVAL_DECIDED = "approval_decided"


class FindingLocation(FrozenModel):
    component_type: ReviewScope
    component_id: str | None = None
    story_position: int | None = Field(default=None, gt=0)
    transition_from_story_position: int | None = Field(default=None, gt=0)
    transition_to_story_position: int | None = Field(default=None, gt=0)
    block_id: str | None = None
    sentence_index: int | None = Field(default=None, ge=0)
    character_start: int | None = Field(default=None, ge=0)
    character_end: int | None = Field(default=None, ge=0)
    quoted_excerpt: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def consistent(self):
        if self.component_type is ReviewScope.EPISODE and self.component_id is not None:
            raise ValueError("episode location must not name a component")
        if self.component_type is not ReviewScope.EPISODE and not self.component_id:
            raise ValueError("component location requires component_id")
        if self.character_end is not None and self.character_start is None:
            raise ValueError("character_end requires character_start")
        if (
            self.character_start is not None
            and self.character_end is not None
            and self.character_end < self.character_start
        ):
            raise ValueError("character offsets must be ordered")
        if self.component_type is ReviewScope.TRANSITION and (
            self.transition_from_story_position is None
            or self.transition_to_story_position is None
        ):
            raise ValueError("transition location requires both story positions")
        return self


class EvidenceItem(FrozenModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=500)


class MetadataEntry(FrozenModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=500)


class EditorialFinding(FrozenModel):
    finding_id: str = Field(pattern=r"^finding:sha256:[0-9a-f]{64}$")
    reviewer_id: str = Field(min_length=1)
    issue_family: EditorialIssueFamily
    issue_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    severity: EditorialSeverity
    confidence: EditorialConfidence
    scope: ReviewScope
    location: FindingLocation
    summary: str = Field(min_length=1, max_length=200)
    explanation: str = Field(min_length=1, max_length=1000)
    evidence: tuple[EvidenceItem, ...] = Field(default=(), max_length=10)
    recommendation: str | None = Field(default=None, max_length=500)
    blocking: bool
    waivable: bool = True
    related_finding_ids: tuple[str, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    @classmethod
    def build(cls, **values):
        values["finding_id"] = finding_id_for(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.scope is not self.location.component_type:
            raise ValueError("finding scope must match location")
        expected_blocking = self.severity >= EditorialSeverity.ERROR
        if self.blocking != expected_blocking:
            raise ValueError("blocking must be derived from severity")
        if self.severity is EditorialSeverity.CRITICAL and self.waivable:
            raise ValueError("critical findings cannot be waivable")
        if self.finding_id != finding_id_for(
            self.model_dump(exclude={"finding_id"}, mode="python")
        ):
            raise ValueError("finding_id does not match deterministic finding content")
        if self.finding_id in self.related_finding_ids:
            raise ValueError("finding cannot relate to itself")
        return self


def finding_id_for(values: dict[str, Any]) -> str:
    evidence = values.get("evidence", ())
    normalized = {
        "reviewer_id": values.get("reviewer_id"),
        "issue_code": values.get("issue_code"),
        "scope": values.get("scope"),
        "location": values.get("location"),
        "evidence": evidence,
    }
    return "finding:" + fingerprint(normalized)


class ReviewerCapabilities(FrozenModel):
    values: tuple[ReviewerCapability, ...] = Field(min_length=1)

    @field_validator("values")
    @classmethod
    def unique_sorted(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("reviewer capabilities must be unique")
        return tuple(sorted(value, key=lambda item: item.value))


class ContextEntry(FrozenModel):
    key: str
    value: str


class EditorialReviewRequest(FrozenModel):
    review_id: str
    reviewer_id: str
    episode_draft: EpisodeDraft
    scope: ReviewScope
    component_ids: tuple[str, ...]
    review_context: tuple[ContextEntry, ...] = ()
    policy: tuple[ContextEntry, ...] = ()
    prior_findings: tuple[EditorialFinding, ...] = ()

    @field_validator("component_ids")
    @classmethod
    def component_ids_unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("review component IDs must be unique")
        return value

    @model_validator(mode="after")
    def scope_matches_components(self):
        if self.scope is not ReviewScope.EPISODE and not self.component_ids:
            raise ValueError("component review scope requires component IDs")
        return self


class EditorialReviewResult(FrozenModel):
    reviewer_id: str
    reviewer_version: str
    status: ReviewExecutionStatus
    findings: tuple[EditorialFinding, ...] = ()
    warnings: tuple[str, ...] = ()
    reviewed_component_ids: tuple[str, ...]
    review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @classmethod
    def build(cls, **values):
        values["review_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_result(self):
        if (
            self.status in {ReviewExecutionStatus.FAILED, ReviewExecutionStatus.SKIPPED}
            and self.findings
        ):
            raise ValueError("failed or skipped result cannot contain findings")
        ids = [item.finding_id for item in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("review result finding IDs must be unique")
        expected = fingerprint(
            self.model_dump(exclude={"review_fingerprint"}, mode="python")
        )
        if self.review_fingerprint != expected:
            raise ValueError("review_fingerprint is inconsistent")
        return self


class ReviewerFailure(FrozenModel):
    manifest_item_id: str
    reviewer_id: str
    required: bool
    code: str
    message: str = Field(max_length=300)


class FindingCount(FrozenModel):
    severity: EditorialSeverity
    count: int = Field(ge=0)


class FindingGroup(FrozenModel):
    severity: EditorialSeverity
    scope: ReviewScope
    component_id: str | None
    reviewer_id: str
    count: int = Field(gt=0)


class CoverageEntry(FrozenModel):
    reviewer_id: str
    scope: ReviewScope
    component_ids: tuple[str, ...]
    completed: bool
    required: bool


class EditorialReviewReport(FrozenModel):
    report_id: str
    episode_draft_fingerprint: str
    manifest_fingerprint: str
    review_results: tuple[EditorialReviewResult, ...]
    findings: tuple[EditorialFinding, ...]
    finding_counts: tuple[FindingCount, ...]
    finding_groups: tuple[FindingGroup, ...]
    blocking_finding_ids: tuple[str, ...]
    reviewer_failures: tuple[ReviewerFailure, ...]
    warnings: tuple[str, ...]
    coverage: tuple[CoverageEntry, ...]
    report_fingerprint: str

    @model_validator(mode="after")
    def validate_derived_fields(self):
        ids = tuple(item.finding_id for item in self.findings)
        if len(ids) != len(set(ids)):
            raise ValueError("report finding IDs must be unique")
        count_map = {item.severity: item.count for item in self.finding_counts}
        if set(count_map) != set(EditorialSeverity):
            raise ValueError("report requires one count per severity")
        for severity in EditorialSeverity:
            if count_map[severity] != sum(
                item.severity is severity for item in self.findings
            ):
                raise ValueError("report finding counts are inconsistent")
        grouped_total = sum(item.count for item in self.finding_groups)
        if grouped_total != len(self.findings):
            raise ValueError("report finding groups are inconsistent")
        expected_blocking = tuple(
            item.finding_id for item in self.findings if item.blocking
        )
        if self.blocking_finding_ids != expected_blocking:
            raise ValueError("report blocking finding IDs are inconsistent")
        payload = self.model_dump(
            mode="python", exclude={"report_id", "report_fingerprint"}
        )
        expected = fingerprint(payload)
        if (
            self.report_fingerprint != expected
            or self.report_id != "qa-report:" + expected
        ):
            raise ValueError("report identity is inconsistent")
        return self


class EditorialApprovalPolicy(FrozenModel):
    policy_id: str = "default-editorial-approval"
    policy_version: str = "1"
    critical_status: ApprovalStatus = ApprovalStatus.REJECTED
    required_failure_status: ApprovalStatus = ApprovalStatus.REQUIRES_HUMAN_REVIEW


class EditorialApprovalDecision(FrozenModel):
    status: ApprovalStatus
    reason_codes: tuple[str, ...]
    blocking_finding_ids: tuple[str, ...]
    warning_finding_ids: tuple[str, ...]
    required_action: RequiredAction
    target_component_ids: tuple[str, ...] = ()
    decision_policy_id: str
    decision_policy_version: str
    decision_fingerprint: str

    @model_validator(mode="after")
    def validate_fingerprint(self):
        expected = fingerprint(
            self.model_dump(mode="python", exclude={"decision_fingerprint"})
        )
        if self.decision_fingerprint != expected:
            raise ValueError("decision fingerprint is inconsistent")
        return self


class QATraceRecord(FrozenModel):
    sequence_number: int = Field(gt=0)
    event_type: TraceEventType
    manifest_item_id: str | None = None
    reviewer_id: str | None = None
    state_revision_before: int
    state_revision_after: int
    result_fingerprint: str | None = None
    finding_ids: tuple[str, ...] = ()
    message_code: str


class EditorialQATrace(FrozenModel):
    records: tuple[QATraceRecord, ...]


class EditorialQAResult(FrozenModel):
    report: EditorialReviewReport
    decision: EditorialApprovalDecision
    manifest: Any
    state: Any
    trace: EditorialQATrace
