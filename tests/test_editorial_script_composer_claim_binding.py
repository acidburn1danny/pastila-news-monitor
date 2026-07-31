"""Focused Phase 4.2 deterministic claim-binding tests."""

import importlib
import json
import re
import subprocess
import sys
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    ClaimBinding,
    ClaimBindingRequirement,
    ClaimBindingRole,
    ClaimBindingValidationContext,
    DraftClaimBindingPlan,
    DraftExecutionPlanReference,
    DraftSection,
    DraftSectionKind,
    DraftStatus,
    DraftStructure,
    DraftValidationContext,
    NormalizedInputDraftScope,
    SectionClaimBindingSet,
    claim_binding_identity,
    claim_binding_semantic_fingerprint,
    draft_claim_binding_plan_identity,
    draft_section_identity,
    draft_semantic_fingerprint,
    draft_structure_identity,
    section_claim_binding_set_identity,
    validate_draft_claim_binding_plan,
)

ZERO = "0" * 64


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def _draft_seal(value, identity_function):
    return _seal(value, identity_function, draft_semantic_fingerprint)


def _binding_seal(value, identity_function):
    return _seal(value, identity_function, claim_binding_semantic_fingerprint)


def _section(index=0, *, required=("claim:required",), optional=("claim:optional",)):
    value = DraftSection(
        identity=f"scout:draft-section:{ZERO}",
        fingerprint=ZERO,
        section_reference=f"section:{index}",
        order_index=index,
        section_kind=DraftSectionKind.INTRO,
        purpose="structural-purpose",
        required_claim_references=required,
        optional_claim_references=optional,
    )
    return _draft_seal(value, draft_section_identity)


def _draft(*sections):
    sections = sections or (_section(),)
    value = DraftStructure(
        identity=f"scout:draft-structure:{ZERO}",
        fingerprint=ZERO,
        normalized_input_reference="input:one",
        execution_plan_reference="execution-plan:one",
        execution_plan_fingerprint="1" * 64,
        section_references=tuple(item.section_reference for item in sections),
        sections=sections,
        status=DraftStatus.VALIDATED,
    )
    return _draft_seal(value, draft_structure_identity)


def _draft_context():
    return DraftValidationContext(
        normalized_input_scopes=(
            NormalizedInputDraftScope(
                normalized_input_reference="input:one",
                claim_references=("claim:required", "claim:optional", "claim:shared"),
                execution_plans=(
                    DraftExecutionPlanReference(
                        execution_plan_reference="execution-plan:one",
                        execution_plan_fingerprint="1" * 64,
                    ),
                ),
            ),
            NormalizedInputDraftScope(
                normalized_input_reference="input:two",
                claim_references=("claim:foreign",),
            ),
        )
    )


def _context(draft=None):
    return ClaimBindingValidationContext(
        drafts=(draft or _draft(),), draft_validation_context=_draft_context()
    )


def _binding(
    draft,
    section,
    claim="claim:required",
    requirement=ClaimBindingRequirement.REQUIRED,
    role=ClaimBindingRole.SECTION_ANCHOR,
    ordinal=0,
    reference=None,
):
    value = ClaimBinding(
        identity=f"scout:claim-binding:{ZERO}",
        fingerprint=ZERO,
        binding_reference=reference or f"binding:{section.section_reference}:{claim}",
        draft_reference=draft.identity,
        section_reference=section.section_reference,
        claim_reference=claim,
        requirement=requirement,
        role=role,
        ordinal=ordinal,
    )
    return _binding_seal(value, claim_binding_identity)


def _binding_set(draft, section, bindings):
    value = SectionClaimBindingSet(
        identity=f"scout:section-claim-binding-set:{ZERO}",
        fingerprint=ZERO,
        binding_set_reference=f"binding-set:{section.section_reference}",
        draft_reference=draft.identity,
        section_reference=section.section_reference,
        bindings=bindings,
    )
    return _binding_seal(value, section_claim_binding_set_identity)


def _plan(draft=None, sets=None):
    draft = draft or _draft()
    if sets is None:
        sets = (
            _binding_set(
                draft, draft.sections[0], (_binding(draft, draft.sections[0]),)
            ),
        )
    value = DraftClaimBindingPlan(
        identity=f"scout:draft-claim-binding-plan:{ZERO}",
        fingerprint=ZERO,
        plan_reference="binding-plan:one",
        draft_reference=draft.identity,
        draft_fingerprint=draft.fingerprint,
        normalized_input_reference=draft.normalized_input_reference,
        section_binding_sets=sets,
    )
    return _binding_seal(value, draft_claim_binding_plan_identity)


def _codes(plan, context=None):
    return {
        item.code
        for item in validate_draft_claim_binding_plan(plan, context or _context())
    }


def _replace_binding(plan, binding):
    binding_set = _binding_seal(
        plan.section_binding_sets[0].model_copy(update={"bindings": (binding,)}),
        section_claim_binding_set_identity,
    )
    return _binding_seal(
        plan.model_copy(update={"section_binding_sets": (binding_set,)}),
        draft_claim_binding_plan_identity,
    )


def test_valid_models_are_immutable_and_contextually_valid():
    plan = _plan()
    assert validate_draft_claim_binding_plan(plan, _context()) == ()
    for value in (
        plan,
        plan.section_binding_sets[0],
        plan.section_binding_sets[0].bindings[0],
    ):
        with pytest.raises(ValidationError):
            value.identity = "changed"


def test_caller_collections_are_defensively_copied():
    draft = _draft()
    bindings = [_binding(draft, draft.sections[0])]
    binding_set = _binding_set(draft, draft.sections[0], bindings)
    bindings.clear()
    sets = [binding_set]
    plan = _plan(draft, sets)
    sets.clear()
    drafts = [draft]
    context = ClaimBindingValidationContext(
        drafts=drafts, draft_validation_context=_draft_context()
    )
    drafts.clear()
    assert (
        len(binding_set.bindings)
        == len(plan.section_binding_sets)
        == len(context.drafts)
        == 1
    )


@pytest.mark.parametrize("requirement", list(ClaimBindingRequirement))
def test_requirement_vocabulary(requirement):
    assert ClaimBindingRequirement(requirement.value) is requirement


@pytest.mark.parametrize("role", list(ClaimBindingRole))
def test_built_in_role_vocabulary(role):
    assert _binding(_draft(), _draft().sections[0], role=role).role == role


@pytest.mark.parametrize(
    "role",
    (
        "unknown",
        "custom:",
        "custom:BAD",
        "custom:a_b",
        "custom:a/b",
        "custom:ș",
        "custom:openai",
        "custom:provider-execution",
        "custom:prompt",
        " custom:x",
    ),
)
def test_invalid_roles_are_rejected(role):
    with pytest.raises(ValidationError):
        ClaimBinding.model_validate(
            {**_binding(_draft(), _draft().sections[0]).model_dump(), "role": role}
        )


def test_valid_custom_role_and_strict_requirement():
    assert (
        _binding(_draft(), _draft().sections[0], role="custom:timeline-anchor").role
        == "custom:timeline-anchor"
    )
    with pytest.raises(ValidationError):
        ClaimBinding.model_validate(
            {
                **_binding(_draft(), _draft().sections[0]).model_dump(),
                "requirement": "mandatory",
            }
        )


def test_identity_fingerprint_and_order_are_deterministic():
    first = _plan()
    second = _plan()
    assert first.identity == second.identity
    assert first.fingerprint == second.fingerprint
    binding = first.section_binding_sets[0].bindings[0]
    for update in (
        {"role": ClaimBindingRole.SECTION_CONTEXT},
        {"requirement": ClaimBindingRequirement.OPTIONAL},
        {"ordinal": 1},
        {"claim_reference": "claim:optional"},
        {"section_reference": "section:foreign"},
        {"draft_reference": f"scout:draft-structure:{'2' * 64}"},
    ):
        assert (
            claim_binding_semantic_fingerprint(binding.model_copy(update=update))
            != binding.fingerprint
        )


def test_stale_identity_and_fingerprint_are_rejected():
    plan = _plan()
    assert "claim-binding-identity-mismatch" in _codes(
        plan.model_copy(update={"plan_reference": "plan:changed"})
    )
    assert "claim-binding-fingerprint-mismatch" in _codes(
        plan.model_copy(update={"draft_fingerprint": "2" * 64})
    )


def test_required_optional_and_undeclared_consistency():
    plan = _plan()
    binding = plan.section_binding_sets[0].bindings[0]
    optional = _binding(
        _draft(),
        _draft().sections[0],
        "claim:optional",
        ClaimBindingRequirement.OPTIONAL,
        ordinal=1,
    )
    assert (
        validate_draft_claim_binding_plan(
            _plan(
                sets=(
                    _binding_set(_draft(), _draft().sections[0], (binding, optional)),
                )
            ),
            _context(),
        )
        == ()
    )
    attacks = (
        (
            binding.model_copy(
                update={"requirement": ClaimBindingRequirement.OPTIONAL}
            ),
            "claim-binding-required-marked-optional",
        ),
        (
            binding.model_copy(update={"claim_reference": "claim:optional"}),
            "claim-binding-optional-marked-required",
        ),
        (
            binding.model_copy(update={"claim_reference": "claim:shared"}),
            "claim-binding-claim-not-declared-by-section",
        ),
    )
    for changed, code in attacks:
        changed = _binding_seal(changed, claim_binding_identity)
        assert code in _codes(_replace_binding(plan, changed))


def test_missing_required_and_optional_omission():
    draft = _draft()
    assert "claim-binding-missing-required-section-binding-set" in _codes(
        _plan(draft, ())
    )
    optional_only = _draft(_section(required=(), optional=("claim:optional",)))
    assert (
        validate_draft_claim_binding_plan(
            _plan(optional_only, ()), _context(optional_only)
        )
        == ()
    )


def test_canonical_empty_no_claim_plan_and_nonempty_set_rule():
    empty_draft = _draft(_section(required=(), optional=()))
    assert (
        validate_draft_claim_binding_plan(_plan(empty_draft, ()), _context(empty_draft))
        == ()
    )
    with pytest.raises(ValidationError):
        SectionClaimBindingSet.model_validate(
            {
                **_binding_set(
                    empty_draft,
                    empty_draft.sections[0],
                    (_binding(empty_draft, empty_draft.sections[0]),),
                ).model_dump(),
                "bindings": (),
            }
        )


def test_cross_section_reuse_is_valid_only_when_declared():
    sections = (
        _section(0, required=("claim:shared",), optional=()),
        _section(1, required=("claim:shared",), optional=()),
    )
    draft = _draft(*sections)
    sets = tuple(
        _binding_set(draft, section, (_binding(draft, section, "claim:shared"),))
        for section in sections
    )
    assert validate_draft_claim_binding_plan(_plan(draft, sets), _context(draft)) == ()


def test_linkage_and_ownership_attacks():
    plan = _plan()
    binding = plan.section_binding_sets[0].bindings[0]
    for update, code in (
        (
            {"claim_reference": "claim:foreign"},
            "claim-binding-cross-normalized-input-claim-ownership",
        ),
        ({"claim_reference": "claim:unknown"}, "claim-binding-unknown-claim-reference"),
        ({"section_reference": "section:foreign"}, "claim-binding-section-mismatch"),
        (
            {"draft_reference": f"scout:draft-structure:{'2' * 64}"},
            "claim-binding-draft-mismatch",
        ),
    ):
        changed = _binding_seal(
            binding.model_copy(update=update), claim_binding_identity
        )
        assert code in _codes(_replace_binding(plan, changed))


def test_plan_draft_fingerprint_and_input_linkage():
    plan = _plan()
    for update, code in (
        (
            {"draft_reference": f"scout:draft-structure:{'2' * 64}"},
            "claim-binding-unknown-draft-reference",
        ),
        ({"draft_fingerprint": "2" * 64}, "claim-binding-draft-fingerprint-mismatch"),
        (
            {"normalized_input_reference": "input:two"},
            "claim-binding-normalized-input-mismatch",
        ),
    ):
        changed = _binding_seal(
            plan.model_copy(update=update), draft_claim_binding_plan_identity
        )
        assert code in _codes(changed)


def test_duplicates_and_ordinal_fail_deterministically():
    draft = _draft()
    first = _binding(draft, draft.sections[0])
    second = _binding(draft, draft.sections[0], ordinal=0, reference="binding:other")
    binding_set = _binding_set(draft, draft.sections[0], (first, second))
    plan = _plan(draft, (binding_set,))
    codes = _codes(plan)
    assert {
        "claim-binding-duplicate-claim-reference",
        "claim-binding-duplicate-ordinal",
        "claim-binding-invalid-ordinal-sequence",
    } <= codes
    reversed_set = _binding_seal(
        binding_set.model_copy(
            update={"bindings": tuple(reversed(binding_set.bindings))}
        ),
        section_claim_binding_set_identity,
    )
    assert codes == _codes(_plan(draft, (reversed_set,)))


def test_binding_and_section_set_ordering():
    section = _section(required=("claim:required",), optional=("claim:optional",))
    draft = _draft(section)
    bindings = (
        _binding(draft, section, ordinal=0),
        _binding(
            draft,
            section,
            "claim:optional",
            ClaimBindingRequirement.OPTIONAL,
            ordinal=1,
        ),
    )
    valid = _binding_set(draft, section, bindings)
    assert (
        validate_draft_claim_binding_plan(_plan(draft, (valid,)), _context(draft)) == ()
    )
    reversed_set = _binding_seal(
        valid.model_copy(update={"bindings": tuple(reversed(bindings))}),
        section_claim_binding_set_identity,
    )
    assert "claim-binding-invalid-ordinal-sequence" in _codes(
        _plan(draft, (reversed_set,)), _context(draft)
    )


def test_multi_section_set_order_matches_draft():
    sections = (_section(0), _section(1))
    draft = _draft(*sections)
    sets = tuple(
        _binding_set(draft, section, (_binding(draft, section),))
        for section in sections
    )
    assert validate_draft_claim_binding_plan(_plan(draft, sets), _context(draft)) == ()
    reversed_plan = _plan(draft, tuple(reversed(sets)))
    assert "claim-binding-section-set-order-mismatch" in _codes(
        reversed_plan, _context(draft)
    )
    assert reversed_plan.fingerprint != _plan(draft, sets).fingerprint


def test_duplicate_section_sets_and_context_drafts_are_rejected():
    plan = _plan()
    changed = _binding_seal(
        plan.model_copy(update={"section_binding_sets": plan.section_binding_sets * 2}),
        draft_claim_binding_plan_identity,
    )
    assert {
        "claim-binding-duplicate-binding-set-reference",
        "claim-binding-duplicate-binding-set-identity",
        "claim-binding-duplicate-section-reference",
    } <= _codes(changed)
    context = _context().model_copy(update={"drafts": (_draft(), _draft())})
    assert "claim-binding-duplicate-context-draft-identity" in _codes(plan, context)


def test_model_copy_mutable_equivalents_reconstruct():
    plan = _plan()
    binding_set = plan.section_binding_sets[0].model_copy(
        update={"bindings": [plan.section_binding_sets[0].bindings[0].model_dump()]}
    )
    copied = plan.model_copy(
        update={"section_binding_sets": [binding_set.model_dump(warnings=False)]}
    )
    context = _context().model_copy(
        update={"drafts": [item.model_dump() for item in _context().drafts]}
    )
    assert validate_draft_claim_binding_plan(copied, context) == ()


@pytest.mark.parametrize(
    "plan",
    (
        _plan().model_copy(update={"section_binding_sets": 42}),
        _plan().model_copy(update={"section_binding_sets": [{"bad": True}]}),
        _plan().model_copy(update={"section_binding_sets": [object()]}),
    ),
)
def test_malformed_copied_plan_is_controlled(plan):
    issues = validate_draft_claim_binding_plan(plan, _context())
    assert issues and all(item.code.startswith("claim-binding-") for item in issues)


def test_fresh_snapshot_between_calls():
    plan = _plan()
    sets = list(plan.section_binding_sets)
    copied = plan.model_copy(update={"section_binding_sets": sets})
    first = validate_draft_claim_binding_plan(copied, _context())
    sets.append(sets[0])
    second = validate_draft_claim_binding_plan(copied, _context())
    assert first == () and second and first == ()


def test_unicode_nfc_and_issue_order_are_stable():
    draft = _draft()
    first = _binding(draft, draft.sections[0], reference="binding:ș")
    second = _binding(draft, draft.sections[0], reference="binding:s\u0326")
    assert first.identity == second.identity and first.fingerprint == second.fingerprint
    invalid = _plan().model_copy(update={"normalized_input_reference": "input:bad"})
    assert validate_draft_claim_binding_plan(
        invalid, _context()
    ) == validate_draft_claim_binding_plan(invalid, _context())


def test_separate_process_seals_are_stable():
    code = "import runpy; n=runpy.run_path('tests/test_editorial_script_composer_claim_binding.py'); p=n['_plan'](); print(p.identity,p.fingerprint)"
    first = subprocess.check_output([sys.executable, "-c", code], text=True)
    second = subprocess.check_output([sys.executable, "-c", code], text=True)
    assert first == second


def test_public_models_exclude_phase_boundary_fields():
    forbidden = {
        "claim_text",
        "evidence",
        "provider",
        "prompt",
        "score",
        "readiness",
        "generated_text",
        "timestamp",
        "runtime",
        "publication",
    }
    for model in (ClaimBinding, SectionClaimBindingSet, DraftClaimBindingPlan):
        assert forbidden.isdisjoint(model.model_fields)


def _assert_no_nondeterministic_repr(issues):
    assert issues
    serialized = json.dumps(
        [asdict(issue) for issue in issues], ensure_ascii=False, sort_keys=True
    )
    assert not re.search(r"0x[0-9A-Fa-f]+", serialized)
    assert "<object object at" not in serialized
    assert "\\" not in serialized
    assert "\n" not in serialized


def _serialized_object_reference_issues():
    issues = validate_draft_claim_binding_plan(
        _plan().model_copy(update={"plan_reference": object()}), _context()
    )
    _assert_no_nondeterministic_repr(issues)
    return json.dumps(
        [asdict(issue) for issue in issues], ensure_ascii=False, sort_keys=True
    )


class _HostilePublicInput:
    plan_reference = "binding-plan:hostile"

    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, *args, **kwargs):
        del args, kwargs
        raise self.error_type("hostile reconstruction detail must not escape")


class _HostileContextInput:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, *args, **kwargs):
        del args, kwargs
        raise self.error_type("hostile reconstruction detail must not escape")


def _serialized_hostile_reconstruction_issues():
    plan_issues = validate_draft_claim_binding_plan(
        _HostilePublicInput(KeyError), _context()
    )
    context_issues = validate_draft_claim_binding_plan(
        _plan(), _HostileContextInput(RuntimeError)
    )
    _assert_no_nondeterministic_repr(plan_issues)
    _assert_no_nondeterministic_repr(context_issues)
    return json.dumps(
        {
            "context": [asdict(issue) for issue in context_issues],
            "plan": [asdict(issue) for issue in plan_issues],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def test_reconstruction_diagnostics_are_safe_and_cross_process_stable():
    first = _serialized_object_reference_issues()
    second = _serialized_object_reference_issues()
    assert first == second
    code = (
        "import runpy; "
        "n=runpy.run_path('tests/test_editorial_script_composer_claim_binding.py'); "
        "print(n['_serialized_object_reference_issues']())"
    )
    external = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert first == external


@pytest.mark.parametrize("error_type", (KeyError, RuntimeError))
def test_hostile_plan_model_dump_exceptions_become_stable_issues(error_type):
    first = validate_draft_claim_binding_plan(
        _HostilePublicInput(error_type), _context()
    )
    second = validate_draft_claim_binding_plan(
        _HostilePublicInput(error_type), _context()
    )
    _assert_no_nondeterministic_repr(first)
    assert first == second
    assert {issue.code for issue in first} == {
        "claim-binding-invalid-reconstructed-plan"
    }
    assert {issue.artifact_reference for issue in first} == {"binding-plan:hostile"}


@pytest.mark.parametrize("error_type", (KeyError, RuntimeError))
def test_hostile_context_model_dump_exceptions_become_stable_issues(error_type):
    first = validate_draft_claim_binding_plan(_plan(), _HostileContextInput(error_type))
    second = validate_draft_claim_binding_plan(
        _plan(), _HostileContextInput(error_type)
    )
    _assert_no_nondeterministic_repr(first)
    assert first == second
    assert {issue.code for issue in first} == {
        "claim-binding-invalid-reconstructed-context"
    }
    assert {issue.artifact_reference for issue in first} == {"draft-claim-binding-plan"}


def test_hostile_reconstruction_issues_are_cross_process_stable():
    first = _serialized_hostile_reconstruction_issues()
    second = _serialized_hostile_reconstruction_issues()
    assert first == second
    code = (
        "import runpy; "
        "n=runpy.run_path('tests/test_editorial_script_composer_claim_binding.py'); "
        "print(n['_serialized_hostile_reconstruction_issues']())"
    )
    external = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert first == external


@pytest.mark.parametrize(
    "control_exception", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_process_control_exceptions_propagate(control_exception):
    with pytest.raises(control_exception):
        validate_draft_claim_binding_plan(
            _HostilePublicInput(control_exception), _context()
        )
    with pytest.raises(control_exception):
        validate_draft_claim_binding_plan(
            _plan(), _HostileContextInput(control_exception)
        )


@pytest.mark.parametrize(
    "reference",
    ("", "invalid reference", "line\nbreak", "C:\\private\\file", "x" * 201),
)
def test_unsafe_invalid_plan_references_use_stable_contract_fallback(reference):
    issues = validate_draft_claim_binding_plan(
        _plan().model_copy(
            update={"plan_reference": reference, "section_binding_sets": 42}
        ),
        _context(),
    )
    _assert_no_nondeterministic_repr(issues)
    assert {issue.artifact_reference for issue in issues} == {
        "draft-claim-binding-plan"
    }


@pytest.mark.parametrize(
    ("level", "field"),
    (
        ("plan", "plan_reference"),
        ("plan", "draft_reference"),
        ("binding_set", "binding_set_reference"),
        ("binding_set", "draft_reference"),
        ("binding_set", "section_reference"),
        ("binding", "binding_reference"),
        ("binding", "draft_reference"),
        ("binding", "section_reference"),
        ("binding", "claim_reference"),
    ),
)
def test_arbitrary_reference_objects_produce_safe_controlled_issues(level, field):
    plan = _plan()
    if level == "plan":
        changed = plan.model_copy(update={field: object()})
    elif level == "binding_set":
        binding_set = plan.section_binding_sets[0].model_copy(update={field: object()})
        changed = plan.model_copy(update={"section_binding_sets": [binding_set]})
    else:
        binding = (
            plan.section_binding_sets[0]
            .bindings[0]
            .model_copy(update={field: object()})
        )
        binding_set = plan.section_binding_sets[0].model_copy(
            update={"bindings": [binding]}
        )
        changed = plan.model_copy(update={"section_binding_sets": [binding_set]})
    first = validate_draft_claim_binding_plan(changed, _context())
    second = validate_draft_claim_binding_plan(changed, _context())
    _assert_no_nondeterministic_repr(first)
    assert first == second


@pytest.mark.parametrize(
    "requirement",
    ("REQUIRED", "Required", " required ", "", None, 7, object(), "mandatory"),
)
def test_copied_requirement_variants_fail_controlled_revalidation(requirement):
    plan = _plan()
    binding = (
        plan.section_binding_sets[0]
        .bindings[0]
        .model_copy(update={"requirement": requirement})
    )
    binding_set = plan.section_binding_sets[0].model_copy(
        update={"bindings": [binding]}
    )
    issues = validate_draft_claim_binding_plan(
        plan.model_copy(update={"section_binding_sets": [binding_set]}), _context()
    )
    _assert_no_nondeterministic_repr(issues)


@pytest.mark.parametrize("ordinal", (False, 0.0, -1, "0"))
def test_copied_invalid_ordinal_types_fail_controlled_revalidation(ordinal):
    plan = _plan()
    binding = (
        plan.section_binding_sets[0].bindings[0].model_copy(update={"ordinal": ordinal})
    )
    binding_set = plan.section_binding_sets[0].model_copy(
        update={"bindings": [binding]}
    )
    issues = validate_draft_claim_binding_plan(
        plan.model_copy(update={"section_binding_sets": [binding_set]}), _context()
    )
    _assert_no_nondeterministic_repr(issues)


def test_large_ordinal_gap_and_reversed_binding_order_are_distinct_failures():
    draft = _draft()
    section = draft.sections[0]
    first = _binding(draft, section)
    optional = _binding(
        draft,
        section,
        "claim:optional",
        ClaimBindingRequirement.OPTIONAL,
        ordinal=999_999,
    )
    gap = _plan(draft, (_binding_set(draft, section, (first, optional)),))
    assert "claim-binding-invalid-ordinal-sequence" in _codes(gap, _context(draft))
    ordered_optional = _binding(
        draft,
        section,
        "claim:optional",
        ClaimBindingRequirement.OPTIONAL,
        ordinal=1,
    )
    reversed_set = _binding_seal(
        _binding_set(draft, section, (first, ordered_optional)).model_copy(
            update={"bindings": (ordered_optional, first)}
        ),
        section_claim_binding_set_identity,
    )
    reversed_plan = _plan(draft, (reversed_set,))
    assert "claim-binding-invalid-ordinal-sequence" in _codes(
        reversed_plan, _context(draft)
    )


@pytest.mark.parametrize("missing_index", (0, 1, 2))
def test_each_required_claim_position_is_independently_required(missing_index):
    claims = ("claim:required", "claim:optional", "claim:shared")
    section = _section(required=claims, optional=())
    draft = _draft(section)
    remaining = tuple(
        claim for index, claim in enumerate(claims) if index != missing_index
    )
    bindings = tuple(
        _binding(draft, section, claim, ordinal=index)
        for index, claim in enumerate(remaining)
    )
    plan = _plan(draft, (_binding_set(draft, section, bindings),))
    issues = validate_draft_claim_binding_plan(plan, _context(draft))
    assert {issue.code for issue in issues} == {"claim-binding-missing-required-claim"}
    assert issues[0].related_references == (claims[missing_index],)


@pytest.mark.parametrize(
    ("field", "expected_code"),
    (
        ("binding_reference", "claim-binding-duplicate-binding-reference"),
        ("identity", "claim-binding-duplicate-binding-identity"),
        ("claim_reference", "claim-binding-duplicate-claim-reference"),
        ("ordinal", "claim-binding-duplicate-ordinal"),
    ),
)
def test_each_duplicate_binding_invariant_is_rejected_after_resealing(
    field, expected_code
):
    draft = _draft()
    first = _binding(draft, draft.sections[0])
    second_updates = {
        "binding_reference": "binding:second",
        "claim_reference": "claim:optional",
        "requirement": ClaimBindingRequirement.OPTIONAL,
        "ordinal": 1,
    }
    second_updates[field] = getattr(first, field)
    second = first.model_copy(update=second_updates)
    if field == "identity":
        second = second.model_copy(
            update={"fingerprint": claim_binding_semantic_fingerprint(second)}
        )
    else:
        second = _binding_seal(second, claim_binding_identity)
    binding_set = _binding_set(draft, draft.sections[0], (first, second))
    plan = _plan(draft, (binding_set,))
    forward = validate_draft_claim_binding_plan(plan, _context(draft))
    reversed_set = _binding_seal(
        binding_set.model_copy(
            update={"bindings": tuple(reversed(binding_set.bindings))}
        ),
        section_claim_binding_set_identity,
    )
    reverse = validate_draft_claim_binding_plan(
        _plan(draft, (reversed_set,)), _context(draft)
    )
    assert expected_code in {issue.code for issue in forward}
    assert expected_code in {issue.code for issue in reverse}


def test_same_section_reference_from_foreign_draft_cannot_substitute():
    draft_a = _draft()
    section_b = _draft_seal(
        draft_a.sections[0].model_copy(update={"purpose": "foreign-purpose"}),
        draft_section_identity,
    )
    draft_b = _draft_seal(
        draft_a.model_copy(update={"sections": (section_b,)}),
        draft_structure_identity,
    )
    context = ClaimBindingValidationContext(
        drafts=(draft_a, draft_b), draft_validation_context=_draft_context()
    )
    foreign_set = _binding_set(draft_b, section_b, (_binding(draft_b, section_b),))
    issues = validate_draft_claim_binding_plan(_plan(draft_a, (foreign_set,)), context)
    assert "claim-binding-set-draft-mismatch" in {issue.code for issue in issues}
    assert "claim-binding-draft-mismatch" in {issue.code for issue in issues}


def test_nested_claim_inventory_mutation_duplicate_and_restoration_are_fresh():
    plan = _plan()
    context = _context()
    scope = context.draft_validation_context.normalized_input_scopes[0]
    claims = list(scope.claim_references)
    copied_scope = scope.model_copy(update={"claim_references": claims})
    draft_context = context.draft_validation_context.model_copy(
        update={
            "normalized_input_scopes": [
                copied_scope,
                *context.draft_validation_context.normalized_input_scopes[1:],
            ]
        }
    )
    copied_context = context.model_copy(
        update={"draft_validation_context": draft_context}
    )
    first = validate_draft_claim_binding_plan(plan, copied_context)
    claims.remove("claim:required")
    removed = validate_draft_claim_binding_plan(plan, copied_context)
    claims.append("claim:required")
    restored = validate_draft_claim_binding_plan(plan, copied_context)
    claims.append("claim:required")
    duplicated = validate_draft_claim_binding_plan(plan, copied_context)
    claims.pop()
    restored_again = validate_draft_claim_binding_plan(plan, copied_context)
    assert first == restored == restored_again == ()
    assert removed and duplicated
    assert first == ()


@pytest.mark.parametrize(
    ("level", "field", "expected_code"),
    (
        ("binding", "identity", "claim-binding-identity-mismatch"),
        ("binding", "fingerprint", "claim-binding-fingerprint-mismatch"),
        ("binding_set", "identity", "claim-binding-identity-mismatch"),
        ("binding_set", "fingerprint", "claim-binding-fingerprint-mismatch"),
    ),
)
def test_stale_nested_seals_are_detected(level, field, expected_code):
    plan = _plan()
    if level == "binding":
        binding = (
            plan.section_binding_sets[0]
            .bindings[0]
            .model_copy(
                update={
                    field: (
                        ZERO
                        if field == "fingerprint"
                        else f"scout:claim-binding:{ZERO}"
                    )
                }
            )
        )
        binding_set = _binding_seal(
            plan.section_binding_sets[0].model_copy(update={"bindings": (binding,)}),
            section_claim_binding_set_identity,
        )
    else:
        replacement = (
            ZERO
            if field == "fingerprint"
            else f"scout:section-claim-binding-set:{ZERO}"
        )
        binding_set = plan.section_binding_sets[0].model_copy(
            update={field: replacement}
        )
    changed = _binding_seal(
        plan.model_copy(update={"section_binding_sets": (binding_set,)}),
        draft_claim_binding_plan_identity,
    )
    assert expected_code in _codes(changed, _context())


@pytest.mark.parametrize("conflicting", (False, True))
def test_duplicate_context_drafts_are_order_independent(conflicting):
    draft = _draft()
    duplicate = (
        draft.model_copy(update={"fingerprint": "2" * 64}) if conflicting else draft
    )
    outcomes = []
    for ordering in ((draft, duplicate), (duplicate, draft)):
        context = _context().model_copy(update={"drafts": ordering})
        outcomes.append(validate_draft_claim_binding_plan(_plan(), context))
    assert outcomes[0] == outcomes[1]
    assert {issue.code for issue in outcomes[0]} == {
        "claim-binding-duplicate-context-draft-identity"
    }


@pytest.mark.parametrize(
    ("target", "value"),
    (
        ("bindings", 42),
        ("bindings", "binding"),
        ("bindings", [{"missing": True}]),
        ("bindings", [object()]),
        ("section_binding_sets", 42),
        ("section_binding_sets", "set"),
        ("section_binding_sets", [{"missing": True}]),
        ("section_binding_sets", [object()]),
        ("drafts", 42),
        ("drafts", "draft"),
        ("drafts", [{"missing": True}]),
        ("drafts", [object()]),
    ),
)
def test_malformed_collection_shapes_return_controlled_safe_findings(target, value):
    plan = _plan()
    context = _context()
    if target == "bindings":
        binding_set = plan.section_binding_sets[0].model_copy(update={target: value})
        plan = plan.model_copy(update={"section_binding_sets": [binding_set]})
    elif target == "section_binding_sets":
        plan = plan.model_copy(update={target: value})
    else:
        context = context.model_copy(update={target: value})
    issues = validate_draft_claim_binding_plan(plan, context)
    _assert_no_nondeterministic_repr(issues)


def test_malformed_nested_context_contracts_are_controlled_and_safe():
    context = _context()
    malformed_contexts = (
        context.model_copy(update={"draft_validation_context": object()}),
        context.model_copy(
            update={
                "draft_validation_context": context.draft_validation_context.model_copy(
                    update={"normalized_input_scopes": [object()]}
                )
            }
        ),
    )
    for malformed in malformed_contexts:
        _assert_no_nondeterministic_repr(
            validate_draft_claim_binding_plan(_plan(), malformed)
        )


def test_phase_4_2_public_exports_are_exhaustive_and_internals_are_private():
    module = importlib.import_module("pastila_scout.editor.script_composer")
    public = {
        "ClaimBinding",
        "SectionClaimBindingSet",
        "DraftClaimBindingPlan",
        "ClaimBindingValidationContext",
        "ClaimBindingRequirement",
        "ClaimBindingRole",
        "validate_draft_claim_binding_plan",
        "claim_binding_identity",
        "section_claim_binding_set_identity",
        "draft_claim_binding_plan_identity",
        "claim_binding_semantic_fingerprint",
    }
    private = {
        "ClaimBindingDomainModel",
        "_AuthoritativeClaimBindingInputs",
        "_reconstruct_for_validation",
        "_safe_reconstruction_artifact_reference",
        "_safe_diagnostic_reference",
        "_safe_error_location",
        "_validate_binding_set",
        "_validate_plan_duplicates",
        "_validate_seals",
    }
    assert all(hasattr(module, name) for name in public)
    assert all(not hasattr(module, name) for name in private)
