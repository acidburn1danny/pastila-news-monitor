"""Explicit opt-in coordinator for provider-neutral Producer execution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pydantic import ValidationError

from pastila_scout.editor.generation.provider_compatibility_v1.composition import (
    ProducerCompatibilityCompositionV1,
    compose_producer_compatibility_v1,
)
from pastila_scout.editor.generation.provider_compatibility_v1.errors import (
    ProducerCompatibilityConfigurationError,
)
from pastila_scout.editor.generation.provider_compatibility_v1.models import (
    AIProviderExecutionStatus,
    ProducerAttemptDiagnosticsV1,
    ProducerCompatibilityEventCodeV1,
    ProducerCompatibilityEventV1,
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
    ProducerTokenUsageV1,
)
from pastila_scout.editor.generation.provider_compatibility_v1.projection import (
    ProducerResultProjectorV1,
    correlation_id_for,
)
from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    ProviderExecutorV2,
)

from .protocols import ProducerGatewayProjectorV1


@dataclass(frozen=True, slots=True)
class ProducerCompatibilityRuntimeV1:
    """One explicitly composed opt-in execution path."""

    coordinator: ProducerCompatibilityCoordinatorV1

    def execute(self) -> ProducerExecutionResultV1:
        """Execute the authoritative request through the injected lower executor."""

        return self.coordinator.execute()


@dataclass(frozen=True, slots=True)
class ProducerCompatibilityCoordinatorV1:
    """Own Producer orchestration while leaving transport lifetime below it."""

    composition: ProducerCompatibilityCompositionV1
    gateway_projector: ProducerGatewayProjectorV1

    def execute(self) -> ProducerExecutionResultV1:
        """Run the separately composed provider-neutral path with no fallback."""

        request = ProducerExecutionRequestV1.reconstruct(self.composition.request)
        states = [ProducerExecutionLifecycleStateV1.ACCEPTED]
        attempts: list[ProducerExecutionAttemptV1] = []
        _emit(
            self.composition,
            request,
            ProducerCompatibilityEventCodeV1.EXECUTION_STARTED,
            states[-1],
        )
        if _cancelled(self.composition.cancellation_token):
            return _cancelled_result(self.composition, request, states, attempts)

        states.append(ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED)
        _emit(
            self.composition,
            request,
            ProducerCompatibilityEventCodeV1.REQUEST_VALIDATED,
            states[-1],
        )
        attempt_number = 0
        while True:
            if _cancelled(self.composition.cancellation_token):
                return _cancelled_result(self.composition, request, states, attempts)
            attempt_number += 1
            lower_request = _fresh_request(request.provider_request)
            states.append(ProducerExecutionLifecycleStateV1.ATTEMPTING)
            _emit(
                self.composition,
                request,
                ProducerCompatibilityEventCodeV1.ATTEMPT_STARTED,
                states[-1],
                attempt_number,
            )
            started = _clock_sample(self.composition.clock)
            lower_result = None
            dispatch_failure = None
            try:
                candidate = self.composition.executor.execute(lower_request)
                lower_result = _validated_lower_result(lower_request, candidate)
                if lower_result is None:
                    dispatch_failure = ProducerExecutionFailureV1.from_code(
                        ProducerFailureCodeV1.PROVIDER_RESULT_INVALID
                    )
            except Exception:  # noqa: BLE001 - public execution boundary
                dispatch_failure = ProducerExecutionFailureV1.from_code(
                    ProducerFailureCodeV1.PROVIDER_EXECUTOR_CONTRACT_FAILED
                )
            finally:
                stopped = _clock_sample(self.composition.clock)
            latency = _latency(started, stopped)

            if lower_result is None:
                attempt = _failed_attempt(
                    lower_request,
                    attempt_number,
                    dispatch_failure,
                    latency,
                )
                projected = None
                observation_state = None
            else:
                observation, observation_state = _observe(
                    self.composition, request, lower_result, attempt_number
                )
                if _lower_succeeded(lower_result):
                    projected = None
                    attempt = _successful_attempt(
                        lower_request,
                        lower_result,
                        attempt_number,
                        observation,
                        latency,
                    )
                else:
                    projected = self.composition.projector.project(
                        request=request,
                        provider_result=lower_result,
                        observation=_projection_observation(
                            request, observation, attempt_number
                        ),
                        latency_ms=latency,
                    )
                    original = projected.attempts[0]
                    attempt = ProducerExecutionAttemptV1.build(
                        attempt_number=attempt_number,
                        execution_request_id=original.execution_request_id,
                        request_envelope_identity=original.request_envelope_identity,
                        timeout_seconds=original.timeout_seconds,
                        cancellation_requested=False,
                        outcome=original.outcome,
                        succeeded=original.succeeded,
                        failure=original.failure,
                        diagnostics=original.diagnostics,
                    )
            attempts.append(attempt)
            if observation_state is not None:
                _emit(
                    self.composition,
                    request,
                    observation_state,
                    states[-1],
                    attempt_number,
                )

            if attempt.succeeded:
                states.append(ProducerExecutionLifecycleStateV1.ATTEMPT_SUCCEEDED)
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.ATTEMPT_SUCCEEDED,
                    states[-1],
                    attempt_number,
                )
                if _cancelled(self.composition.cancellation_token):
                    return _cancelled_result(
                        self.composition, request, states, attempts
                    )
                states.append(ProducerExecutionLifecycleStateV1.PROJECTING_RESULT)
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.PROJECTION_STARTED,
                    states[-1],
                    attempt_number,
                )
                try:
                    gateway = self.gateway_projector.project(
                        request=lower_request, result=lower_result
                    )
                except Exception:  # noqa: BLE001 - projection failure is a value
                    gateway = None
                projected = self.composition.projector.project(
                    request=request,
                    provider_result=lower_result,
                    observation=_projection_observation(
                        request, observation, attempt_number
                    ),
                    latency_ms=latency,
                    gateway_result=gateway,
                )
                if projected.gateway_result is not None:
                    states.append(ProducerExecutionLifecycleStateV1.SUCCEEDED)
                    _emit(
                        self.composition,
                        request,
                        ProducerCompatibilityEventCodeV1.PROJECTION_COMPLETED,
                        states[-2],
                        attempt_number,
                    )
                    _emit(
                        self.composition,
                        request,
                        ProducerCompatibilityEventCodeV1.EXECUTION_SUCCEEDED,
                        states[-1],
                    )
                    return _result(
                        request,
                        attempts,
                        states,
                        projected.gateway_result,
                        None,
                    )
                failure = ProducerExecutionFailureV1.from_code(
                    ProducerFailureCodeV1.GATEWAY_PROJECTION_FAILED
                )
                states.append(ProducerExecutionLifecycleStateV1.FAILED)
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.PROJECTION_FAILED,
                    states[-1],
                    attempt_number,
                    failure.diagnostic_code,
                )
                _emit_terminal_failure(self.composition, request, states, failure)
                return _result(request, attempts, states, None, failure)

            states.append(ProducerExecutionLifecycleStateV1.ATTEMPT_FAILED)
            failure = attempt.failure
            _emit(
                self.composition,
                request,
                ProducerCompatibilityEventCodeV1.ATTEMPT_FAILED,
                states[-1],
                attempt_number,
                failure.diagnostic_code,
            )
            if failure.diagnostic_code is ProducerFailureCodeV1.PROVIDER_TIMEOUT:
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.TIMEOUT_DETECTED,
                    states[-1],
                    attempt_number,
                    failure.diagnostic_code,
                )
            if (
                attempt.outcome is not None and attempt.outcome.value == "cancelled"
            ) or _cancelled(self.composition.cancellation_token):
                return _cancelled_result(self.composition, request, states, attempts)
            if _retry(self.composition, request, failure, attempt_number):
                states.append(ProducerExecutionLifecycleStateV1.RETRY_WAIT)
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.RETRY_SCHEDULED,
                    states[-1],
                    attempt_number,
                )
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.BACKOFF_STARTED,
                    states[-1],
                    attempt_number,
                )
                try:
                    self.composition.sleeper.sleep(request.retry_policy.delay_seconds)
                except Exception:  # noqa: BLE001 - no lower exception may escape
                    failure = ProducerExecutionFailureV1.from_code(
                        ProducerFailureCodeV1.RETRY_EXHAUSTED,
                        source_outcome=attempt.failure.source_outcome,
                        source_failure_code=attempt.failure.source_failure_code,
                    )
                    states.append(ProducerExecutionLifecycleStateV1.FAILED)
                    _emit_terminal_failure(self.composition, request, states, failure)
                    return _result(request, attempts, states, None, failure)
                states.append(ProducerExecutionLifecycleStateV1.RETRY_WAIT)
                _emit(
                    self.composition,
                    request,
                    ProducerCompatibilityEventCodeV1.BACKOFF_COMPLETED,
                    states[-1],
                    attempt_number,
                )
                continue
            if (
                failure.retryable
                and attempt_number >= request.retry_policy.maximum_attempts
            ):
                failure = ProducerExecutionFailureV1.from_code(
                    ProducerFailureCodeV1.RETRY_EXHAUSTED,
                    source_outcome=attempt.failure.source_outcome,
                    source_failure_code=attempt.failure.source_failure_code,
                )
            states.append(ProducerExecutionLifecycleStateV1.FAILED)
            _emit_terminal_failure(self.composition, request, states, failure)
            return _result(request, attempts, states, None, failure)


def compose_producer_compatibility_runtime_v1(
    *,
    request: ProducerExecutionRequestV1,
    executor: ProviderExecutorV2,
    diagnostics_authority,
    clock,
    cancellation_token,
    retry_decider,
    sleeper,
    gateway_projector: ProducerGatewayProjectorV1,
    observer=None,
) -> ProducerCompatibilityRuntimeV1:
    """Create the only explicit entry point for neutral Producer execution."""

    runtime = _validated_runtime_composition(
        request=request,
        executor=executor,
        diagnostics_authority=diagnostics_authority,
        clock=clock,
        cancellation_token=cancellation_token,
        retry_decider=retry_decider,
        sleeper=sleeper,
        gateway_projector=gateway_projector,
        observer=observer,
    )
    if runtime is not None:
        return runtime
    del (
        request,
        executor,
        diagnostics_authority,
        clock,
        cancellation_token,
        retry_decider,
        sleeper,
        gateway_projector,
        observer,
        runtime,
    )
    _raise_configuration_error()


def _validated_runtime_composition(**bindings) -> ProducerCompatibilityRuntimeV1 | None:
    try:
        if bindings["diagnostics_authority"] is None or bindings["clock"] is None:
            return None
        gateway_projector = bindings["gateway_projector"]
        if not callable(getattr(type(gateway_projector), "project", None)):
            return None
        phase_a = compose_producer_compatibility_v1(
            request=bindings["request"],
            executor=bindings["executor"],
            diagnostics_authority=bindings["diagnostics_authority"],
            clock=bindings["clock"],
            observer=bindings["observer"],
            cancellation_token=bindings["cancellation_token"],
            retry_decider=bindings["retry_decider"],
            sleeper=bindings["sleeper"],
            projector=ProducerResultProjectorV1(),
        )
        return ProducerCompatibilityRuntimeV1(
            ProducerCompatibilityCoordinatorV1(phase_a, gateway_projector)
        )
    except (ProducerCompatibilityConfigurationError, TypeError, ValueError):
        return None
    finally:
        bindings.clear()


def _fresh_request(request: ProviderExecutionRequestV2) -> ProviderExecutionRequestV2:
    payload = request.model_dump(mode="python", warnings=False)
    payload["context"]["cancellation"] = {"cancellation_requested": False}
    return ProviderExecutionRequestV2.model_validate(payload, strict=True)


def _validated_lower_result(request, result) -> ProviderExecutionResultV2 | None:
    try:
        payload = result.model_dump(mode="python", warnings=False)
        value = ProviderExecutionResultV2.model_validate(payload, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None
    if (
        value.request_id != request.context.request_id
        or value.provider_id != request.provider.provider_id
        or value.request_envelope_identity != request.request_envelope.identity
        or not _outputs_belong_to_request(request, value)
    ):
        return None
    return value


def _outputs_belong_to_request(
    request: ProviderExecutionRequestV2, result: ProviderExecutionResultV2
) -> bool:
    projection = result.provider_result
    if projection is None:
        return True
    authoritative = tuple(
        (unit.source_request_reference, unit.ordinal)
        for unit in request.request_intent.request_units
    )
    projected = tuple(
        (output.source_request_reference, output.ordinal)
        for output in projection.outputs
    )
    if any(item not in authoritative for item in projected):
        return False
    if projected != tuple(item for item in authoritative if item in projected):
        return False
    return projection.status.value != "success" or projected == authoritative


def _lower_succeeded(result: ProviderExecutionResultV2) -> bool:
    return (
        result.outcome.value == "completed"
        and result.provider_result is not None
        and result.provider_result.status.value == "success"
    )


def _observe(composition, request, result, attempt_number):
    authority = composition.diagnostics_authority
    correlation = correlation_id_for(request, attempt_number=attempt_number)
    try:
        observation = authority.observe(
            correlation_id=correlation,
            attempt_number=attempt_number,
            execution_request_id=result.request_id,
            request_envelope_identity=result.request_envelope_identity,
            result=result,
        )
        if observation is None:
            return None, ProducerCompatibilityEventCodeV1.DIAGNOSTICS_UNAVAILABLE
        observation = ProducerDiagnosticsObservationV1.reconstruct(observation)
        if not observation.correlated_to(
            correlation_id=correlation,
            attempt_number=attempt_number,
            execution_request_id=result.request_id,
            request_envelope_identity=result.request_envelope_identity,
        ):
            raise ValueError
        return observation, ProducerCompatibilityEventCodeV1.DIAGNOSTICS_SAMPLED
    except Exception:  # noqa: BLE001 - diagnostics cannot alter execution
        return None, ProducerCompatibilityEventCodeV1.DIAGNOSTICS_REJECTED


def _projection_observation(request, observation, attempt_number):
    """Adapt Phase A's single-attempt projector without changing its contracts."""

    if observation is None or attempt_number == 1:
        return observation
    return ProducerDiagnosticsObservationV1(
        correlation_id=correlation_id_for(request, attempt_number=1),
        attempt_number=1,
        execution_request_id=observation.execution_request_id,
        request_envelope_identity=observation.request_envelope_identity,
        usage=observation.usage,
        provider_request_id=observation.provider_request_id,
        returned_model_id=observation.returned_model_id,
    )


def _clock_sample(clock) -> int | None:
    try:
        value = clock.read_monotonic_ns()
        return value if type(value) is int and value >= 0 else None
    except Exception:  # noqa: BLE001 - clock failure means unavailable latency
        return None


def _latency(start: int | None, stop: int | None) -> str | None:
    if start is None or stop is None or stop < start:
        return None
    value = Decimal(stop - start) / Decimal(1_000_000)
    return _decimal_text(value)


def _cancelled(token) -> bool:
    try:
        return token.is_cancelled() is not False
    except Exception:  # noqa: BLE001 - cancellation fails closed
        return True


def _retry(composition, request, failure, attempt_number) -> bool:
    if not failure.retryable or attempt_number >= request.retry_policy.maximum_attempts:
        return False
    code = failure.diagnostic_code
    policy = request.retry_policy
    allowed = (
        (code is ProducerFailureCodeV1.PROVIDER_TIMEOUT and policy.retry_timeouts)
        or (
            code is ProducerFailureCodeV1.PROVIDER_RATE_LIMITED
            and policy.retry_rate_limits
        )
        or (
            code
            in {
                ProducerFailureCodeV1.PROVIDER_TRANSPORT_FAILED,
                ProducerFailureCodeV1.PROVIDER_UNAVAILABLE,
            }
            and policy.retry_transport_errors
        )
    )
    if not allowed:
        return False
    try:
        return (
            composition.retry_decider.should_retry(
                failure=failure,
                attempt_number=attempt_number,
                policy=policy,
            )
            is True
        )
    except Exception:  # noqa: BLE001 - retry authority fails closed
        return False


def _failed_attempt(request, number, failure, latency):
    unavailable = ProducerDiagnosticAuthorityV1.UNAVAILABLE
    diagnostics = ProducerAttemptDiagnosticsV1(
        usage=None,
        usage_authority=unavailable,
        latency_ms=latency,
        latency_authority=(
            ProducerDiagnosticAuthorityV1.COMPATIBILITY_CLOCK
            if latency is not None
            else unavailable
        ),
        provider_request_id=None,
        provider_request_id_authority=unavailable,
        returned_model_id=None,
        returned_model_id_authority=unavailable,
        finish_metadata=(),
        finish_metadata_authority=unavailable,
    )
    return ProducerExecutionAttemptV1.build(
        attempt_number=number,
        execution_request_id=request.context.request_id,
        request_envelope_identity=request.request_envelope.identity,
        timeout_seconds=request.timeout_policy.timeout_seconds,
        cancellation_requested=False,
        outcome=None,
        succeeded=False,
        failure=failure,
        diagnostics=diagnostics,
    )


def _successful_attempt(request, result, number, observation, latency):
    unavailable = ProducerDiagnosticAuthorityV1.UNAVAILABLE
    application = ProducerDiagnosticAuthorityV1.APPLICATION_DIAGNOSTICS_AUTHORITY
    finish = tuple(
        ProducerFinishMetadataV1(
            source_request_reference=output.source_request_reference,
            ordinal=output.ordinal,
            finish_reason=output.finish_reason,
        )
        for output in result.provider_result.outputs
    )
    diagnostics = ProducerAttemptDiagnosticsV1(
        usage=observation.usage if observation else None,
        usage_authority=(
            application if observation and observation.usage else unavailable
        ),
        latency_ms=latency,
        latency_authority=(
            ProducerDiagnosticAuthorityV1.COMPATIBILITY_CLOCK
            if latency is not None
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
        finish_metadata=finish,
        finish_metadata_authority=ProducerDiagnosticAuthorityV1.PROVIDER_RESULT,
    )
    return ProducerExecutionAttemptV1.build(
        attempt_number=number,
        execution_request_id=request.context.request_id,
        request_envelope_identity=request.request_envelope.identity,
        timeout_seconds=request.timeout_policy.timeout_seconds,
        cancellation_requested=False,
        outcome=result.outcome,
        succeeded=True,
        failure=None,
        diagnostics=diagnostics,
    )


def _cancelled_result(composition, request, states, attempts):
    states.append(ProducerExecutionLifecycleStateV1.CANCELLED)
    lower_cancellation = (
        attempts[-1]
        if attempts
        and attempts[-1].outcome is not None
        and attempts[-1].outcome.value == "cancelled"
        else None
    )
    failure = ProducerExecutionFailureV1.from_code(
        ProducerFailureCodeV1.PRODUCER_EXECUTION_CANCELLED,
        source_outcome=(
            lower_cancellation.failure.source_outcome if lower_cancellation else None
        ),
        source_failure_code=(
            lower_cancellation.failure.source_failure_code
            if lower_cancellation
            else None
        ),
    )
    _emit(
        composition,
        request,
        ProducerCompatibilityEventCodeV1.EXECUTION_CANCELLED,
        states[-1],
        diagnostic_code=failure.diagnostic_code,
    )
    return _result(request, attempts, states, None, failure)


def _aggregate_usage(attempts):
    values = [item.diagnostics.usage for item in attempts]
    if not values or any(value is None for value in values):
        return None
    fields = ("prompt_tokens", "completion_tokens", "total_tokens")
    totals = {
        name: (
            sum(getattr(value, name) for value in values)
            if all(getattr(value, name) is not None for value in values)
            else None
        )
        for name in fields
    }
    costs = [value.estimated_cost for value in values]
    versions = [value.pricing_version for value in values]
    if all(cost is not None for cost in costs) and len(set(versions)) == 1:
        cost = _decimal_text(sum(Decimal(item) for item in costs))
        version = versions[0]
    else:
        cost = version = None
    if all(value is None for value in totals.values()) and cost is None:
        return None
    return ProducerTokenUsageV1(**totals, estimated_cost=cost, pricing_version=version)


def _result(request, attempts, states, gateway, failure):
    terminal = states[-1]
    unavailable = ProducerDiagnosticAuthorityV1.UNAVAILABLE
    coordinator = ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
    terminal_diagnostics = attempts[-1].diagnostics if attempts else None
    usage = _aggregate_usage(attempts)
    latencies = [item.diagnostics.latency_ms for item in attempts]
    latency = (
        _decimal_text(sum(Decimal(value) for value in latencies))
        if attempts and all(value is not None for value in latencies)
        else None
    )
    diagnostics = ProducerExecutionDiagnosticsV1(
        usage=usage,
        usage_authority=coordinator if usage is not None else unavailable,
        latency_ms=latency,
        latency_authority=coordinator if latency is not None else unavailable,
        provider_request_id=(
            terminal_diagnostics.provider_request_id if terminal_diagnostics else None
        ),
        provider_request_id_authority=(
            terminal_diagnostics.provider_request_id_authority
            if terminal_diagnostics
            else unavailable
        ),
        returned_model_id=(
            terminal_diagnostics.returned_model_id if terminal_diagnostics else None
        ),
        returned_model_id_authority=(
            terminal_diagnostics.returned_model_id_authority
            if terminal_diagnostics
            else unavailable
        ),
        finish_metadata=(
            terminal_diagnostics.finish_metadata if terminal_diagnostics else ()
        ),
        finish_metadata_authority=(
            terminal_diagnostics.finish_metadata_authority
            if terminal_diagnostics
            else unavailable
        ),
        retryable=failure.retryable if failure is not None else None,
        retryability_authority=coordinator if failure is not None else unavailable,
        attempt_count=len(attempts),
        attempt_count_authority=coordinator,
        lifecycle_state=terminal,
        lifecycle_authority=coordinator,
    )
    lifecycle = ProducerExecutionLifecycleV1(
        states=tuple(states), terminal_state=terminal
    )
    status = {
        ProducerExecutionLifecycleStateV1.SUCCEEDED: AIProviderExecutionStatus.SUCCESS,
        ProducerExecutionLifecycleStateV1.FAILED: AIProviderExecutionStatus.FAILED,
        ProducerExecutionLifecycleStateV1.CANCELLED: AIProviderExecutionStatus.CANCELLED,
    }[terminal]
    return ProducerExecutionResultV1.build(
        request_reference=request.request_reference,
        request_fingerprint=request.request_fingerprint,
        invocation_reference=request.invocation_reference,
        invocation_fingerprint=request.invocation_fingerprint,
        status=status,
        gateway_result=gateway,
        diagnostics=diagnostics,
        failure=failure,
        attempts=tuple(attempts),
        lifecycle=lifecycle,
    )


def _emit_terminal_failure(composition, request, states, failure):
    _emit(
        composition,
        request,
        ProducerCompatibilityEventCodeV1.EXECUTION_FAILED,
        states[-1],
        diagnostic_code=failure.diagnostic_code,
    )


def _emit(
    composition,
    request,
    code,
    state,
    attempt_number=None,
    diagnostic_code=None,
):
    observer = composition.observer
    if observer is None:
        return
    try:
        observer.emit(
            ProducerCompatibilityEventV1(
                event_code=code,
                request_reference=request.request_reference,
                attempt_number=attempt_number,
                diagnostic_code=diagnostic_code,
                lifecycle_state=state,
            )
        )
    except Exception:  # noqa: BLE001 - observers cannot alter execution
        _discard_authority_failure()


def _discard_authority_failure() -> None:
    """Make intentional authority-failure suppression explicit."""


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _raise_configuration_error() -> None:
    raise ProducerCompatibilityConfigurationError from None


__all__ = ()
