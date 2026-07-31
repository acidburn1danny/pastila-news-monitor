"""Immutable provider-neutral contracts for targeted draft revision."""

import re
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel

from .enums import (
    ControlledGenerationOperation,
    RevisionDiagnosticCode,
    RevisionGatewayStatus,
    RevisionLifecyclePhase,
    RevisionResultStatus,
    RevisionTargetType,
)
from .identity import field, revision_fingerprint

CONTRACT_VERSION = "controlled-revision-request-v1"
INVOCATION_VERSION = "controlled-revision-invocation-v1"
GATEWAY_RESULT_VERSION = "controlled-revision-gateway-result-v1"
RESULT_VERSION = "controlled-revision-result-v1"
LIFECYCLE_VERSION = "controlled-revision-lifecycle-v1"
REPORT_VERSION = "controlled-revision-report-v1"
_FP = re.compile(r"^sha256:[0-9a-f]{64}$")


class ControlledRevisionTarget(FrozenModel):
    """Boundary projection of one upstream-authorized typed target."""

    target_type: RevisionTargetType
    story_id: int | None = Field(default=None, gt=0)
    from_story_id: int | None = Field(default=None, gt=0)
    to_story_id: int | None = Field(default=None, gt=0)
    upstream_target_fingerprint: str
    target_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("story_id", None)
        values.setdefault("from_story_id", None)
        values.setdefault("to_story_id", None)
        values["target_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @property
    def canonical_key(self) -> tuple[int, int, int]:
        return (
            tuple(RevisionTargetType).index(self.target_type),
            self.story_id or self.from_story_id or 0,
            self.to_story_id or 0,
        )

    @property
    def canonical_reference(self) -> str:
        """Return the sole canonical structural identifier for this target."""

        if self.target_type is RevisionTargetType.STORY:
            return f"story:{self.story_id}"
        if self.target_type is RevisionTargetType.TRANSITION:
            return f"transition:{self.from_story_id}:{self.to_story_id}"
        return self.target_type.value

    @model_validator(mode="after")
    def invariants(self):
        if self.target_type is RevisionTargetType.STORY:
            valid = (
                self.story_id is not None
                and self.from_story_id is self.to_story_id is None
            )
        elif self.target_type is RevisionTargetType.TRANSITION:
            valid = (
                self.story_id is None
                and self.from_story_id is not None
                and self.to_story_id is not None
                and self.from_story_id != self.to_story_id
            )
        else:
            valid = self.story_id is self.from_story_id is self.to_story_id is None
        if not valid:
            raise ValueError("controlled revision target identity is inconsistent")
        return _validate_fingerprint(self, "target_fingerprint")


class ControlledRevisionPolicy(FrozenModel):
    preserve_unmodified_content: bool = True
    require_explicit_scope: bool = True
    allow_structural_changes: bool = False
    allow_factual_changes: bool = False
    maximum_revision_targets: int = Field(ge=1, le=50)
    upstream_policy_fingerprint: str
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("preserve_unmodified_content", True)
        values.setdefault("require_explicit_scope", True)
        values.setdefault("allow_structural_changes", False)
        values.setdefault("allow_factual_changes", False)
        values["policy_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if not self.preserve_unmodified_content or not self.require_explicit_scope:
            raise ValueError("controlled revision requires explicit preservation")
        return _validate_fingerprint(self, "policy_fingerprint")


class ControlledRevisionInstructions(FrozenModel):
    """Authorized instruction content; hidden from repr and safe reports."""

    editorial_instruction: str = Field(min_length=1, max_length=1000, repr=False)
    authorized_scope_fingerprint: str
    upstream_instructions_fingerprint: str
    instructions_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["editorial_instruction"] = values["editorial_instruction"].strip()
        values["instructions_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @field_validator("editorial_instruction")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("controlled revision instruction is blank")
        return value

    @model_validator(mode="after")
    def invariants(self):
        return _validate_fingerprint(self, "instructions_fingerprint")


class DraftPreservationRequirements(FrozenModel):
    """Typed declaration of authorized and protected draft regions."""

    source_draft_fingerprint: str
    allowed_target_fingerprints: tuple[str, ...] = Field(min_length=1)
    protected_component_fingerprints: tuple[tuple[str, str], ...]
    immutable_fields: tuple[str, ...] = ("episode_id",)
    require_structural_compatibility: bool = True
    upstream_scope_fingerprint: str
    preservation_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["allowed_target_fingerprints"] = tuple(
            sorted(values["allowed_target_fingerprints"])
        )
        values["protected_component_fingerprints"] = tuple(
            sorted(values.get("protected_component_fingerprints", ()))
        )
        values["immutable_fields"] = tuple(
            sorted(values.get("immutable_fields", ("episode_id",)))
        )
        values.setdefault("require_structural_compatibility", True)
        values["preservation_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if len(set(self.allowed_target_fingerprints)) != len(
            self.allowed_target_fingerprints
        ):
            raise ValueError("preservation targets contain duplicates")
        if len({key for key, _ in self.protected_component_fingerprints}) != len(
            self.protected_component_fingerprints
        ):
            raise ValueError("protected component identifiers contain duplicates")
        return _validate_fingerprint(self, "preservation_fingerprint")


class ControlledRevisionOutputContract(FrozenModel):
    output_type: str = Field(default="episode_draft", pattern="^episode_draft$")
    episode_draft_contract_version: str = Field(default="1", pattern="^1$")
    source_draft_fingerprint: str
    preservation_fingerprint: str
    require_distinct_draft_identity: bool = True
    output_contract_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("output_type", "episode_draft")
        values.setdefault("episode_draft_contract_version", "1")
        values.setdefault("require_distinct_draft_identity", True)
        values["output_contract_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        return _validate_fingerprint(self, "output_contract_fingerprint")


class ControlledRevisionRequest(FrozenModel):
    contract_version: str = CONTRACT_VERSION
    operation: ControlledGenerationOperation = ControlledGenerationOperation.REVISION
    source_draft: EpisodeDraft = Field(repr=False)
    revision_targets: tuple[ControlledRevisionTarget, ...] = Field(min_length=1)
    revision_instructions: ControlledRevisionInstructions = Field(repr=False)
    revision_policy: ControlledRevisionPolicy
    preservation_requirements: DraftPreservationRequirements
    expected_output_contract: ControlledRevisionOutputContract
    planning_input_fingerprint: str
    executor_request_fingerprint: str
    revision_request_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", CONTRACT_VERSION)
        values.setdefault("operation", ControlledGenerationOperation.REVISION)
        values["revision_targets"] = tuple(
            sorted(values["revision_targets"], key=lambda item: item.canonical_key)
        )
        values["revision_request_fingerprint"] = revision_fingerprint(
            _request_identity(values)
        )
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported controlled revision request version")
        if self.operation is not ControlledGenerationOperation.REVISION:
            raise ValueError("controlled revision operation must be explicit")
        if (
            tuple(sorted(self.revision_targets, key=lambda item: item.canonical_key))
            != self.revision_targets
        ):
            raise ValueError("controlled revision targets are not canonical")
        if len({item.target_fingerprint for item in self.revision_targets}) != len(
            self.revision_targets
        ):
            raise ValueError("controlled revision targets contain duplicates")
        if len(self.revision_targets) > self.revision_policy.maximum_revision_targets:
            raise ValueError("controlled revision exceeds policy target limit")
        source_fp = revision_fingerprint(self.source_draft)
        if self.preservation_requirements.source_draft_fingerprint != source_fp:
            raise ValueError("preservation source lineage is inconsistent")
        if self.expected_output_contract.source_draft_fingerprint != source_fp:
            raise ValueError("output-contract source lineage is inconsistent")
        if (
            self.expected_output_contract.preservation_fingerprint
            != self.preservation_requirements.preservation_fingerprint
        ):
            raise ValueError("output-contract preservation lineage is inconsistent")
        target_fps = tuple(
            sorted(item.target_fingerprint for item in self.revision_targets)
        )
        if self.preservation_requirements.allowed_target_fingerprints != target_fps:
            raise ValueError("preservation target lineage is inconsistent")
        if (
            self.revision_instructions.authorized_scope_fingerprint
            != self.preservation_requirements.upstream_scope_fingerprint
        ):
            raise ValueError("revision instructions do not reference authorized scope")
        _validate_targets_against_draft(self.revision_targets, self.source_draft)
        if _all_editable_targets(self.source_draft) == {
            _target_identity(item) for item in self.revision_targets
        }:
            raise ValueError("controlled revision cannot imply full regeneration")
        expected = revision_fingerprint(
            _request_identity(self.model_dump(mode="python"))
        )
        if self.revision_request_fingerprint != expected:
            raise ValueError("controlled revision request fingerprint is inconsistent")
        return self


class ControlledRevisionLifecycle(FrozenModel):
    lifecycle_version: str = LIFECYCLE_VERSION
    phases: tuple[RevisionLifecyclePhase, ...] = (RevisionLifecyclePhase.CREATED,)
    lifecycle_fingerprint: str

    @classmethod
    def build(cls, phases=(RevisionLifecyclePhase.CREATED,)):
        values = {"lifecycle_version": LIFECYCLE_VERSION, "phases": tuple(phases)}
        values["lifecycle_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.lifecycle_version != LIFECYCLE_VERSION or not self.phases:
            raise ValueError("unsupported controlled revision lifecycle")
        if self.phases[0] is not RevisionLifecyclePhase.CREATED:
            raise ValueError("controlled revision lifecycle must start at created")
        valid = _valid_lifecycle(self.phases)
        if not valid:
            raise ValueError("controlled revision lifecycle transition is invalid")
        return _validate_fingerprint(self, "lifecycle_fingerprint")


class ControlledRevisionInvocation(FrozenModel):
    invocation_version: str = INVOCATION_VERSION
    operation: ControlledGenerationOperation = ControlledGenerationOperation.REVISION
    request: ControlledRevisionRequest
    lifecycle: ControlledRevisionLifecycle
    invocation_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("invocation_version", INVOCATION_VERSION)
        values.setdefault("operation", ControlledGenerationOperation.REVISION)
        values.setdefault(
            "lifecycle",
            ControlledRevisionLifecycle.build(
                (RevisionLifecyclePhase.CREATED, RevisionLifecyclePhase.VALIDATED)
            ),
        )
        values["invocation_fingerprint"] = revision_fingerprint(
            _invocation_identity(values)
        )
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if (
            self.invocation_version != INVOCATION_VERSION
            or self.operation is not ControlledGenerationOperation.REVISION
        ):
            raise ValueError("unsupported controlled revision invocation")
        if self.request.operation is not self.operation:
            raise ValueError("revision invocation operation mismatch")
        if self.lifecycle.phases[-1] is not RevisionLifecyclePhase.VALIDATED:
            raise ValueError("revision invocation must be validated")
        return _validate_identity(self, "invocation_fingerprint", _invocation_identity)


class ControlledRevisionDiagnostic(FrozenModel):
    code: RevisionDiagnosticCode
    safe_message: str = Field(min_length=1, max_length=200)
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["diagnostic_fingerprint"] = revision_fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_message")
    @classmethod
    def safe(cls, value: str) -> str:
        lowered = value.casefold()
        if any(
            token in lowered
            for token in ("api_key", "bearer ", "traceback", "c:\\", "/home/")
        ):
            raise ValueError("revision diagnostic contains unsafe detail")
        return value

    @model_validator(mode="after")
    def invariants(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class ControlledRevisionGatewayResult(FrozenModel):
    gateway_result_version: str = GATEWAY_RESULT_VERSION
    status: RevisionGatewayStatus
    revised_draft: EpisodeDraft | None = Field(default=None, repr=False)
    source_draft_fingerprint: str
    revision_request_fingerprint: str
    invocation_fingerprint: str
    output_contract_fingerprint: str
    preservation_fingerprint: str
    diagnostic: ControlledRevisionDiagnostic | None = None
    gateway_result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("gateway_result_version", GATEWAY_RESULT_VERSION)
        values.setdefault("revised_draft", None)
        values.setdefault("diagnostic", None)
        values["gateway_result_fingerprint"] = revision_fingerprint(
            _gateway_identity(values)
        )
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.gateway_result_version != GATEWAY_RESULT_VERSION:
            raise ValueError("unsupported revision gateway-result version")
        success = self.status is RevisionGatewayStatus.SUCCESS
        if success != (self.revised_draft is not None) or success == (
            self.diagnostic is not None
        ):
            raise ValueError("revision gateway-result shape is inconsistent")
        return _validate_identity(self, "gateway_result_fingerprint", _gateway_identity)


class ControlledRevisionResult(FrozenModel):
    result_version: str = RESULT_VERSION
    status: RevisionResultStatus
    revised_draft: EpisodeDraft | None = Field(default=None, repr=False)
    source_draft_fingerprint: str
    revision_request_fingerprint: str
    invocation_fingerprint: str
    gateway_result_fingerprint: str
    output_contract_fingerprint: str
    preservation_fingerprint: str
    lifecycle: ControlledRevisionLifecycle
    diagnostic: ControlledRevisionDiagnostic | None = None
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("result_version", RESULT_VERSION)
        values.setdefault("revised_draft", None)
        values.setdefault("diagnostic", None)
        values["result_fingerprint"] = revision_fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.result_version != RESULT_VERSION:
            raise ValueError("unsupported controlled revision result version")
        success = self.status is RevisionResultStatus.SUCCESS
        if success:
            if (
                self.revised_draft is None
                or self.diagnostic is not None
                or self.lifecycle.phases[-1] is not RevisionLifecyclePhase.COMPLETED
            ):
                raise ValueError(
                    "successful controlled revision result is inconsistent"
                )
        elif (
            self.revised_draft is not None
            or self.diagnostic is None
            or self.lifecycle.phases[-1] is not RevisionLifecyclePhase.FAILED
        ):
            raise ValueError("failed controlled revision result is inconsistent")
        return _validate_identity(self, "result_fingerprint", _result_identity)


def _validate_fingerprint(model: FrozenModel, name: str):
    if not _FP.fullmatch(getattr(model, name)):
        raise ValueError(f"{name} has invalid format")
    expected = revision_fingerprint(model.model_dump(exclude={name}, mode="python"))
    if getattr(model, name) != expected:
        raise ValueError(f"{name} is inconsistent")
    return model


def _validate_identity(model, name, identity):
    expected = revision_fingerprint(identity(model.model_dump(mode="python")))
    if getattr(model, name) != expected:
        raise ValueError(f"{name} is inconsistent")
    return model


def _request_identity(values):
    return {
        "contract_version": values["contract_version"],
        "operation": values["operation"],
        "source_draft_fingerprint": revision_fingerprint(values["source_draft"]),
        "target_fingerprints": tuple(
            field(item, "target_fingerprint") for item in values["revision_targets"]
        ),
        "instructions_fingerprint": field(
            values["revision_instructions"], "instructions_fingerprint"
        ),
        "policy_fingerprint": field(values["revision_policy"], "policy_fingerprint"),
        "preservation_fingerprint": field(
            values["preservation_requirements"], "preservation_fingerprint"
        ),
        "output_contract_fingerprint": field(
            values["expected_output_contract"], "output_contract_fingerprint"
        ),
        "planning_input_fingerprint": values["planning_input_fingerprint"],
        "executor_request_fingerprint": values["executor_request_fingerprint"],
    }


def _invocation_identity(values):
    return {
        "invocation_version": values["invocation_version"],
        "operation": values["operation"],
        "request_fingerprint": field(values["request"], "revision_request_fingerprint"),
        "lifecycle_fingerprint": field(values["lifecycle"], "lifecycle_fingerprint"),
    }


def _gateway_identity(values):
    return {
        key: (
            revision_fingerprint(value)
            if key == "revised_draft" and value is not None
            else (
                field(value, "diagnostic_fingerprint")
                if key == "diagnostic" and value is not None
                else value
            )
        )
        for key, value in values.items()
        if key != "gateway_result_fingerprint"
    }


def _result_identity(values):
    return {
        key: (
            revision_fingerprint(value)
            if key == "revised_draft" and value is not None
            else (
                field(value, "lifecycle_fingerprint")
                if key == "lifecycle"
                else (
                    field(value, "diagnostic_fingerprint")
                    if key == "diagnostic" and value is not None
                    else value
                )
            )
        )
        for key, value in values.items()
        if key != "result_fingerprint"
    }


def _target_identity(target):
    return (
        target.target_type,
        target.story_id or target.from_story_id,
        target.to_story_id,
    )


def _all_editable_targets(draft):
    targets = {
        (RevisionTargetType.OPENING, None, None),
        (RevisionTargetType.CLOSING, None, None),
    }
    targets.update(
        (RevisionTargetType.STORY, item.story_id, None) for item in draft.stories
    )
    targets.update(
        (RevisionTargetType.TRANSITION, item.from_story_id, item.to_story_id)
        for item in draft.transitions
    )
    if draft.cta is not None:
        targets.add((RevisionTargetType.CALL_TO_ACTION, None, None))
    return targets


def _validate_targets_against_draft(targets, draft):
    valid = _all_editable_targets(draft)
    if any(_target_identity(target) not in valid for target in targets):
        raise ValueError("controlled revision target is absent from source draft")


def _valid_lifecycle(phases):
    normal = (
        RevisionLifecyclePhase.CREATED,
        RevisionLifecyclePhase.VALIDATED,
        RevisionLifecyclePhase.INVOKED,
        RevisionLifecyclePhase.GATEWAY_COMPLETED,
        RevisionLifecyclePhase.OUTPUT_VALIDATED,
        RevisionLifecyclePhase.COMPLETED,
    )
    if len(phases) != len(set(phases)):
        return False
    if phases[-1] is RevisionLifecyclePhase.FAILED:
        prefix = phases[:-1]
        return bool(prefix) and normal[: len(prefix)] == prefix
    return normal[: len(phases)] == phases
