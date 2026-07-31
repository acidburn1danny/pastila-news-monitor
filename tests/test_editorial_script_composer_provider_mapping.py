"""Focused tests for Phase 6.2 deterministic provider-request mapping."""

import runpy
import sys

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    DraftProviderRequestPlan,
    OpenAIProviderMessage,
    OpenAIProviderRequest,
    OpenAIProviderRequestPlan,
    ProviderMappingValidationContext,
    ProviderRequestPlanDescriptor,
    build_draft_provider_request_plan,
    build_openai_provider_request_plan,
    derive_draft_provider_request_plan_fingerprint,
    derive_draft_provider_request_plan_identity,
    derive_openai_provider_message_fingerprint,
    derive_openai_provider_message_identity,
    derive_openai_provider_request_fingerprint,
    derive_openai_provider_request_identity,
    derive_openai_provider_request_plan_fingerprint,
    derive_openai_provider_request_plan_identity,
    derive_provider_request_plan_descriptor_fingerprint,
    derive_provider_request_plan_descriptor_identity,
    validate_draft_provider_request_plan,
    validate_openai_provider_request_plan,
)

sys.path.insert(0, "tests")
UPSTREAM = runpy.run_path("tests/test_editorial_script_composer_llm_execution.py")
ZERO = "0" * 64


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def _descriptor():
    value = ProviderRequestPlanDescriptor(
        identity=f"scout:provider-request-plan-descriptor:{ZERO}",
        fingerprint=ZERO,
        provider_descriptor_reference=(
            "provider-mapping-descriptor:openai:phase-6.2-openai-v1"
        ),
        provider="openai",
        mapping_contract_version="phase-6.2-openai-v1",
    )
    return _seal(
        value,
        derive_provider_request_plan_descriptor_identity,
        derive_provider_request_plan_descriptor_fingerprint,
    )


def _execution(single=True):
    return UPSTREAM["_plan"]() if single else UPSTREAM["_multi"]()[0]


def _execution_context(single=True):
    return UPSTREAM["_context"]() if single else UPSTREAM["_multi"]()[1]


def _context(execution=None, execution_context=None, descriptor=None):
    execution = execution or _execution()
    return ProviderMappingValidationContext(
        execution_plans=(execution,),
        execution_validation_context=execution_context or _execution_context(),
        provider_descriptors=(descriptor or _descriptor(),),
    )


def _openai(single=True):
    execution = _execution(single)
    descriptor = _descriptor()
    context = _context(execution, _execution_context(single), descriptor)
    return (
        build_openai_provider_request_plan(execution, descriptor, context),
        context,
    )


def _generic(single=True):
    execution = _execution(single)
    descriptor = _descriptor()
    context = _context(execution, _execution_context(single), descriptor)
    return build_draft_provider_request_plan(execution, descriptor, context), context


def _seal_message(value):
    return _seal(
        value,
        derive_openai_provider_message_identity,
        derive_openai_provider_message_fingerprint,
    )


def _seal_request(value):
    return _seal(
        value,
        derive_openai_provider_request_identity,
        derive_openai_provider_request_fingerprint,
    )


def _seal_openai_plan(value):
    return _seal(
        value,
        derive_openai_provider_request_plan_identity,
        derive_openai_provider_request_plan_fingerprint,
    )


def _seal_generic(value):
    return _seal(
        value,
        derive_draft_provider_request_plan_identity,
        derive_draft_provider_request_plan_fingerprint,
    )


def _replace_request(plan, index, request):
    items = list(plan.requests)
    items[index] = request
    return _seal_openai_plan(plan.model_copy(update={"requests": tuple(items)}))


def _replace_message(plan, request_index, message_index, message):
    request = plan.requests[request_index]
    items = list(request.messages)
    items[message_index] = message
    request = _seal_request(request.model_copy(update={"messages": tuple(items)}))
    return _replace_request(plan, request_index, request)


def test_exact_models_fields_and_immutability():
    expected = {
        ProviderRequestPlanDescriptor: {
            "identity",
            "fingerprint",
            "provider_descriptor_reference",
            "provider",
            "mapping_contract_version",
        },
        DraftProviderRequestPlan: {
            "identity",
            "fingerprint",
            "provider_request_plan_reference",
            "provider_descriptor",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "provider_plan_reference",
            "provider_plan_identity",
            "provider_plan_fingerprint",
            "openai_request_plan",
        },
        OpenAIProviderMessage: {
            "identity",
            "fingerprint",
            "openai_message_reference",
            "execution_message_reference",
            "execution_message_identity",
            "execution_message_fingerprint",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "role",
            "content",
            "ordinal",
        },
        OpenAIProviderRequest: {
            "identity",
            "fingerprint",
            "openai_request_reference",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "request_ordinal",
            "messages",
        },
        OpenAIProviderRequestPlan: {
            "identity",
            "fingerprint",
            "openai_request_plan_reference",
            "provider_descriptor_reference",
            "provider_descriptor_identity",
            "provider_descriptor_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "requests",
        },
        ProviderMappingValidationContext: {
            "execution_plans",
            "execution_validation_context",
            "provider_descriptors",
        },
    }
    for model, fields in expected.items():
        assert set(model.model_fields) == fields
    plan, _ = _generic()
    with pytest.raises(ValidationError):
        plan.identity = "changed"
    with pytest.raises(ValidationError):
        DraftProviderRequestPlan.model_validate({**plan.model_dump(), "extra": True})


@pytest.mark.parametrize(
    "provider",
    (
        "OpenAI",
        "OPENAI",
        " openai",
        "openai ",
        "open-ai",
        "gpt",
        "anthropic",
        "gemini",
        "",
    ),
)
def test_provider_identifier_is_closed_strict_and_canonical(provider):
    with pytest.raises(ValidationError):
        ProviderRequestPlanDescriptor(
            identity=f"scout:provider-request-plan-descriptor:{ZERO}",
            fingerprint=ZERO,
            provider_descriptor_reference="provider-mapping-descriptor:openai:phase-6.2-openai-v1",
            provider=provider,
            mapping_contract_version="phase-6.2-openai-v1",
        )


def test_complete_repeated_provider_descriptor_is_rejected():
    context = _context()
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=context.execution_plans,
            execution_validation_context=context.execution_validation_context,
            provider_descriptors=(context.provider_descriptors[0],) * 2,
        )
    assert "provider-mapping-duplicate-provider_descriptors-identity" in str(
        caught.value
    )


def test_projection_role_content_order_and_lineage_are_exact():
    plan, context = _openai(False)
    source = context.execution_plans[0]
    assert len(plan.requests) == len(source.execution_requests)
    for request, execution_request in zip(
        plan.requests, source.execution_requests, strict=True
    ):
        assert request.request_ordinal == execution_request.request_ordinal
        assert len(request.messages) == len(execution_request.execution_messages)
        for message, execution_message in zip(
            request.messages, execution_request.execution_messages, strict=True
        ):
            expected_role = (
                "developer"
                if execution_message.execution_role == "instruction"
                else "user"
            )
            assert message.role == expected_role
            assert message.content == execution_message.execution_text
            assert message.ordinal == execution_message.ordinal
    assert validate_openai_provider_request_plan(plan, context) == ()


def test_generic_wrapper_is_typed_and_authoritatively_validated():
    plan, context = _generic()
    assert plan.provider_descriptor.provider == "openai"
    assert plan.openai_request_plan.identity == plan.provider_plan_identity
    assert plan.openai_request_plan.fingerprint == plan.provider_plan_fingerprint
    assert validate_draft_provider_request_plan(plan, context) == ()


@pytest.mark.parametrize("role", ("developer", "user"))
def test_wrong_valid_role_is_rejected_after_correct_resealing(role):
    plan, context = _openai()
    message = plan.requests[0].messages[0]
    if role == message.role:
        role = "developer" if role == "user" else "user"
    changed = _seal_message(message.model_copy(update={"role": role}))
    issues = validate_openai_provider_request_plan(
        _replace_message(plan, 0, 0, changed), context
    )
    assert "provider-mapping-openai-message-role-mismatch" in {
        item.code for item in issues
    }


@pytest.mark.parametrize(
    "role",
    (
        "system",
        "assistant",
        "tool",
        "function",
        "Developer",
        "USER",
        " developer",
        "user ",
        "",
        "usеr",
    ),
)
def test_noncanonical_openai_roles_are_model_invalid(role):
    plan, _ = _openai()
    message = plan.requests[0].messages[0]
    with pytest.raises(ValidationError):
        OpenAIProviderMessage.model_validate({**message.model_dump(), "role": role})


@pytest.mark.parametrize(
    "content",
    (
        "altered content",
        "original appended",
        "prepended original",
        "line removed",
        "line added\nextra",
        "line one\r\nline two",
        "line one\rline two",
        "line one\u2028line two",
        "line one\u2029line two",
        " leading whitespace",
        "trailing whitespace ",
        "trailing newline\n",
        "tab\tcontent",
        "NBSP\u00a0content",
        "thin\u2009space",
        "Unicode confusable е",
        "changed",
    ),
)
def test_content_authority_rejects_resealed_mutations(content):
    plan, context = _openai()
    message = _seal_message(
        plan.requests[0].messages[0].model_copy(update={"content": content})
    )
    issues = validate_openai_provider_request_plan(
        _replace_message(plan, 0, 0, message), context
    )
    assert "provider-mapping-openai-message-content-mismatch" in {
        item.code for item in issues
    }


def test_canonical_references_and_empty_projection():
    plan, _ = _openai()
    assert (
        plan.openai_request_plan_reference
        == f"openai-request-plan:{plan.execution_plan_identity}"
    )
    assert (
        plan.requests[0].openai_request_reference
        == f"openai-request:{plan.requests[0].execution_request_identity}"
    )
    assert (
        plan.requests[0].messages[0].openai_message_reference
        == f"openai-message:{plan.requests[0].messages[0].execution_message_identity}"
    )
    _, _, rendered, rendered_context = UPSTREAM["FREEZE"]["_empty_authority"]()
    execution_context = UPSTREAM["_context"](rendered, rendered_context)
    execution = UPSTREAM["build_draft_llm_execution_plan"](rendered, execution_context)
    descriptor = _descriptor()
    context = _context(execution, execution_context, descriptor)
    empty = build_openai_provider_request_plan(execution, descriptor, context)
    assert empty.requests == ()
    assert validate_openai_provider_request_plan(empty, context) == ()
