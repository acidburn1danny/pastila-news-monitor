"""Phase 3 provider-neutral execution contract tests."""

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    PASTILA_ACIDA_GENERATION_PROFILE,
    AuthorityLevel,
    AuthorityReference,
    ConstraintSeverity,
    DomainValidationError,
    FailurePropagationMode,
    GenerationCapability,
    GenerationCapabilityRequirement,
    GenerationCapabilitySet,
    GenerationConstraint,
    GenerationConstraintType,
    GenerationDependencyDeclaration,
    GenerationExecutionEligibility,
    GenerationExecutionFailureType,
    GenerationExecutionIntent,
    GenerationExecutionOutcome,
    GenerationExecutionPlan,
    GenerationExecutionRequest,
    GenerationExecutionState,
    GenerationExecutionStateObservation,
    GenerationExecutionUnit,
    GenerationFailurePolicy,
    GenerationInstruction,
    GenerationInstructionType,
    GenerationOperation,
    GenerationOutcomeStatus,
    GenerationOutputBinding,
    GenerationOutputBindingType,
    GenerationOutputScope,
    GenerationRetryPolicy,
    InputNormalizationResult,
    OutputCardinality,
    ResolvedGenerationPolicySnapshot,
    RetryBackoffClassification,
    RetryScope,
    capability_set_identity,
    construct_generation_execution_plan,
    derive_generation_execution_eligibility,
    derive_identity,
    execution_intent_identity,
    execution_outcome_identity,
    execution_plan_identity,
    execution_request_identity,
    execution_unit_identity,
    failure_policy_identity,
    normalize_generation_input_bundle,
    output_binding_identity,
    retry_policy_identity,
    semantic_fingerprint,
    state_observation_identity,
    validate_generation_execution_intent,
    validate_generation_execution_outcome,
    validate_generation_execution_plan,
    validate_generation_execution_request,
    validate_generation_execution_state_observation,
    validate_generation_execution_unit,
    validate_generation_input_bundle,
    validate_generation_retry_policy,
)
from pastila_scout.editor.script_composer.compatibility import GenerationInputBundle

ZERO = "0" * 64


def _seal(value, identity_field=None, identity_function=None):
    if identity_field:
        value = value.model_copy(update={identity_field: identity_function(value)})
    return value.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(value)}
    )


def _phase2_input() -> InputNormalizationResult:
    authority = AuthorityReference(
        authority_reference_id="authority:composition",
        authority_type=AuthorityLevel.COMPOSITION_PLAN.value,
        source_reference="composition:one",
        authority_version="1.0.0",
        semantic_fingerprint=ZERO,
    )
    authority = authority.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(authority)}
    )
    constraints = []
    for index in range(1, 4):
        constraint = GenerationConstraint(
            generation_constraint_id=f"constraint:beat:{index}",
            constraint_type=GenerationConstraintType.STRUCTURE,
            target_references=(f"beat:{index}",),
            severity=ConstraintSeverity.BLOCKING,
            mandatory=True,
            constraint_reference=f"rule:beat:{index}",
            source_references=("composition:one",),
            constraint_fingerprint=ZERO,
        )
        constraints.append(
            constraint.model_copy(
                update={"constraint_fingerprint": semantic_fingerprint(constraint)}
            )
        )
    policy = ResolvedGenerationPolicySnapshot(
        resolved_generation_policy_id="policy:one",
        policy_version="1.0.0",
        source_policy_reference="source-policy:one",
        source_policy_fingerprint=ZERO,
        authority_references=("authority:composition",),
        resolved_generation_constraints=tuple(constraints),
        policy_fingerprint=ZERO,
    )
    policy = policy.model_copy(
        update={"policy_fingerprint": semantic_fingerprint(policy)}
    )
    bundle = GenerationInputBundle(
        generation_input_bundle_id="input:one",
        generation_profiles=(PASTILA_ACIDA_GENERATION_PROFILE,),
        policy_snapshots=(policy,),
        authority_artifacts=(authority,),
    )
    return normalize_generation_input_bundle(bundle)


def _intent(normalized=None):
    normalized = normalized or _phase2_input()
    profile = PASTILA_ACIDA_GENERATION_PROFILE
    policy = normalized.normalized_bundle.policy_snapshots[0]
    value = GenerationExecutionIntent(
        execution_intent_id=derive_identity("temporary", "intent"),
        normalized_generation_input_fingerprint=normalized.normalized_fingerprint,
        generation_profile_reference=profile.generation_profile_id,
        generation_profile_fingerprint=profile.profile_fingerprint,
        policy_snapshot_reference=policy.resolved_generation_policy_id,
        policy_snapshot_fingerprint=policy.policy_fingerprint,
        requested_operation=GenerationOperation.INITIAL_GENERATION,
        requested_output_scope=GenerationOutputScope.BEAT,
        requested_target_references=("beat:1", "beat:2", "beat:3"),
        authority_references=("authority:composition",),
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "execution_intent_id", execution_intent_identity)


def _capabilities(requirements=None):
    requirements = requirements or (
        GenerationCapabilityRequirement(
            capability=GenerationCapability.STRUCTURED_OUTPUT
        ),
    )
    value = GenerationCapabilitySet(
        capability_set_id=derive_identity("temporary", "capabilities"),
        requirements=requirements,
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "capability_set_id", capability_set_identity)


def _retry():
    value = GenerationRetryPolicy(
        retry_policy_id=derive_identity("temporary", "retry"),
        maximum_attempts=2,
        retryable_failure_types=(GenerationExecutionFailureType.EXECUTION_TIMEOUT,),
        non_retryable_failure_types=(GenerationExecutionFailureType.INVALID_REQUEST,),
        retry_scope=RetryScope.UNIT,
        replacement_execution_allowed=True,
        backoff_classification=RetryBackoffClassification.DEFERRED,
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "retry_policy_id", retry_policy_identity)


def _failure(retry, required=()):
    value = GenerationFailurePolicy(
        failure_policy_id=derive_identity("temporary", "failure"),
        allowed_partial_completion=True,
        required_output_binding_references=required,
        propagation_mode=FailurePropagationMode.BLOCK_DEPENDENTS,
        block_dependent_units=True,
        allow_supersession=True,
        allow_cancellation=True,
        retry_policy_reference=retry.retry_policy_id,
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "failure_policy_id", failure_policy_identity)


def _unit(intent, plan_ref, ordinal=0, dependencies=(), binding_ref="binding:pending"):
    value = GenerationExecutionUnit(
        execution_unit_id=derive_identity("temporary", ("unit", ordinal)),
        execution_plan_reference=plan_ref,
        ordinal=ordinal,
        operation_type=intent.requested_operation,
        target_references=(f"beat:{ordinal + 1}",),
        source_input_references=("input:one",),
        generation_profile_reference=intent.generation_profile_reference,
        generation_profile_fingerprint=intent.generation_profile_fingerprint,
        policy_snapshot_reference=intent.policy_snapshot_reference,
        policy_snapshot_fingerprint=intent.policy_snapshot_fingerprint,
        authority_references=intent.authority_references,
        dependency_unit_references=dependencies,
        expected_output_binding_reference=binding_ref,
        capability_set_reference="capability:pending",
        semantic_fingerprint=ZERO,
    )
    return value


def _binding(unit_ref, ordinal=0):
    value = GenerationOutputBinding(
        output_binding_id=derive_identity("temporary", ("binding", ordinal)),
        binding_type=GenerationOutputBindingType.GENERATED_TEXT_UNIT,
        target_reference=f"beat:{ordinal + 1}",
        expected_artifact_type="provider-generated-unit-v1",
        required=True,
        unit_reference=unit_ref,
        scope_reference=f"beat:{ordinal + 1}",
        cardinality=OutputCardinality.ONE,
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "output_binding_id", output_binding_identity)


def _plan(
    unit_count=1,
    *,
    normalized=None,
    plan_policy_references=None,
    plan_authority_references=None,
    plan_evidence_references=None,
    unit_updates=None,
    intent_override=None,
):
    intent = intent_override or _intent(normalized)
    retry = _retry()
    capabilities = _capabilities()
    provisional_bindings = tuple(
        _binding(f"provisional:{index}", index) for index in range(unit_count)
    )
    provisional_units = tuple(
        _unit(
            intent,
            "plan:pending",
            index,
            (() if index == 0 else (f"provisional:{index - 1}",)),
            provisional_bindings[index].output_binding_id,
        ).model_copy(
            update={
                "execution_unit_id": f"provisional:{index}",
                **(unit_updates or {}),
            }
        )
        for index in range(unit_count)
    )
    provisional_dependencies = tuple(
        GenerationDependencyDeclaration(
            source_unit_reference=f"provisional:{index}",
            dependency_unit_reference=f"provisional:{index - 1}",
        )
        for index in range(1, unit_count)
    )
    initial_failure = _failure(
        retry, tuple(item.output_binding_id for item in provisional_bindings)
    )
    provisional = GenerationExecutionPlan.model_construct(
        execution_plan_id=derive_identity("temporary", "plan"),
        contract_version="generation-execution-plan-v1",
        execution_intent_reference=intent.execution_intent_id,
        execution_intent_fingerprint=intent.semantic_fingerprint,
        normalized_input_fingerprint=intent.normalized_generation_input_fingerprint,
        ordered_execution_units=provisional_units,
        dependency_declarations=provisional_dependencies,
        policy_references=(
            (intent.policy_snapshot_reference,)
            if plan_policy_references is None
            else plan_policy_references
        ),
        authority_references=(
            intent.authority_references
            if plan_authority_references is None
            else plan_authority_references
        ),
        evidence_references=(
            () if plan_evidence_references is None else plan_evidence_references
        ),
        expected_output_bindings=provisional_bindings,
        capability_sets=(capabilities,),
        retry_policy_reference=retry.retry_policy_id,
        retry_policy=retry,
        failure_policy_reference=initial_failure.failure_policy_id,
        failure_policy=initial_failure,
        semantic_fingerprint=ZERO,
    )
    plan_id = execution_plan_identity(provisional)
    units = []
    bindings = []
    for index in range(unit_count):
        dependencies = () if index == 0 else (units[index - 1].execution_unit_id,)
        unit = _unit(
            intent,
            plan_id,
            index,
            dependencies,
            provisional_bindings[index].output_binding_id,
        )
        unit = unit.model_copy(update=unit_updates or {})
        unit = unit.model_copy(
            update={"capability_set_reference": capabilities.capability_set_id}
        )
        unit = unit.model_copy(
            update={"execution_unit_id": execution_unit_identity(unit)}
        )
        binding = provisional_bindings[index].model_copy(
            update={"unit_reference": unit.execution_unit_id}
        )
        binding = binding.model_copy(
            update={"semantic_fingerprint": semantic_fingerprint(binding)}
        )
        unit = unit.model_copy(
            update={"semantic_fingerprint": semantic_fingerprint(unit)}
        )
        units.append(unit)
        bindings.append(binding)
    failure = _failure(retry, tuple(item.output_binding_id for item in bindings))
    dependencies = tuple(
        GenerationDependencyDeclaration(
            source_unit_reference=units[index].execution_unit_id,
            dependency_unit_reference=units[index - 1].execution_unit_id,
        )
        for index in range(1, unit_count)
    )
    plan = GenerationExecutionPlan(
        execution_plan_id=plan_id,
        execution_intent_reference=intent.execution_intent_id,
        execution_intent_fingerprint=intent.semantic_fingerprint,
        normalized_input_fingerprint=intent.normalized_generation_input_fingerprint,
        ordered_execution_units=tuple(units),
        dependency_declarations=dependencies,
        policy_references=(
            (intent.policy_snapshot_reference,)
            if plan_policy_references is None
            else plan_policy_references
        ),
        authority_references=(
            intent.authority_references
            if plan_authority_references is None
            else plan_authority_references
        ),
        evidence_references=(
            () if plan_evidence_references is None else plan_evidence_references
        ),
        expected_output_bindings=tuple(bindings),
        capability_sets=(capabilities,),
        retry_policy_reference=retry.retry_policy_id,
        retry_policy=retry,
        failure_policy_reference=failure.failure_policy_id,
        failure_policy=failure,
        semantic_fingerprint=ZERO,
    )
    plan = plan.model_copy(update={"semantic_fingerprint": semantic_fingerprint(plan)})
    assert execution_plan_identity(plan) == plan_id
    return intent, plan


def _request(intent, plan):
    unit = plan.ordered_execution_units[0]
    value = GenerationExecutionRequest(
        execution_request_id=derive_identity("temporary", "request"),
        execution_plan_reference=plan.execution_plan_id,
        execution_plan_fingerprint=plan.semantic_fingerprint,
        execution_unit_reference=unit.execution_unit_id,
        execution_unit_fingerprint=unit.semantic_fingerprint,
        normalized_input_fingerprint=plan.normalized_input_fingerprint,
        execution_intent_reference=intent.execution_intent_id,
        generation_profile_reference=unit.generation_profile_reference,
        generation_profile_fingerprint=unit.generation_profile_fingerprint,
        policy_snapshot_reference=unit.policy_snapshot_reference,
        policy_snapshot_fingerprint=unit.policy_snapshot_fingerprint,
        target_references=unit.target_references,
        instruction_references=unit.instruction_references,
        constraint_references=unit.constraint_references,
        authority_references=unit.authority_references,
        evidence_references=unit.evidence_references,
        capability_set=plan.capability_sets[0],
        expected_output_binding_reference=unit.expected_output_binding_reference,
        retry_policy_reference=plan.retry_policy_reference,
        failure_policy_reference=plan.failure_policy_reference,
        semantic_fingerprint=ZERO,
    )
    return _seal(value, "execution_request_id", execution_request_identity)


def test_valid_intent_links_to_normalized_phase2_input():
    normalized = _phase2_input()
    intent = _intent(normalized)
    assert validate_generation_execution_intent(intent, normalized) == ()
    assert execution_intent_identity(intent) == intent.execution_intent_id


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "normalized_generation_input_fingerprint",
            "execution-normalized-input-mismatch",
        ),
        ("generation_profile_fingerprint", "execution-profile-linkage-mismatch"),
        ("policy_snapshot_fingerprint", "execution-policy-linkage-mismatch"),
    ),
)
def test_intent_linkage_mismatches_are_deterministic(field, code):
    normalized = _phase2_input()
    invalid = _seal(
        _intent(normalized).model_copy(update={field: "1" * 64}),
        "execution_intent_id",
        execution_intent_identity,
    )
    assert code in {
        item.code for item in validate_generation_execution_intent(invalid, normalized)
    }


def test_valid_single_and_multi_unit_plans_are_deterministic():
    for count in (1, 3):
        intent, plan = _plan(count)
        assert validate_generation_execution_plan(plan, intent) == ()
        assert execution_plan_identity(plan) == plan.execution_plan_id


@pytest.mark.parametrize(
    ("mutation", "code"),
    (
        ("duplicate-id", "execution-unit-identity-duplicate"),
        ("duplicate-ordinal", "execution-unit-ordinal-duplicate"),
        ("missing-dependency", "execution-unit-dependency-missing"),
        ("self-dependency", "execution-unit-self-dependency"),
        ("cycle", "execution-unit-dependency-cycle"),
    ),
)
def test_graph_failures_survive_model_copy_and_resealing(mutation, code):
    intent, plan = _plan(2)
    first, second = plan.ordered_execution_units
    if mutation == "duplicate-id":
        second = second.model_copy(
            update={"execution_unit_id": first.execution_unit_id}
        )
    elif mutation == "duplicate-ordinal":
        second = second.model_copy(update={"ordinal": first.ordinal})
    elif mutation == "missing-dependency":
        second = second.model_copy(
            update={"dependency_unit_references": ("unit:missing",)}
        )
    elif mutation == "self-dependency":
        second = second.model_copy(
            update={"dependency_unit_references": (second.execution_unit_id,)}
        )
    else:
        first = first.model_copy(
            update={"dependency_unit_references": (second.execution_unit_id,)}
        )
    invalid = plan.model_copy(update={"ordered_execution_units": (first, second)})
    invalid = invalid.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(invalid)}
    )
    issues = validate_generation_execution_plan(invalid, intent)
    assert code in {item.code for item in issues}


def test_capability_vocabulary_custom_extension_and_duplicate_rejection():
    custom = GenerationCapabilityRequirement(
        capability=GenerationCapability.CUSTOM,
        custom_identifier="custom:editorial-json",
    )
    value = _capabilities((custom,))
    assert value.requirements == (custom,)
    with pytest.raises(ValidationError, match="execution-capability-duplicate"):
        _capabilities((custom, custom))


def test_valid_request_and_context_mismatch():
    intent, plan = _plan()
    request = _request(intent, plan)
    assert validate_generation_execution_request(request, plan) == ()
    invalid = _seal(
        request.model_copy(update={"target_references": ("beat:other",)}),
        "execution_request_id",
        execution_request_identity,
    )
    assert "execution-request-linkage-mismatch" in {
        item.code for item in validate_generation_execution_request(invalid, plan)
    }
    assert "model" not in GenerationExecutionRequest.model_fields
    assert "prompt" not in GenerationExecutionRequest.model_fields
    assert "temperature" not in GenerationExecutionRequest.model_fields


@pytest.mark.parametrize("status", tuple(GenerationOutcomeStatus))
def test_outcome_shapes_and_fingerprints(status):
    intent, plan = _plan(2 if status is GenerationOutcomeStatus.PARTIAL_SUCCESS else 1)
    request = _request(intent, plan)
    binding = plan.expected_output_bindings[0].output_binding_id
    values = {
        "execution_outcome_id": derive_identity("temporary", status.value),
        "execution_request_reference": request.execution_request_id,
        "execution_request_fingerprint": request.semantic_fingerprint,
        "status": status,
        "applied_profile_fingerprint": request.generation_profile_fingerprint,
        "applied_policy_fingerprint": request.policy_snapshot_fingerprint,
        "semantic_fingerprint": ZERO,
    }
    if status is GenerationOutcomeStatus.SUCCESS:
        values.update(
            produced_output_artifact_references=("output:one",),
            satisfied_output_binding_references=(binding,),
        )
    elif status is GenerationOutcomeStatus.PARTIAL_SUCCESS:
        values.update(
            produced_output_artifact_references=("output:one",),
            satisfied_output_binding_references=(binding,),
            missing_output_binding_references=(
                plan.expected_output_bindings[1].output_binding_id,
            ),
            retry_eligible=True,
        )
    else:
        values.update(
            failure_type=GenerationExecutionFailureType.EXECUTION_TIMEOUT,
            failure_code="execution-timeout",
            retry_eligible=True,
        )
    outcome = GenerationExecutionOutcome(**values)
    outcome = _seal(outcome, "execution_outcome_id", execution_outcome_identity)
    assert validate_generation_execution_outcome(outcome, request, plan) == ()


def test_retry_conflict_and_invalid_attempt_count_are_rejected():
    retry = _retry()
    invalid = retry.model_copy(
        update={"non_retryable_failure_types": retry.retryable_failure_types}
    )
    invalid = invalid.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(invalid)}
    )
    assert "execution-retry-classification-conflict" in {
        item.code for item in validate_generation_retry_policy(invalid)
    }
    with pytest.raises(ValidationError):
        GenerationRetryPolicy(**{**retry.model_dump(), "maximum_attempts": 0})


def test_lifecycle_observation_requires_deterministic_lineage():
    value = GenerationExecutionStateObservation(
        state_observation_id=derive_identity("temporary", "state"),
        execution_request_reference="request:one",
        observed_state=GenerationExecutionState.PLANNED,
        sequence_number=0,
        semantic_fingerprint=ZERO,
    )
    value = _seal(value, "state_observation_id", state_observation_identity)
    assert validate_generation_execution_state_observation(value) == ()
    invalid = value.model_copy(update={"sequence_number": 1})
    invalid = _seal(invalid, "state_observation_id", state_observation_identity)
    assert "execution-observation-previous-required" in {
        item.code for item in validate_generation_execution_state_observation(invalid)
    }


def test_eligibility_is_structural_not_editorial_readiness():
    _, plan = _plan()
    result = derive_generation_execution_eligibility(plan)
    assert result.eligible
    assert result.structurally_eligible_unit_references == (
        plan.ordered_execution_units[0].execution_unit_id,
    )
    assert "readiness" not in GenerationExecutionEligibility.model_fields


def test_plan_public_factory_normalizes_contract_errors():
    _, plan = _plan()
    payload = plan.model_dump()
    payload["ordered_execution_units"] = []
    with pytest.raises(DomainValidationError):
        construct_generation_execution_plan(payload)


def test_unicode_and_permutation_fingerprints_are_stable():
    composed = GenerationCapabilityRequirement(
        capability=GenerationCapability.CUSTOM,
        custom_identifier="custom:romanian-output",
    )
    first = _capabilities(
        (
            composed,
            GenerationCapabilityRequirement(
                capability=GenerationCapability.STRUCTURED_OUTPUT
            ),
        )
    )
    second = _capabilities(tuple(reversed(first.requirements)))
    assert first.semantic_fingerprint == second.semantic_fingerprint
    assert first.capability_set_id == second.capability_set_id


def test_graph_issue_order_is_permutation_independent_after_resealing():
    intent, plan = _plan(3)
    outputs = []
    for dependencies in (("missing:z", "missing:a"), ("missing:a", "missing:z")):
        units = tuple(
            unit.model_copy(update={"dependency_unit_references": dependencies})
            for unit in plan.ordered_execution_units
        )
        invalid = plan.model_copy(update={"ordered_execution_units": units})
        invalid = invalid.model_copy(
            update={"semantic_fingerprint": semantic_fingerprint(invalid)}
        )
        outputs.append(
            tuple(
                (x.code, x.related_references)
                for x in validate_generation_execution_plan(invalid, intent)
            )
        )
    assert outputs[0] == outputs[1]


def test_phase3_modules_have_no_runtime_dependency_leaks():
    root = (
        Path(__file__).parents[1]
        / "src"
        / "pastila_scout"
        / "editor"
        / "script_composer"
    )
    forbidden = {
        "asyncio",
        "httpx",
        "openai",
        "requests",
        "sqlite3",
        "subprocess",
    }
    for path in sorted(root.glob("execution_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not imports & forbidden


def test_phase3_public_api_does_not_export_internal_graph_helpers():
    import pastila_scout.editor.script_composer as api

    assert hasattr(api, "validate_generation_execution_plan")
    assert hasattr(api, "derive_generation_execution_eligibility")
    assert not hasattr(api, "execution_plan_violations")
    assert not hasattr(api, "_cycles")


def test_plan_and_unit_identities_include_binding_semantics():
    _, plan = _plan()
    policy = plan.failure_policy.model_copy(
        update={
            "required_output_binding_references": (),
            "optional_output_binding_references": (
                plan.expected_output_bindings[0].output_binding_id,
            ),
        }
    )
    assert (
        execution_plan_identity(plan.model_copy(update={"failure_policy": policy}))
        != plan.execution_plan_id
    )
    unit = plan.ordered_execution_units[0]
    identities = {
        execution_unit_identity(unit),
        execution_unit_identity(
            unit.model_copy(update={"expected_output_binding_reference": None})
        ),
        execution_unit_identity(
            unit.model_copy(
                update={"expected_output_binding_reference": "binding:other"}
            )
        ),
    }
    assert len(identities) == 3


@pytest.mark.parametrize(
    "field",
    (
        "execution_intent_reference",
        "generation_profile_reference",
        "generation_profile_fingerprint",
        "policy_snapshot_reference",
        "policy_snapshot_fingerprint",
        "retry_policy_reference",
        "failure_policy_reference",
        "normalized_input_fingerprint",
        "target_references",
        "instruction_references",
        "constraint_references",
        "authority_references",
        "evidence_references",
        "expected_output_binding_reference",
    ),
)
def test_every_request_link_is_reconciled(field):
    intent, plan = _plan()
    request = _request(intent, plan)
    current = getattr(request, field)
    replacement = (
        ("unrelated:value",) if isinstance(current, tuple) else "unrelated:value"
    )
    if field.endswith("fingerprint"):
        replacement = "1" * 64
    invalid = _seal(
        request.model_copy(update={field: replacement}),
        "execution_request_id",
        execution_request_identity,
    )
    issues = validate_generation_execution_request(invalid, plan, intent)
    assert any(
        item.code == "execution-request-linkage-mismatch"
        and item.field_path == (field,)
        for item in issues
    )


def test_unknown_intent_context_references_are_rejected():
    normalized = _phase2_input()
    base = _intent(normalized)
    cases = (
        (
            {"revision_request_reference": "revision:missing"},
            "execution-revision-reference-unresolved",
        ),
        (
            {"evidence_references": ("evidence:missing",)},
            "execution-evidence-reference-unresolved",
        ),
        (
            {"requested_target_references": ("beat:missing",)},
            "execution-target-reference-unresolved",
        ),
        (
            {"parent_execution_reference": "not-an-identity"},
            "execution-parent-reference-invalid",
        ),
    )
    for update, expected in cases:
        invalid = _seal(
            base.model_copy(update=update),
            "execution_intent_id",
            execution_intent_identity,
        )
        assert expected in {
            item.code
            for item in validate_generation_execution_intent(invalid, normalized)
        }


def test_binding_and_dependency_defects_block_eligibility():
    intent, plan = _plan(2)
    binding = plan.expected_output_bindings[0].model_copy(
        update={"target_reference": "beat:unowned"}
    )
    binding = binding.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(binding)}
    )
    invalid = plan.model_copy(
        update={
            "expected_output_bindings": (binding, *plan.expected_output_bindings[1:])
        }
    )
    invalid = invalid.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(invalid)}
    )
    assert not derive_generation_execution_eligibility(invalid, intent=intent).eligible
    missing = plan.model_copy(update={"dependency_declarations": ()})
    missing = missing.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(missing)}
    )
    assert "execution-dependency-declarations-mismatch" in {
        item.code for item in validate_generation_execution_plan(missing)
    }
    assert not derive_generation_execution_eligibility(missing).eligible


@pytest.mark.parametrize(
    ("field", "value", "path"),
    (
        ("operation_type", GenerationOperation.REVISION_GENERATION, "operation_type"),
        (
            "instruction_references",
            ("instruction:unrelated",),
            "instruction_references",
        ),
        ("constraint_references", ("constraint:unrelated",), "constraint_references"),
        ("authority_references", ("authority:unrelated",), "authority_references"),
        ("evidence_references", ("evidence:unrelated",), "evidence_references"),
        ("source_input_references", ("input:unrelated",), "source_input_references"),
    ),
)
def test_resealed_unit_semantics_are_reconciled(field, value, path):
    normalized = _phase2_input()
    intent, plan = _plan(normalized=normalized)
    unit = plan.ordered_execution_units[0].model_copy(update={field: value})
    unit = _seal(unit, "execution_unit_id", execution_unit_identity)
    issues = validate_generation_execution_unit(unit, intent, normalized)
    assert any(
        item.field_path == (path,) and item.artifact_reference == unit.execution_unit_id
        for item in issues
    )


@pytest.mark.parametrize(
    ("kwargs", "code", "path"),
    (
        (
            {"plan_policy_references": ("policy:unrelated",)},
            "execution-plan-policy-references-mismatch",
            "policy_references",
        ),
        (
            {"plan_authority_references": ("authority:unrelated",)},
            "execution-plan-authority-references-mismatch",
            "authority_references",
        ),
        (
            {"plan_evidence_references": ("evidence:unrelated",)},
            "execution-plan-evidence-references-mismatch",
            "evidence_references",
        ),
    ),
)
def test_fully_rebuilt_plan_collections_are_reconciled(kwargs, code, path):
    intent, plan = _plan(**kwargs)
    issues = validate_generation_execution_plan(plan, intent)
    matching = [item for item in issues if item.code == code]
    assert len(matching) == 1
    assert matching[0].field_path == (path,)
    assert matching[0].artifact_reference == plan.execution_plan_id


@pytest.mark.parametrize(
    ("state", "payload", "code"),
    (
        (
            GenerationExecutionState.CANCELLED,
            {"superseding_execution_reference": "request:other"},
            "execution-observation-cancelled-payload-invalid",
        ),
        (
            GenerationExecutionState.CANCELLED,
            {"failure_reference": "failure:arbitrary"},
            "execution-observation-cancelled-payload-invalid",
        ),
        (
            GenerationExecutionState.SUPERSEDED,
            {
                "superseding_execution_reference": "request:other",
                "failure_reference": "failure:arbitrary",
            },
            "execution-observation-superseded-payload-invalid",
        ),
        (
            GenerationExecutionState.SUCCEEDED,
            {
                "outcome_reference": "outcome:success",
                "superseding_execution_reference": "request:other",
            },
            "execution-observation-supersession-forbidden",
        ),
    ),
)
def test_lifecycle_matrix_rejects_incompatible_payloads(state, payload, code):
    values = {
        "state_observation_id": derive_identity("temporary", state.value),
        "contract_version": "generation-execution-state-observation-v1",
        "execution_request_reference": "request:one",
        "observed_state": state,
        "sequence_number": 0,
        "previous_observation_fingerprint": None,
        "outcome_reference": None,
        "failure_reference": None,
        "superseding_execution_reference": None,
        "semantic_fingerprint": ZERO,
    }
    values.update(payload)
    observation = GenerationExecutionStateObservation.model_construct(**values)
    observation = _seal(observation, "state_observation_id", state_observation_identity)
    assert code in {
        item.code
        for item in validate_generation_execution_state_observation(observation)
    }


@pytest.mark.parametrize("retry_eligible", (True, False))
def test_unclassified_failure_retry_disposition_is_rejected(retry_eligible):
    intent, plan = _plan()
    request = _request(intent, plan)
    outcome = GenerationExecutionOutcome(
        execution_outcome_id=derive_identity("temporary", "unclassified"),
        execution_request_reference=request.execution_request_id,
        execution_request_fingerprint=request.semantic_fingerprint,
        status=GenerationOutcomeStatus.FAILURE,
        failure_type=GenerationExecutionFailureType.PROVIDER_UNAVAILABLE,
        failure_code="provider-unavailable",
        retry_eligible=retry_eligible,
        applied_profile_fingerprint=request.generation_profile_fingerprint,
        applied_policy_fingerprint=request.policy_snapshot_fingerprint,
        semantic_fingerprint=ZERO,
    )
    outcome = _seal(outcome, "execution_outcome_id", execution_outcome_identity)
    issues = validate_generation_execution_outcome(outcome, request, plan)
    assert any(
        item.code == "execution-retry-failure-type-unclassified"
        and item.field_path == ("failure_type",)
        and item.artifact_reference == outcome.execution_outcome_id
        for item in issues
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("operation_type", GenerationOperation.REVISION_GENERATION),
        ("instruction_references", ("instruction:unrelated",)),
        ("constraint_references", ("constraint:unrelated",)),
        ("authority_references", ("authority:unrelated",)),
        ("evidence_references", ("evidence:unrelated",)),
        ("source_input_references", ("input:unrelated",)),
    ),
)
def test_contextual_unit_defects_make_rebuilt_plan_ineligible(field, value):
    normalized = _phase2_input()
    intent, plan = _plan(normalized=normalized, unit_updates={field: value})
    result = derive_generation_execution_eligibility(
        plan,
        intent=intent,
        normalized_input=normalized,
    )
    assert not result.eligible
    assert result.blocked_unit_references == tuple(
        item.execution_unit_id for item in plan.ordered_execution_units
    )


def _valid_outcome(status):
    intent, plan = _plan()
    request = _request(intent, plan)
    values = {
        "execution_outcome_id": derive_identity("temporary", status.value),
        "execution_request_reference": request.execution_request_id,
        "execution_request_fingerprint": request.semantic_fingerprint,
        "status": status,
        "applied_profile_fingerprint": request.generation_profile_fingerprint,
        "applied_policy_fingerprint": request.policy_snapshot_fingerprint,
        "semantic_fingerprint": ZERO,
    }
    if status is GenerationOutcomeStatus.SUCCESS:
        values.update(
            produced_output_artifact_references=("output:one",),
            satisfied_output_binding_references=(
                plan.expected_output_bindings[0].output_binding_id,
            ),
        )
    else:
        values.update(
            failure_type=GenerationExecutionFailureType.EXECUTION_TIMEOUT,
            failure_code="execution-timeout",
            retry_eligible=True,
        )
    outcome = GenerationExecutionOutcome(**values)
    return (
        _seal(outcome, "execution_outcome_id", execution_outcome_identity),
        request,
        plan,
    )


@pytest.mark.parametrize(
    ("status", "update"),
    (
        (
            GenerationOutcomeStatus.SUCCESS,
            {"failure_type": GenerationExecutionFailureType.INVALID_REQUEST},
        ),
        (GenerationOutcomeStatus.SUCCESS, {"failure_code": "invalid-request"}),
        (GenerationOutcomeStatus.FAILURE, {"failure_code": None}),
        (GenerationOutcomeStatus.FAILURE, {"failure_type": None}),
    ),
)
def test_failure_metadata_must_remain_a_pair_after_resealing(status, update):
    outcome, _, _ = _valid_outcome(status)
    invalid = _seal(
        outcome.model_copy(update=update),
        "execution_outcome_id",
        execution_outcome_identity,
    )
    issues = validate_generation_execution_outcome(invalid)
    assert tuple((item.code, item.field_path) for item in issues) == (
        ("execution-failure-metadata-pair-invalid", ("failure_type",)),
    )


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "applied_profile_fingerprint",
            "execution-outcome-profile-linkage-mismatch",
        ),
        (
            "applied_policy_fingerprint",
            "execution-outcome-policy-linkage-mismatch",
        ),
    ),
)
def test_applied_outcome_fingerprints_are_contextually_linked(field, code):
    outcome, request, plan = _valid_outcome(GenerationOutcomeStatus.SUCCESS)
    invalid = _seal(
        outcome.model_copy(update={field: "1" * 64}),
        "execution_outcome_id",
        execution_outcome_identity,
    )
    issues = validate_generation_execution_outcome(invalid, request, plan)
    assert tuple((item.code, item.field_path) for item in issues) == ((code, (field,)),)


@pytest.mark.parametrize(
    "targets",
    (
        ("target:unrelated",),
        ("target:unknown",),
        ("beat:1", "target:extra"),
    ),
)
def test_affected_targets_are_an_exact_request_subset(targets):
    outcome, request, plan = _valid_outcome(GenerationOutcomeStatus.SUCCESS)
    invalid = _seal(
        outcome.model_copy(update={"affected_target_references": targets}),
        "execution_outcome_id",
        execution_outcome_identity,
    )
    issues = validate_generation_execution_outcome(invalid, request, plan)
    assert len(issues) == 1
    assert issues[0].code == "execution-outcome-target-reference-unresolved"
    assert issues[0].field_path == ("affected_target_references",)
    assert issues[0].artifact_reference == invalid.execution_outcome_id


def _two_policy_input():
    normalized = _phase2_input()
    bundle = normalized.normalized_bundle
    authority_one = bundle.authority_artifacts[0]
    authority_two = AuthorityReference(
        authority_reference_id="authority:policy-two",
        authority_type=AuthorityLevel.STORY_ARCHITECTURE.value,
        source_reference="composition:two",
        authority_version="1.0.0",
        semantic_fingerprint=ZERO,
    )
    authority_two = authority_two.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(authority_two)}
    )
    profile_authority = AuthorityReference(
        authority_reference_id="editorial-authority:pastila-acida",
        authority_type=AuthorityLevel.EDITOR_IN_CHIEF.value,
        source_reference="pastila-acida-baseline-generation-profile",
        authority_version="1.0.0",
        semantic_fingerprint=ZERO,
    )
    profile_authority = profile_authority.model_copy(
        update={"semantic_fingerprint": semantic_fingerprint(profile_authority)}
    )

    def instruction(policy_name, target, authority_level):
        value = GenerationInstruction(
            generation_instruction_id=f"instruction:{policy_name}",
            instruction_type=GenerationInstructionType.BEAT_REALIZATION,
            target_references=(target,),
            authority_level=authority_level,
            instruction_reference=f"rule:{policy_name}",
            required=True,
            source_rule_references=(f"rule:{policy_name}",),
            instruction_fingerprint=ZERO,
        )
        return value.model_copy(
            update={"instruction_fingerprint": semantic_fingerprint(value)}
        )

    def constraint(policy_name, target):
        value = GenerationConstraint(
            generation_constraint_id=f"constraint:{policy_name}",
            constraint_type=GenerationConstraintType.STRUCTURE,
            target_references=(target,),
            severity=ConstraintSeverity.BLOCKING,
            mandatory=True,
            constraint_reference=f"rule:{policy_name}",
            source_references=(f"policy:{policy_name}",),
            constraint_fingerprint=ZERO,
        )
        return value.model_copy(
            update={"constraint_fingerprint": semantic_fingerprint(value)}
        )

    policy_one = bundle.policy_snapshots[0].model_copy(
        update={
            "resolved_generation_instructions": (
                instruction("one", "beat:1", AuthorityLevel.COMPOSITION_PLAN),
            ),
            "resolved_generation_constraints": (constraint("one", "beat:1"),),
            "policy_fingerprint": ZERO,
        }
    )
    policy_one = policy_one.model_copy(
        update={"policy_fingerprint": semantic_fingerprint(policy_one)}
    )
    policy_two = policy_one.model_copy(
        update={
            "resolved_generation_policy_id": "policy:two",
            "source_policy_reference": "source-policy:two",
            "resolved_generation_instructions": (
                instruction("two", "beat:2", AuthorityLevel.STORY_ARCHITECTURE),
            ),
            "resolved_generation_constraints": (constraint("two", "beat:2"),),
            "authority_references": (authority_two.authority_reference_id,),
            "policy_fingerprint": ZERO,
        }
    )
    policy_two = policy_two.model_copy(
        update={"policy_fingerprint": semantic_fingerprint(policy_two)}
    )
    two_policy_bundle = bundle.model_copy(
        update={
            "policy_snapshots": (policy_one, policy_two),
            "authority_artifacts": (
                authority_one,
                authority_two,
                profile_authority,
            ),
        }
    )
    result = normalize_generation_input_bundle(two_policy_bundle)
    return result, policy_one, policy_two


def _policy_one_context():
    normalized, policy_one, policy_two = _two_policy_input()
    intent = _intent(normalized).model_copy(
        update={
            "policy_snapshot_reference": policy_one.resolved_generation_policy_id,
            "policy_snapshot_fingerprint": policy_one.policy_fingerprint,
            "instruction_references": ("instruction:one",),
            "constraint_references": ("constraint:one",),
            "authority_references": ("authority:composition",),
            "requested_target_references": ("beat:1",),
        }
    )
    intent = _seal(intent, "execution_intent_id", execution_intent_identity)
    intent, plan = _plan(
        normalized=normalized,
        intent_override=intent,
        unit_updates={
            "instruction_references": intent.instruction_references,
            "constraint_references": intent.constraint_references,
            "authority_references": intent.authority_references,
            "target_references": intent.requested_target_references,
        },
    )
    return normalized, policy_one, policy_two, intent, plan, _request(intent, plan)


def test_two_policy_baseline_is_valid_through_request_and_eligibility():
    normalized, _, _, intent, plan, request = _policy_one_context()
    assert validate_generation_input_bundle(normalized.normalized_bundle).compatible
    assert validate_generation_execution_intent(intent, normalized) == ()
    assert validate_generation_execution_plan(plan, intent, normalized) == ()
    assert (
        validate_generation_execution_request(request, plan, intent, normalized) == ()
    )
    assert derive_generation_execution_eligibility(
        plan,
        intent=intent,
        requests=(request,),
        normalized_input=normalized,
    ).eligible


@pytest.mark.parametrize(
    ("update", "code", "path"),
    (
        (
            {"instruction_references": ("instruction:two",)},
            "execution-intent-instruction-policy-mismatch",
            "instruction_references",
        ),
        (
            {"constraint_references": ("constraint:two",)},
            "execution-intent-constraint-policy-mismatch",
            "constraint_references",
        ),
        (
            {"authority_references": ("authority:policy-two",)},
            "execution-intent-authority-policy-mismatch",
            "authority_references",
        ),
        (
            {"requested_target_references": ("beat:2",)},
            "execution-intent-target-policy-mismatch",
            "requested_target_references",
        ),
    ),
)
def test_intent_rejects_foreign_selected_policy_members(update, code, path):
    normalized, _, _, intent, _, _ = _policy_one_context()
    invalid = _seal(
        intent.model_copy(update=update),
        "execution_intent_id",
        execution_intent_identity,
    )
    issues = validate_generation_execution_intent(invalid, normalized)
    assert any(
        item.code == code
        and item.field_path == (path,)
        and item.artifact_reference == invalid.execution_intent_id
        for item in issues
    )


def test_reference_and_fingerprint_must_select_the_same_policy():
    normalized, policy_one, policy_two, intent, _, _ = _policy_one_context()
    for update in (
        {"policy_snapshot_fingerprint": policy_two.policy_fingerprint},
        {
            "policy_snapshot_reference": policy_two.resolved_generation_policy_id,
            "policy_snapshot_fingerprint": policy_one.policy_fingerprint,
        },
    ):
        invalid = _seal(
            intent.model_copy(update=update),
            "execution_intent_id",
            execution_intent_identity,
        )
        assert "execution-intent-selected-policy-unresolved" in {
            item.code
            for item in validate_generation_execution_intent(invalid, normalized)
        }


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "instruction_references",
            ("instruction:two",),
            "execution-unit-instruction-policy-mismatch",
        ),
        (
            "constraint_references",
            ("constraint:two",),
            "execution-unit-constraint-policy-mismatch",
        ),
        (
            "authority_references",
            ("authority:policy-two",),
            "execution-unit-authority-policy-mismatch",
        ),
        (
            "target_references",
            ("beat:2",),
            "execution-unit-target-policy-mismatch",
        ),
    ),
)
def test_unit_independently_rejects_foreign_policy_members(field, value, code):
    normalized, _, _, intent, plan, _ = _policy_one_context()
    unit = plan.ordered_execution_units[0].model_copy(update={field: value})
    unit = _seal(unit, "execution_unit_id", execution_unit_identity)
    assert code in {
        item.code
        for item in validate_generation_execution_unit(unit, intent, normalized)
    }


def test_poisoned_intent_is_rejected_transitively_and_is_ineligible():
    normalized, _, _, intent, _, _ = _policy_one_context()
    poisoned = _seal(
        intent.model_copy(update={"instruction_references": ("instruction:two",)}),
        "execution_intent_id",
        execution_intent_identity,
    )
    poisoned, plan = _plan(
        normalized=normalized,
        intent_override=poisoned,
        unit_updates={
            "instruction_references": poisoned.instruction_references,
            "constraint_references": poisoned.constraint_references,
            "authority_references": poisoned.authority_references,
            "target_references": poisoned.requested_target_references,
        },
    )
    request = _request(poisoned, plan)
    assert "execution-intent-instruction-policy-mismatch" in {
        item.code
        for item in validate_generation_execution_plan(plan, poisoned, normalized)
    }
    assert "execution-intent-instruction-policy-mismatch" in {
        item.code
        for item in validate_generation_execution_request(
            request, plan, poisoned, normalized
        )
    }
    result = derive_generation_execution_eligibility(
        plan,
        intent=poisoned,
        requests=(request,),
        normalized_input=normalized,
    )
    assert not result.eligible
    assert result.blocked_unit_references == (
        plan.ordered_execution_units[0].execution_unit_id,
    )


def test_poisoned_unit_is_rejected_by_plan_request_and_eligibility():
    normalized, _, _, intent, _, _ = _policy_one_context()
    intent, plan = _plan(
        normalized=normalized,
        intent_override=intent,
        unit_updates={
            "instruction_references": ("instruction:two",),
            "constraint_references": intent.constraint_references,
            "authority_references": intent.authority_references,
            "target_references": intent.requested_target_references,
        },
    )
    request = _request(intent, plan)
    for issues in (
        validate_generation_execution_plan(plan, intent, normalized),
        validate_generation_execution_request(request, plan, intent, normalized),
    ):
        assert "execution-unit-instruction-policy-mismatch" in {
            item.code for item in issues
        }
    result = derive_generation_execution_eligibility(
        plan,
        intent=intent,
        requests=(request,),
        normalized_input=normalized,
    )
    assert not result.eligible
    assert result.blocked_unit_references == (
        plan.ordered_execution_units[0].execution_unit_id,
    )


def test_policy_order_permutation_preserves_ownership_findings():
    normalized, _, _, intent, _, _ = _policy_one_context()
    reversed_bundle = normalized.normalized_bundle.model_copy(
        update={
            "policy_snapshots": tuple(
                reversed(normalized.normalized_bundle.policy_snapshots)
            )
        }
    )
    reversed_input = normalized.model_copy(
        update={
            "normalized_bundle": reversed_bundle,
            "normalized_fingerprint": semantic_fingerprint(reversed_bundle),
        }
    )
    poisoned = intent.model_copy(
        update={
            "normalized_generation_input_fingerprint": reversed_input.normalized_fingerprint,
            "instruction_references": ("instruction:two",),
        }
    )
    poisoned = _seal(poisoned, "execution_intent_id", execution_intent_identity)
    first = validate_generation_execution_intent(poisoned, reversed_input)
    second = validate_generation_execution_intent(poisoned, reversed_input)
    assert first == second
    assert "execution-intent-instruction-policy-mismatch" in {
        item.code for item in first
    }
