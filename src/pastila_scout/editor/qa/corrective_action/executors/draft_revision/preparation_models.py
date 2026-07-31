"""Immutable M6C.6D Part 2 preparation contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.generation.revision import ControlledRevisionRequest
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutorRequestV2,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import (
    DraftRevisionInstructions,
    DraftRevisionRequest,
    DraftRevisionScope,
)
from .policy import DraftRevisionPolicy

PREPARATION_VERSION = "1"
RESOLVED_INPUT_VERSION = "1"
PRESERVATION_VERSION = "1"
PRECONDITION_VERSION = "1"
LIFECYCLE_VERSION = "1"
REPORT_VERSION = "1"


class DraftRevisionPreparationOutcome(StrEnum):
    PREPARED = "prepared"
    REJECTED = "rejected"
    FAILED_INTERNAL = "failed_internal"


class DraftRevisionPreparationStatus(StrEnum):
    PREPARED = "prepared"
    REJECTED = "rejected"
    FAILED = "failed"


class DraftRevisionPreparationPhase(StrEnum):
    RECEIVED = "received"
    VALIDATING_EXECUTOR_REQUEST = "validating_executor_request"
    RESOLVING_INPUT = "resolving_input"
    VALIDATING_SCOPE = "validating_scope"
    BUILDING_PRESERVATION_BASELINE = "building_preservation_baseline"
    BUILDING_REVISION_REQUEST = "building_revision_request"
    EVALUATING_PRECONDITIONS = "evaluating_preconditions"
    PROJECTING_GENERATION_REQUEST = "projecting_generation_request"
    VALIDATING_PROJECTION = "validating_projection"
    PREPARED = "prepared"
    REJECTED = "rejected"
    FAILED = "failed"


class DraftRevisionPreparationDiagnosticCode(StrEnum):
    INVALID_EXECUTOR_REQUEST = "invalid_executor_request"
    DESCRIPTOR_MISMATCH = "descriptor_mismatch"
    CAPABILITY_MISMATCH = "capability_mismatch"
    ACTION_MISMATCH = "action_mismatch"
    REVISION_NOT_AUTHORIZED = "revision_not_authorized"
    SOURCE_DRAFT_UNAVAILABLE = "source_draft_unavailable"
    INVALID_REVISION_POLICY = "invalid_revision_policy"
    INVALID_REVISION_SCOPE = "invalid_revision_scope"
    INVALID_REVISION_TARGET = "invalid_revision_target"
    OVERLAPPING_REVISION_TARGETS = "overlapping_revision_targets"
    INVALID_REVISION_INSTRUCTIONS = "invalid_revision_instructions"
    PROHIBITED_REVISION = "prohibited_revision"
    IMPLICIT_REGENERATION = "implicit_regeneration"
    PRESERVATION_BASELINE_FAILED = "preservation_baseline_failed"
    GENERATION_PROJECTION_UNSUPPORTED = "generation_projection_unsupported"
    PREPARATION_INTERNAL_FAILURE = "preparation_internal_failure"


class DraftRevisionPreconditionCode(StrEnum):
    EXECUTOR_REQUEST_VALID = "executor_request_valid"
    CAPABILITY_VALID = "capability_valid"
    ACTION_VALID = "action_valid"
    AUTHORIZATION_VALID = "authorization_valid"
    SOURCE_DRAFT_VALID = "source_draft_valid"
    POLICY_VALID = "policy_valid"
    SCOPE_VALID = "scope_valid"
    TARGET_COUNT_VALID = "target_count_valid"
    INSTRUCTIONS_VALID = "instructions_valid"
    REQUEST_PERMITTED = "request_permitted"
    NOT_IMPLICIT_REGENERATION = "not_implicit_regeneration"
    PRESERVATION_BASELINE_VALID = "preservation_baseline_valid"
    PROJECTION_SUPPORTED = "projection_supported"


class ResolvedDraftRevisionInput(FrozenModel):
    contract_version: str = RESOLVED_INPUT_VERSION
    executor_request: CorrectiveActionExecutorRequestV2
    source_draft: EpisodeDraft = Field(repr=False)
    policy: DraftRevisionPolicy
    scope: DraftRevisionScope
    instructions: DraftRevisionInstructions = Field(repr=False)
    authorization_state: CorrectiveActionAuthorizationState
    planning_input_fingerprint: str
    resolved_input_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", RESOLVED_INPUT_VERSION)
        values["resolved_input_fingerprint"] = fingerprint(_resolved_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != RESOLVED_INPUT_VERSION:
            raise ValueError("unsupported resolved revision-input version")
        planning = self.executor_request.planning_input
        if (
            self.source_draft is not planning.source_draft
            or self.policy is not planning.revision_policy
            or self.scope is not planning.revision_scope
            or self.instructions is not planning.revision_instructions
        ):
            raise ValueError("resolved revision input does not preserve identity")
        if self.planning_input_fingerprint != planning.input_fingerprint:
            raise ValueError("resolved revision planning lineage mismatch")
        if self.resolved_input_fingerprint != fingerprint(
            _resolved_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("resolved revision-input fingerprint is inconsistent")
        return self


class DraftRevisionPreservationManifest(FrozenModel):
    contract_version: str = PRESERVATION_VERSION
    source_draft_fingerprint: str
    authorized_target_fingerprints: tuple[str, ...] = Field(min_length=1)
    protected_region_fingerprints: tuple[tuple[str, str], ...]
    protected_metadata_fingerprints: tuple[tuple[str, str], ...]
    structural_order_fingerprint: str
    scope_fingerprint: str
    manifest_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", PRESERVATION_VERSION)
        values["authorized_target_fingerprints"] = tuple(
            sorted(values["authorized_target_fingerprints"])
        )
        values["protected_region_fingerprints"] = tuple(
            sorted(values.get("protected_region_fingerprints", ()))
        )
        values["protected_metadata_fingerprints"] = tuple(
            sorted(values.get("protected_metadata_fingerprints", ()))
        )
        values["manifest_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != PRESERVATION_VERSION:
            raise ValueError("unsupported revision-preservation version")
        if len(set(self.authorized_target_fingerprints)) != len(
            self.authorized_target_fingerprints
        ):
            raise ValueError("preservation targets contain duplicates")
        for collection in (
            self.protected_region_fingerprints,
            self.protected_metadata_fingerprints,
        ):
            if len({item[0] for item in collection}) != len(collection):
                raise ValueError(
                    "preservation component identifiers contain duplicates"
                )
        return _validate_own_fingerprint(self, "manifest_fingerprint")


class DraftRevisionPreconditionFinding(FrozenModel):
    contract_version: str = PRECONDITION_VERSION
    code: DraftRevisionPreconditionCode
    passed: bool
    diagnostic_code: DraftRevisionPreparationDiagnosticCode | None = None
    finding_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", PRECONDITION_VERSION)
        values.setdefault("diagnostic_code", None)
        values["finding_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != PRECONDITION_VERSION:
            raise ValueError("unsupported revision-precondition version")
        if self.passed == (self.diagnostic_code is not None):
            raise ValueError("revision-precondition finding shape is inconsistent")
        return _validate_own_fingerprint(self, "finding_fingerprint")


class DraftRevisionPreconditionEvaluation(FrozenModel):
    contract_version: str = PRECONDITION_VERSION
    revision_request_fingerprint: str
    manifest_fingerprint: str
    findings: tuple[DraftRevisionPreconditionFinding, ...] = Field(min_length=1)
    passed: bool
    evaluation_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", PRECONDITION_VERSION)
        values["passed"] = all(item.passed for item in values["findings"])
        values["evaluation_fingerprint"] = fingerprint(_evaluation_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != PRECONDITION_VERSION:
            raise ValueError("unsupported revision-precondition evaluation version")
        expected_order = tuple(DraftRevisionPreconditionCode)
        if tuple(item.code for item in self.findings) != expected_order:
            raise ValueError("revision preconditions are not canonically ordered")
        if self.passed != all(item.passed for item in self.findings):
            raise ValueError("revision-precondition aggregate is inconsistent")
        if self.evaluation_fingerprint != fingerprint(
            _evaluation_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("revision-precondition fingerprint is inconsistent")
        return self


class DraftRevisionPreparationDiagnostic(FrozenModel):
    code: DraftRevisionPreparationDiagnosticCode
    safe_message: str = Field(min_length=1, max_length=200)
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        lowered = self.safe_message.casefold()
        if any(
            token in lowered
            for token in ("traceback", "api_key", "bearer ", "c:\\", "/home/")
        ):
            raise ValueError("revision-preparation diagnostic contains unsafe detail")
        return _validate_own_fingerprint(self, "diagnostic_fingerprint")


class DraftRevisionPreparationLifecycle(FrozenModel):
    lifecycle_version: str = LIFECYCLE_VERSION
    phases: tuple[DraftRevisionPreparationPhase, ...] = Field(min_length=2)
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
            raise ValueError("revision-preparation lifecycle is invalid")
        return _validate_own_fingerprint(self, "lifecycle_fingerprint")


class DraftRevisionPreparationResult(FrozenModel):
    contract_version: str = PREPARATION_VERSION
    executor_request: CorrectiveActionExecutorRequestV2 | None = None
    resolved_input: ResolvedDraftRevisionInput | None = Field(default=None, repr=False)
    revision_request: DraftRevisionRequest | None = Field(default=None, repr=False)
    preservation_manifest: DraftRevisionPreservationManifest | None = None
    precondition_evaluation: DraftRevisionPreconditionEvaluation | None = None
    generation_request: ControlledRevisionRequest | None = Field(
        default=None, repr=False
    )
    outcome: DraftRevisionPreparationOutcome
    status: DraftRevisionPreparationStatus
    diagnostic: DraftRevisionPreparationDiagnostic | None = None
    lifecycle: DraftRevisionPreparationLifecycle
    input_request_fingerprint: str | None
    preparation_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", PREPARATION_VERSION)
        for name in (
            "executor_request",
            "resolved_input",
            "revision_request",
            "preservation_manifest",
            "precondition_evaluation",
            "generation_request",
            "diagnostic",
            "input_request_fingerprint",
        ):
            values.setdefault(name, None)
        values["preparation_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != PREPARATION_VERSION:
            raise ValueError("unsupported draft-revision preparation version")
        prepared = self.outcome is DraftRevisionPreparationOutcome.PREPARED
        expected_status = {
            DraftRevisionPreparationOutcome.PREPARED: DraftRevisionPreparationStatus.PREPARED,
            DraftRevisionPreparationOutcome.REJECTED: DraftRevisionPreparationStatus.REJECTED,
            DraftRevisionPreparationOutcome.FAILED_INTERNAL: DraftRevisionPreparationStatus.FAILED,
        }[self.outcome]
        if self.status is not expected_status:
            raise ValueError("revision-preparation outcome and status differ")
        artifacts = (
            self.executor_request,
            self.resolved_input,
            self.revision_request,
            self.preservation_manifest,
            self.precondition_evaluation,
            self.generation_request,
        )
        if prepared:
            if any(item is None for item in artifacts) or self.diagnostic is not None:
                raise ValueError("prepared revision result is incomplete")
            if not self.precondition_evaluation.passed:
                raise ValueError("prepared revision result has failed preconditions")
            if self.lifecycle.phases[-1] is not DraftRevisionPreparationPhase.PREPARED:
                raise ValueError("prepared revision lifecycle is not terminal")
            if (
                self.resolved_input.executor_request is not self.executor_request
                or self.revision_request.executor_request
                is not self.executor_request.legacy_request
                or self.revision_request.source_draft
                is not self.resolved_input.source_draft
                or self.generation_request.source_draft
                is not self.resolved_input.source_draft
            ):
                raise ValueError("revision-preparation nested identity is inconsistent")
        elif any(item is not None for item in artifacts) or self.diagnostic is None:
            raise ValueError("failed revision preparation exposes partial artifacts")
        if self.preparation_fingerprint != fingerprint(
            _result_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("revision-preparation fingerprint is inconsistent")
        return self


class DraftRevisionPreparationReport(FrozenModel):
    report_version: str = REPORT_VERSION
    executor_id: str | None
    capability: str
    action: str
    target_count: int
    source_draft_fingerprint: str | None
    policy_fingerprint: str | None
    scope_fingerprint: str | None
    preservation_manifest_fingerprint: str | None
    generation_request_fingerprint: str | None
    outcome: DraftRevisionPreparationOutcome
    status: DraftRevisionPreparationStatus
    diagnostic_code: DraftRevisionPreparationDiagnosticCode | None
    lifecycle: tuple[str, ...]
    preparation_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)


def _resolved_identity(values):
    return {
        "contract_version": values["contract_version"],
        "executor_request_fingerprint": _field(
            values["executor_request"], "request_fingerprint"
        ),
        "source_draft_fingerprint": fingerprint(values["source_draft"]),
        "policy_fingerprint": _field(values["policy"], "policy_fingerprint"),
        "scope_fingerprint": _field(values["scope"], "scope_fingerprint"),
        "instructions_fingerprint": _field(
            values["instructions"], "instructions_fingerprint"
        ),
        "authorization_state": values["authorization_state"],
        "planning_input_fingerprint": values["planning_input_fingerprint"],
    }


def _evaluation_identity(values):
    return {
        "contract_version": values["contract_version"],
        "revision_request_fingerprint": values["revision_request_fingerprint"],
        "manifest_fingerprint": values["manifest_fingerprint"],
        "finding_fingerprints": tuple(
            _field(item, "finding_fingerprint") for item in values["findings"]
        ),
        "passed": values["passed"],
    }


def _result_identity(values):
    names = {
        "executor_request": "request_fingerprint",
        "resolved_input": "resolved_input_fingerprint",
        "revision_request": "request_fingerprint",
        "preservation_manifest": "manifest_fingerprint",
        "precondition_evaluation": "evaluation_fingerprint",
        "generation_request": "revision_request_fingerprint",
        "diagnostic": "diagnostic_fingerprint",
        "lifecycle": "lifecycle_fingerprint",
    }
    result = {
        "contract_version": values["contract_version"],
        "outcome": values["outcome"],
        "status": values["status"],
        "input_request_fingerprint": values.get("input_request_fingerprint"),
    }
    result.update(
        {
            f"{name}_fingerprint": (
                _field(values[name], field_name)
                if values.get(name) is not None
                else None
            )
            for name, field_name in names.items()
        }
    )
    return result


def _valid_lifecycle(phases):
    normal = tuple(DraftRevisionPreparationPhase)[:10]
    if phases[-1] is DraftRevisionPreparationPhase.PREPARED:
        return phases == normal
    terminal = phases[-1]
    if terminal not in (
        DraftRevisionPreparationPhase.REJECTED,
        DraftRevisionPreparationPhase.FAILED,
    ):
        return False
    prefix = phases[:-1]
    return bool(prefix) and prefix == normal[: len(prefix)]


def _validate_own_fingerprint(model, name):
    expected = fingerprint(model.model_dump(exclude={name}, mode="python"))
    if getattr(model, name) != expected:
        raise ValueError(f"{name} is inconsistent")
    return model


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
