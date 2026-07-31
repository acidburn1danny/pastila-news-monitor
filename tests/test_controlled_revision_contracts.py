"""Focused Controlled Generation Revision Evolution Part 1 tests."""

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.models import EpisodeDraft, GenerationMode
from pastila_scout.editor.generation.revision import (
    ControlledGenerationOperation,
    ControlledRevisionDiagnostic,
    ControlledRevisionGateway,
    ControlledRevisionGatewayResult,
    ControlledRevisionInstructions,
    ControlledRevisionInvocation,
    ControlledRevisionLifecycle,
    ControlledRevisionOutputContract,
    ControlledRevisionPolicy,
    ControlledRevisionRequest,
    ControlledRevisionResult,
    ControlledRevisionTarget,
    DraftPreservationRequirements,
    RevisionDiagnosticCode,
    RevisionGatewayStatus,
    RevisionLifecyclePhase,
    RevisionResultStatus,
    RevisionTargetType,
    build_revision_execution_report,
    build_revision_request_report,
    revision_fingerprint,
    serialize_revision_contract,
    serialize_revision_report,
    validate_controlled_revision_invocation,
    validate_controlled_revision_request,
    validate_controlled_revision_result,
    validate_revision_gateway_result,
)

FP = "sha256:" + "1" * 64


def _draft(label="sursă"):
    opening = f"Deschidere {label}."
    closing = f"Închidere {label}."
    text = f"{opening}\n\n{closing}"
    return EpisodeDraft(
        episode_id="episod-1",
        opening=opening,
        stories=(),
        transitions=(),
        closing=closing,
        cta=None,
        assembled_text=text,
        teleprompter_text=text,
    )


def _request(source=None, targets=None):
    source = source or _draft()
    if targets is None:
        targets = (
            ControlledRevisionTarget.build(
                target_type=RevisionTargetType.OPENING,
                upstream_target_fingerprint=FP,
            ),
        )
    policy = ControlledRevisionPolicy.build(
        maximum_revision_targets=10,
        upstream_policy_fingerprint=FP,
    )
    instructions = ControlledRevisionInstructions.build(
        editorial_instruction="Clarifică formularea autorizată.",
        authorized_scope_fingerprint=FP,
        upstream_instructions_fingerprint=FP,
    )
    source_fp = revision_fingerprint(source)
    preservation = DraftPreservationRequirements.build(
        source_draft_fingerprint=source_fp,
        allowed_target_fingerprints=tuple(item.target_fingerprint for item in targets),
        protected_component_fingerprints=(
            ("closing", revision_fingerprint(source.closing)),
        ),
        upstream_scope_fingerprint=FP,
    )
    output = ControlledRevisionOutputContract.build(
        source_draft_fingerprint=source_fp,
        preservation_fingerprint=preservation.preservation_fingerprint,
    )
    return ControlledRevisionRequest.build(
        source_draft=source,
        revision_targets=targets,
        revision_instructions=instructions,
        revision_policy=policy,
        preservation_requirements=preservation,
        expected_output_contract=output,
        planning_input_fingerprint=FP,
        executor_request_fingerprint="sha256:" + "2" * 64,
    )


def _invocation(request=None):
    return ControlledRevisionInvocation.build(request=request or _request())


def _gateway_success(invocation, revised=None):
    request = invocation.request
    return ControlledRevisionGatewayResult.build(
        status=RevisionGatewayStatus.SUCCESS,
        revised_draft=revised or _draft("revizuită"),
        source_draft_fingerprint=revision_fingerprint(request.source_draft),
        revision_request_fingerprint=request.revision_request_fingerprint,
        invocation_fingerprint=invocation.invocation_fingerprint,
        output_contract_fingerprint=request.expected_output_contract.output_contract_fingerprint,
        preservation_fingerprint=request.preservation_requirements.preservation_fingerprint,
    )


def test_valid_request_is_immutable_explicit_and_deterministic():
    source = _draft()
    first = _request(source)
    second = _request(source)
    validate_controlled_revision_request(first)

    assert first.operation is ControlledGenerationOperation.REVISION
    assert first.source_draft is source
    assert first.revision_request_fingerprint == second.revision_request_fingerprint
    with pytest.raises(ValidationError):
        first.operation = ControlledGenerationOperation.REVISION


def test_targets_are_canonical_and_duplicates_or_missing_targets_fail():
    opening = ControlledRevisionTarget.build(
        target_type="opening", upstream_target_fingerprint=FP
    )
    closing = ControlledRevisionTarget.build(
        target_type="closing", upstream_target_fingerprint="sha256:" + "3" * 64
    )
    with pytest.raises(ValidationError, match="duplicates"):
        _request(targets=(opening, opening))
    with pytest.raises(ValidationError):
        _request(targets=())
    missing = ControlledRevisionTarget.build(
        target_type="story", story_id=99, upstream_target_fingerprint=FP
    )
    with pytest.raises(ValidationError, match="absent"):
        _request(targets=(missing,))
    with pytest.raises(ValidationError, match="full regeneration"):
        _request(targets=(opening, closing))


def test_policy_instruction_preservation_and_output_mismatches_fail_closed():
    with pytest.raises(ValidationError, match="preservation"):
        ControlledRevisionPolicy.build(
            preserve_unmodified_content=False,
            maximum_revision_targets=1,
            upstream_policy_fingerprint=FP,
        )
    with pytest.raises(ValidationError):
        ControlledRevisionInstructions.build(
            editorial_instruction="  ",
            authorized_scope_fingerprint=FP,
            upstream_instructions_fingerprint=FP,
        )
    request = _request()
    data = request.model_dump(mode="python")
    data["planning_input_fingerprint"] = "sha256:" + "9" * 64
    with pytest.raises(ValidationError, match="fingerprint"):
        ControlledRevisionRequest.model_validate(data)


def test_unknown_versions_and_legacy_modes_cannot_enter_revision():
    request = _request()
    data = request.model_dump(mode="python")
    data["contract_version"] = "unknown"
    with pytest.raises(ValidationError, match="unsupported"):
        ControlledRevisionRequest.model_validate(data)
    assert not hasattr(request, "generation_mode")
    assert set(GenerationMode) == {
        GenerationMode.STANDARD,
        GenerationMode.CONSTRAINED,
        GenerationMode.MINIMAL_SAFE,
    }


def test_lifecycle_and_invocation_validation_are_closed_and_deterministic():
    invocation = _invocation()
    validate_controlled_revision_invocation(invocation)
    assert invocation == _invocation(invocation.request)
    with pytest.raises(ValidationError, match="transition"):
        ControlledRevisionLifecycle.build(
            (RevisionLifecyclePhase.CREATED, RevisionLifecyclePhase.COMPLETED)
        )


def test_gateway_protocol_and_gateway_result_deep_lineage_validation():
    invocation = _invocation()
    result = _gateway_success(invocation)
    validate_revision_gateway_result(result, invocation)

    class Gateway:
        def revise(self, invocation):
            return result

    gateway: ControlledRevisionGateway = Gateway()
    assert gateway.revise(invocation) is result
    data = result.model_dump(exclude={"gateway_result_fingerprint"}, mode="python")
    data["invocation_fingerprint"] = "sha256:" + "0" * 64
    tampered = ControlledRevisionGatewayResult.build(**data)
    with pytest.raises(ValueError, match="lineage"):
        validate_revision_gateway_result(tampered, invocation)


def test_gateway_failure_has_no_output_and_no_partial_success():
    invocation = _invocation()
    request = invocation.request
    diagnostic = ControlledRevisionDiagnostic.build(
        code=RevisionDiagnosticCode.REVISION_OPERATION_UNSUPPORTED,
        safe_message="Revision operation is unsupported.",
    )
    result = ControlledRevisionGatewayResult.build(
        status=RevisionGatewayStatus.UNSUPPORTED,
        revised_draft=None,
        source_draft_fingerprint=revision_fingerprint(request.source_draft),
        revision_request_fingerprint=request.revision_request_fingerprint,
        invocation_fingerprint=invocation.invocation_fingerprint,
        output_contract_fingerprint=request.expected_output_contract.output_contract_fingerprint,
        preservation_fingerprint=request.preservation_requirements.preservation_fingerprint,
        diagnostic=diagnostic,
    )
    validate_revision_gateway_result(result, invocation)
    with pytest.raises(ValidationError, match="shape"):
        ControlledRevisionGatewayResult.build(
            **{
                **result.model_dump(
                    exclude={"gateway_result_fingerprint"}, mode="python"
                ),
                "revised_draft": _draft("ilegal"),
            }
        )


def test_success_and_failure_controlled_results_enforce_terminal_invariants():
    invocation = _invocation()
    gateway = _gateway_success(invocation)
    lifecycle = ControlledRevisionLifecycle.build(tuple(RevisionLifecyclePhase)[:-1])
    success = ControlledRevisionResult.build(
        status=RevisionResultStatus.SUCCESS,
        revised_draft=gateway.revised_draft,
        source_draft_fingerprint=gateway.source_draft_fingerprint,
        revision_request_fingerprint=gateway.revision_request_fingerprint,
        invocation_fingerprint=gateway.invocation_fingerprint,
        gateway_result_fingerprint=gateway.gateway_result_fingerprint,
        output_contract_fingerprint=gateway.output_contract_fingerprint,
        preservation_fingerprint=gateway.preservation_fingerprint,
        lifecycle=lifecycle,
    )
    validate_controlled_revision_result(
        success, invocation=invocation, gateway_result=gateway
    )
    diagnostic = ControlledRevisionDiagnostic.build(
        code=RevisionDiagnosticCode.REVISION_GATEWAY_FAILURE,
        safe_message="Revision gateway failed.",
    )
    failed_lifecycle = ControlledRevisionLifecycle.build(
        (
            RevisionLifecyclePhase.CREATED,
            RevisionLifecyclePhase.VALIDATED,
            RevisionLifecyclePhase.FAILED,
        )
    )
    failed = ControlledRevisionResult.build(
        status=RevisionResultStatus.GATEWAY_FAILURE,
        revised_draft=None,
        source_draft_fingerprint=gateway.source_draft_fingerprint,
        revision_request_fingerprint=gateway.revision_request_fingerprint,
        invocation_fingerprint=gateway.invocation_fingerprint,
        gateway_result_fingerprint=gateway.gateway_result_fingerprint,
        output_contract_fingerprint=gateway.output_contract_fingerprint,
        preservation_fingerprint=gateway.preservation_fingerprint,
        lifecycle=failed_lifecycle,
        diagnostic=diagnostic,
    )
    validate_controlled_revision_result(failed, invocation=invocation)


def test_safe_reports_and_repr_do_not_leak_draft_or_instruction_prose():
    request = _request()
    request_report = build_revision_request_report(request)
    serialized = serialize_revision_report(request_report)
    assert request.revision_instructions.editorial_instruction not in serialized
    assert request.source_draft.assembled_text not in serialized
    assert request.revision_instructions.editorial_instruction not in repr(request)
    assert request.source_draft.assembled_text not in repr(request)
    assert serialize_revision_report(request_report) == serialized
    assert request.source_draft.opening in serialize_revision_contract(request)


def test_execution_report_is_safe_and_deterministic():
    invocation = _invocation()
    gateway = _gateway_success(invocation)
    result = ControlledRevisionResult.build(
        status="success",
        revised_draft=gateway.revised_draft,
        source_draft_fingerprint=gateway.source_draft_fingerprint,
        revision_request_fingerprint=gateway.revision_request_fingerprint,
        invocation_fingerprint=gateway.invocation_fingerprint,
        gateway_result_fingerprint=gateway.gateway_result_fingerprint,
        output_contract_fingerprint=gateway.output_contract_fingerprint,
        preservation_fingerprint=gateway.preservation_fingerprint,
        lifecycle=ControlledRevisionLifecycle.build(tuple(RevisionLifecyclePhase)[:-1]),
    )
    report = build_revision_execution_report(invocation, result)
    text = serialize_revision_report(report)
    assert text == serialize_revision_report(report)
    assert gateway.revised_draft.assembled_text not in text
    assert "completed" in text


def test_revision_package_has_no_provider_runtime_or_mutable_registry():
    from pastila_scout.editor.generation import revision

    names = set(dir(revision))
    assert "LanguageModelProvider" not in names
    assert "GenerationMode" not in names
    assert not any("registry" in name.casefold() for name in names)
