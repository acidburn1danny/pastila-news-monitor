"""M6C.6B.1 backward-compatible executor output-reference tests."""

from test_draft_regeneration_contracts import _executor_request

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorResult,
    CorrectiveActionOutputReference,
    validate_executor_result,
)
from pastila_scout.editor.qa.models import fingerprint


def test_legacy_result_keeps_version_one_shape_and_fingerprint():
    request = _executor_request()
    legacy = CorrectiveActionExecutorResult.build(
        executor_descriptor=request.executor_descriptor,
        request=request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        diagnostic=None,
    )

    assert legacy.result_version == "1"
    assert legacy.output_reference is None
    validate_executor_result(legacy)


def test_output_reference_selects_version_two_and_is_deterministic():
    request = _executor_request()
    output = CorrectiveActionOutputReference.build(
        output_type="episode-draft",
        capability=request.plan.required_capability,
        output_fingerprint=fingerprint({"output": "opaque"}),
        capability_result_fingerprint=fingerprint({"result": "opaque"}),
    )
    result = CorrectiveActionExecutorResult.build(
        executor_descriptor=request.executor_descriptor,
        request=request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        output_reference=output,
        diagnostic=None,
    )
    duplicate = CorrectiveActionExecutorResult.build(
        executor_descriptor=request.executor_descriptor,
        request=request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        output_reference=output,
        diagnostic=None,
    )

    assert result.result_version == "2"
    assert result.output_reference is output
    assert result.result_fingerprint == duplicate.result_fingerprint
    validate_executor_result(result)
