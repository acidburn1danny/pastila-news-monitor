"""Authoritative deep validators for Controlled Revision aggregates."""

from pydantic import ValidationError

from pastila_scout.editor.generation.models import EpisodeDraft

from .contracts import (
    ControlledRevisionGatewayResult,
    ControlledRevisionInvocation,
    ControlledRevisionLifecycle,
    ControlledRevisionOutputContract,
    ControlledRevisionRequest,
    ControlledRevisionResult,
    DraftPreservationRequirements,
)
from .enums import RevisionGatewayStatus, RevisionResultStatus
from .identity import revision_fingerprint


def validate_preservation_requirements(value: DraftPreservationRequirements) -> None:
    _revalidate(DraftPreservationRequirements, value)


def validate_revision_output_contract(value: ControlledRevisionOutputContract) -> None:
    _revalidate(ControlledRevisionOutputContract, value)


def validate_revision_lifecycle(value: ControlledRevisionLifecycle) -> None:
    _revalidate(ControlledRevisionLifecycle, value)


def validate_controlled_revision_request(value: ControlledRevisionRequest) -> None:
    _require(ControlledRevisionRequest, value)
    value.invariants()
    _revalidate(EpisodeDraft, value.source_draft)
    for target in value.revision_targets:
        _revalidate(type(target), target)
    _revalidate(type(value.revision_instructions), value.revision_instructions)
    _revalidate(type(value.revision_policy), value.revision_policy)
    validate_preservation_requirements(value.preservation_requirements)
    validate_revision_output_contract(value.expected_output_contract)


def validate_controlled_revision_invocation(
    value: ControlledRevisionInvocation,
) -> None:
    _require(ControlledRevisionInvocation, value)
    value.invariants()
    validate_controlled_revision_request(value.request)
    validate_revision_lifecycle(value.lifecycle)


def validate_revision_gateway_result(
    value: ControlledRevisionGatewayResult,
    invocation: ControlledRevisionInvocation | None = None,
) -> None:
    _require(ControlledRevisionGatewayResult, value)
    value.invariants()
    if value.revised_draft:
        _revalidate(EpisodeDraft, value.revised_draft)
    if value.diagnostic:
        _revalidate(type(value.diagnostic), value.diagnostic)
    if invocation:
        request = invocation.request
        expected = (
            revision_fingerprint(request.source_draft),
            request.revision_request_fingerprint,
            invocation.invocation_fingerprint,
            request.expected_output_contract.output_contract_fingerprint,
            request.preservation_requirements.preservation_fingerprint,
        )
        actual = (
            value.source_draft_fingerprint,
            value.revision_request_fingerprint,
            value.invocation_fingerprint,
            value.output_contract_fingerprint,
            value.preservation_fingerprint,
        )
        if actual != expected:
            raise ValueError("controlled revision gateway lineage mismatch")
        if (
            value.status is RevisionGatewayStatus.SUCCESS
            and value.revised_draft is request.source_draft
        ):
            raise ValueError("controlled revision gateway reused source identity")


def validate_controlled_revision_result(
    value: ControlledRevisionResult,
    *,
    invocation: ControlledRevisionInvocation | None = None,
    gateway_result: ControlledRevisionGatewayResult | None = None,
) -> None:
    _require(ControlledRevisionResult, value)
    value.invariants()
    validate_revision_lifecycle(value.lifecycle)
    if value.revised_draft:
        _revalidate(EpisodeDraft, value.revised_draft)
    if value.diagnostic:
        _revalidate(type(value.diagnostic), value.diagnostic)
    if invocation:
        request = invocation.request
        if (
            value.source_draft_fingerprint != revision_fingerprint(request.source_draft)
            or value.revision_request_fingerprint
            != request.revision_request_fingerprint
            or value.invocation_fingerprint != invocation.invocation_fingerprint
            or value.output_contract_fingerprint
            != request.expected_output_contract.output_contract_fingerprint
            or value.preservation_fingerprint
            != request.preservation_requirements.preservation_fingerprint
        ):
            raise ValueError("controlled revision result lineage mismatch")
        if (
            value.status is RevisionResultStatus.SUCCESS
            and value.revised_draft is request.source_draft
        ):
            raise ValueError("controlled revision result reused source identity")
    if gateway_result:
        if (
            value.gateway_result_fingerprint
            != gateway_result.gateway_result_fingerprint
        ):
            raise ValueError("controlled revision gateway-result lineage mismatch")
        if (
            value.status is RevisionResultStatus.SUCCESS
            and value.revised_draft != gateway_result.revised_draft
        ):
            raise ValueError("controlled revision output differs from gateway result")


def _revalidate(model_type, value) -> None:
    _require(model_type, value)
    try:
        model_type.model_validate(value.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(f"{model_type.__name__} integrity validation failed") from exc


def _require(model_type, value) -> None:
    if not isinstance(value, model_type):
        raise TypeError(f"invalid {model_type.__name__}")
