"""M6C.6D Part 1 immutable draft-revision contract tests."""

import pytest
from pydantic import ValidationError
from test_draft_regeneration_contracts import _executor_request
from test_draft_regeneration_runtime import _draft

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorResult,
    validate_executor_result,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    DraftRevisionArchitectureDescriptor,
    DraftRevisionDiagnostic,
    DraftRevisionDiagnosticCategory,
    DraftRevisionDiagnosticCode,
    DraftRevisionInstructions,
    DraftRevisionOutcome,
    DraftRevisionRequest,
    DraftRevisionResult,
    DraftRevisionScope,
    DraftRevisionTarget,
    DraftRevisionTargetType,
    build_draft_revision_executor_descriptor,
    build_draft_revision_report,
    build_standard_draft_revision_policy,
    serialize_draft_revision_report,
    validate_draft_revision_request,
    validate_draft_revision_result,
)


def _scope(*targets):
    policy = build_standard_draft_revision_policy()
    return policy, DraftRevisionScope.build(
        targets=targets, maximum_targets=policy.maximum_revision_targets
    )


def _request(*targets):
    policy, scope = _scope(
        *(targets or (DraftRevisionTarget.build(target_type="opening"),))
    )
    instructions = DraftRevisionInstructions.build(
        scope_fingerprint=scope.scope_fingerprint,
        editorial_instruction="Clarifică formularea din secțiunea autorizată.",
    )
    source = _draft("sursa")
    request = DraftRevisionRequest.build(
        executor_request=_executor_request(CorrectiveAction.REQUEST_REVISION),
        source_draft=source,
        policy=policy,
        scope=scope,
        instructions=instructions,
    )
    return source, request


def test_descriptor_and_architecture_are_exact_and_deterministic():
    descriptor = build_draft_revision_executor_descriptor()
    assert descriptor.supported_capability.value == "draft_revision"
    assert tuple(item.value for item in descriptor.supported_plan_types) == (
        "revise_draft",
    )
    assert (
        DraftRevisionArchitectureDescriptor.build()
        == DraftRevisionArchitectureDescriptor.build()
    )


def test_target_scope_is_canonical_immutable_and_rejects_duplicates():
    closing = DraftRevisionTarget.build(target_type=DraftRevisionTargetType.CLOSING)
    opening = DraftRevisionTarget.build(target_type=DraftRevisionTargetType.OPENING)
    policy, scope = _scope(closing, opening)

    assert tuple(item.target_type for item in scope.targets) == (
        DraftRevisionTargetType.OPENING,
        DraftRevisionTargetType.CLOSING,
    )
    with pytest.raises(ValidationError):
        scope.targets = ()
    with pytest.raises(ValidationError, match="duplicate"):
        DraftRevisionScope.build(
            targets=(opening, opening),
            maximum_targets=policy.maximum_revision_targets,
        )


def test_empty_scope_and_ambiguous_target_fail_closed():
    with pytest.raises(ValidationError):
        DraftRevisionScope.build(targets=(), maximum_targets=10)
    with pytest.raises(ValidationError, match="identity"):
        DraftRevisionTarget.build(target_type="story")
    with pytest.raises(ValidationError):
        DraftRevisionTarget.build(target_type="unknown")


def test_request_preserves_source_identity_and_rejects_missing_target():
    source, request = _request()
    assert request.source_draft is source
    validate_draft_revision_request(request)

    missing = DraftRevisionTarget.build(target_type="story", story_id=999)
    with pytest.raises(ValidationError, match="does not exist"):
        _request(missing)


def test_instruction_scope_and_policy_versions_fail_closed():
    _, request = _request()
    payload = request.instructions.model_dump(mode="python")
    payload["scope_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError):
        DraftRevisionInstructions.model_validate(payload)
    with pytest.raises(ValidationError, match="unsupported"):
        type(request.policy).build(contract_version="999")


def test_success_requires_distinct_draft_and_has_v2_compatible_reference():
    source, request = _request()
    with pytest.raises(ValidationError, match="reuses"):
        DraftRevisionResult.build_success(request, source)

    result = DraftRevisionResult.build_success(request, _draft("revizuita"))
    validate_draft_revision_result(result)
    generic = CorrectiveActionExecutorResult.build(
        executor_descriptor=request.executor_request.executor_descriptor,
        request=request.executor_request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        output_reference=result.output_reference.executor_output_reference,
        diagnostic=None,
    )
    assert generic.result_version == "2"
    assert generic.output_reference is result.output_reference.executor_output_reference
    validate_executor_result(generic)


def test_failure_shape_and_diagnostic_safety():
    _, request = _request()
    diagnostic = DraftRevisionDiagnostic.build(
        code=DraftRevisionDiagnosticCode.PROHIBITED_REVISION,
        category=DraftRevisionDiagnosticCategory.REVISION,
        safe_message="Revision exceeds its authorized scope.",
    )
    result = DraftRevisionResult.build_failure(
        revision_request=request,
        revision_outcome=DraftRevisionOutcome.FAILED_CONTROLLED_REVISION,
        diagnostic=diagnostic,
    )
    assert result.revised_draft is result.output_reference is None
    with pytest.raises(ValidationError):
        DraftRevisionDiagnostic.build(
            code=DraftRevisionDiagnosticCode.REVISION_INTERNAL_FAILURE,
            category=DraftRevisionDiagnosticCategory.INTERNAL,
            safe_message="secret token at C:\\private",
        )


def test_report_and_serialization_exclude_draft_and_instruction_content():
    _, request = _request()
    result = DraftRevisionResult.build_success(request, _draft("noua"))
    report = build_draft_revision_report(result)
    serialized = serialize_draft_revision_report(report)

    assert serialized == serialize_draft_revision_report(report)
    assert request.instructions.editorial_instruction not in serialized
    assert request.source_draft.assembled_text not in serialized
    assert report.target_count == 1
