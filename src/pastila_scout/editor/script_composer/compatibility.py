"""Pure Phase 2 input compatibility, authority, and normalization layer."""

import json
from collections.abc import Callable, Iterable
from enum import StrEnum

from pydantic import Field

from .canonical import canonical_json, semantic_fingerprint
from .defaults import CUSTOM_PATTERN, SEMVER_PATTERN
from .errors import DomainValidationError, DomainValidationIssue
from .models import (
    AuthorityLevel,
    AuthorityReference,
    FrozenDomainModel,
    GenerationConstraint,
    GenerationDecision,
    GenerationProfile,
    ProviderGenerationRequest,
    ResolvedGenerationPolicySnapshot,
    RevisionAuthorityInputSnapshot,
    RevisionRequest,
    ScriptCompositionInputBundle,
)
from .validation import validate_artifact


class AuthorityConflictType(StrEnum):
    DUPLICATE_AUTHORITY = "duplicate_authority"
    CONFLICTING_AUTHORITY = "conflicting_authority"
    CONFLICTING_POLICY = "conflicting_policy"
    CONFLICTING_INSTRUCTION = "conflicting_instruction"
    CONFLICTING_CONSTRAINT = "conflicting_constraint"
    CONFLICTING_DECISION = "conflicting_decision"
    DUPLICATE_EVIDENCE = "duplicate_evidence"


class CustomInstructionDefinition(FrozenDomainModel):
    custom_identifier: str = Field(pattern=CUSTOM_PATTERN)
    instruction_reference: str = Field(min_length=1)
    authority_level: AuthorityLevel
    authority_references: tuple[str, ...] = Field(min_length=1)


class CustomConstraintDefinition(FrozenDomainModel):
    custom_identifier: str = Field(pattern=CUSTOM_PATTERN)
    constraint_reference: str = Field(min_length=1)
    authority_references: tuple[str, ...] = Field(min_length=1)


class GenerationInputBundle(FrozenDomainModel):
    """Immutable envelope containing artifacts considered for compatibility."""

    generation_input_bundle_id: str = Field(min_length=1)
    contract_version: str = "generation-input-compatibility-v1"
    bundle_version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    composition_input_bundles: tuple[ScriptCompositionInputBundle, ...] = ()
    generation_profiles: tuple[GenerationProfile, ...] = ()
    policy_snapshots: tuple[ResolvedGenerationPolicySnapshot, ...] = ()
    authority_artifacts: tuple[AuthorityReference, ...] = ()
    revision_authority_snapshots: tuple[RevisionAuthorityInputSnapshot, ...] = ()
    provider_requests: tuple[ProviderGenerationRequest, ...] = ()
    revision_requests: tuple[RevisionRequest, ...] = ()
    generation_decisions: tuple[GenerationDecision, ...] = ()
    custom_instruction_definitions: tuple[CustomInstructionDefinition, ...] = ()
    custom_constraint_definitions: tuple[CustomConstraintDefinition, ...] = ()


class AuthorityConflict(FrozenDomainModel):
    authority_conflict_id: str = Field(min_length=1)
    conflict_type: AuthorityConflictType
    artifact_references: tuple[str, ...] = Field(min_length=1)
    target_references: tuple[str, ...] = ()
    field_path: tuple[str | int, ...] = ()
    authority_references: tuple[str, ...] = ()
    issue_code: str = Field(min_length=1)


class AuthorityConflictSet(FrozenDomainModel):
    contract_version: str = "authority-conflict-set-v1"
    conflicts: tuple[AuthorityConflict, ...] = ()


class CompatibilityResult(FrozenDomainModel):
    contract_version: str = "generation-input-compatibility-result-v1"
    generation_input_bundle_reference: str = Field(min_length=1)
    compatible: bool
    issues: tuple[DomainValidationIssue, ...] = ()
    authority_conflicts: AuthorityConflictSet


class InputNormalizationResult(FrozenDomainModel):
    contract_version: str = "generation-input-normalization-result-v1"
    source_bundle_reference: str = Field(min_length=1)
    normalized_bundle: GenerationInputBundle
    changed: bool
    normalized_fingerprint: str = Field(min_length=64, max_length=64)


def validate_generation_input_bundle(
    bundle: GenerationInputBundle,
) -> CompatibilityResult:
    """Return deterministic compatibility and authority findings without mutation."""
    issues: list[DomainValidationIssue] = []
    conflicts: list[AuthorityConflict] = []
    reference = bundle.generation_input_bundle_id
    issues.extend(_phase1_integrity_issues(bundle))
    for field_name in (
        "generation_profiles",
        "policy_snapshots",
        "authority_artifacts",
    ):
        if not getattr(bundle, field_name):
            issues.append(_issue("required-artifact-missing", reference, field_name))

    _check_identity_collection(
        bundle.authority_artifacts,
        "authority_reference_id",
        "semantic_fingerprint",
        "duplicate-authority",
        "conflicting-authority",
        issues,
        conflicts,
        AuthorityConflictType.DUPLICATE_AUTHORITY,
        AuthorityConflictType.CONFLICTING_AUTHORITY,
    )
    _check_identity_collection(
        bundle.generation_profiles,
        "generation_profile_id",
        "profile_fingerprint",
        "duplicate-generation-profile",
        "conflicting-generation-profile",
        issues,
    )
    _check_identity_collection(
        bundle.provider_requests,
        "provider_generation_request_id",
        "request_fingerprint",
        "duplicate-provider-request",
        "conflicting-provider-request",
        issues,
    )
    _check_identity_collection(
        bundle.policy_snapshots,
        "resolved_generation_policy_id",
        "policy_fingerprint",
        "duplicate-policy-snapshot",
        "conflicting-policy-snapshot",
        issues,
        conflicts,
        None,
        AuthorityConflictType.CONFLICTING_POLICY,
    )
    _check_policy_sources(bundle, issues, conflicts)
    _check_authority_compatibility(bundle, issues)
    _check_profile_compatibility(bundle, issues)
    _check_revision_compatibility(bundle, issues)
    _check_custom_definitions(bundle, issues)
    _check_policy_members(bundle, issues, conflicts)
    _check_decisions(bundle, issues, conflicts)
    _check_duplicate_evidence(bundle, issues, conflicts)
    ordered_issues = tuple(sorted(issues, key=_issue_key))
    unique_conflicts = {item.authority_conflict_id: item for item in conflicts}
    ordered_conflicts = tuple(
        sorted(
            unique_conflicts.values(),
            key=lambda item: (
                item.conflict_type.value,
                item.target_references,
                tuple(map(str, item.field_path)),
                item.authority_conflict_id,
            ),
        )
    )
    return CompatibilityResult(
        generation_input_bundle_reference=reference,
        compatible=not ordered_issues,
        issues=ordered_issues,
        authority_conflicts=AuthorityConflictSet(conflicts=ordered_conflicts),
    )


def require_compatible_generation_input(bundle: GenerationInputBundle) -> None:
    """Raise the stable domain error when a compatibility result is invalid."""
    result = validate_generation_input_bundle(bundle)
    if result.issues:
        raise DomainValidationError(result.issues)


def construct_compatible_generation_input(payload: dict) -> GenerationInputBundle:
    """Construct and semantically validate an untrusted compatibility envelope."""
    from .validation import construct_artifact

    bundle = construct_artifact(GenerationInputBundle, payload)
    require_compatible_generation_input(bundle)
    return bundle


def normalize_generation_input_bundle(
    bundle: GenerationInputBundle,
) -> InputNormalizationResult:
    """Deduplicate exact artifacts and deterministically order all collections."""
    if integrity_issues := _phase1_integrity_issues(bundle):
        raise DomainValidationError(integrity_issues)
    updates = {
        "composition_input_bundles": _normalize(
            bundle.composition_input_bundles,
            lambda item: (item.input_bundle_id, item.input_fingerprint),
        ),
        "generation_profiles": _normalize(
            bundle.generation_profiles,
            lambda item: (item.generation_profile_id, item.profile_fingerprint),
        ),
        "policy_snapshots": _normalize(
            bundle.policy_snapshots,
            lambda item: (item.resolved_generation_policy_id, item.policy_fingerprint),
        ),
        "authority_artifacts": _normalize(
            bundle.authority_artifacts,
            lambda item: (item.authority_reference_id, item.semantic_fingerprint),
        ),
        "revision_authority_snapshots": _normalize(
            bundle.revision_authority_snapshots, lambda item: (canonical_json(item),)
        ),
        "provider_requests": _normalize(
            bundle.provider_requests,
            lambda item: (
                item.provider_generation_request_id,
                item.request_fingerprint,
            ),
        ),
        "revision_requests": _normalize(
            bundle.revision_requests,
            lambda item: (item.revision_request_id, item.request_fingerprint),
        ),
        "generation_decisions": _normalize(
            bundle.generation_decisions,
            lambda item: (item.generation_decision_id, item.decision_fingerprint),
        ),
        "custom_instruction_definitions": _normalize(
            bundle.custom_instruction_definitions,
            lambda item: (item.custom_identifier, canonical_json(item)),
        ),
        "custom_constraint_definitions": _normalize(
            bundle.custom_constraint_definitions,
            lambda item: (item.custom_identifier, canonical_json(item)),
        ),
    }
    normalized = bundle.model_copy(update=updates)
    return InputNormalizationResult(
        source_bundle_reference=bundle.generation_input_bundle_id,
        normalized_bundle=normalized,
        changed=normalized != bundle,
        normalized_fingerprint=semantic_fingerprint(normalized),
    )


def _check_authority_compatibility(bundle, issues) -> None:
    available = {item.authority_reference_id for item in bundle.authority_artifacts}
    levels = {item.authority_type for item in bundle.authority_artifacts}
    artifacts = (*bundle.generation_profiles, *bundle.policy_snapshots)
    for artifact in artifacts:
        for authority in artifact.authority_references:
            if authority not in available:
                issues.append(
                    _issue(
                        "missing-authority",
                        _reference(artifact),
                        "authority_references",
                        (authority,),
                    )
                )
    for policy in bundle.policy_snapshots:
        for instruction in policy.resolved_generation_instructions:
            if instruction.authority_level.value not in levels:
                issues.append(
                    _issue(
                        "incompatible-authority-level",
                        instruction.generation_instruction_id,
                        "authority_level",
                    )
                )


def _check_profile_compatibility(bundle, issues) -> None:
    authorities = {item.authority_reference_id for item in bundle.authority_artifacts}
    for profile in bundle.generation_profiles:
        definitions = [item.custom_value for item in profile.custom_value_definitions]
        for identifier in sorted(set(definitions)):
            if definitions.count(identifier) > 1:
                issues.append(
                    _issue(
                        "profile-custom-identifier-duplicate",
                        profile.generation_profile_id,
                        "custom_value_definitions",
                        (identifier,),
                    )
                )
        used = {
            value
            for value in profile.__dict__.values()
            if isinstance(value, str) and value.startswith("custom:")
        }
        if used != set(definitions):
            issues.append(
                _issue(
                    "profile-custom-vocabulary-mismatch",
                    profile.generation_profile_id,
                    "custom_value_definitions",
                )
            )
        for definition in profile.custom_value_definitions:
            for authority in definition.authority_references:
                if authority not in authorities:
                    issues.append(
                        _issue(
                            "profile-custom-authority-missing",
                            profile.generation_profile_id,
                            "custom_value_definitions",
                            (authority,),
                        )
                    )
    profiles = {
        (item.generation_profile_id, item.profile_fingerprint)
        for item in bundle.generation_profiles
    }
    policies = {
        (item.resolved_generation_policy_id, item.policy_fingerprint)
        for item in bundle.policy_snapshots
    }
    for item in bundle.composition_input_bundles:
        if (
            item.generation_profile.generation_profile_id,
            item.generation_profile_fingerprint,
        ) not in profiles:
            issues.append(
                _issue(
                    "composition-profile-incompatible",
                    item.input_bundle_id,
                    "generation_profile_fingerprint",
                )
            )
        if (
            item.resolved_generation_policy.resolved_generation_policy_id,
            item.resolved_generation_policy_fingerprint,
        ) not in policies:
            issues.append(
                _issue(
                    "composition-policy-incompatible",
                    item.input_bundle_id,
                    "resolved_generation_policy_fingerprint",
                )
            )
    profiles_by_reference = {
        item.generation_profile_id: item for item in bundle.generation_profiles
    }
    for request in bundle.provider_requests:
        profile = profiles_by_reference.get(request.generation_profile_reference)
        if profile is None:
            issues.append(
                _issue(
                    "provider-profile-reference-unknown",
                    request.provider_generation_request_id,
                    "generation_profile_reference",
                )
            )
        elif profile.profile_fingerprint != request.generation_profile_fingerprint:
            issues.append(
                _issue(
                    "provider-profile-fingerprint-mismatch",
                    request.provider_generation_request_id,
                    "generation_profile_fingerprint",
                    (profile.generation_profile_id,),
                )
            )


def _check_revision_compatibility(bundle, issues) -> None:
    profiles = {item.profile_fingerprint for item in bundle.generation_profiles}
    policies = {item.policy_fingerprint for item in bundle.policy_snapshots}
    for snapshot in bundle.revision_authority_snapshots:
        if snapshot.generation_profile_fingerprint not in profiles:
            issues.append(
                _issue(
                    "revision-profile-incompatible",
                    bundle.generation_input_bundle_id,
                    "revision_authority_snapshots",
                )
            )
        if snapshot.resolved_policy_fingerprint not in policies:
            issues.append(
                _issue(
                    "revision-policy-incompatible",
                    bundle.generation_input_bundle_id,
                    "revision_authority_snapshots",
                )
            )
    for request in bundle.revision_requests:
        if (
            request.requested_authority_inputs
            not in bundle.revision_authority_snapshots
        ):
            issues.append(
                _issue(
                    "revision-snapshot-unknown",
                    request.revision_request_id,
                    "requested_authority_inputs",
                )
            )


def _check_custom_definitions(bundle, issues) -> None:
    instruction_ids = _definition_ids(
        bundle.custom_instruction_definitions,
        "custom-instruction-identifier-duplicate",
        issues,
        bundle.generation_input_bundle_id,
    )
    constraint_ids = _definition_ids(
        bundle.custom_constraint_definitions,
        "custom-constraint-identifier-duplicate",
        issues,
        bundle.generation_input_bundle_id,
    )
    available_authorities = {
        item.authority_reference_id for item in bundle.authority_artifacts
    }
    for field_name, definitions in (
        ("custom_instruction_definitions", bundle.custom_instruction_definitions),
        ("custom_constraint_definitions", bundle.custom_constraint_definitions),
    ):
        for definition in definitions:
            for authority in definition.authority_references:
                if authority not in available_authorities:
                    issues.append(
                        _issue(
                            "custom-definition-authority-missing",
                            definition.custom_identifier,
                            field_name,
                            (authority,),
                        )
                    )
    for policy in bundle.policy_snapshots:
        for instruction in policy.resolved_generation_instructions:
            if (
                instruction.instruction_reference.startswith("custom:")
                and instruction.instruction_reference not in instruction_ids
            ):
                issues.append(
                    _issue(
                        "custom-instruction-definition-missing",
                        instruction.generation_instruction_id,
                        "instruction_reference",
                    )
                )
        for constraint in policy.resolved_generation_constraints:
            if (
                constraint.constraint_reference.startswith("custom:")
                and constraint.constraint_reference not in constraint_ids
            ):
                issues.append(
                    _issue(
                        "custom-constraint-definition-missing",
                        constraint.generation_constraint_id,
                        "constraint_reference",
                    )
                )


def _check_policy_members(bundle, issues, conflicts) -> None:
    instructions = [
        item
        for policy in bundle.policy_snapshots
        for item in policy.resolved_generation_instructions
    ]
    constraints = [
        item
        for policy in bundle.policy_snapshots
        for item in policy.resolved_generation_constraints
    ]
    _check_identity_collection(
        instructions,
        "generation_instruction_id",
        "instruction_fingerprint",
        "duplicate-generation-instruction",
        "conflicting-generation-instruction",
        issues,
        conflicts,
        None,
        AuthorityConflictType.CONFLICTING_INSTRUCTION,
    )
    _check_identity_collection(
        constraints,
        "generation_constraint_id",
        "constraint_fingerprint",
        "duplicate-generation-constraint",
        "conflicting-generation-constraint",
        issues,
        conflicts,
        None,
        AuthorityConflictType.CONFLICTING_CONSTRAINT,
    )
    by_target: dict[tuple[str, str], list[GenerationConstraint]] = {}
    for item in constraints:
        for target in item.target_references:
            by_target.setdefault((target, item.constraint_type.value), []).append(item)
    for (target, _constraint_type), values in by_target.items():
        if _constraints_structurally_contradict(values):
            _add_conflict(
                "contradictory-generation-constraints",
                values,
                conflicts,
                AuthorityConflictType.CONFLICTING_CONSTRAINT,
                target_references=(target,),
                field_path=(
                    "resolved_generation_constraints",
                    "prohibited_outcomes",
                ),
            )
            issues.append(
                _issue(
                    "contradictory-generation-constraints",
                    _reference(values[0]),
                    "target_references",
                )
            )


def _check_decisions(bundle, issues, conflicts) -> None:
    by_target: dict[tuple[tuple[str, ...], str], list[GenerationDecision]] = {}
    for item in bundle.generation_decisions:
        by_target.setdefault(
            (item.target_references, item.decision_type.value), []
        ).append(item)
    for values in by_target.values():
        if len({item.selected_option_reference for item in values}) > 1:
            _add_conflict(
                "conflicting-generation-decisions",
                values,
                conflicts,
                AuthorityConflictType.CONFLICTING_DECISION,
                target_references=values[0].target_references,
                field_path=("generation_decisions", "selected_option_reference"),
            )
            issues.append(
                _issue(
                    "conflicting-generation-decisions",
                    _reference(values[0]),
                    "selected_option_reference",
                )
            )


def _check_policy_sources(bundle, issues, conflicts) -> None:
    by_source: dict[str, list[ResolvedGenerationPolicySnapshot]] = {}
    for item in bundle.policy_snapshots:
        by_source.setdefault(item.source_policy_reference, []).append(item)
    for values in by_source.values():
        if len({item.policy_fingerprint for item in values}) > 1:
            _add_conflict(
                "conflicting-policy-snapshots",
                values,
                conflicts,
                AuthorityConflictType.CONFLICTING_POLICY,
                target_references=(values[0].source_policy_reference,),
                field_path=("policy_snapshots", "source_policy_reference"),
            )
            issues.append(
                _issue(
                    "conflicting-policy-snapshots",
                    _reference(values[0]),
                    "source_policy_reference",
                )
            )


def _check_duplicate_evidence(bundle, issues, conflicts) -> None:
    by_source: dict[tuple[str, str], list[AuthorityReference]] = {}
    for item in bundle.authority_artifacts:
        by_source.setdefault((item.authority_type, item.source_reference), []).append(
            item
        )
    for values in by_source.values():
        if len(values) > 1:
            _add_conflict(
                "duplicate-authoritative-evidence",
                values,
                conflicts,
                AuthorityConflictType.DUPLICATE_EVIDENCE,
                target_references=(values[0].source_reference,),
                field_path=("authority_artifacts", "source_reference"),
            )
            issues.append(
                _issue(
                    "duplicate-authoritative-evidence",
                    _reference(values[0]),
                    "source_reference",
                )
            )


def _check_identity_collection(
    items,
    id_field,
    fingerprint_field,
    duplicate_code,
    conflict_code,
    issues,
    conflicts=None,
    duplicate_type=None,
    conflict_type=None,
) -> None:
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(getattr(item, id_field), []).append(item)
    for identity, values in groups.items():
        if len(values) < 2:
            continue
        fingerprints = {getattr(item, fingerprint_field) for item in values}
        code = duplicate_code if len(fingerprints) == 1 else conflict_code
        issues.append(_issue(code, identity, id_field))
        conflict_kind = duplicate_type if len(fingerprints) == 1 else conflict_type
        if conflicts is not None and conflict_kind is not None:
            _add_conflict(
                code,
                values,
                conflicts,
                conflict_kind,
                target_references=(identity,),
                field_path=(id_field,),
            )


def _definition_ids(items, code, issues, reference):
    identifiers = [item.custom_identifier for item in items]
    for identifier in sorted(set(identifiers)):
        if identifiers.count(identifier) > 1:
            issues.append(_issue(code, reference, "custom_identifier", (identifier,)))
    return set(identifiers)


def _phase1_integrity_issues(
    bundle: GenerationInputBundle,
) -> tuple[DomainValidationIssue, ...]:
    """Recursively validate every embedded Phase 1 artifact exactly once."""
    findings: dict[tuple, DomainValidationIssue] = {}
    collections = (
        "composition_input_bundles",
        "generation_profiles",
        "policy_snapshots",
        "authority_artifacts",
        "revision_authority_snapshots",
        "provider_requests",
        "revision_requests",
        "generation_decisions",
    )
    for field_name in collections:
        for index, artifact in enumerate(getattr(bundle, field_name)):
            for issue in validate_artifact(artifact):
                key = (
                    issue.code,
                    issue.artifact_reference,
                    issue.field_reference,
                    issue.artifact_type,
                    issue.related_references,
                    issue.message_key,
                )
                findings.setdefault(
                    key,
                    DomainValidationIssue(
                        code=issue.code,
                        artifact_reference=issue.artifact_reference,
                        field_reference=issue.field_reference,
                        artifact_type=issue.artifact_type,
                        field_path=(field_name, index, *issue.field_path),
                        related_references=issue.related_references,
                        message_key=issue.message_key,
                    ),
                )
    return tuple(sorted(findings.values(), key=_issue_key))


def _constraints_structurally_contradict(
    constraints: list[GenerationConstraint],
) -> bool:
    """Recognize only explicit cross-reference prohibitions as contradictions."""
    references = {item.constraint_reference for item in constraints}
    return any(
        bool(references.intersection(item.prohibited_outcomes)) for item in constraints
    )


def _authority_references(artifact) -> tuple[str, ...]:
    references = getattr(artifact, "authority_references", ())
    if references:
        return tuple(references)
    identity = getattr(artifact, "authority_reference_id", None)
    return (identity,) if identity else ()


def _complete_artifact_key(artifact) -> str:
    """Return a total deterministic key, including non-semantic stored fields."""
    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _add_conflict(
    code,
    artifacts,
    conflicts,
    conflict_type,
    *,
    target_references=(),
    field_path=(),
) -> None:
    references = tuple(sorted({_reference(item) for item in artifacts}))
    authorities = tuple(
        sorted(
            {
                reference
                for item in artifacts
                for reference in _authority_references(item)
            }
        )
    )
    targets = tuple(sorted(set(target_references)))
    path = tuple(field_path)
    seed = {
        "conflict_type": conflict_type.value,
        "issue_code": code,
        "artifact_references": references,
        "target_references": targets,
        "field_path": path,
        "authority_references": authorities,
    }
    conflicts.append(
        AuthorityConflict(
            authority_conflict_id=f"conflict:{semantic_fingerprint(seed)}",
            conflict_type=conflict_type,
            artifact_references=references,
            target_references=targets,
            field_path=path,
            authority_references=authorities,
            issue_code=code,
        )
    )


def _normalize(items: Iterable, key: Callable) -> tuple:
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(canonical_json(item), []).append(item)
    representatives = [
        min(values, key=_complete_artifact_key) for values in groups.values()
    ]
    return tuple(
        sorted(
            representatives,
            key=lambda item: (*key(item), _complete_artifact_key(item)),
        )
    )


def _issue(code, reference, field, related=()):
    return DomainValidationIssue(
        code=code,
        artifact_reference=reference,
        field_reference=field,
        field_path=(field,),
        related_references=tuple(sorted(related)),
    )


def _issue_key(issue):
    return (
        issue.code,
        issue.artifact_reference,
        tuple(map(str, issue.field_path)),
        issue.related_references,
    )


def _reference(artifact) -> str:
    for name in artifact.__class__.model_fields:
        if name.endswith("_id"):
            return str(getattr(artifact, name))
    return type(artifact).__name__


__all__ = (
    "AuthorityConflict",
    "AuthorityConflictSet",
    "AuthorityConflictType",
    "CompatibilityResult",
    "CustomConstraintDefinition",
    "CustomInstructionDefinition",
    "GenerationInputBundle",
    "InputNormalizationResult",
    "construct_compatible_generation_input",
    "normalize_generation_input_bundle",
    "require_compatible_generation_input",
    "validate_generation_input_bundle",
)
