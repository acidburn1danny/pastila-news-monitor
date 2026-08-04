"""Pure application-owned projection from validated provider-neutral results."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from pastila_scout.editor.generation.revision import (
    ControlledRevisionGatewayResult,
    RevisionGatewayStatus,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderResultStatusV2,
)

from .canonical import semantic_sha256
from .models import (
    AIProviderExecutionStatus,
    ProducerAttemptDiagnosticsV1,
    ProducerDiagnosticAuthorityV1,
    ProducerDiagnosticsObservationV1,
    ProducerExecutionAttemptV1,
    ProducerExecutionDiagnosticsV1,
    ProducerExecutionFailureV1,
    ProducerExecutionLifecycleStateV1,
    ProducerExecutionLifecycleV1,
    ProducerExecutionRequestV1,
    ProducerExecutionResultV1,
    ProducerFailureCodeV1,
    ProducerFinishMetadataV1,
)


def correlation_id_for(
    request: ProducerExecutionRequestV1, *, attempt_number: int
) -> str:
    """Return the specification-owned diagnostics correlation identifier."""
    provider_request = request.provider_request
    return semantic_sha256(
        {
            "attempt_number": attempt_number,
            "execution_request_id": provider_request.context.request_id,
            "request_envelope_identity": provider_request.request_envelope.identity,
            "request_fingerprint": request.request_fingerprint,
        }
    )


@dataclass(frozen=True, slots=True)
class ProducerResultProjectorV1:
    """Project already-created values without execution or external observation."""

    def project(
        self,
        *,
        request: ProducerExecutionRequestV1,
        provider_result: ProviderExecutionResultV2,
        observation: ProducerDiagnosticsObservationV1 | None = None,
        latency_ms: str | None = None,
        gateway_result: ControlledRevisionGatewayResult | None = None,
    ) -> ProducerExecutionResultV1:
        request = _reconstruct(ProducerExecutionRequestV1, request)
        lower = _reconstruct(ProviderExecutionResultV2, provider_result)
        _validate_lower_lineage(request, lower)
        observation = _validated_observation(request, observation)
        finish_metadata = _finish_metadata(lower)
        failure = _failure_for(lower)
        attempt_succeeded = failure is None
        gateway_result = _validated_gateway(request, gateway_result)
        attempt_diagnostics = _attempt_diagnostics(
            observation=observation,
            latency_ms=latency_ms,
            finish_metadata=finish_metadata,
            has_lower_result=True,
        )
        attempt = ProducerExecutionAttemptV1.build(
            attempt_number=1,
            execution_request_id=lower.request_id,
            request_envelope_identity=lower.request_envelope_identity,
            timeout_seconds=request.provider_request.timeout_policy.timeout_seconds,
            cancellation_requested=False,
            outcome=lower.outcome,
            succeeded=attempt_succeeded,
            failure=failure,
            diagnostics=attempt_diagnostics,
        )

        if attempt_succeeded and gateway_result is not None:
            status = AIProviderExecutionStatus.SUCCESS
            terminal = ProducerExecutionLifecycleStateV1.SUCCEEDED
            result_failure = None
            states = (
                ProducerExecutionLifecycleStateV1.ACCEPTED,
                ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED,
                ProducerExecutionLifecycleStateV1.ATTEMPTING,
                ProducerExecutionLifecycleStateV1.ATTEMPT_SUCCEEDED,
                ProducerExecutionLifecycleStateV1.PROJECTING_RESULT,
                terminal,
            )
        else:
            status = (
                AIProviderExecutionStatus.CANCELLED
                if lower.outcome is ExecutionOutcomeV2.CANCELLED
                else AIProviderExecutionStatus.FAILED
            )
            terminal = (
                ProducerExecutionLifecycleStateV1.CANCELLED
                if status is AIProviderExecutionStatus.CANCELLED
                else ProducerExecutionLifecycleStateV1.FAILED
            )
            if attempt_succeeded:
                result_failure = ProducerExecutionFailureV1.from_code(
                    ProducerFailureCodeV1.GATEWAY_PROJECTION_FAILED
                )
                states = (
                    ProducerExecutionLifecycleStateV1.ACCEPTED,
                    ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED,
                    ProducerExecutionLifecycleStateV1.ATTEMPTING,
                    ProducerExecutionLifecycleStateV1.ATTEMPT_SUCCEEDED,
                    ProducerExecutionLifecycleStateV1.PROJECTING_RESULT,
                    terminal,
                )
            else:
                result_failure = failure
                states = (
                    ProducerExecutionLifecycleStateV1.ACCEPTED,
                    ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED,
                    ProducerExecutionLifecycleStateV1.ATTEMPTING,
                    ProducerExecutionLifecycleStateV1.ATTEMPT_FAILED,
                    terminal,
                )
            gateway_result = None

        lifecycle = ProducerExecutionLifecycleV1(states=states, terminal_state=terminal)
        diagnostics = _execution_diagnostics(
            attempt=attempt,
            terminal=terminal,
            failure=result_failure,
        )
        return ProducerExecutionResultV1.build(
            request_reference=request.request_reference,
            request_fingerprint=request.request_fingerprint,
            invocation_reference=request.invocation_reference,
            invocation_fingerprint=request.invocation_fingerprint,
            status=status,
            gateway_result=gateway_result,
            diagnostics=diagnostics,
            failure=result_failure,
            attempts=(attempt,),
            lifecycle=lifecycle,
        )


def _validate_lower_lineage(
    request: ProducerExecutionRequestV1, result: ProviderExecutionResultV2
) -> None:
    lower_request = request.provider_request
    if (
        result.request_id != lower_request.context.request_id
        or result.provider_id != lower_request.provider.provider_id
        or result.request_envelope_identity != lower_request.request_envelope.identity
    ):
        raise ValueError("provider result lineage is invalid")


def _validated_gateway(
    request: ProducerExecutionRequestV1,
    gateway_result: ControlledRevisionGatewayResult | None,
) -> ControlledRevisionGatewayResult | None:
    if gateway_result is None:
        return None
    try:
        gateway = _reconstruct(ControlledRevisionGatewayResult, gateway_result)
    except ValueError:
        return None
    if (
        gateway.status is not RevisionGatewayStatus.SUCCESS
        or gateway.revised_draft is None
        or gateway.diagnostic is not None
        or gateway.invocation_fingerprint != request.invocation_fingerprint
        or gateway.source_draft_fingerprint
        != "sha256:" + request.provider_request.request_intent.draft_fingerprint
    ):
        return None
    return gateway


def _validated_observation(
    request: ProducerExecutionRequestV1,
    observation: ProducerDiagnosticsObservationV1 | None,
) -> ProducerDiagnosticsObservationV1 | None:
    if observation is None:
        return None
    observation = _reconstruct(ProducerDiagnosticsObservationV1, observation)
    lower_request = request.provider_request
    correlation = correlation_id_for(request, attempt_number=1)
    if not observation.correlated_to(
        correlation_id=correlation,
        attempt_number=1,
        execution_request_id=lower_request.context.request_id,
        request_envelope_identity=lower_request.request_envelope.identity,
    ):
        raise ValueError("diagnostics observation is stale or foreign")
    return observation


def _finish_metadata(
    result: ProviderExecutionResultV2,
) -> tuple[ProducerFinishMetadataV1, ...]:
    if result.provider_result is None:
        return ()
    return tuple(
        ProducerFinishMetadataV1(
            source_request_reference=output.source_request_reference,
            ordinal=output.ordinal,
            finish_reason=output.finish_reason,
        )
        for output in result.provider_result.outputs
    )


def _failure_for(
    result: ProviderExecutionResultV2,
) -> ProducerExecutionFailureV1 | None:
    if result.outcome is ExecutionOutcomeV2.COMPLETED:
        projection = result.provider_result
        if (
            projection is not None
            and projection.status is ProviderResultStatusV2.SUCCESS
        ):
            return None
        code = _known_lower_code(projection.failure_code if projection else None)
        code = code or ProducerFailureCodeV1.PROVIDER_PARTIAL_RESULT
        if projection is not None:
            reasons = tuple(output.finish_reason for output in projection.outputs)
            if ProviderFinishReasonV2.CONTENT_FILTERED in reasons:
                code = ProducerFailureCodeV1.PROVIDER_CONTENT_FILTERED
            elif ProviderFinishReasonV2.LENGTH in reasons:
                code = ProducerFailureCodeV1.PROVIDER_LENGTH_LIMITED
            elif projection.status is ProviderResultStatusV2.FAILED:
                code = ProducerFailureCodeV1.PROVIDER_EXECUTION_FAILED
        return ProducerExecutionFailureV1.from_code(
            code,
            source_outcome=result.outcome,
            source_failure_code=(projection.failure_code if projection else None),
        )
    code = (
        _known_lower_code(result.failure_code)
        or {
            ExecutionOutcomeV2.PROVIDER_FAILURE: ProducerFailureCodeV1.PROVIDER_EXECUTION_FAILED,
            ExecutionOutcomeV2.TIMEOUT: ProducerFailureCodeV1.PROVIDER_TIMEOUT,
            ExecutionOutcomeV2.CANCELLED: ProducerFailureCodeV1.PRODUCER_EXECUTION_CANCELLED,
            ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE: ProducerFailureCodeV1.PROVIDER_INTERNAL_FAILURE,
        }[result.outcome]
    )
    return ProducerExecutionFailureV1.from_code(
        code,
        source_outcome=result.outcome,
        source_failure_code=result.failure_code,
    )


def _known_lower_code(value: str | None) -> ProducerFailureCodeV1 | None:
    known = {
        code.value: code
        for code in (
            ProducerFailureCodeV1.PROVIDER_TIMEOUT,
            ProducerFailureCodeV1.PROVIDER_RATE_LIMITED,
            ProducerFailureCodeV1.PROVIDER_TRANSPORT_FAILED,
            ProducerFailureCodeV1.PROVIDER_UNAVAILABLE,
            ProducerFailureCodeV1.PROVIDER_REFUSAL,
            ProducerFailureCodeV1.PROVIDER_LENGTH_LIMITED,
            ProducerFailureCodeV1.PROVIDER_CONTENT_FILTERED,
        )
    }
    return known.get(value)


def _attempt_diagnostics(
    *,
    observation: ProducerDiagnosticsObservationV1 | None,
    latency_ms: str | None,
    finish_metadata: tuple[ProducerFinishMetadataV1, ...],
    has_lower_result: bool,
) -> ProducerAttemptDiagnosticsV1:
    unavailable = ProducerDiagnosticAuthorityV1.UNAVAILABLE
    application = ProducerDiagnosticAuthorityV1.APPLICATION_DIAGNOSTICS_AUTHORITY
    return ProducerAttemptDiagnosticsV1(
        usage=observation.usage if observation else None,
        usage_authority=(
            application if observation and observation.usage else unavailable
        ),
        latency_ms=latency_ms,
        latency_authority=(
            ProducerDiagnosticAuthorityV1.COMPATIBILITY_CLOCK
            if latency_ms is not None
            else unavailable
        ),
        provider_request_id=observation.provider_request_id if observation else None,
        provider_request_id_authority=(
            application
            if observation and observation.provider_request_id
            else unavailable
        ),
        returned_model_id=observation.returned_model_id if observation else None,
        returned_model_id_authority=(
            application
            if observation and observation.returned_model_id
            else unavailable
        ),
        finish_metadata=finish_metadata,
        finish_metadata_authority=(
            ProducerDiagnosticAuthorityV1.PROVIDER_RESULT
            if has_lower_result
            else unavailable
        ),
    )


def _execution_diagnostics(
    *,
    attempt: ProducerExecutionAttemptV1,
    terminal: ProducerExecutionLifecycleStateV1,
    failure: ProducerExecutionFailureV1 | None,
) -> ProducerExecutionDiagnosticsV1:
    local = attempt.diagnostics
    unavailable = ProducerDiagnosticAuthorityV1.UNAVAILABLE
    coordinator = ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
    return ProducerExecutionDiagnosticsV1(
        usage=local.usage,
        usage_authority=coordinator if local.usage else unavailable,
        latency_ms=local.latency_ms,
        latency_authority=coordinator if local.latency_ms is not None else unavailable,
        provider_request_id=local.provider_request_id,
        provider_request_id_authority=local.provider_request_id_authority,
        returned_model_id=local.returned_model_id,
        returned_model_id_authority=local.returned_model_id_authority,
        finish_metadata=local.finish_metadata,
        finish_metadata_authority=local.finish_metadata_authority,
        retryable=failure.retryable if failure else None,
        retryability_authority=coordinator if failure else unavailable,
        attempt_count=1,
        attempt_count_authority=coordinator,
        lifecycle_state=terminal,
        lifecycle_authority=coordinator,
    )


def _reconstruct(model, value):
    try:
        payload = value.model_dump(mode="python", warnings=False)
        return model.model_validate(payload, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError) as error:
        raise ValueError(f"invalid retained {model.__name__}") from error


__all__ = ()
