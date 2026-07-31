"""Explicit pure validation for Module 2.9 Phase 3 execution contracts."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .canonical import semantic_fingerprint
from .compatibility import CompatibilityResult, InputNormalizationResult
from .errors import DomainValidationError, DomainValidationIssue
from .execution_identity import *
from .execution_invariants import (
    capability_requirement_violations,
    capability_set_violations,
    duplicate_reference_violations,
    execution_plan_violations,
    failure_policy_violations,
    observation_violations,
    outcome_violations,
    retry_policy_violations,
)
from .execution_models import *
from .identity import is_canonical_identity
from .models import FrozenDomainModel

_IDENTITIES = {
    GenerationExecutionIntent: ("execution_intent_id", execution_intent_identity),
    GenerationExecutionPlan: ("execution_plan_id", execution_plan_identity),
    GenerationExecutionUnit: ("execution_unit_id", execution_unit_identity),
    GenerationExecutionRequest: ("execution_request_id", execution_request_identity),
    GenerationExecutionOutcome: ("execution_outcome_id", execution_outcome_identity),
    GenerationExecutionStateObservation: (
        "state_observation_id",
        state_observation_identity,
    ),
    GenerationCapabilitySet: ("capability_set_id", capability_set_identity),
    GenerationOutputBinding: ("output_binding_id", output_binding_identity),
    GenerationRetryPolicy: ("retry_policy_id", retry_policy_identity),
    GenerationFailurePolicy: ("failure_policy_id", failure_policy_identity),
}


def _issue(code, artifact, path=(), related=()) -> DomainValidationIssue:
    return DomainValidationIssue(
        code=code,
        artifact_reference=_reference(artifact),
        artifact_type=type(artifact).__name__,
        field_reference=".".join(map(str, path)) or None,
        field_path=tuple(path),
        related_references=tuple(sorted(related)),
    )


def _reference(artifact) -> str:
    for name in artifact.__class__.model_fields:
        if name.endswith("_id"):
            return str(getattr(artifact, name))
    return type(artifact).__name__


def _base_issues(artifact) -> list[DomainValidationIssue]:
    issues: list[DomainValidationIssue] = []
    seen: set[int] = set()

    def walk(value, path=()) -> None:
        if isinstance(value, FrozenDomainModel):
            if id(value) in seen:
                return
            seen.add(id(value))
            if hasattr(value, "semantic_fingerprint") and (
                value.semantic_fingerprint != semantic_fingerprint(value)
            ):
                issues.append(
                    _issue(
                        "execution-fingerprint-mismatch",
                        value,
                        (*path, "semantic_fingerprint"),
                    )
                )
            identity = _IDENTITIES.get(type(value))
            if identity and getattr(value, identity[0]) != identity[1](value):
                issues.append(
                    _issue("execution-identity-mismatch", value, (*path, identity[0]))
                )
            for violation in _local_violations(value):
                issues.append(
                    _issue(
                        violation.code,
                        value,
                        (*path, *violation.field_path),
                        violation.related_references,
                    )
                )
            for name in sorted(value.__class__.model_fields):
                walk(getattr(value, name), (*path, name))
        elif isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                walk(item, (*path, index))

    walk(artifact)
    return issues


def _local_violations(artifact):
    issues = list(duplicate_reference_violations(artifact))
    if isinstance(artifact, GenerationCapabilityRequirement):
        issues.extend(capability_requirement_violations(artifact))
    elif isinstance(artifact, GenerationCapabilitySet):
        issues.extend(capability_set_violations(artifact))
    elif isinstance(artifact, GenerationRetryPolicy):
        issues.extend(retry_policy_violations(artifact))
    elif isinstance(artifact, GenerationFailurePolicy):
        issues.extend(failure_policy_violations(artifact))
    elif isinstance(artifact, GenerationExecutionPlan):
        issues.extend(execution_plan_violations(artifact))
    elif isinstance(artifact, GenerationExecutionOutcome):
        issues.extend(outcome_violations(artifact))
    elif isinstance(artifact, GenerationExecutionStateObservation):
        issues.extend(observation_violations(artifact))
    return tuple(issues)


def _ordered(issues) -> tuple[DomainValidationIssue, ...]:
    unique = {
        (
            item.code,
            item.artifact_reference,
            item.field_path,
            item.related_references,
        ): item
        for item in issues
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.code,
                item.artifact_reference,
                tuple(map(str, item.field_path)),
                item.related_references,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class _SelectedPolicyContext:
    policy: Any
    instruction_references: frozenset[str]
    constraint_references: frozenset[str]
    authority_references: frozenset[str]
    target_references: frozenset[str]


def _selected_policy_context(intent, normalized_input, issues):
    policies = tuple(
        item
        for item in normalized_input.normalized_bundle.policy_snapshots
        if item.resolved_generation_policy_id == intent.policy_snapshot_reference
    )
    if len(policies) != 1 or (
        policies[0].policy_fingerprint != intent.policy_snapshot_fingerprint
    ):
        issues.append(
            _issue(
                "execution-intent-selected-policy-unresolved",
                intent,
                ("policy_snapshot_reference",),
            )
        )
        return None
    policy = policies[0]
    instructions = frozenset(
        item.generation_instruction_id
        for item in policy.resolved_generation_instructions
    )
    constraints = frozenset(
        item.generation_constraint_id for item in policy.resolved_generation_constraints
    )
    targets = frozenset(
        reference
        for item in (
            *policy.resolved_generation_instructions,
            *policy.resolved_generation_constraints,
        )
        for reference in item.target_references
    )
    return _SelectedPolicyContext(
        policy=policy,
        instruction_references=instructions,
        constraint_references=constraints,
        authority_references=frozenset(policy.authority_references),
        target_references=targets,
    )


def _global_policy_members(bundle, field: str) -> set[str]:
    return {
        getattr(item, field)
        for policy in bundle.policy_snapshots
        for item in (
            *policy.resolved_generation_instructions,
            *policy.resolved_generation_constraints,
        )
        if hasattr(item, field)
    }


def validate_generation_execution_intent(
    intent: GenerationExecutionIntent,
    normalized_input: InputNormalizationResult | None = None,
    parent_intents: tuple[GenerationExecutionIntent, ...] = (),
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(intent)
    if normalized_input is not None:
        bundle = normalized_input.normalized_bundle
        if (
            intent.normalized_generation_input_fingerprint
            != normalized_input.normalized_fingerprint
        ):
            issues.append(
                _issue(
                    "execution-normalized-input-mismatch",
                    intent,
                    ("normalized_generation_input_fingerprint",),
                )
            )
        profiles = {
            (x.generation_profile_id, x.profile_fingerprint)
            for x in bundle.generation_profiles
        }
        policies = {
            (x.resolved_generation_policy_id, x.policy_fingerprint)
            for x in bundle.policy_snapshots
        }
        if (
            intent.generation_profile_reference,
            intent.generation_profile_fingerprint,
        ) not in profiles:
            issues.append(
                _issue(
                    "execution-profile-linkage-mismatch",
                    intent,
                    ("generation_profile_reference",),
                )
            )
        if (
            intent.policy_snapshot_reference,
            intent.policy_snapshot_fingerprint,
        ) not in policies:
            issues.append(
                _issue(
                    "execution-policy-linkage-mismatch",
                    intent,
                    ("policy_snapshot_reference",),
                )
            )
        selected_policy = _selected_policy_context(intent, normalized_input, issues)
        instruction_refs = (
            set(selected_policy.instruction_references) if selected_policy else set()
        )
        constraint_refs = (
            set(selected_policy.constraint_references) if selected_policy else set()
        )
        authorities = {x.authority_reference_id for x in bundle.authority_artifacts}
        for field, supplied, available in (
            ("authority_references", intent.authority_references, authorities),
        ):
            missing = set(supplied) - available
            if missing:
                issues.append(
                    _issue(
                        "execution-reference-unresolved",
                        intent,
                        (field,),
                        tuple(missing),
                    )
                )
        global_instructions = _global_policy_members(
            bundle, "generation_instruction_id"
        )
        global_constraints = _global_policy_members(bundle, "generation_constraint_id")
        for field, supplied, owned, global_members, code in (
            (
                "instruction_references",
                intent.instruction_references,
                instruction_refs,
                global_instructions,
                "execution-intent-instruction-policy-mismatch",
            ),
            (
                "constraint_references",
                intent.constraint_references,
                constraint_refs,
                global_constraints,
                "execution-intent-constraint-policy-mismatch",
            ),
        ):
            missing = set(supplied) - owned
            if missing:
                issues.append(
                    _issue(
                        (
                            code
                            if missing <= global_members
                            else "execution-reference-unresolved"
                        ),
                        intent,
                        (field,),
                        tuple(missing),
                    )
                )
        if selected_policy is not None:
            supplied_authorities = set(intent.authority_references)
            if foreign := supplied_authorities - set(
                selected_policy.authority_references
            ):
                issues.append(
                    _issue(
                        "execution-intent-authority-policy-mismatch",
                        intent,
                        ("authority_references",),
                        tuple(foreign),
                    )
                )
            selected_instructions = {
                item.generation_instruction_id: item
                for item in selected_policy.policy.resolved_generation_instructions
            }
            authority_types = {
                item.authority_reference_id: item.authority_type
                for item in bundle.authority_artifacts
            }
            required_levels = {
                selected_instructions[reference].authority_level.value
                for reference in intent.instruction_references
                if reference in selected_instructions
            }
            supplied_levels = {
                authority_types[reference]
                for reference in intent.authority_references
                if reference in authority_types
            }
            if missing_levels := required_levels - supplied_levels:
                issues.append(
                    _issue(
                        "execution-intent-authority-policy-mismatch",
                        intent,
                        ("authority_references",),
                        tuple(missing_levels),
                    )
                )
        revisions = {
            item.revision_request_id: item for item in bundle.revision_requests
        }
        if intent.revision_request_reference is not None:
            revision = revisions.get(intent.revision_request_reference)
            if revision is None:
                issues.append(
                    _issue(
                        "execution-revision-reference-unresolved",
                        intent,
                        ("revision_request_reference",),
                    )
                )
            elif (
                revision.requested_authority_inputs.generation_profile_fingerprint
                != intent.generation_profile_fingerprint
                or revision.requested_authority_inputs.resolved_policy_fingerprint
                != intent.policy_snapshot_fingerprint
            ):
                issues.append(
                    _issue(
                        "execution-revision-linkage-mismatch",
                        intent,
                        ("revision_request_reference",),
                    )
                )
        evidence = {
            reference
            for item in bundle.composition_input_bundles
            for reference in _composition_evidence_references(item)
        }
        if missing := set(intent.evidence_references) - evidence:
            issues.append(
                _issue(
                    "execution-evidence-reference-unresolved",
                    intent,
                    ("evidence_references",),
                    tuple(missing),
                )
            )
        targets = {
            reference
            for item in bundle.composition_input_bundles
            for reference in _composition_target_references(item)
        }
        if selected_policy is not None:
            targets.update(selected_policy.target_references)
        targets.update(
            reference
            for revision in bundle.revision_requests
            for reference in revision.target_references
        )
        if missing := set(intent.requested_target_references) - targets:
            foreign_targets = {
                reference
                for policy in bundle.policy_snapshots
                if selected_policy is None or policy is not selected_policy.policy
                for member in (
                    *policy.resolved_generation_instructions,
                    *policy.resolved_generation_constraints,
                )
                for reference in member.target_references
            }
            issues.append(
                _issue(
                    (
                        "execution-intent-target-policy-mismatch"
                        if missing <= foreign_targets
                        else "execution-target-reference-unresolved"
                    ),
                    intent,
                    ("requested_target_references",),
                    tuple(missing),
                )
            )
    if intent.parent_execution_reference is not None:
        if not is_canonical_identity(intent.parent_execution_reference):
            issues.append(
                _issue(
                    "execution-parent-reference-invalid",
                    intent,
                    ("parent_execution_reference",),
                )
            )
        if intent.parent_execution_reference == intent.execution_intent_id:
            issues.append(
                _issue(
                    "execution-parent-self-reference",
                    intent,
                    ("parent_execution_reference",),
                )
            )
        if parent_intents and intent.parent_execution_reference not in {
            item.execution_intent_id for item in parent_intents
        }:
            issues.append(
                _issue(
                    "execution-parent-reference-unresolved",
                    intent,
                    ("parent_execution_reference",),
                )
            )
    return _ordered(issues)


def _composition_evidence_references(item) -> set[str]:
    references: set[str] = set()
    for source in item.verified_sources:
        references.update(
            {source.source_material_id, source.article_reference, source.source_id}
        )
        references.update(span.source_span_id for span in source.verified_text_spans)
    for claim in item.approved_claims:
        references.add(claim.approved_claim_id)
        references.update(claim.source_span_references)
    return references


def _composition_target_references(item) -> set[str]:
    references = {item.episode_reference, item.composition_plan.composition_plan_id}

    def walk(value) -> None:
        if hasattr(value, "model_fields"):
            for name in value.__class__.model_fields:
                child = getattr(value, name)
                if name.endswith(("_id", "_reference")) and isinstance(child, str):
                    references.add(child)
                elif name.endswith("_references") and isinstance(child, tuple):
                    references.update(item for item in child if isinstance(item, str))
                walk(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                walk(child)

    walk(item.composition_plan)
    return references


def validate_generation_execution_unit(
    unit: GenerationExecutionUnit,
    intent: GenerationExecutionIntent | None = None,
    normalized_input: InputNormalizationResult | None = None,
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(unit)
    if intent is not None:
        if (unit.generation_profile_reference, unit.generation_profile_fingerprint) != (
            intent.generation_profile_reference,
            intent.generation_profile_fingerprint,
        ):
            issues.append(
                _issue(
                    "execution-profile-linkage-mismatch",
                    unit,
                    ("generation_profile_reference",),
                )
            )
        if (unit.policy_snapshot_reference, unit.policy_snapshot_fingerprint) != (
            intent.policy_snapshot_reference,
            intent.policy_snapshot_fingerprint,
        ):
            issues.append(
                _issue(
                    "execution-policy-linkage-mismatch",
                    unit,
                    ("policy_snapshot_reference",),
                )
            )
        if not set(unit.target_references).issubset(intent.requested_target_references):
            issues.append(
                _issue("execution-target-outside-intent", unit, ("target_references",))
            )
        comparisons = (
            ("operation_type", unit.operation_type, intent.requested_operation),
            (
                "instruction_references",
                set(unit.instruction_references),
                set(intent.instruction_references),
            ),
            (
                "constraint_references",
                set(unit.constraint_references),
                set(intent.constraint_references),
            ),
            (
                "authority_references",
                set(unit.authority_references),
                set(intent.authority_references),
            ),
            (
                "evidence_references",
                set(unit.evidence_references),
                set(intent.evidence_references),
            ),
        )
        for field, supplied, available in comparisons:
            compatible = (
                supplied == available
                if field == "operation_type"
                else supplied <= available
            )
            if not compatible:
                issues.append(
                    _issue(
                        "execution-unit-intent-linkage-mismatch",
                        unit,
                        (field,),
                    )
                )
    if normalized_input is not None:
        bundle = normalized_input.normalized_bundle
        policy_issues: list[DomainValidationIssue] = []
        selected_policy = (
            _selected_policy_context(intent, normalized_input, policy_issues)
            if intent is not None
            else None
        )
        if intent is not None and selected_policy is None:
            issues.append(
                _issue(
                    "execution-unit-selected-policy-unresolved",
                    unit,
                    ("policy_snapshot_reference",),
                )
            )
        instructions = {
            item.generation_instruction_id: item
            for item in (
                selected_policy.policy.resolved_generation_instructions
                if selected_policy is not None
                else ()
            )
        }
        instruction_refs = set(instructions)
        constraint_refs = {
            item.generation_constraint_id
            for item in (
                selected_policy.policy.resolved_generation_constraints
                if selected_policy is not None
                else ()
            )
        }
        authorities = {
            item.authority_reference_id: item for item in bundle.authority_artifacts
        }
        authority_refs = set(authorities)
        evidence_refs = {
            reference
            for item in bundle.composition_input_bundles
            for reference in _composition_evidence_references(item)
        }
        global_instructions = _global_policy_members(
            bundle, "generation_instruction_id"
        )
        global_constraints = _global_policy_members(bundle, "generation_constraint_id")
        for field, supplied, available, global_members, code in (
            (
                "instruction_references",
                unit.instruction_references,
                instruction_refs,
                global_instructions,
                "execution-unit-instruction-policy-mismatch",
            ),
            (
                "constraint_references",
                unit.constraint_references,
                constraint_refs,
                global_constraints,
                "execution-unit-constraint-policy-mismatch",
            ),
            (
                "authority_references",
                unit.authority_references,
                authority_refs,
                authority_refs,
                "execution-unit-reference-unresolved",
            ),
            (
                "evidence_references",
                unit.evidence_references,
                evidence_refs,
                evidence_refs,
                "execution-unit-reference-unresolved",
            ),
        ):
            if missing := set(supplied) - available:
                issues.append(
                    _issue(
                        (
                            code
                            if missing <= global_members
                            else "execution-unit-reference-unresolved"
                        ),
                        unit,
                        (field,),
                        tuple(missing),
                    )
                )
        if selected_policy is not None and (
            foreign := set(unit.authority_references)
            - set(selected_policy.authority_references)
        ):
            issues.append(
                _issue(
                    "execution-unit-authority-policy-mismatch",
                    unit,
                    ("authority_references",),
                    tuple(foreign),
                )
            )
        required_authority_levels = {
            instructions[reference].authority_level.value
            for reference in unit.instruction_references
            if reference in instructions
        }
        supplied_authority_levels = {
            authorities[reference].authority_type
            for reference in unit.authority_references
            if reference in authorities
        }
        if not required_authority_levels <= supplied_authority_levels:
            issues.append(
                _issue(
                    "execution-unit-authority-insufficient",
                    unit,
                    ("authority_references",),
                    tuple(required_authority_levels - supplied_authority_levels),
                )
            )
        available_sources = {bundle.generation_input_bundle_id}
        direct_targets: set[str] = set()
        for item in bundle.composition_input_bundles:
            direct_targets.update(_composition_target_references(item))
            if set(unit.target_references) & _composition_target_references(item):
                available_sources.update(
                    {
                        item.composition_input_bundle_id,
                        item.composition_plan.composition_plan_id,
                    }
                )
        direct_targets.update(
            reference
            for revision in bundle.revision_requests
            for reference in revision.target_references
        )
        selected_targets = (
            set(selected_policy.target_references) if selected_policy else set()
        )
        missing_targets = (
            set(unit.target_references) - direct_targets - selected_targets
        )
        if missing_targets:
            foreign_targets = {
                reference
                for policy in bundle.policy_snapshots
                if selected_policy is None or policy is not selected_policy.policy
                for member in (
                    *policy.resolved_generation_instructions,
                    *policy.resolved_generation_constraints,
                )
                for reference in member.target_references
            }
            issues.append(
                _issue(
                    (
                        "execution-unit-target-policy-mismatch"
                        if missing_targets <= foreign_targets
                        else "execution-target-outside-intent"
                    ),
                    unit,
                    ("target_references",),
                    tuple(missing_targets),
                )
            )
        if missing := set(unit.source_input_references) - available_sources:
            issues.append(
                _issue(
                    "execution-unit-source-input-unresolved",
                    unit,
                    ("source_input_references",),
                    tuple(missing),
                )
            )
    return _ordered(issues)


def validate_generation_execution_plan(
    plan: GenerationExecutionPlan,
    intent: GenerationExecutionIntent | None = None,
    normalized_input: InputNormalizationResult | None = None,
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(plan)
    if intent is not None:
        if normalized_input is not None:
            issues.extend(
                validate_generation_execution_intent(intent, normalized_input)
            )
        if (plan.execution_intent_reference, plan.execution_intent_fingerprint) != (
            intent.execution_intent_id,
            intent.semantic_fingerprint,
        ):
            issues.append(
                _issue(
                    "execution-intent-linkage-mismatch",
                    plan,
                    ("execution_intent_reference",),
                )
            )
        if (
            plan.normalized_input_fingerprint
            != intent.normalized_generation_input_fingerprint
        ):
            issues.append(
                _issue(
                    "execution-normalized-input-mismatch",
                    plan,
                    ("normalized_input_fingerprint",),
                )
            )
        for unit in plan.ordered_execution_units:
            issues.extend(
                validate_generation_execution_unit(unit, intent, normalized_input)
            )
    capability_ids = {item.capability_set_id for item in plan.capability_sets}
    binding_ids = {item.output_binding_id for item in plan.expected_output_bindings}
    units = {item.execution_unit_id: item for item in plan.ordered_execution_units}
    expected_policies = {item.policy_snapshot_reference for item in units.values()}
    expected_authorities = {
        reference for item in units.values() for reference in item.authority_references
    }
    expected_evidence = {
        reference for item in units.values() for reference in item.evidence_references
    }
    if intent is not None:
        expected_policies.add(intent.policy_snapshot_reference)
        expected_authorities.update(intent.authority_references)
        expected_evidence.update(intent.evidence_references)
    for field, supplied, expected, code in (
        (
            "policy_references",
            set(plan.policy_references),
            expected_policies,
            "execution-plan-policy-references-mismatch",
        ),
        (
            "authority_references",
            set(plan.authority_references),
            expected_authorities,
            "execution-plan-authority-references-mismatch",
        ),
        (
            "evidence_references",
            set(plan.evidence_references),
            expected_evidence,
            "execution-plan-evidence-references-mismatch",
        ),
    ):
        if supplied != expected:
            issues.append(_issue(code, plan, (field,)))
    for index, unit in enumerate(plan.ordered_execution_units):
        if unit.execution_plan_reference != plan.execution_plan_id:
            issues.append(
                _issue(
                    "execution-unit-plan-linkage-mismatch",
                    unit,
                    ("execution_plan_reference",),
                )
            )
        if unit.capability_set_reference not in capability_ids:
            issues.append(
                _issue(
                    "execution-capability-set-unresolved",
                    unit,
                    ("capability_set_reference",),
                )
            )
    for binding in plan.expected_output_bindings:
        unit = units.get(binding.unit_reference)
        if unit is None:
            continue
        if binding.target_reference not in unit.target_references:
            issues.append(
                _issue(
                    "execution-output-binding-target-mismatch",
                    binding,
                    ("target_reference",),
                )
            )
        allowed_scopes = set(unit.target_references) | set(unit.source_input_references)
        if unit.revision_scope_reference is not None:
            allowed_scopes.add(unit.revision_scope_reference)
        if unit.regeneration_scope_reference is not None:
            allowed_scopes.add(unit.regeneration_scope_reference)
        if binding.scope_reference not in allowed_scopes:
            issues.append(
                _issue(
                    "execution-output-binding-scope-mismatch",
                    binding,
                    ("scope_reference",),
                )
            )
        if unit.expected_output_binding_reference != binding.output_binding_id:
            issues.append(
                _issue(
                    "execution-unit-output-binding-linkage-mismatch",
                    unit,
                    ("expected_output_binding_reference",),
                )
            )
        if binding.ordering_required and binding.cardinality.value != "one_or_more":
            issues.append(
                _issue(
                    "execution-output-binding-ordering-invalid",
                    binding,
                    ("ordering_required",),
                )
            )
        expected_types = {
            "generated_text_unit": "provider-generated-unit-v1",
            "generated_section": "generated-section-v1",
            "generated_claim_candidate": "generated-claim-candidate-v1",
            "generated_revision_candidate": "generated-revision-candidate-v1",
            "structured_generation_payload": "structured-generation-payload-v1",
        }
        if binding.expected_artifact_type != expected_types[binding.binding_type.value]:
            issues.append(
                _issue(
                    "execution-output-binding-artifact-type-mismatch",
                    binding,
                    ("expected_artifact_type",),
                )
            )
        if (
            binding.binding_type.value == "generated_revision_candidate"
            and unit.operation_type.value
            not in {"revision_generation", "scoped_regeneration"}
        ):
            issues.append(
                _issue(
                    "execution-output-binding-operation-mismatch",
                    binding,
                    ("binding_type",),
                )
            )
    required = set(plan.failure_policy.required_output_binding_references)
    optional = set(plan.failure_policy.optional_output_binding_references)
    if required & optional:
        issues.append(
            _issue(
                "execution-failure-binding-classification-conflict",
                plan.failure_policy,
                ("required_output_binding_references",),
            )
        )
    missing = (required | optional) - binding_ids
    if missing:
        issues.append(
            _issue(
                "execution-failure-binding-unresolved",
                plan.failure_policy,
                ("required_output_binding_references",),
                tuple(missing),
            )
        )
    expected_required = {
        item.output_binding_id
        for item in plan.expected_output_bindings
        if item.required
    }
    expected_optional = binding_ids - expected_required
    if required != expected_required or optional != expected_optional:
        issues.append(
            _issue(
                "execution-output-binding-classification-mismatch",
                plan.failure_policy,
                ("required_output_binding_references",),
            )
        )
    if plan.failure_policy.retry_policy_reference != plan.retry_policy.retry_policy_id:
        issues.append(
            _issue(
                "execution-failure-retry-linkage-mismatch",
                plan.failure_policy,
                ("retry_policy_reference",),
            )
        )
    return _ordered(issues)


def validate_generation_execution_request(
    request: GenerationExecutionRequest,
    plan: GenerationExecutionPlan | None = None,
    intent: GenerationExecutionIntent | None = None,
    normalized_input: InputNormalizationResult | None = None,
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(request)
    if plan is not None and intent is not None and normalized_input is not None:
        issues.extend(
            validate_generation_execution_plan(plan, intent, normalized_input)
        )
    if plan is not None:
        if (request.execution_plan_reference, request.execution_plan_fingerprint) != (
            plan.execution_plan_id,
            plan.semantic_fingerprint,
        ):
            issues.append(
                _issue(
                    "execution-request-plan-linkage-mismatch",
                    request,
                    ("execution_plan_reference",),
                )
            )
        units = {item.execution_unit_id: item for item in plan.ordered_execution_units}
        unit = units.get(request.execution_unit_reference)
        if (
            unit is None
            or request.execution_unit_fingerprint != unit.semantic_fingerprint
        ):
            issues.append(
                _issue(
                    "execution-request-unit-linkage-mismatch",
                    request,
                    ("execution_unit_reference",),
                )
            )
        else:
            comparisons = (
                (
                    "normalized_input_fingerprint",
                    request.normalized_input_fingerprint,
                    plan.normalized_input_fingerprint,
                ),
                (
                    "execution_intent_reference",
                    request.execution_intent_reference,
                    plan.execution_intent_reference,
                ),
                (
                    "generation_profile_reference",
                    request.generation_profile_reference,
                    unit.generation_profile_reference,
                ),
                (
                    "generation_profile_fingerprint",
                    request.generation_profile_fingerprint,
                    unit.generation_profile_fingerprint,
                ),
                (
                    "policy_snapshot_reference",
                    request.policy_snapshot_reference,
                    unit.policy_snapshot_reference,
                ),
                (
                    "policy_snapshot_fingerprint",
                    request.policy_snapshot_fingerprint,
                    unit.policy_snapshot_fingerprint,
                ),
                (
                    "target_references",
                    request.target_references,
                    unit.target_references,
                ),
                (
                    "instruction_references",
                    request.instruction_references,
                    unit.instruction_references,
                ),
                (
                    "constraint_references",
                    request.constraint_references,
                    unit.constraint_references,
                ),
                (
                    "authority_references",
                    request.authority_references,
                    unit.authority_references,
                ),
                (
                    "evidence_references",
                    request.evidence_references,
                    unit.evidence_references,
                ),
                (
                    "expected_output_binding_reference",
                    request.expected_output_binding_reference,
                    unit.expected_output_binding_reference,
                ),
                (
                    "retry_policy_reference",
                    request.retry_policy_reference,
                    plan.retry_policy_reference,
                ),
                (
                    "failure_policy_reference",
                    request.failure_policy_reference,
                    plan.failure_policy_reference,
                ),
            )
            for field, supplied, expected in comparisons:
                if supplied != expected:
                    issues.append(
                        _issue(
                            "execution-request-linkage-mismatch",
                            request,
                            (field,),
                        )
                    )
            capabilities = {
                item.capability_set_id: item for item in plan.capability_sets
            }
            if request.capability_set != capabilities.get(
                unit.capability_set_reference
            ):
                issues.append(
                    _issue(
                        "execution-request-capability-mismatch",
                        request,
                        ("capability_set",),
                    )
                )
    if (
        intent is not None
        and request.execution_intent_reference != intent.execution_intent_id
    ):
        issues.append(
            _issue(
                "execution-request-intent-linkage-mismatch",
                request,
                ("execution_intent_reference",),
            )
        )
    if (
        normalized_input is not None
        and request.normalized_input_fingerprint
        != normalized_input.normalized_fingerprint
    ):
        issues.append(
            _issue(
                "execution-request-normalized-input-mismatch",
                request,
                ("normalized_input_fingerprint",),
            )
        )
    return _ordered(issues)


def validate_generation_execution_outcome(
    outcome: GenerationExecutionOutcome,
    request: GenerationExecutionRequest | None = None,
    plan: GenerationExecutionPlan | None = None,
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(outcome)
    if request is not None and (
        outcome.execution_request_reference,
        outcome.execution_request_fingerprint,
    ) != (request.execution_request_id, request.semantic_fingerprint):
        issues.append(
            _issue(
                "execution-outcome-request-linkage-mismatch",
                outcome,
                ("execution_request_reference",),
            )
        )
    if request is not None:
        if (
            outcome.applied_profile_fingerprint
            != request.generation_profile_fingerprint
        ):
            issues.append(
                _issue(
                    "execution-outcome-profile-linkage-mismatch",
                    outcome,
                    ("applied_profile_fingerprint",),
                )
            )
        if outcome.applied_policy_fingerprint != request.policy_snapshot_fingerprint:
            issues.append(
                _issue(
                    "execution-outcome-policy-linkage-mismatch",
                    outcome,
                    ("applied_policy_fingerprint",),
                )
            )
        if not set(outcome.affected_target_references).issubset(
            request.target_references
        ):
            issues.append(
                _issue(
                    "execution-outcome-target-reference-unresolved",
                    outcome,
                    ("affected_target_references",),
                    tuple(
                        set(outcome.affected_target_references)
                        - set(request.target_references)
                    ),
                )
            )
    if plan is not None:
        known = {item.output_binding_id for item in plan.expected_output_bindings}
        supplied = set(outcome.satisfied_output_binding_references) | set(
            outcome.missing_output_binding_references
        )
        overlap = set(outcome.satisfied_output_binding_references) & set(
            outcome.missing_output_binding_references
        )
        if overlap:
            issues.append(
                _issue(
                    "execution-outcome-binding-classification-conflict",
                    outcome,
                    ("satisfied_output_binding_references",),
                    tuple(overlap),
                )
            )
        if not supplied.issubset(known):
            issues.append(
                _issue(
                    "execution-outcome-binding-unresolved",
                    outcome,
                    ("satisfied_output_binding_references",),
                    tuple(supplied - known),
                )
            )
        required = set(plan.failure_policy.required_output_binding_references)
        if outcome.status.value == "success" and not required.issubset(
            outcome.satisfied_output_binding_references
        ):
            issues.append(
                _issue(
                    "execution-outcome-required-binding-missing",
                    outcome,
                    ("satisfied_output_binding_references",),
                )
            )
        if outcome.failure_type is not None:
            retryable = set(plan.retry_policy.retryable_failure_types)
            non_retryable = set(plan.retry_policy.non_retryable_failure_types)
            if outcome.failure_type not in retryable | non_retryable:
                issues.append(
                    _issue(
                        "execution-retry-failure-type-unclassified",
                        outcome,
                        ("failure_type",),
                    )
                )
            elif (outcome.failure_type in retryable and not outcome.retry_eligible) or (
                outcome.failure_type in non_retryable and outcome.retry_eligible
            ):
                issues.append(
                    _issue(
                        "execution-outcome-retry-policy-mismatch",
                        outcome,
                        ("retry_eligible",),
                    )
                )
    return _ordered(issues)


def validate_generation_retry_policy(
    policy: GenerationRetryPolicy,
) -> tuple[DomainValidationIssue, ...]:
    return _ordered(_base_issues(policy))


def validate_generation_failure_policy(
    policy: GenerationFailurePolicy, retry_policy: GenerationRetryPolicy | None = None
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(policy)
    if (
        retry_policy is not None
        and policy.retry_policy_reference != retry_policy.retry_policy_id
    ):
        issues.append(
            _issue(
                "execution-failure-retry-linkage-mismatch",
                policy,
                ("retry_policy_reference",),
            )
        )
    return _ordered(issues)


def validate_generation_execution_state_observation(
    observation: GenerationExecutionStateObservation,
    outcome: GenerationExecutionOutcome | None = None,
    previous_observation: GenerationExecutionStateObservation | None = None,
) -> tuple[DomainValidationIssue, ...]:
    issues = _base_issues(observation)
    expected_status = {
        "succeeded": "success",
        "partially_succeeded": "partial_success",
        "failed": "failure",
    }.get(observation.observed_state.value)
    if outcome is not None:
        if observation.outcome_reference != outcome.execution_outcome_id:
            issues.append(
                _issue(
                    "execution-observation-outcome-linkage-mismatch",
                    observation,
                    ("outcome_reference",),
                )
            )
        if expected_status is None or outcome.status.value != expected_status:
            issues.append(
                _issue(
                    "execution-observation-outcome-status-mismatch",
                    observation,
                    ("observed_state",),
                )
            )
    if previous_observation is not None and (
        observation.sequence_number != previous_observation.sequence_number + 1
        or observation.execution_request_reference
        != previous_observation.execution_request_reference
        or observation.previous_observation_fingerprint
        != previous_observation.semantic_fingerprint
    ):
        issues.append(
            _issue(
                "execution-observation-previous-linkage-mismatch",
                observation,
                ("previous_observation_fingerprint",),
            )
        )
    return _ordered(issues)


def require_valid_generation_execution_plan(
    plan: GenerationExecutionPlan, intent: GenerationExecutionIntent | None = None
) -> None:
    if issues := validate_generation_execution_plan(plan, intent):
        raise DomainValidationError(issues)


def construct_generation_execution_plan(
    payload: dict[str, Any],
) -> GenerationExecutionPlan:
    try:
        plan = GenerationExecutionPlan.model_validate(payload)
    except ValidationError as error:
        issues = tuple(
            DomainValidationIssue(
                code=str(item["type"]),
                artifact_reference=str(
                    payload.get("execution_plan_id", "GenerationExecutionPlan")
                ),
                artifact_type="GenerationExecutionPlan",
                field_reference=".".join(map(str, item["loc"])),
                field_path=tuple(item["loc"]),
                message_key=str(item["type"]),
            )
            for item in sorted(error.errors(), key=lambda x: tuple(map(str, x["loc"])))
        )
        raise DomainValidationError(issues) from None
    require_valid_generation_execution_plan(plan)
    return plan


def derive_generation_execution_eligibility(
    plan: GenerationExecutionPlan,
    compatibility: CompatibilityResult | None = None,
    intent: GenerationExecutionIntent | None = None,
    requests: tuple[GenerationExecutionRequest, ...] = (),
    normalized_input: InputNormalizationResult | None = None,
) -> GenerationExecutionEligibility:
    issues = list(validate_generation_execution_plan(plan, intent, normalized_input))
    if intent is not None:
        issues.extend(validate_generation_execution_intent(intent, normalized_input))
    for request in requests:
        issues.extend(
            validate_generation_execution_request(
                request,
                plan=plan,
                intent=intent,
                normalized_input=normalized_input,
            )
        )
    conflicts = ()
    input_codes = ()
    if compatibility is not None and not compatibility.compatible:
        input_codes = tuple(sorted({item.code for item in compatibility.issues}))
        conflicts = tuple(
            item.authority_conflict_id
            for item in compatibility.authority_conflicts.conflicts
        )
        issues.extend(compatibility.issues)
    blocked = bool(issues)
    units = tuple(item.execution_unit_id for item in plan.ordered_execution_units)
    capabilities = tuple(
        sorted(
            (r for s in plan.capability_sets for r in s.requirements),
            key=lambda x: (x.capability.value, x.custom_identifier or "", x.required),
        )
    )
    value = GenerationExecutionEligibility(
        execution_plan_reference=plan.execution_plan_id,
        eligible=not blocked,
        blocking_issues=_ordered(issues),
        required_capabilities=capabilities,
        unresolved_authority_conflict_references=tuple(sorted(conflicts)),
        unresolved_input_issue_codes=input_codes,
        structurally_eligible_unit_references=() if blocked else units,
        blocked_unit_references=units if blocked else (),
        semantic_fingerprint="0" * 64,
    )
    return value.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(value)}
    )


__all__ = tuple(
    name
    for name in globals()
    if name.startswith(
        (
            "validate_generation_",
            "require_valid_generation_",
            "construct_generation_",
            "derive_generation_",
        )
    )
)
