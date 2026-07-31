"""Phase 6.3 deterministic provider execution-result regressions."""

import ast
import json
import runpy
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.editor.script_composer as public_api
from pastila_scout.editor.script_composer import (
    DomainValidationError,
    OpenAIProviderExecutionResult,
    OpenAIProviderResponse,
    OpenAIProviderResponseMessage,
    ProviderExecutionResult,
    ProviderExecutionResultValidationContext,
    build_openai_extracted_execution_result,
    build_openai_provider_execution_result,
    build_provider_execution_result,
    derive_openai_extracted_execution_result_fingerprint,
    derive_openai_extracted_execution_result_identity,
    derive_openai_extracted_response_fingerprint,
    derive_openai_extracted_response_identity,
    derive_openai_extracted_response_message_fingerprint,
    derive_openai_extracted_response_message_identity,
    derive_openai_provider_execution_result_fingerprint,
    derive_openai_provider_execution_result_identity,
    derive_openai_provider_response_fingerprint,
    derive_openai_provider_response_identity,
    derive_openai_provider_response_message_fingerprint,
    derive_openai_provider_response_message_identity,
    derive_provider_execution_result_fingerprint,
    derive_provider_execution_result_identity,
    validate_openai_provider_execution_result,
    validate_provider_execution_result,
)

sys.path.insert(0, "tests")
MAPPING = runpy.run_path("tests/test_editorial_script_composer_provider_mapping.py")


def _authority(single=False):
    plan, mapping_context = MAPPING["_generic"](single)
    outputs = tuple(
        f"Rezultat editorial {index} — știre"
        for index, _ in enumerate(plan.openai_request_plan.requests)
    )
    reasons = tuple(
        ("stop", "length", "content_filter")[index % 3] for index in range(len(outputs))
    )
    extracted = build_openai_extracted_execution_result(
        plan, outputs, reasons, mapping_context
    )
    context = ProviderExecutionResultValidationContext(
        provider_request_plans=(plan,),
        extracted_execution_results=(extracted,),
        provider_mapping_validation_context=mapping_context,
    )
    return plan, context, outputs, reasons


def _generic(single=False):
    plan, context, outputs, reasons = _authority(single)
    return build_provider_execution_result(plan, outputs, reasons, context), context


def _openai(single=False):
    plan, context, outputs, reasons = _authority(single)
    return (
        build_openai_provider_execution_result(plan, outputs, reasons, context),
        context,
    )


def _seal(value, identity_fn, fingerprint_fn):
    value = value.model_copy(update={"identity": identity_fn(value)})
    return value.model_copy(update={"fingerprint": fingerprint_fn(value)})


def _seal_message(value):
    return _seal(
        value,
        derive_openai_provider_response_message_identity,
        derive_openai_provider_response_message_fingerprint,
    )


def _seal_response(value):
    return _seal(
        value,
        derive_openai_provider_response_identity,
        derive_openai_provider_response_fingerprint,
    )


def _seal_openai(value):
    return _seal(
        value,
        derive_openai_provider_execution_result_identity,
        derive_openai_provider_execution_result_fingerprint,
    )


def _seal_generic(value):
    return _seal(
        value,
        derive_provider_execution_result_identity,
        derive_provider_execution_result_fingerprint,
    )


def _replace_response(result, index, response):
    responses = list(result.responses)
    responses[index] = response
    return _seal_openai(result.model_copy(update={"responses": tuple(responses)}))


def _replace_message(result, response_index, message):
    response = result.responses[response_index]
    response = _seal_response(response.model_copy(update={"messages": (message,)}))
    return _replace_response(result, response_index, response)


def _codes(result, context):
    return {
        issue.code
        for issue in validate_openai_provider_execution_result(result, context)
    }


def test_exact_public_models_and_fields():
    expected = {
        OpenAIProviderResponseMessage: {
            "identity",
            "fingerprint",
            "provider_response_message_reference",
            "openai_request_reference",
            "openai_request_identity",
            "openai_request_fingerprint",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "ordinal",
            "generated_text",
            "finish_reason",
        },
        OpenAIProviderResponse: {
            "identity",
            "fingerprint",
            "provider_response_reference",
            "openai_request_reference",
            "openai_request_identity",
            "openai_request_fingerprint",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "response_ordinal",
            "messages",
        },
        OpenAIProviderExecutionResult: {
            "identity",
            "fingerprint",
            "openai_provider_execution_result_reference",
            "provider",
            "provider_request_plan_reference",
            "provider_request_plan_identity",
            "provider_request_plan_fingerprint",
            "openai_request_plan_reference",
            "openai_request_plan_identity",
            "openai_request_plan_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "responses",
        },
        ProviderExecutionResultValidationContext: {
            "provider_request_plans",
            "provider_mapping_validation_context",
        },
        ProviderExecutionResult: {
            "identity",
            "fingerprint",
            "provider_execution_result_reference",
            "provider",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "provider_request_plan_reference",
            "provider_request_plan_identity",
            "provider_request_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "provider_result_reference",
            "provider_result_identity",
            "provider_result_fingerprint",
            "openai_execution_result",
        },
    }
    for model, fields in expected.items():
        if model is OpenAIProviderResponseMessage:
            fields |= {
                "provider_response_reference",
                "provider_request_plan_reference",
                "provider_request_plan_identity",
                "provider_request_plan_fingerprint",
                "openai_request_plan_reference",
                "openai_request_plan_identity",
                "openai_request_plan_fingerprint",
                "draft_reference",
                "draft_fingerprint",
            }
        if model is OpenAIProviderResponse:
            fields |= {
                "provider_request_plan_reference",
                "provider_request_plan_identity",
                "provider_request_plan_fingerprint",
                "openai_request_plan_reference",
                "openai_request_plan_identity",
                "openai_request_plan_fingerprint",
            }
        if model is ProviderExecutionResultValidationContext:
            fields.add("extracted_execution_results")
        assert set(model.model_fields) == fields


def test_models_are_strict_frozen_and_nested_tuple_based():
    result, _ = _generic()
    with pytest.raises(ValidationError):
        result.identity = "changed"
    with pytest.raises(ValidationError):
        ProviderExecutionResult.model_validate({**result.model_dump(), "extra": True})
    assert isinstance(result.openai_execution_result.responses, tuple)
    assert isinstance(result.openai_execution_result.responses[0].messages, tuple)


@pytest.mark.parametrize(
    "finish_reason",
    ("Stop", " STOP", "stop ", "tool_calls", "function_call", "", "stоp"),
)
def test_finish_reason_is_closed(finish_reason):
    result, _ = _openai()
    message = result.responses[0].messages[0]
    with pytest.raises(ValidationError):
        OpenAIProviderResponseMessage.model_validate(
            {**message.model_dump(), "finish_reason": finish_reason}
        )


def test_builder_projection_references_lineage_order_and_output_are_exact():
    plan, context, outputs, reasons = _authority()
    result = build_provider_execution_result(plan, outputs, reasons, context)
    concrete = result.openai_execution_result
    assert result.provider_execution_result_reference == (
        f"provider-execution-result:openai:{plan.identity}"
    )
    assert concrete.openai_provider_execution_result_reference == (
        f"openai-provider-execution-result:{plan.openai_request_plan.identity}"
    )
    assert len(concrete.responses) == len(plan.openai_request_plan.requests)
    for ordinal, (response, request, text, reason) in enumerate(
        zip(
            concrete.responses,
            plan.openai_request_plan.requests,
            outputs,
            reasons,
            strict=True,
        )
    ):
        assert response.response_ordinal == ordinal
        assert response.provider_response_reference == (
            f"openai-provider-response:{request.identity}"
        )
        assert len(response.messages) == 1
        message = response.messages[0]
        assert message.provider_response_message_reference == (
            f"openai-provider-response-message:{request.identity}:0"
        )
        assert message.generated_text == text
        assert message.finish_reason == reason
    assert validate_provider_execution_result(result, context) == ()


@pytest.mark.parametrize("count_delta", (-1, 1))
@pytest.mark.parametrize("target", ("outputs", "reasons"))
def test_builder_rejects_incomplete_or_extra_output(target, count_delta):
    plan, context, outputs, reasons = _authority()
    values = list(outputs if target == "outputs" else reasons)
    if count_delta < 0:
        values.pop()
    else:
        values.append("extra" if target == "outputs" else "stop")
    with pytest.raises(DomainValidationError) as caught:
        build_provider_execution_result(
            plan,
            tuple(values) if target == "outputs" else outputs,
            tuple(values) if target == "reasons" else reasons,
            context,
        )
    assert "provider-result-output-count-mismatch" in {
        issue.code for issue in caught.value.issues
    }


@pytest.mark.parametrize(
    ("outputs", "reasons", "code"),
    (
        (("",), ("stop",), "provider-result-invalid-generated-output"),
        ((1,), ("stop",), "provider-result-invalid-generated-output"),
        (("valid",), ("tool_calls",), "provider-result-invalid-finish-reason"),
    ),
)
def test_builder_rejects_invalid_extracted_output(outputs, reasons, code):
    plan, context, _, _ = _authority(True)
    with pytest.raises(DomainValidationError) as caught:
        build_openai_provider_execution_result(plan, outputs, reasons, context)
    assert code in {issue.code for issue in caught.value.issues}


def _alternate(field, value):
    if isinstance(value, str):
        if field == "provider":
            return "foreign"
        if field == "finish_reason":
            return "length" if value != "length" else "stop"
        if field.endswith(("identity", "fingerprint")):
            return value[:-1] + ("e" if value.endswith("f") else "f")
        return value + "-changed"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, tuple):
        return value + value[:1]
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"fingerprint": "f" * 64})
    raise AssertionError(field)


def test_every_semantic_field_changes_identity_and_fingerprint():
    generic, _ = _generic()
    concrete = generic.openai_execution_result
    artifacts = (
        (
            generic,
            derive_provider_execution_result_identity,
            derive_provider_execution_result_fingerprint,
        ),
        (
            concrete,
            derive_openai_provider_execution_result_identity,
            derive_openai_provider_execution_result_fingerprint,
        ),
        (
            concrete.responses[0],
            derive_openai_provider_response_identity,
            derive_openai_provider_response_fingerprint,
        ),
        (
            concrete.responses[0].messages[0],
            derive_openai_provider_response_message_identity,
            derive_openai_provider_response_message_fingerprint,
        ),
    )
    checked = 0
    for artifact, identity_fn, fingerprint_fn in artifacts:
        for field in artifact.__class__.model_fields:
            if field in {"identity", "fingerprint"}:
                continue
            changed = artifact.model_copy(
                update={field: _alternate(field, getattr(artifact, field))}
            )
            identity = identity_fn(changed)
            assert identity != artifact.identity, field
            changed = changed.model_copy(update={"identity": identity})
            assert fingerprint_fn(changed) != artifact.fingerprint, field
            checked += 1
    assert checked == 70


def test_every_extracted_authority_field_changes_identity_and_fingerprint():
    _, context, _, _ = _authority()
    authority = context.extracted_execution_results[0]
    artifacts = (
        (
            authority,
            derive_openai_extracted_execution_result_identity,
            derive_openai_extracted_execution_result_fingerprint,
        ),
        (
            authority.responses[0],
            derive_openai_extracted_response_identity,
            derive_openai_extracted_response_fingerprint,
        ),
        (
            authority.responses[0].messages[0],
            derive_openai_extracted_response_message_identity,
            derive_openai_extracted_response_message_fingerprint,
        ),
    )
    checked = 0
    for artifact, identity_fn, fingerprint_fn in artifacts:
        for field in artifact.__class__.model_fields:
            if field in {"identity", "fingerprint"}:
                continue
            changed = artifact.model_copy(
                update={field: _alternate(field, getattr(artifact, field))}
            )
            identity = identity_fn(changed)
            assert identity != artifact.identity, field
            changed = changed.model_copy(update={"identity": identity})
            assert fingerprint_fn(changed) != artifact.fingerprint, field
            checked += 1
    assert checked == 56


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    (
        (
            "generated_text",
            "Conținut străin, dar corect resigilat",
            "provider-result-message-generated-text-mismatch",
        ),
        ("finish_reason", "length", "provider-result-message-finish-reason-mismatch"),
    ),
)
def test_resealed_submitted_output_cannot_replace_independent_authority(
    field, replacement, expected_code
):
    result, context = _openai()
    message = result.responses[0].messages[0]
    if getattr(message, field) == replacement:
        replacement = "stop"
    changed_message = _seal_message(message.model_copy(update={field: replacement}))
    changed = _replace_message(result, 0, changed_message)
    assert expected_code in _codes(changed, context)


def test_independent_extracted_authority_is_required_and_not_result_derived():
    result, context = _openai()
    missing = context.model_copy(update={"extracted_execution_results": ()})
    issues = validate_openai_provider_execution_result(result, missing)
    assert {issue.code for issue in issues} == {"provider-result-invalid-context"}


@pytest.mark.parametrize(
    ("level", "field", "code"),
    (
        (
            "result",
            "openai_provider_execution_result_reference",
            "provider-result-openai-openai-provider-execution-result-reference-mismatch",
        ),
        (
            "response",
            "provider_response_reference",
            "provider-result-response-provider-response-reference-mismatch",
        ),
        (
            "message",
            "provider_response_message_reference",
            "provider-result-message-provider-response-message-reference-mismatch",
        ),
    ),
)
def test_correctly_resealed_noncanonical_references_are_rejected(level, field, code):
    result, context = _openai()
    if level == "result":
        changed = _seal_openai(result.model_copy(update={field: "foreign:result"}))
    elif level == "response":
        response = _seal_response(
            result.responses[0].model_copy(update={field: "foreign:response"})
        )
        changed = _replace_response(result, 0, response)
    else:
        message = _seal_message(
            result.responses[0]
            .messages[0]
            .model_copy(update={field: "foreign:message"})
        )
        changed = _replace_message(result, 0, message)
    assert code in _codes(changed, context)


@pytest.mark.parametrize("seal", ("identity", "fingerprint"))
@pytest.mark.parametrize("level", ("result", "response", "message"))
def test_stale_nested_seals_are_rejected(level, seal):
    result, context = _openai()
    stale_identity = result.identity[:-1] + (
        "e" if result.identity.endswith("f") else "f"
    )
    if level == "result":
        changed = result.model_copy(
            update={seal: stale_identity if seal == "identity" else "f" * 64}
        )
    elif level == "response":
        original = result.responses[0]
        value = (
            original.identity[:-1] + ("e" if original.identity.endswith("f") else "f")
            if seal == "identity"
            else "f" * 64
        )
        response = original.model_copy(update={seal: value})
        changed = _replace_response(result, 0, response)
    else:
        original = result.responses[0].messages[0]
        value = (
            original.identity[:-1] + ("e" if original.identity.endswith("f") else "f")
            if seal == "identity"
            else "f" * 64
        )
        message = original.model_copy(update={seal: value})
        changed = _replace_message(result, 0, message)
    expected = f"provider-result-invalid-{level if level != 'result' else 'openai-result'}-{seal}"
    assert expected in _codes(changed, context)


@pytest.mark.parametrize("seal", ("identity", "fingerprint"))
def test_stale_generic_seals_are_rejected(seal):
    result, context = _generic()
    value = (
        result.identity[:-1] + ("e" if result.identity.endswith("f") else "f")
        if seal == "identity"
        else "f" * 64
    )
    changed = result.model_copy(update={seal: value})
    codes = {
        issue.code for issue in validate_provider_execution_result(changed, context)
    }
    assert f"provider-result-invalid-generic-result-{seal}" in codes


@pytest.mark.parametrize("level", ("generic", "result", "response", "message"))
def test_forged_resealed_semantic_artifacts_are_rejected(level):
    generic, context = _generic()
    result = generic.openai_execution_result
    if level == "generic":
        changed = _seal_generic(
            generic.model_copy(update={"draft_reference": "draft:forged"})
        )
        assert validate_provider_execution_result(changed, context)
    elif level == "result":
        changed = _seal_openai(
            result.model_copy(update={"draft_reference": "draft:forged"})
        )
        assert validate_openai_provider_execution_result(changed, context)
    elif level == "response":
        response = _seal_response(
            result.responses[0].model_copy(update={"draft_reference": "draft:forged"})
        )
        changed = _replace_response(result, 0, response)
        assert validate_openai_provider_execution_result(changed, context)
    else:
        message = _seal_message(
            result.responses[0]
            .messages[0]
            .model_copy(
                update={"execution_plan_reference": "llm-execution-plan:forged"}
            )
        )
        changed = _replace_message(result, 0, message)
        assert validate_openai_provider_execution_result(changed, context)


def test_correctly_resealed_wrong_lineage_is_rejected():
    result, context = _openai()
    message = _seal_message(
        result.responses[0]
        .messages[0]
        .model_copy(update={"execution_plan_identity": result.responses[1].identity})
    )
    changed = _replace_message(result, 0, message)
    assert "provider-result-message-execution-plan-identity-mismatch" in _codes(
        changed, context
    )


def test_response_reordering_is_rejected_even_with_corrected_ordinals():
    result, context = _openai()
    responses = tuple(
        _seal_response(item.model_copy(update={"response_ordinal": index}))
        for index, item in enumerate(reversed(result.responses))
    )
    changed = _seal_openai(result.model_copy(update={"responses": responses}))
    assert "provider-result-invalid-response-order" in _codes(changed, context)


@pytest.mark.parametrize("index", (0, 1, 2), ids=("first", "middle", "last"))
def test_response_positional_omissions_are_rejected(index):
    result, context = _openai()
    responses = result.responses[:index] + result.responses[index + 1 :]
    omitted = _seal_openai(result.model_copy(update={"responses": responses}))
    assert validate_openai_provider_execution_result(omitted, context)


def test_duplicate_responses_are_rejected():
    result, context = _openai()
    duplicate = _seal_openai(
        result.model_copy(
            update={"responses": result.responses + (result.responses[0],)}
        )
    )
    assert any(
        code.startswith("provider-result-duplicate-")
        for code in _codes(duplicate, context)
    )


def test_duplicate_response_messages_are_rejected():
    result, context = _openai()
    response = result.responses[0]
    response = _seal_response(
        response.model_copy(update={"messages": response.messages * 2})
    )
    changed = _replace_response(result, 0, response)
    codes = _codes(changed, context)
    assert any(code.startswith("provider-result-duplicate-message-") for code in codes)


def test_foreign_valid_response_is_rejected():
    result, context = _openai(False)
    foreign, foreign_context = _openai(True)
    assert validate_openai_provider_execution_result(foreign, foreign_context) == ()
    changed = _seal_openai(
        result.model_copy(
            update={"responses": result.responses + (foreign.responses[0],)}
        )
    )
    assert validate_openai_provider_execution_result(changed, context)


def test_generic_concrete_mismatch_is_rejected():
    result, context = _generic(False)
    foreign, _ = _generic(True)
    changed = _seal_generic(
        result.model_copy(
            update={"openai_execution_result": foreign.openai_execution_result}
        )
    )
    assert validate_provider_execution_result(changed, context)


class _Hostile:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, **_kwargs):
        raise self.error_type("secret traceback C:\\private 0x7ff")


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize(
    "operation",
    (
        "build-generic-plan",
        "build-generic-context",
        "build-openai-plan",
        "build-openai-context",
        "validate-generic-result",
        "validate-generic-context",
        "validate-openai-result",
        "validate-openai-context",
    ),
)
def test_reconstruction_failures_are_contained(error_type, operation):
    plan, context, outputs, reasons = _authority()
    generic = build_provider_execution_result(plan, outputs, reasons, context)
    hostile = _Hostile(error_type)
    if operation.startswith("build-"):
        builder = (
            build_provider_execution_result
            if "generic" in operation
            else build_openai_provider_execution_result
        )
        args = [plan, outputs, reasons, context]
        args[0 if operation.endswith("plan") else 3] = hostile
        with pytest.raises(DomainValidationError) as caught:
            builder(*args)
        issues = caught.value.issues
    else:
        validator = (
            validate_provider_execution_result
            if "generic" in operation
            else validate_openai_provider_execution_result
        )
        artifact = (
            generic if "generic" in operation else generic.openai_execution_result
        )
        issues = (
            validator(hostile, context)
            if operation.endswith("result")
            else validator(artifact, hostile)
        )
    payload = json.dumps([asdict(issue) for issue in issues], default=str)
    assert issues and all(
        value not in payload for value in ("secret", "traceback", "0x7ff")
    )


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize(
    "operation",
    ("build-generic", "build-openai", "validate-generic", "validate-openai"),
)
def test_process_control_propagates(error_type, operation):
    _, context, outputs, reasons = _authority()
    hostile = _Hostile(error_type)
    with pytest.raises(error_type):
        if operation == "build-generic":
            build_provider_execution_result(hostile, outputs, reasons, context)
        elif operation == "build-openai":
            build_openai_provider_execution_result(hostile, outputs, reasons, context)
        elif operation == "validate-generic":
            validate_provider_execution_result(hostile, context)
        else:
            validate_openai_provider_execution_result(hostile, context)


def test_diagnostics_are_safe_deterministic_and_prior_results_immutable():
    result, context = _openai()
    changed = _seal_openai(
        result.model_copy(
            update={
                "openai_provider_execution_result_reference": (
                    "https://user:secret@example.invalid/x?token=private#traceback"
                )
            }
        )
    )
    first = validate_openai_provider_execution_result(changed, context)
    second = validate_openai_provider_execution_result(changed, context)
    assert first == second and first
    frozen = tuple(asdict(item) for item in first)
    payload = json.dumps(frozen, sort_keys=True, default=str)
    assert all(
        value not in payload
        for value in ("secret", "private", "traceback", "example.invalid")
    )
    assert tuple(asdict(item) for item in first) == frozen


def test_separate_process_artifacts_and_diagnostics_are_equal():
    code = "import runpy,sys,json;sys.path.insert(0,'tests');n=runpy.run_path('tests/test_editorial_script_composer_provider_results.py');p,c=n['_generic']();from dataclasses import asdict;q=p.model_copy(update={'fingerprint':'f'*64});print(json.dumps({'p':p.model_dump(mode='json'),'d':[asdict(x) for x in n['validate_provider_execution_result'](q,c)]},sort_keys=True,separators=(',',':'),ensure_ascii=True))"
    assert subprocess.check_output(
        [sys.executable, "-c", code]
    ) == subprocess.check_output([sys.executable, "-c", code])


def test_public_exports_internal_exclusions_dependency_and_execution_boundary():
    expected = {
        "OpenAIProviderResponseMessage",
        "OpenAIProviderResponse",
        "OpenAIProviderExecutionResult",
        "ProviderExecutionResultValidationContext",
        "ProviderExecutionResult",
        "build_openai_provider_execution_result",
        "validate_openai_provider_execution_result",
        "build_provider_execution_result",
        "validate_provider_execution_result",
        "derive_openai_provider_response_message_identity",
        "derive_openai_provider_response_identity",
        "derive_openai_provider_execution_result_identity",
        "derive_provider_execution_result_identity",
        "derive_openai_provider_response_message_fingerprint",
        "derive_openai_provider_response_fingerprint",
        "derive_openai_provider_execution_result_fingerprint",
        "derive_provider_execution_result_fingerprint",
    }
    assert expected <= set(dir(public_api))
    assert not {"_project_response", "_safe_reference", "_Reconstruction"} & set(
        dir(public_api)
    )
    root = Path("src/pastila_scout/editor/script_composer")
    result_files = tuple(root.glob("*result*.py"))
    forbidden = {
        "openai",
        "httpx",
        "requests",
        "aiohttp",
        "socket",
        "sqlite3",
        "logging",
    }
    for path in result_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(name.split(".")[0] in forbidden for name in imports)
    for path in root.glob("*.py"):
        if path.name == "__init__.py" or "result" in path.name:
            continue
        assert "provider_result" not in path.read_text(encoding="utf-8")
