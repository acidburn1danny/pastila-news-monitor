"""Final freeze-grade coverage for Phase 6.3 provider result contracts."""

import json
import runpy
import subprocess
import sys
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import (
    OpenAIExtractedExecutionResult,
    OpenAIProviderExecutionResult,
    validate_openai_extracted_execution_result,
    validate_openai_provider_execution_result,
    validate_provider_execution_result,
)

sys.path.insert(0, "tests")
FREEZE = runpy.run_path(
    "tests/test_editorial_script_composer_provider_results_freeze.py"
)


def _empty(purpose="final-empty"):
    return FREEZE["_empty_source"](purpose)


def _nonempty(single=True):
    return FREEZE["_submitted_source"](single)


def _dump(issues):
    return json.dumps(
        [asdict(issue) for issue in issues],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _assert_exact(issues, code, reference):
    assert tuple(issue.code for issue in issues) == (code,)
    issue = issues[0]
    assert issue.artifact_reference == reference
    assert issue.field_reference is None
    assert issue.field_path == ()
    assert issue.related_references == ()
    assert issue.message_key == code


def test_valid_empty_phase_62_provider_request_plan():
    plan, *_ = _empty()
    assert plan.openai_request_plan.requests == ()


def test_valid_empty_openai_request_plan():
    plan, *_ = _empty()
    assert plan.openai_request_plan.requests == ()


def test_valid_empty_extracted_execution_result():
    _, extracted, *_ = _empty()
    assert extracted.responses == ()


def test_valid_empty_submitted_openai_execution_result():
    *_, openai, _ = _empty()
    assert openai.responses == ()


def test_valid_empty_generic_provider_result():
    *_, generic = _empty()
    assert generic.openai_execution_result.responses == ()


def test_valid_empty_validation_context():
    plan, extracted, context, *_ = _empty()
    assert context.provider_request_plans == (plan,)
    assert context.extracted_execution_results == (extracted,)


def test_locally_valid_empty_extracted_authority():
    plan, extracted, context, *_ = _empty()
    assert (
        validate_openai_extracted_execution_result(
            extracted, plan, context.provider_mapping_validation_context
        )
        == ()
    )


def test_locally_valid_empty_submitted_openai_result():
    *_, context, openai, _ = _empty()
    assert validate_openai_provider_execution_result(openai, context) == ()


def test_locally_valid_empty_generic_result():
    *_, context, _, generic = _empty()
    assert validate_provider_execution_result(generic, context) == ()


def test_independently_valid_foreign_empty_extracted_authority():
    plan, extracted, context, *_ = _empty("foreign-valid-extracted")
    assert (
        validate_openai_extracted_execution_result(
            extracted, plan, context.provider_mapping_validation_context
        )
        == ()
    )


def test_independently_valid_foreign_empty_submitted_openai_result():
    *_, context, openai, _ = _empty("foreign-valid-openai")
    assert validate_openai_provider_execution_result(openai, context) == ()


def test_independently_valid_foreign_empty_generic_result():
    *_, context, _, generic = _empty("foreign-valid-generic")
    assert validate_provider_execution_result(generic, context) == ()


def test_equal_empty_artifacts_from_equal_authority():
    first = _empty("equal-empty")
    second = _empty("equal-empty")
    assert first[1:] == second[1:]


def test_equal_empty_artifacts_are_distinct_instances():
    first = _empty("distinct-empty")
    second = _empty("distinct-empty")
    assert first[1] == second[1] and first[1] is not second[1]
    assert first[3] == second[3] and first[3] is not second[3]
    assert first[4] == second[4] and first[4] is not second[4]


def test_fresh_empty_builder_output_on_repeated_calls():
    first = _empty("fresh-empty")
    second = _empty("fresh-empty")
    assert first[1:] == second[1:]
    assert all(left is not right for left, right in zip(first[1:], second[1:]))


def test_empty_result_round_trip_reconstruction():
    _, extracted, context, openai, generic = _empty("round-trip-empty")
    assert type(extracted).model_validate(extracted.model_dump()) == extracted
    assert type(openai).model_validate(openai.model_dump()) == openai
    assert type(generic).model_validate(generic.model_dump()) == generic
    assert type(context).model_validate(context.model_dump()) == context


def test_empty_result_validation_success():
    plan, extracted, context, openai, generic = _empty("validation-empty")
    assert (
        validate_openai_extracted_execution_result(
            extracted, plan, context.provider_mapping_validation_context
        )
        == validate_openai_provider_execution_result(openai, context)
        == validate_provider_execution_result(generic, context)
        == ()
    )


def test_deterministic_empty_identity():
    first, second = _empty("identity-empty"), _empty("identity-empty")
    assert tuple(item.identity for item in (first[1], first[3], first[4])) == tuple(
        item.identity for item in (second[1], second[3], second[4])
    )


def test_deterministic_empty_fingerprint():
    first, second = _empty("fingerprint-empty"), _empty("fingerprint-empty")
    assert tuple(item.fingerprint for item in (first[1], first[3], first[4])) == tuple(
        item.fingerprint for item in (second[1], second[3], second[4])
    )


def test_deterministic_empty_canonical_reference():
    first, second = _empty("reference-empty"), _empty("reference-empty")
    assert (
        first[1].extracted_execution_result_reference
        == second[1].extracted_execution_result_reference
    )
    assert (
        first[3].openai_provider_execution_result_reference
        == second[3].openai_provider_execution_result_reference
    )
    assert (
        first[4].provider_execution_result_reference
        == second[4].provider_execution_result_reference
    )


@pytest.mark.parametrize(
    ("value", "accepted"),
    (
        (None, False),
        ({}, False),
        (set(), True),
        ("", False),
        (1, False),
        ([], True),
        ((None,), False),
        (({},), False),
        (("placeholder",), False),
    ),
    ids=(
        "none",
        "empty-dict",
        "empty-set-canonicalized",
        "empty-string",
        "integer",
        "mutable-list-canonicalized",
        "tuple-none",
        "tuple-dict",
        "tuple-scalar",
    ),
)
@pytest.mark.parametrize("artifact", ("extracted", "openai"))
def test_empty_response_container_public_reconstruction_is_deterministic(
    value, accepted, artifact
):
    plan, extracted, context, openai, _ = _empty("container-empty")
    target = extracted if artifact == "extracted" else openai
    changed = target.model_copy(update={"responses": value})
    issues = (
        validate_openai_extracted_execution_result(
            changed, plan, context.provider_mapping_validation_context
        )
        if artifact == "extracted"
        else validate_openai_provider_execution_result(changed, context)
    )
    if accepted:
        assert issues == ()
    else:
        _assert_exact(
            issues,
            (
                "extracted-result-invalid-reconstruction"
                if artifact == "extracted"
                else "provider-result-invalid-openai-result"
            ),
            (
                "extracted-result-authority"
                if artifact == "extracted"
                else "provider-result-artifact"
            ),
        )


def test_mutable_empty_list_is_canonicalized_at_model_construction():
    _, extracted, _, openai, _ = _empty("strict-list-empty")
    assert (
        OpenAIExtractedExecutionResult.model_validate(
            {**extracted.model_dump(), "responses": []}
        ).responses
        == ()
    )
    assert (
        OpenAIProviderExecutionResult.model_validate(
            {**openai.model_dump(), "responses": []}
        ).responses
        == ()
    )


@pytest.mark.parametrize("model_name", ("extracted", "openai", "generic"))
def test_extra_caller_controlled_empty_metadata_is_rejected(model_name):
    _, extracted, _, openai, generic = _empty("extra-empty")
    model = {"extracted": extracted, "openai": openai, "generic": generic}[model_name]
    with pytest.raises(ValidationError):
        type(model).model_validate({**model.model_dump(), "metadata": {}})


def test_empty_request_plan_rejects_nonempty_extracted_authority():
    empty = _empty("empty-request-nonempty-extracted")
    nonempty = _nonempty(True)
    issues = validate_openai_extracted_execution_result(
        nonempty[1], empty[0], empty[2].provider_mapping_validation_context
    )
    assert tuple(item.code for item in issues) == (
        "extracted-result-output-count-mismatch",
    )


def test_nonempty_request_plan_rejects_empty_extracted_authority():
    empty = _empty("nonempty-request-empty-extracted")
    nonempty = _nonempty(True)
    issues = validate_openai_extracted_execution_result(
        empty[1], nonempty[0], nonempty[2].provider_mapping_validation_context
    )
    assert tuple(item.code for item in issues) == (
        "extracted-result-output-count-mismatch",
    )


def test_empty_extracted_context_rejects_nonempty_openai_result():
    empty = _empty("empty-extracted-nonempty-openai")
    nonempty = _nonempty(True)
    issues = validate_openai_provider_execution_result(nonempty[3], empty[2])
    assert tuple(item.code for item in issues) == (
        "provider-result-unknown-provider-request-plan",
    )


def test_nonempty_extracted_context_rejects_empty_openai_result():
    empty = _empty("nonempty-extracted-empty-openai")
    nonempty = _nonempty(True)
    issues = validate_openai_provider_execution_result(empty[3], nonempty[2])
    assert tuple(item.code for item in issues) == (
        "provider-result-unknown-provider-request-plan",
    )


def test_empty_generic_context_rejects_nonempty_concrete_result():
    empty = _empty("empty-generic-nonempty-concrete")
    nonempty = _nonempty(True)
    changed = empty[4].model_copy(update={"openai_execution_result": nonempty[3]})
    changed = FREEZE["_seal_generic_result"](changed)
    issues = validate_provider_execution_result(changed, empty[2])
    assert tuple(item.code for item in issues) == (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-unknown-provider-request-plan",
    )


def test_nonempty_generic_context_rejects_empty_concrete_result():
    empty = _empty("nonempty-generic-empty-concrete")
    nonempty = _nonempty(True)
    changed = nonempty[4].model_copy(update={"openai_execution_result": empty[3]})
    changed = FREEZE["_seal_generic_result"](changed)
    issues = validate_provider_execution_result(changed, nonempty[2])
    assert tuple(item.code for item in issues) == (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-unknown-provider-request-plan",
    )


RESPONSE_FIELDS = tuple(
    field
    for field in FREEZE["_source"]()[1].responses[0].__class__.model_fields
    if field != "messages"
)
MESSAGE_FIELDS = tuple(
    FREEZE["_source"]()[1].responses[0].messages[0].__class__.model_fields
)


def _malformed_nested(field, level):
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    if level == "response":
        payload["responses"][0][field] = None
    else:
        payload["responses"][0]["messages"][0][field] = None
    holder = FREEZE["_ReturningModelDump"](payload)
    issues = validate_openai_extracted_execution_result(
        holder, plan, context.provider_mapping_validation_context
    )
    _assert_exact(
        issues,
        "extracted-result-invalid-reconstruction",
        "extracted-result-authority",
    )


@pytest.mark.parametrize("field", RESPONSE_FIELDS)
def test_each_malformed_extracted_response_field_is_bounded(field):
    _malformed_nested(field, "response")


@pytest.mark.parametrize("field", MESSAGE_FIELDS)
def test_each_malformed_extracted_message_field_is_bounded(field):
    _malformed_nested(field, "message")


@pytest.mark.parametrize(
    "responses",
    (None, {}, "scalar", (None,), ({},)),
    ids=("none", "mapping", "scalar", "malformed-child", "mapping-child"),
)
def test_each_malformed_extracted_responses_shape_is_bounded(responses):
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    payload["responses"] = responses
    issues = validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )
    _assert_exact(
        issues,
        "extracted-result-invalid-reconstruction",
        "extracted-result-authority",
    )


@pytest.mark.parametrize(
    "messages",
    (None, {}, "scalar", (None,), ({},)),
    ids=("none", "mapping", "scalar", "malformed-child", "mapping-child"),
)
def test_each_malformed_extracted_messages_shape_is_bounded(messages):
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    payload["responses"][0]["messages"] = messages
    issues = validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )
    _assert_exact(
        issues,
        "extracted-result-invalid-reconstruction",
        "extracted-result-authority",
    )


def test_extracted_response_missing_messages_is_bounded():
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    del payload["responses"][0]["messages"]
    issues = validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )
    _assert_exact(
        issues, "extracted-result-invalid-reconstruction", "extracted-result-authority"
    )


def test_extracted_message_missing_generated_text_is_bounded():
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    del payload["responses"][0]["messages"][0]["generated_text"]
    issues = validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )
    _assert_exact(
        issues, "extracted-result-invalid-reconstruction", "extracted-result-authority"
    )


def test_extracted_message_missing_finish_reason_is_bounded():
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    del payload["responses"][0]["messages"][0]["finish_reason"]
    issues = validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )
    _assert_exact(
        issues, "extracted-result-invalid-reconstruction", "extracted-result-authority"
    )


def test_malformed_extracted_diagnostic_survives_caller_mutation():
    plan, extracted, context = FREEZE["_source"](True)
    payload = extracted.model_dump(mode="python")
    payload["responses"][0]["messages"] = [{"secret": "https://x/?token=one"}]
    holder = FREEZE["_ReturningModelDump"](payload)
    first = validate_openai_extracted_execution_result(
        holder, plan, context.provider_mapping_validation_context
    )
    before = (_dump(first), str(first), repr(first))
    payload["responses"][0]["messages"][0]["secret"] = "C:\\changed\\0x7ff"
    assert (
        validate_openai_extracted_execution_result(
            extracted, plan, context.provider_mapping_validation_context
        )
        == ()
    )
    assert before == (_dump(first), str(first), repr(first))


def test_prior_failure_diagnostic_is_isolated_from_later_failure_and_success():
    plan, extracted, context = FREEZE["_source"](True)
    first = validate_openai_extracted_execution_result(
        object(), plan, context.provider_mapping_validation_context
    )
    before = (_dump(first), str(first), repr(first))
    second = validate_openai_provider_execution_result(object(), context)
    assert second is not first
    assert (
        validate_openai_extracted_execution_result(
            extracted, plan, context.provider_mapping_validation_context
        )
        == ()
    )
    assert before == (_dump(first), str(first), repr(first))


def _diagnostic_matrix():
    plan, extracted, context, openai, _generic = _nonempty(True)
    local_empty = _empty("process-local")
    foreign_empty = _empty("process-foreign")
    malformed_payload = extracted.model_dump(mode="python")
    malformed_payload["responses"][0]["messages"][0]["finish_reason"] = None
    forged_openai = openai.model_copy(update={"identity": "scout:forged:" + "e" * 64})
    forged_extracted = extracted.model_copy(update={"fingerprint": "f" * 64})
    cases = {
        "malformed-extracted": validate_openai_extracted_execution_result(
            object(), plan, context.provider_mapping_validation_context
        ),
        "malformed-response": validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](malformed_payload),
            plan,
            context.provider_mapping_validation_context,
        ),
        "malformed-openai": validate_openai_provider_execution_result(
            object(), context
        ),
        "malformed-generic": validate_provider_execution_result(object(), context),
        "malformed-context": validate_openai_provider_execution_result(
            openai, object()
        ),
        "forged-openai-identity": validate_openai_provider_execution_result(
            forged_openai, context
        ),
        "forged-extracted-fingerprint": validate_openai_extracted_execution_result(
            forged_extracted, plan, context.provider_mapping_validation_context
        ),
        "foreign-empty-extracted": validate_openai_extracted_execution_result(
            foreign_empty[1],
            local_empty[0],
            local_empty[2].provider_mapping_validation_context,
        ),
        "foreign-empty-openai": validate_openai_provider_execution_result(
            foreign_empty[3], local_empty[2]
        ),
        "foreign-empty-generic": validate_provider_execution_result(
            foreign_empty[4], local_empty[2]
        ),
    }
    return {
        name: {
            "serialized": _dump(issues),
            "asdict": [asdict(issue) for issue in issues],
            "str": str(issues),
            "repr": repr(issues),
            "count": len(issues),
            "order": [issue.code for issue in issues],
        }
        for name, issues in sorted(cases.items())
    }


def test_complete_diagnostic_matrix_is_equal_across_processes():
    code = (
        "import json,runpy,sys;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_final_freeze.py');"
        "print(json.dumps(n['_diagnostic_matrix'](),sort_keys=True,separators=(',',':'),ensure_ascii=True))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second
    expected = json.loads(
        json.dumps(
            _diagnostic_matrix(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    )
    assert json.loads(first) == expected


@pytest.mark.parametrize("error", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize(
    ("validator", "boundary"),
    (
        ("extracted", "authority"),
        ("extracted", "plan"),
        ("extracted", "context"),
        ("extracted", "nearest-nested-authority"),
        ("openai", "result"),
        ("openai", "context"),
        ("openai", "nearest-nested-authority"),
        ("generic", "result"),
        ("generic", "context"),
        ("generic", "nearest-nested-authority"),
    ),
)
def test_process_control_propagates_at_each_reachable_or_nearest_boundary(
    error, validator, boundary
):
    plan, extracted, context, openai, generic = _nonempty(True)
    hostile = FREEZE["_FailingModelDump"](error)
    with pytest.raises(error):
        if validator == "extracted":
            args = [extracted, plan, context.provider_mapping_validation_context]
            args[
                {
                    "authority": 0,
                    "plan": 1,
                    "context": 2,
                    "nearest-nested-authority": 0,
                }[boundary]
            ] = hostile
            validate_openai_extracted_execution_result(*args)
        elif validator == "openai":
            validate_openai_provider_execution_result(
                hostile if boundary == "result" else openai,
                context if boundary == "result" else hostile,
            )
        else:
            validate_provider_execution_result(
                hostile if boundary == "result" else generic,
                context if boundary == "result" else hostile,
            )
