"""Adversarial Phase 4.3 deterministic section-composition tests."""

import importlib
import json
import runpy
import subprocess
import sys
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    ClaimBindingRequirement,
    ClaimBindingRole,
    ComposedClaim,
    ComposedSection,
    DomainValidationError,
    DraftSectionCompositionPlan,
    SectionCompositionValidationContext,
    build_draft_section_composition_plan,
    compute_composed_claim_fingerprint,
    compute_composed_claim_identity,
    compute_composed_section_fingerprint,
    compute_composed_section_identity,
    compute_draft_section_composition_plan_fingerprint,
    compute_draft_section_composition_plan_identity,
    validate_draft_section_composition_plan,
)

UPSTREAM = runpy.run_path("tests/test_editorial_script_composer_claim_binding.py")
ZERO = "0" * 64


def _source_plan(draft=None, sets=None):
    return UPSTREAM["_plan"](draft, sets)


def _source_context(draft=None):
    return UPSTREAM["_context"](draft)


def _composition(plan=None, context=None):
    plan = plan or _source_plan()
    context = context or _source_context()
    return build_draft_section_composition_plan(plan, context)


def _context(plan=None, source_context=None):
    return SectionCompositionValidationContext(
        claim_binding_plans=(plan or _source_plan(),),
        claim_binding_validation_context=source_context or _source_context(),
    )


def _seal_claim(value):
    value = value.model_copy(
        update={"identity": compute_composed_claim_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": compute_composed_claim_fingerprint(value)}
    )


def _seal_section(value):
    value = value.model_copy(
        update={"identity": compute_composed_section_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": compute_composed_section_fingerprint(value)}
    )


def _seal_plan(value):
    value = value.model_copy(
        update={"identity": compute_draft_section_composition_plan_identity(value)}
    )
    return value.model_copy(
        update={
            "fingerprint": compute_draft_section_composition_plan_fingerprint(value)
        }
    )


def _replace_claim(plan, claim, index=0):
    section = plan.composed_sections[0]
    claims = list(section.composed_claims)
    claims[index] = claim
    section = _seal_section(
        section.model_copy(update={"composed_claims": tuple(claims)})
    )
    return _seal_plan(plan.model_copy(update={"composed_sections": (section,)}))


def _codes(plan, context=None):
    return {
        issue.code
        for issue in validate_draft_section_composition_plan(
            plan, context or _context()
        )
    }


def test_valid_projection_is_exact_immutable_and_deterministic():
    source = _source_plan()
    first = _composition(source)
    second = _composition(source)
    assert first == second
    assert validate_draft_section_composition_plan(first, _context(source)) == ()
    binding = source.section_binding_sets[0].bindings[0]
    claim = first.composed_sections[0].composed_claims[0]
    assert (
        claim.source_claim_binding_reference,
        claim.source_claim_binding_identity,
        claim.source_claim_binding_fingerprint,
        claim.claim_reference,
        claim.requirement,
        claim.role,
        claim.ordinal,
    ) == (
        binding.binding_reference,
        binding.identity,
        binding.fingerprint,
        binding.claim_reference,
        binding.requirement,
        binding.role,
        binding.ordinal,
    )
    with pytest.raises(ValidationError):
        claim.ordinal = 2


def test_required_optional_multiple_claims_and_optional_omission():
    section = UPSTREAM["_section"]()
    draft = UPSTREAM["_draft"](section)
    bindings = (
        UPSTREAM["_binding"](draft, section),
        UPSTREAM["_binding"](
            draft,
            section,
            "claim:optional",
            ClaimBindingRequirement.OPTIONAL,
            ordinal=1,
        ),
    )
    source = _source_plan(draft, (UPSTREAM["_binding_set"](draft, section, bindings),))
    assert (
        len(
            _composition(source, _source_context(draft))
            .composed_sections[0]
            .composed_claims
        )
        == 2
    )
    optional_draft = UPSTREAM["_draft"](
        UPSTREAM["_section"](required=(), optional=("claim:optional",))
    )
    optional_plan = _source_plan(optional_draft, ())
    assert (
        _composition(optional_plan, _source_context(optional_draft)).composed_sections
        == ()
    )


def test_multiple_sections_and_cross_section_reuse():
    sections = (
        UPSTREAM["_section"](0, required=("claim:shared",), optional=()),
        UPSTREAM["_section"](1, required=("claim:shared",), optional=()),
    )
    draft = UPSTREAM["_draft"](*sections)
    sets = tuple(
        UPSTREAM["_binding_set"](
            draft, section, (UPSTREAM["_binding"](draft, section, "claim:shared"),)
        )
        for section in sections
    )
    source = _source_plan(draft, sets)
    result = _composition(source, _source_context(draft))
    assert tuple(item.section_reference for item in result.composed_sections) == (
        "section:0",
        "section:1",
    )


def test_canonical_empty_plan_and_explicit_empty_section_rejected():
    draft = UPSTREAM["_draft"](UPSTREAM["_section"](required=(), optional=()))
    source = _source_plan(draft, ())
    result = _composition(source, _source_context(draft))
    assert result.composed_sections == ()
    with pytest.raises(ValidationError):
        ComposedSection.model_validate(
            {
                "identity": f"scout:composed-section:{ZERO}",
                "fingerprint": ZERO,
                "composed_section_reference": "composed-section:empty",
                "source_section_binding_set_reference": "binding-set:empty",
                "source_section_binding_set_identity": f"scout:section-claim-binding-set:{ZERO}",
                "source_section_binding_set_fingerprint": ZERO,
                "draft_reference": source.draft_reference,
                "section_reference": "section:0",
                "composed_claims": (),
            }
        )


@pytest.mark.parametrize(
    "reference",
    (
        "composition-plan:forged",
        "https://attacker.example/composition",
        r"C:\attacker\composition.json",
        f"composition-plan:scout:draft-claim-binding-plan:{'2' * 64}",
    ),
)
def test_resealed_noncanonical_composition_plan_reference_is_rejected(reference):
    changed = _seal_plan(
        _composition().model_copy(update={"composition_plan_reference": reference})
    )
    assert "section-composition-invalid-composition-plan-reference" in _codes(changed)


@pytest.mark.parametrize(
    "reference",
    (
        "composed-section:forged",
        "https://attacker.example/section",
        r"C:\attacker\section.json",
        f"composed-section:scout:section-claim-binding-set:{'2' * 64}",
    ),
)
def test_resealed_noncanonical_composed_section_reference_is_rejected(reference):
    plan = _composition()
    section = _seal_section(
        plan.composed_sections[0].model_copy(
            update={"composed_section_reference": reference}
        )
    )
    changed = _seal_plan(plan.model_copy(update={"composed_sections": (section,)}))
    assert "section-composition-invalid-composed-section-reference" in _codes(changed)


@pytest.mark.parametrize(
    "reference",
    (
        "composed-claim:forged",
        "https://attacker.example/claim",
        r"C:\attacker\claim.json",
        f"composed-claim:scout:claim-binding:{'2' * 64}",
    ),
)
def test_resealed_noncanonical_composed_claim_reference_is_rejected(reference):
    plan = _composition()
    claim = _seal_claim(
        plan.composed_sections[0]
        .composed_claims[0]
        .model_copy(update={"composed_claim_reference": reference})
    )
    assert "section-composition-invalid-composed-claim-reference" in _codes(
        _replace_claim(plan, claim)
    )


@pytest.mark.parametrize(
    ("field", "reference"),
    (
        ("composition_plan_reference", "composition-plan:line\nbreak"),
        ("composition_plan_reference", "x" * 201),
    ),
)
def test_malformed_plan_references_remain_controlled(field, reference):
    changed = _seal_plan(_composition().model_copy(update={field: reference}))
    issues = validate_draft_section_composition_plan(changed, _context())
    assert issues
    assert all(item.code.startswith("section-composition-") for item in issues)
    payload = json.dumps([asdict(item) for item in issues], default=str)
    assert reference not in payload


def test_builder_and_validator_share_canonical_reference_values():
    source = _source_plan()
    result = _composition(source)
    section = result.composed_sections[0]
    claim = section.composed_claims[0]
    source_set = source.section_binding_sets[0]
    source_binding = source_set.bindings[0]
    assert result.composition_plan_reference == f"composition-plan:{source.identity}"
    assert (
        section.composed_section_reference == f"composed-section:{source_set.identity}"
    )
    assert claim.composed_claim_reference == f"composed-claim:{source_binding.identity}"
    assert validate_draft_section_composition_plan(result, _context(source)) == ()


def test_builder_reconstructs_and_rejects_invalid_upstream_state():
    source = _source_plan()
    invalid = UPSTREAM["_binding_seal"](
        source.model_copy(update={"section_binding_sets": ()}),
        UPSTREAM["draft_claim_binding_plan_identity"],
    )
    with pytest.raises(DomainValidationError):
        build_draft_section_composition_plan(invalid, _source_context())
    with pytest.raises(DomainValidationError):
        build_draft_section_composition_plan(_Hostile(KeyError), _source_context())


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_claim_binding_plan_identity",
            f"scout:draft-claim-binding-plan:{'2' * 64}",
            "section-composition-source-plan-identity-mismatch",
        ),
        (
            "source_claim_binding_plan_fingerprint",
            "2" * 64,
            "section-composition-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            f"scout:draft-structure:{'2' * 64}",
            "section-composition-draft-reference-mismatch",
        ),
        (
            "draft_fingerprint",
            "2" * 64,
            "section-composition-draft-fingerprint-mismatch",
        ),
        (
            "normalized_input_reference",
            "input:foreign",
            "section-composition-normalized-input-mismatch",
        ),
    ),
)
def test_plan_lineage_mutations_fail_after_resealing(field, value, code):
    changed = _seal_plan(_composition().model_copy(update={field: value}))
    assert code in _codes(changed)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_section_binding_set_reference",
            "binding-set:foreign",
            "section-composition-source-binding-set-reference-mismatch",
        ),
        (
            "source_section_binding_set_identity",
            f"scout:section-claim-binding-set:{'2' * 64}",
            "section-composition-source-binding-set-mismatch",
        ),
        (
            "source_section_binding_set_fingerprint",
            "2" * 64,
            "section-composition-source-binding-set-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            f"scout:draft-structure:{'2' * 64}",
            "section-composition-section-draft-mismatch",
        ),
        (
            "section_reference",
            "section:foreign",
            "section-composition-section-reference-mismatch",
        ),
    ),
)
def test_section_lineage_mutations_fail_after_resealing(field, value, code):
    plan = _composition()
    section = _seal_section(plan.composed_sections[0].model_copy(update={field: value}))
    changed = _seal_plan(plan.model_copy(update={"composed_sections": (section,)}))
    assert code in _codes(changed)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_claim_binding_reference",
            "binding:foreign",
            "section-composition-source-binding-reference-mismatch",
        ),
        (
            "source_claim_binding_identity",
            f"scout:claim-binding:{'2' * 64}",
            "section-composition-source-binding-mismatch",
        ),
        (
            "source_claim_binding_fingerprint",
            "2" * 64,
            "section-composition-source-binding-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            f"scout:draft-structure:{'2' * 64}",
            "section-composition-claim-draft-mismatch",
        ),
        (
            "section_reference",
            "section:foreign",
            "section-composition-claim-section-mismatch",
        ),
        (
            "claim_reference",
            "claim:foreign",
            "section-composition-claim-reference-mismatch",
        ),
        (
            "requirement",
            ClaimBindingRequirement.OPTIONAL,
            "section-composition-requirement-mismatch",
        ),
        ("role", ClaimBindingRole.SECTION_CONTEXT, "section-composition-role-mismatch"),
        ("ordinal", 1, "section-composition-ordinal-mismatch"),
    ),
)
def test_claim_semantic_mutations_fail_after_resealing(field, value, code):
    plan = _composition()
    claim = _seal_claim(
        plan.composed_sections[0].composed_claims[0].model_copy(update={field: value})
    )
    assert code in _codes(_replace_claim(plan, claim))


def test_missing_extra_and_reordered_sections_are_rejected():
    sections = (UPSTREAM["_section"](0), UPSTREAM["_section"](1))
    draft = UPSTREAM["_draft"](*sections)
    sets = tuple(
        UPSTREAM["_binding_set"](draft, s, (UPSTREAM["_binding"](draft, s),))
        for s in sections
    )
    source = _source_plan(draft, sets)
    plan = _composition(source, _source_context(draft))
    context = _context(source, _source_context(draft))
    missing = _seal_plan(
        plan.model_copy(update={"composed_sections": plan.composed_sections[:1]})
    )
    extra = _seal_plan(
        plan.model_copy(
            update={
                "composed_sections": plan.composed_sections
                + (plan.composed_sections[0],)
            }
        )
    )
    reversed_plan = _seal_plan(
        plan.model_copy(
            update={"composed_sections": tuple(reversed(plan.composed_sections))}
        )
    )
    assert "section-composition-missing-composed-section" in _codes(missing, context)
    assert "section-composition-extra-composed-section" in _codes(extra, context)
    assert "section-composition-invalid-section-order" in _codes(reversed_plan, context)


def test_missing_extra_reordered_and_duplicate_claims_are_rejected():
    section = UPSTREAM["_section"]()
    draft = UPSTREAM["_draft"](section)
    bindings = (
        UPSTREAM["_binding"](draft, section),
        UPSTREAM["_binding"](
            draft,
            section,
            "claim:optional",
            ClaimBindingRequirement.OPTIONAL,
            ordinal=1,
        ),
    )
    source = _source_plan(draft, (UPSTREAM["_binding_set"](draft, section, bindings),))
    plan = _composition(source, _source_context(draft))
    context = _context(source, _source_context(draft))
    base = plan.composed_sections[0]
    variants = {
        "section-composition-missing-composed-claim": base.composed_claims[:1],
        "section-composition-extra-composed-claim": base.composed_claims
        + (base.composed_claims[0],),
        "section-composition-invalid-claim-order": tuple(
            reversed(base.composed_claims)
        ),
    }
    for code, claims in variants.items():
        changed_section = _seal_section(
            base.model_copy(update={"composed_claims": claims})
        )
        changed = _seal_plan(
            plan.model_copy(update={"composed_sections": (changed_section,)})
        )
        assert code in _codes(changed, context)


@pytest.mark.parametrize("missing_index", (0, 1, 2))
def test_each_composed_claim_position_is_required(missing_index):
    section = UPSTREAM["_section"](
        required=("claim:required",),
        optional=("claim:optional", "claim:shared"),
    )
    draft = UPSTREAM["_draft"](section)
    bindings = (
        UPSTREAM["_binding"](draft, section),
        UPSTREAM["_binding"](
            draft,
            section,
            "claim:optional",
            ClaimBindingRequirement.OPTIONAL,
            ordinal=1,
        ),
        UPSTREAM["_binding"](
            draft,
            section,
            "claim:shared",
            ClaimBindingRequirement.OPTIONAL,
            ordinal=2,
        ),
    )
    source = _source_plan(draft, (UPSTREAM["_binding_set"](draft, section, bindings),))
    plan = _composition(source, _source_context(draft))
    claims = tuple(
        item
        for index, item in enumerate(plan.composed_sections[0].composed_claims)
        if index != missing_index
    )
    changed_section = _seal_section(
        plan.composed_sections[0].model_copy(update={"composed_claims": claims})
    )
    changed = _seal_plan(
        plan.model_copy(update={"composed_sections": (changed_section,)})
    )
    assert "section-composition-missing-composed-claim" in _codes(
        changed, _context(source, _source_context(draft))
    )


@pytest.mark.parametrize("missing_index", (0, 1, 2))
def test_each_composed_section_position_is_required(missing_index):
    sections = tuple(UPSTREAM["_section"](index) for index in range(3))
    draft = UPSTREAM["_draft"](*sections)
    sets = tuple(
        UPSTREAM["_binding_set"](
            draft, section, (UPSTREAM["_binding"](draft, section),)
        )
        for section in sections
    )
    source = _source_plan(draft, sets)
    plan = _composition(source, _source_context(draft))
    composed = tuple(
        item
        for index, item in enumerate(plan.composed_sections)
        if index != missing_index
    )
    changed = _seal_plan(plan.model_copy(update={"composed_sections": composed}))
    assert "section-composition-missing-composed-section" in _codes(
        changed, _context(source, _source_context(draft))
    )


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "composed_claim_reference",
            "section-composition-duplicate-composed-claim-reference",
        ),
        ("identity", "section-composition-duplicate-composed-claim-identity"),
        (
            "source_claim_binding_reference",
            "section-composition-duplicate-source-binding-reference",
        ),
        (
            "source_claim_binding_identity",
            "section-composition-duplicate-source-binding-identity",
        ),
        ("claim_reference", "section-composition-duplicate-claim-reference"),
        ("ordinal", "section-composition-duplicate-ordinal"),
    ),
)
def test_claim_duplicate_dimensions_are_explicit(field, code):
    plan = _composition()
    section = plan.composed_sections[0]
    first = section.composed_claims[0]
    if field == "identity":
        second = first
    else:
        second = _seal_claim(
            first.model_copy(
                update={"composed_claim_reference": "composed-claim:second"}
            )
        )
        second = _seal_claim(second.model_copy(update={field: getattr(first, field)}))
    changed_section = _seal_section(
        section.model_copy(update={"composed_claims": (first, second)})
    )
    changed = _seal_plan(
        plan.model_copy(update={"composed_sections": (changed_section,)})
    )
    assert code in _codes(changed)


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "composed_section_reference",
            "section-composition-duplicate-composed-section-reference",
        ),
        ("identity", "section-composition-duplicate-composed-section-identity"),
        ("section_reference", "section-composition-duplicate-section-reference"),
        (
            "source_section_binding_set_reference",
            "section-composition-duplicate-source-binding-set-reference",
        ),
        (
            "source_section_binding_set_identity",
            "section-composition-duplicate-source-binding-set-identity",
        ),
    ),
)
def test_section_duplicate_dimensions_are_explicit(field, code):
    plan = _composition()
    first = plan.composed_sections[0]
    if field == "identity":
        second = first
    else:
        second = _seal_section(
            first.model_copy(
                update={"composed_section_reference": "composed-section:second"}
            )
        )
        second = _seal_section(second.model_copy(update={field: getattr(first, field)}))
    changed = _seal_plan(plan.model_copy(update={"composed_sections": (first, second)}))
    assert code in _codes(changed)


def test_mutable_dictionary_representations_reconstruct_and_are_fresh():
    source = _source_plan()
    plan = _composition(source)
    sections = [item.model_dump() for item in plan.composed_sections]
    copied = plan.model_copy(update={"composed_sections": sections})
    contexts = [source.model_dump()]
    context = _context(source).model_copy(update={"claim_binding_plans": contexts})
    first = validate_draft_section_composition_plan(copied, context)
    sections.append(sections[0])
    second = validate_draft_section_composition_plan(copied, context)
    sections.pop()
    third = validate_draft_section_composition_plan(copied, context)
    assert first == third == () and second


@pytest.mark.parametrize("field", ("composed_sections", "draft_reference"))
@pytest.mark.parametrize("value", (42, True, None, object(), {"bad": True}))
def test_malformed_copied_plan_is_controlled(field, value):
    plan = _composition().model_copy(update={field: value})
    issues = validate_draft_section_composition_plan(plan, _context())
    assert issues and all(
        item.code.startswith("section-composition-") for item in issues
    )


class _Hostile:
    def __init__(self, error_type, reference=None):
        self.error_type = error_type
        self.composition_plan_reference = reference

    def model_dump(self, **_kwargs):
        raise self.error_type("private hostile detail")


@pytest.mark.parametrize(
    "error_type", (KeyError, RuntimeError, LookupError, AssertionError)
)
def test_hostile_reconstruction_is_safe(error_type):
    first = validate_draft_section_composition_plan(_Hostile(error_type), _context())
    second = validate_draft_section_composition_plan(_Hostile(error_type), _context())
    assert first == second
    payload = json.dumps([asdict(item) for item in first], default=str)
    assert "private hostile detail" not in payload and "0x" not in payload


@pytest.mark.parametrize(
    "error_type", (KeyError, RuntimeError, LookupError, AssertionError)
)
def test_hostile_context_reconstruction_is_safe(error_type):
    first = validate_draft_section_composition_plan(
        _composition(), _Hostile(error_type)
    )
    second = validate_draft_section_composition_plan(
        _composition(), _Hostile(error_type)
    )
    assert first == second
    payload = json.dumps([asdict(item) for item in first], default=str)
    assert "private hostile detail" not in payload and "0x" not in payload


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
def test_process_control_exceptions_propagate(error_type):
    with pytest.raises(error_type):
        validate_draft_section_composition_plan(_Hostile(error_type), _context())
    with pytest.raises(error_type):
        validate_draft_section_composition_plan(_composition(), _Hostile(error_type))


def test_identity_fingerprint_field_sensitivity_and_unicode_nfc():
    plan = _composition()
    claim = plan.composed_sections[0].composed_claims[0]
    for field, value in (
        ("composed_claim_reference", "composed-claim:changed"),
        ("claim_reference", "claim:changed"),
        ("role", ClaimBindingRole.SECTION_CONTEXT),
        ("ordinal", 1),
    ):
        changed = claim.model_copy(update={field: value})
        assert compute_composed_claim_identity(changed) != claim.identity
        changed = changed.model_copy(
            update={"identity": compute_composed_claim_identity(changed)}
        )
        assert compute_composed_claim_fingerprint(changed) != claim.fingerprint
    first = claim.model_copy(
        update={"composed_claim_reference": "composed-claim:\u0219"}
    )
    second = claim.model_copy(
        update={"composed_claim_reference": "composed-claim:s\u0326"}
    )
    assert compute_composed_claim_identity(first) == compute_composed_claim_identity(
        second
    )


def test_separate_process_seals_and_diagnostics_are_stable():
    code = "import runpy; n=runpy.run_path('tests/test_editorial_script_composer_section_composition.py'); p=n['_composition'](); print(p.identity,p.fingerprint)"
    assert subprocess.check_output(
        [sys.executable, "-c", code], text=True
    ) == subprocess.check_output([sys.executable, "-c", code], text=True)


def test_public_exports_and_phase_boundary():
    module = importlib.import_module("pastila_scout.editor.script_composer")
    public = {
        "ComposedClaim",
        "ComposedSection",
        "DraftSectionCompositionPlan",
        "SectionCompositionValidationContext",
        "compute_composed_claim_identity",
        "compute_composed_claim_fingerprint",
        "compute_composed_section_identity",
        "compute_composed_section_fingerprint",
        "compute_draft_section_composition_plan_identity",
        "compute_draft_section_composition_plan_fingerprint",
        "build_draft_section_composition_plan",
        "validate_draft_section_composition_plan",
    }
    private = {
        "SectionCompositionDomainModel",
        "_AuthoritativeCompositionInputs",
        "_reconstruct_for_validation",
        "_safe_artifact_reference",
        "_validate_seals",
    }
    assert all(hasattr(module, name) for name in public)
    assert all(not hasattr(module, name) for name in private)
    forbidden = {
        "text",
        "evidence",
        "provider",
        "prompt",
        "score",
        "readiness",
        "timestamp",
        "runtime",
        "url",
    }
    for model in (ComposedClaim, ComposedSection, DraftSectionCompositionPlan):
        assert forbidden.isdisjoint(model.model_fields)
