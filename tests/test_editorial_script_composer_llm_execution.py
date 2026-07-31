"""Focused tests for Phase 6.1 provider-neutral execution planning."""

import json
import runpy
import subprocess
import sys
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    DraftLLMExecutionPlan,
    LLMExecutionMessage,
    LLMExecutionRequest,
    LLMExecutionValidationContext,
    build_draft_llm_execution_plan,
    derive_draft_llm_execution_plan_fingerprint,
    derive_draft_llm_execution_plan_identity,
    derive_llm_execution_message_fingerprint,
    derive_llm_execution_message_identity,
    derive_llm_execution_request_fingerprint,
    derive_llm_execution_request_identity,
    validate_draft_llm_execution_plan,
)

UPSTREAM = runpy.run_path("tests/test_editorial_script_composer_prompt_rendering.py")
FREEZE = runpy.run_path(
    "tests/test_editorial_script_composer_prompt_rendering_freeze.py"
)


def _source():
    return UPSTREAM["_plan"]()


def _source_context():
    return UPSTREAM["_context"]()


def _context(source=None, source_context=None):
    return LLMExecutionValidationContext(
        rendered_prompt_plans=(source or _source(),),
        rendered_prompt_validation_context=source_context or _source_context(),
    )


def _plan(source=None, source_context=None):
    source = source or _source()
    return build_draft_llm_execution_plan(
        source, _context(source, source_context or _source_context())
    )


def _seal_message(value):
    value = value.model_copy(
        update={"identity": derive_llm_execution_message_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_llm_execution_message_fingerprint(value)}
    )


def _seal_request(value):
    value = value.model_copy(
        update={"identity": derive_llm_execution_request_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_llm_execution_request_fingerprint(value)}
    )


def _seal_plan(value):
    value = value.model_copy(
        update={"identity": derive_draft_llm_execution_plan_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_draft_llm_execution_plan_fingerprint(value)}
    )


def _replace_request(plan, index, request):
    requests = list(plan.execution_requests)
    requests[index] = request
    return _seal_plan(plan.model_copy(update={"execution_requests": tuple(requests)}))


def _replace_message(plan, request_index, message_index, message):
    request = plan.execution_requests[request_index]
    messages = list(request.execution_messages)
    messages[message_index] = message
    request = _seal_request(
        request.model_copy(update={"execution_messages": tuple(messages)})
    )
    return _replace_request(plan, request_index, request)


def _codes(plan, context=None):
    return {
        issue.code
        for issue in validate_draft_llm_execution_plan(plan, context or _context())
    }


def _multi():
    rendered, rendered_context = UPSTREAM["_multi"]()
    context = _context(rendered, rendered_context)
    return build_draft_llm_execution_plan(rendered, context), context


def test_models_are_strict_frozen_and_tuple_based():
    plan = _plan()
    assert isinstance(plan.execution_requests, tuple)
    assert isinstance(plan.execution_requests[0].execution_messages, tuple)
    with pytest.raises(ValidationError):
        plan.execution_plan_reference = "changed"
    with pytest.raises(ValidationError):
        DraftLLMExecutionPlan.model_validate(
            {**plan.model_dump(), "unexpected": "value"}
        )
    with pytest.raises(ValidationError):
        LLMExecutionRequest.model_validate(
            {**plan.execution_requests[0].model_dump(), "request_ordinal": "0"}
        )


def test_valid_projection_is_exact_deterministic_and_provider_neutral():
    source = _source()
    context = _context(source)
    first = build_draft_llm_execution_plan(source, context)
    second = build_draft_llm_execution_plan(source, context)
    assert first == second
    assert validate_draft_llm_execution_plan(first, context) == ()
    request = first.execution_requests[0]
    message = request.execution_messages[0]
    rendered = source.rendered_sections[0].rendered_messages[0]
    assert message.execution_role == rendered.rendering_role == "generation"
    assert message.execution_text == rendered.rendered_text
    assert message.ordinal == rendered.ordinal
    assert request.request_ordinal == 0


def test_multi_request_and_multi_message_projection_preserves_order():
    plan, context = _multi()
    source = context.rendered_prompt_plans[0]
    assert len(plan.execution_requests) == len(source.rendered_sections) == 3
    assert all(len(item.execution_messages) == 3 for item in plan.execution_requests)
    assert tuple(item.request_ordinal for item in plan.execution_requests) == (0, 1, 2)
    assert tuple(
        item.ordinal for item in plan.execution_requests[0].execution_messages
    ) == (0, 1, 2)


def test_canonical_references_are_derived_from_authoritative_identities():
    plan = _plan()
    request = plan.execution_requests[0]
    message = request.execution_messages[0]
    assert (
        plan.execution_plan_reference
        == f"llm-execution-plan:{plan.rendered_plan_identity}"
    )
    assert request.execution_request_reference == (
        f"llm-execution-request:{request.rendered_section_identity}"
    )
    assert message.execution_message_reference == (
        f"llm-execution-message:{message.rendered_message_identity}"
    )


def test_canonical_empty_plan():
    request, _, rendered, rendered_context = FREEZE["_empty_authority"]()
    assert request.request_sections == ()
    context = _context(rendered, rendered_context)
    plan = build_draft_llm_execution_plan(rendered, context)
    assert plan.execution_requests == ()
    assert validate_draft_llm_execution_plan(plan, context) == ()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        (
            "execution_plan_reference",
            "llm-execution-plan:wrong",
            "llm-execution-execution-plan-reference-mismatch",
        ),
        (
            "rendered_plan_fingerprint",
            "f" * 64,
            "llm-execution-rendered-plan-fingerprint-mismatch",
        ),
        (
            "request_plan_fingerprint",
            "f" * 64,
            "llm-execution-request-plan-fingerprint-mismatch",
        ),
        ("draft_fingerprint", "f" * 64, "llm-execution-draft-fingerprint-mismatch"),
        (
            "normalized_input_identity",
            f"scout:normalized-input:{'f' * 64}",
            "llm-execution-normalized-input-identity-mismatch",
        ),
    ),
)
def test_resealed_plan_lineage_substitutions_are_rejected(field, value, code):
    changed = _seal_plan(_plan().model_copy(update={field: value}))
    assert code in _codes(changed)


@pytest.mark.parametrize("role", ("instruction", "context"))
def test_valid_but_authoritatively_wrong_roles_are_rejected(role):
    plan = _plan()
    message = _seal_message(
        plan.execution_requests[0]
        .execution_messages[0]
        .model_copy(update={"execution_role": role})
    )
    assert "llm-execution-message-execution-role-mismatch" in _codes(
        _replace_message(plan, 0, 0, message)
    )


@pytest.mark.parametrize(
    "role",
    (
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
def test_provider_and_malformed_roles_fail_reconstruction(role):
    plan = _plan()
    message = (
        plan.execution_requests[0]
        .execution_messages[0]
        .model_copy(update={"execution_role": role})
    )
    assert "llm-execution-invalid-reconstructed-plan" in _codes(
        _replace_message(plan, 0, 0, message)
    )


@pytest.mark.parametrize(
    "text",
    (
        "changed",
        "prefix ",
        "\r\n",
        "\u2028",
        "\n",
        "\t",
        "confusable Ñ•",
    ),
)
def test_resealed_execution_text_substitutions_are_rejected(text):
    plan = _plan()
    original = plan.execution_requests[0].execution_messages[0]
    message = _seal_message(original.model_copy(update={"execution_text": text}))
    assert "llm-execution-message-execution-text-mismatch" in _codes(
        _replace_message(plan, 0, 0, message)
    )


class _Hostile:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, **_kwargs):
        raise self.error_type("private traceback C:\\Users\\secret 0x7ff")


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize("side", ("plan", "context"))
def test_ordinary_reconstruction_failures_are_contained(error_type, side):
    issues = (
        validate_draft_llm_execution_plan(_Hostile(error_type), _context())
        if side == "plan"
        else validate_draft_llm_execution_plan(_plan(), _Hostile(error_type))
    )
    payload = json.dumps([asdict(issue) for issue in issues], default=str)
    assert issues
    assert all(value not in payload for value in ("private", "traceback", "0x7ff"))


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize("side", ("plan", "context"))
def test_process_control_exceptions_propagate(error_type, side):
    with pytest.raises(error_type):
        if side == "plan":
            validate_draft_llm_execution_plan(_Hostile(error_type), _context())
        else:
            validate_draft_llm_execution_plan(_plan(), _Hostile(error_type))


def test_separate_process_artifacts_and_diagnostics_are_deterministic():
    code = (
        "import runpy,sys,json;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_llm_execution.py');"
        "p=n['_plan']();print(json.dumps(p.model_dump(mode='json'),sort_keys=True,separators=(',',':')));"
        "p=p.model_copy(update={'fingerprint':'f'*64});"
        "from dataclasses import asdict;print(json.dumps([asdict(x) for x in n['validate_draft_llm_execution_plan'](p,n['_context']())],sort_keys=True,separators=(',',':'),default=str))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second


def test_builder_rejects_invalid_phase_5_2_authority():
    source = _source().model_copy(update={"fingerprint": "f" * 64})
    context = _context(source)
    with pytest.raises(DomainValidationError):
        build_draft_llm_execution_plan(source, context)


@pytest.mark.parametrize("side", ("plan", "context"))
@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
def test_builder_contains_ordinary_reconstruction_failures(side, error_type):
    with pytest.raises(DomainValidationError) as caught:
        if side == "plan":
            build_draft_llm_execution_plan(_Hostile(error_type), _context())
        else:
            build_draft_llm_execution_plan(_source(), _Hostile(error_type))
    assert {item.code for item in caught.value.issues} == {
        "llm-execution-invalid-builder-input"
    }


@pytest.mark.parametrize("side", ("plan", "context"))
@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
def test_builder_propagates_process_control_exceptions(side, error_type):
    with pytest.raises(error_type):
        if side == "plan":
            build_draft_llm_execution_plan(_Hostile(error_type), _context())
        else:
            build_draft_llm_execution_plan(_source(), _Hostile(error_type))


def test_caller_owned_collections_are_not_retained():
    source = _source()
    source_payload = source.model_dump(mode="python")
    source_sections = list(source_payload["rendered_sections"])
    source_payload["rendered_sections"] = source_sections
    context_payload = _context(source).model_dump(mode="python")
    context_plans = list(context_payload["rendered_prompt_plans"])
    context_payload["rendered_prompt_plans"] = context_plans
    reconstructed_source = type(source).model_validate(source_payload)
    reconstructed_context = LLMExecutionValidationContext.model_validate(
        context_payload
    )
    result = build_draft_llm_execution_plan(reconstructed_source, reconstructed_context)
    source_sections.clear()
    context_plans.clear()
    assert result.execution_requests
    assert reconstructed_source.rendered_sections
    assert reconstructed_context.rendered_prompt_plans
    assert validate_draft_llm_execution_plan(result, reconstructed_context) == ()


def test_public_models_are_the_expected_types():
    plan = _plan()
    assert isinstance(plan, DraftLLMExecutionPlan)
    assert isinstance(plan.execution_requests[0], LLMExecutionRequest)
    assert isinstance(
        plan.execution_requests[0].execution_messages[0], LLMExecutionMessage
    )
