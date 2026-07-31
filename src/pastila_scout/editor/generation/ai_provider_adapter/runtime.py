"""Canonical provider-neutral AI Provider Adapter execution runtime."""

# Raw projector/client/interpreter/observer failures are deliberately normalized here.
# ruff: noqa: BLE001,S110

from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import SecretStr

from pastila_scout.editor.generation.revision import ControlledRevisionGatewayResult

from .contracts import (
    AIProviderClientResponse,
    AIProviderConfiguration,
    AIRetryPolicy,
)
from .errors import (
    AIProviderAuthenticationError,
    AIProviderAuthorizationError,
    AIProviderMalformedResponseError,
    AIProviderRateLimitError,
    AIProviderSchemaViolationError,
    AIProviderTimeoutError,
    AIProviderTransportError,
    AIProviderUnavailableError,
    AIProviderUnsupportedCapabilityError,
)
from .runtime_models import (
    AIProviderAggregatedUsage,
    AIProviderExecutionAttempt,
    AIProviderExecutionDiagnostic,
    AIProviderExecutionEvent,
    AIProviderExecutionFailureKind,
    AIProviderExecutionLifecycle,
    AIProviderExecutionPhase,
    AIProviderExecutionRequest,
    AIProviderExecutionResult,
    AIProviderExecutionSafeReport,
    AIProviderExecutionStatus,
    AIProviderInterpretationFailure,
    AIProviderInterpretationResult,
    AIProviderNormalizedError,
    AIProviderObservabilityEventCode,
    AIProviderRetryDecision,
    ProjectedAIProviderRequest,
)


class AIProviderRequestProjector(Protocol):
    def project(
        self, request: AIProviderExecutionRequest
    ) -> ProjectedAIProviderRequest: ...


class AIProviderResponseInterpreter(Protocol):
    def interpret(
        self,
        request: AIProviderExecutionRequest,
        response: AIProviderClientResponse,
    ) -> AIProviderInterpretationResult: ...


class AIProviderExceptionNormalizer(Protocol):
    def normalize(self, error: BaseException) -> AIProviderNormalizedError: ...


class AIProviderRetryDecider(Protocol):
    def decide(
        self,
        error: AIProviderNormalizedError,
        attempt_number: int,
        policy: AIRetryPolicy,
    ) -> AIProviderRetryDecision: ...


class AIProviderBackoffStrategy(Protocol):
    def delay_seconds(self, attempt_number: int, policy: AIRetryPolicy) -> float: ...


class AIProviderSleeper(Protocol):
    def sleep(self, delay_seconds: float) -> None: ...


class AIProviderCancellationToken(Protocol):
    def is_cancelled(self) -> bool: ...


class AIProviderExecutionObserver(Protocol):
    def emit(self, event: AIProviderExecutionEvent) -> None: ...


class CanonicalAIProviderExceptionNormalizer:
    """Map known neutral failures and sanitize every unknown client exception."""

    def normalize(self, error: BaseException) -> AIProviderNormalizedError:
        mappings = (
            (
                AIProviderAuthenticationError,
                AIProviderExecutionFailureKind.CLIENT,
                "authentication_failed",
                False,
            ),
            (
                AIProviderAuthorizationError,
                AIProviderExecutionFailureKind.CLIENT,
                "authorization_failed",
                False,
            ),
            (
                AIProviderTimeoutError,
                AIProviderExecutionFailureKind.CLIENT,
                "provider_timeout",
                True,
            ),
            (
                AIProviderRateLimitError,
                AIProviderExecutionFailureKind.CLIENT,
                "provider_rate_limited",
                True,
            ),
            (
                AIProviderTransportError,
                AIProviderExecutionFailureKind.CLIENT,
                "provider_transport_failed",
                True,
            ),
            (
                AIProviderUnavailableError,
                AIProviderExecutionFailureKind.CLIENT,
                "provider_unavailable",
                True,
            ),
            (
                AIProviderMalformedResponseError,
                AIProviderExecutionFailureKind.CLIENT,
                "provider_response_malformed",
                False,
            ),
            (
                AIProviderSchemaViolationError,
                AIProviderExecutionFailureKind.SCHEMA,
                "provider_schema_violation",
                False,
            ),
            (
                AIProviderUnsupportedCapabilityError,
                AIProviderExecutionFailureKind.UNSUPPORTED_CAPABILITY,
                "provider_capability_unsupported",
                False,
            ),
        )
        for error_type, category, code, retryable in mappings:
            if isinstance(error, error_type):
                return AIProviderNormalizedError(
                    category=category, diagnostic_code=code, retryable=retryable
                )
        return AIProviderNormalizedError(
            category=AIProviderExecutionFailureKind.INTERNAL,
            diagnostic_code="provider_internal_failure",
            retryable=False,
        )


class CanonicalAIProviderRetryDecider:
    def decide(self, error, attempt_number, policy):
        enabled = error.retryable
        if error.diagnostic_code == "provider_timeout":
            enabled = policy.retry_timeouts
        elif error.diagnostic_code == "provider_rate_limited":
            enabled = policy.retry_rate_limits
        elif error.diagnostic_code in (
            "provider_transport_failed",
            "provider_unavailable",
        ):
            enabled = policy.retry_transport_errors
        retry = enabled and attempt_number < policy.maximum_attempts
        return AIProviderRetryDecision(
            retry=retry,
            delay_seconds=policy.delay_seconds if retry else 0,
            reason_code="retry_scheduled" if retry else "retry_not_permitted",
        )


class ConstantAIProviderBackoff:
    def delay_seconds(self, attempt_number, policy):
        return policy.delay_seconds


class NoOpAIProviderSleeper:
    def sleep(self, delay_seconds):
        return None


class NeverCancelledAIProviderToken:
    def is_cancelled(self):
        return False


class _ResolvedCredentialProvider:
    def __init__(self, reference: str, credential: SecretStr):
        self.reference = reference
        self.credential = credential

    def resolve(self, authentication_reference: str) -> SecretStr:
        if authentication_reference != self.reference:
            raise AIProviderAuthenticationError("credential reference mismatch")
        return self.credential


class AIProviderAdapterRuntime:
    """Project once, coordinate transport attempts, and interpret at most once."""

    def __init__(
        self,
        *,
        configuration,
        client,
        credential_provider,
        projector,
        interpreter,
        exception_normalizer,
        retry_decider,
        backoff_strategy,
        sleeper,
        cancellation_token,
        observer=None,
    ):
        self.configuration = configuration
        self.client = client
        self.credential_provider = credential_provider
        self.projector = projector
        self.interpreter = interpreter
        self.exception_normalizer = exception_normalizer
        self.retry_decider = retry_decider
        self.backoff_strategy = backoff_strategy
        self.sleeper = sleeper
        self.cancellation_token = cancellation_token
        self.observer = observer

    def execute(self, invocation) -> AIProviderExecutionResult:
        request = AIProviderExecutionRequest(
            execution_identifier=_execution_identifier(
                invocation.invocation_fingerprint, self.configuration
            ),
            invocation=invocation,
            provider_identifier=self.configuration.provider_identifier,
            model_identifier=self.configuration.model_identifier,
            correlation_identifier=invocation.invocation_fingerprint,
        )
        phases = [AIProviderExecutionPhase.ACCEPTED]
        attempts = []
        usage = []
        self._emit(request, AIProviderObservabilityEventCode.EXECUTION_STARTED)
        if self.cancellation_token.is_cancelled():
            return self._cancelled(request, phases, attempts, usage)
        try:
            AIProviderConfiguration.model_validate(
                self.configuration.model_dump(mode="python")
            )
        except Exception:
            return self._failed(
                request,
                phases,
                attempts,
                usage,
                AIProviderExecutionFailureKind.CONFIGURATION,
                "provider_configuration_invalid",
            )
        try:
            projected = self.projector.project(request)
            if not isinstance(projected, ProjectedAIProviderRequest):
                raise TypeError("invalid projected provider request")
            if projected.invocation is not request.invocation:
                raise ValueError("projection invocation identity mismatch")
            if projected.invocation_fingerprint != invocation.invocation_fingerprint:
                raise ValueError("projection lineage mismatch")
        except Exception:
            return self._failed(
                request,
                phases,
                attempts,
                usage,
                AIProviderExecutionFailureKind.PROJECTION,
                "provider_projection_failed",
            )
        phases.append(AIProviderExecutionPhase.PROJECTED)
        self._emit(request, AIProviderObservabilityEventCode.PROJECTION_COMPLETED)
        self._emit(request, AIProviderObservabilityEventCode.PROJECTION_VALIDATED)
        self._emit(
            request, AIProviderObservabilityEventCode.CREDENTIAL_RESOLUTION_STARTED
        )
        try:
            credential = self.credential_provider.resolve(
                self.configuration.authentication_reference
            )
            if not isinstance(credential, SecretStr):
                raise TypeError("credential provider returned an invalid value")
            resolved_credentials = _ResolvedCredentialProvider(
                self.configuration.authentication_reference, credential
            )
        except Exception:
            return self._failed(
                request,
                phases,
                attempts,
                usage,
                AIProviderExecutionFailureKind.CREDENTIAL,
                "provider_credential_resolution_failed",
            )
        phases.append(AIProviderExecutionPhase.CREDENTIAL_READY)
        self._emit(
            request,
            AIProviderObservabilityEventCode.CREDENTIAL_RESOLUTION_COMPLETED,
        )
        accepted_response = None
        for number in range(1, self.configuration.retry_policy.maximum_attempts + 1):
            if self.cancellation_token.is_cancelled():
                return self._cancelled(request, phases, attempts, usage)
            phases.append(AIProviderExecutionPhase.ATTEMPTING)
            self._emit(
                request, AIProviderObservabilityEventCode.ATTEMPT_STARTED, number
            )
            try:
                accepted_response = self.client.send(
                    projected.client_request, credential_provider=resolved_credentials
                )
                if not isinstance(accepted_response, AIProviderClientResponse):
                    raise AIProviderMalformedResponseError("invalid client response")
                attempts.append(
                    AIProviderExecutionAttempt(
                        attempt_number=number,
                        succeeded=True,
                    )
                )
                self._emit(
                    request, AIProviderObservabilityEventCode.ATTEMPT_SUCCEEDED, number
                )
                break
            except Exception as raw_error:
                normalized = self.exception_normalizer.normalize(raw_error)
                if normalized.usage:
                    usage.append(normalized.usage)
                attempts.append(
                    AIProviderExecutionAttempt(
                        attempt_number=number,
                        succeeded=False,
                        diagnostic_code=normalized.diagnostic_code,
                        usage=normalized.usage,
                    )
                )
                self._emit(
                    request,
                    AIProviderObservabilityEventCode.ATTEMPT_FAILED,
                    number,
                    normalized.diagnostic_code,
                )
                decision = self.retry_decider.decide(
                    normalized, number, self.configuration.retry_policy
                )
                if not decision.retry:
                    kind = (
                        AIProviderExecutionFailureKind.RETRY_EXHAUSTED
                        if normalized.retryable
                        and number >= self.configuration.retry_policy.maximum_attempts
                        else normalized.category
                    )
                    return self._failed(
                        request,
                        phases,
                        attempts,
                        usage,
                        kind,
                        normalized.diagnostic_code,
                    )
                self._emit(
                    request, AIProviderObservabilityEventCode.RETRY_SCHEDULED, number
                )
                phases.append(AIProviderExecutionPhase.RETRY_WAIT)
                delay = self.backoff_strategy.delay_seconds(
                    number, self.configuration.retry_policy
                )
                self._emit(
                    request, AIProviderObservabilityEventCode.BACKOFF_STARTED, number
                )
                self.sleeper.sleep(delay)
                self._emit(
                    request, AIProviderObservabilityEventCode.BACKOFF_COMPLETED, number
                )
        phases.append(AIProviderExecutionPhase.INTERPRETING)
        if self.cancellation_token.is_cancelled():
            return self._cancelled(request, phases[:-1], attempts, usage)
        self._emit(request, AIProviderObservabilityEventCode.INTERPRETATION_STARTED)
        try:
            interpretation = self.interpreter.interpret(request, accepted_response)
            if not isinstance(interpretation, AIProviderInterpretationResult):
                raise TypeError("invalid provider interpretation result")
            interpretation.safe_and_canonical()
            gateway_result = interpretation.gateway_result
            if not isinstance(gateway_result, ControlledRevisionGatewayResult):
                raise TypeError("invalid interpreted gateway result")
        except Exception as error:
            if isinstance(error, AIProviderInterpretationFailure):
                kind = error.failure_kind
                code = error.diagnostic_code
            elif isinstance(error, AIProviderSchemaViolationError):
                kind = AIProviderExecutionFailureKind.SCHEMA
                code = "provider_schema_violation"
            else:
                kind = AIProviderExecutionFailureKind.INTERPRETATION
                code = "provider_interpretation_failed"
            return self._failed(request, phases, attempts, usage, kind, code)
        self._emit(request, AIProviderObservabilityEventCode.INTERPRETATION_COMPLETED)
        if interpretation.usage:
            usage.append(interpretation.usage)
        self._emit(request, AIProviderObservabilityEventCode.USAGE_AGGREGATED)
        phases.append(AIProviderExecutionPhase.SUCCEEDED)
        self._emit(request, AIProviderObservabilityEventCode.EXECUTION_SUCCEEDED)
        return AIProviderExecutionResult(
            request=request,
            status=AIProviderExecutionStatus.SUCCESS,
            gateway_result=gateway_result,
            interpretation_result=interpretation,
            attempts=tuple(attempts),
            usage=_aggregate(usage, len(attempts)),
            lifecycle=AIProviderExecutionLifecycle(phases=tuple(phases)),
        )

    def _failed(self, request, phases, attempts, usage, kind, code):
        phases.append(AIProviderExecutionPhase.FAILED)
        self._emit(
            request,
            AIProviderObservabilityEventCode.EXECUTION_FAILED,
            diagnostic_code=code,
        )
        return AIProviderExecutionResult(
            request=request,
            status=AIProviderExecutionStatus.FAILED,
            attempts=tuple(attempts),
            usage=_aggregate(usage, len(attempts)),
            lifecycle=AIProviderExecutionLifecycle(phases=tuple(phases)),
            diagnostic=AIProviderExecutionDiagnostic(
                failure_kind=kind,
                diagnostic_code=code,
                safe_message="AI provider execution failed.",
            ),
        )

    def _cancelled(self, request, phases, attempts, usage):
        phases.append(AIProviderExecutionPhase.CANCELLED)
        self._emit(request, AIProviderObservabilityEventCode.EXECUTION_CANCELLED)
        return AIProviderExecutionResult(
            request=request,
            status=AIProviderExecutionStatus.CANCELLED,
            attempts=tuple(attempts),
            usage=_aggregate(usage, len(attempts)),
            lifecycle=AIProviderExecutionLifecycle(phases=tuple(phases)),
            diagnostic=AIProviderExecutionDiagnostic(
                failure_kind=AIProviderExecutionFailureKind.CANCELLATION,
                diagnostic_code="provider_execution_cancelled",
                safe_message="AI provider execution was cancelled.",
            ),
        )

    def _emit(self, request, code, attempt_number=None, diagnostic_code=None):
        if self.observer is None:
            return
        try:
            self.observer.emit(
                AIProviderExecutionEvent(
                    code=code,
                    execution_identifier=request.execution_identifier,
                    attempt_number=attempt_number,
                    diagnostic_code=diagnostic_code,
                )
            )
        except Exception:
            pass


def build_ai_provider_execution_safe_report(result):
    interpretation = result.interpretation_result
    return AIProviderExecutionSafeReport(
        execution_identifier=result.request.execution_identifier,
        provider_identifier=result.request.provider_identifier,
        model_identifier=result.request.model_identifier,
        provider_model_identifier=(
            interpretation.provider_model_identifier if interpretation else None
        ),
        provider_request_identifier=(
            interpretation.provider_request_identifier if interpretation else None
        ),
        status=result.status,
        attempt_count=len(result.attempts),
        retry_count=max(0, len(result.attempts) - 1),
        diagnostic_code=(
            result.diagnostic.diagnostic_code if result.diagnostic else None
        ),
        lifecycle=tuple(item.value for item in result.lifecycle.phases),
        usage=result.usage,
        correlation_identifier=result.request.correlation_identifier,
        metadata=interpretation.metadata if interpretation else (),
    )


def serialize_ai_provider_execution_safe_report(report):
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _aggregate(usages, attempt_count):
    costs = [item.estimated_cost for item in usages if item.estimated_cost is not None]
    return AIProviderAggregatedUsage(
        prompt_tokens=sum(item.prompt_tokens or 0 for item in usages),
        completion_tokens=sum(item.completion_tokens or 0 for item in usages),
        total_tokens=sum(item.total_tokens or 0 for item in usages),
        estimated_cost=sum(costs) if costs else None,
        cumulative_latency_ms=sum(item.latency_ms or 0 for item in usages),
        attempt_count=attempt_count,
    )


def _execution_identifier(invocation_fingerprint, configuration):
    raw = json.dumps(
        {
            "invocation": invocation_fingerprint,
            "provider": configuration.provider_identifier,
            "model": configuration.model_identifier,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
