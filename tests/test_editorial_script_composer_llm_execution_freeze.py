"""Freeze-grade adversarial tests for Phase 6.1 execution planning."""

import json
from dataclasses import asdict

import pytest
from test_editorial_script_composer_llm_execution import (
    FREEZE,
    UPSTREAM,
    _codes,
    _context,
    _multi,
    _plan,
    _replace_message,
    _replace_request,
    _seal_message,
    _seal_plan,
    _seal_request,
)

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    build_draft_llm_execution_plan,
    derive_draft_llm_execution_plan_fingerprint,
    derive_draft_llm_execution_plan_identity,
    derive_llm_execution_message_fingerprint,
    derive_llm_execution_message_identity,
    derive_llm_execution_request_fingerprint,
    derive_llm_execution_request_identity,
    validate_draft_llm_execution_plan,
)


def _issues(plan, context=None):
    return tuple(
        asdict(item)
        for item in validate_draft_llm_execution_plan(plan, context or _context())
    )


@pytest.mark.parametrize("level", ("plan", "request", "message"))
@pytest.mark.parametrize(
    "value",
    (
        "arbitrary",
        "llm-execution-plan:wrong",
        "https://example.test/item",
        "https://user:secret@example.test/item?token=private#fragment",
        r"C:\Users\private\item.json",
        "/home/private/item.json",
        "line\nbreak",
        "x" * 201,
        " llm-execution-plan:wrong",
        "LLM-EXECUTION-PLAN:WRONG",
        "llmâ€execution-plan:wrong",
    ),
)
def test_canonical_reference_attack_matrix(level, value):
    plan = _plan()
    if level == "plan":
        changed = _seal_plan(
            plan.model_copy(update={"execution_plan_reference": value})
        )
        expected = "llm-execution-execution-plan-reference-mismatch"
    elif level == "request":
        request = _seal_request(
            plan.execution_requests[0].model_copy(
                update={"execution_request_reference": value}
            )
        )
        changed = _replace_request(plan, 0, request)
        expected = "llm-execution-request-execution-request-reference-mismatch"
    else:
        message = _seal_message(
            plan.execution_requests[0]
            .execution_messages[0]
            .model_copy(update={"execution_message_reference": value})
        )
        changed = _replace_message(plan, 0, 0, message)
        expected = "llm-execution-message-execution-message-reference-mismatch"
    codes = _codes(changed)
    assert expected in codes or "llm-execution-invalid-reconstructed-plan" in codes


@pytest.mark.parametrize("level", ("plan", "request", "message"))
@pytest.mark.parametrize("seal", ("identity", "fingerprint"))
def test_stale_and_forged_seals_are_rejected(level, seal):
    plan = _plan()
    if level == "plan":
        prefix = "scout:draft-llm-execution-plan:"
        changed = plan.model_copy(
            update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
        )
    elif level == "request":
        prefix = "scout:llm-execution-request:"
        request = plan.execution_requests[0].model_copy(
            update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
        )
        changed = _replace_request(plan, 0, request)
    else:
        prefix = "scout:llm-execution-message:"
        message = (
            plan.execution_requests[0]
            .execution_messages[0]
            .model_copy(
                update={seal: "f" * 64 if seal == "fingerprint" else prefix + "f" * 64}
            )
        )
        changed = _replace_message(plan, 0, 0, message)
    assert f"llm-execution-invalid-{level}-{seal}" in _codes(changed)


@pytest.mark.parametrize("index", (0, 1, 2))
def test_first_middle_and_final_requests_and_messages_are_required(index):
    plan, context = _multi()
    requests = tuple(
        item
        for position, item in enumerate(plan.execution_requests)
        if position != index
    )
    changed = _seal_plan(plan.model_copy(update={"execution_requests": requests}))
    assert "llm-execution-missing-request" in _codes(changed, context)
    request = plan.execution_requests[0]
    messages = tuple(
        item
        for position, item in enumerate(request.execution_messages)
        if position != index
    )
    request = _seal_request(request.model_copy(update={"execution_messages": messages}))
    assert "llm-execution-missing-message" in _codes(
        _replace_request(plan, 0, request), context
    )


@pytest.mark.parametrize("order", ((1, 0, 2), (2, 1, 0), (0, 2, 1)))
def test_request_and_message_order_is_not_repaired(order):
    plan, context = _multi()
    changed = _seal_plan(
        plan.model_copy(
            update={
                "execution_requests": tuple(plan.execution_requests[i] for i in order)
            }
        )
    )
    assert "llm-execution-invalid-request-order" in _codes(changed, context)
    request = plan.execution_requests[0]
    request = _seal_request(
        request.model_copy(
            update={
                "execution_messages": tuple(
                    request.execution_messages[i] for i in order
                )
            }
        )
    )
    assert "llm-execution-invalid-message-order" in _codes(
        _replace_request(plan, 0, request), context
    )


@pytest.mark.parametrize(
    ("scope", "field", "expected"),
    (
        (
            "request",
            "execution_request_reference",
            "llm-execution-duplicate-execution-request-reference",
        ),
        ("request", "identity", "llm-execution-duplicate-execution-request-identity"),
        (
            "request",
            "rendered_section_reference",
            "llm-execution-duplicate-rendered-section-reference",
        ),
        (
            "request",
            "rendered_section_identity",
            "llm-execution-duplicate-rendered-section-identity",
        ),
        ("request", "request_ordinal", "llm-execution-duplicate-request-ordinal"),
        (
            "message",
            "execution_message_reference",
            "llm-execution-duplicate-execution-message-reference",
        ),
        ("message", "identity", "llm-execution-duplicate-execution-message-identity"),
        (
            "message",
            "rendered_message_reference",
            "llm-execution-duplicate-rendered-message-reference",
        ),
        (
            "message",
            "rendered_message_identity",
            "llm-execution-duplicate-rendered-message-identity",
        ),
        ("message", "ordinal", "llm-execution-duplicate-message-ordinal"),
    ),
)
def test_every_duplicate_dimension_is_detected(scope, field, expected):
    plan, context = _multi()
    if scope == "request":
        first, second = plan.execution_requests[:2]
        second = second.model_copy(update={field: getattr(first, field)})
        changed = _replace_request(plan, 1, second)
    else:
        first, second = plan.execution_requests[0].execution_messages[:2]
        second = second.model_copy(update={field: getattr(first, field)})
        changed = _replace_message(plan, 0, 1, second)
    assert expected in _codes(changed, context)


def test_foreign_valid_request_and_messages_are_rejected():
    plan, context = _multi()
    request_plan, request_context, _, _ = UPSTREAM["FREEZE"]["_multi_section_request"](
        2, 2
    )
    rendered = UPSTREAM["_plan"](request_plan, request_context)
    rendered_context = UPSTREAM["_context"](request_plan, request_context)
    foreign_context = _context(rendered, rendered_context)
    foreign = build_draft_llm_execution_plan(rendered, foreign_context)
    assert validate_draft_llm_execution_plan(foreign, foreign_context) == ()
    changed = _seal_plan(
        plan.model_copy(
            update={
                "execution_requests": (
                    *plan.execution_requests,
                    foreign.execution_requests[0],
                )
            }
        )
    )
    assert "llm-execution-extra-request" in _codes(changed, context)
    request = plan.execution_requests[0]
    request = _seal_request(
        request.model_copy(
            update={
                "execution_messages": (
                    *request.execution_messages,
                    foreign.execution_requests[0].execution_messages[0],
                )
            }
        )
    )
    assert "llm-execution-extra-message" in _codes(
        _replace_request(plan, 0, request), context
    )
    same_plan_foreign = plan.execution_requests[1].execution_messages[0]
    request = plan.execution_requests[0]
    request = _seal_request(
        request.model_copy(
            update={
                "execution_messages": (*request.execution_messages, same_plan_foreign)
            }
        )
    )
    assert "llm-execution-extra-message" in _codes(
        _replace_request(plan, 0, request), context
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "plan-identity",
        "plan-fingerprint",
        "plan-reference",
        "section-identity",
        "section-fingerprint",
        "message-identity",
        "message-fingerprint",
        "section-order",
        "message-order",
        "missing-section",
        "missing-message",
    ),
)
def test_builder_rejects_malformed_phase_5_2_authority(mutation):
    source, rendered_context = UPSTREAM["_multi"]()
    if mutation == "plan-identity":
        source = source.model_copy(
            update={"identity": f"scout:draft-rendered-prompt-plan:{'f' * 64}"}
        )
    elif mutation == "plan-fingerprint":
        source = source.model_copy(update={"fingerprint": "f" * 64})
    elif mutation == "plan-reference":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"rendered_plan_reference": "rendered-prompt-plan:x"}
            )
        )
    elif mutation in {"section-identity", "section-fingerprint"}:
        field = mutation.split("-")[1]
        section = source.rendered_sections[0].model_copy(
            update={
                field: (
                    f"scout:rendered-prompt-section:{'f' * 64}"
                    if field == "identity"
                    else "f" * 64
                )
            }
        )
        source = UPSTREAM["_replace_section"](source, 0, section)
    elif mutation in {"message-identity", "message-fingerprint"}:
        field = mutation.split("-")[1]
        message = (
            source.rendered_sections[0]
            .rendered_messages[0]
            .model_copy(
                update={
                    field: (
                        f"scout:rendered-prompt-message:{'f' * 64}"
                        if field == "identity"
                        else "f" * 64
                    )
                }
            )
        )
        source = UPSTREAM["_replace_message"](source, 0, 0, message)
    elif mutation == "section-order":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"rendered_sections": tuple(reversed(source.rendered_sections))}
            )
        )
    elif mutation == "message-order":
        section = source.rendered_sections[0]
        section = UPSTREAM["_seal_section"](
            section.model_copy(
                update={"rendered_messages": tuple(reversed(section.rendered_messages))}
            )
        )
        source = UPSTREAM["_replace_section"](source, 0, section)
    elif mutation == "missing-section":
        source = UPSTREAM["_seal_plan"](
            source.model_copy(
                update={"rendered_sections": source.rendered_sections[1:]}
            )
        )
    else:
        section = source.rendered_sections[0]
        section = UPSTREAM["_seal_section"](
            section.model_copy(
                update={"rendered_messages": section.rendered_messages[1:]}
            )
        )
        source = UPSTREAM["_replace_section"](source, 0, section)
    context = _context(source, rendered_context)
    with pytest.raises(DomainValidationError) as first:
        build_draft_llm_execution_plan(source, context)
    with pytest.raises(DomainValidationError) as second:
        build_draft_llm_execution_plan(source, context)
    assert tuple(map(asdict, first.value.issues)) == tuple(
        map(asdict, second.value.issues)
    )


def _alternate(field, value):
    if isinstance(value, tuple):
        return (*value, value[0])
    if isinstance(value, int):
        return value + 1
    if field == "execution_role":
        return "context"
    if field.endswith("_fingerprint"):
        return ("f" if value[0] != "f" else "e") * 64
    if field.endswith("_identity"):
        return value[:-1] + ("f" if value[-1] != "f" else "e")
    return value + "-changed"


def test_every_semantic_field_changes_identity_and_fingerprint():
    plan = _plan()
    artifacts = (
        (
            plan.execution_requests[0].execution_messages[0],
            derive_llm_execution_message_identity,
            derive_llm_execution_message_fingerprint,
        ),
        (
            plan.execution_requests[0],
            derive_llm_execution_request_identity,
            derive_llm_execution_request_fingerprint,
        ),
        (
            plan,
            derive_draft_llm_execution_plan_identity,
            derive_draft_llm_execution_plan_fingerprint,
        ),
    )
    checked = 0
    for artifact, identity_function, fingerprint_function in artifacts:
        for field in artifact.__class__.model_fields:
            if field in {"identity", "fingerprint"}:
                continue
            changed = artifact.model_copy(
                update={field: _alternate(field, getattr(artifact, field))}
            )
            identity = identity_function(changed)
            assert identity != artifact.identity, field
            changed = changed.model_copy(update={"identity": identity})
            assert fingerprint_function(changed) != artifact.fingerprint, field
            checked += 1
    assert checked == 37


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
        "llmâ€execution-request:spoof",
    ),
)
def test_duplicate_diagnostics_do_not_expose_unsafe_values(unsafe):
    plan, context = _multi()
    requests = list(plan.execution_requests)
    for index in (0, 1):
        requests[index] = _seal_request(
            requests[index].model_copy(update={"execution_request_reference": unsafe})
        )
    changed = _seal_plan(
        plan.model_copy(update={"execution_requests": tuple(requests)})
    )
    issues = validate_draft_llm_execution_plan(changed, context)
    payloads = (
        json.dumps([asdict(item) for item in issues], ensure_ascii=False, default=str),
        str(issues),
    )
    assert issues and all(unsafe not in payload for payload in payloads)


def test_canonical_empty_adversarial_matrix():
    _, _, rendered, rendered_context = FREEZE["_empty_authority"]()
    context = _context(rendered, rendered_context)
    plan = build_draft_llm_execution_plan(rendered, context)
    assert plan.execution_requests == ()
    null = plan.model_construct(**{**plan.model_dump(), "execution_requests": None})
    assert _codes(null, context) == {"llm-execution-invalid-reconstructed-plan"}
    mutable = plan.model_construct(**{**plan.model_dump(), "execution_requests": []})
    assert validate_draft_llm_execution_plan(mutable, context) == ()
    assert _codes(
        plan.model_copy(
            update={"identity": f"scout:draft-llm-execution-plan:{'f' * 64}"}
        ),
        context,
    )
    assert _codes(plan.model_copy(update={"fingerprint": "f" * 64}), context)
    nonempty = _seal_plan(
        plan.model_copy(update={"execution_requests": (_plan().execution_requests[0],)})
    )
    assert "llm-execution-extra-request" in _codes(nonempty, context)


def test_empty_plan_rejects_foreign_valid_empty_plan_lineage():
    _, _, rendered, rendered_context = FREEZE["_empty_authority"]()
    context = _context(rendered, rendered_context)
    plan = build_draft_llm_execution_plan(rendered, context)
    _, _, foreign_rendered, foreign_rendered_context = FREEZE["_empty_authority"](
        purpose="foreign-empty-purpose"
    )
    foreign_context = _context(foreign_rendered, foreign_rendered_context)
    foreign = build_draft_llm_execution_plan(foreign_rendered, foreign_context)
    assert validate_draft_llm_execution_plan(foreign, foreign_context) == ()
    changed = _seal_plan(
        plan.model_copy(
            update={
                "rendered_plan_reference": foreign.rendered_plan_reference,
                "rendered_plan_identity": foreign.rendered_plan_identity,
                "rendered_plan_fingerprint": foreign.rendered_plan_fingerprint,
                "request_plan_reference": foreign.request_plan_reference,
                "request_plan_identity": foreign.request_plan_identity,
                "request_plan_fingerprint": foreign.request_plan_fingerprint,
                "draft_reference": foreign.draft_reference,
                "draft_fingerprint": foreign.draft_fingerprint,
            }
        )
    )
    first = _issues(changed, context)
    assert first == _issues(changed, context)
    assert "llm-execution-unknown-rendered-plan" in {item["code"] for item in first}
