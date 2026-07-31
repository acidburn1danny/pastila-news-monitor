"""Phase 4.1 structural draft contract tests."""

import json

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    DraftExecutionPlanReference,
    DraftSection,
    DraftSectionKind,
    DraftStatus,
    DraftStructure,
    DraftValidationContext,
    NormalizedInputDraftScope,
    StructuralMetadataEntry,
    TransitionSlot,
    canonical_json,
    construct_draft_structure,
    draft_section_identity,
    draft_semantic_fingerprint,
    draft_structure_identity,
    require_valid_draft_structure,
    transition_slot_identity,
    validate_draft_structure,
)

ZERO = "0" * 64
DUMMY_SECTION_ID = f"scout:draft-section:{ZERO}"
DUMMY_TRANSITION_ID = f"scout:draft-transition:{ZERO}"
DUMMY_DRAFT_ID = f"scout:draft-structure:{ZERO}"


def _seal(value, identity_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": draft_semantic_fingerprint(value)})


def _section(index: int, kind=DraftSectionKind.INTRO) -> DraftSection:
    value = DraftSection(
        identity=DUMMY_SECTION_ID,
        fingerprint=ZERO,
        section_reference=f"section:{index}",
        order_index=index,
        section_kind=kind,
        purpose=f"purpose:{index}",
        required_claim_references=(f"claim:{index}",),
        required_evidence_references=(f"evidence:{index}",),
        transition_before="transition:0-1" if index == 1 else None,
        transition_after="transition:0-1" if index == 0 else None,
    )
    return _seal(value, draft_section_identity)


def _transition() -> TransitionSlot:
    value = TransitionSlot(
        identity=DUMMY_TRANSITION_ID,
        fingerprint=ZERO,
        transition_reference="transition:0-1",
        from_section="section:0",
        to_section="section:1",
        required=True,
    )
    return _seal(value, transition_slot_identity)


def _draft(*, status=DraftStatus.VALIDATED) -> DraftStructure:
    sections = (_section(0), _section(1, DraftSectionKind.CONCLUSION))
    value = DraftStructure(
        identity=DUMMY_DRAFT_ID,
        fingerprint=ZERO,
        title="Structură știri",
        normalized_input_reference="normalized-input:one",
        execution_plan_reference="execution-plan:one",
        execution_plan_fingerprint="1" * 64,
        section_references=tuple(item.section_reference for item in sections),
        sections=sections,
        transitions=(_transition(),),
        status=status,
    )
    return _seal(value, draft_structure_identity)


def _context() -> DraftValidationContext:
    return DraftValidationContext(
        normalized_input_scopes=(
            NormalizedInputDraftScope(
                normalized_input_reference="normalized-input:one",
                execution_plans=(
                    DraftExecutionPlanReference(
                        execution_plan_reference="execution-plan:one",
                        execution_plan_fingerprint="1" * 64,
                    ),
                ),
                claim_references=("claim:0", "claim:1"),
                evidence_references=("evidence:0", "evidence:1"),
            ),
        )
    )


def _codes(draft, context=None):
    return {item.code for item in validate_draft_structure(draft, context)}


def test_valid_draft_is_immutable_and_contextually_valid():
    draft = _draft()
    assert validate_draft_structure(draft, _context()) == ()
    with pytest.raises(ValidationError):
        draft.status = DraftStatus.PLANNED


def test_duplicate_sections_and_order_are_rejected():
    draft = _draft()
    duplicate = draft.sections[1].model_copy(
        update={"section_reference": "section:0", "order_index": 0}
    )
    changed = draft.model_copy(
        update={
            "sections": (draft.sections[0], duplicate),
            "section_references": ("section:0", "section:0"),
        }
    )
    codes = _codes(changed)
    assert "draft-duplicate-section-reference" in codes
    assert "draft-duplicate-section-order" in codes


def test_invalid_order_and_section_reference_order_are_rejected():
    draft = _draft()
    second = draft.sections[1].model_copy(update={"order_index": 2})
    changed = draft.model_copy(
        update={
            "sections": (draft.sections[0], second),
            "section_references": ("section:1", "section:0"),
        }
    )
    codes = _codes(changed)
    assert "draft-invalid-section-order" in codes
    assert "draft-section-reference-order-mismatch" in codes


def test_missing_execution_plan_is_contextual_failure():
    context = DraftValidationContext(
        normalized_input_scopes=(
            NormalizedInputDraftScope(
                normalized_input_reference="normalized-input:one"
            ),
        )
    )
    assert "draft-missing-execution-plan-reference" in _codes(_draft(), context)


def test_invalid_section_kind_and_status_are_rejected():
    with pytest.raises(ValidationError) as kind_error:
        DraftSection.model_validate(
            {**_section(0).model_dump(), "section_kind": "invented"}
        )
    assert "draft-unknown-section-kind" in str(kind_error.value)
    with pytest.raises(ValidationError):
        DraftStructure.model_validate({**_draft().model_dump(), "status": "running"})
    custom = DraftSection.model_validate(
        {**_section(0).model_dump(), "section_kind": "custom:explainer"}
    )
    assert custom.section_kind == "custom:explainer"


def test_duplicate_transition_and_fingerprint_are_rejected():
    draft = _draft()
    changed = draft.model_copy(update={"transitions": (draft.transitions[0],) * 2})
    codes = _codes(changed)
    assert "draft-duplicate-transition-identity" in codes
    assert "draft-duplicate-transition-transition-reference" in codes
    assert "draft-duplicate-transition-fingerprint" in codes
    assert "draft-duplicate-fingerprint" in codes


def test_self_and_orphan_transitions_are_rejected():
    draft = _draft()
    self_transition = draft.transitions[0].model_copy(
        update={"to_section": "section:0"}
    )
    assert "draft-self-transition" in _codes(
        draft.model_copy(update={"transitions": (self_transition,)})
    )
    orphan = draft.transitions[0].model_copy(update={"to_section": "section:missing"})
    assert "draft-orphan-transition" in _codes(
        draft.model_copy(update={"transitions": (orphan,)})
    )


def test_missing_claim_and_evidence_references_are_rejected():
    context = DraftValidationContext(
        normalized_input_scopes=(
            NormalizedInputDraftScope(
                normalized_input_reference="normalized-input:one",
                execution_plans=(
                    DraftExecutionPlanReference(
                        execution_plan_reference="execution-plan:one",
                        execution_plan_fingerprint="1" * 64,
                    ),
                ),
            ),
        )
    )
    codes = _codes(_draft(), context)
    assert "draft-missing-claim-reference" in codes
    assert "draft-missing-evidence-reference" in codes


def test_duplicate_claim_and_evidence_classification_is_rejected():
    draft = _draft()
    changed_section = draft.sections[0].model_copy(
        update={
            "optional_claim_references": draft.sections[0].required_claim_references,
            "optional_evidence_references": (
                *draft.sections[0].required_evidence_references,
                *draft.sections[0].required_evidence_references,
            ),
        }
    )
    changed = draft.model_copy(
        update={"sections": (changed_section, draft.sections[1])}
    )
    codes = _codes(changed)
    assert "draft-duplicate-claim-reference" in codes
    assert "draft-duplicate-evidence-reference" in codes


def test_identity_fingerprint_and_canonical_serialization_are_deterministic():
    first = _draft()
    second = _draft()
    assert first.identity == second.identity
    assert first.fingerprint == second.fingerprint
    assert first.canonical_json() == second.canonical_json()
    assert json.loads(canonical_json(first))["title"] == "Structură știri"
    assert canonical_json(first).encode("utf-8").decode("utf-8") == canonical_json(
        first
    )


def test_canonical_collection_order_is_deterministic():
    payload = _draft().model_dump()
    payload["sections"] = tuple(reversed(payload["sections"]))
    parsed = DraftStructure.model_validate(payload)
    assert tuple(item.order_index for item in parsed.sections) == (0, 1)
    assert parsed.canonical_json() == _draft().canonical_json()


def test_model_copy_semantic_mutation_is_detected():
    changed = _draft().model_copy(update={"title": "Altă structură"})
    assert {"draft-identity-mismatch", "draft-fingerprint-mismatch"} <= _codes(changed)


def test_construct_and_require_raise_stable_domain_errors():
    draft = _draft()
    assert construct_draft_structure(draft.model_dump(), _context()) == draft
    invalid = draft.model_copy(
        update={"execution_plan_reference": "execution-plan:missing"}
    )
    with pytest.raises(DomainValidationError) as error:
        require_valid_draft_structure(invalid, _context())
    assert "draft-missing-execution-plan-reference" in {
        item.code for item in error.value.issues
    }


def test_no_text_generation_fields_exist_in_public_models():
    forbidden = {"text", "paragraphs", "sentences", "prompt", "provider"}
    for model in (DraftStructure, DraftSection, TransitionSlot):
        assert forbidden.isdisjoint(model.model_fields)


def _seal_draft(value):
    return _seal(value, draft_structure_identity)


def _replace_section(draft, index, section):
    sections = list(draft.sections)
    sections[index] = section
    return _seal_draft(draft.model_copy(update={"sections": tuple(sections)}))


def _second_scope():
    return NormalizedInputDraftScope(
        normalized_input_reference="normalized-input:two",
        claim_references=("claim:foreign",),
        evidence_references=("evidence:foreign",),
        execution_plans=(
            DraftExecutionPlanReference(
                execution_plan_reference="execution-plan:two",
                execution_plan_fingerprint="2" * 64,
            ),
        ),
    )


def _two_scope_context():
    return DraftValidationContext(
        normalized_input_scopes=(
            _context().normalized_input_scopes[0],
            _second_scope(),
        )
    )


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    (
        ("section_kind", "unknown-kind", "draft-unknown-section-kind"),
        ("section_kind", "custom:BAD", "draft-unknown-section-kind"),
        ("purpose", "   ", "draft-blank-purpose"),
        ("order_index", -1, "draft-invalid-reconstructed-model-contract"),
        (
            "required_claim_references",
            (7,),
            "draft-invalid-reconstructed-model-contract",
        ),
    ),
)
def test_explicit_validation_reconstructs_copied_section(field, value, expected_code):
    draft = _draft()
    section = _seal(
        draft.sections[0].model_copy(update={field: value}),
        draft_section_identity,
    )
    changed = _replace_section(draft, 0, section)
    assert expected_code in _codes(changed, _context())


def test_explicit_validation_reconstructs_status_transition_and_metadata():
    draft = _draft()
    bad_status = _seal_draft(draft.model_copy(update={"status": "executing"}))
    assert "draft-invalid-reconstructed-model-contract" in _codes(
        bad_status, _context()
    )
    bad_title = _seal_draft(draft.model_copy(update={"title": "   "}))
    assert "draft-blank-title" in _codes(bad_title, _context())

    transition = _seal(
        draft.transitions[0].model_copy(update={"required": "yes"}),
        transition_slot_identity,
    )
    bad_transition = _seal_draft(
        draft.model_copy(update={"transitions": (transition,)})
    )
    assert "draft-invalid-reconstructed-model-contract" in _codes(
        bad_transition, _context()
    )

    metadata = StructuralMetadataEntry(
        key="structural_label", value="intro"
    ).model_copy(update={"key": "provider"})
    section = _seal(
        draft.sections[0].model_copy(update={"metadata": (metadata,)}),
        draft_section_identity,
    )
    bad_metadata = _replace_section(draft, 0, section)
    assert "draft-prohibited-metadata-key" in _codes(bad_metadata, _context())

    metadata = StructuralMetadataEntry(
        key="structural_label", value="intro"
    ).model_copy(update={"value": "prompt text"})
    section = _seal(
        draft.sections[0].model_copy(update={"metadata": (metadata,)}),
        draft_section_identity,
    )
    bad_metadata_value = _replace_section(draft, 0, section)
    assert "draft-prohibited-metadata-value" in _codes(bad_metadata_value, _context())


def test_fully_rebuilt_valid_semantic_mutation_passes():
    draft = _draft()
    section = _seal(
        draft.sections[0].model_copy(
            update={
                "section_kind": "custom:explainer",
                "purpose": "provide chronology",
            }
        ),
        draft_section_identity,
    )
    changed = _replace_section(draft, 0, section)
    assert validate_draft_structure(changed, _context()) == ()


def test_context_copies_mutable_caller_inputs_deeply():
    claims = ["claim:0", "claim:1"]
    plans = [
        {
            "execution_plan_reference": "execution-plan:one",
            "execution_plan_fingerprint": "1" * 64,
        }
    ]
    scope_payload = {
        "normalized_input_reference": "normalized-input:one",
        "claim_references": claims,
        "evidence_references": {"evidence:0", "evidence:1"},
        "execution_plans": plans,
    }
    scopes = [scope_payload]
    context = DraftValidationContext(normalized_input_scopes=scopes)
    claims.append("claim:mutated")
    plans.append(
        {
            "execution_plan_reference": "execution-plan:mutated",
            "execution_plan_fingerprint": "3" * 64,
        }
    )
    scopes.append(_second_scope().model_dump())
    scope_payload["normalized_input_reference"] = "normalized-input:mutated"
    assert context == _context()
    assert isinstance(context.normalized_input_scopes, tuple)
    assert isinstance(context.normalized_input_scopes[0].claim_references, tuple)
    assert isinstance(context.normalized_input_scopes[0].execution_plans, tuple)


@pytest.mark.parametrize(
    "payload",
    (
        {
            "normalized_input_scopes": (
                {
                    "normalized_input_reference": "normalized-input:one",
                    "claim_references": ("claim:0", "claim:0"),
                },
            )
        },
        {
            "normalized_input_scopes": (
                {
                    "normalized_input_reference": "normalized-input:one",
                    "execution_plans": (
                        {
                            "execution_plan_reference": "execution-plan:one",
                            "execution_plan_fingerprint": "1" * 64,
                        },
                        {
                            "execution_plan_reference": "execution-plan:one",
                            "execution_plan_fingerprint": "1" * 64,
                        },
                    ),
                },
            )
        },
        {
            "normalized_input_scopes": (
                {
                    "normalized_input_reference": "normalized-input:one",
                    "evidence_references": ("evidence:0", "evidence:0"),
                },
            )
        },
        {
            "normalized_input_scopes": (
                {
                    "normalized_input_reference": "normalized-input:one",
                    "execution_plans": (
                        {
                            "execution_plan_reference": "execution-plan:one",
                            "execution_plan_fingerprint": "1" * 64,
                        },
                        {
                            "execution_plan_reference": "execution-plan:one",
                            "execution_plan_fingerprint": "2" * 64,
                        },
                    ),
                },
            )
        },
        {
            "normalized_input_scopes": (
                {"normalized_input_reference": "normalized-input:one"},
                {"normalized_input_reference": "normalized-input:one"},
            )
        },
    ),
)
def test_duplicate_context_identities_are_rejected(payload):
    with pytest.raises(ValidationError) as error:
        DraftValidationContext.model_validate(payload)
    assert "draft-duplicate-context-" in str(error.value)


def test_duplicate_context_rejection_is_permutation_invariant():
    plans = (
        {
            "execution_plan_reference": "execution-plan:one",
            "execution_plan_fingerprint": "1" * 64,
        },
        {
            "execution_plan_reference": "execution-plan:one",
            "execution_plan_fingerprint": "2" * 64,
        },
    )
    outcomes = []
    for ordering in (plans, tuple(reversed(plans))):
        with pytest.raises(ValidationError) as error:
            NormalizedInputDraftScope(
                normalized_input_reference="normalized-input:one",
                execution_plans=ordering,
            )
        outcomes.append(tuple(item["type"] for item in error.value.errors()))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    ("section_update", "expected_code"),
    (
        (
            {"required_claim_references": ("claim:foreign",)},
            "draft-cross-normalized-input-claim-ownership",
        ),
        (
            {"required_evidence_references": ("evidence:foreign",)},
            "draft-cross-normalized-input-evidence-ownership",
        ),
    ),
)
def test_cross_normalized_input_article_reference_ownership_fails(
    section_update, expected_code
):
    draft = _draft()
    section = _seal(
        draft.sections[0].model_copy(update=section_update), draft_section_identity
    )
    changed = _replace_section(draft, 0, section)
    assert expected_code in _codes(changed, _two_scope_context())


def test_cross_normalized_input_execution_plan_ownership_fails():
    draft = _seal_draft(
        _draft().model_copy(
            update={
                "execution_plan_reference": "execution-plan:two",
                "execution_plan_fingerprint": "2" * 64,
            }
        )
    )
    assert "draft-cross-normalized-input-execution-plan-ownership" in _codes(
        draft, _two_scope_context()
    )


def test_execution_plan_reference_fingerprint_cross_pair_fails():
    draft = _seal_draft(
        _draft().model_copy(update={"execution_plan_fingerprint": "2" * 64})
    )
    assert "draft-execution-plan-fingerprint-mismatch" in _codes(
        draft, _two_scope_context()
    )


def test_transition_requires_both_endpoint_references():
    draft = _draft()
    source = _seal(
        draft.sections[0].model_copy(update={"transition_after": None}),
        draft_section_identity,
    )
    destination = _seal(
        draft.sections[1].model_copy(update={"transition_before": None}),
        draft_section_identity,
    )
    for sections in (
        (source, destination),
        (draft.sections[0], destination),
        (source, draft.sections[1]),
    ):
        changed = _seal_draft(draft.model_copy(update={"sections": sections}))
        assert "draft-transition-endpoint-participation-mismatch" in _codes(
            changed, _context()
        )


def test_transition_reversal_and_duplicate_slot_fail():
    draft = _draft()
    reversed_transition = _seal(
        draft.transitions[0].model_copy(
            update={"from_section": "section:1", "to_section": "section:0"}
        ),
        transition_slot_identity,
    )
    reversed_draft = _seal_draft(
        draft.model_copy(update={"transitions": (reversed_transition,)})
    )
    assert "draft-transition-endpoint-participation-mismatch" in _codes(
        reversed_draft, _context()
    )

    extra = _seal(
        draft.transitions[0].model_copy(
            update={"transition_reference": "transition:alternate"}
        ),
        transition_slot_identity,
    )
    duplicate = _seal_draft(
        draft.model_copy(update={"transitions": (*draft.transitions, extra)})
    )
    codes = _codes(duplicate, _context())
    assert "draft-transition-slot-collision" in codes
    assert "draft-transition-endpoint-participation-mismatch" in codes


def test_ordered_section_references_are_identity_and_fingerprint_bearing():
    draft = _draft()
    reversed_draft = _seal_draft(
        draft.model_copy(
            update={"section_references": tuple(reversed(draft.section_references))}
        )
    )
    assert reversed_draft.identity != draft.identity
    assert reversed_draft.fingerprint != draft.fingerprint
    assert "draft-section-reference-order-mismatch" in _codes(
        reversed_draft, _context()
    )


def test_unordered_reference_and_context_permutations_are_stable():
    draft = _draft()
    section = DraftSection.model_validate(
        {
            **draft.sections[0].model_dump(),
            "required_claim_references": ("claim:1", "claim:0"),
            "required_evidence_references": ("evidence:1", "evidence:0"),
        }
    )
    reversed_section = DraftSection.model_validate(
        {
            **draft.sections[0].model_dump(),
            "required_claim_references": ("claim:0", "claim:1"),
            "required_evidence_references": ("evidence:0", "evidence:1"),
        }
    )
    assert draft_section_identity(section) == draft_section_identity(reversed_section)
    context = _two_scope_context()
    reversed_context = DraftValidationContext(
        normalized_input_scopes=tuple(reversed(context.normalized_input_scopes))
    )
    assert context == reversed_context


@pytest.mark.parametrize(
    "key",
    (
        "provider",
        "model",
        "prompt",
        "system_prompt",
        "generated_text",
        "paragraph",
        "sentence",
        "editorial_copy",
        "created_at",
        "timestamp",
        "runtime",
        "database",
        "network",
        "Provider",
        "system-prompt",
        "system prompt",
    ),
)
def test_prohibited_metadata_keys_are_rejected(key):
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key=key, value="structural-token")


def test_metadata_shape_limits_uniqueness_and_determinism():
    valid = StructuralMetadataEntry(key="structural_label", value="intro")
    assert valid.value == "intro"
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="x" * 65, value="token")
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="structural_label", value="x" * 81)
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="structural_label", value="prompt text")
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="structural_label", value="2026-07-29t10:30:00")
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="structural_label", value="c:/database/file")
    with pytest.raises(ValidationError):
        StructuralMetadataEntry(key="structural_label", value={"nested": "value"})
    with pytest.raises(ValidationError) as duplicate:
        DraftSection.model_validate(
            {**_section(0).model_dump(), "metadata": (valid, valid)}
        )
    assert "draft-duplicate-metadata-key" in str(duplicate.value)

    category = StructuralMetadataEntry(key="structural_category", value="national")
    left = DraftSection.model_validate(
        {**_section(0).model_dump(), "metadata": (valid, category)}
    )
    right = DraftSection.model_validate(
        {**_section(0).model_dump(), "metadata": (category, valid)}
    )
    assert left.metadata == right.metadata
    assert draft_section_identity(left) == draft_section_identity(right)


def test_unicode_nfc_and_validation_issue_order_are_stable():
    first = DraftSection.model_validate(
        {**_section(0).model_dump(), "purpose": "\u0218tiri"}
    )
    second = DraftSection.model_validate(
        {**_section(0).model_dump(), "purpose": "S\u0326tiri"}
    )
    assert first.purpose == second.purpose
    invalid = _draft().model_copy(update={"section_references": ("missing",)})
    first_issues = validate_draft_structure(invalid, _context())
    second_issues = validate_draft_structure(invalid, _context())
    assert first_issues == second_issues


@pytest.mark.parametrize(
    ("field", "mutable_value"),
    (
        ("sections", lambda draft: list(draft.sections)),
        ("transitions", lambda draft: list(draft.transitions)),
        ("section_references", lambda draft: list(draft.section_references)),
        ("draft_metadata", lambda draft: list(draft.draft_metadata)),
    ),
)
def test_mutable_copied_draft_collections_use_rebuilt_snapshot(field, mutable_value):
    canonical = _draft()
    caller_collection = mutable_value(canonical)
    copied = _seal_draft(canonical.model_copy(update={field: caller_collection}))
    assert validate_draft_structure(copied, _context()) == validate_draft_structure(
        canonical, _context()
    )


@pytest.mark.parametrize(
    "field",
    (
        "required_claim_references",
        "optional_claim_references",
        "required_evidence_references",
        "optional_evidence_references",
        "metadata",
    ),
)
def test_mutable_copied_section_collections_use_rebuilt_snapshot(field):
    draft = _draft()
    section = draft.sections[0]
    copied_section = _seal(
        section.model_copy(update={field: list(getattr(section, field))}),
        draft_section_identity,
    )
    copied = _replace_section(draft, 0, copied_section)
    assert validate_draft_structure(copied, _context()) == ()


def test_dictionary_shaped_nested_draft_members_reconstruct():
    draft = _draft()
    copied_sections = _seal_draft(
        draft.model_copy(
            update={"sections": [item.model_dump() for item in draft.sections]}
        )
    )
    assert validate_draft_structure(copied_sections, _context()) == ()

    copied_transitions = _seal_draft(
        draft.model_copy(
            update={"transitions": [item.model_dump() for item in draft.transitions]}
        )
    )
    assert validate_draft_structure(copied_transitions, _context()) == ()

    metadata = StructuralMetadataEntry(key="structural_label", value="intro")
    section = _seal(
        draft.sections[0].model_copy(update={"metadata": [metadata.model_dump()]}),
        draft_section_identity,
    )
    assert (
        validate_draft_structure(_replace_section(draft, 0, section), _context()) == ()
    )


def test_malformed_nested_draft_member_is_controlled():
    draft = _seal_draft(_draft().model_copy(update={"sections": [{"malformed": True}]}))
    issues = validate_draft_structure(draft, _context())
    assert issues
    assert {item.code for item in issues} == {
        "draft-invalid-reconstructed-model-contract"
    }


def test_copied_context_collections_and_dictionaries_reconstruct():
    draft = _draft()
    canonical = _context()
    scope = canonical.normalized_input_scopes[0]
    copied_scope = scope.model_copy(
        update={
            "claim_references": list(scope.claim_references),
            "evidence_references": set(scope.evidence_references),
            "execution_plans": [item.model_dump() for item in scope.execution_plans],
        }
    )
    contexts = (
        canonical.model_copy(update={"normalized_input_scopes": [copied_scope]}),
        canonical.model_copy(
            update={
                "normalized_input_scopes": [copied_scope.model_dump(warnings=False)]
            }
        ),
    )
    for copied in contexts:
        assert validate_draft_structure(draft, copied) == ()


@pytest.mark.parametrize(
    "context",
    (
        _context().model_copy(update={"normalized_input_scopes": 42}),
        _context().model_copy(update={"normalized_input_scopes": "scope"}),
        _context().model_copy(
            update={"normalized_input_scopes": [{"malformed": True}]}
        ),
        _context().model_copy(
            update={
                "normalized_input_scopes": (
                    _context()
                    .normalized_input_scopes[0]
                    .model_copy(update={"claim_references": 42}),
                )
            }
        ),
        _context().model_copy(
            update={
                "normalized_input_scopes": (
                    _context()
                    .normalized_input_scopes[0]
                    .model_copy(update={"execution_plans": 42}),
                )
            }
        ),
    ),
)
def test_malformed_copied_context_is_controlled(context):
    issues = validate_draft_structure(_draft(), context)
    assert issues
    assert all(item.code.startswith("draft-") for item in issues)


def test_each_validation_call_uses_a_fresh_context_snapshot():
    draft = _draft()
    scopes = list(_context().normalized_input_scopes)
    copied_context = _context().model_copy(update={"normalized_input_scopes": scopes})
    first_result = validate_draft_structure(draft, copied_context)
    scopes.append(scopes[0])
    second_result = validate_draft_structure(draft, copied_context)
    assert first_result == ()
    assert {item.code for item in second_result} == {
        "draft-duplicate-context-normalized-input-identity"
    }
    assert first_result == ()


def test_each_validation_call_uses_a_fresh_draft_snapshot():
    draft = _draft()
    sections = list(draft.sections)
    copied = _seal_draft(draft.model_copy(update={"sections": sections}))
    first_result = validate_draft_structure(copied, _context())
    sections.append(sections[0])
    second_result = validate_draft_structure(copied, _context())
    assert first_result == ()
    assert second_result
    assert first_result == ()
