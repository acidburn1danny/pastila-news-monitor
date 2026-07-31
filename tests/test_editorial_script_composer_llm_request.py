"""Adversarial Phase 5.1 deterministic semantic-request tests."""

import importlib
import json
import runpy
import subprocess
import sys
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    DraftLLMRequestPlan,
    LLMRequestClaim,
    LLMRequestSection,
    LLMRequestValidationContext,
    build_draft_llm_request_plan,
    derive_draft_llm_request_plan_fingerprint,
    derive_draft_llm_request_plan_identity,
    derive_llm_request_claim_fingerprint,
    derive_llm_request_claim_identity,
    derive_llm_request_section_fingerprint,
    derive_llm_request_section_identity,
    validate_draft_llm_request_plan,
)

UPSTREAM = runpy.run_path("tests/test_editorial_script_composer_section_composition.py")


def _source():
    return UPSTREAM["_composition"]()


def _source_context():
    return UPSTREAM["_context"]()


def _request(source=None, context=None):
    return build_draft_llm_request_plan(
        source or _source(), context or _source_context()
    )


def _context(source=None, source_context=None):
    return LLMRequestValidationContext(
        composition_plans=(source or _source(),),
        section_composition_validation_context=source_context or _source_context(),
    )


def _seal_claim(value):
    value = value.model_copy(
        update={"identity": derive_llm_request_claim_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_llm_request_claim_fingerprint(value)}
    )


def _seal_section(value):
    value = value.model_copy(
        update={"identity": derive_llm_request_section_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_llm_request_section_fingerprint(value)}
    )


def _seal_plan(value):
    value = value.model_copy(
        update={"identity": derive_draft_llm_request_plan_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_draft_llm_request_plan_fingerprint(value)}
    )


def _replace_claim(plan, claim):
    section = _seal_section(
        plan.request_sections[0].model_copy(update={"request_claims": (claim,)})
    )
    return _seal_plan(plan.model_copy(update={"request_sections": (section,)}))


def _codes(plan, context=None):
    return {
        item.code
        for item in validate_draft_llm_request_plan(plan, context or _context())
    }


def test_valid_projection_is_self_contained_immutable_and_deterministic():
    source = _source()
    first = _request(source)
    second = _request(source)
    assert first == second
    assert validate_draft_llm_request_plan(first, _context(source)) == ()
    source_claim = source.composed_sections[0].composed_claims[0]
    claim = first.request_sections[0].request_claims[0]
    assert (
        claim.claim_reference,
        claim.requirement,
        claim.role,
        claim.ordinal,
    ) == (
        source_claim.claim_reference,
        str(source_claim.requirement),
        str(source_claim.role),
        source_claim.ordinal,
    )
    with pytest.raises(ValidationError):
        claim.ordinal = 9


def test_builder_rejects_invalid_authoritative_upstream():
    source = _source()
    invalid = UPSTREAM["_seal_plan"](
        source.model_copy(update={"composition_plan_reference": "composition-plan:x"})
    )
    with pytest.raises(DomainValidationError):
        build_draft_llm_request_plan(invalid, _source_context())


def test_canonical_empty_projection():
    empty_draft = UPSTREAM["UPSTREAM"]["_draft"](
        UPSTREAM["UPSTREAM"]["_section"](required=(), optional=())
    )
    binding = UPSTREAM["_source_plan"](empty_draft, ())
    binding_context = UPSTREAM["_source_context"](empty_draft)
    composition = UPSTREAM["_composition"](binding, binding_context)
    composition_context = UPSTREAM["_context"](binding, binding_context)
    result = _request(composition, composition_context)
    assert result.request_sections == ()
    assert (
        validate_draft_llm_request_plan(
            result, _context(composition, composition_context)
        )
        == ()
    )


@pytest.mark.parametrize(
    ("level", "reference", "code"),
    tuple(
        (level, value, code)
        for level, code, prefix, kind in (
            (
                "plan",
                "llm-request-invalid-request-plan-reference",
                "llm-request-plan",
                "draft-section-composition-plan",
            ),
            (
                "section",
                "llm-request-invalid-request-section-reference",
                "llm-request-section",
                "composed-section",
            ),
            (
                "claim",
                "llm-request-invalid-request-claim-reference",
                "llm-request-claim",
                "composed-claim",
            ),
        )
        for value in (
            f"{prefix}:forged",
            f"{prefix}:scout:{kind}:{'2' * 64}",
            "https://attacker.example/item",
            r"C:\attacker\item.json",
            "/tmp/attacker/item.json",
        )
    ),
)
def test_resealed_noncanonical_references_fail(level, reference, code):
    plan = _request()
    if level == "plan":
        changed = _seal_plan(
            plan.model_copy(update={"request_plan_reference": reference})
        )
    elif level == "section":
        section = _seal_section(
            plan.request_sections[0].model_copy(
                update={"request_section_reference": reference}
            )
        )
        changed = _seal_plan(plan.model_copy(update={"request_sections": (section,)}))
    else:
        claim = _seal_claim(
            plan.request_sections[0]
            .request_claims[0]
            .model_copy(update={"request_claim_reference": reference})
        )
        changed = _replace_claim(plan, claim)
    issues = validate_draft_llm_request_plan(changed, _context())
    assert code in {item.code for item in issues}
    if "/" in reference or "\\" in reference:
        assert reference not in json.dumps(
            [asdict(item) for item in issues], default=str
        )


@pytest.mark.parametrize("reference", ("llm-request-plan:line\nbreak", "x" * 201))
def test_malformed_reference_reconstruction_is_safe(reference):
    changed = _seal_plan(
        _request().model_copy(update={"request_plan_reference": reference})
    )
    issues = validate_draft_llm_request_plan(changed, _context())
    assert issues and reference not in json.dumps(
        [asdict(item) for item in issues], default=str
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_composition_plan_identity",
            f"scout:draft-section-composition-plan:{'2' * 64}",
            "llm-request-source-plan-identity-mismatch",
        ),
        (
            "source_composition_plan_fingerprint",
            "2" * 64,
            "llm-request-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            f"scout:draft-structure:{'2' * 64}",
            "llm-request-draft-reference-mismatch",
        ),
        ("draft_fingerprint", "2" * 64, "llm-request-draft-fingerprint-mismatch"),
        (
            "normalized_input_reference",
            "input:foreign",
            "llm-request-normalized-input-mismatch",
        ),
    ),
)
def test_plan_lineage_is_authoritative(field, value, code):
    changed = _seal_plan(_request().model_copy(update={field: value}))
    assert code in _codes(changed)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_composed_section_reference",
            "composed-section:foreign",
            "llm-request-source-section-reference-mismatch",
        ),
        (
            "source_composed_section_identity",
            f"scout:composed-section:{'2' * 64}",
            "llm-request-source-section-mismatch",
        ),
        (
            "source_composed_section_fingerprint",
            "2" * 64,
            "llm-request-source-section-fingerprint-mismatch",
        ),
        (
            "section_reference",
            "section:foreign",
            "llm-request-section-reference-mismatch",
        ),
        (
            "normalized_input_reference",
            "input:foreign",
            "llm-request-section-input-mismatch",
        ),
    ),
)
def test_section_lineage_is_authoritative(field, value, code):
    plan = _request()
    section = _seal_section(plan.request_sections[0].model_copy(update={field: value}))
    changed = _seal_plan(plan.model_copy(update={"request_sections": (section,)}))
    assert code in _codes(changed)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "source_composed_claim_reference",
            "composed-claim:foreign",
            "llm-request-source-claim-reference-mismatch",
        ),
        (
            "source_composed_claim_identity",
            f"scout:composed-claim:{'2' * 64}",
            "llm-request-source-claim-mismatch",
        ),
        (
            "source_composed_claim_fingerprint",
            "2" * 64,
            "llm-request-source-claim-fingerprint-mismatch",
        ),
        (
            "claim_reference",
            "claim:foreign",
            "llm-request-semantic-claim-reference-mismatch",
        ),
        ("requirement", "optional", "llm-request-requirement-mismatch"),
        ("role", "section_context", "llm-request-role-mismatch"),
        ("ordinal", 1, "llm-request-ordinal-mismatch"),
    ),
)
def test_claim_payload_and_lineage_are_authoritative(field, value, code):
    plan = _request()
    claim = _seal_claim(
        plan.request_sections[0].request_claims[0].model_copy(update={field: value})
    )
    assert code in _codes(_replace_claim(plan, claim))


def test_missing_extra_duplicate_and_order_corruption_fail():
    plan = _request()
    section = plan.request_sections[0]
    claim = section.request_claims[0]
    missing = _seal_plan(plan.model_copy(update={"request_sections": ()}))
    extra = _seal_plan(plan.model_copy(update={"request_sections": (section, section)}))
    duplicated_section = _seal_section(
        section.model_copy(update={"request_claims": (claim, claim)})
    )
    duplicated = _seal_plan(
        plan.model_copy(update={"request_sections": (duplicated_section,)})
    )
    assert "llm-request-missing-section" in _codes(missing)
    assert "llm-request-extra-section" in _codes(extra)
    assert "llm-request-duplicate-request-claim-identity" in _codes(duplicated)


def _multi_claim_request():
    bindings = UPSTREAM["UPSTREAM"]
    section = bindings["_section"](
        required=("claim:required",),
        optional=("claim:optional", "claim:shared"),
    )
    draft = bindings["_draft"](section)
    source_bindings = (
        bindings["_binding"](draft, section),
        bindings["_binding"](
            draft,
            section,
            "claim:optional",
            bindings["ClaimBindingRequirement"].OPTIONAL,
            ordinal=1,
        ),
        bindings["_binding"](
            draft,
            section,
            "claim:shared",
            bindings["ClaimBindingRequirement"].OPTIONAL,
            ordinal=2,
        ),
    )
    binding_plan = UPSTREAM["_source_plan"](
        draft, (bindings["_binding_set"](draft, section, source_bindings),)
    )
    binding_context = UPSTREAM["_source_context"](draft)
    composition = UPSTREAM["_composition"](binding_plan, binding_context)
    composition_context = UPSTREAM["_context"](binding_plan, binding_context)
    return _request(composition, composition_context), _context(
        composition, composition_context
    )


@pytest.mark.parametrize("missing_index", (0, 1, 2))
def test_each_request_claim_position_is_required(missing_index):
    plan, context = _multi_claim_request()
    section = plan.request_sections[0]
    claims = tuple(
        item
        for index, item in enumerate(section.request_claims)
        if index != missing_index
    )
    changed_section = _seal_section(
        section.model_copy(update={"request_claims": claims})
    )
    changed = _seal_plan(
        plan.model_copy(update={"request_sections": (changed_section,)})
    )
    assert "llm-request-missing-claim" in _codes(changed, context)


def test_request_claim_order_is_not_repaired():
    plan, context = _multi_claim_request()
    section = plan.request_sections[0]
    changed_section = _seal_section(
        section.model_copy(
            update={"request_claims": tuple(reversed(section.request_claims))}
        )
    )
    changed = _seal_plan(
        plan.model_copy(update={"request_sections": (changed_section,)})
    )
    assert "llm-request-invalid-claim-order" in _codes(changed, context)


@pytest.mark.parametrize("missing_index", (0, 1, 2))
def test_each_request_section_position_is_required(missing_index):
    bindings = UPSTREAM["UPSTREAM"]
    sections = tuple(bindings["_section"](index) for index in range(3))
    draft = bindings["_draft"](*sections)
    sets = tuple(
        bindings["_binding_set"](
            draft, section, (bindings["_binding"](draft, section),)
        )
        for section in sections
    )
    binding_plan = UPSTREAM["_source_plan"](draft, sets)
    binding_context = UPSTREAM["_source_context"](draft)
    composition = UPSTREAM["_composition"](binding_plan, binding_context)
    composition_context = UPSTREAM["_context"](binding_plan, binding_context)
    plan = _request(composition, composition_context)
    context = _context(composition, composition_context)
    request_sections = tuple(
        item
        for index, item in enumerate(plan.request_sections)
        if index != missing_index
    )
    changed = _seal_plan(plan.model_copy(update={"request_sections": request_sections}))
    assert "llm-request-missing-section" in _codes(changed, context)


def test_every_semantic_field_changes_identity_and_fingerprint():
    plan = _request()
    section = plan.request_sections[0]
    claim = section.request_claims[0]
    claim_updates = {
        "request_claim_reference": "llm-request-claim:x",
        "source_composed_claim_reference": "composed-claim:x",
        "source_composed_claim_identity": f"scout:composed-claim:{'2' * 64}",
        "source_composed_claim_fingerprint": "2" * 64,
        "source_composed_section_reference": "composed-section:x",
        "source_composed_section_identity": f"scout:composed-section:{'2' * 64}",
        "source_composed_section_fingerprint": "2" * 64,
        "source_composition_plan_reference": "composition-plan:x",
        "source_composition_plan_identity": f"scout:draft-section-composition-plan:{'2' * 64}",
        "source_composition_plan_fingerprint": "2" * 64,
        "draft_reference": f"scout:draft-structure:{'2' * 64}",
        "normalized_input_reference": "input:x",
        "section_reference": "section:x",
        "claim_reference": "claim:x",
        "requirement": "optional",
        "role": "section_context",
        "ordinal": 1,
    }
    changed_claim = _seal_claim(
        claim.model_copy(update={"request_claim_reference": "llm-request-claim:x"})
    )
    section_updates = {
        "request_section_reference": "llm-request-section:x",
        "source_composed_section_reference": "composed-section:x",
        "source_composed_section_identity": f"scout:composed-section:{'2' * 64}",
        "source_composed_section_fingerprint": "2" * 64,
        "source_composition_plan_reference": "composition-plan:x",
        "source_composition_plan_identity": f"scout:draft-section-composition-plan:{'2' * 64}",
        "source_composition_plan_fingerprint": "2" * 64,
        "draft_reference": f"scout:draft-structure:{'2' * 64}",
        "normalized_input_reference": "input:x",
        "section_reference": "section:x",
        "request_claims": (changed_claim,),
    }
    changed_section = _seal_section(
        section.model_copy(
            update={"request_section_reference": "llm-request-section:x"}
        )
    )
    plan_updates = {
        "request_plan_reference": "llm-request-plan:x",
        "source_composition_plan_reference": "composition-plan:x",
        "source_composition_plan_identity": f"scout:draft-section-composition-plan:{'2' * 64}",
        "source_composition_plan_fingerprint": "2" * 64,
        "draft_reference": f"scout:draft-structure:{'2' * 64}",
        "draft_fingerprint": "2" * 64,
        "normalized_input_reference": "input:x",
        "request_sections": (changed_section,),
    }
    cases = (
        (
            claim,
            claim_updates,
            derive_llm_request_claim_identity,
            derive_llm_request_claim_fingerprint,
        ),
        (
            section,
            section_updates,
            derive_llm_request_section_identity,
            derive_llm_request_section_fingerprint,
        ),
        (
            plan,
            plan_updates,
            derive_draft_llm_request_plan_identity,
            derive_draft_llm_request_plan_fingerprint,
        ),
    )
    for artifact, updates, identity_function, fingerprint_function in cases:
        for field, value in updates.items():
            changed = artifact.model_copy(update={field: value})
            identity = identity_function(changed)
            resealed = changed.model_copy(update={"identity": identity})
            assert identity != artifact.identity, field
            assert fingerprint_function(resealed) != artifact.fingerprint, field


def test_copied_mutable_representations_are_fresh_snapshots():
    source = _source()
    plan = _request(source)
    sections = [item.model_dump() for item in plan.request_sections]
    copied = plan.model_copy(update={"request_sections": sections})
    plans = [source.model_dump()]
    context = _context(source).model_copy(update={"composition_plans": plans})
    first = validate_draft_llm_request_plan(copied, context)
    sections.append(sections[0])
    second = validate_draft_llm_request_plan(copied, context)
    sections.pop()
    third = validate_draft_llm_request_plan(copied, context)
    assert first == third == () and second


class _Hostile:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, **_kwargs):
        raise self.error_type("private hostile detail")


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize("side", ("plan", "context"))
def test_ordinary_hostile_exceptions_are_contained(error_type, side):
    issues = (
        validate_draft_llm_request_plan(_Hostile(error_type), _context())
        if side == "plan"
        else validate_draft_llm_request_plan(_request(), _Hostile(error_type))
    )
    payload = json.dumps([asdict(item) for item in issues], default=str)
    assert issues and "private hostile detail" not in payload and "0x" not in payload


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize("side", ("plan", "context"))
def test_process_control_exceptions_propagate(error_type, side):
    with pytest.raises(error_type):
        if side == "plan":
            validate_draft_llm_request_plan(_Hostile(error_type), _context())
        else:
            validate_draft_llm_request_plan(_request(), _Hostile(error_type))


def test_separate_process_output_is_stable():
    code = "import runpy,json; n=runpy.run_path('tests/test_editorial_script_composer_llm_request.py'); p=n['_request'](); print(json.dumps(p.model_dump(),default=str,sort_keys=True))"
    assert subprocess.check_output(
        [sys.executable, "-c", code], text=True
    ) == subprocess.check_output([sys.executable, "-c", code], text=True)


def test_public_api_and_phase_boundary():
    module = importlib.import_module("pastila_scout.editor.script_composer")
    public = {
        "LLMRequestClaim",
        "LLMRequestSection",
        "DraftLLMRequestPlan",
        "LLMRequestValidationContext",
        "build_draft_llm_request_plan",
        "validate_draft_llm_request_plan",
        "derive_llm_request_claim_identity",
        "derive_llm_request_section_identity",
        "derive_draft_llm_request_plan_identity",
        "derive_llm_request_claim_fingerprint",
        "derive_llm_request_section_fingerprint",
        "derive_draft_llm_request_plan_fingerprint",
    }
    private = {
        "LLMRequestDomainModel",
        "_AuthoritativeLLMRequestInputs",
        "_canonical_llm_request_plan_reference",
        "_reconstruct_for_validation",
        "_safe_artifact_reference",
        "_validate_seals",
    }
    assert all(hasattr(module, name) for name in public)
    assert all(not hasattr(module, name) for name in private)
    forbidden = {
        "prompt",
        "provider",
        "model_name",
        "temperature",
        "top_p",
        "tokens",
        "retry",
        "generated_text",
        "response",
    }
    for model in (LLMRequestClaim, LLMRequestSection, DraftLLMRequestPlan):
        assert forbidden.isdisjoint(model.model_fields)
