"""Controlled Generation Revision Evolution Part 2 runtime tests."""

import inspect

from test_controlled_revision_contracts import _gateway_success, _invocation

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.generation.revision import (
    ControlledRevisionDiagnostic,
    ControlledRevisionGatewayResult,
    ControlledRevisionLifecycle,
    RevisionDiagnosticCode,
    RevisionGatewayStatus,
    RevisionLifecyclePhase,
    RevisionResultStatus,
    build_revision_execution_report,
    compose_controlled_revision_execution_service,
    revision_fingerprint,
    serialize_revision_report,
)


class GatewaySpy:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0
        self.last_invocation = None

    def revise(self, invocation):
        self.calls += 1
        self.last_invocation = invocation
        if self.error:
            raise self.error
        return self.result

    def generate(self, invocation):  # pragma: no cover - must never be called
        raise AssertionError("legacy generation must not be invoked")


def _revised_opening(invocation, text="Deschidere revizuită."):
    source = invocation.request.source_draft
    assembled = f"{text}\n\n{source.closing}"
    return EpisodeDraft(
        episode_id=source.episode_id,
        opening=text,
        stories=source.stories,
        transitions=source.transitions,
        closing=source.closing,
        cta=source.cta,
        assembled_text=assembled,
        teleprompter_text=assembled,
    )


def _success(invocation, revised=None):
    return _gateway_success(invocation, revised or _revised_opening(invocation))


def test_valid_success_invokes_gateway_once_and_preserves_exact_identity():
    invocation = _invocation()
    gateway_result = _success(invocation)
    gateway = GatewaySpy(gateway_result)
    service = compose_controlled_revision_execution_service(gateway)

    result = service.execute(invocation)

    assert gateway.calls == 1
    assert gateway.last_invocation is invocation
    assert result.status is RevisionResultStatus.SUCCESS
    assert result.revised_draft is gateway_result.revised_draft
    assert (
        result.gateway_result_fingerprint == gateway_result.gateway_result_fingerprint
    )
    assert result.lifecycle.phases[-1] is RevisionLifecyclePhase.COMPLETED
    assert result == service.execute(invocation)
    assert gateway.calls == 2  # one call for each independent execution


def test_invalid_invocation_calls_gateway_zero_times():
    invocation = _invocation()
    invalid = invocation.model_copy(
        update={"invocation_fingerprint": "sha256:" + "0" * 64}
    )
    gateway = GatewaySpy()
    result = compose_controlled_revision_execution_service(gateway).execute(invalid)

    assert gateway.calls == 0
    assert result.status is RevisionResultStatus.CONTRACT_FAILURE
    assert result.diagnostic.code is RevisionDiagnosticCode.INVALID_REVISION_REQUEST
    assert result.lifecycle.phases == (
        RevisionLifecyclePhase.CREATED,
        RevisionLifecyclePhase.FAILED,
    )


def test_gateway_exception_is_sanitized_and_not_retried():
    invocation = _invocation()
    sentinel = "OPENAI_API_KEY=secret C:\\private\\provider.py"
    gateway = GatewaySpy(error=RuntimeError(sentinel))
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)
    report = serialize_revision_report(
        build_revision_execution_report(invocation, result)
    )

    assert gateway.calls == 1
    assert result.status is RevisionResultStatus.GATEWAY_FAILURE
    assert result.diagnostic.code is RevisionDiagnosticCode.REVISION_GATEWAY_FAILURE
    assert sentinel not in repr(result)
    assert sentinel not in report


def test_approved_gateway_failure_is_normalized_without_output():
    invocation = _invocation()
    request = invocation.request
    diagnostic = ControlledRevisionDiagnostic.build(
        code=RevisionDiagnosticCode.REVISION_OPERATION_UNSUPPORTED,
        safe_message="Revision operation is unsupported.",
    )
    gateway_result = ControlledRevisionGatewayResult.build(
        status=RevisionGatewayStatus.UNSUPPORTED,
        source_draft_fingerprint=revision_fingerprint(request.source_draft),
        revision_request_fingerprint=request.revision_request_fingerprint,
        invocation_fingerprint=invocation.invocation_fingerprint,
        output_contract_fingerprint=request.expected_output_contract.output_contract_fingerprint,
        preservation_fingerprint=request.preservation_requirements.preservation_fingerprint,
        diagnostic=diagnostic,
    )
    gateway = GatewaySpy(gateway_result)
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)

    assert gateway.calls == 1
    assert result.status is RevisionResultStatus.GATEWAY_FAILURE
    assert result.revised_draft is None


def test_malformed_or_wrong_type_gateway_result_fails_after_one_call():
    invocation = _invocation()
    for returned in (object(), "not-a-result"):
        gateway = GatewaySpy(returned)
        result = compose_controlled_revision_execution_service(gateway).execute(
            invocation
        )
        assert gateway.calls == 1
        assert (
            result.diagnostic.code
            is RevisionDiagnosticCode.INVALID_REVISION_GATEWAY_RESULT
        )


def test_each_lineage_mismatch_fails_closed_after_one_call():
    invocation = _invocation()
    for field_name in (
        "source_draft_fingerprint",
        "revision_request_fingerprint",
        "invocation_fingerprint",
        "output_contract_fingerprint",
        "preservation_fingerprint",
    ):
        valid = _success(invocation)
        data = valid.model_dump(exclude={"gateway_result_fingerprint"}, mode="python")
        data[field_name] = "sha256:" + "0" * 64
        gateway = GatewaySpy(ControlledRevisionGatewayResult.build(**data))
        result = compose_controlled_revision_execution_service(gateway).execute(
            invocation
        )
        assert gateway.calls == 1
        assert (
            result.diagnostic.code is RevisionDiagnosticCode.REVISION_LINEAGE_MISMATCH
        )


def test_invalid_episode_draft_is_rejected_without_second_gateway_call():
    invocation = _invocation()
    source = invocation.request.source_draft
    invalid = EpisodeDraft.model_construct(
        **{
            **source.model_dump(mode="python"),
            "opening": "Schimbat",
            "assembled_text": "invalid",
        }
    )
    gateway_result = _success(invocation)
    gateway = GatewaySpy(gateway_result.model_copy(update={"revised_draft": invalid}))
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)

    assert gateway.calls == 1
    assert result.status is RevisionResultStatus.CONTRACT_FAILURE
    assert (
        result.diagnostic.code is RevisionDiagnosticCode.INVALID_REVISION_GATEWAY_RESULT
    )


def test_unauthorized_protected_change_and_whole_draft_replacement_fail():
    invocation = _invocation()
    source = invocation.request.source_draft
    opening = "Altă deschidere."
    closing = "Altă închidere."
    replacement = EpisodeDraft(
        episode_id=source.episode_id,
        opening=opening,
        stories=source.stories,
        transitions=source.transitions,
        closing=closing,
        cta=source.cta,
        assembled_text=f"{opening}\n\n{closing}",
        teleprompter_text=f"{opening}\n\n{closing}",
    )
    gateway = GatewaySpy(_success(invocation, replacement))
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)

    assert gateway.calls == 1
    assert result.status is RevisionResultStatus.REJECTED
    assert (
        result.diagnostic.code
        is RevisionDiagnosticCode.INVALID_PRESERVATION_REQUIREMENTS
    )
    assert result.lifecycle.phases[-2:] == (
        RevisionLifecyclePhase.OUTPUT_VALIDATED,
        RevisionLifecyclePhase.FAILED,
    )


def test_unauthorized_metadata_change_fails_before_preservation_success():
    invocation = _invocation()
    source = invocation.request.source_draft
    changed = EpisodeDraft(
        episode_id="different-episode",
        opening="Revizuit.",
        stories=source.stories,
        transitions=source.transitions,
        closing=source.closing,
        cta=source.cta,
        assembled_text=f"Revizuit.\n\n{source.closing}",
        teleprompter_text=f"Revizuit.\n\n{source.closing}",
    )
    gateway = GatewaySpy(_success(invocation, changed))
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)

    assert gateway.calls == 1
    assert result.diagnostic.code is RevisionDiagnosticCode.REVISION_OUTPUT_INVALID


def test_invalid_manifest_and_nested_tampering_fail_closed():
    invocation = _invocation()
    request = invocation.request
    requirements = request.preservation_requirements.model_copy(
        update={"preservation_fingerprint": "sha256:" + "0" * 64}
    )
    invalid_request = request.model_copy(
        update={"preservation_requirements": requirements}
    )
    invalid_invocation = invocation.model_copy(update={"request": invalid_request})
    gateway = GatewaySpy()
    result = compose_controlled_revision_execution_service(gateway).execute(
        invalid_invocation
    )
    assert gateway.calls == 0
    assert result.diagnostic.code is RevisionDiagnosticCode.INVALID_REVISION_REQUEST


def test_composition_preserves_dependency_identity_and_has_no_runtime_discovery():
    gateway = GatewaySpy()
    first = compose_controlled_revision_execution_service(gateway)
    second = compose_controlled_revision_execution_service(gateway)

    assert first is not second
    assert first.gateway is gateway is second.gateway
    assert first.result_factory.lifecycle_factory is not None
    source = inspect.getsource(type(first))
    assert ".generate(" not in source
    assert "retry" not in source.casefold()
    assert "fallback" not in source.casefold()


def test_runtime_report_is_content_free_utf8_and_deterministic():
    invocation = _invocation()
    gateway_result = _success(invocation)
    result = compose_controlled_revision_execution_service(
        GatewaySpy(gateway_result)
    ).execute(invocation)
    report = build_revision_execution_report(invocation, result)
    text = serialize_revision_report(report)

    assert text == serialize_revision_report(report)
    assert invocation.request.source_draft.assembled_text not in text
    assert gateway_result.revised_draft.assembled_text not in text
    assert invocation.request.revision_instructions.editorial_instruction not in text


def test_invalid_lifecycle_and_unknown_gateway_version_are_rejected():
    invocation = _invocation()
    invalid_lifecycle = ControlledRevisionLifecycle.model_construct(
        lifecycle_version="unknown",
        phases=(RevisionLifecyclePhase.CREATED,),
        lifecycle_fingerprint="sha256:" + "0" * 64,
    )
    invalid_invocation = invocation.model_copy(update={"lifecycle": invalid_lifecycle})
    gateway = GatewaySpy()
    result = compose_controlled_revision_execution_service(gateway).execute(
        invalid_invocation
    )
    assert gateway.calls == 0
    assert result.status is RevisionResultStatus.CONTRACT_FAILURE

    gateway_result = _success(invocation).model_copy(
        update={"gateway_result_version": "unknown"}
    )
    gateway = GatewaySpy(gateway_result)
    result = compose_controlled_revision_execution_service(gateway).execute(invocation)
    assert gateway.calls == 1
    assert (
        result.diagnostic.code is RevisionDiagnosticCode.INVALID_REVISION_GATEWAY_RESULT
    )
