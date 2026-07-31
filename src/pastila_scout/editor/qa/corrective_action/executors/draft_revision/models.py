"""Immutable M6C.6D draft-revision contracts."""

import re
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutorRequest,
    CorrectiveActionOutputReference,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.models import fingerprint

from .descriptor import build_draft_revision_executor_descriptor
from .enums import (
    DraftRevisionDiagnosticCategory,
    DraftRevisionDiagnosticCode,
    DraftRevisionOutcome,
    DraftRevisionStatus,
    DraftRevisionTargetType,
)
from .policy import DraftRevisionPolicy

CONTRACT_VERSION = "1"
TARGET_VERSION = "1"
SCOPE_VERSION = "1"
INSTRUCTIONS_VERSION = "1"
DIAGNOSTIC_VERSION = "1"
OUTPUT_REFERENCE_VERSION = "1"
RESULT_VERSION = "1"
REPORT_VERSION = "1"
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")


class DraftRevisionTarget(FrozenModel):
    target_version: str = TARGET_VERSION
    target_type: DraftRevisionTargetType
    story_id: int | None = Field(default=None, gt=0)
    from_story_id: int | None = Field(default=None, gt=0)
    to_story_id: int | None = Field(default=None, gt=0)
    target_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("target_version", TARGET_VERSION)
        values.setdefault("story_id", None)
        values.setdefault("from_story_id", None)
        values.setdefault("to_story_id", None)
        values["target_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @property
    def canonical_key(self) -> tuple[int, int, int]:
        return (
            tuple(DraftRevisionTargetType).index(self.target_type),
            self.story_id or self.from_story_id or 0,
            self.to_story_id or 0,
        )

    @model_validator(mode="after")
    def invariants(self):
        if self.target_version != TARGET_VERSION:
            raise ValueError("unsupported revision-target version")
        if self.target_type is DraftRevisionTargetType.STORY:
            valid = (
                self.story_id is not None
                and self.from_story_id is None
                and self.to_story_id is None
            )
        elif self.target_type is DraftRevisionTargetType.TRANSITION:
            valid = (
                self.story_id is None
                and self.from_story_id is not None
                and self.to_story_id is not None
                and self.from_story_id != self.to_story_id
            )
        else:
            valid = (
                self.story_id is None
                and self.from_story_id is None
                and self.to_story_id is None
            )
        if not valid:
            raise ValueError("revision target identity is inconsistent")
        return _validate_fingerprint(self, "target_fingerprint")


class DraftRevisionScope(FrozenModel):
    scope_version: str = SCOPE_VERSION
    targets: tuple[DraftRevisionTarget, ...] = Field(min_length=1)
    maximum_targets: int = Field(ge=1, le=50)
    scope_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("scope_version", SCOPE_VERSION)
        values["targets"] = tuple(
            sorted(values["targets"], key=lambda item: item.canonical_key)
        )
        values["scope_fingerprint"] = fingerprint(_scope_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.scope_version != SCOPE_VERSION:
            raise ValueError("unsupported draft-revision scope version")
        if len(self.targets) > self.maximum_targets:
            raise ValueError("revision scope exceeds maximum targets")
        if (
            tuple(sorted(self.targets, key=lambda item: item.canonical_key))
            != self.targets
        ):
            raise ValueError("revision targets are not canonical")
        if len({item.target_fingerprint for item in self.targets}) != len(self.targets):
            raise ValueError("revision scope contains duplicate targets")
        if self.scope_fingerprint != fingerprint(
            _scope_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("draft-revision scope fingerprint is inconsistent")
        return self


class DraftRevisionInstructions(FrozenModel):
    instructions_version: str = INSTRUCTIONS_VERSION
    scope_fingerprint: str
    editorial_instruction: str = Field(min_length=1, max_length=1000)
    instructions_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("instructions_version", INSTRUCTIONS_VERSION)
        values["editorial_instruction"] = values["editorial_instruction"].strip()
        values["instructions_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("scope_fingerprint")
    @classmethod
    def scope_fingerprint_valid(cls, value: str) -> str:
        if not _FINGERPRINT.fullmatch(value):
            raise ValueError("instruction scope fingerprint is invalid")
        return value

    @field_validator("editorial_instruction")
    @classmethod
    def instruction_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("revision instruction must not be blank")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.instructions_version != INSTRUCTIONS_VERSION:
            raise ValueError("unsupported revision-instructions version")
        return _validate_fingerprint(self, "instructions_fingerprint")


class DraftRevisionRequest(FrozenModel):
    contract_version: str = CONTRACT_VERSION
    executor_request: CorrectiveActionExecutorRequest
    source_draft: EpisodeDraft
    policy: DraftRevisionPolicy
    scope: DraftRevisionScope
    instructions: DraftRevisionInstructions
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", CONTRACT_VERSION)
        values["request_fingerprint"] = fingerprint(_request_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported draft-revision request version")
        plan = self.executor_request.plan
        if plan.plan_type is not CorrectiveActionExecutionPlanType.REVISE_DRAFT:
            raise ValueError("draft revision requires REVISE_DRAFT")
        if (
            plan.required_capability
            is not CorrectiveActionExecutionCapability.DRAFT_REVISION
        ):
            raise ValueError("draft revision requires DRAFT_REVISION")
        if (
            self.executor_request.executor_descriptor
            != build_draft_revision_executor_descriptor()
        ):
            raise ValueError("executor request does not use revision descriptor")
        if plan.execution_mode is CorrectiveActionExecutionMode.NON_EXECUTABLE:
            raise ValueError("draft revision cannot be non-executable")
        if (
            plan.execution_mode is CorrectiveActionExecutionMode.HUMAN_GATED
            and self.executor_request.execution_context.authorization_state
            is not CorrectiveActionAuthorizationState.GRANTED
        ):
            raise ValueError("human-gated draft revision requires authorization")
        if self.scope.maximum_targets != self.policy.maximum_revision_targets:
            raise ValueError("revision scope and policy target limits differ")
        if self.instructions.scope_fingerprint != self.scope.scope_fingerprint:
            raise ValueError("revision instructions do not reference the scope")
        _validate_scope_against_draft(self.scope, self.source_draft)
        if self.request_fingerprint != fingerprint(
            _request_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("draft-revision request fingerprint is inconsistent")
        return self


class DraftRevisionDiagnostic(FrozenModel):
    diagnostic_version: str = DIAGNOSTIC_VERSION
    code: DraftRevisionDiagnosticCode
    category: DraftRevisionDiagnosticCategory
    safe_message: str
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("diagnostic_version", DIAGNOSTIC_VERSION)
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_message")
    @classmethod
    def safe_message_valid(cls, value: str) -> str:
        forbidden = ("\\", "/", "secret", "token", "prompt", "traceback", "@")
        if (
            not value.strip()
            or len(value) > 200
            or any(item in value.casefold() for item in forbidden)
        ):
            raise ValueError("revision diagnostic message is unsafe")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.diagnostic_version != DIAGNOSTIC_VERSION:
            raise ValueError("unsupported draft-revision diagnostic version")
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class DraftRevisionOutputReference(FrozenModel):
    reference_version: str = OUTPUT_REFERENCE_VERSION
    revision_request_fingerprint: str
    revised_draft_fingerprint: str
    revision_result_fingerprint: str
    executor_descriptor_fingerprint: str
    executor_output_reference: CorrectiveActionOutputReference
    output_reference_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("reference_version", OUTPUT_REFERENCE_VERSION)
        values["output_reference_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator(
        "revision_request_fingerprint",
        "revised_draft_fingerprint",
        "revision_result_fingerprint",
        "executor_descriptor_fingerprint",
    )
    @classmethod
    def lineage_valid(cls, value: str) -> str:
        if not _FINGERPRINT.fullmatch(value):
            raise ValueError("revision output lineage fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def invariants(self):
        if self.reference_version != OUTPUT_REFERENCE_VERSION:
            raise ValueError("unsupported revision output-reference version")
        generic = self.executor_output_reference
        if (
            generic.capability is not CorrectiveActionExecutionCapability.DRAFT_REVISION
            or generic.output_type != "episode-draft-revision"
        ):
            raise ValueError("generic output reference is not draft revision")
        if (
            generic.output_fingerprint != self.revised_draft_fingerprint
            or generic.capability_result_fingerprint != self.revision_result_fingerprint
        ):
            raise ValueError("generic output-reference lineage is inconsistent")
        return _validate_fingerprint(self, "output_reference_fingerprint")


class DraftRevisionResult(FrozenModel):
    contract_version: str = RESULT_VERSION
    revision_request: DraftRevisionRequest
    revision_outcome: DraftRevisionOutcome
    revision_status: DraftRevisionStatus
    revised_draft: EpisodeDraft | None
    output_reference: DraftRevisionOutputReference | None
    diagnostic: DraftRevisionDiagnostic | None
    result_fingerprint: str

    @classmethod
    def build_success(
        cls, revision_request: DraftRevisionRequest, revised_draft: EpisodeDraft
    ):
        core = _result_core_fingerprint(
            revision_request,
            DraftRevisionOutcome.COMPLETED,
            DraftRevisionStatus.COMPLETED,
            revised_draft,
        )
        generic = CorrectiveActionOutputReference.build(
            output_type="episode-draft-revision",
            capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
            output_fingerprint=fingerprint(revised_draft),
            capability_result_fingerprint=core,
        )
        reference = DraftRevisionOutputReference.build(
            revision_request_fingerprint=revision_request.request_fingerprint,
            revised_draft_fingerprint=fingerprint(revised_draft),
            revision_result_fingerprint=core,
            executor_descriptor_fingerprint=revision_request.executor_request.executor_descriptor.descriptor_fingerprint,
            executor_output_reference=generic,
        )
        return cls._build(
            revision_request=revision_request,
            revision_outcome=DraftRevisionOutcome.COMPLETED,
            revision_status=DraftRevisionStatus.COMPLETED,
            revised_draft=revised_draft,
            output_reference=reference,
            diagnostic=None,
        )

    @classmethod
    def build_failure(
        cls,
        *,
        revision_request: DraftRevisionRequest,
        revision_outcome: DraftRevisionOutcome,
        diagnostic: DraftRevisionDiagnostic,
    ):
        return cls._build(
            revision_request=revision_request,
            revision_outcome=revision_outcome,
            revision_status=DraftRevisionStatus.FAILED,
            revised_draft=None,
            output_reference=None,
            diagnostic=diagnostic,
        )

    @classmethod
    def _build(cls, **values: Any):
        values.setdefault("contract_version", RESULT_VERSION)
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != RESULT_VERSION:
            raise ValueError("unsupported draft-revision result version")
        completed = self.revision_outcome is DraftRevisionOutcome.COMPLETED
        if completed != (self.revision_status is DraftRevisionStatus.COMPLETED):
            raise ValueError("revision outcome and status are inconsistent")
        if completed:
            if (
                self.revised_draft is None
                or self.output_reference is None
                or self.diagnostic is not None
            ):
                raise ValueError("successful revision result shape is inconsistent")
            if self.revised_draft is self.revision_request.source_draft:
                raise ValueError("revised draft reuses source-draft identity")
            core = _result_core_fingerprint(
                self.revision_request,
                self.revision_outcome,
                self.revision_status,
                self.revised_draft,
            )
            if self.output_reference.revision_result_fingerprint != core:
                raise ValueError("revision output result lineage is inconsistent")
            if (
                self.output_reference.revision_request_fingerprint
                != self.revision_request.request_fingerprint
                or self.output_reference.revised_draft_fingerprint
                != fingerprint(self.revised_draft)
            ):
                raise ValueError("revision output lineage is inconsistent")
        elif (
            self.revised_draft is not None
            or self.output_reference is not None
            or self.diagnostic is None
        ):
            raise ValueError("failed revision result shape is inconsistent")
        if self.result_fingerprint != fingerprint(
            _result_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("draft-revision result fingerprint is inconsistent")
        return self


class DraftRevisionReport(FrozenModel):
    report_version: str = REPORT_VERSION
    capability: str
    plan_type: str
    target_count: int
    revision_outcome: DraftRevisionOutcome
    revision_status: DraftRevisionStatus
    diagnostic_code: DraftRevisionDiagnosticCode | None
    revision_request_fingerprint: str
    revision_result_fingerprint: str
    output_reference_fingerprint: str | None
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.report_version != REPORT_VERSION:
            raise ValueError("unsupported draft-revision report version")
        return _validate_fingerprint(self, "report_fingerprint")


def _validate_scope_against_draft(
    scope: DraftRevisionScope, draft: EpisodeDraft
) -> None:
    stories = {item.story_id for item in draft.stories}
    transitions = {(item.from_story_id, item.to_story_id) for item in draft.transitions}
    for target in scope.targets:
        if (
            target.target_type is DraftRevisionTargetType.STORY
            and target.story_id not in stories
        ):
            raise ValueError("revision target does not exist in source draft")
        if (
            target.target_type is DraftRevisionTargetType.TRANSITION
            and (target.from_story_id, target.to_story_id) not in transitions
        ):
            raise ValueError("revision transition does not exist in source draft")
        if (
            target.target_type is DraftRevisionTargetType.CALL_TO_ACTION
            and draft.cta is None
        ):
            raise ValueError("source draft has no call to action")


def _scope_identity(values):
    return {
        "scope_version": values["scope_version"],
        "target_fingerprints": tuple(
            (
                item["target_fingerprint"]
                if isinstance(item, dict)
                else item.target_fingerprint
            )
            for item in values["targets"]
        ),
        "maximum_targets": values["maximum_targets"],
    }


def _request_identity(values):
    def field(obj, name):
        return obj[name] if isinstance(obj, dict) else getattr(obj, name)

    return {
        "contract_version": values["contract_version"],
        "executor_request_fingerprint": field(
            values["executor_request"], "request_fingerprint"
        ),
        "source_draft_fingerprint": fingerprint(values["source_draft"]),
        "policy_fingerprint": field(values["policy"], "policy_fingerprint"),
        "scope_fingerprint": field(values["scope"], "scope_fingerprint"),
        "instructions_fingerprint": field(
            values["instructions"], "instructions_fingerprint"
        ),
    }


def _result_core_fingerprint(request, outcome, status, draft):
    return fingerprint(
        {
            "revision_request_fingerprint": request.request_fingerprint,
            "revision_outcome": outcome,
            "revision_status": status,
            "revised_draft_fingerprint": fingerprint(draft) if draft else None,
        }
    )


def _result_identity(values):
    def field(obj, name):
        return obj[name] if isinstance(obj, dict) else getattr(obj, name)

    return {
        "contract_version": values["contract_version"],
        "revision_request_fingerprint": field(
            values["revision_request"], "request_fingerprint"
        ),
        "revision_outcome": values["revision_outcome"],
        "revision_status": values["revision_status"],
        "revised_draft_fingerprint": (
            fingerprint(values["revised_draft"])
            if values.get("revised_draft")
            else None
        ),
        "output_reference_fingerprint": (
            field(values["output_reference"], "output_reference_fingerprint")
            if values.get("output_reference")
            else None
        ),
        "diagnostic_code": (
            field(values["diagnostic"], "code") if values.get("diagnostic") else None
        ),
    }


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
