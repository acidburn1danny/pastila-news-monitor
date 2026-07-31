"""Adversarial Phase 5.2 deterministic prompt-rendering tests."""

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
    DraftRenderedPromptPlan,
    RenderedPromptMessage,
    RenderedPromptSection,
    RenderedPromptValidationContext,
    build_draft_rendered_prompt_plan,
    derive_draft_rendered_prompt_plan_fingerprint,
    derive_draft_rendered_prompt_plan_identity,
    derive_rendered_prompt_message_fingerprint,
    derive_rendered_prompt_message_identity,
    derive_rendered_prompt_section_fingerprint,
    derive_rendered_prompt_section_identity,
    validate_draft_rendered_prompt_plan,
)

UPSTREAM = runpy.run_path("tests/test_editorial_script_composer_llm_request.py")
FREEZE = runpy.run_path("tests/test_editorial_script_composer_llm_request_freeze.py")


def _source():
    return UPSTREAM["_request"]()


def _source_context():
    return UPSTREAM["_context"]()


def _plan(source=None, source_context=None):
    return build_draft_rendered_prompt_plan(
        source or _source(), source_context or _source_context()
    )


def _context(source=None, source_context=None):
    return RenderedPromptValidationContext(
        request_plans=(source or _source(),),
        llm_request_validation_context=source_context or _source_context(),
    )


def _seal_message(value):
    value = value.model_copy(
        update={"identity": derive_rendered_prompt_message_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_rendered_prompt_message_fingerprint(value)}
    )


def _seal_section(value):
    value = value.model_copy(
        update={"identity": derive_rendered_prompt_section_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_rendered_prompt_section_fingerprint(value)}
    )


def _seal_plan(value):
    value = value.model_copy(
        update={"identity": derive_draft_rendered_prompt_plan_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_draft_rendered_prompt_plan_fingerprint(value)}
    )


def _replace_section(plan, index, section):
    sections = list(plan.rendered_sections)
    sections[index] = section
    return _seal_plan(plan.model_copy(update={"rendered_sections": tuple(sections)}))


def _replace_message(plan, section_index, message_index, message):
    section = plan.rendered_sections[section_index]
    messages = list(section.rendered_messages)
    messages[message_index] = message
    section = _seal_section(
        section.model_copy(update={"rendered_messages": tuple(messages)})
    )
    return _replace_section(plan, section_index, section)


def _codes(plan, context=None):
    return {
        issue.code
        for issue in validate_draft_rendered_prompt_plan(plan, context or _context())
    }


def _multi():
    request, request_context, _, _ = FREEZE["_multi_section_request"]()
    return _plan(request, request_context), _context(request, request_context)


def test_rendering_is_exact_self_contained_immutable_and_deterministic():
    source = _source()
    first = _plan(source)
    second = _plan(source)
    assert first == second
    assert validate_draft_rendered_prompt_plan(first, _context(source)) == ()
    message = first.rendered_sections[0].rendered_messages[0]
    assert message.rendering_role == "generation"
    assert message.rendered_text == (
        "<request-claim>\n"
        "claim-reference: claim:required\n"
        "requirement: required\n"
        "role: section_anchor\n"
        "ordinal: 0\n"
        "</request-claim>"
    )
    assert "\r" not in message.rendered_text
    assert all(not line.endswith(" ") for line in message.rendered_text.split("\n"))
    with pytest.raises(ValidationError):
        message.ordinal = 2


def test_builder_rejects_invalid_phase_5_1_authority():
    source = _source().model_copy(update={"fingerprint": "f" * 64})
    with pytest.raises(DomainValidationError):
        build_draft_rendered_prompt_plan(source, _source_context())


@pytest.mark.parametrize(
    "text",
    (
        "different",
        "<request-claim>\r\nclaim-reference: claim:required\r\n</request-claim>",
        "<request-claim>\n claim-reference: claim:required\n</request-claim>",
        "<request-claim>\n\nclaim-reference: claim:required\n</request-claim>",
        "<request-claim>\nclaim-reference: claim:required \n</request-claim>",
    ),
)
def test_correctly_resealed_alternative_rendering_is_rejected(text):
    plan = _plan()
    message = _seal_message(
        plan.rendered_sections[0]
        .rendered_messages[0]
        .model_copy(update={"rendered_text": text})
    )
    assert "prompt-rendering-text-mismatch" in _codes(
        _replace_message(plan, 0, 0, message)
    )


@pytest.mark.parametrize(
    ("level", "field", "value", "code"),
    (
        (
            "plan",
            "rendered_plan_reference",
            "rendered-prompt-plan:x",
            "prompt-rendering-invalid-plan-reference",
        ),
        (
            "section",
            "rendered_section_reference",
            "rendered-prompt-section:x",
            "prompt-rendering-invalid-section-reference",
        ),
        (
            "message",
            "rendered_message_reference",
            "rendered-prompt-message:x",
            "prompt-rendering-invalid-message-reference",
        ),
        (
            "plan",
            "source_request_plan_fingerprint",
            "f" * 64,
            "prompt-rendering-source-plan-fingerprint-mismatch",
        ),
        (
            "section",
            "source_request_section_fingerprint",
            "f" * 64,
            "prompt-rendering-source-section-fingerprint-mismatch",
        ),
        (
            "message",
            "source_request_claim_fingerprint",
            "f" * 64,
            "prompt-rendering-source-claim-fingerprint-mismatch",
        ),
        ("message", "rendering_role", "context", "prompt-rendering-role-mismatch"),
        ("message", "ordinal", 3, "prompt-rendering-ordinal-mismatch"),
    ),
)
def test_resealed_reference_lineage_role_and_ordinal_substitutions_fail(
    level, field, value, code
):
    plan = _plan()
    if level == "plan":
        changed = _seal_plan(plan.model_copy(update={field: value}))
    elif level == "section":
        section = _seal_section(
            plan.rendered_sections[0].model_copy(update={field: value})
        )
        changed = _replace_section(plan, 0, section)
    else:
        message = _seal_message(
            plan.rendered_sections[0]
            .rendered_messages[0]
            .model_copy(update={field: value})
        )
        changed = _replace_message(plan, 0, 0, message)
    assert code in _codes(changed)


@pytest.mark.parametrize("level", ("plan", "section", "message"))
@pytest.mark.parametrize("seal", ("identity", "fingerprint"))
def test_stale_and_forged_seals_are_rejected(level, seal):
    plan = _plan()
    if level == "plan":
        prefix = "scout:draft-rendered-prompt-plan:"
        changed = plan.model_copy(
            update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
        )
    elif level == "section":
        prefix = "scout:rendered-prompt-section:"
        section = plan.rendered_sections[0].model_copy(
            update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
        )
        changed = _replace_section(plan, 0, section)
    else:
        prefix = "scout:rendered-prompt-message:"
        message = (
            plan.rendered_sections[0]
            .rendered_messages[0]
            .model_copy(
                update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
            )
        )
        changed = _replace_message(plan, 0, 0, message)
    assert f"prompt-rendering-invalid-{level}-{seal}" in _codes(changed)


@pytest.mark.parametrize(
    ("scope", "field", "code"),
    (
        (
            "section",
            "rendered_section_reference",
            "prompt-rendering-duplicate-rendered-section-reference",
        ),
        ("section", "identity", "prompt-rendering-duplicate-rendered-section-identity"),
        (
            "section",
            "source_request_section_reference",
            "prompt-rendering-duplicate-source-section-reference",
        ),
        (
            "section",
            "source_request_section_identity",
            "prompt-rendering-duplicate-source-section-identity",
        ),
        (
            "message",
            "rendered_message_reference",
            "prompt-rendering-duplicate-rendered-message-reference",
        ),
        ("message", "identity", "prompt-rendering-duplicate-rendered-message-identity"),
        (
            "message",
            "source_request_claim_reference",
            "prompt-rendering-duplicate-source-claim-reference",
        ),
        (
            "message",
            "source_request_claim_identity",
            "prompt-rendering-duplicate-source-claim-identity",
        ),
        ("message", "ordinal", "prompt-rendering-duplicate-ordinal"),
    ),
)
def test_every_duplicate_dimension_is_reported(scope, field, code):
    plan, context = _multi()
    if scope == "section":
        first, second = plan.rendered_sections[:2]
        second = second.model_copy(update={field: getattr(first, field)})
        changed = _replace_section(plan, 1, second)
    else:
        first, second = plan.rendered_sections[0].rendered_messages[:2]
        second = second.model_copy(update={field: getattr(first, field)})
        changed = _replace_message(plan, 0, 1, second)
    assert code in _codes(changed, context)


@pytest.mark.parametrize("order", ((1, 0, 2), (2, 1, 0), (0, 2, 1)))
def test_section_and_message_order_are_not_repaired(order):
    plan, context = _multi()
    changed = _seal_plan(
        plan.model_copy(
            update={
                "rendered_sections": tuple(
                    plan.rendered_sections[index] for index in order
                )
            }
        )
    )
    assert "prompt-rendering-invalid-section-order" in _codes(changed, context)
    section = plan.rendered_sections[0]
    section = _seal_section(
        section.model_copy(
            update={
                "rendered_messages": tuple(
                    section.rendered_messages[index] for index in order
                )
            }
        )
    )
    assert "prompt-rendering-invalid-message-order" in _codes(
        _replace_section(plan, 0, section), context
    )


def test_missing_and_extra_sections_and_messages_are_rejected():
    plan, context = _multi()
    missing_section = _seal_plan(
        plan.model_copy(update={"rendered_sections": plan.rendered_sections[1:]})
    )
    extra_section = _seal_plan(
        plan.model_copy(
            update={
                "rendered_sections": (
                    *plan.rendered_sections,
                    plan.rendered_sections[0],
                )
            }
        )
    )
    section = plan.rendered_sections[0]
    missing_message = _seal_section(
        section.model_copy(update={"rendered_messages": section.rendered_messages[1:]})
    )
    extra_message = _seal_section(
        section.model_copy(
            update={
                "rendered_messages": (
                    *section.rendered_messages,
                    section.rendered_messages[0],
                )
            }
        )
    )
    assert "prompt-rendering-missing-section" in _codes(missing_section, context)
    assert "prompt-rendering-extra-section" in _codes(extra_section, context)
    assert "prompt-rendering-missing-message" in _codes(
        _replace_section(plan, 0, missing_message), context
    )
    assert "prompt-rendering-extra-message" in _codes(
        _replace_section(plan, 0, extra_message), context
    )


def test_canonical_empty_rendering():
    bindings = UPSTREAM["UPSTREAM"]["UPSTREAM"]
    draft = bindings["_draft"](bindings["_section"](required=(), optional=()))
    source_binding = UPSTREAM["UPSTREAM"]["_source_plan"](draft, ())
    binding_context = UPSTREAM["UPSTREAM"]["_source_context"](draft)
    composition = UPSTREAM["UPSTREAM"]["_composition"](source_binding, binding_context)
    composition_context = UPSTREAM["UPSTREAM"]["_context"](
        source_binding, binding_context
    )
    request = UPSTREAM["_request"](composition, composition_context)
    request_context = UPSTREAM["_context"](composition, composition_context)
    plan = _plan(request, request_context)
    assert plan.rendered_sections == ()
    assert (
        validate_draft_rendered_prompt_plan(plan, _context(request, request_context))
        == ()
    )


def test_unicode_is_nfc_preserved_and_deterministic():
    bindings = UPSTREAM["UPSTREAM"]["UPSTREAM"]
    claim_reference = "claim:s\u0326tire-東京-🙂"
    section = bindings["_section"](required=(claim_reference,), optional=())
    draft = bindings["_draft"](section)
    draft_context = bindings["_draft_context"]()
    scope = draft_context.normalized_input_scopes[0].model_copy(
        update={"claim_references": (claim_reference,)}
    )
    draft_context = draft_context.model_copy(
        update={
            "normalized_input_scopes": (
                scope,
                *draft_context.normalized_input_scopes[1:],
            )
        }
    )
    binding_context = bindings["ClaimBindingValidationContext"](
        drafts=(draft,), draft_validation_context=draft_context
    )
    binding = bindings["_binding"](draft, section, claim_reference)
    binding_plan = UPSTREAM["UPSTREAM"]["_source_plan"](
        draft, (bindings["_binding_set"](draft, section, (binding,)),)
    )
    composition = UPSTREAM["UPSTREAM"]["_composition"](binding_plan, binding_context)
    composition_context = UPSTREAM["UPSTREAM"]["_context"](
        binding_plan, binding_context
    )
    source = UPSTREAM["_request"](composition, composition_context)
    source_context = UPSTREAM["_context"](composition, composition_context)
    plan = _plan(source, source_context)
    assert (
        "știre-東京-🙂" in plan.rendered_sections[0].rendered_messages[0].rendered_text
    )
    assert plan == _plan(source, source_context)


class _Hostile:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, **_kwargs):
        raise self.error_type("private C:\\Users\\secret 0x7ff traceback")


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize("side", ("plan", "context"))
def test_ordinary_reconstruction_failures_are_contained(error_type, side):
    issues = (
        validate_draft_rendered_prompt_plan(_Hostile(error_type), _context())
        if side == "plan"
        else validate_draft_rendered_prompt_plan(_plan(), _Hostile(error_type))
    )
    payload = json.dumps([asdict(issue) for issue in issues], default=str)
    assert issues
    assert "private" not in payload and "0x7ff" not in payload


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize("side", ("plan", "context"))
def test_process_control_exceptions_propagate(error_type, side):
    with pytest.raises(error_type):
        if side == "plan":
            validate_draft_rendered_prompt_plan(_Hostile(error_type), _context())
        else:
            validate_draft_rendered_prompt_plan(_plan(), _Hostile(error_type))


def test_mutable_inputs_are_reconstructed_as_fresh_snapshots():
    plan = _plan()
    sections = [item.model_dump() for item in plan.rendered_sections]
    copied = plan.model_copy(update={"rendered_sections": sections})
    sources = [_source().model_dump()]
    context = _context().model_copy(update={"request_plans": sources})
    first = validate_draft_rendered_prompt_plan(copied, context)
    sections.append(sections[0])
    sources.append(sources[0])
    second = validate_draft_rendered_prompt_plan(copied, context)
    sections.pop()
    sources.pop()
    third = validate_draft_rendered_prompt_plan(copied, context)
    assert first == third == () and second


def test_every_semantic_field_changes_identity_and_fingerprint():
    plan = _plan()
    section = plan.rendered_sections[0]
    message = section.rendered_messages[0]

    def alternate(field, value):
        if isinstance(value, str):
            if field == "rendering_role":
                return "context"
            if len(value) == 64 and set(value) <= set("0123456789abcdef"):
                return ("2" if value[0] != "2" else "3") + value[1:]
            if value.startswith("scout:") and len(value.rsplit(":", 1)[-1]) == 64:
                return value[:-1] + ("2" if value[-1] != "2" else "3")
            return value + "x"
        if isinstance(value, int):
            return value + 1
        if isinstance(value, tuple):
            return tuple(reversed(value)) if len(value) > 1 else value + value
        raise AssertionError((field, type(value)))

    cases = (
        (
            message,
            derive_rendered_prompt_message_identity,
            derive_rendered_prompt_message_fingerprint,
        ),
        (
            section,
            derive_rendered_prompt_section_identity,
            derive_rendered_prompt_section_fingerprint,
        ),
        (
            plan,
            derive_draft_rendered_prompt_plan_identity,
            derive_draft_rendered_prompt_plan_fingerprint,
        ),
    )
    checked = 0
    for artifact, identity_function, fingerprint_function in cases:
        for field in type(artifact).model_fields:
            if field in {"identity", "fingerprint"}:
                continue
            changed = artifact.model_copy(
                update={field: alternate(field, getattr(artifact, field))}
            )
            identity = identity_function(changed)
            assert identity != artifact.identity, field
            changed = changed.model_copy(update={"identity": identity})
            assert fingerprint_function(changed) != artifact.fingerprint, field
            checked += 1
    assert checked == 30


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize("side", ("plan", "context"))
def test_builder_ordinary_reconstruction_failures_are_domain_errors(error_type, side):
    with pytest.raises(DomainValidationError) as caught:
        if side == "plan":
            build_draft_rendered_prompt_plan(_Hostile(error_type), _source_context())
        else:
            build_draft_rendered_prompt_plan(_source(), _Hostile(error_type))
    payload = str(caught.value)
    assert "private" not in payload and "0x7ff" not in payload


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize("side", ("plan", "context"))
def test_builder_process_control_exceptions_propagate(error_type, side):
    with pytest.raises(error_type):
        if side == "plan":
            build_draft_rendered_prompt_plan(_Hostile(error_type), _source_context())
        else:
            build_draft_rendered_prompt_plan(_source(), _Hostile(error_type))


def test_separate_process_rendering_and_validation_are_identical():
    prefix = "import json,runpy,sys; sys.path.insert(0,'tests'); "
    artifact = (
        prefix
        + "n=runpy.run_path('tests/test_editorial_script_composer_prompt_rendering.py'); print(json.dumps(n['_plan']().model_dump(),ensure_ascii=False,sort_keys=True,separators=(',',':')))"
    )
    diagnostic = (
        prefix
        + "from dataclasses import asdict; n=runpy.run_path('tests/test_editorial_script_composer_prompt_rendering.py'); p=n['_seal_plan'](n['_plan']().model_copy(update={'rendered_plan_reference':'rendered-prompt-plan:x'})); print(json.dumps([asdict(x) for x in n['validate_draft_rendered_prompt_plan'](p,n['_context']())],sort_keys=True,separators=(',',':')))"
    )
    for code in (artifact, diagnostic):
        assert subprocess.check_output(
            [sys.executable, "-c", code]
        ) == subprocess.check_output([sys.executable, "-c", code])


def test_public_api_internal_exclusions_and_phase_boundary():
    module = importlib.import_module("pastila_scout.editor.script_composer")
    public = {
        "RenderedPromptMessage",
        "RenderedPromptSection",
        "DraftRenderedPromptPlan",
        "RenderedPromptValidationContext",
        "build_draft_rendered_prompt_plan",
        "validate_draft_rendered_prompt_plan",
        "derive_rendered_prompt_message_identity",
        "derive_rendered_prompt_section_identity",
        "derive_draft_rendered_prompt_plan_identity",
        "derive_rendered_prompt_message_fingerprint",
        "derive_rendered_prompt_section_fingerprint",
        "derive_draft_rendered_prompt_plan_fingerprint",
    }
    private = {
        "RenderedPromptDomainModel",
        "_render_request_claim",
        "_canonical_rendered_plan_reference",
        "_AuthoritativeRenderedPromptInputs",
        "_validate_seals",
    }
    assert all(hasattr(module, name) for name in public)
    assert all(not hasattr(module, name) for name in private)
    forbidden = {
        "provider",
        "model",
        "temperature",
        "top_p",
        "max_tokens",
        "retry",
        "response",
        "generated_output",
    }
    for model in (
        RenderedPromptMessage,
        RenderedPromptSection,
        DraftRenderedPromptPlan,
    ):
        assert forbidden.isdisjoint(model.model_fields)
