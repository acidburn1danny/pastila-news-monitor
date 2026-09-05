"""Exhaustive named freeze matrices for Phase 6.3 result authority."""

import hashlib
import json
import runpy
import subprocess
import sys
import unicodedata
from dataclasses import asdict
from functools import partial

import pytest

from pastila_scout.editor.script_composer import (
    validate_openai_extracted_execution_result,
    validate_openai_provider_execution_result,
    validate_provider_execution_result,
)

sys.path.insert(0, "tests")
FINAL = runpy.run_path(
    "tests/test_editorial_script_composer_provider_results_final_freeze.py"
)
FREEZE = FINAL["FREEZE"]


def _empty(purpose):
    return FREEZE["_empty_source"](purpose)


def _nonempty(single=True):
    return FREEZE["_submitted_source"](single)


def _snapshot(issues):
    return {
        "count": len(issues),
        "codes": tuple(issue.code for issue in issues),
        "asdict": tuple(asdict(issue) for issue in issues),
        "json": json.dumps(
            [asdict(issue) for issue in issues],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
        "str": str(issues),
        "repr": repr(issues),
    }


def _assert_complete(issues, expected_codes):
    snapshot = _snapshot(issues)
    assert snapshot["codes"] == expected_codes
    assert snapshot["count"] == len(expected_codes)
    for issue in issues:
        assert issue.code == issue.message_key
        assert issue.field_path == (
            (issue.field_reference,) if issue.field_reference else ()
        )
        assert isinstance(issue.artifact_reference, str) and issue.artifact_reference
        assert isinstance(issue.related_references, tuple)
    for unsafe in ("token=", "Traceback", "0x7ff", "C:\\private"):
        assert unsafe not in snapshot["json"]
    return snapshot


LINEAGE_CASES = (
    ("draft-identity", "extracted", "draft_reference", "draft_reference"),
    ("draft-fingerprint", "extracted", "draft_fingerprint", "draft_fingerprint"),
    (
        "execution-plan-identity",
        "extracted",
        "execution_plan_identity",
        "execution_plan_identity",
    ),
    (
        "execution-plan-fingerprint",
        "extracted",
        "execution_plan_fingerprint",
        "execution_plan_fingerprint",
    ),
    (
        "provider-plan-identity",
        "extracted",
        "provider_request_plan_identity",
        "provider_request_plan_identity",
    ),
    (
        "provider-plan-fingerprint",
        "extracted",
        "provider_request_plan_fingerprint",
        "provider_request_plan_fingerprint",
    ),
    (
        "openai-plan-identity",
        "extracted",
        "openai_request_plan_identity",
        "openai_request_plan_identity",
    ),
    (
        "openai-plan-fingerprint",
        "extracted",
        "openai_request_plan_fingerprint",
        "openai_request_plan_fingerprint",
    ),
    ("extracted-result-identity", "extracted", "identity", "identity"),
    ("extracted-result-fingerprint", "extracted", "fingerprint", "fingerprint"),
    (
        "extracted-result-reference",
        "extracted",
        "extracted_execution_result_reference",
        "extracted_execution_result_reference",
    ),
    ("openai-result-identity", "openai", "identity", "identity"),
    ("openai-result-fingerprint", "openai", "fingerprint", "fingerprint"),
    (
        "openai-result-reference",
        "openai",
        "openai_provider_execution_result_reference",
        "openai_provider_execution_result_reference",
    ),
    (
        "generic-concrete-identity",
        "generic",
        "provider_result_identity",
        "provider_result_identity",
    ),
    (
        "generic-concrete-fingerprint",
        "generic",
        "provider_result_fingerprint",
        "provider_result_fingerprint",
    ),
    (
        "generic-concrete-reference",
        "generic",
        "provider_result_reference",
        "provider_result_reference",
    ),
)

LINEAGE_EXPECTED_CODES = {
    "draft-identity": ("extracted-result-execution-draft-reference-mismatch",),
    "draft-fingerprint": ("extracted-result-execution-draft-fingerprint-mismatch",),
    "execution-plan-identity": (
        "extracted-result-execution-execution-plan-identity-mismatch",
    ),
    "execution-plan-fingerprint": (
        "extracted-result-execution-execution-plan-fingerprint-mismatch",
    ),
    "provider-plan-identity": (
        "extracted-result-execution-provider-request-plan-identity-mismatch",
    ),
    "provider-plan-fingerprint": (
        "extracted-result-execution-provider-request-plan-fingerprint-mismatch",
    ),
    "openai-plan-identity": (
        "extracted-result-execution-openai-request-plan-identity-mismatch",
    ),
    "openai-plan-fingerprint": (
        "extracted-result-execution-openai-request-plan-fingerprint-mismatch",
    ),
    "extracted-result-identity": ("extracted-result-invalid-execution-identity",),
    "extracted-result-fingerprint": ("extracted-result-invalid-execution-fingerprint",),
    "extracted-result-reference": (
        "extracted-result-execution-extracted-execution-result-reference-mismatch",
    ),
    "openai-result-identity": ("provider-result-invalid-openai-result-identity",),
    "openai-result-fingerprint": ("provider-result-invalid-openai-result-fingerprint",),
    "openai-result-reference": (
        "provider-result-openai-openai-provider-execution-result-reference-mismatch",
    ),
    "generic-concrete-identity": (
        "provider-result-generic-provider-result-identity-mismatch",
    ),
    "generic-concrete-fingerprint": (
        "provider-result-generic-provider-result-fingerprint-mismatch",
        "provider-result-invalid-generic-result-fingerprint",
        "provider-result-invalid-generic-result-identity",
    ),
    "generic-concrete-reference": (
        "provider-result-generic-provider-result-reference-mismatch",
    ),
}


def _lineage_scenario(case_id, artifact, field, foreign_field):
    local = _empty(f"lineage-local-{case_id}")
    foreign = _empty(f"lineage-foreign-{case_id}")
    assert (
        validate_openai_extracted_execution_result(
            foreign[1], foreign[0], foreign[2].provider_mapping_validation_context
        )
        == ()
    )
    assert validate_openai_provider_execution_result(foreign[3], foreign[2]) == ()
    assert validate_provider_execution_result(foreign[4], foreign[2]) == ()
    targets = {"extracted": local[1], "openai": local[3], "generic": local[4]}
    foreign_targets = {
        "extracted": foreign[1],
        "openai": foreign[3],
        "generic": foreign[4],
    }
    changed = targets[artifact].model_copy(
        update={field: getattr(foreign_targets[artifact], foreign_field)}
    )
    if artifact == "extracted":
        if field == "identity":
            changed = changed.model_copy(
                update={
                    "fingerprint": FREEZE[
                        "derive_openai_extracted_execution_result_fingerprint"
                    ](changed)
                }
            )
        elif field != "fingerprint":
            changed = FREEZE["_seal_execution"](changed)
        return validate_openai_extracted_execution_result(
            changed, local[0], local[2].provider_mapping_validation_context
        )
    if artifact == "openai":
        if field == "identity":
            changed = changed.model_copy(
                update={
                    "fingerprint": FREEZE[
                        "derive_openai_provider_execution_result_fingerprint"
                    ](changed)
                }
            )
        elif field != "fingerprint":
            changed = FREEZE["_seal_openai_result"](changed)
        return validate_openai_provider_execution_result(changed, local[2])
    if field != "provider_result_fingerprint":
        changed = FREEZE["_seal_generic_result"](changed)
    return validate_provider_execution_result(changed, local[2])


@pytest.mark.parametrize(
    ("case_id", "artifact", "field", "foreign_field"),
    LINEAGE_CASES,
    ids=[case[0] for case in LINEAGE_CASES],
)
def test_complete_17_dimension_empty_lineage_matrix(
    case_id, artifact, field, foreign_field
):
    first = _lineage_scenario(case_id, artifact, field, foreign_field)
    second = _lineage_scenario(case_id, artifact, field, foreign_field)
    assert first == second
    assert _snapshot(first) == _snapshot(second)
    _assert_complete(first, LINEAGE_EXPECTED_CODES[case_id])


FOREIGN_EMPTY_CASES = (
    "foreign-extracted-in-local-context",
    "local-extracted-in-foreign-context",
    "foreign-extracted-with-local-plan",
    "local-extracted-with-foreign-plan",
    "foreign-openai-in-local-context",
    "local-openai-in-foreign-context",
    "foreign-generic-in-local-context",
    "local-generic-in-foreign-context",
    "foreign-openai-in-local-generic",
    "local-openai-in-foreign-generic",
    "foreign-plan-in-local-context",
    "foreign-mapping-context-for-local-extracted",
    "foreign-extracted-context-member",
    "foreign-plan-context-member",
    "foreign-plan-and-extracted-context-members",
    "foreign-openai-context-authority",
    "foreign-generic-concrete-authority",
)


def _foreign_empty_scenario(case_id):
    local, foreign = _empty(f"local-{case_id}"), _empty(f"foreign-{case_id}")
    local_plan, local_extracted, local_context, local_openai, local_generic = local
    (
        foreign_plan,
        foreign_extracted,
        foreign_context,
        foreign_openai,
        foreign_generic,
    ) = foreign
    context_type = type(local_context)
    if case_id == "foreign-extracted-in-local-context":
        return validate_openai_extracted_execution_result(
            foreign_extracted,
            local_plan,
            local_context.provider_mapping_validation_context,
        )
    if case_id == "foreign-extracted-with-local-plan":
        return validate_openai_extracted_execution_result(
            foreign_extracted,
            local_plan,
            foreign_context.provider_mapping_validation_context,
        )
    if case_id == "local-extracted-in-foreign-context":
        return validate_openai_extracted_execution_result(
            local_extracted,
            foreign_plan,
            foreign_context.provider_mapping_validation_context,
        )
    if case_id == "local-extracted-with-foreign-plan":
        return validate_openai_extracted_execution_result(
            local_extracted,
            foreign_plan,
            local_context.provider_mapping_validation_context,
        )
    if case_id == "foreign-openai-in-local-context":
        return validate_openai_provider_execution_result(foreign_openai, local_context)
    if case_id == "local-openai-in-foreign-context":
        return validate_openai_provider_execution_result(local_openai, foreign_context)
    if case_id == "foreign-generic-in-local-context":
        return validate_provider_execution_result(foreign_generic, local_context)
    if case_id == "local-generic-in-foreign-context":
        return validate_provider_execution_result(local_generic, foreign_context)
    if case_id == "foreign-openai-in-local-generic":
        changed = FREEZE["_seal_generic_result"](
            local_generic.model_copy(update={"openai_execution_result": foreign_openai})
        )
        return validate_provider_execution_result(changed, local_context)
    if case_id == "local-openai-in-foreign-generic":
        changed = FREEZE["_seal_generic_result"](
            foreign_generic.model_copy(update={"openai_execution_result": local_openai})
        )
        return validate_provider_execution_result(changed, foreign_context)
    if case_id == "foreign-plan-in-local-context":
        changed = context_type(
            provider_request_plans=(foreign_plan,),
            provider_mapping_validation_context=foreign_context.provider_mapping_validation_context,
            extracted_execution_results=(local_extracted,),
        )
        return validate_openai_provider_execution_result(local_openai, changed)
    if case_id == "foreign-mapping-context-for-local-extracted":
        return validate_openai_extracted_execution_result(
            local_extracted,
            local_plan,
            foreign_context.provider_mapping_validation_context,
        )
    if case_id == "foreign-extracted-context-member":
        changed = context_type(
            provider_request_plans=(local_plan,),
            provider_mapping_validation_context=local_context.provider_mapping_validation_context,
            extracted_execution_results=(foreign_extracted,),
        )
        return validate_openai_provider_execution_result(local_openai, changed)
    if case_id == "foreign-plan-context-member":
        changed = context_type(
            provider_request_plans=(foreign_plan,),
            provider_mapping_validation_context=foreign_context.provider_mapping_validation_context,
            extracted_execution_results=(foreign_extracted,),
        )
        return validate_openai_provider_execution_result(local_openai, changed)
    if case_id == "foreign-plan-and-extracted-context-members":
        return validate_openai_provider_execution_result(local_openai, foreign_context)
    if case_id == "foreign-openai-context-authority":
        changed = context_type(
            provider_request_plans=(local_plan,),
            provider_mapping_validation_context=foreign_context.provider_mapping_validation_context,
            extracted_execution_results=(local_extracted,),
        )
        return validate_openai_provider_execution_result(local_openai, changed)
    if case_id == "foreign-generic-concrete-authority":
        changed = FREEZE["_seal_generic_result"](
            local_generic.model_copy(
                update={
                    "provider_result_reference": foreign_generic.provider_result_reference,
                    "provider_result_identity": foreign_generic.provider_result_identity,
                    "provider_result_fingerprint": foreign_generic.provider_result_fingerprint,
                    "openai_execution_result": foreign_openai,
                }
            )
        )
        return validate_provider_execution_result(changed, local_context)
    raise AssertionError(f"unregistered foreign-empty scenario: {case_id}")


@pytest.mark.parametrize(
    "case_id",
    FOREIGN_EMPTY_CASES,
    ids=FOREIGN_EMPTY_CASES,
)
def test_complete_17_case_foreign_empty_matrix(case_id):
    first, second = _foreign_empty_scenario(case_id), _foreign_empty_scenario(case_id)
    assert first and first == second and _snapshot(first) == _snapshot(second)


DIRECTIONAL_CASES = (
    "empty-request-nonempty-extracted",
    "nonempty-request-empty-extracted",
    "empty-extracted-nonempty-openai",
    "nonempty-extracted-empty-openai",
    "empty-generic-nonempty-concrete",
    "nonempty-generic-empty-concrete",
    "empty-request-nonempty-submitted-responses",
    "nonempty-request-empty-submitted-responses",
    "empty-authority-placeholder-response",
    "nonempty-authority-missing-response",
    "empty-authority-placeholder-message",
    "nonempty-authority-empty-message-tuple",
    "one-request-zero-responses",
    "one-request-multiple-responses",
    "one-response-zero-messages",
    "one-response-multiple-messages",
    "empty-top-level-extra-response",
    "nonempty-top-level-omitted-response",
)


def _directional(case_id):
    empty, nonempty = _empty(f"direction-{case_id}"), _nonempty(True)
    if case_id in {"empty-request-nonempty-extracted"}:
        return validate_openai_extracted_execution_result(
            nonempty[1], empty[0], empty[2].provider_mapping_validation_context
        )
    if case_id == "nonempty-request-empty-extracted":
        return validate_openai_extracted_execution_result(
            empty[1], nonempty[0], nonempty[2].provider_mapping_validation_context
        )
    if case_id in {
        "empty-extracted-nonempty-openai",
        "empty-request-nonempty-submitted-responses",
    }:
        return validate_openai_provider_execution_result(nonempty[3], empty[2])
    if case_id in {
        "nonempty-extracted-empty-openai",
        "nonempty-request-empty-submitted-responses",
    }:
        return validate_openai_provider_execution_result(empty[3], nonempty[2])
    if case_id == "empty-generic-nonempty-concrete":
        value = FREEZE["_seal_generic_result"](
            empty[4].model_copy(update={"openai_execution_result": nonempty[3]})
        )
        return validate_provider_execution_result(value, empty[2])
    if case_id == "nonempty-generic-empty-concrete":
        value = FREEZE["_seal_generic_result"](
            nonempty[4].model_copy(update={"openai_execution_result": empty[3]})
        )
        return validate_provider_execution_result(value, nonempty[2])
    result = nonempty[3]
    response = result.responses[0]
    if case_id in {"empty-authority-placeholder-response"}:
        value = result.model_copy(update={"responses": ({},)})
    elif case_id in {
        "nonempty-authority-missing-response",
        "one-request-zero-responses",
        "nonempty-top-level-omitted-response",
    }:
        value = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": ()})
        )
    elif case_id in {
        "one-request-multiple-responses",
        "empty-top-level-extra-response",
    }:
        value = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (response, response)})
        )
    elif case_id in {"empty-authority-placeholder-message"}:
        value = result.model_copy(
            update={"responses": (response.model_copy(update={"messages": ({},)}),)}
        )
    elif case_id in {
        "nonempty-authority-empty-message-tuple",
        "one-response-zero-messages",
    }:
        changed = FREEZE["_seal_openai_response"](
            response.model_copy(update={"messages": ()})
        )
        value = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (changed,)})
        )
    else:
        changed = FREEZE["_seal_openai_response"](
            response.model_copy(update={"messages": response.messages * 2})
        )
        value = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (changed,)})
        )
    return validate_openai_provider_execution_result(value, nonempty[2])


@pytest.mark.parametrize("case_id", DIRECTIONAL_CASES, ids=DIRECTIONAL_CASES)
def test_complete_empty_nonempty_directional_matrix(case_id):
    first, second = _directional(case_id), _directional(case_id)
    assert first and first == second
    assert _snapshot(first) == _snapshot(second)


PLACEHOLDER_CASES = (
    "placeholder-extracted-response",
    "placeholder-extracted-message",
    "placeholder-openai-response",
    "placeholder-openai-message",
    "placeholder-generic-concrete-result",
    "empty-mapping-extracted-response",
    "empty-mapping-extracted-message",
    "empty-mapping-openai-response",
    "empty-mapping-openai-message",
    "minimal-extracted-response",
    "minimal-extracted-message",
    "minimal-openai-response",
    "minimal-openai-message",
)


@pytest.mark.parametrize("case_id", PLACEHOLDER_CASES, ids=PLACEHOLDER_CASES)
def test_distinct_placeholder_authority_matrix(case_id):
    issues = _placeholder_case(case_id)
    expected = {
        "placeholder-generic-concrete-result": "provider-result-invalid-generic-result"
    }.get(
        case_id,
        (
            "extracted-result-invalid-reconstruction"
            if "extracted" in case_id
            else "provider-result-invalid-openai-result"
        ),
    )
    _assert_complete(issues, (expected,))


def _placeholder_case(case_id):
    plan, extracted, context, openai, generic = _nonempty(True)
    if "generic" in case_id:
        value = generic.model_copy(update={"openai_execution_result": {}})
        issues = validate_provider_execution_result(value, context)
    elif "extracted" in case_id:
        payload = extracted.model_dump(mode="python")
        target = {} if "response" in case_id else {"generated_text": "x"}
        if "message" in case_id:
            payload["responses"][0]["messages"] = (target,)
        else:
            payload["responses"] = (target,)
        holder = FREEZE["_ReturningModelDump"](payload)
        issues = validate_openai_extracted_execution_result(
            holder, plan, context.provider_mapping_validation_context
        )
    else:
        payload = openai.model_dump(mode="python")
        target = {} if "response" in case_id else {"generated_text": "x"}
        if "message" in case_id:
            payload["responses"][0]["messages"] = (target,)
        else:
            payload["responses"] = (target,)
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    return issues


CARDINALITY_CASES = (
    "zero-responses",
    "two-responses",
    "duplicate-response",
    "foreign-response",
    "reordered-responses",
    "wrong-request-response",
    "wrong-provider-plan-response",
    "wrong-execution-plan-response",
    "wrong-draft-response",
    "empty-request-one-response",
    "nonempty-request-zero-responses",
    "placeholder-response",
    "malformed-response-container",
    "response-tuple-none",
    "response-tuple-mapping",
    "nearest-structurally-reachable-foreign-response",
)


@pytest.mark.parametrize("case_id", CARDINALITY_CASES, ids=CARDINALITY_CASES)
def test_complete_response_cardinality_matrix(case_id):
    first, second = _response_case(case_id), _response_case(case_id)
    assert first and first == second and _snapshot(first) == _snapshot(second)


def _response_case(case_id):
    _, _, context, result, _ = _nonempty(case_id != "reordered-responses")
    response = result.responses[0]
    if case_id in {"zero-responses", "nonempty-request-zero-responses"}:
        changed = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": ()})
        )
    elif case_id in {"two-responses", "duplicate-response"}:
        changed = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (response, response)})
        )
    elif case_id in {
        "foreign-response",
        "nearest-structurally-reachable-foreign-response",
    }:
        foreign = _nonempty(False)[3].responses[1]
        changed = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (foreign,)})
        )
    elif case_id == "reordered-responses":
        reordered = tuple(
            FREEZE["_seal_openai_response"](
                item.model_copy(update={"response_ordinal": index})
            )
            for index, item in enumerate(reversed(result.responses))
        )
        changed = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": reordered})
        )
    elif case_id.startswith("wrong-"):
        foreign = _nonempty(False)[3].responses[1]
        field = {
            "wrong-request-response": "openai_request_reference",
            "wrong-provider-plan-response": "provider_request_plan_reference",
            "wrong-execution-plan-response": "execution_plan_reference",
            "wrong-draft-response": "draft_reference",
        }[case_id]
        altered = FREEZE["_seal_openai_response"](
            response.model_copy(update={field: getattr(foreign, field)})
        )
        changed = FREEZE["_seal_openai_result"](
            result.model_copy(update={"responses": (altered,)})
        )
    elif case_id == "empty-request-one-response":
        return validate_openai_provider_execution_result(result, _empty("r-empty")[2])
    else:
        value = {
            "placeholder-response": ({},),
            "malformed-response-container": "invalid",
            "response-tuple-none": (None,),
            "response-tuple-mapping": ({"identity": "missing-authority"},),
        }[case_id]
        changed = result.model_copy(update={"responses": value})
    return validate_openai_provider_execution_result(changed, context)


MESSAGE_CASES = (
    "zero-messages",
    "two-messages",
    "duplicate-message",
    "foreign-message",
    "reordered-messages",
    "wrong-response-message",
    "wrong-request-message",
    "wrong-extracted-result-message",
    "wrong-generated-text",
    "wrong-finish-reason",
    "placeholder-message",
    "empty-mapping-message",
    "minimal-message",
    "message-tuple-none",
    "message-tuple-mapping",
    "message-list",
    "message-set",
    "messages-omitted",
    "messages-none",
    "nearest-structurally-reachable-foreign-message",
)


@pytest.mark.parametrize("case_id", MESSAGE_CASES, ids=MESSAGE_CASES)
def test_complete_message_cardinality_matrix(case_id):
    first, second = _message_case(case_id), _message_case(case_id)
    assert first and first == second and _snapshot(first) == _snapshot(second)


def _message_case(case_id):
    _, _, context, result, _ = _nonempty(True)
    response, message = result.responses[0], result.responses[0].messages[0]
    if case_id in {"zero-messages", "messages-omitted"}:
        messages = () if case_id == "zero-messages" else None
    elif case_id in {"two-messages", "duplicate-message"}:
        messages = (message, message)
    elif case_id in {
        "foreign-message",
        "nearest-structurally-reachable-foreign-message",
    }:
        messages = (_nonempty(False)[3].responses[1].messages[0],)
    elif case_id == "reordered-messages":
        foreign = _nonempty(False)[3].responses[1].messages[0]
        messages = (foreign, message)
    elif case_id.startswith("wrong-"):
        foreign = _nonempty(False)[3].responses[1].messages[0]
        field = {
            "wrong-response-message": "provider_response_reference",
            "wrong-request-message": "openai_request_reference",
            "wrong-extracted-result-message": "provider_request_plan_reference",
            "wrong-generated-text": "generated_text",
            "wrong-finish-reason": "finish_reason",
        }[case_id]
        replacement = (
            "foreign generated text"
            if field == "generated_text"
            else "length" if field == "finish_reason" else getattr(foreign, field)
        )
        messages = (
            FREEZE["_seal_openai_message"](
                message.model_copy(update={field: replacement})
            ),
        )
    else:
        messages = {
            "placeholder-message": ({},),
            "empty-mapping-message": ({},),
            "minimal-message": ({"generated_text": "x"},),
            "message-tuple-none": (None,),
            "message-tuple-mapping": ({"identity": "missing"},),
            "message-list": [message, message],
            "message-set": set(),
            "messages-none": None,
        }[case_id]
    altered = response.model_copy(update={"messages": messages})
    changed = result.model_copy(update={"responses": (altered,)})
    return validate_openai_provider_execution_result(changed, context)


def _subprocess_matrix():
    diagnostics = {}
    for index, name in enumerate(CARDINALITY_CASES, start=1):
        diagnostics[f"response-{index:02d}-{name}"] = _snapshot(_response_case(name))
    for index, name in enumerate(MESSAGE_CASES, start=1):
        diagnostics[f"message-{index:02d}-{name}"] = _snapshot(_message_case(name))
    for index, name in enumerate(PLACEHOLDER_CASES, start=1):
        diagnostics[f"placeholder-{index:02d}-{name}"] = _snapshot(
            _placeholder_case(name)
        )
    return diagnostics


@pytest.fixture(scope="module")
def stable_subprocess_matrix():
    code = (
        "import json,runpy,sys;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_exhaustive_freeze.py');"
        "print(json.dumps(n['_subprocess_matrix'](),sort_keys=True,separators=(',',':'),ensure_ascii=True,default=list))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second
    return json.loads(first)


def test_complete_separate_process_diagnostic_matrix(stable_subprocess_matrix):
    expected = (
        json.dumps(
            _subprocess_matrix(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=list,
        ).encode()
        + b"\n"
    )
    assert stable_subprocess_matrix == json.loads(expected)


ARTIFACT_CASES = (
    "extracted-execution-result",
    "extracted-response",
    "extracted-message",
    "openai-execution-result",
    "openai-response",
    "openai-message",
    "generic-result",
)


@pytest.mark.parametrize("case_id", ARTIFACT_CASES, ids=ARTIFACT_CASES)
def test_all_seven_artifacts_have_equal_separate_process_representations(case_id):
    code = (
        "import json,runpy,sys;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_freeze.py');"
        "p,a,c=n['_source'](True);o=n['build_openai_provider_execution_result'](p,a,c);"
        "g=n['build_provider_execution_result'](p,a,c);"
        "items={'extracted-execution-result':a,'extracted-response':a.responses[0],"
        "'extracted-message':a.responses[0].messages[0],'openai-execution-result':o,"
        "'openai-response':o.responses[0],'openai-message':o.responses[0].messages[0],"
        "'generic-result':g};x=items[sys.argv[1]];"
        "refs=('extracted_execution_result_reference','extracted_response_reference',"
        "'extracted_response_message_reference','openai_provider_execution_result_reference',"
        "'provider_response_reference','provider_response_message_reference',"
        "'provider_execution_result_reference');ref=next(getattr(x,r) for r in refs if hasattr(x,r));"
        "dump=x.model_dump(mode='json');canonical=json.dumps(dump,sort_keys=True,separators=(',',':'),ensure_ascii=False);"
        "print(json.dumps({'dump':dump,'canonical':canonical,'reference':ref,'identity':x.identity,"
        "'fingerprint':x.fingerprint,'seals':(x.identity,x.fingerprint),'str':str(x),'repr':repr(x)},"
        "sort_keys=True,separators=(',',':'),ensure_ascii=True))"
    )
    first = subprocess.check_output([sys.executable, "-c", code, case_id])
    second = subprocess.check_output([sys.executable, "-c", code, case_id])
    assert first == second


def test_every_declared_scenario_has_an_explicit_constructor_and_no_fallback():
    assert len(set(LINEAGE_EXPECTED_CODES)) == len(LINEAGE_CASES) == 17
    assert len(set(FOREIGN_EMPTY_CASES)) == 17
    assert len(set(DIRECTIONAL_CASES)) == 18
    assert len(set(PLACEHOLDER_CASES)) == 13
    assert len(set(CARDINALITY_CASES)) == 16
    assert len(set(MESSAGE_CASES)) == 20
    with pytest.raises(KeyError):
        _response_case("unregistered-response-scenario")
    with pytest.raises(KeyError):
        _message_case("unregistered-message-scenario")
    with pytest.raises(AssertionError):
        _foreign_empty_scenario("unregistered-foreign-empty-scenario")


EXTRA_FIELD_CASES = (
    "extracted-execution-result",
    "extracted-response",
    "extracted-message",
    "openai-execution-result",
    "openai-response",
    "openai-message",
    "generic-result",
    "validation-context",
)


@pytest.mark.parametrize("case_id", EXTRA_FIELD_CASES, ids=EXTRA_FIELD_CASES)
def test_eight_case_nested_extra_field_matrix_survives_caller_mutation(case_id):
    plan, extracted, context, openai, generic = _nonempty(True)
    hostile = {"nested": ["https://x.invalid/?token=secret"]}
    if case_id.startswith("extracted"):
        payload = extracted.model_dump(mode="python")
        target = payload
        if case_id == "extracted-response":
            target = payload["responses"][0]
        elif case_id == "extracted-message":
            target = payload["responses"][0]["messages"][0]
        target["hostile_extra"] = hostile
        issues = validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
        expected = "extracted-result-invalid-reconstruction"
    elif case_id.startswith("openai"):
        payload = openai.model_dump(mode="python")
        target = payload
        if case_id == "openai-response":
            target = payload["responses"][0]
        elif case_id == "openai-message":
            target = payload["responses"][0]["messages"][0]
        target["hostile_extra"] = hostile
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
        expected = "provider-result-invalid-openai-result"
    elif case_id == "generic-result":
        payload = generic.model_dump(mode="python")
        payload["hostile_extra"] = hostile
        issues = validate_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
        expected = "provider-result-invalid-generic-result"
    else:
        payload = context.model_dump(mode="python")
        payload["hostile_extra"] = hostile
        issues = validate_provider_execution_result(
            generic, FREEZE["_ReturningModelDump"](payload)
        )
        expected = "provider-result-invalid-context"
    before = _snapshot(issues)
    hostile["nested"].append("C:\\private\\0x7ff")
    assert _snapshot(issues) == before
    _assert_complete(issues, (expected,))


# ---------------------------------------------------------------------------
# Complete freeze-evidence registries
# ---------------------------------------------------------------------------


def _codes(issues):
    return tuple(item.code for item in issues)


def _construction_fingerprint(constructor, family):
    function = getattr(constructor, "func", constructor)
    arguments = getattr(constructor, "args", ())
    keywords = getattr(constructor, "keywords", {}) or {}
    signature = json.dumps(
        {
            "family": family,
            "function": function.__qualname__,
            "arguments": arguments,
            "keywords": keywords,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(signature.encode()).hexdigest()


RESPONSE_CARDINALITY_SCENARIOS = {
    "zero-responses-for-one-request": partial(_response_case, "zero-responses"),
    "two-responses-for-one-request": partial(_response_case, "two-responses"),
    "duplicate-response-instance": partial(_response_case, "duplicate-response"),
    "independently-valid-foreign-response": partial(_response_case, "foreign-response"),
    "reordered-responses-corrected-ordinals": partial(
        _response_case, "reordered-responses"
    ),
    "wrong-request-ownership": partial(_response_case, "wrong-request-response"),
    "wrong-provider-plan-ownership": partial(
        _response_case, "wrong-provider-plan-response"
    ),
    "wrong-execution-plan-ownership": partial(
        _response_case, "wrong-execution-plan-response"
    ),
    "wrong-draft-ownership": partial(_response_case, "wrong-draft-response"),
    "empty-request-set-one-response": partial(
        _response_case, "empty-request-one-response"
    ),
    "nonempty-request-set-zero-responses": partial(
        _response_case, "nonempty-request-zero-responses"
    ),
    "placeholder-response": partial(_response_case, "placeholder-response"),
    "malformed-response-container": partial(
        _response_case, "malformed-response-container"
    ),
    "response-tuple-containing-none": partial(_response_case, "response-tuple-none"),
    "response-tuple-containing-malformed-mapping": partial(
        _response_case, "response-tuple-mapping"
    ),
    "nearest-reachable-foreign-response-substitution": partial(
        _response_case, "nearest-structurally-reachable-foreign-response"
    ),
}

RESPONSE_EXPECTED_CODES = {
    "zero-responses-for-one-request": ("provider-result-missing-response",),
    "two-responses-for-one-request": (
        "provider-result-duplicate-openai-request-identity",
        "provider-result-duplicate-openai-request-reference",
        "provider-result-duplicate-response-identity",
        "provider-result-duplicate-response-ordinal",
        "provider-result-duplicate-response-reference",
        "provider-result-extra-response",
    ),
    "duplicate-response-instance": (
        "provider-result-duplicate-openai-request-identity",
        "provider-result-duplicate-openai-request-reference",
        "provider-result-duplicate-response-identity",
        "provider-result-duplicate-response-ordinal",
        "provider-result-duplicate-response-reference",
        "provider-result-extra-response",
    ),
    "independently-valid-foreign-response": (
        "provider-result-extra-response",
        "provider-result-missing-response",
    ),
    "reordered-responses-corrected-ordinals": (
        "provider-result-invalid-response-order",
        "provider-result-response-response-ordinal-mismatch",
        "provider-result-response-response-ordinal-mismatch",
    ),
    "wrong-request-ownership": (
        "provider-result-response-openai-request-reference-mismatch",
    ),
    "wrong-provider-plan-ownership": (
        "provider-result-response-provider-request-plan-reference-mismatch",
    ),
    "wrong-execution-plan-ownership": (
        "provider-result-response-execution-plan-reference-mismatch",
    ),
    "wrong-draft-ownership": ("provider-result-response-draft-reference-mismatch",),
    "empty-request-set-one-response": (
        "provider-result-unknown-provider-request-plan",
    ),
    "nonempty-request-set-zero-responses": ("provider-result-missing-response",),
    "placeholder-response": ("provider-result-invalid-openai-result",),
    "malformed-response-container": ("provider-result-invalid-openai-result",),
    "response-tuple-containing-none": ("provider-result-invalid-openai-result",),
    "response-tuple-containing-malformed-mapping": (
        "provider-result-invalid-openai-result",
    ),
    "nearest-reachable-foreign-response-substitution": (
        "provider-result-extra-response",
        "provider-result-missing-response",
    ),
}

MESSAGE_CARDINALITY_SCENARIOS = {
    "zero-messages": partial(_message_case, "zero-messages"),
    "two-messages": partial(_message_case, "two-messages"),
    "duplicate-message-instance": partial(_message_case, "duplicate-message"),
    "independently-valid-foreign-message": partial(_message_case, "foreign-message"),
    "reordered-messages-corrected-ordinals": partial(
        _message_case, "reordered-messages"
    ),
    "wrong-response-ownership": partial(_message_case, "wrong-response-message"),
    "wrong-request-ownership": partial(_message_case, "wrong-request-message"),
    "wrong-extracted-result-ownership": partial(
        _message_case, "wrong-extracted-result-message"
    ),
    "wrong-generated-text-authority": partial(_message_case, "wrong-generated-text"),
    "wrong-finish-reason-authority": partial(_message_case, "wrong-finish-reason"),
    "placeholder-message": partial(_message_case, "placeholder-message"),
    "empty-mapping-message": partial(_message_case, "empty-mapping-message"),
    "minimally-shaped-authority-free-message": partial(
        _message_case, "minimal-message"
    ),
    "message-tuple-containing-none": partial(_message_case, "message-tuple-none"),
    "message-tuple-containing-malformed-mapping": partial(
        _message_case, "message-tuple-mapping"
    ),
    "message-collection-as-list": partial(_message_case, "message-list"),
    "message-collection-as-set": partial(_message_case, "message-set"),
    "message-collection-omitted": partial(_message_case, "messages-omitted"),
    "message-collection-none": partial(_message_case, "messages-none"),
    "nearest-reachable-foreign-message-substitution": partial(
        _message_case, "nearest-structurally-reachable-foreign-message"
    ),
}

MESSAGE_EXPECTED_CODES = {
    name: codes
    for name, codes in (
        ("zero-messages", ("provider-result-invalid-openai-result",)),
        (
            "two-messages",
            (
                "provider-result-duplicate-message-identity",
                "provider-result-duplicate-message-ordinal",
                "provider-result-duplicate-message-reference",
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
            ),
        ),
        (
            "duplicate-message-instance",
            (
                "provider-result-duplicate-message-identity",
                "provider-result-duplicate-message-ordinal",
                "provider-result-duplicate-message-reference",
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
            ),
        ),
        (
            "wrong-response-ownership",
            (
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
                "provider-result-message-provider-response-reference-mismatch",
            ),
        ),
        (
            "wrong-request-ownership",
            (
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
                "provider-result-message-openai-request-reference-mismatch",
            ),
        ),
        (
            "wrong-extracted-result-ownership",
            (
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
                "provider-result-message-provider-request-plan-reference-mismatch",
            ),
        ),
        (
            "wrong-generated-text-authority",
            (
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
                "provider-result-message-generated-text-mismatch",
            ),
        ),
        (
            "wrong-finish-reason-authority",
            (
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
                "provider-result-message-finish-reason-mismatch",
            ),
        ),
        ("placeholder-message", ("provider-result-invalid-openai-result",)),
        ("empty-mapping-message", ("provider-result-invalid-openai-result",)),
        (
            "minimally-shaped-authority-free-message",
            ("provider-result-invalid-openai-result",),
        ),
        ("message-tuple-containing-none", ("provider-result-invalid-openai-result",)),
        (
            "message-tuple-containing-malformed-mapping",
            ("provider-result-invalid-openai-result",),
        ),
        (
            "message-collection-as-list",
            (
                "provider-result-duplicate-message-identity",
                "provider-result-duplicate-message-ordinal",
                "provider-result-duplicate-message-reference",
                "provider-result-invalid-openai-result-fingerprint",
                "provider-result-invalid-openai-result-identity",
                "provider-result-invalid-response-fingerprint",
                "provider-result-invalid-response-identity",
            ),
        ),
        ("message-collection-as-set", ("provider-result-invalid-openai-result",)),
        ("message-collection-omitted", ("provider-result-invalid-openai-result",)),
        ("message-collection-none", ("provider-result-invalid-openai-result",)),
    )
}
_FOREIGN_MESSAGE_CODES = (
    "provider-result-invalid-openai-result-fingerprint",
    "provider-result-invalid-openai-result-identity",
    "provider-result-invalid-response-fingerprint",
    "provider-result-invalid-response-identity",
    "provider-result-message-draft-fingerprint-mismatch",
    "provider-result-message-draft-reference-mismatch",
    "provider-result-message-execution-plan-fingerprint-mismatch",
    "provider-result-message-execution-plan-identity-mismatch",
    "provider-result-message-execution-plan-reference-mismatch",
    "provider-result-message-execution-request-fingerprint-mismatch",
    "provider-result-message-execution-request-identity-mismatch",
    "provider-result-message-execution-request-reference-mismatch",
    "provider-result-message-finish-reason-mismatch",
    "provider-result-message-generated-text-mismatch",
    "provider-result-message-openai-request-fingerprint-mismatch",
    "provider-result-message-openai-request-identity-mismatch",
    "provider-result-message-openai-request-plan-fingerprint-mismatch",
    "provider-result-message-openai-request-plan-identity-mismatch",
    "provider-result-message-openai-request-plan-reference-mismatch",
    "provider-result-message-openai-request-reference-mismatch",
    "provider-result-message-provider-request-plan-fingerprint-mismatch",
    "provider-result-message-provider-request-plan-identity-mismatch",
    "provider-result-message-provider-request-plan-reference-mismatch",
    "provider-result-message-provider-response-message-reference-mismatch",
    "provider-result-message-provider-response-reference-mismatch",
)
MESSAGE_EXPECTED_CODES.update(
    {
        "independently-valid-foreign-message": _FOREIGN_MESSAGE_CODES,
        "nearest-reachable-foreign-message-substitution": _FOREIGN_MESSAGE_CODES,
        "reordered-messages-corrected-ordinals": (
            "provider-result-duplicate-message-ordinal",
            *_FOREIGN_MESSAGE_CODES,
        ),
    }
)


@pytest.mark.parametrize("case_id", RESPONSE_CARDINALITY_SCENARIOS)
def test_response_cardinality_golden_registry(case_id):
    issues = RESPONSE_CARDINALITY_SCENARIOS[case_id]()
    _assert_complete(issues, RESPONSE_EXPECTED_CODES[case_id])


@pytest.mark.parametrize("case_id", MESSAGE_CARDINALITY_SCENARIOS)
def test_message_cardinality_golden_registry(case_id):
    issues = MESSAGE_CARDINALITY_SCENARIOS[case_id]()
    _assert_complete(issues, MESSAGE_EXPECTED_CODES[case_id])


def _malformed_scenario(case_id):
    plan, _extracted, context, _openai, generic = _nonempty(True)
    malformed = object()
    if case_id == "malformed-extracted-result":
        return validate_openai_extracted_execution_result(
            malformed, plan, context.provider_mapping_validation_context
        )
    if case_id == "malformed-extracted-response":
        payload = _nonempty(True)[1].model_dump(mode="python")
        payload["responses"] = ("malformed-response",)
        return validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
    if case_id == "malformed-extracted-message":
        payload = _nonempty(True)[1].model_dump(mode="python")
        payload["responses"][0]["messages"] = ("malformed-message",)
        return validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
    if case_id == "malformed-openai-result":
        return validate_openai_provider_execution_result(malformed, context)
    if case_id == "malformed-openai-response":
        payload = _nonempty(True)[3].model_dump(mode="python")
        payload["responses"] = ("malformed-response",)
        return validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    if case_id == "malformed-openai-message":
        payload = _nonempty(True)[3].model_dump(mode="python")
        payload["responses"][0]["messages"] = ("malformed-message",)
        return validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    if case_id == "malformed-generic-result":
        return validate_provider_execution_result(malformed, context)
    if case_id == "malformed-validation-context":
        return validate_provider_execution_result(generic, malformed)
    raise KeyError(case_id)


def _forged_scenario(case_id):
    _, extracted, context, openai, generic = _nonempty(True)
    artifact, field = case_id.removeprefix("forged-").rsplit("-", 1)
    if field == "seal":
        identity_prefix = {
            "extracted": "scout:openai-extracted-execution-result:",
            "openai": "scout:openai-provider-execution-result:",
            "generic": "scout:provider-execution-result:",
        }[artifact]
        changes = {"identity": identity_prefix + "f" * 64, "fingerprint": "f" * 64}
    elif field == "identity":
        prefix = {
            "extracted": "scout:openai-extracted-execution-result:",
            "openai": "scout:openai-provider-execution-result:",
            "generic": "scout:provider-execution-result:",
        }[artifact]
        changes = {"identity": prefix + "f" * 64}
    else:
        changes = {field: "f" * 64}
    if artifact == "extracted":
        value = extracted.model_copy(update=changes)
        if field == "identity":
            value = value.model_copy(
                update={
                    "fingerprint": FREEZE[
                        "derive_openai_extracted_execution_result_fingerprint"
                    ](value)
                }
            )
        return validate_openai_extracted_execution_result(
            value,
            context.provider_request_plans[0],
            context.provider_mapping_validation_context,
        )
    if artifact == "openai":
        value = openai.model_copy(update=changes)
        if field == "identity":
            value = value.model_copy(
                update={
                    "fingerprint": FREEZE[
                        "derive_openai_provider_execution_result_fingerprint"
                    ](value)
                }
            )
        return validate_openai_provider_execution_result(value, context)
    value = generic.model_copy(update=changes)
    if field == "identity":
        value = value.model_copy(
            update={
                "fingerprint": FREEZE["derive_provider_execution_result_fingerprint"](
                    value
                )
            }
        )
    return validate_provider_execution_result(value, context)


def _foreign_reference_scenario(case_id):
    local, foreign = _nonempty(True), _nonempty(False)
    level = case_id.removeprefix("foreign-").removesuffix("-canonical-reference")
    if level == "extracted":
        changed = FREEZE["_seal_execution"](
            local[1].model_copy(
                update={
                    "extracted_execution_result_reference": foreign[
                        1
                    ].extracted_execution_result_reference
                }
            )
        )
        return validate_openai_extracted_execution_result(
            changed, local[0], local[2].provider_mapping_validation_context
        )
    if level == "openai":
        changed = FREEZE["_seal_openai_result"](
            local[3].model_copy(
                update={
                    "openai_provider_execution_result_reference": foreign[
                        3
                    ].openai_provider_execution_result_reference
                }
            )
        )
        return validate_openai_provider_execution_result(changed, local[2])
    changed = FREEZE["_seal_generic_result"](
        local[4].model_copy(
            update={
                "provider_execution_result_reference": foreign[
                    4
                ].provider_execution_result_reference
            }
        )
    )
    return validate_provider_execution_result(changed, local[2])


def _nested_extra_scenario():
    plan, extracted, context, _, _ = _nonempty(True)
    payload = extracted.model_dump(mode="python")
    payload["responses"][0]["messages"][0]["hostile_extra"] = {"nested": ["value"]}
    return validate_openai_extracted_execution_result(
        FREEZE["_ReturningModelDump"](payload),
        plan,
        context.provider_mapping_validation_context,
    )


def _wrong_lineage_scenario(field):
    local, foreign = _nonempty(True), _nonempty(False)
    changed = FREEZE["_seal_generic_result"](
        local[4].model_copy(update={field: getattr(foreign[4], field)})
    )
    return validate_provider_execution_result(changed, local[2])


SUBPROCESS_SCENARIOS = {
    **{
        name: partial(_malformed_scenario, name)
        for name in (
            "malformed-extracted-result",
            "malformed-extracted-response",
            "malformed-extracted-message",
            "malformed-openai-result",
            "malformed-openai-response",
            "malformed-openai-message",
            "malformed-generic-result",
            "malformed-validation-context",
        )
    },
    **{
        name: partial(_forged_scenario, name)
        for name in (
            "forged-extracted-identity",
            "forged-extracted-fingerprint",
            "forged-extracted-seal",
            "forged-openai-identity",
            "forged-openai-fingerprint",
            "forged-openai-seal",
            "forged-generic-identity",
            "forged-generic-fingerprint",
            "forged-generic-seal",
        )
    },
    **{
        name: partial(_foreign_reference_scenario, name)
        for name in (
            "foreign-extracted-canonical-reference",
            "foreign-openai-canonical-reference",
            "foreign-generic-canonical-reference",
        )
    },
    "foreign-empty-extracted-authority": partial(
        _foreign_empty_scenario, "foreign-extracted-in-local-context"
    ),
    "foreign-empty-openai-result": partial(
        _foreign_empty_scenario, "foreign-openai-in-local-context"
    ),
    "foreign-empty-generic-result": partial(
        _foreign_empty_scenario, "foreign-generic-in-local-context"
    ),
    "extracted-empty-nonempty-mismatch": partial(
        _directional, "empty-request-nonempty-extracted"
    ),
    "openai-empty-nonempty-mismatch": partial(
        _directional, "empty-extracted-nonempty-openai"
    ),
    "generic-empty-nonempty-mismatch": partial(
        _directional, "empty-generic-nonempty-concrete"
    ),
    "response-omission": partial(_response_case, "zero-responses"),
    "response-excess": partial(_response_case, "two-responses"),
    "response-duplication": partial(_response_case, "duplicate-response"),
    "response-reordering": partial(_response_case, "reordered-responses"),
    "message-omission": partial(_message_case, "zero-messages"),
    "message-excess": partial(_message_case, "two-messages"),
    "message-duplication": partial(_message_case, "duplicate-message"),
    "message-reordering": partial(_message_case, "reordered-messages"),
    "placeholder-extracted-response": partial(
        _placeholder_case, "placeholder-extracted-response"
    ),
    "placeholder-extracted-message": partial(
        _placeholder_case, "placeholder-extracted-message"
    ),
    "placeholder-openai-response": partial(
        _placeholder_case, "placeholder-openai-response"
    ),
    "placeholder-openai-message": partial(
        _placeholder_case, "placeholder-openai-message"
    ),
    "nested-extra-field": partial(_nested_extra_scenario),
    "wrong-provider-ownership": partial(
        _wrong_lineage_scenario, "provider_result_reference"
    ),
    "wrong-request-plan-lineage": partial(
        _wrong_lineage_scenario, "provider_request_plan_reference"
    ),
    "wrong-provider-plan-lineage": partial(
        _wrong_lineage_scenario, "provider_result_identity"
    ),
    "wrong-execution-plan-lineage": partial(
        _wrong_lineage_scenario, "execution_plan_reference"
    ),
    "wrong-draft-lineage": partial(_wrong_lineage_scenario, "draft_reference"),
}

_SIMPLE_INVALID_CODES = {
    "malformed-extracted-result": ("extracted-result-invalid-reconstruction",),
    "malformed-extracted-response": ("extracted-result-invalid-reconstruction",),
    "malformed-extracted-message": ("extracted-result-invalid-reconstruction",),
    "malformed-openai-result": ("provider-result-invalid-openai-result",),
    "malformed-openai-response": ("provider-result-invalid-openai-result",),
    "malformed-openai-message": ("provider-result-invalid-openai-result",),
    "malformed-generic-result": ("provider-result-invalid-generic-result",),
    "malformed-validation-context": ("provider-result-invalid-context",),
    "placeholder-extracted-response": ("extracted-result-invalid-reconstruction",),
    "placeholder-extracted-message": ("extracted-result-invalid-reconstruction",),
    "placeholder-openai-response": ("provider-result-invalid-openai-result",),
    "placeholder-openai-message": ("provider-result-invalid-openai-result",),
    "nested-extra-field": ("extracted-result-invalid-reconstruction",),
}


def _subprocess_expected_codes():
    """Literal family mapping; individual tuples are frozen below by test collection."""
    expected = dict(_SIMPLE_INVALID_CODES)
    expected.update(
        {
            "response-omission": RESPONSE_EXPECTED_CODES[
                "zero-responses-for-one-request"
            ],
            "response-excess": RESPONSE_EXPECTED_CODES["two-responses-for-one-request"],
            "response-duplication": RESPONSE_EXPECTED_CODES[
                "duplicate-response-instance"
            ],
            "response-reordering": RESPONSE_EXPECTED_CODES[
                "reordered-responses-corrected-ordinals"
            ],
            "message-omission": MESSAGE_EXPECTED_CODES["zero-messages"],
            "message-excess": MESSAGE_EXPECTED_CODES["two-messages"],
            "message-duplication": MESSAGE_EXPECTED_CODES["duplicate-message-instance"],
            "message-reordering": MESSAGE_EXPECTED_CODES[
                "reordered-messages-corrected-ordinals"
            ],
        }
    )
    return expected


def _subprocess_scenario_payload(case_id):
    constructor = SUBPROCESS_SCENARIOS[case_id]
    issues = constructor()
    return {
        "scenario_id": case_id,
        "descriptor": {
            "scenario_id": case_id,
            "validator": "public-phase-6.3-validator",
            "boundary": case_id,
            "reconstruction": case_id.startswith(
                ("malformed", "placeholder", "nested")
            ),
            "contextual_authority": not case_id.startswith(
                ("malformed", "placeholder", "nested")
            ),
            "construction_fingerprint": _construction_fingerprint(
                constructor, "subprocess"
            ),
        },
        "diagnostics": _snapshot(issues),
    }


@pytest.fixture(scope="module")
def stable_subprocess_scenarios():
    code = (
        "import json,runpy,sys;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_exhaustive_freeze.py');"
        "print(json.dumps({case_id:n['_subprocess_scenario_payload'](case_id) "
        "for case_id in n['SUBPROCESS_SCENARIOS']},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=list))"
    )
    first = subprocess.check_output([sys.executable, "-c", code])
    second = subprocess.check_output([sys.executable, "-c", code])
    assert first == second
    return json.loads(first)


@pytest.mark.parametrize("case_id", SUBPROCESS_SCENARIOS)
def test_each_subprocess_scenario_is_stable_and_reports_its_descriptor(
    case_id, stable_subprocess_scenarios
):
    actual = stable_subprocess_scenarios[case_id]
    expected = json.loads(
        json.dumps(_subprocess_scenario_payload(case_id), default=list)
    )
    assert actual == expected
    assert actual["scenario_id"] == case_id
    assert actual["descriptor"]["scenario_id"] == case_id


def test_exact_44_subprocess_registry_and_unique_construction_fingerprints():
    assert len(SUBPROCESS_SCENARIOS) == 44
    assert tuple(SUBPROCESS_SCENARIOS) == tuple(dict.fromkeys(SUBPROCESS_SCENARIOS))
    fingerprints = {
        _construction_fingerprint(constructor, "subprocess")
        for constructor in SUBPROCESS_SCENARIOS.values()
    }
    assert len(fingerprints) == 44
    with pytest.raises(KeyError):
        SUBPROCESS_SCENARIOS["unknown-scenario"]()


def _caller_mutation_scenario(case_id):
    plan, extracted, context, openai, generic = _nonempty(True)
    if case_id.startswith("malformed-extracted"):
        payload = extracted.model_dump(mode="python")
        if case_id == "malformed-extracted-result":
            payload["hostile_extra"] = {"mutable": [case_id]}
        elif case_id == "malformed-extracted-response":
            payload["responses"] = [{"mutable": [case_id]}]
        else:
            payload["responses"][0]["messages"] = [{"mutable": [case_id]}]
        issues = validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
    elif case_id.startswith("malformed-openai"):
        payload = openai.model_dump(mode="python")
        if case_id == "malformed-openai-result":
            payload["hostile_extra"] = {"mutable": [case_id]}
        elif case_id == "malformed-openai-response":
            payload["responses"] = [{"mutable": [case_id]}]
        else:
            payload["responses"][0]["messages"] = [{"mutable": [case_id]}]
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "malformed-generic-result":
        payload = generic.model_dump(mode="python")
        payload["hostile_extra"] = {"mutable": [case_id]}
        issues = validate_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "malformed-validation-context":
        payload = context.model_dump(mode="python")
        payload["hostile_extra"] = {"mutable": [case_id]}
        issues = validate_provider_execution_result(
            generic, FREEZE["_ReturningModelDump"](payload)
        )
    elif case_id.startswith("forged-"):
        forged = {
            "forged-identity": "forged-openai-identity",
            "forged-fingerprint": "forged-openai-fingerprint",
            "forged-seal": "forged-openai-seal",
        }[case_id]
        value = openai
        field = forged.rsplit("-", 1)[1]
        if field == "identity":
            value = value.model_copy(
                update={
                    "identity": "scout:openai-provider-execution-result:" + "f" * 64
                }
            )
            value = value.model_copy(
                update={
                    "fingerprint": FREEZE[
                        "derive_openai_provider_execution_result_fingerprint"
                    ](value)
                }
            )
        elif field == "fingerprint":
            value = value.model_copy(update={"fingerprint": "f" * 64})
        else:
            value = value.model_copy(
                update={
                    "identity": "scout:openai-provider-execution-result:" + "f" * 64,
                    "fingerprint": "f" * 64,
                }
            )
        payload = value.model_dump(mode="python")
        payload["caller_mutable"] = {"values": [case_id]}
        # Keep the semantic model payload strict by exposing the mutable caller
        # value through a wrapper that returns a projection without that probe.
        projected = dict(payload)
        projected.pop("caller_mutable")
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](projected), context
        )
    elif case_id == "foreign-canonical-reference":
        foreign = _nonempty(False)[3]
        value = FREEZE["_seal_openai_result"](
            openai.model_copy(
                update={
                    "openai_provider_execution_result_reference": foreign.openai_provider_execution_result_reference
                }
            )
        )
        payload = value.model_dump(mode="python")
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id in {"foreign-empty-authority", "empty-nonempty-mismatch"}:
        value = _empty(f"caller-{case_id}")[3]
        payload = value.model_dump(mode="python")
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "response-cardinality-mismatch":
        payload = openai.model_dump(mode="python")
        payload["responses"] = payload["responses"] * 2
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "message-cardinality-mismatch":
        payload = openai.model_dump(mode="python")
        payload["responses"][0]["messages"] *= 2
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "placeholder-artifact":
        payload = openai.model_dump(mode="python")
        payload["responses"] = [{}]
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif case_id == "nested-extra-field":
        payload = extracted.model_dump(mode="python")
        payload["responses"][0]["messages"][0]["hostile_extra"] = {"mutable": [case_id]}
        issues = validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
    else:
        raise KeyError(case_id)
    return issues, payload


CALLER_MUTATION_CASE_IDS = (
    "malformed-extracted-result",
    "malformed-extracted-response",
    "malformed-extracted-message",
    "malformed-openai-result",
    "malformed-openai-response",
    "malformed-openai-message",
    "malformed-generic-result",
    "malformed-validation-context",
    "forged-identity",
    "forged-fingerprint",
    "forged-seal",
    "foreign-canonical-reference",
    "foreign-empty-authority",
    "empty-nonempty-mismatch",
    "response-cardinality-mismatch",
    "message-cardinality-mismatch",
    "placeholder-artifact",
    "nested-extra-field",
)
CALLER_MUTATION_SCENARIOS = {
    case_id: partial(_caller_mutation_scenario, case_id)
    for case_id in CALLER_MUTATION_CASE_IDS
}


def _deep_mutate(value):
    if isinstance(value, dict):
        for nested in tuple(value.values()):
            _deep_mutate(nested)
        value.clear()
        value["mutated"] = ["after-validation"]
    elif isinstance(value, list):
        for nested in tuple(value):
            _deep_mutate(nested)
        value.clear()
        value.append("after-validation")


@pytest.mark.parametrize("case_id", CALLER_MUTATION_SCENARIOS)
def test_complete_18_family_caller_mutation_matrix(case_id):
    issues, payload = CALLER_MUTATION_SCENARIOS[case_id]()
    before = _assert_complete(issues, CALLER_MUTATION_EXPECTED_CODES[case_id])
    _deep_mutate(payload)
    successful = _nonempty(True)
    assert validate_openai_provider_execution_result(successful[3], successful[2]) == ()
    assert _malformed_scenario("malformed-generic-result")
    assert _snapshot(issues) == before


def _scenario_value(value):
    return value


NESTED_EXTRA_FIELD_SCENARIOS = {
    "OpenAIExtractedExecutionResult": partial(
        _scenario_value, "extracted-execution-result"
    ),
    "OpenAIExtractedResponse": partial(_scenario_value, "extracted-response"),
    "OpenAIExtractedResponseMessage": partial(_scenario_value, "extracted-message"),
    "OpenAIProviderExecutionResult": partial(
        _scenario_value, "openai-execution-result"
    ),
    "OpenAIProviderResponse": partial(_scenario_value, "openai-response"),
    "OpenAIProviderResponseMessage": partial(_scenario_value, "openai-message"),
    "ProviderExecutionResult": partial(_scenario_value, "generic-result"),
    "ProviderExecutionResultValidationContext": partial(
        _scenario_value, "validation-context"
    ),
}


def _nested_extra_field_issues(case_id):
    legacy_id = NESTED_EXTRA_FIELD_SCENARIOS[case_id]()
    plan, extracted, context, openai, generic = _nonempty(True)
    hostile = {"nested": [["safe-value"]]}
    if legacy_id.startswith("extracted"):
        payload = extracted.model_dump(mode="python")
        target = payload
        if legacy_id == "extracted-response":
            target = payload["responses"][0]
        elif legacy_id == "extracted-message":
            target = payload["responses"][0]["messages"][0]
        target["hostile_extra"] = hostile
        issues = validate_openai_extracted_execution_result(
            FREEZE["_ReturningModelDump"](payload),
            plan,
            context.provider_mapping_validation_context,
        )
    elif legacy_id.startswith("openai"):
        payload = openai.model_dump(mode="python")
        target = payload
        if legacy_id == "openai-response":
            target = payload["responses"][0]
        elif legacy_id == "openai-message":
            target = payload["responses"][0]["messages"][0]
        target["hostile_extra"] = hostile
        issues = validate_openai_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    elif legacy_id == "generic-result":
        payload = generic.model_dump(mode="python")
        payload["hostile_extra"] = hostile
        issues = validate_provider_execution_result(
            FREEZE["_ReturningModelDump"](payload), context
        )
    else:
        payload = context.model_dump(mode="python")
        payload["hostile_extra"] = hostile
        issues = validate_provider_execution_result(
            generic, FREEZE["_ReturningModelDump"](payload)
        )
    return issues, hostile


@pytest.mark.parametrize("case_id", NESTED_EXTRA_FIELD_SCENARIOS)
def test_complete_named_nested_extra_field_registry(case_id):
    issues, hostile = _nested_extra_field_issues(case_id)
    before = _assert_complete(issues, NESTED_EXTRA_FIELD_EXPECTED_CODES[case_id])
    hostile["nested"][0].append("mutated")
    hostile["nested"].append(["new"])
    assert _snapshot(issues) == before


_PROCESS_EXCEPTIONS = (KeyboardInterrupt, SystemExit, GeneratorExit)
_PROCESS_BOUNDARIES = {
    "extracted": (
        "extracted-result-argument",
        "provider-plan-argument",
        "extracted-response-reconstruction",
        "extracted-message-reconstruction",
        "mapping-context-argument",
    ),
    "openai": (
        "submitted-result-argument",
        "validation-context-argument",
        "extracted-authority-in-context",
        "provider-plan-authority-in-context",
        "submitted-response-reconstruction",
        "submitted-message-reconstruction",
    ),
    "generic": (
        "generic-result-argument",
        "validation-context-argument",
        "concrete-openai-result-in-generic",
        "extracted-authority-in-context",
        "provider-plan-authority-in-context",
        "concrete-response-reconstruction",
        "concrete-message-reconstruction",
    ),
}


def _process_case(validator_name, boundary, error_type):
    error = error_type(f"{validator_name}:{boundary}")

    class _RaiseExact:
        def model_dump(self, **_kwargs):
            raise error

    hostile = _RaiseExact()
    plan, extracted, context, openai, generic = _nonempty(True)
    try:
        if validator_name == "extracted":
            if boundary == "provider-plan-argument":
                validate_openai_extracted_execution_result(
                    extracted, hostile, context.provider_mapping_validation_context
                )
            elif boundary == "mapping-context-argument":
                validate_openai_extracted_execution_result(extracted, plan, hostile)
            else:
                # Nested response/message reconstruction is reached through the
                # owning extracted-result public reconstruction boundary.
                validate_openai_extracted_execution_result(
                    hostile, plan, context.provider_mapping_validation_context
                )
        elif validator_name == "openai":
            if boundary == "validation-context-argument":
                validate_openai_provider_execution_result(openai, hostile)
            else:
                # Context-member and nested child reconstruction are reached
                # through their nearest owning public argument boundary.
                validate_openai_provider_execution_result(hostile, context)
        elif boundary == "validation-context-argument":
            validate_provider_execution_result(generic, hostile)
        else:
            validate_provider_execution_result(hostile, context)
    except _PROCESS_EXCEPTIONS as caught:
        assert caught is error
        return
    raise AssertionError("process-control exception was contained")


PROCESS_CONTROL_SCENARIOS = {
    f"{validator}-{boundary}-{error.__name__}": partial(
        _process_case, validator, boundary, error
    )
    for validator, boundaries in _PROCESS_BOUNDARIES.items()
    for boundary in boundaries
    for error in _PROCESS_EXCEPTIONS
}


@pytest.mark.parametrize("case_id", PROCESS_CONTROL_SCENARIOS)
def test_complete_expanded_process_control_matrix(case_id):
    PROCESS_CONTROL_SCENARIOS[case_id]()


ARTIFACT_SUBPROCESS_CASE_NAMES = (
    "OpenAIExtractedExecutionResult",
    "OpenAIExtractedResponse",
    "OpenAIExtractedResponseMessage",
    "OpenAIProviderExecutionResult",
    "OpenAIProviderResponse",
    "OpenAIProviderResponseMessage",
    "ProviderExecutionResult",
)


def _artifact_representation(case_id):
    _, extracted, _, openai, generic = _nonempty(True)
    artifacts = {
        "OpenAIExtractedExecutionResult": extracted,
        "OpenAIExtractedResponse": extracted.responses[0],
        "OpenAIExtractedResponseMessage": extracted.responses[0].messages[0],
        "OpenAIProviderExecutionResult": openai,
        "OpenAIProviderResponse": openai.responses[0],
        "OpenAIProviderResponseMessage": openai.responses[0].messages[0],
        "ProviderExecutionResult": generic,
    }
    value = artifacts[case_id]
    dump = value.model_dump(mode="json")
    canonical = value.canonical_json()
    reference_fields = (
        "extracted_execution_result_reference",
        "extracted_response_reference",
        "extracted_response_message_reference",
        "openai_provider_execution_result_reference",
        "provider_response_reference",
        "provider_response_message_reference",
        "provider_execution_result_reference",
    )
    reference = next(
        getattr(value, field) for field in reference_fields if hasattr(value, field)
    )
    nested_tuple_ordering = tuple(
        item.identity
        for item in getattr(value, "responses", getattr(value, "messages", ()))
    )
    return {
        "complete_model_dump": dump,
        "canonical_serializer_output": canonical,
        "identity": value.identity,
        "fingerprint": value.fingerprint,
        "canonical_reference": reference,
        "complete_seal_tuple": (value.identity, value.fingerprint),
        "nested_tuple_ordering": nested_tuple_ordering,
        "unicode_nfc": unicodedata.normalize("NFC", canonical),
        "str": str(value),
        "repr": repr(value),
    }


ARTIFACT_SUBPROCESS_SCENARIOS = {
    name: partial(_artifact_representation, name)
    for name in ARTIFACT_SUBPROCESS_CASE_NAMES
}


@pytest.mark.parametrize("case_id", ARTIFACT_SUBPROCESS_SCENARIOS)
def test_complete_ten_field_artifact_subprocess_representation(case_id):
    code = (
        "import json,runpy,sys;sys.path.insert(0,'tests');"
        "n=runpy.run_path('tests/test_editorial_script_composer_provider_results_exhaustive_freeze.py');"
        "print(json.dumps(n['_artifact_representation'](sys.argv[1]),sort_keys=True,separators=(',',':'),ensure_ascii=True))"
    )
    first = subprocess.check_output([sys.executable, "-c", code, case_id])
    second = subprocess.check_output([sys.executable, "-c", code, case_id])
    assert first == second
    assert json.loads(first) == json.loads(
        json.dumps(_artifact_representation(case_id))
    )
    assert len(json.loads(first)) == 10


EMPTY_LINEAGE_SCENARIOS = {
    case_id: partial(_lineage_scenario, case_id, artifact, field, foreign_field)
    for case_id, artifact, field, foreign_field in LINEAGE_CASES
}


@pytest.mark.parametrize("case_id", EMPTY_LINEAGE_SCENARIOS)
def test_empty_lineage_registry_has_complete_golden_diagnostics(case_id):
    first = EMPTY_LINEAGE_SCENARIOS[case_id]()
    second = EMPTY_LINEAGE_SCENARIOS[case_id]()
    assert first == second
    assert _assert_complete(first, LINEAGE_EXPECTED_CODES[case_id]) == _snapshot(second)


FOREIGN_EMPTY_EXPECTED_CODES = {
    "foreign-extracted-in-local-context": (
        "extracted-result-execution-draft-fingerprint-mismatch",
        "extracted-result-execution-draft-reference-mismatch",
        "extracted-result-execution-execution-plan-fingerprint-mismatch",
        "extracted-result-execution-execution-plan-identity-mismatch",
        "extracted-result-execution-execution-plan-reference-mismatch",
        "extracted-result-execution-extracted-execution-result-reference-mismatch",
        "extracted-result-execution-openai-request-plan-fingerprint-mismatch",
        "extracted-result-execution-openai-request-plan-identity-mismatch",
        "extracted-result-execution-openai-request-plan-reference-mismatch",
        "extracted-result-execution-provider-request-plan-fingerprint-mismatch",
        "extracted-result-execution-provider-request-plan-identity-mismatch",
        "extracted-result-execution-provider-request-plan-reference-mismatch",
    ),
    "local-extracted-in-foreign-context": (
        "extracted-result-execution-draft-fingerprint-mismatch",
        "extracted-result-execution-draft-reference-mismatch",
        "extracted-result-execution-execution-plan-fingerprint-mismatch",
        "extracted-result-execution-execution-plan-identity-mismatch",
        "extracted-result-execution-execution-plan-reference-mismatch",
        "extracted-result-execution-extracted-execution-result-reference-mismatch",
        "extracted-result-execution-openai-request-plan-fingerprint-mismatch",
        "extracted-result-execution-openai-request-plan-identity-mismatch",
        "extracted-result-execution-openai-request-plan-reference-mismatch",
        "extracted-result-execution-provider-request-plan-fingerprint-mismatch",
        "extracted-result-execution-provider-request-plan-identity-mismatch",
        "extracted-result-execution-provider-request-plan-reference-mismatch",
    ),
    "foreign-extracted-with-local-plan": ("provider-mapping-unknown-execution-plan",),
    "local-extracted-with-foreign-plan": ("provider-mapping-unknown-execution-plan",),
    "foreign-openai-in-local-context": (
        "provider-result-unknown-provider-request-plan",
    ),
    "local-openai-in-foreign-context": (
        "provider-result-unknown-provider-request-plan",
    ),
    "foreign-generic-in-local-context": (
        "provider-result-unknown-provider-request-plan",
    ),
    "local-generic-in-foreign-context": (
        "provider-result-unknown-provider-request-plan",
    ),
    "foreign-openai-in-local-generic": (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-unknown-provider-request-plan",
    ),
    "local-openai-in-foreign-generic": (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-unknown-provider-request-plan",
    ),
    "foreign-plan-in-local-context": ("provider-result-unknown-provider-request-plan",),
    "foreign-mapping-context-for-local-extracted": (
        "provider-mapping-unknown-execution-plan",
    ),
    "foreign-extracted-context-member": (
        "provider-result-unresolved-extracted-authority",
    ),
    "foreign-plan-context-member": ("provider-result-unknown-provider-request-plan",),
    "foreign-plan-and-extracted-context-members": (
        "provider-result-unknown-provider-request-plan",
    ),
    "foreign-openai-context-authority": ("provider-mapping-unknown-execution-plan",),
    "foreign-generic-concrete-authority": (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-generic-provider-result-fingerprint-mismatch",
        "provider-result-generic-provider-result-identity-mismatch",
        "provider-result-generic-provider-result-reference-mismatch",
        "provider-result-unknown-provider-request-plan",
    ),
}
FOREIGN_EMPTY_SCENARIOS = {
    case_id: partial(_foreign_empty_scenario, case_id)
    for case_id in FOREIGN_EMPTY_CASES
}


@pytest.mark.parametrize("case_id", FOREIGN_EMPTY_SCENARIOS)
def test_foreign_empty_registry_has_complete_golden_diagnostics(case_id):
    first = FOREIGN_EMPTY_SCENARIOS[case_id]()
    second = FOREIGN_EMPTY_SCENARIOS[case_id]()
    assert first == second
    assert _assert_complete(first, FOREIGN_EMPTY_EXPECTED_CODES[case_id]) == _snapshot(
        second
    )


SUBPROCESS_EXPECTED_CODES = {
    **_SIMPLE_INVALID_CODES,
    "forged-extracted-identity": ("extracted-result-invalid-execution-identity",),
    "forged-extracted-fingerprint": ("extracted-result-invalid-execution-fingerprint",),
    "forged-extracted-seal": (
        "extracted-result-invalid-execution-fingerprint",
        "extracted-result-invalid-execution-identity",
    ),
    "forged-openai-identity": ("provider-result-invalid-openai-result-identity",),
    "forged-openai-fingerprint": ("provider-result-invalid-openai-result-fingerprint",),
    "forged-openai-seal": (
        "provider-result-invalid-openai-result-fingerprint",
        "provider-result-invalid-openai-result-identity",
    ),
    "forged-generic-identity": ("provider-result-invalid-generic-result-identity",),
    "forged-generic-fingerprint": (
        "provider-result-invalid-generic-result-fingerprint",
    ),
    "forged-generic-seal": (
        "provider-result-invalid-generic-result-fingerprint",
        "provider-result-invalid-generic-result-identity",
    ),
    "foreign-extracted-canonical-reference": (
        "extracted-result-execution-extracted-execution-result-reference-mismatch",
    ),
    "foreign-openai-canonical-reference": (
        "provider-result-openai-openai-provider-execution-result-reference-mismatch",
    ),
    "foreign-generic-canonical-reference": (
        "provider-result-generic-provider-execution-result-reference-mismatch",
    ),
    "foreign-empty-extracted-authority": FOREIGN_EMPTY_EXPECTED_CODES[
        "foreign-extracted-in-local-context"
    ],
    "foreign-empty-openai-result": ("provider-result-unknown-provider-request-plan",),
    "foreign-empty-generic-result": ("provider-result-unknown-provider-request-plan",),
    "extracted-empty-nonempty-mismatch": ("extracted-result-output-count-mismatch",),
    "openai-empty-nonempty-mismatch": (
        "provider-result-unknown-provider-request-plan",
    ),
    "generic-empty-nonempty-mismatch": (
        "provider-result-generic-openai-execution-result-mismatch",
        "provider-result-unknown-provider-request-plan",
    ),
    "response-omission": RESPONSE_EXPECTED_CODES["zero-responses-for-one-request"],
    "response-excess": RESPONSE_EXPECTED_CODES["two-responses-for-one-request"],
    "response-duplication": RESPONSE_EXPECTED_CODES["duplicate-response-instance"],
    "response-reordering": RESPONSE_EXPECTED_CODES[
        "reordered-responses-corrected-ordinals"
    ],
    "message-omission": MESSAGE_EXPECTED_CODES["zero-messages"],
    "message-excess": MESSAGE_EXPECTED_CODES["two-messages"],
    "message-duplication": MESSAGE_EXPECTED_CODES["duplicate-message-instance"],
    "message-reordering": MESSAGE_EXPECTED_CODES[
        "reordered-messages-corrected-ordinals"
    ],
    "wrong-provider-ownership": (
        "provider-result-generic-provider-result-reference-mismatch",
    ),
    "wrong-request-plan-lineage": ("provider-result-unknown-provider-request-plan",),
    "wrong-provider-plan-lineage": (
        "provider-result-generic-provider-result-identity-mismatch",
    ),
    "wrong-execution-plan-lineage": (
        "provider-result-generic-execution-plan-reference-mismatch",
    ),
    "wrong-draft-lineage": ("provider-result-generic-draft-reference-mismatch",),
}

CALLER_MUTATION_EXPECTED_CODES = {
    "malformed-extracted-result": ("extracted-result-invalid-reconstruction",),
    "malformed-extracted-response": ("extracted-result-invalid-reconstruction",),
    "malformed-extracted-message": ("extracted-result-invalid-reconstruction",),
    "malformed-openai-result": ("provider-result-invalid-openai-result",),
    "malformed-openai-response": ("provider-result-invalid-openai-result",),
    "malformed-openai-message": ("provider-result-invalid-openai-result",),
    "malformed-generic-result": ("provider-result-invalid-generic-result",),
    "malformed-validation-context": ("provider-result-invalid-context",),
    "forged-identity": ("provider-result-invalid-openai-result-identity",),
    "forged-fingerprint": ("provider-result-invalid-openai-result-fingerprint",),
    "forged-seal": (
        "provider-result-invalid-openai-result-fingerprint",
        "provider-result-invalid-openai-result-identity",
    ),
    "foreign-canonical-reference": (
        "provider-result-openai-openai-provider-execution-result-reference-mismatch",
    ),
    "foreign-empty-authority": ("provider-result-unknown-provider-request-plan",),
    "empty-nonempty-mismatch": ("provider-result-unknown-provider-request-plan",),
    "response-cardinality-mismatch": (
        "provider-result-duplicate-openai-request-identity",
        "provider-result-duplicate-openai-request-reference",
        "provider-result-duplicate-response-identity",
        "provider-result-duplicate-response-ordinal",
        "provider-result-duplicate-response-reference",
        "provider-result-extra-response",
        "provider-result-invalid-openai-result-fingerprint",
        "provider-result-invalid-openai-result-identity",
    ),
    "message-cardinality-mismatch": MESSAGE_EXPECTED_CODES["two-messages"],
    "placeholder-artifact": ("provider-result-invalid-openai-result",),
    "nested-extra-field": ("extracted-result-invalid-reconstruction",),
}

NESTED_EXTRA_FIELD_EXPECTED_CODES = {
    "OpenAIExtractedExecutionResult": ("extracted-result-invalid-reconstruction",),
    "OpenAIExtractedResponse": ("extracted-result-invalid-reconstruction",),
    "OpenAIExtractedResponseMessage": ("extracted-result-invalid-reconstruction",),
    "OpenAIProviderExecutionResult": ("provider-result-invalid-openai-result",),
    "OpenAIProviderResponse": ("provider-result-invalid-openai-result",),
    "OpenAIProviderResponseMessage": ("provider-result-invalid-openai-result",),
    "ProviderExecutionResult": ("provider-result-invalid-generic-result",),
    "ProviderExecutionResultValidationContext": ("provider-result-invalid-context",),
}


def _annotate_registry(registry, expected, *, validator, boundary, reconstruction):
    for case_id, constructor in registry.items():
        constructor.scenario_id = case_id
        constructor.expected_codes = expected.get(case_id, ())
        constructor.validator = validator
        constructor.public_boundary = boundary
        constructor.tests_reconstruction = reconstruction
        constructor.tests_contextual_authority = not reconstruction


_annotate_registry(
    RESPONSE_CARDINALITY_SCENARIOS,
    RESPONSE_EXPECTED_CODES,
    validator="validate_openai_provider_execution_result",
    boundary="submitted-response-collection",
    reconstruction=False,
)
_annotate_registry(
    MESSAGE_CARDINALITY_SCENARIOS,
    MESSAGE_EXPECTED_CODES,
    validator="validate_openai_provider_execution_result",
    boundary="submitted-message-collection",
    reconstruction=False,
)
_annotate_registry(
    EMPTY_LINEAGE_SCENARIOS,
    LINEAGE_EXPECTED_CODES,
    validator="phase-6.3-public-validator",
    boundary="empty-lineage",
    reconstruction=False,
)
_annotate_registry(
    FOREIGN_EMPTY_SCENARIOS,
    FOREIGN_EMPTY_EXPECTED_CODES,
    validator="phase-6.3-public-validator",
    boundary="foreign-empty-authority",
    reconstruction=False,
)
_annotate_registry(
    SUBPROCESS_SCENARIOS,
    SUBPROCESS_EXPECTED_CODES,
    validator="phase-6.3-public-validator",
    boundary="fresh-python-process",
    reconstruction=True,
)
_annotate_registry(
    CALLER_MUTATION_SCENARIOS,
    CALLER_MUTATION_EXPECTED_CODES,
    validator="phase-6.3-public-validator",
    boundary="caller-owned-payload",
    reconstruction=True,
)
_annotate_registry(
    NESTED_EXTRA_FIELD_SCENARIOS,
    NESTED_EXTRA_FIELD_EXPECTED_CODES,
    validator="nearest-phase-6.3-public-validator",
    boundary="nested-model-reconstruction",
    reconstruction=True,
)
_annotate_registry(
    PROCESS_CONTROL_SCENARIOS,
    {},
    validator="phase-6.3-public-validator",
    boundary="logical-or-nearest-reachable-reconstruction",
    reconstruction=True,
)
_annotate_registry(
    ARTIFACT_SUBPROCESS_SCENARIOS,
    {},
    validator="not-applicable-representation-comparison",
    boundary="fresh-python-process",
    reconstruction=False,
)


@pytest.mark.parametrize("case_id", SUBPROCESS_SCENARIOS)
def test_all_subprocess_scenarios_have_explicit_golden_diagnostics(case_id):
    _assert_complete(
        SUBPROCESS_SCENARIOS[case_id](), SUBPROCESS_EXPECTED_CODES[case_id]
    )


META_INTEGRITY_SAFEGUARDS = (
    "explicit-constructor-per-id",
    "unknown-id-rejected",
    "response-constructor-isolation",
    "message-constructor-isolation",
    "subprocess-constructor-specificity",
    "lineage-registry-separation",
    "caller-mutation-collection",
    "nested-extra-field-collection",
    "process-control-collection",
    "explicit-golden-code-tuples",
    "diagnostic-structure-assertions",
    "subprocess-descriptor-identity",
)


@pytest.mark.parametrize("safeguard", META_INTEGRITY_SAFEGUARDS)
def test_complete_meta_integrity_matrix(safeguard):
    counts = {
        "subprocess": len(SUBPROCESS_SCENARIOS),
        "caller": len(CALLER_MUTATION_SCENARIOS),
        "nested": len(NESTED_EXTRA_FIELD_SCENARIOS),
        "response": len(RESPONSE_CARDINALITY_SCENARIOS),
        "message": len(MESSAGE_CARDINALITY_SCENARIOS),
        "lineage": len(EMPTY_LINEAGE_SCENARIOS),
        "foreign": len(FOREIGN_EMPTY_SCENARIOS),
        "process": len(PROCESS_CONTROL_SCENARIOS),
        "artifact": len(ARTIFACT_SUBPROCESS_SCENARIOS),
        "meta": len(META_INTEGRITY_SAFEGUARDS),
    }
    assert counts == {
        "subprocess": 44,
        "caller": 18,
        "nested": 8,
        "response": 16,
        "message": 20,
        "lineage": 17,
        "foreign": 17,
        "process": 54,
        "artifact": 7,
        "meta": 12,
    }
    assert len(SUBPROCESS_EXPECTED_CODES) == 44
    assert all(
        isinstance(value, tuple) and value
        for value in SUBPROCESS_EXPECTED_CODES.values()
    )
    assert set(RESPONSE_CARDINALITY_SCENARIOS) == set(RESPONSE_EXPECTED_CODES)
    assert set(MESSAGE_CARDINALITY_SCENARIOS) == set(MESSAGE_EXPECTED_CODES)
    assert set(EMPTY_LINEAGE_SCENARIOS) == set(LINEAGE_EXPECTED_CODES)
    assert set(FOREIGN_EMPTY_SCENARIOS) == set(FOREIGN_EMPTY_EXPECTED_CODES)
    assert EMPTY_LINEAGE_SCENARIOS is not FOREIGN_EMPTY_SCENARIOS
    for registry in (
        SUBPROCESS_SCENARIOS,
        CALLER_MUTATION_SCENARIOS,
        NESTED_EXTRA_FIELD_SCENARIOS,
        RESPONSE_CARDINALITY_SCENARIOS,
        MESSAGE_CARDINALITY_SCENARIOS,
        EMPTY_LINEAGE_SCENARIOS,
        FOREIGN_EMPTY_SCENARIOS,
        PROCESS_CONTROL_SCENARIOS,
        ARTIFACT_SUBPROCESS_SCENARIOS,
    ):
        assert len({id(constructor) for constructor in registry.values()}) == len(
            registry
        )
        for case_id, constructor in registry.items():
            assert constructor.scenario_id == case_id
            assert hasattr(constructor, "expected_codes")
            assert constructor.validator
            assert constructor.public_boundary
    assert safeguard in META_INTEGRITY_SAFEGUARDS


# Frozen full-structure digests cover count, ordered codes, artifact/field/path,
# message keys, related references, asdict, canonical diagnostic JSON, str, and repr.
FULL_DIAGNOSTIC_GOLDEN_SHA256 = {
    "caller:empty-nonempty-mismatch": "114b49f06493210104b895f33947e695c68f0f855b69c3eb7b0a3c7790832916",
    "caller:foreign-canonical-reference": "2024e0f7947910bd192d236c8de9137dcd3f37f8bfb2ed67fdad52b0984f292d",
    "caller:foreign-empty-authority": "70e4a0343f3aab9bab352a2bfa786d014cf81c986a3f8ae95251fe35a83e5e8b",
    "caller:forged-fingerprint": "9b607e80620fad87913ee4c48b563aca418b026701177b732707a125822922e4",
    "caller:forged-identity": "919237a95591560cf7d5b8db112b38dc82071920a9b11d7f4a58731f67d2522b",
    "caller:forged-seal": "8e8dd09abadaa18ffb1c2d1367447ab527ed870d1599371adea12f4511441d2c",
    "caller:malformed-extracted-message": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "caller:malformed-extracted-response": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "caller:malformed-extracted-result": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "caller:malformed-generic-result": "119ee454350720081576d1cd0900784a3fb86a688696aacde813fb2ed80dcd32",
    "caller:malformed-openai-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "caller:malformed-openai-response": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "caller:malformed-openai-result": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "caller:malformed-validation-context": "849513b6b1516320693262ef447b5fc982e8e22c06e796131b4d30445e90e72e",
    "caller:message-cardinality-mismatch": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "caller:nested-extra-field": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "caller:placeholder-artifact": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "caller:response-cardinality-mismatch": "1a1f9feef4e4dd074db3c2fce71aeb8f8b6ae8a6ce224061433aabb3c86f5516",
    "empty:draft-fingerprint": "a979d860572bd81fd5a07463ecf11a3cf692ea15e941bf62060c439ead7e8388",
    "empty:draft-identity": "3976cd262fca191b8db9e0b5a1118e213a3f4da0848bf7c6b3758c3e53eea052",
    "empty:execution-plan-fingerprint": "789145cc10993efce83fa603d8dfdf9c850a0277ff3203ff6d3ba7aa74e30e49",
    "empty:execution-plan-identity": "f640d61df49200a496a6872d35d4a3f6a21106f5a6cfd04651bf6aee49faf741",
    "empty:extracted-result-fingerprint": "cb12e262bd0d161e92b48f3b88d8715c24f0063c3563d9f84f0c114263a2dce3",
    "empty:extracted-result-identity": "8f9bcdb4a15c8cf60b93fa9ab000d78d38b1225dfe8ac8c61f3aeaef6de1fa19",
    "empty:extracted-result-reference": "c9d99b22de4f8417b866d08d3f8eb490ab54b31ca4f221a5639975addc073457",
    "empty:generic-concrete-fingerprint": "ed7f2b597e15d58d9b4252a5147cb40adc3ea82a6a22bb5cc14c37f89632c943",
    "empty:generic-concrete-identity": "0fe09a951be9616445847662c28a01271ed29ff317134eab55a909ac4487fd6d",
    "empty:generic-concrete-reference": "6add75a47cfa37f50650d8211bd2df6e8c452621037b8bc2812246a6a9083286",
    "empty:openai-plan-fingerprint": "95cb29906a4f135a3f79d308f2bc1e362f4fcf49d908057fcd15f9bf9e843ccc",
    "empty:openai-plan-identity": "b458e471708161fc243e425834ca3b737b46e5f038f3d9feb06e0bd0bbe3a8d0",
    "empty:openai-result-fingerprint": "c04cd1c37f87990cb76c3957c6047aba3ac6e3373edb60e996e516c19eb684e8",
    "empty:openai-result-identity": "c2488356770ea7a93ed0787d47296c58a615cee06f580432db1129eb30e72360",
    "empty:openai-result-reference": "d0e10d6b8059eaa053b8f40277711e4c9bb7688253ff9240b193fd96c649bdc2",
    "empty:provider-plan-fingerprint": "135eaa37b6b626a73e9c15dd33280cfe53be12d80c26c890a98cee30268cd84c",
    "empty:provider-plan-identity": "605f0c2fec1af5a0ae9aa6d38a92f94c91e52a678567f199ed584b01ccf6f281",
    "foreign:foreign-extracted-context-member": "644842120f3b3c71372090b4c9d0a56f253600902f089883a3250775a536f983",
    "foreign:foreign-extracted-in-local-context": "60861b133a4fe199465d1ad72396c850fcc88d2f6c9c25e60f2a537548fac1fa",
    "foreign:foreign-extracted-with-local-plan": "d2e0897fd61cbb50d8409a4a7e667238d57479c5869ca619c50a65c45ffbdf4f",
    "foreign:foreign-generic-concrete-authority": "a50b00a36952fcdcf80a949a8d8afeefcb5534647892b67d44eb91d14ae7d692",
    "foreign:foreign-generic-in-local-context": "73a478f56753dd242cda9c9e2aef767572be436dd15e371ac9faef73b487c7de",
    "foreign:foreign-mapping-context-for-local-extracted": "85516f5c646092f93053c7c50b1e477be510b5f0491f01e21f659ed8711cbcf6",
    "foreign:foreign-openai-context-authority": "3de3969bbac14844c399493b4656d1699255387b130a5ddee29e704050ef0cde",
    "foreign:foreign-openai-in-local-context": "88c123c0f83eb4c1f8d57a8159a7fd482dbe318a830bd291df0cb338242fc384",
    "foreign:foreign-openai-in-local-generic": "04d83ec96e7b2c374eeec34d4e688c238e84fd06432ca1b5a0187a92bfab3a58",
    "foreign:foreign-plan-and-extracted-context-members": "9a8ece1a8c0baf41d2bb8a8d56dff6b14c1c1e4a8a711933da2c1ee09dda9540",
    "foreign:foreign-plan-context-member": "b07a093a6bb461b9ee3153aee5c954d7ee69f741d22c8b4fc01f9b85337cc7d4",
    "foreign:foreign-plan-in-local-context": "f00d978cae8e00a35cd4ef39d5a8aa60d7a682a0612e7b8d9536c5b107695a44",
    "foreign:local-extracted-in-foreign-context": "2f98bd4eeceda8874118eb83a084cee483f963ffffd88910fdbd3b69b5ed52ec",
    "foreign:local-extracted-with-foreign-plan": "ca4d576bb3862c84e87c706e05232907e5f2eb89e975bc4528fe4925b79d7300",
    "foreign:local-generic-in-foreign-context": "37562cb8a2a0036fd19a7ab70a4e079e542df3b143f2a96aa8fe135553e1ed9d",
    "foreign:local-openai-in-foreign-context": "6c0789f56d623d2149146cbe80b63ec7a0da155530818aadd13768520539e345",
    "foreign:local-openai-in-foreign-generic": "1489cddd1942f59eff2633958c4bae4c2319ffc3bcf73bf4bc86baf768a6280e",
    "message:duplicate-message-instance": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "message:empty-mapping-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:independently-valid-foreign-message": "63278ecd6e53e7d289c7ef2c6a7e34359f3352186276be6f60ead80592295efb",
    "message:message-collection-as-list": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "message:message-collection-as-set": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:message-collection-none": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:message-collection-omitted": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:message-tuple-containing-malformed-mapping": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:message-tuple-containing-none": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:minimally-shaped-authority-free-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:nearest-reachable-foreign-message-substitution": "63278ecd6e53e7d289c7ef2c6a7e34359f3352186276be6f60ead80592295efb",
    "message:placeholder-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "message:reordered-messages-corrected-ordinals": "906f92e17f793922b7ac6b0acd2d49e0a549e77392666be0404d0aa8164d4908",
    "message:two-messages": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "message:wrong-extracted-result-ownership": "fbd7519360d53500d07d0044641bfda6ba12c18d803dd8e9566227c5392c8721",
    "message:wrong-finish-reason-authority": "36bc15dffb9ffdd2fed67248a2672bda242c4bbfb2397f75e3c2b3c1917536f8",
    "message:wrong-generated-text-authority": "d8aa3a69171f9cfbe34fc6e1ebdaf8393bfb7609267fd468ac815bceb75a4996",
    "message:wrong-request-ownership": "9dd9d7bfe92ae9f43b41ab65df59363cdb881025c9c4812492960e7f4817eb93",
    "message:wrong-response-ownership": "fb77b9836a70cbe37cd2efe4c8eed3bef257862a98d52a3bada691e77e302834",
    "message:zero-messages": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "response:duplicate-response-instance": "1c34728a8bdfedb01ed368b757d135a887a8a3f69cc5662c2a5b2e7ccf8298a0",
    "response:empty-request-set-one-response": "26837b10eb9d94e1630d001925900d79395f849f7037f82fd28f5073be870979",
    "response:independently-valid-foreign-response": "bc309199a7b61fe0d1f174eac63e0e00b33dcc713550d447126a1526b1b5ab9d",
    "response:malformed-response-container": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "response:nearest-reachable-foreign-response-substitution": "bc309199a7b61fe0d1f174eac63e0e00b33dcc713550d447126a1526b1b5ab9d",
    "response:nonempty-request-set-zero-responses": "aeba65fdbea7482e6ed881bb56bbcab651479d2e22253c1db3df39242ad1049b",
    "response:placeholder-response": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "response:reordered-responses-corrected-ordinals": "68cf3694d519af4fad88ca775cae48f20c5bbade8a69f77630a2319b7794f467",
    "response:response-tuple-containing-malformed-mapping": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "response:response-tuple-containing-none": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "response:two-responses-for-one-request": "1c34728a8bdfedb01ed368b757d135a887a8a3f69cc5662c2a5b2e7ccf8298a0",
    "response:wrong-draft-ownership": "d070ca1612199678cf692d79e678cf9b0b79a116a266767acdde9992d90fa202",
    "response:wrong-execution-plan-ownership": "3ce6fd18a4d7b85882b35bc0552f353917d912c1c055d64a6b3405811c2f564f",
    "response:wrong-provider-plan-ownership": "7afe3a65a5951c427ba0bee80bbc906a147e012927d492ed27fdeac19d2a86f8",
    "response:wrong-request-ownership": "796d781eb08f660a0adaaeb6a06da334bb29737909083956b9874215ec271bfa",
    "response:zero-responses-for-one-request": "aeba65fdbea7482e6ed881bb56bbcab651479d2e22253c1db3df39242ad1049b",
    "subprocess:extracted-empty-nonempty-mismatch": "bc81a1723ca1fdc448a64c65191783109415f1753bd3c5060700e8e8ed2071ef",
    "subprocess:foreign-empty-extracted-authority": "60861b133a4fe199465d1ad72396c850fcc88d2f6c9c25e60f2a537548fac1fa",
    "subprocess:foreign-empty-generic-result": "73a478f56753dd242cda9c9e2aef767572be436dd15e371ac9faef73b487c7de",
    "subprocess:foreign-empty-openai-result": "88c123c0f83eb4c1f8d57a8159a7fd482dbe318a830bd291df0cb338242fc384",
    "subprocess:foreign-extracted-canonical-reference": "2c3f83fe964ade5a42cc181988e0748d47305ef7046fb5d0177c86b6793820bc",
    "subprocess:foreign-generic-canonical-reference": "ede4e98266df128125ef8327774cb5d68f85c48ae70bfefc41df21db7653e0ce",
    "subprocess:foreign-openai-canonical-reference": "2024e0f7947910bd192d236c8de9137dcd3f37f8bfb2ed67fdad52b0984f292d",
    "subprocess:forged-extracted-fingerprint": "629656686b0f5bf724a281e48ab84b6a80f0d009e75191117441d8ecd5ef7940",
    "subprocess:forged-extracted-identity": "4d697eea3d56dee5df560afab41d86c11b78b043fcada4d21a87c01ae54893a2",
    "subprocess:forged-extracted-seal": "bf139bd63f640654ae7bc66946d654d1fa61abe030867bd1bd5d05ef4c47b9ed",
    "subprocess:forged-generic-fingerprint": "4ec0804081f3f05a6dd2009ccee304ef0ad99d13c34d61f8714e20e6754db70d",
    "subprocess:forged-generic-identity": "d75940f565c8ff86e6141089b87709b57aca560be9d95de86ada4584e446346f",
    "subprocess:forged-generic-seal": "961b12796ac36a15b5fb678a90939a860cb4a0ad3cad6fe1c4509a62fd89151c",
    "subprocess:forged-openai-fingerprint": "9b607e80620fad87913ee4c48b563aca418b026701177b732707a125822922e4",
    "subprocess:forged-openai-identity": "919237a95591560cf7d5b8db112b38dc82071920a9b11d7f4a58731f67d2522b",
    "subprocess:forged-openai-seal": "8e8dd09abadaa18ffb1c2d1367447ab527ed870d1599371adea12f4511441d2c",
    "subprocess:generic-empty-nonempty-mismatch": "50f4593023ff5a3cc10fb5013f6279a1ea93f85a5ca17937e8e6225f15b7def3",
    "subprocess:malformed-extracted-message": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:malformed-extracted-response": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:malformed-extracted-result": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:malformed-generic-result": "119ee454350720081576d1cd0900784a3fb86a688696aacde813fb2ed80dcd32",
    "subprocess:malformed-openai-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:malformed-openai-response": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:malformed-openai-result": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:malformed-validation-context": "849513b6b1516320693262ef447b5fc982e8e22c06e796131b4d30445e90e72e",
    "subprocess:message-duplication": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "subprocess:message-excess": "29938e236b0288956094e139ca84bde32be606a1b08fc8bba86b8af8a9bf3bde",
    "subprocess:message-omission": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:message-reordering": "906f92e17f793922b7ac6b0acd2d49e0a549e77392666be0404d0aa8164d4908",
    "subprocess:nested-extra-field": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:openai-empty-nonempty-mismatch": "26837b10eb9d94e1630d001925900d79395f849f7037f82fd28f5073be870979",
    "subprocess:placeholder-extracted-message": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:placeholder-extracted-response": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "subprocess:placeholder-openai-message": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:placeholder-openai-response": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "subprocess:response-duplication": "1c34728a8bdfedb01ed368b757d135a887a8a3f69cc5662c2a5b2e7ccf8298a0",
    "subprocess:response-excess": "1c34728a8bdfedb01ed368b757d135a887a8a3f69cc5662c2a5b2e7ccf8298a0",
    "subprocess:response-omission": "aeba65fdbea7482e6ed881bb56bbcab651479d2e22253c1db3df39242ad1049b",
    "subprocess:response-reordering": "68cf3694d519af4fad88ca775cae48f20c5bbade8a69f77630a2319b7794f467",
    "subprocess:wrong-draft-lineage": "2a642eb01225ae275a85047a8dc1965872e70e778e7ce651d7a4341446b01321",
    "subprocess:wrong-execution-plan-lineage": "72fa89cd03cd5397f089c7214088e48c531853b86f42f322fe14a0f6ad22d460",
    "subprocess:wrong-provider-ownership": "edfa8fdf839b8b9ba32c261e5e93427b6b2474115c15135c21f5f0cc972f9e19",
    "subprocess:wrong-provider-plan-lineage": "16191b2428c5e1cb0882f6bc3864e63105f5cef5a85210d769170796de535a13",
    "subprocess:wrong-request-plan-lineage": "18e1f5aeec177f00cd58d838892974f2860fb1b725969ef5782c7a042819ae27",
}


def _golden_issues(case_key):
    family, case_id = case_key.split(":", 1)
    registries = {
        "subprocess": SUBPROCESS_SCENARIOS,
        "response": RESPONSE_CARDINALITY_SCENARIOS,
        "message": MESSAGE_CARDINALITY_SCENARIOS,
        "empty": EMPTY_LINEAGE_SCENARIOS,
        "foreign": FOREIGN_EMPTY_SCENARIOS,
    }
    if family == "caller":
        return CALLER_MUTATION_SCENARIOS[case_id]()[0]
    return registries[family][case_id]()


@pytest.mark.parametrize("case_key", FULL_DIAGNOSTIC_GOLDEN_SHA256)
def test_complete_diagnostic_structures_match_frozen_golden_sha256(case_key):
    serialized = json.dumps(
        _snapshot(_golden_issues(case_key)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=list,
    ).encode()
    assert (
        hashlib.sha256(serialized).hexdigest()
        == FULL_DIAGNOSTIC_GOLDEN_SHA256[case_key]
    )


NESTED_DIAGNOSTIC_GOLDEN_SHA256 = {
    "OpenAIExtractedExecutionResult": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "OpenAIExtractedResponse": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "OpenAIExtractedResponseMessage": "fbed4ce61c5c6dc84a56501d43092181a975474397e1a3defdad30af227803f6",
    "OpenAIProviderExecutionResult": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "OpenAIProviderResponse": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "OpenAIProviderResponseMessage": "f0e06462922586c7b724cb90d09955f5dc484de9b6bf35630e670f8a766fe39e",
    "ProviderExecutionResult": "119ee454350720081576d1cd0900784a3fb86a688696aacde813fb2ed80dcd32",
    "ProviderExecutionResultValidationContext": "849513b6b1516320693262ef447b5fc982e8e22c06e796131b4d30445e90e72e",
}


@pytest.mark.parametrize("case_id", NESTED_DIAGNOSTIC_GOLDEN_SHA256)
def test_nested_diagnostic_structures_match_frozen_golden_sha256(case_id):
    issues, _hostile = _nested_extra_field_issues(case_id)
    serialized = json.dumps(
        _snapshot(issues),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=list,
    ).encode()
    assert (
        hashlib.sha256(serialized).hexdigest()
        == NESTED_DIAGNOSTIC_GOLDEN_SHA256[case_id]
    )
