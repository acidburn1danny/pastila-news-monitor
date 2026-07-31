"""Freeze-grade adversarial regressions for Phase 5.2 prompt rendering."""

import json
import subprocess
import sys
from dataclasses import asdict

import pytest
from test_editorial_script_composer_prompt_rendering import (
    FREEZE,
    UPSTREAM,
    _codes,
    _context,
    _multi,
    _plan,
    _replace_message,
    _replace_section,
    _seal_message,
    _seal_plan,
    _seal_section,
    _source,
    _source_context,
)

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    build_draft_rendered_prompt_plan,
    derive_draft_rendered_prompt_plan_identity,
    derive_rendered_prompt_message_identity,
    derive_rendered_prompt_section_identity,
    validate_draft_rendered_prompt_plan,
)


def _changed_message(plan, **updates):
    message = _seal_message(
        plan.rendered_sections[0].rendered_messages[0].model_copy(update=updates)
    )
    return _replace_message(plan, 0, 0, message)


def _changed_section(plan, **updates):
    section = _seal_section(plan.rendered_sections[0].model_copy(update=updates))
    return _replace_section(plan, 0, section)


def _complete_issues(plan, context=None):
    return tuple(
        asdict(issue)
        for issue in validate_draft_rendered_prompt_plan(plan, context or _context())
    )


def _empty_authority(*, purpose=None):
    bindings = UPSTREAM["UPSTREAM"]["UPSTREAM"]
    section = bindings["_section"](required=(), optional=())
    if purpose is not None:
        section = bindings["_draft_seal"](
            section.model_copy(update={"purpose": purpose}),
            bindings["draft_section_identity"],
        )
    draft = bindings["_draft"](section)
    source_binding = UPSTREAM["UPSTREAM"]["_source_plan"](draft, ())
    binding_context = UPSTREAM["UPSTREAM"]["_source_context"](draft)
    composition = UPSTREAM["UPSTREAM"]["_composition"](source_binding, binding_context)
    composition_context = UPSTREAM["UPSTREAM"]["_context"](
        source_binding, binding_context
    )
    request = UPSTREAM["_request"](composition, composition_context)
    request_context = UPSTREAM["_context"](composition, composition_context)
    return (
        request,
        request_context,
        _plan(request, request_context),
        _context(request, request_context),
    )


def _assert_deterministic_builder_rejection(source):
    first = None
    second = None
    for position in range(2):
        with pytest.raises(DomainValidationError) as caught:
            build_draft_rendered_prompt_plan(source, _source_context())
        payload = tuple(asdict(issue) for issue in caught.value.issues)
        if position == 0:
            first = payload
        else:
            second = payload
    assert first == second
    assert first
    return {issue["code"] for issue in first}


@pytest.mark.parametrize(
    ("level", "value", "expected"),
    tuple(
        (level, value, expected)
        for level, expected in (
            ("plan", "prompt-rendering-invalid-plan-reference"),
            ("section", "prompt-rendering-invalid-section-reference"),
            ("message", "prompt-rendering-invalid-message-reference"),
        )
        for value in (
            "rendered-prompt-plan:wrong",
            "https://example.test/item",
            "https://user:secret@example.test/item?token=private",
            r"C:\Users\private\item.json",
            "/home/private/item.json",
            "line\nbreak",
            "x" * 201,
            " rendered-prompt-plan:wrong",
            "RENDERED-PROMPT-PLAN:WRONG",
            "rendered‐prompt-plan:wrong",
        )
    ),
)
def test_canonical_reference_attack_matrix(level, value, expected):
    plan = _plan()
    if level == "plan":
        changed = _seal_plan(plan.model_copy(update={"rendered_plan_reference": value}))
    elif level == "section":
        changed = _changed_section(plan, rendered_section_reference=value)
    else:
        changed = _changed_message(plan, rendered_message_reference=value)
    codes = _codes(changed)
    assert expected in codes or "prompt-rendering-invalid-reconstructed-plan" in codes


@pytest.mark.parametrize(
    "text",
    (
        "<REQUEST-CLAIM>\nclaim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</request-claim>",
        "<request-claim>\nclaim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</REQUEST-CLAIM>",
        "claim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</request-claim>",
        "<request-claim>\n<request-claim>\nclaim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</request-claim>",
        "<request-claim >\nclaim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</request-claim>",
        "<requeѕt-claim>\nclaim-reference: claim:required\nrequirement: required\nrole: section_anchor\nordinal: 0\n</request-claim>",
    ),
)
def test_delimiter_attack_matrix(text):
    assert "prompt-rendering-text-mismatch" in _codes(
        _changed_message(_plan(), rendered_text=text)
    )


@pytest.mark.parametrize(
    "transform",
    (
        lambda text: text.replace("\n", "\r\n"),
        lambda text: text.replace("\n", "\r"),
        lambda text: text.replace("\n", "\u2028"),
        lambda text: text.replace("\n", "\u2029"),
        lambda text: text.replace("claim-reference", "\tclaim-reference"),
        lambda text: text + " ",
        lambda text: " " + text,
        lambda text: text.replace(": ", ":\u00a0"),
        lambda text: text.replace(": ", ":\u2009"),
        lambda text: text.replace("\n", "\n\n", 1),
        lambda text: text.replace(": ", ":  "),
        lambda text: text.replace(": ", ":"),
    ),
)
def test_whitespace_and_line_ending_attack_matrix(transform):
    plan = _plan()
    canonical = plan.rendered_sections[0].rendered_messages[0].rendered_text
    assert "prompt-rendering-text-mismatch" in _codes(
        _changed_message(plan, rendered_text=transform(canonical))
    )


@pytest.mark.parametrize(
    "transform",
    (
        lambda lines: [lines[0], lines[2], lines[1], *lines[3:]],
        lambda lines: [lines[0], *reversed(lines[1:-1]), lines[-1]],
        lambda lines: [lines[0], lines[1], lines[3], lines[2], lines[4], lines[5]],
        lambda lines: [*lines[:-1], lines[1], lines[-1]],
        lambda lines: [line for line in lines if not line.startswith("role:")],
        lambda lines: [*lines[:-1], "unknown: value", lines[-1]],
        lambda lines: [line.replace(": ", "= ") for line in lines],
        lambda lines: [
            line.replace("requirement: required", 'requirement: "required"')
            for line in lines
        ],
        lambda lines: [line.replace("ordinal: 0", "ordinal: 00") for line in lines],
        lambda lines: [line.replace("ordinal: 0", "ordinal: zero") for line in lines],
    ),
)
def test_field_order_punctuation_and_ordinal_attack_matrix(transform):
    plan = _plan()
    lines = plan.rendered_sections[0].rendered_messages[0].rendered_text.split("\n")
    assert "prompt-rendering-text-mismatch" in _codes(
        _changed_message(plan, rendered_text="\n".join(transform(lines)))
    )


@pytest.mark.parametrize(
    "role",
    (
        "instruction",
        "context",
        "system",
        "developer",
        "user",
        "assistant",
        "tool",
        "function",
        "",
        " generation",
        "Generation",
    ),
)
def test_rendering_role_attack_matrix(role):
    codes = _codes(_changed_message(_plan(), rendering_role=role))
    assert (
        "prompt-rendering-role-mismatch" in codes
        or "prompt-rendering-invalid-reconstructed-plan" in codes
    )


def test_stale_plan_identity_is_rejected():
    plan = _plan().model_copy(
        update={"rendered_plan_reference": "rendered-prompt-plan:x"}
    )
    assert "prompt-rendering-invalid-plan-identity" in _codes(plan)


def test_forged_plan_identity_is_rejected():
    plan = _plan().model_copy(
        update={"identity": f"scout:draft-rendered-prompt-plan:{'f' * 64}"}
    )
    assert "prompt-rendering-invalid-plan-identity" in _codes(plan)


def test_stale_plan_fingerprint_is_rejected():
    plan = _plan().model_copy(
        update={"rendered_plan_reference": "rendered-prompt-plan:x"}
    )
    plan = plan.model_copy(
        update={"identity": derive_draft_rendered_prompt_plan_identity(plan)}
    )
    assert "prompt-rendering-invalid-plan-fingerprint" in _codes(plan)


def test_forged_plan_fingerprint_is_rejected():
    assert "prompt-rendering-invalid-plan-fingerprint" in _codes(
        _plan().model_copy(update={"fingerprint": "f" * 64})
    )


def test_stale_section_identity_is_rejected():
    plan = _plan()
    section = plan.rendered_sections[0].model_copy(
        update={"draft_reference": "draft:x"}
    )
    assert "prompt-rendering-invalid-section-identity" in _codes(
        _replace_section(plan, 0, section)
    )


def test_forged_section_identity_is_rejected():
    plan = _plan()
    section = plan.rendered_sections[0].model_copy(
        update={"identity": f"scout:rendered-prompt-section:{'f' * 64}"}
    )
    assert "prompt-rendering-invalid-section-identity" in _codes(
        _replace_section(plan, 0, section)
    )


def test_stale_section_fingerprint_is_rejected():
    plan = _plan()
    section = plan.rendered_sections[0].model_copy(
        update={"draft_reference": "draft:x"}
    )
    section = section.model_copy(
        update={"identity": derive_rendered_prompt_section_identity(section)}
    )
    assert "prompt-rendering-invalid-section-fingerprint" in _codes(
        _replace_section(plan, 0, section)
    )


def test_forged_section_fingerprint_is_rejected():
    plan = _plan()
    section = plan.rendered_sections[0].model_copy(update={"fingerprint": "f" * 64})
    assert "prompt-rendering-invalid-section-fingerprint" in _codes(
        _replace_section(plan, 0, section)
    )


def test_stale_message_identity_is_rejected():
    plan = _plan()
    message = (
        plan.rendered_sections[0]
        .rendered_messages[0]
        .model_copy(update={"rendered_text": "changed"})
    )
    assert "prompt-rendering-invalid-message-identity" in _codes(
        _replace_message(plan, 0, 0, message)
    )


def test_forged_message_identity_is_rejected():
    plan = _plan()
    message = (
        plan.rendered_sections[0]
        .rendered_messages[0]
        .model_copy(update={"identity": f"scout:rendered-prompt-message:{'f' * 64}"})
    )
    assert "prompt-rendering-invalid-message-identity" in _codes(
        _replace_message(plan, 0, 0, message)
    )


def test_stale_message_fingerprint_is_rejected():
    plan = _plan()
    message = (
        plan.rendered_sections[0]
        .rendered_messages[0]
        .model_copy(update={"rendered_text": "changed"})
    )
    message = message.model_copy(
        update={"identity": derive_rendered_prompt_message_identity(message)}
    )
    assert "prompt-rendering-invalid-message-fingerprint" in _codes(
        _replace_message(plan, 0, 0, message)
    )


def test_forged_message_fingerprint_is_rejected():
    plan = _plan()
    message = (
        plan.rendered_sections[0]
        .rendered_messages[0]
        .model_copy(update={"fingerprint": "f" * 64})
    )
    assert "prompt-rendering-invalid-message-fingerprint" in _codes(
        _replace_message(plan, 0, 0, message)
    )


@pytest.mark.parametrize("index", (0, 1, 2))
def test_each_section_and_message_position_is_required(index):
    plan, context = _multi()
    sections = tuple(
        item
        for position, item in enumerate(plan.rendered_sections)
        if position != index
    )
    assert "prompt-rendering-missing-section" in _codes(
        _seal_plan(plan.model_copy(update={"rendered_sections": sections})), context
    )
    section = plan.rendered_sections[0]
    messages = tuple(
        item
        for position, item in enumerate(section.rendered_messages)
        if position != index
    )
    changed = _seal_section(section.model_copy(update={"rendered_messages": messages}))
    assert "prompt-rendering-missing-message" in _codes(
        _replace_section(plan, 0, changed), context
    )


def test_foreign_and_unique_extra_artifacts_are_rejected():
    plan, context = _multi()
    section = plan.rendered_sections[0]
    foreign_message = plan.rendered_sections[1].rendered_messages[0]
    unique_message = _seal_message(
        foreign_message.model_copy(
            update={
                "rendered_message_reference": "rendered-prompt-message:unique",
                "ordinal": 99,
            }
        )
    )
    foreign = _seal_section(
        section.model_copy(
            update={"rendered_messages": (*section.rendered_messages, foreign_message)}
        )
    )
    unique = _seal_section(
        section.model_copy(
            update={"rendered_messages": (*section.rendered_messages, unique_message)}
        )
    )
    assert "prompt-rendering-extra-message" in _codes(
        _replace_section(plan, 0, foreign), context
    )
    assert "prompt-rendering-extra-message" in _codes(
        _replace_section(plan, 0, unique), context
    )
    extra_section = _seal_section(
        plan.rendered_sections[1].model_copy(
            update={"rendered_section_reference": "rendered-prompt-section:unique"}
        )
    )
    changed = _seal_plan(
        plan.model_copy(
            update={"rendered_sections": (*plan.rendered_sections, extra_section)}
        )
    )
    assert "prompt-rendering-extra-section" in _codes(changed, context)


def test_valid_section_from_a_separate_authoritative_plan_is_rejected():
    plan, context = _multi()
    foreign_request, foreign_context, _, _ = FREEZE["_multi_section_request"](
        section_count=2, claims_per_section=2
    )
    foreign_plan = _plan(foreign_request, foreign_context)
    assert (
        validate_draft_rendered_prompt_plan(
            foreign_plan, _context(foreign_request, foreign_context)
        )
        == ()
    )
    changed = _seal_plan(
        plan.model_copy(
            update={
                "rendered_sections": (
                    *plan.rendered_sections,
                    foreign_plan.rendered_sections[0],
                )
            }
        )
    )
    first = _complete_issues(changed, context)
    second = _complete_issues(changed, context)
    assert first == second
    assert "prompt-rendering-extra-section" in {item["code"] for item in first}


def test_valid_message_from_a_separate_authoritative_plan_is_rejected():
    plan, context = _multi()
    foreign_request, foreign_context, _, _ = FREEZE["_multi_section_request"](
        section_count=2, claims_per_section=2
    )
    foreign_plan = _plan(foreign_request, foreign_context)
    assert (
        validate_draft_rendered_prompt_plan(
            foreign_plan, _context(foreign_request, foreign_context)
        )
        == ()
    )
    section = plan.rendered_sections[0]
    changed_section = _seal_section(
        section.model_copy(
            update={
                "rendered_messages": (
                    *section.rendered_messages,
                    foreign_plan.rendered_sections[0].rendered_messages[0],
                )
            }
        )
    )
    changed = _replace_section(plan, 0, changed_section)
    first = _complete_issues(changed, context)
    second = _complete_issues(changed, context)
    assert first == second
    assert "prompt-rendering-extra-message" in {item["code"] for item in first}


@pytest.mark.parametrize(
    "unsafe",
    (
        "https://user:secret@example.test/item?token=private#fragment",
        r"C:\Users\private\secret.txt",
        "/home/private/secret.txt",
        "OPENAI_API_KEY=secret",
        "TracebackRuntimeError",
        "0x7ffdeadbeef",
        "line\nbreak\tcontrol\x01",
        "x" * 201,
        "rendered‐prompt-section:spoof",
    ),
)
@pytest.mark.parametrize("scope", ("section", "message"))
def test_duplicate_diagnostics_never_expose_unsafe_values(scope, unsafe):
    plan, context = _multi()
    if scope == "section":
        sections = list(plan.rendered_sections)
        sections[0] = _seal_section(
            sections[0].model_copy(update={"rendered_section_reference": unsafe})
        )
        sections[1] = _seal_section(
            sections[1].model_copy(update={"rendered_section_reference": unsafe})
        )
        changed = _seal_plan(
            plan.model_copy(update={"rendered_sections": tuple(sections)})
        )
    else:
        section = plan.rendered_sections[0]
        messages = list(section.rendered_messages)
        messages[0] = _seal_message(
            messages[0].model_copy(update={"rendered_message_reference": unsafe})
        )
        messages[1] = _seal_message(
            messages[1].model_copy(update={"rendered_message_reference": unsafe})
        )
        changed_section = _seal_section(
            section.model_copy(update={"rendered_messages": tuple(messages)})
        )
        changed = _replace_section(plan, 0, changed_section)
    issues = validate_draft_rendered_prompt_plan(changed, context)
    payloads = (
        json.dumps(
            [asdict(issue) for issue in issues], ensure_ascii=False, default=str
        ),
        str(issues),
    )
    assert issues and all(unsafe not in payload for payload in payloads)
    assert all(len(payload) < 30_000 for payload in payloads)


@pytest.mark.parametrize(
    "mutation",
    (
        "identity",
        "fingerprint",
        "reference",
        "missing-section",
        "section-lineage",
        "claim-lineage",
        "semantic-payload",
        "draft-lineage",
    ),
)
def test_builder_rejects_multiple_malformed_phase_5_1_authority_classes(mutation):
    source = _source()
    if mutation == "identity":
        source = source.model_copy(
            update={"identity": f"scout:draft-llm-request-plan:{'f' * 64}"}
        )
    elif mutation == "fingerprint":
        source = source.model_copy(update={"fingerprint": "f" * 64})
    elif mutation == "reference":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(update={"request_plan_reference": "llm-request-plan:x"})
        )
    elif mutation == "missing-section":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(update={"request_sections": ()})
        )
    elif mutation == "section-lineage":
        section = UPSTREAM["_seal_section"](
            source.request_sections[0].model_copy(
                update={"section_reference": "section:x"}
            )
        )
        source = UPSTREAM["_seal_plan"](
            source.model_copy(update={"request_sections": (section,)})
        )
    else:
        claim = source.request_sections[0].request_claims[0]
        field, value = {
            "claim-lineage": ("section_reference", "section:x"),
            "semantic-payload": ("claim_reference", "claim:x"),
            "draft-lineage": ("draft_reference", "draft:x"),
        }[mutation]
        claim = UPSTREAM["_seal_claim"](claim.model_copy(update={field: value}))
        source = UPSTREAM["_replace_claim"](source, claim)
    with pytest.raises(DomainValidationError):
        build_draft_rendered_prompt_plan(source, _source_context())


def test_builder_rejects_reordered_authoritative_request_sections():
    source, source_context, _, _ = FREEZE["_multi_section_request"]()
    source = UPSTREAM["_seal_plan"](
        source.model_copy(
            update={"request_sections": tuple(reversed(source.request_sections))}
        )
    )
    first = None
    second = None
    for position in range(2):
        with pytest.raises(DomainValidationError) as caught:
            build_draft_rendered_prompt_plan(source, source_context)
        payload = tuple(asdict(issue) for issue in caught.value.issues)
        first, second = (payload, second) if position == 0 else (first, payload)
    assert first == second
    assert "llm-request-invalid-section-order" in {issue["code"] for issue in first}


def test_builder_rejects_reordered_authoritative_request_claims():
    source, source_context, _, _ = FREEZE["_multi_section_request"]()
    section = source.request_sections[0]
    section = UPSTREAM["_seal_section"](
        section.model_copy(
            update={"request_claims": tuple(reversed(section.request_claims))}
        )
    )
    source = UPSTREAM["_seal_plan"](
        source.model_copy(
            update={"request_sections": (section, *source.request_sections[1:])}
        )
    )
    with pytest.raises(DomainValidationError) as first:
        build_draft_rendered_prompt_plan(source, source_context)
    with pytest.raises(DomainValidationError) as second:
        build_draft_rendered_prompt_plan(source, source_context)
    assert tuple(map(asdict, first.value.issues)) == tuple(
        map(asdict, second.value.issues)
    )
    assert "llm-request-invalid-claim-order" in {
        issue.code for issue in first.value.issues
    }


@pytest.mark.parametrize(
    ("artifact", "seal", "expected"),
    (
        ("section", "identity", "llm-request-invalid-section-identity"),
        ("section", "fingerprint", "llm-request-invalid-section-fingerprint"),
        ("claim", "identity", "llm-request-invalid-claim-identity"),
        ("claim", "fingerprint", "llm-request-invalid-claim-fingerprint"),
    ),
)
def test_builder_rejects_stale_nested_phase_5_1_seals(artifact, seal, expected):
    source = _source()
    if artifact == "section":
        section = source.request_sections[0].model_copy(
            update={
                seal: (
                    f"scout:llm-request-section:{'f' * 64}"
                    if seal == "identity"
                    else "f" * 64
                )
            }
        )
        source = UPSTREAM["_seal_plan"](
            source.model_copy(update={"request_sections": (section,)})
        )
    else:
        claim = (
            source.request_sections[0]
            .request_claims[0]
            .model_copy(
                update={
                    seal: (
                        f"scout:llm-request-claim:{'f' * 64}"
                        if seal == "identity"
                        else "f" * 64
                    )
                }
            )
        )
        source = UPSTREAM["_replace_claim"](source, claim)
    assert expected in _assert_deterministic_builder_rejection(source)


def test_empty_plan_reconstruction_rejects_null_instead_of_tuple():
    _, _, plan, context = _empty_authority()
    changed = plan.model_construct(**{**plan.model_dump(), "rendered_sections": None})
    first = _complete_issues(changed, context)
    second = _complete_issues(changed, context)
    assert first == second
    assert {item["code"] for item in first} == {
        "prompt-rendering-invalid-reconstructed-plan"
    }


def test_empty_plan_reconstruction_canonicalizes_mutable_empty_list():
    _, _, plan, context = _empty_authority()
    changed = plan.model_construct(**{**plan.model_dump(), "rendered_sections": []})
    assert _complete_issues(changed, context) == ()
    rebuilt = _plan(*_empty_authority()[:2])
    assert rebuilt.rendered_sections == ()
    assert isinstance(rebuilt.rendered_sections, tuple)


@pytest.mark.parametrize("placeholder", ("section", "message"))
def test_empty_plan_rejects_placeholder_rendered_artifacts(placeholder):
    _, _, plan, context = _empty_authority()
    nonempty = _plan()
    section = nonempty.rendered_sections[0]
    if placeholder == "message":
        section = _seal_section(
            section.model_copy(
                update={
                    "rendered_section_reference": "rendered-prompt-section:placeholder",
                    "rendered_messages": (section.rendered_messages[0],),
                }
            )
        )
    changed = _seal_plan(plan.model_copy(update={"rendered_sections": (section,)}))
    first = _complete_issues(changed, context)
    assert first == _complete_issues(changed, context)
    assert "prompt-rendering-extra-section" in {item["code"] for item in first}


@pytest.mark.parametrize("seal", ("identity", "fingerprint"))
def test_empty_plan_rejects_stale_plan_seals(seal):
    _, _, plan, context = _empty_authority()
    changed = plan.model_copy(
        update={
            seal: (
                f"scout:draft-rendered-prompt-plan:{'f' * 64}"
                if seal == "identity"
                else "f" * 64
            )
        }
    )
    first = _complete_issues(changed, context)
    assert first == _complete_issues(changed, context)
    assert f"prompt-rendering-invalid-plan-{seal}" in {item["code"] for item in first}


def test_empty_plan_rejects_foreign_lineage_after_correct_resealing():
    _, _, plan, context = _empty_authority()
    _, _, foreign_plan, foreign_validation_context = _empty_authority(
        purpose="foreign-empty-purpose"
    )
    assert foreign_plan != plan
    assert (
        validate_draft_rendered_prompt_plan(foreign_plan, foreign_validation_context)
        == ()
    )
    changed = _seal_plan(
        plan.model_copy(
            update={
                "source_request_plan_reference": foreign_plan.source_request_plan_reference,
                "source_request_plan_identity": foreign_plan.source_request_plan_identity,
                "source_request_plan_fingerprint": foreign_plan.source_request_plan_fingerprint,
                "draft_reference": foreign_plan.draft_reference,
                "draft_fingerprint": foreign_plan.draft_fingerprint,
                "normalized_input_reference": foreign_plan.normalized_input_reference,
            }
        )
    )
    first = _complete_issues(changed, context)
    assert first == _complete_issues(changed, context)
    assert "prompt-rendering-unknown-source-plan" in {item["code"] for item in first}


def test_empty_plan_rejects_nonempty_projection_after_correct_resealing():
    _, _, plan, context = _empty_authority()
    nonempty_section = _plan().rendered_sections[0]
    changed = _seal_plan(
        plan.model_copy(update={"rendered_sections": (nonempty_section,)})
    )
    first = _complete_issues(changed, context)
    assert first == _complete_issues(changed, context)
    codes = {item["code"] for item in first}
    assert "prompt-rendering-extra-section" in codes
    assert changed.identity == derive_draft_rendered_prompt_plan_identity(changed)


def test_complete_diagnostics_are_equal_within_and_across_processes():
    plan, context = _multi()
    sections = list(plan.rendered_sections)
    unsafe = "https://user:secret@example.test/item?token=private"
    sections[0] = _seal_section(
        sections[0].model_copy(update={"rendered_section_reference": unsafe})
    )
    sections[1] = _seal_section(
        sections[1].model_copy(update={"rendered_section_reference": unsafe})
    )
    changed = _seal_plan(plan.model_copy(update={"rendered_sections": tuple(sections)}))
    assert _complete_issues(changed, context) == _complete_issues(changed, context)
    code = (
        "import json,runpy,sys; from dataclasses import asdict; "
        "sys.path.insert(0,'tests'); n=runpy.run_path('tests/test_editorial_script_composer_prompt_rendering_freeze.py'); "
        "p,c=n['_multi'](); s=list(p.rendered_sections); u='https://user:secret@example.test/item?token=private'; "
        "s[0]=n['_seal_section'](s[0].model_copy(update={'rendered_section_reference':u})); "
        "s[1]=n['_seal_section'](s[1].model_copy(update={'rendered_section_reference':u})); "
        "p=n['_seal_plan'](p.model_copy(update={'rendered_sections':tuple(s)})); "
        "print(json.dumps([asdict(x) for x in n['validate_draft_rendered_prompt_plan'](p,c)],sort_keys=True,separators=(',',':')))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second
    assert b"secret" not in first and b"token" not in first
