"""M6C.6B.2 Part 2 executor-request transport compatibility tests."""

import json

import pytest
from pydantic import ValidationError
from test_capability_execution_planning_input import _lineage
from test_corrective_action_execution_dispatch_contracts import _context

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorRequestV2,
    build_corrective_action_executor_request_v2,
    build_executor_request_v2_report,
    serialize_executor_request_v2_report,
    validate_executor_request_v2,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    build_draft_revision_executor_descriptor,
)


def _transport():
    *_, planning_input, _request_v2, _plan_v2, planning_result = _lineage()
    context = _context(CorrectiveActionAuthorizationState.NOT_REQUIRED)
    executor_request = build_corrective_action_executor_request_v2(
        planning_result,
        build_draft_revision_executor_descriptor(),
        context,
    )
    return planning_input, planning_result, context, executor_request


def test_v1_executor_request_shape_fingerprint_and_serialization_are_unchanged():
    _, planning_result, context, request_v2 = _transport()
    legacy = request_v2.legacy_request
    rebuilt = CorrectiveActionExecutorRequest.build(
        planning_result=planning_result.legacy_result,
        plan=planning_result.legacy_result.plan,
        executor_descriptor=legacy.executor_descriptor,
        execution_context=context,
    )

    assert rebuilt.request_fingerprint == legacy.request_fingerprint
    assert json.dumps(rebuilt.model_dump(mode="json"), sort_keys=True) == json.dumps(
        legacy.model_dump(mode="json"), sort_keys=True
    )
    assert "planning_input" not in legacy.model_dump(mode="python")


def test_v2_preserves_exact_planning_and_nested_revision_identities():
    planning_input, planning_result, context, request = _transport()

    assert request.planning_result is planning_result
    assert request.planning_input is planning_result.planning_input
    assert request.planning_input is planning_input
    assert request.execution_context is context
    assert request.planning_input.source_draft is planning_input.source_draft
    assert request.planning_input.revision_scope is planning_input.revision_scope
    assert request.planning_input.revision_policy is planning_input.revision_policy
    assert (
        request.planning_input.revision_instructions
        is planning_input.revision_instructions
    )
    validate_executor_request_v2(request)


def test_v2_transport_fingerprints_are_deterministic():
    first = _transport()[3]
    second = _transport()[3]
    assert first.request_fingerprint == second.request_fingerprint
    assert (
        first.planning_input.input_fingerprint
        == second.planning_input.input_fingerprint
    )


def test_planning_result_and_input_identity_mismatch_fails_closed():
    _, first_result, _, first_request = _transport()
    second_input, _, _, _ = _transport()
    with pytest.raises(ValidationError, match="identity"):
        CorrectiveActionExecutorRequestV2.build(
            legacy_request=first_request.legacy_request,
            planning_result=first_result,
            planning_input=second_input,
        )


def test_unknown_version_and_tampered_fingerprint_fail_closed():
    request = _transport()[3]
    with pytest.raises(ValidationError, match="unsupported"):
        CorrectiveActionExecutorRequestV2.build(
            request_version="999",
            legacy_request=request.legacy_request,
            planning_result=request.planning_result,
            planning_input=request.planning_input,
        )
    with pytest.raises(ValidationError, match="fingerprint"):
        CorrectiveActionExecutorRequestV2(
            request_version=request.request_version,
            legacy_request=request.legacy_request,
            planning_result=request.planning_result,
            planning_input=request.planning_input,
            request_fingerprint="sha256:" + "0" * 64,
        )


def test_safe_transport_report_is_deterministic_and_content_free():
    planning_input, _, _, request = _transport()
    report = build_executor_request_v2_report(request)
    serialized = serialize_executor_request_v2_report(report)

    assert serialized == serialize_executor_request_v2_report(report)
    assert planning_input.revision_instructions.editorial_instruction not in serialized
    assert planning_input.source_draft.assembled_text not in serialized
    assert report["planning_input_type"] == "draft_revision"
