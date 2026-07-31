"""Freeze-grade adversarial coverage for Phase 5.1 semantic requests."""

import json
import subprocess
import sys
import unicodedata
from dataclasses import asdict

import pytest
from test_editorial_script_composer_llm_request import (
    UPSTREAM,
    _codes,
    _context,
    _request,
    _seal_claim,
    _seal_plan,
    _seal_section,
    _source_context,
)

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    build_draft_llm_request_plan,
    derive_draft_llm_request_plan_identity,
    derive_llm_request_claim_identity,
    derive_llm_request_section_identity,
    validate_draft_llm_request_plan,
)


def _replace_section(plan, index, section):
    sections = list(plan.request_sections)
    sections[index] = section
    return _seal_plan(plan.model_copy(update={"request_sections": tuple(sections)}))


def _replace_claim(plan, section_index, claim_index, claim):
    section = plan.request_sections[section_index]
    claims = list(section.request_claims)
    claims[claim_index] = claim
    section = _seal_section(
        section.model_copy(update={"request_claims": tuple(claims)})
    )
    return _replace_section(plan, section_index, section)


def _multi_section_request(section_count=3, claims_per_section=3):
    bindings = UPSTREAM["UPSTREAM"]
    authoritative_claims = ("claim:required", "claim:optional", "claim:shared")
    sections = tuple(
        bindings["_section"](
            index,
            required=(authoritative_claims[0],),
            optional=authoritative_claims[1:claims_per_section],
        )
        for index in range(section_count)
    )
    draft = bindings["_draft"](*sections)
    binding_sets = []
    for section_index, section in enumerate(sections):
        claims = tuple(
            bindings["_binding"](
                draft,
                section,
                authoritative_claims[claim_index],
                (
                    bindings["ClaimBindingRequirement"].REQUIRED
                    if claim_index == 0
                    else bindings["ClaimBindingRequirement"].OPTIONAL
                ),
                ordinal=claim_index,
            )
            for claim_index in range(claims_per_section)
        )
        binding_sets.append(bindings["_binding_set"](draft, section, claims))
    binding_plan = UPSTREAM["_source_plan"](draft, tuple(binding_sets))
    binding_context = UPSTREAM["_source_context"](draft)
    composition = UPSTREAM["_composition"](binding_plan, binding_context)
    composition_context = UPSTREAM["_context"](binding_plan, binding_context)
    return (
        _request(composition, composition_context),
        _context(composition, composition_context),
        composition,
        composition_context,
    )


def _issues_payload(plan, context):
    return [asdict(issue) for issue in validate_draft_llm_request_plan(plan, context)]


# Each seal regression is independently named so failures identify the artifact level.
def test_stale_plan_identity_is_rejected():
    plan = _request().model_copy(
        update={"request_plan_reference": "llm-request-plan:x"}
    )
    assert "llm-request-invalid-plan-identity" in _codes(plan)


def test_forged_plan_identity_is_rejected():
    plan = _request().model_copy(
        update={"identity": f"scout:draft-llm-request-plan:{'f' * 64}"}
    )
    assert "llm-request-invalid-plan-identity" in _codes(plan)


def test_stale_plan_fingerprint_is_rejected():
    plan = _request().model_copy(
        update={"request_plan_reference": "llm-request-plan:x"}
    )
    plan = plan.model_copy(
        update={"identity": derive_draft_llm_request_plan_identity(plan)}
    )
    assert "llm-request-invalid-plan-fingerprint" in _codes(plan)


def test_forged_plan_fingerprint_is_rejected():
    plan = _request().model_copy(update={"fingerprint": "f" * 64})
    assert "llm-request-invalid-plan-fingerprint" in _codes(plan)


def test_stale_section_identity_is_rejected():
    plan = _request()
    section = plan.request_sections[0].model_copy(
        update={"section_reference": "section:x"}
    )
    assert "llm-request-invalid-section-identity" in _codes(
        _replace_section(plan, 0, section)
    )


def test_forged_section_identity_is_rejected():
    plan = _request()
    section = plan.request_sections[0].model_copy(
        update={"identity": f"scout:llm-request-section:{'f' * 64}"}
    )
    assert "llm-request-invalid-section-identity" in _codes(
        _replace_section(plan, 0, section)
    )


def test_stale_section_fingerprint_is_rejected():
    plan = _request()
    section = plan.request_sections[0].model_copy(
        update={"section_reference": "section:x"}
    )
    section = section.model_copy(
        update={"identity": derive_llm_request_section_identity(section)}
    )
    assert "llm-request-invalid-section-fingerprint" in _codes(
        _replace_section(plan, 0, section)
    )


def test_forged_section_fingerprint_is_rejected():
    plan = _request()
    section = plan.request_sections[0].model_copy(update={"fingerprint": "f" * 64})
    assert "llm-request-invalid-section-fingerprint" in _codes(
        _replace_section(plan, 0, section)
    )


def test_stale_claim_identity_is_rejected():
    plan = _request()
    claim = (
        plan.request_sections[0]
        .request_claims[0]
        .model_copy(update={"claim_reference": "claim:x"})
    )
    assert "llm-request-invalid-claim-identity" in _codes(
        _replace_claim(plan, 0, 0, claim)
    )


def test_forged_claim_identity_is_rejected():
    plan = _request()
    claim = (
        plan.request_sections[0]
        .request_claims[0]
        .model_copy(update={"identity": f"scout:llm-request-claim:{'f' * 64}"})
    )
    assert "llm-request-invalid-claim-identity" in _codes(
        _replace_claim(plan, 0, 0, claim)
    )


def test_stale_claim_fingerprint_is_rejected():
    plan = _request()
    claim = (
        plan.request_sections[0]
        .request_claims[0]
        .model_copy(update={"claim_reference": "claim:x"})
    )
    claim = claim.model_copy(
        update={"identity": derive_llm_request_claim_identity(claim)}
    )
    assert "llm-request-invalid-claim-fingerprint" in _codes(
        _replace_claim(plan, 0, 0, claim)
    )


def test_forged_claim_fingerprint_is_rejected():
    plan = _request()
    claim = (
        plan.request_sections[0]
        .request_claims[0]
        .model_copy(update={"fingerprint": "f" * 64})
    )
    assert "llm-request-invalid-claim-fingerprint" in _codes(
        _replace_claim(plan, 0, 0, claim)
    )


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "request_section_reference",
            "llm-request-duplicate-request-section-reference",
        ),
        ("identity", "llm-request-duplicate-request-section-identity"),
        (
            "source_composed_section_reference",
            "llm-request-duplicate-source-section-reference",
        ),
        (
            "source_composed_section_identity",
            "llm-request-duplicate-source-section-identity",
        ),
        ("section_reference", "llm-request-duplicate-section-reference"),
    ),
)
def test_each_section_duplicate_dimension_is_reported(field, code):
    plan, context, _, _ = _multi_section_request()
    first, second = plan.request_sections[:2]
    second = second.model_copy(update={field: getattr(first, field)})
    changed = _replace_section(plan, 1, second)
    assert code in _codes(changed, context)


def test_duplicate_complete_request_section_is_not_hidden_by_mapping():
    plan, context, _, _ = _multi_section_request()
    sections = (
        plan.request_sections[0],
        plan.request_sections[0],
        *plan.request_sections[2:],
    )
    changed = _seal_plan(plan.model_copy(update={"request_sections": sections}))
    assert "llm-request-duplicate-request-section-identity" in _codes(changed, context)


@pytest.mark.parametrize(
    ("field", "code"),
    (
        ("request_claim_reference", "llm-request-duplicate-request-claim-reference"),
        ("identity", "llm-request-duplicate-request-claim-identity"),
        (
            "source_composed_claim_reference",
            "llm-request-duplicate-source-claim-reference",
        ),
        (
            "source_composed_claim_identity",
            "llm-request-duplicate-source-claim-identity",
        ),
        ("claim_reference", "llm-request-duplicate-claim-reference"),
        ("ordinal", "llm-request-duplicate-ordinal"),
    ),
)
def test_each_claim_duplicate_dimension_is_reported(field, code):
    plan, context, _, _ = _multi_section_request()
    section = plan.request_sections[0]
    first, second = section.request_claims[:2]
    second = second.model_copy(update={field: getattr(first, field)})
    changed = _replace_claim(plan, 0, 1, second)
    assert code in _codes(changed, context)


def test_duplicate_complete_request_claim_is_not_hidden_by_mapping():
    plan, context, _, _ = _multi_section_request()
    section = plan.request_sections[0]
    claims = (
        section.request_claims[0],
        section.request_claims[0],
        *section.request_claims[2:],
    )
    changed_section = _seal_section(
        section.model_copy(update={"request_claims": claims})
    )
    assert "llm-request-duplicate-request-claim-identity" in _codes(
        _replace_section(plan, 0, changed_section), context
    )


@pytest.mark.parametrize("permutation", ((1, 0, 2), (2, 1, 0), (0, 2, 1)))
def test_section_swap_reversal_and_partial_reorder_are_rejected(permutation):
    plan, context, _, _ = _multi_section_request()
    sections = tuple(plan.request_sections[index] for index in permutation)
    changed = _seal_plan(plan.model_copy(update={"request_sections": sections}))
    assert "llm-request-invalid-section-order" in _codes(changed, context)


def test_correct_section_tuple_with_forged_source_lineage_is_rejected():
    plan, context, _, _ = _multi_section_request()
    section = _seal_section(
        plan.request_sections[1].model_copy(
            update={
                "source_composed_section_identity": plan.request_sections[
                    0
                ].source_composed_section_identity
            }
        )
    )
    changed = _replace_section(plan, 1, section)
    codes = _codes(changed, context)
    assert "llm-request-invalid-section-order" in codes
    assert "llm-request-duplicate-source-section-identity" in codes


@pytest.mark.parametrize("permutation", ((1, 0, 2), (2, 1, 0), (0, 2, 1)))
def test_claim_swap_reversal_and_partial_reorder_are_rejected(permutation):
    plan, context, _, _ = _multi_section_request()
    section = plan.request_sections[0]
    claims = tuple(section.request_claims[index] for index in permutation)
    changed_section = _seal_section(
        section.model_copy(update={"request_claims": claims})
    )
    assert "llm-request-invalid-claim-order" in _codes(
        _replace_section(plan, 0, changed_section), context
    )


def test_correct_claim_tuple_with_forged_ordinals_is_rejected():
    plan, context, _, _ = _multi_section_request()
    claim = _seal_claim(
        plan.request_sections[0].request_claims[1].model_copy(update={"ordinal": 7})
    )
    changed = _replace_claim(plan, 0, 1, claim)
    codes = _codes(changed, context)
    assert "llm-request-invalid-ordinal-sequence" in codes
    assert "llm-request-ordinal-mismatch" in codes


def test_reordered_claims_with_resealed_apparently_correct_ordinals_fail():
    plan, context, _, _ = _multi_section_request()
    section = plan.request_sections[0]
    claims = tuple(
        _seal_claim(claim.model_copy(update={"ordinal": index}))
        for index, claim in enumerate(reversed(section.request_claims))
    )
    changed_section = _seal_section(
        section.model_copy(update={"request_claims": claims})
    )
    codes = _codes(_replace_section(plan, 0, changed_section), context)
    assert "llm-request-invalid-claim-order" in codes


@pytest.mark.parametrize("mode", ("foreign-section", "unique", "middle"))
def test_extra_claims_independent_of_duplicate_attacks_are_rejected(mode):
    plan, context, _, _ = _multi_section_request()
    section = plan.request_sections[0]
    foreign = plan.request_sections[1].request_claims[0]
    if mode == "unique":
        foreign = _seal_claim(
            foreign.model_copy(
                update={
                    "request_claim_reference": "llm-request-claim:unique-extra",
                    "claim_reference": "claim:unique-extra",
                    "ordinal": 99,
                }
            )
        )
    claims = list(section.request_claims)
    claims.insert(1 if mode == "middle" else len(claims), foreign)
    changed_section = _seal_section(
        section.model_copy(update={"request_claims": tuple(claims)})
    )
    codes = _codes(_replace_section(plan, 0, changed_section), context)
    assert "llm-request-extra-claim" in codes


def test_foreign_claim_from_another_valid_plan_is_rejected():
    plan, context, _, _ = _multi_section_request()
    other, _, _, _ = _multi_section_request(section_count=2, claims_per_section=2)
    foreign = _seal_claim(
        other.request_sections[1]
        .request_claims[1]
        .model_copy(
            update={"request_claim_reference": "llm-request-claim:other-plan-extra"}
        )
    )
    section = plan.request_sections[0]
    changed_section = _seal_section(
        section.model_copy(
            update={"request_claims": (*section.request_claims, foreign)}
        )
    )
    assert "llm-request-extra-claim" in _codes(
        _replace_section(plan, 0, changed_section), context
    )


def test_unicode_semantic_references_are_preserved_and_sealed_deterministically():
    bindings = UPSTREAM["UPSTREAM"]
    values = ("știre-țară", "s\u0326tire-t\u0326ară", "東京", "știre-🙂")
    artifacts = []
    for value in values:
        section = bindings["_section"](required=("claim:required",), optional=())
        section = bindings["_draft_seal"](
            section.model_copy(update={"section_reference": f"section:{value}"}),
            bindings["draft_section_identity"],
        )
        draft = bindings["_draft"](section)
        binding_plan = UPSTREAM["_source_plan"](
            draft,
            (
                bindings["_binding_set"](
                    draft, section, (bindings["_binding"](draft, section),)
                ),
            ),
        )
        binding_context = UPSTREAM["_source_context"](draft)
        composition = UPSTREAM["_composition"](binding_plan, binding_context)
        composition_context = UPSTREAM["_context"](binding_plan, binding_context)
        artifact = _request(composition, composition_context)
        assert artifact.request_sections[0].request_claims[
            0
        ].section_reference == unicodedata.normalize("NFC", f"section:{value}")
        assert (
            validate_draft_llm_request_plan(
                artifact, _context(composition, composition_context)
            )
            == ()
        )
        artifacts.append(artifact)
    assert artifacts[0].identity == artifacts[1].identity
    assert artifacts[0].fingerprint == artifacts[1].fingerprint
    assert unicodedata.normalize("NFC", values[0]) == unicodedata.normalize(
        "NFC", values[1]
    )
    assert _request() == _request()


@pytest.mark.parametrize(
    ("level", "value"),
    tuple(
        (level, value)
        for level in ("plan", "section", "claim")
        for value in (
            "https://user:secret@example.test/item?token=secret",
            r"C:\Users\private\secret.txt",
            "/home/private/secret.txt",
            "line\nnext\tcontrol\x01",
            "0x7ffdeadbeef traceback RuntimeError: secret",
            "ș-secret\n🙂" + "x" * 180,
        )
    ),
)
def test_complete_diagnostics_redact_unsafe_caller_values(level, value):
    plan = _request()
    if level == "plan":
        changed = _seal_plan(plan.model_copy(update={"request_plan_reference": value}))
    elif level == "section":
        section = _seal_section(
            plan.request_sections[0].model_copy(
                update={"request_section_reference": value}
            )
        )
        changed = _replace_section(plan, 0, section)
    else:
        claim = _seal_claim(
            plan.request_sections[0]
            .request_claims[0]
            .model_copy(update={"request_claim_reference": value})
        )
        changed = _replace_claim(plan, 0, 0, claim)
    issues = validate_draft_llm_request_plan(changed, _context())
    rendered = json.dumps(
        [asdict(issue) for issue in issues], ensure_ascii=False, default=str
    )
    assert issues and value not in rendered
    assert len(rendered) < 20_000


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
def test_reconstruction_exception_diagnostics_do_not_leak_hostile_text(error_type):
    class Hostile:
        def model_dump(self, **_kwargs):
            raise error_type(r"secret C:\Users\private 0x7ffdeadbeef\nTraceback")

    issues = validate_draft_llm_request_plan(Hostile(), _context())
    rendered = json.dumps([asdict(issue) for issue in issues], default=str)
    assert "secret" not in rendered and "0x7ffdeadbeef" not in rendered


def test_complete_diagnostics_are_identical_across_processes():
    code = (
        "import json,runpy; from dataclasses import asdict; "
        "n=runpy.run_path('tests/test_editorial_script_composer_llm_request.py'); "
        "p=n['_seal_plan'](n['_request']().model_copy(update={'request_plan_reference':'llm-request-plan:forged'})); "
        "i=n['validate_draft_llm_request_plan'](p,n['_context']()); "
        "print(json.dumps([asdict(x) for x in i],ensure_ascii=False,sort_keys=True,separators=(',',':')))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second


@pytest.mark.parametrize(
    "mutation",
    (
        "plan-identity",
        "plan-fingerprint",
        "section-identity",
        "section-fingerprint",
        "claim-identity",
        "claim-fingerprint",
        "missing-section",
        "reordered-sections",
        "reordered-claims",
        "section-lineage",
        "claim-lineage",
        "draft-lineage",
    ),
)
def test_builder_rejects_multiple_malformed_authoritative_phase_4_3_classes(mutation):
    source_context = _source_context()
    if mutation in {"reordered-sections", "missing-section"}:
        _, _, source, source_context = _multi_section_request()
    else:
        source = UPSTREAM["_composition"]()
    if mutation == "plan-identity":
        source = source.model_copy(
            update={"identity": f"scout:draft-section-composition-plan:{'f' * 64}"}
        )
    elif mutation == "plan-fingerprint":
        source = source.model_copy(update={"fingerprint": "f" * 64})
    elif mutation.startswith("section-"):
        section = source.composed_sections[0]
        if mutation == "section-identity":
            section = section.model_copy(
                update={"identity": f"scout:composed-section:{'f' * 64}"}
            )
        elif mutation == "section-fingerprint":
            section = section.model_copy(update={"fingerprint": "f" * 64})
        else:
            section = UPSTREAM["_seal_section"](
                section.model_copy(update={"section_reference": "section:foreign"})
            )
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"composed_sections": (section, *source.composed_sections[1:])}
            )
        )
    elif mutation.startswith("claim-") or mutation == "reordered-claims":
        if mutation == "reordered-claims":
            _, _, source, source_context = _multi_section_request()
        section = source.composed_sections[0]
        claim = section.composed_claims[0]
        if mutation == "claim-identity":
            claim = claim.model_copy(
                update={"identity": f"scout:composed-claim:{'f' * 64}"}
            )
            claims = (claim, *section.composed_claims[1:])
        elif mutation == "claim-fingerprint":
            claim = claim.model_copy(update={"fingerprint": "f" * 64})
            claims = (claim, *section.composed_claims[1:])
        elif mutation == "claim-lineage":
            claim = UPSTREAM["_seal_claim"](
                claim.model_copy(update={"section_reference": "section:foreign"})
            )
            claims = (claim, *section.composed_claims[1:])
        else:
            claims = tuple(reversed(section.composed_claims))
        section = UPSTREAM["_seal_section"](
            section.model_copy(update={"composed_claims": claims})
        )
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"composed_sections": (section, *source.composed_sections[1:])}
            )
        )
    elif mutation == "missing-section":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"composed_sections": source.composed_sections[1:]}
            )
        )
    elif mutation == "reordered-sections":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"composed_sections": tuple(reversed(source.composed_sections))}
            )
        )
    else:
        source = UPSTREAM["_seal_plan"](
            source.model_copy(update={"draft_reference": "draft:foreign"})
        )
    with pytest.raises(DomainValidationError):
        build_draft_llm_request_plan(source, source_context)
