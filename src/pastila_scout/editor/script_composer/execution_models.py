"""Immutable provider-neutral execution contracts for Module 2.9 Phase 3."""

from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from .defaults import (
    CUSTOM_PATTERN,
    FINGERPRINT_PATTERN,
    IDENTITY_PATTERN,
    SEMVER_PATTERN,
)
from .errors import DomainValidationIssue
from .execution_defaults import *
from .execution_invariants import (
    capability_requirement_violations,
    capability_set_violations,
    execution_plan_violations,
    failure_policy_violations,
    observation_violations,
    outcome_violations,
    retry_policy_violations,
)
from .models import FrozenDomainModel


def _raise_first(violations) -> None:
    if violations:
        item = violations[0]
        raise PydanticCustomError(item.code, item.code)


class ExecutionDomainModel(FrozenDomainModel):
    """Phase 3 base with canonical reference collections and shared checks."""

    @field_validator("*", mode="before")
    @classmethod
    def canonicalize_references(cls, value, info):
        if info.field_name.endswith("_references") and isinstance(value, (list, tuple)):
            return tuple(sorted(value, key=lambda item: getattr(item, "value", item)))
        return value

    @model_validator(mode="after")
    def validate_duplicate_references(self) -> Self:
        from .execution_invariants import duplicate_reference_violations

        _raise_first(duplicate_reference_violations(self))
        return self


class GenerationCapabilityRequirement(ExecutionDomainModel):
    capability: GenerationCapability
    custom_identifier: str | None = Field(default=None, pattern=CUSTOM_PATTERN)
    required: bool = True

    @model_validator(mode="after")
    def validate_custom_capability(self) -> Self:
        _raise_first(capability_requirement_violations(self))
        return self


class GenerationCapabilitySet(ExecutionDomainModel):
    capability_set_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-capability-set-v1"
    capability_set_version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    requirements: tuple[GenerationCapabilityRequirement, ...] = ()
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @field_validator("requirements", mode="before")
    @classmethod
    def canonicalize_requirements(cls, value):
        def key(item):
            if isinstance(item, dict):
                capability = getattr(
                    item.get("capability"), "value", item.get("capability", "")
                )
                return (
                    capability,
                    item.get("custom_identifier") or "",
                    item.get("required", True),
                )
            return (
                getattr(item.capability, "value", item.capability),
                item.custom_identifier or "",
                item.required,
            )

        return tuple(sorted(value, key=key))

    @model_validator(mode="after")
    def validate_capabilities(self) -> Self:
        _raise_first(capability_set_violations(self))
        return self


class GenerationOutputBinding(ExecutionDomainModel):
    output_binding_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-output-binding-v1"
    binding_type: GenerationOutputBindingType
    target_reference: str = Field(min_length=1)
    expected_artifact_type: str = Field(min_length=1)
    required: bool
    unit_reference: str = Field(min_length=1)
    scope_reference: str = Field(min_length=1)
    cardinality: OutputCardinality
    ordering_required: bool = False
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationDependencyDeclaration(ExecutionDomainModel):
    source_unit_reference: str = Field(min_length=1)
    dependency_unit_reference: str = Field(min_length=1)


class GenerationRetryPolicy(ExecutionDomainModel):
    retry_policy_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-retry-policy-v1"
    policy_version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    maximum_attempts: int = Field(ge=1)
    retryable_failure_types: tuple[GenerationExecutionFailureType, ...] = ()
    non_retryable_failure_types: tuple[GenerationExecutionFailureType, ...] = ()
    retry_scope: RetryScope
    replacement_execution_allowed: bool
    required_preservation_references: tuple[str, ...] = ()
    backoff_classification: RetryBackoffClassification
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_retry_classifications(self) -> Self:
        _raise_first(retry_policy_violations(self))
        return self


class GenerationFailurePolicy(ExecutionDomainModel):
    failure_policy_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-failure-policy-v1"
    policy_version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    allowed_partial_completion: bool
    required_output_binding_references: tuple[str, ...] = ()
    optional_output_binding_references: tuple[str, ...] = ()
    propagation_mode: FailurePropagationMode
    block_dependent_units: bool
    allow_supersession: bool
    allow_cancellation: bool
    retry_policy_reference: str = Field(min_length=1)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_binding_classification(self) -> Self:
        _raise_first(failure_policy_violations(self))
        return self


class GenerationExecutionIntent(ExecutionDomainModel):
    execution_intent_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-intent-v1"
    normalized_generation_input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    generation_profile_reference: str = Field(min_length=1)
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    policy_snapshot_reference: str = Field(min_length=1)
    policy_snapshot_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    requested_operation: GenerationOperation
    requested_output_scope: GenerationOutputScope
    requested_target_references: tuple[str, ...] = Field(min_length=1)
    instruction_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    revision_request_reference: str | None = None
    parent_execution_reference: str | None = None
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationExecutionUnit(ExecutionDomainModel):
    execution_unit_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-unit-v1"
    execution_plan_reference: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    operation_type: GenerationOperation
    target_references: tuple[str, ...] = Field(min_length=1)
    source_input_references: tuple[str, ...] = Field(min_length=1)
    generation_profile_reference: str = Field(min_length=1)
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    policy_snapshot_reference: str = Field(min_length=1)
    policy_snapshot_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    instruction_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    dependency_unit_references: tuple[str, ...] = ()
    expected_output_binding_reference: str | None = Field(default=None, min_length=1)
    revision_scope_reference: str | None = None
    regeneration_scope_reference: str | None = None
    capability_set_reference: str = Field(min_length=1)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationExecutionPlan(ExecutionDomainModel):
    execution_plan_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-plan-v1"
    execution_intent_reference: str = Field(min_length=1)
    execution_intent_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    ordered_execution_units: tuple[GenerationExecutionUnit, ...] = Field(min_length=1)
    dependency_declarations: tuple[GenerationDependencyDeclaration, ...] = ()
    policy_references: tuple[str, ...] = Field(min_length=1)
    authority_references: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    expected_output_bindings: tuple[GenerationOutputBinding, ...] = Field(min_length=1)
    capability_sets: tuple[GenerationCapabilitySet, ...] = Field(min_length=1)
    retry_policy_reference: str = Field(min_length=1)
    retry_policy: GenerationRetryPolicy
    failure_policy_reference: str = Field(min_length=1)
    failure_policy: GenerationFailurePolicy
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @field_validator("ordered_execution_units", mode="before")
    @classmethod
    def canonicalize_units(cls, value):
        return tuple(
            sorted(
                value,
                key=lambda item: (
                    item.get("ordinal", -1) if isinstance(item, dict) else item.ordinal
                ),
            )
        )

    @field_validator("expected_output_bindings", mode="before")
    @classmethod
    def canonicalize_bindings(cls, value):
        return tuple(
            sorted(
                value,
                key=lambda item: (
                    item.get("output_binding_id", "")
                    if isinstance(item, dict)
                    else item.output_binding_id
                ),
            )
        )

    @field_validator("dependency_declarations", mode="before")
    @classmethod
    def canonicalize_dependency_declarations(cls, value):
        return tuple(
            sorted(
                value,
                key=lambda item: (
                    (
                        item.get("source_unit_reference", "")
                        if isinstance(item, dict)
                        else item.source_unit_reference
                    ),
                    (
                        item.get("dependency_unit_reference", "")
                        if isinstance(item, dict)
                        else item.dependency_unit_reference
                    ),
                ),
            )
        )

    @field_validator("capability_sets", mode="before")
    @classmethod
    def canonicalize_capability_sets(cls, value):
        return tuple(
            sorted(
                value,
                key=lambda item: (
                    item.get("capability_set_id", "")
                    if isinstance(item, dict)
                    else item.capability_set_id
                ),
            )
        )

    @model_validator(mode="after")
    def validate_plan_structure(self) -> Self:
        _raise_first(execution_plan_violations(self))
        return self


class GenerationExecutionRequest(ExecutionDomainModel):
    execution_request_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-request-v1"
    execution_plan_reference: str = Field(min_length=1)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_unit_reference: str = Field(min_length=1)
    execution_unit_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_intent_reference: str = Field(min_length=1)
    generation_profile_reference: str = Field(min_length=1)
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    policy_snapshot_reference: str = Field(min_length=1)
    policy_snapshot_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    target_references: tuple[str, ...] = Field(min_length=1)
    instruction_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    capability_set: GenerationCapabilitySet
    expected_output_binding_reference: str = Field(min_length=1)
    retry_policy_reference: str = Field(min_length=1)
    failure_policy_reference: str = Field(min_length=1)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationUsageSummary(ExecutionDomainModel):
    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    reasoning_units: int | None = Field(default=None, ge=0)


class GenerationExecutionOutcome(ExecutionDomainModel):
    execution_outcome_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-outcome-v1"
    execution_request_reference: str = Field(min_length=1)
    execution_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    status: GenerationOutcomeStatus
    produced_output_artifact_references: tuple[str, ...] = ()
    satisfied_output_binding_references: tuple[str, ...] = ()
    missing_output_binding_references: tuple[str, ...] = ()
    failure_type: GenerationExecutionFailureType | None = None
    failure_code: str | None = Field(default=None, min_length=1)
    affected_target_references: tuple[str, ...] = ()
    retry_eligible: bool = False
    warning_codes: tuple[str, ...] = ()
    diagnostic_issues: tuple[DomainValidationIssue, ...] = ()
    applied_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    applied_policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    usage_summary: GenerationUsageSummary | None = None
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> Self:
        _raise_first(outcome_violations(self))
        return self


class GenerationExecutionStateObservation(ExecutionDomainModel):
    state_observation_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "generation-execution-state-observation-v1"
    execution_request_reference: str = Field(min_length=1)
    observed_state: GenerationExecutionState
    sequence_number: int = Field(ge=0)
    previous_observation_fingerprint: str | None = Field(
        default=None, pattern=FINGERPRINT_PATTERN
    )
    outcome_reference: str | None = None
    failure_reference: str | None = None
    superseding_execution_reference: str | None = None
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_observation_shape(self) -> Self:
        _raise_first(observation_violations(self))
        return self


class GenerationExecutionEligibility(ExecutionDomainModel):
    contract_version: str = "generation-execution-eligibility-v1"
    execution_plan_reference: str = Field(min_length=1)
    eligible: bool
    blocking_issues: tuple[DomainValidationIssue, ...] = ()
    required_capabilities: tuple[GenerationCapabilityRequirement, ...] = ()
    unresolved_authority_conflict_references: tuple[str, ...] = ()
    unresolved_input_issue_codes: tuple[str, ...] = ()
    structurally_eligible_unit_references: tuple[str, ...] = ()
    blocked_unit_references: tuple[str, ...] = ()
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


__all__ = tuple(name for name in globals() if name.startswith("Generation"))
