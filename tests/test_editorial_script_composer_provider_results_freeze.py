"""Freeze-completion regressions for Phase 6.3 independent result authority."""

import importlib
import json
import runpy
import subprocess
import sys
from dataclasses import asdict

import pytest

from pastila_scout.editor.script_composer import (
    DomainValidationError,
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
    validate_openai_extracted_execution_result,
    validate_openai_provider_execution_result,
    validate_provider_execution_result,
)

sys.path.insert(0, "tests")
BASE = runpy.run_path("tests/test_editorial_script_composer_provider_results.py")
MAPPING_EMPTY = runpy.run_path(
    "tests/test_editorial_script_composer_provider_mapping_final_freeze.py"
)


def _source(single=False):
    plan, context, _outputs, _reasons = BASE["_authority"](single)
    return plan, context.extracted_execution_results[0], context


def _seal(value, identity_fn, fingerprint_fn):
    value = value.model_copy(update={"identity": identity_fn(value)})
    return value.model_copy(update={"fingerprint": fingerprint_fn(value)})


def _seal_execution(value):
    return _seal(
        value,
        derive_openai_extracted_execution_result_identity,
        derive_openai_extracted_execution_result_fingerprint,
    )


def _seal_response(value):
    return _seal(
        value,
        derive_openai_extracted_response_identity,
        derive_openai_extracted_response_fingerprint,
    )


def _seal_message(value):
    return _seal(
        value,
        derive_openai_extracted_response_message_identity,
        derive_openai_extracted_response_message_fingerprint,
    )


def _seal_openai_message(value):
    return _seal(
        value,
        derive_openai_provider_response_message_identity,
        derive_openai_provider_response_message_fingerprint,
    )


def _seal_openai_response(value):
    return _seal(
        value,
        derive_openai_provider_response_identity,
        derive_openai_provider_response_fingerprint,
    )


def _seal_openai_result(value):
    return _seal(
        value,
        derive_openai_provider_execution_result_identity,
        derive_openai_provider_execution_result_fingerprint,
    )


def _seal_generic_result(value):
    return _seal(
        value,
        derive_provider_execution_result_identity,
        derive_provider_execution_result_fingerprint,
    )


def _replace_response(authority, response):
    return _seal_execution(
        authority.model_copy(
            update={"responses": (response,) + authority.responses[1:]}
        )
    )


def _replace_message(authority, message):
    response = _seal_response(
        authority.responses[0].model_copy(update={"messages": (message,)})
    )
    return _replace_response(authority, response)


@pytest.mark.parametrize("artifact", ("execution", "response", "message"))
@pytest.mark.parametrize(
    "defect",
    ("stale-identity", "forged-identity", "stale-fingerprint", "forged-fingerprint"),
)
def test_extracted_authority_seal_matrix(artifact, defect):
    plan, authority, context = _source()
    target = {
        "execution": authority,
        "response": authority.responses[0],
        "message": authority.responses[0].messages[0],
    }[artifact]
    if defect == "stale-identity":
        field = "draft_reference"
        changed = target.model_copy(update={field: getattr(target, field) + "-changed"})
        seal_kind = "identity"
    elif defect == "forged-identity":
        changed = target.model_copy(update={"identity": "scout:forged:" + "e" * 64})
        fingerprint_fn = {
            "execution": derive_openai_extracted_execution_result_fingerprint,
            "response": derive_openai_extracted_response_fingerprint,
            "message": derive_openai_extracted_response_message_fingerprint,
        }[artifact]
        changed = changed.model_copy(update={"fingerprint": fingerprint_fn(changed)})
        seal_kind = "identity"
    else:
        changed = target.model_copy(
            update={"fingerprint": ("e" if defect == "stale-fingerprint" else "f") * 64}
        )
        seal_kind = "fingerprint"
    if artifact == "response":
        changed_authority = _replace_response(authority, changed)
    elif artifact == "message":
        changed_authority = _replace_message(authority, changed)
    else:
        changed_authority = changed
    codes = {
        item.code
        for item in validate_openai_extracted_execution_result(
            changed_authority, plan, context.provider_mapping_validation_context
        )
    }
    assert f"extracted-result-invalid-{artifact}-{seal_kind}" in codes


REFERENCE_VALUES = (
    "wrong",
    "valid-looking:wrong",
    "stale:reference",
    "foreign-valid:" + "e" * 64,
    "other-provider-plan:" + "f" * 64,
    "other-openai-plan:" + "e" * 64,
    "other-request:" + "f" * 64,
    "other-response:" + "e" * 64,
    "CASE-MUTATION",
    " leading",
    "trailing ",
    "tab\tvalue",
    "line\nvalue",
    "nbsp\u00a0value",
    "zero\u200bwidth",
    "h\u043emoglyph",
    "https://example.invalid/value",
    "https://user:pass@example.invalid/value",
    "https://example.invalid/value?token=secret",
    "https://example.invalid/value#fragment",
    "C:\\private\\value",
    "/private/value",
    "first\nsecond",
    "x" * 201,
    "object:0x7ffdeadbeef",
)


@pytest.mark.parametrize("artifact", ("execution", "response", "message"))
@pytest.mark.parametrize("replacement", REFERENCE_VALUES)
def test_extracted_canonical_reference_attack_matrix(artifact, replacement):
    plan, authority, context = _source()
    field = {
        "execution": "extracted_execution_result_reference",
        "response": "extracted_response_reference",
        "message": "extracted_response_message_reference",
    }[artifact]
    target = {
        "execution": authority,
        "response": authority.responses[0],
        "message": authority.responses[0].messages[0],
    }[artifact]
    changed = target.model_copy(update={field: replacement})
    changed = {
        "execution": _seal_execution,
        "response": _seal_response,
        "message": _seal_message,
    }[artifact](changed)
    if artifact == "response":
        changed = _replace_response(authority, changed)
    elif artifact == "message":
        changed = _replace_message(authority, changed)
    issues = validate_openai_extracted_execution_result(
        changed, plan, context.provider_mapping_validation_context
    )
    expected = (
        "extracted-result-invalid-reconstruction"
        if replacement
        in {
            " leading",
            "trailing ",
            "tab\tvalue",
            "line\nvalue",
            "nbsp\u00a0value",
            "first\nsecond",
            "x" * 201,
        }
        else f"extracted-result-{artifact}-{field.replace('_', '-')}-mismatch"
    )
    assert expected in {item.code for item in issues}


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "extracted_response_reference",
            "extracted-result-duplicate-extracted-response-reference",
        ),
        ("identity", "extracted-result-duplicate-identity"),
        (
            "openai_request_reference",
            "extracted-result-duplicate-openai-request-reference",
        ),
        (
            "openai_request_identity",
            "extracted-result-duplicate-openai-request-identity",
        ),
        ("response_ordinal", "extracted-result-duplicate-response-ordinal"),
    ),
)
def test_extracted_response_duplicate_dimensions(field, code):
    plan, authority, context = _source()
    first, second = authority.responses[:2]
    changed = second.model_copy(update={field: getattr(first, field)})
    if field == "identity":
        changed = changed.model_copy(
            update={
                "fingerprint": derive_openai_extracted_response_fingerprint(changed)
            }
        )
    else:
        changed = _seal_response(changed)
    value = _seal_execution(
        authority.model_copy(
            update={"responses": (first, changed) + authority.responses[2:]}
        )
    )
    issues = validate_openai_extracted_execution_result(
        value, plan, context.provider_mapping_validation_context
    )
    assert code in {item.code for item in issues}


def test_extracted_repeated_message_reports_every_collapsed_duplicate_dimension():
    plan, authority, context = _source()
    response = authority.responses[0]
    response = _seal_response(
        response.model_copy(update={"messages": response.messages * 2})
    )
    value = _replace_response(authority, response)
    codes = {
        item.code
        for item in validate_openai_extracted_execution_result(
            value, plan, context.provider_mapping_validation_context
        )
    }
    expected_fields = {
        "extracted-response-message-reference",
        "identity",
        "extracted-response-reference",
        "openai-request-reference",
        "openai-request-identity",
        "ordinal",
    }
    assert {f"extracted-result-duplicate-{field}" for field in expected_fields} <= codes


@pytest.mark.parametrize(
    ("argument", "code"),
    (
        ("plan", "provider-result-invalid-provider-request-plan-input"),
        ("authority", "provider-result-invalid-extracted-authority-input"),
        ("context", "provider-result-invalid-validation-context-input"),
    ),
)
@pytest.mark.parametrize(
    "builder", (build_openai_provider_execution_result, build_provider_execution_result)
)
def test_preferred_builder_reconstruction_is_bounded(builder, argument, code):
    plan, authority, context = _source()
    values = {"plan": plan, "authority": authority, "context": context}
    values[argument] = object()
    with pytest.raises(DomainValidationError) as caught:
        builder(values["plan"], values["authority"], values["context"])
    assert tuple(item.code for item in caught.value.issues) == (code,)


class _ProcessControl:
    def __init__(self, error):
        self.error = error

    def model_dump(self, **_kwargs):
        raise self.error


@pytest.mark.parametrize("error", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize(
    "builder", (build_openai_provider_execution_result, build_provider_execution_result)
)
def test_preferred_builder_process_control_propagates(builder, error):
    _, authority, context = _source()
    with pytest.raises(error):
        builder(_ProcessControl(error), authority, context)


@pytest.mark.parametrize(
    "builder", (build_openai_provider_execution_result, build_provider_execution_result)
)
def test_unsupported_builder_signatures_are_bounded(builder):
    with pytest.raises(DomainValidationError) as missing:
        builder()
    assert tuple(item.code for item in missing.value.issues) == (
        "provider-result-unsupported-builder-signature",
    )
    plan, authority, context = _source()
    with pytest.raises(DomainValidationError) as extra:
        builder(plan, authority, context, None, "extra")
    assert tuple(item.code for item in extra.value.issues) == (
        "provider-result-unsupported-builder-signature",
    )


@pytest.mark.parametrize(
    "error", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize("argument", ("plan", "authority", "context"))
@pytest.mark.parametrize(
    "builder", (build_openai_provider_execution_result, build_provider_execution_result)
)
def test_preferred_builder_ordinary_reconstruction_failures_are_bounded(
    builder, argument, error
):
    plan, authority, context = _source()
    values = {"plan": plan, "authority": authority, "context": context}
    values[argument] = _ProcessControl(error)
    expected = {
        "plan": "provider-result-invalid-provider-request-plan-input",
        "authority": "provider-result-invalid-extracted-authority-input",
        "context": "provider-result-invalid-validation-context-input",
    }[argument]
    with pytest.raises(DomainValidationError) as caught:
        builder(values["plan"], values["authority"], values["context"])
    assert tuple(item.code for item in caught.value.issues) == (expected,)
    assert "ProcessControl" not in str(caught.value.issues)


def _empty_source(purpose):
    plan, mapping_context = MAPPING_EMPTY["_empty_generic"](purpose=purpose)
    authority = build_openai_extracted_execution_result(plan, (), (), mapping_context)
    context = ProviderExecutionResultValidationContext(
        provider_request_plans=(plan,),
        provider_mapping_validation_context=mapping_context,
        extracted_execution_results=(authority,),
    )
    openai = build_openai_provider_execution_result(plan, authority, context)
    generic = build_provider_execution_result(plan, authority, context)
    return plan, authority, context, openai, generic


def test_canonical_empty_result_is_fresh_equal_and_tuple_based():
    first = _empty_source("empty-authority")
    second = _empty_source("empty-authority")
    assert first[1:] == second[1:]
    assert first[1] is not second[1]
    assert (
        first[1].responses
        == first[3].responses
        == first[4].openai_execution_result.responses
        == ()
    )
    assert validate_openai_provider_execution_result(first[3], first[2]) == ()
    assert validate_provider_execution_result(first[4], first[2]) == ()


def test_true_foreign_empty_lineage_is_contextually_rejected():
    local = _empty_source("local-empty-authority")
    foreign = _empty_source("foreign-empty-authority")
    assert local[0].identity != foreign[0].identity
    assert local[1].identity != foreign[1].identity
    assert validate_openai_extracted_execution_result(
        foreign[1], local[0], local[2].provider_mapping_validation_context
    )
    assert validate_openai_provider_execution_result(foreign[3], local[2])
    assert validate_provider_execution_result(foreign[4], local[2])
    assert validate_provider_execution_result(local[4], foreign[2])


@pytest.mark.parametrize("artifact", ("extracted", "openai", "generic"))
@pytest.mark.parametrize(
    "defect",
    ("stale-identity", "forged-identity", "stale-fingerprint", "forged-fingerprint"),
)
def test_empty_result_seal_matrix(artifact, defect):
    plan, extracted, context, openai, generic = _empty_source("empty-seal-authority")
    value = {"extracted": extracted, "openai": openai, "generic": generic}[artifact]
    if defect == "stale-identity":
        value = value.model_copy(
            update={"draft_reference": value.draft_reference + "-changed"}
        )
        expected = f"{'extracted-result-invalid-execution' if artifact == 'extracted' else 'provider-result-invalid-' + ('openai-result' if artifact == 'openai' else 'generic-result')}-identity"
    elif defect == "forged-identity":
        value = value.model_copy(update={"identity": "scout:forged:" + "e" * 64})
        expected = f"{'extracted-result-invalid-execution' if artifact == 'extracted' else 'provider-result-invalid-' + ('openai-result' if artifact == 'openai' else 'generic-result')}-identity"
    else:
        value = value.model_copy(
            update={"fingerprint": ("e" if defect == "stale-fingerprint" else "f") * 64}
        )
        expected = f"{'extracted-result-invalid-execution' if artifact == 'extracted' else 'provider-result-invalid-' + ('openai-result' if artifact == 'openai' else 'generic-result')}-fingerprint"
    if artifact == "extracted":
        issues = validate_openai_extracted_execution_result(
            value, plan, context.provider_mapping_validation_context
        )
    elif artifact == "openai":
        issues = validate_openai_provider_execution_result(value, context)
    else:
        issues = validate_provider_execution_result(value, context)
    assert expected in {item.code for item in issues}


def test_all_phase_63_artifacts_are_equal_across_processes():
    code = (
        "import runpy,sys,json;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_freeze.py');"
        "p,a,c=n['_source']();"
        "o=n['build_openai_provider_execution_result'](p,a,c);"
        "g=n['build_provider_execution_result'](p,a,c);"
        "bad=a.model_copy(update={'fingerprint':'f'*64});"
        "d=n['validate_openai_extracted_execution_result'](bad,p,c.provider_mapping_validation_context);"
        "from dataclasses import asdict;"
        "items=(a,a.responses[0],a.responses[0].messages[0],g,o,o.responses[0],o.responses[0].messages[0]);"
        "print(json.dumps({'artifacts':[x.model_dump(mode='json') if hasattr(x,'model_dump') else x for x in items],"
        "'diagnostics':[asdict(x) for x in d]},sort_keys=True,separators=(',',':'),ensure_ascii=True))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert json.loads(first) == json.loads(second)


def test_exact_phase_63_public_api_is_frozen_at_28_symbols():
    modules = (
        "extracted_result_models",
        "extracted_result_identity",
        "extracted_result_validation",
        "openai_result_models",
        "openai_result_identity",
        "openai_result_validation",
        "provider_result_models",
        "provider_result_identity",
        "provider_result_validation",
    )
    actual = set()
    for name in modules:
        module = importlib.import_module(f"pastila_scout.editor.script_composer.{name}")
        actual.update(module.__all__)
    expected = {
        "OpenAIExtractedExecutionResult",
        "OpenAIExtractedResponse",
        "OpenAIExtractedResponseMessage",
        "OpenAIProviderExecutionResult",
        "OpenAIProviderResponse",
        "OpenAIProviderResponseMessage",
        "ProviderExecutionResult",
        "ProviderExecutionResultValidationContext",
        "build_openai_extracted_execution_result",
        "build_openai_provider_execution_result",
        "build_provider_execution_result",
        "validate_openai_extracted_execution_result",
        "validate_openai_provider_execution_result",
        "validate_provider_execution_result",
        "derive_openai_extracted_execution_result_identity",
        "derive_openai_extracted_response_identity",
        "derive_openai_extracted_response_message_identity",
        "derive_openai_provider_execution_result_identity",
        "derive_openai_provider_response_identity",
        "derive_openai_provider_response_message_identity",
        "derive_provider_execution_result_identity",
        "derive_openai_extracted_execution_result_fingerprint",
        "derive_openai_extracted_response_fingerprint",
        "derive_openai_extracted_response_message_fingerprint",
        "derive_openai_provider_execution_result_fingerprint",
        "derive_openai_provider_response_fingerprint",
        "derive_openai_provider_response_message_fingerprint",
        "derive_provider_execution_result_fingerprint",
    }
    assert actual == expected
    assert len(actual) == 28
    assert not any(name.startswith("_") for name in actual)


class _NoModelDump:
    pass


class _HostileModelDumpProperty:
    @property
    def model_dump(self):
        raise AttributeError("secret token C:\\private 0x7ff")


class _FailingModelDump:
    def __init__(self, error):
        self.error = error

    def model_dump(self, **_kwargs):
        raise self.error("secret token C:\\private 0x7ff")


class _ReturningModelDump:
    def __init__(self, value):
        self.value = value

    def model_dump(self, **_kwargs):
        return self.value


MALFORMED_RECONSTRUCTION_INPUTS = (
    _NoModelDump(),
    _HostileModelDumpProperty(),
    *(
        _FailingModelDump(error)
        for error in (
            AttributeError,
            TypeError,
            ValueError,
            KeyError,
            LookupError,
            RuntimeError,
        )
    ),
    _ReturningModelDump(None),
    _ReturningModelDump("placeholder"),
    _ReturningModelDump({"hostile": "https://x.invalid/?token=secret#fragment"}),
    _ReturningModelDump({"responses": [{"messages": [object()]}]}),
    _ReturningModelDump([]),
)


def _assert_safe_deterministic(issues, expected_code):
    repeated = tuple(issues)
    assert tuple(item.code for item in repeated) == (expected_code,)
    assert repeated == tuple(issues)
    serialized = json.dumps(
        [asdict(item) for item in repeated], sort_keys=True, ensure_ascii=True
    )
    assert repeated[0].field_reference is None
    assert repeated[0].field_path == ()
    assert repeated[0].artifact_reference in {
        "extracted-result-authority",
        "provider-result-artifact",
    }
    for unsafe in ("secret", "token=", "C:\\private", "0x7ff", "Traceback"):
        assert unsafe not in serialized
        assert unsafe not in str(repeated)
        assert unsafe not in repr(repeated)


@pytest.mark.parametrize("malformed", MALFORMED_RECONSTRUCTION_INPUTS)
@pytest.mark.parametrize("position", ("authority", "plan", "context"))
def test_extracted_validator_contains_every_ordinary_malformed_input(
    malformed, position
):
    plan, authority, context = _source()
    values = {
        "authority": authority,
        "plan": plan,
        "context": context.provider_mapping_validation_context,
    }
    values[position] = malformed
    first = validate_openai_extracted_execution_result(
        values["authority"], values["plan"], values["context"]
    )
    second = validate_openai_extracted_execution_result(
        values["authority"], values["plan"], values["context"]
    )
    assert first == second and first is not second
    _assert_safe_deterministic(first, "extracted-result-invalid-reconstruction")


@pytest.mark.parametrize("malformed", MALFORMED_RECONSTRUCTION_INPUTS)
@pytest.mark.parametrize(
    ("validator", "position", "expected"),
    (
        (
            validate_openai_provider_execution_result,
            "result",
            "provider-result-invalid-openai-result",
        ),
        (
            validate_openai_provider_execution_result,
            "context",
            "provider-result-invalid-context",
        ),
        (
            validate_provider_execution_result,
            "result",
            "provider-result-invalid-generic-result",
        ),
        (
            validate_provider_execution_result,
            "context",
            "provider-result-invalid-context",
        ),
    ),
)
def test_submitted_validators_contain_every_ordinary_malformed_input(
    malformed, validator, position, expected
):
    plan, authority, context = _source()
    result = (
        build_openai_provider_execution_result(plan, authority, context)
        if validator is validate_openai_provider_execution_result
        else build_provider_execution_result(plan, authority, context)
    )
    values = {"result": result, "context": context}
    values[position] = malformed
    first = validator(values["result"], values["context"])
    second = validator(values["result"], values["context"])
    assert first == second and first is not second
    _assert_safe_deterministic(first, expected)


@pytest.mark.parametrize("error", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize("position", ("authority", "plan", "context"))
def test_extracted_validator_process_control_propagates_at_each_boundary(
    error, position
):
    plan, authority, context = _source()
    values = {
        "authority": authority,
        "plan": plan,
        "context": context.provider_mapping_validation_context,
    }
    values[position] = _FailingModelDump(error)
    with pytest.raises(error):
        validate_openai_extracted_execution_result(
            values["authority"], values["plan"], values["context"]
        )


@pytest.mark.parametrize("error", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize(
    ("validator", "position"),
    (
        (validate_openai_provider_execution_result, "result"),
        (validate_openai_provider_execution_result, "context"),
        (validate_provider_execution_result, "result"),
        (validate_provider_execution_result, "context"),
    ),
)
def test_submitted_validator_process_control_propagates_at_each_boundary(
    error, validator, position
):
    plan, authority, context = _source()
    result = (
        build_openai_provider_execution_result(plan, authority, context)
        if validator is validate_openai_provider_execution_result
        else build_provider_execution_result(plan, authority, context)
    )
    values = {"result": result, "context": context}
    values[position] = _FailingModelDump(error)
    with pytest.raises(error):
        validator(values["result"], values["context"])


def _submitted_source(single=False):
    plan, authority, context = _source(single)
    openai = build_openai_provider_execution_result(plan, authority, context)
    generic = build_provider_execution_result(plan, authority, context)
    return plan, authority, context, openai, generic


@pytest.mark.parametrize(
    ("artifact", "field", "foreign_level"),
    (
        ("execution", "extracted_execution_result_reference", "execution"),
        ("execution", "provider_request_plan_reference", "execution"),
        ("execution", "openai_request_plan_reference", "execution"),
        ("execution", "execution_plan_reference", "execution"),
        ("execution", "draft_reference", "execution"),
        ("response", "extracted_response_reference", "response"),
        ("response", "provider_request_plan_reference", "response"),
        ("response", "openai_request_plan_reference", "response"),
        ("response", "openai_request_reference", "response"),
        ("response", "execution_request_reference", "response"),
        ("response", "execution_plan_reference", "response"),
        ("response", "draft_reference", "response"),
        ("message", "extracted_response_message_reference", "message"),
        ("message", "extracted_response_reference", "message"),
        ("message", "provider_request_plan_reference", "message"),
        ("message", "openai_request_plan_reference", "message"),
        ("message", "openai_request_reference", "message"),
        ("message", "execution_request_reference", "message"),
        ("message", "execution_plan_reference", "message"),
        ("message", "draft_reference", "message"),
    ),
)
def test_genuine_foreign_valid_extracted_reference_matrix(
    artifact, field, foreign_level
):
    plan, local, context = _source()
    _, foreign, foreign_context = _source(True)
    assert (
        validate_openai_extracted_execution_result(
            foreign,
            foreign_context.provider_request_plans[0],
            foreign_context.provider_mapping_validation_context,
        )
        == ()
    )
    target = {
        "execution": local,
        "response": local.responses[0],
        "message": local.responses[0].messages[0],
    }[artifact]
    foreign_target = {
        "execution": foreign,
        "response": foreign.responses[0],
        "message": foreign.responses[0].messages[0],
    }[foreign_level]
    changed = target.model_copy(update={field: getattr(foreign_target, field)})
    if artifact == "execution":
        changed = _seal_execution(changed)
    elif artifact == "response":
        changed = _replace_response(local, _seal_response(changed))
    else:
        changed = _replace_message(local, _seal_message(changed))
    issues = validate_openai_extracted_execution_result(
        changed, plan, context.provider_mapping_validation_context
    )
    assert f"extracted-result-{artifact}-{field.replace('_', '-')}-mismatch" in {
        item.code for item in issues
    }


@pytest.mark.parametrize(
    ("artifact", "field"),
    (
        ("generic", "provider_request_plan_reference"),
        ("generic", "execution_plan_reference"),
        ("generic", "draft_reference"),
        ("generic", "provider_result_reference"),
        ("openai", "provider_request_plan_reference"),
        ("openai", "openai_request_plan_reference"),
        ("openai", "execution_plan_reference"),
        ("openai", "draft_reference"),
        ("openai", "openai_provider_execution_result_reference"),
        ("response", "provider_request_plan_reference"),
        ("response", "openai_request_plan_reference"),
        ("response", "openai_request_reference"),
        ("response", "execution_request_reference"),
        ("response", "execution_plan_reference"),
        ("response", "draft_reference"),
        ("response", "provider_response_reference"),
        ("message", "provider_response_reference"),
        ("message", "provider_request_plan_reference"),
        ("message", "openai_request_plan_reference"),
        ("message", "openai_request_reference"),
        ("message", "execution_request_reference"),
        ("message", "execution_plan_reference"),
        ("message", "draft_reference"),
        ("message", "provider_response_message_reference"),
    ),
)
def test_genuine_foreign_valid_submitted_reference_matrix(artifact, field):
    _, _, context, openai, generic = _submitted_source()
    _, _, foreign_context, foreign_openai, foreign_generic = _submitted_source(True)
    assert (
        validate_openai_provider_execution_result(foreign_openai, foreign_context) == ()
    )
    foreign_targets = {
        "generic": foreign_generic,
        "openai": foreign_openai,
        "response": foreign_openai.responses[0],
        "message": foreign_openai.responses[0].messages[0],
    }
    target = {
        "generic": generic,
        "openai": openai,
        "response": openai.responses[0],
        "message": openai.responses[0].messages[0],
    }[artifact]
    changed = target.model_copy(
        update={field: getattr(foreign_targets[artifact], field)}
    )
    if artifact == "generic":
        changed = _seal_generic_result(changed)
        issues = validate_provider_execution_result(changed, context)
        prefix = "provider-result-generic-"
    else:
        if artifact == "openai":
            changed = _seal_openai_result(changed)
        elif artifact == "response":
            response = _seal_openai_response(changed)
            changed = _seal_openai_result(
                openai.model_copy(
                    update={"responses": (response,) + openai.responses[1:]}
                )
            )
        else:
            message = _seal_openai_message(changed)
            response = _seal_openai_response(
                openai.responses[0].model_copy(update={"messages": (message,)})
            )
            changed = _seal_openai_result(
                openai.model_copy(
                    update={"responses": (response,) + openai.responses[1:]}
                )
            )
        issues = validate_openai_provider_execution_result(changed, context)
        prefix = f"provider-result-{'openai' if artifact == 'openai' else artifact}-"
    expected = (
        "provider-result-unknown-provider-request-plan"
        if field == "provider_request_plan_reference"
        and artifact in {"generic", "openai"}
        else f"{prefix}{field.replace('_', '-')}-mismatch"
    )
    assert expected in {item.code for item in issues}


@pytest.mark.parametrize("artifact", ("generic", "openai", "response", "message"))
@pytest.mark.parametrize(
    "defect",
    ("stale-identity", "forged-identity", "stale-fingerprint", "forged-fingerprint"),
)
def test_complete_nonempty_submitted_seal_matrix(artifact, defect):
    _, _, context, openai, generic = _submitted_source()
    target = {
        "generic": generic,
        "openai": openai,
        "response": openai.responses[0],
        "message": openai.responses[0].messages[0],
    }[artifact]
    identity_fn, fingerprint_fn = {
        "generic": (
            derive_provider_execution_result_identity,
            derive_provider_execution_result_fingerprint,
        ),
        "openai": (
            derive_openai_provider_execution_result_identity,
            derive_openai_provider_execution_result_fingerprint,
        ),
        "response": (
            derive_openai_provider_response_identity,
            derive_openai_provider_response_fingerprint,
        ),
        "message": (
            derive_openai_provider_response_message_identity,
            derive_openai_provider_response_message_fingerprint,
        ),
    }[artifact]
    if defect == "stale-identity":
        changed = target.model_copy(
            update={"draft_reference": target.draft_reference + "-changed"}
        )
        changed = changed.model_copy(update={"fingerprint": fingerprint_fn(changed)})
        expected_kind = "identity"
    elif defect == "forged-identity":
        changed = target.model_copy(update={"identity": "scout:forged:" + "e" * 64})
        changed = changed.model_copy(update={"fingerprint": fingerprint_fn(changed)})
        expected_kind = "identity"
    elif defect == "stale-fingerprint":
        changed = target.model_copy(
            update={"draft_reference": target.draft_reference + "-changed"}
        )
        changed = changed.model_copy(update={"identity": identity_fn(changed)})
        expected_kind = "fingerprint"
    else:
        changed = target.model_copy(update={"fingerprint": "f" * 64})
        expected_kind = "fingerprint"
    if artifact == "generic":
        result = changed
        issues = validate_provider_execution_result(result, context)
        kind = "generic-result"
    else:
        if artifact == "openai":
            result = changed
        elif artifact == "response":
            result = _seal_openai_result(
                openai.model_copy(
                    update={"responses": (changed,) + openai.responses[1:]}
                )
            )
        else:
            response = _seal_openai_response(
                openai.responses[0].model_copy(update={"messages": (changed,)})
            )
            result = _seal_openai_result(
                openai.model_copy(
                    update={"responses": (response,) + openai.responses[1:]}
                )
            )
        issues = validate_openai_provider_execution_result(result, context)
        kind = "openai-result" if artifact == "openai" else artifact
    assert f"provider-result-invalid-{kind}-{expected_kind}" in {
        item.code for item in issues
    }
