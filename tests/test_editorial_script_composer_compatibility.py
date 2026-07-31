"""Pure Phase 2 compatibility and authority tests for Module 2.9."""

import pytest

from pastila_scout.editor.script_composer import (
    PASTILA_ACIDA_GENERATION_PROFILE,
    AuthorityConflictType,
    AuthorityLevel,
    AuthorityReference,
    ConstraintSeverity,
    CustomConstraintDefinition,
    CustomInstructionDefinition,
    DomainValidationError,
    GenerationConstraint,
    GenerationInputBundle,
    GenerationInstruction,
    GenerationInstructionType,
    ProviderGenerationRequest,
    ProviderNeutralExecutionMetadata,
    ResolvedGenerationPolicySnapshot,
    RevisionAuthorityInputSnapshot,
    construct_artifact,
    construct_compatible_generation_input,
    derive_identity,
    normalize_generation_input_bundle,
    provider_request_identity,
    require_compatible_generation_input,
    semantic_fingerprint,
    validate_artifact,
    validate_generation_input_bundle,
)
from pastila_scout.editor.script_composer.compatibility import _add_conflict

ZERO = "0" * 64
ONE = "1" * 64


def _seal(value, field):
    return value.model_copy(update={field: semantic_fingerprint(value)})


def _authority(identity="editorial-authority:pastila-acida", *, source="source:one"):
    return _seal(
        AuthorityReference(
            authority_reference_id=identity,
            authority_type=AuthorityLevel.COMPOSITION_PLAN.value,
            source_reference=source,
            authority_version="1.0.0",
            semantic_fingerprint=ZERO,
        ),
        "semantic_fingerprint",
    )


def _instruction(identity="instruction:one", *, reference="instruction-source:one"):
    return _seal(
        GenerationInstruction(
            generation_instruction_id=identity,
            instruction_type=GenerationInstructionType.BEAT_REALIZATION,
            target_references=("beat:one",),
            authority_level=AuthorityLevel.COMPOSITION_PLAN,
            instruction_reference=reference,
            required=True,
            source_rule_references=("rule:one",),
            instruction_fingerprint=ZERO,
        ),
        "instruction_fingerprint",
    )


def _constraint(
    identity="constraint:one",
    *,
    reference="constraint-source:one",
    target="beat:one",
    prohibited=(),
):
    return _seal(
        GenerationConstraint(
            generation_constraint_id=identity,
            constraint_type="factual",
            target_references=(target,),
            severity=ConstraintSeverity.BLOCKING,
            mandatory=True,
            constraint_reference=reference,
            prohibited_outcomes=prohibited,
            source_references=("policy-source:one",),
            constraint_fingerprint=ZERO,
        ),
        "constraint_fingerprint",
    )


def _policy(
    identity="policy:one",
    *,
    source="policy-source:one",
    instructions=(),
    constraints=(),
):
    return _seal(
        ResolvedGenerationPolicySnapshot(
            resolved_generation_policy_id=identity,
            policy_version="1.0.0",
            source_policy_reference=source,
            source_policy_fingerprint=ONE,
            resolved_generation_instructions=instructions,
            resolved_generation_constraints=constraints,
            authority_references=("editorial-authority:pastila-acida",),
            policy_fingerprint=ZERO,
        ),
        "policy_fingerprint",
    )


def _bundle(**updates):
    values = {
        "generation_input_bundle_id": "compatibility-input:one",
        "generation_profiles": (PASTILA_ACIDA_GENERATION_PROFILE,),
        "policy_snapshots": (_policy(),),
        "authority_artifacts": (_authority(),),
    }
    values.update(updates)
    return GenerationInputBundle(**values)


def _provider_request():
    metadata = ProviderNeutralExecutionMetadata(
        execution_policy_reference="execution-policy:one",
        response_schema_reference="schema:one",
        reproducibility_policy_reference="reproducibility:one",
    )
    request = ProviderGenerationRequest(
        provider_generation_request_id=derive_identity(
            "provider-generation-request", "temporary"
        ),
        request_version="1.0.0",
        target_episode_reference="episode:one",
        target_segment_references=("segment:one",),
        target_beat_references=("beat:one",),
        generation_profile_reference=(
            PASTILA_ACIDA_GENERATION_PROFILE.generation_profile_id
        ),
        generation_profile_fingerprint=PASTILA_ACIDA_GENERATION_PROFILE.profile_fingerprint,
        composition_plan_reference="composition:one",
        composition_plan_fingerprint=ONE,
        authority_references=("editorial-authority:pastila-acida",),
        output_schema_identity="schema:one",
        prompt_template_identity_reference="prompt:one",
        execution_policy_reference="execution-policy:one",
        provider_neutral_execution_metadata=metadata,
        request_fingerprint=ZERO,
    )
    request = request.model_copy(
        update={"provider_generation_request_id": provider_request_identity(request)}
    )
    return _seal(request, "request_fingerprint")


def test_valid_bundle_is_compatible():
    result = validate_generation_input_bundle(_bundle())
    assert result.compatible
    assert result.issues == ()


def test_missing_required_artifacts_are_deterministic_issues():
    result = validate_generation_input_bundle(
        GenerationInputBundle(generation_input_bundle_id="compatibility-input:empty")
    )
    assert [issue.field_reference for issue in result.issues] == [
        "authority_artifacts",
        "generation_profiles",
        "policy_snapshots",
    ]


def test_duplicate_authority_and_profile_are_rejected():
    authority = _authority()
    profile = PASTILA_ACIDA_GENERATION_PROFILE
    result = validate_generation_input_bundle(
        _bundle(
            authority_artifacts=(authority, authority),
            generation_profiles=(profile, profile),
        )
    )
    assert {issue.code for issue in result.issues} >= {
        "duplicate-authority",
        "duplicate-generation-profile",
    }
    assert result.authority_conflicts.conflicts


def test_duplicate_provider_request_and_conflicting_profile_are_rejected():
    request = _provider_request()
    profile = PASTILA_ACIDA_GENERATION_PROFILE
    conflicting = profile.model_copy(update={"voice_reference": "voice:other"})
    conflicting = _seal(conflicting, "profile_fingerprint")
    result = validate_generation_input_bundle(
        _bundle(
            provider_requests=(request, request),
            generation_profiles=(profile, conflicting),
        )
    )
    assert {issue.code for issue in result.issues} >= {
        "duplicate-provider-request",
        "conflicting-generation-profile",
    }


def test_policy_source_conflict_is_reported_without_resolution():
    first = _policy("policy:one")
    second = _policy("policy:two", instructions=(_instruction(),))
    result = validate_generation_input_bundle(_bundle(policy_snapshots=(first, second)))
    assert "conflicting-policy-snapshots" in {issue.code for issue in result.issues}
    conflict = next(
        conflict
        for conflict in result.authority_conflicts.conflicts
        if conflict.conflict_type.value == "conflicting_policy"
    )
    assert conflict.authority_references == ("editorial-authority:pastila-acida",)
    assert conflict.target_references == ("policy-source:one",)


def test_conflicting_instructions_and_constraints_are_reported():
    instruction_one = _instruction()
    instruction_two = _instruction(reference="instruction-source:two")
    constraint_one = _constraint()
    constraint_two = _constraint(reference="constraint-source:two")
    policy_one = _policy(
        "policy:one",
        source="policy-source:one",
        instructions=(instruction_one,),
        constraints=(constraint_one,),
    )
    policy_two = _policy(
        "policy:two",
        source="policy-source:two",
        instructions=(instruction_two,),
        constraints=(constraint_two,),
    )
    result = validate_generation_input_bundle(
        _bundle(policy_snapshots=(policy_one, policy_two))
    )
    codes = {issue.code for issue in result.issues}
    assert "conflicting-generation-instruction" in codes
    assert "conflicting-generation-constraint" in codes
    assert "contradictory-generation-constraints" not in codes


def test_duplicate_custom_identifiers_and_unknown_custom_reference_are_rejected():
    definition = CustomInstructionDefinition(
        custom_identifier="custom:spoken-hook",
        instruction_reference="instruction-definition:one",
        authority_level=AuthorityLevel.COMPOSITION_PLAN,
        authority_references=("editorial-authority:pastila-acida",),
    )
    policy = _policy(instructions=(_instruction(reference="custom:missing-hook"),))
    result = validate_generation_input_bundle(
        _bundle(
            policy_snapshots=(policy,),
            custom_instruction_definitions=(definition, definition),
        )
    )
    assert {issue.code for issue in result.issues} >= {
        "custom-instruction-definition-missing",
        "custom-instruction-identifier-duplicate",
    }


def test_revision_snapshot_requires_known_profile_and_policy():
    snapshot = RevisionAuthorityInputSnapshot(
        **{name: ONE for name in RevisionAuthorityInputSnapshot.model_fields}
    )
    result = validate_generation_input_bundle(
        _bundle(revision_authority_snapshots=(snapshot,))
    )
    assert {issue.code for issue in result.issues} >= {
        "revision-profile-incompatible",
        "revision-policy-incompatible",
    }


def test_authority_level_requires_compatible_authority_artifact():
    authority = _authority()
    incompatible = authority.model_copy(update={"authority_type": "legal_precision"})
    policy = _policy(instructions=(_instruction(),))
    result = validate_generation_input_bundle(
        _bundle(authority_artifacts=(incompatible,), policy_snapshots=(policy,))
    )
    assert "incompatible-authority-level" in {issue.code for issue in result.issues}


def test_normalization_is_deterministic_and_deduplicates_exact_artifacts():
    profile = PASTILA_ACIDA_GENERATION_PROFILE
    policy_one = _policy("policy:one", source="policy-source:one")
    policy_two = _policy("policy:two", source="policy-source:two")
    first = _bundle(
        generation_profiles=(profile, profile),
        policy_snapshots=(policy_two, policy_one, policy_two),
    )
    second = _bundle(
        generation_profiles=(profile,),
        policy_snapshots=(policy_one, policy_two),
    )
    normalized_first = normalize_generation_input_bundle(first)
    normalized_second = normalize_generation_input_bundle(second)
    assert normalized_first.normalized_bundle == normalized_second.normalized_bundle
    assert (
        normalized_first.normalized_fingerprint
        == normalized_second.normalized_fingerprint
    )
    assert normalized_first.changed
    assert not normalized_second.changed


def test_strict_compatibility_raises_stable_domain_errors():
    bundle = GenerationInputBundle(
        generation_input_bundle_id="compatibility-input:empty"
    )
    with pytest.raises(DomainValidationError) as caught:
        require_compatible_generation_input(bundle)
    assert [issue.code for issue in caught.value.issues] == [
        "required-artifact-missing",
        "required-artifact-missing",
        "required-artifact-missing",
    ]


def test_public_construction_and_explicit_compatibility_share_issue_codes():
    bundle = GenerationInputBundle(
        generation_input_bundle_id="compatibility-input:empty"
    )
    explicit_codes = tuple(
        issue.code for issue in validate_generation_input_bundle(bundle).issues
    )
    with pytest.raises(DomainValidationError) as caught:
        construct_compatible_generation_input(bundle.model_dump())
    assert tuple(issue.code for issue in caught.value.issues) == explicit_codes


@pytest.mark.parametrize(
    ("field_name", "artifact"),
    (
        (
            "generation_profiles",
            PASTILA_ACIDA_GENERATION_PROFILE.model_copy(
                update={"profile_fingerprint": ONE}
            ),
        ),
        ("policy_snapshots", _policy().model_copy(update={"policy_fingerprint": ONE})),
    ),
)
def test_nested_phase1_fingerprint_corruption_is_rejected(field_name, artifact):
    result = validate_generation_input_bundle(_bundle(**{field_name: (artifact,)}))
    issue = next(
        issue for issue in result.issues if issue.code == "fingerprint-mismatch"
    )
    assert issue.field_path[:2] == (field_name, 0)


def test_resealed_parent_does_not_hide_corrupt_nested_instruction():
    corrupt = _instruction().model_copy(update={"instruction_reference": "changed"})
    policy = _policy(instructions=(corrupt,))
    result = validate_generation_input_bundle(_bundle(policy_snapshots=(policy,)))
    assert "fingerprint-mismatch" in {issue.code for issue in result.issues}


def test_provider_request_identity_and_profile_linkage_are_enforced():
    valid = _provider_request()
    assert validate_generation_input_bundle(
        _bundle(provider_requests=(valid,))
    ).compatible

    corrupt_identity = valid.model_copy(
        update={"provider_generation_request_id": "provider-generation-request:wrong"}
    )
    corrupt_identity = _seal(corrupt_identity, "request_fingerprint")
    identity_result = validate_generation_input_bundle(
        _bundle(provider_requests=(corrupt_identity,))
    )
    assert "identity-mismatch" in {issue.code for issue in identity_result.issues}

    unknown = valid.model_copy(
        update={"generation_profile_reference": "profile:unknown"}
    )
    unknown = _seal(unknown, "request_fingerprint")
    unknown_result = validate_generation_input_bundle(
        _bundle(provider_requests=(unknown,))
    )
    assert "provider-profile-reference-unknown" in {
        issue.code for issue in unknown_result.issues
    }

    mismatch = valid.model_copy(update={"generation_profile_fingerprint": ONE})
    mismatch = mismatch.model_copy(
        update={"provider_generation_request_id": provider_request_identity(mismatch)}
    )
    mismatch = _seal(mismatch, "request_fingerprint")
    mismatch_result = validate_generation_input_bundle(
        _bundle(provider_requests=(mismatch,))
    )
    assert "provider-profile-fingerprint-mismatch" in {
        issue.code for issue in mismatch_result.issues
    }


@pytest.mark.parametrize(
    ("update", "code", "path"),
    (
        (
            {"generation_instruction_references": ("instruction:missing",)},
            "provider-instruction-references-mismatch",
            "generation_instruction_references",
        ),
        (
            {"generation_constraint_references": ("constraint:missing",)},
            "provider-constraint-references-mismatch",
            "generation_constraint_references",
        ),
    ),
)
def test_resealed_provider_request_reference_mismatch_cannot_bypass_validation(
    update, code, path
):
    request = _seal(
        _provider_request().model_copy(update=update), "request_fingerprint"
    )

    direct_issue = next(
        issue for issue in validate_artifact(request) if issue.code == code
    )
    assert direct_issue.artifact_reference == request.provider_generation_request_id
    assert direct_issue.field_path == (path,)

    copied_bundle = _bundle().model_copy(update={"provider_requests": (request,)})
    nested_issue = next(
        issue
        for issue in validate_generation_input_bundle(copied_bundle).issues
        if issue.code == code
    )
    assert nested_issue.artifact_reference == request.provider_generation_request_id
    assert nested_issue.field_path == ("provider_requests", 0, path)

    with pytest.raises(DomainValidationError) as caught:
        construct_artifact(ProviderGenerationRequest, request.model_dump())
    constructed_issue = next(
        issue for issue in caught.value.issues if issue.code == code
    )
    assert (
        constructed_issue.artifact_reference == request.provider_generation_request_id
    )
    assert constructed_issue.field_path == (path,)


def test_custom_definitions_require_known_authority_references():
    instruction = CustomInstructionDefinition(
        custom_identifier="custom:instruction",
        instruction_reference="definition:instruction",
        authority_level=AuthorityLevel.COMPOSITION_PLAN,
        authority_references=("authority:missing",),
    )
    constraint = CustomConstraintDefinition(
        custom_identifier="custom:constraint",
        constraint_reference="definition:constraint",
        authority_references=("authority:missing",),
    )
    result = validate_generation_input_bundle(
        _bundle(
            custom_instruction_definitions=(instruction,),
            custom_constraint_definitions=(constraint,),
        )
    )
    assert [issue.code for issue in result.issues].count(
        "custom-definition-authority-missing"
    ) == 2

    valid_instruction = instruction.model_copy(
        update={"authority_references": ("editorial-authority:pastila-acida",)}
    )
    valid_constraint = constraint.model_copy(
        update={"authority_references": ("editorial-authority:pastila-acida",)}
    )
    valid_result = validate_generation_input_bundle(
        _bundle(
            custom_instruction_definitions=(valid_instruction,),
            custom_constraint_definitions=(valid_constraint,),
        )
    )
    assert valid_result.compatible


def test_distinct_rules_on_same_target_are_not_implicitly_conflicting():
    first_instruction = _instruction("instruction:one", reference="rule:first")
    second_instruction = _instruction("instruction:two", reference="rule:second")
    first_constraint = _constraint("constraint:one", reference="constraint:first")
    second_constraint = _constraint("constraint:two", reference="constraint:second")
    result = validate_generation_input_bundle(
        _bundle(
            policy_snapshots=(
                _policy(
                    instructions=(first_instruction, second_instruction),
                    constraints=(first_constraint, second_constraint),
                ),
            )
        )
    )
    assert result.compatible


def test_explicit_cross_reference_prohibition_creates_one_contextual_conflict():
    first = _constraint(
        "constraint:one",
        reference="constraint:first",
        prohibited=("constraint:second",),
    )
    second = _constraint("constraint:two", reference="constraint:second")
    policy = _policy(constraints=(first, second, first, second))
    result = validate_generation_input_bundle(_bundle(policy_snapshots=(policy,)))
    contradictions = [
        item
        for item in result.authority_conflicts.conflicts
        if item.issue_code == "contradictory-generation-constraints"
    ]
    assert len(contradictions) == 1
    assert contradictions[0].target_references == ("beat:one",)
    assert contradictions[0].field_path == (
        "resolved_generation_constraints",
        "prohibited_outcomes",
    )


def test_repeated_equivalent_conflict_has_canonical_references_and_identity():
    first = _constraint(
        "constraint:one",
        reference="constraint:first",
        prohibited=("constraint:second",),
    )
    second = _constraint("constraint:two", reference="constraint:second")

    def contradiction(constraints):
        result = validate_generation_input_bundle(
            _bundle(policy_snapshots=(_policy(constraints=constraints),))
        )
        matches = [
            item
            for item in result.authority_conflicts.conflicts
            if item.issue_code == "contradictory-generation-constraints"
        ]
        assert len(matches) == 1
        return matches[0]

    single = contradiction((first, second))
    repeated = contradiction((first, second, first, second))
    permuted = contradiction((second, first, second, first))
    expected = ("constraint:one", "constraint:two")
    assert single.artifact_references == expected
    assert repeated.artifact_references == expected
    assert permuted.artifact_references == expected
    assert single.authority_conflict_id == repeated.authority_conflict_id
    assert single.authority_conflict_id == permuted.authority_conflict_id


def test_conflict_field_path_remains_part_of_identity():
    artifacts = (_constraint("constraint:one"), _constraint("constraint:two"))
    first_path = []
    second_path = []
    for output, path in (
        (first_path, ("policy", "first")),
        (second_path, ("policy", "second")),
    ):
        _add_conflict(
            "conflicting-constraints",
            artifacts,
            output,
            AuthorityConflictType.CONFLICTING_CONSTRAINT,
            target_references=("beat:one", "beat:one"),
            field_path=path,
        )
    assert first_path[0].target_references == ("beat:one",)
    assert first_path[0].authority_conflict_id != second_path[0].authority_conflict_id


def test_equal_conflicts_on_different_targets_have_distinct_identities():
    constraints = []
    for target in ("beat:one", "beat:two"):
        constraints.extend(
            (
                _constraint(
                    f"constraint:{target}:first",
                    reference="constraint:first",
                    target=target,
                    prohibited=("constraint:second",),
                ),
                _constraint(
                    f"constraint:{target}:second",
                    reference="constraint:second",
                    target=target,
                ),
            )
        )
    result = validate_generation_input_bundle(
        _bundle(policy_snapshots=(_policy(constraints=tuple(constraints)),))
    )
    conflicts = [
        item
        for item in result.authority_conflicts.conflicts
        if item.issue_code == "contradictory-generation-constraints"
    ]
    assert len(conflicts) == 2
    assert len({item.authority_conflict_id for item in conflicts}) == 2
    assert {item.target_references for item in conflicts} == {
        ("beat:one",),
        ("beat:two",),
    }


def test_normalization_rejects_valid_corrupt_canonical_collision_in_any_order():
    valid = PASTILA_ACIDA_GENERATION_PROFILE
    corrupt = valid.model_copy(update={"profile_fingerprint": ONE})
    issue_sets = []
    for profiles in ((valid, corrupt), (corrupt, valid)):
        with pytest.raises(DomainValidationError) as caught:
            normalize_generation_input_bundle(_bundle(generation_profiles=profiles))
        issue_sets.append(
            tuple((i.code, i.artifact_reference) for i in caught.value.issues)
        )
    assert issue_sets[0] == issue_sets[1]
    assert issue_sets[0][0][0] == "fingerprint-mismatch"


def test_normalization_is_idempotent_across_collection_permutations():
    policies = (
        _policy("policy:three", source="source:three"),
        _policy("policy:one", source="source:one"),
        _policy("policy:two", source="source:two"),
    )
    results = [
        normalize_generation_input_bundle(_bundle(policy_snapshots=order))
        for order in (
            policies,
            tuple(reversed(policies)),
            (policies[1], policies[2], policies[0]),
        )
    ]
    assert len({item.normalized_fingerprint for item in results}) == 1
    second_pass = normalize_generation_input_bundle(results[0].normalized_bundle)
    assert not second_pass.changed
    assert second_pass.normalized_fingerprint == results[0].normalized_fingerprint
