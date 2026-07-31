"""Immutable contracts for canonical AI Provider Adapter execution."""

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.generation.revision import (
    ControlledRevisionGatewayResult,
    ControlledRevisionInvocation,
)

from .contracts import AIProviderClientRequest, AIProviderUsage


class AIProviderExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIProviderExecutionFailureKind(StrEnum):
    PROJECTION = "projection_failure"
    CREDENTIAL = "credential_resolution_failure"
    CONFIGURATION = "configuration_failure"
    CLIENT = "client_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
    CANCELLATION = "cancellation"
    INTERPRETATION = "interpretation_failure"
    MALFORMED_RESPONSE = "malformed_provider_response"
    REFUSAL = "provider_refusal"
    INCOMPLETE_RESPONSE = "incomplete_provider_response"
    UNSUPPORTED_OUTPUT = "unsupported_provider_output"
    MISSING_STRUCTURED_OUTPUT = "missing_structured_output"
    INVALID_GATEWAY_PROJECTION = "invalid_gateway_projection"
    UNSAFE_METADATA = "unsafe_metadata"
    MALFORMED_USAGE = "malformed_usage"
    SCHEMA = "schema_failure"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    INTERNAL = "internal_failure"


class AIProviderExecutionPhase(StrEnum):
    ACCEPTED = "accepted"
    PROJECTED = "projected"
    CREDENTIAL_READY = "credential_ready"
    ATTEMPTING = "attempting"
    RETRY_WAIT = "retry_wait"
    INTERPRETING = "interpreting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIProviderObservabilityEventCode(StrEnum):
    EXECUTION_STARTED = "execution_started"
    PROJECTION_COMPLETED = "projection_completed"
    PROJECTION_VALIDATED = "projection_validated"
    CREDENTIAL_RESOLUTION_STARTED = "credential_resolution_started"
    CREDENTIAL_RESOLUTION_COMPLETED = "credential_resolution_completed"
    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_SUCCEEDED = "attempt_succeeded"
    ATTEMPT_FAILED = "attempt_failed"
    RETRY_SCHEDULED = "retry_scheduled"
    BACKOFF_STARTED = "backoff_started"
    BACKOFF_COMPLETED = "backoff_completed"
    INTERPRETATION_STARTED = "interpretation_started"
    INTERPRETATION_COMPLETED = "interpretation_completed"
    USAGE_AGGREGATED = "usage_aggregated"
    EXECUTION_SUCCEEDED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"


class AIProviderExecutionRequest(FrozenModel):
    execution_version: str = "1"
    execution_identifier: str
    invocation: ControlledRevisionInvocation = Field(repr=False)
    provider_identifier: str
    model_identifier: str
    correlation_identifier: str | None = None


class ProjectedAIProviderRequest(FrozenModel):
    projection_version: str = "1"
    invocation: ControlledRevisionInvocation = Field(repr=False)
    invocation_fingerprint: str
    client_request: AIProviderClientRequest = Field(repr=False)

    @model_validator(mode="after")
    def lineage(self):
        if self.projection_version != "1":
            raise ValueError("unsupported projected provider-request version")
        if self.invocation_fingerprint != self.invocation.invocation_fingerprint:
            raise ValueError("projected provider-request fingerprint is inconsistent")
        return self


class AIProviderInterpretationResult(FrozenModel):
    """Interpreter-owned gateway projection and safe infrastructure metadata."""

    interpretation_version: str = "1"
    gateway_result: ControlledRevisionGatewayResult = Field(repr=False)
    usage: AIProviderUsage | None = None
    provider_request_identifier: str | None = Field(default=None, max_length=200)
    provider_model_identifier: str | None = Field(default=None, max_length=200)
    metadata: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def safe_and_canonical(self):
        if self.interpretation_version != "1":
            raise ValueError("unsupported interpretation-result version")
        keys = tuple(key for key, _ in self.metadata)
        if len(set(keys)) != len(keys) or self.metadata != tuple(sorted(self.metadata)):
            raise ValueError("interpretation metadata is not canonical")
        values = (
            *(f"{key}={value}" for key, value in self.metadata),
            self.provider_request_identifier or "",
            self.provider_model_identifier or "",
        )
        forbidden = (
            "api_key",
            "bearer ",
            "authorization",
            "cookie",
            "credential",
            "secret",
            "traceback",
            "c:\\",
            "/home/",
            "source_draft",
            "revision_instruction",
            "prompt=",
            "payload=",
            "response_body",
        )
        if any(token in " ".join(values).casefold() for token in forbidden):
            raise ValueError("interpretation metadata contains unsafe content")
        return self


class AIProviderNormalizedError(FrozenModel):
    category: AIProviderExecutionFailureKind
    diagnostic_code: str = Field(min_length=1, max_length=100)
    retryable: bool
    usage: AIProviderUsage | None = None
    metadata: tuple[tuple[str, str], ...] = ()


class AIProviderInterpretationFailure(Exception):
    """Safe provider-neutral signal emitted by a concrete interpreter."""

    def __init__(
        self,
        failure_kind: AIProviderExecutionFailureKind,
        diagnostic_code: str,
    ) -> None:
        super().__init__(diagnostic_code)
        self.failure_kind = failure_kind
        self.diagnostic_code = diagnostic_code


class AIProviderRetryDecision(FrozenModel):
    retry: bool
    delay_seconds: float = Field(ge=0)
    reason_code: str


class AIProviderExecutionAttempt(FrozenModel):
    attempt_number: int = Field(ge=1)
    succeeded: bool
    diagnostic_code: str | None = None
    usage: AIProviderUsage | None = None


class AIProviderAggregatedUsage(FrozenModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    cumulative_latency_ms: float = Field(ge=0)
    attempt_count: int = Field(ge=0)


class AIProviderExecutionLifecycle(FrozenModel):
    phases: tuple[AIProviderExecutionPhase, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def terminal(self):
        if self.phases[0] is not AIProviderExecutionPhase.ACCEPTED:
            raise ValueError("AI provider lifecycle must start at accepted")
        if self.phases[-1] not in (
            AIProviderExecutionPhase.SUCCEEDED,
            AIProviderExecutionPhase.FAILED,
            AIProviderExecutionPhase.CANCELLED,
        ):
            raise ValueError("AI provider lifecycle lacks a terminal phase")
        transitions = {
            AIProviderExecutionPhase.ACCEPTED: {
                AIProviderExecutionPhase.PROJECTED,
                AIProviderExecutionPhase.FAILED,
                AIProviderExecutionPhase.CANCELLED,
            },
            AIProviderExecutionPhase.PROJECTED: {
                AIProviderExecutionPhase.CREDENTIAL_READY,
                AIProviderExecutionPhase.FAILED,
                AIProviderExecutionPhase.CANCELLED,
            },
            AIProviderExecutionPhase.CREDENTIAL_READY: {
                AIProviderExecutionPhase.ATTEMPTING,
                AIProviderExecutionPhase.FAILED,
                AIProviderExecutionPhase.CANCELLED,
            },
            AIProviderExecutionPhase.ATTEMPTING: {
                AIProviderExecutionPhase.RETRY_WAIT,
                AIProviderExecutionPhase.INTERPRETING,
                AIProviderExecutionPhase.FAILED,
                AIProviderExecutionPhase.CANCELLED,
            },
            AIProviderExecutionPhase.RETRY_WAIT: {
                AIProviderExecutionPhase.ATTEMPTING,
                AIProviderExecutionPhase.FAILED,
                AIProviderExecutionPhase.CANCELLED,
            },
            AIProviderExecutionPhase.INTERPRETING: {
                AIProviderExecutionPhase.SUCCEEDED,
                AIProviderExecutionPhase.FAILED,
            },
        }
        if any(
            following not in transitions.get(current, set())
            for current, following in zip(self.phases, self.phases[1:], strict=False)
        ):
            raise ValueError("AI provider lifecycle transition is invalid")
        return self


class AIProviderExecutionDiagnostic(FrozenModel):
    failure_kind: AIProviderExecutionFailureKind
    diagnostic_code: str = Field(min_length=1, max_length=100)
    safe_message: str = Field(min_length=1, max_length=200)


class AIProviderExecutionResult(FrozenModel):
    result_version: str = "1"
    request: AIProviderExecutionRequest = Field(repr=False)
    status: AIProviderExecutionStatus
    gateway_result: ControlledRevisionGatewayResult | None = Field(
        default=None, repr=False
    )
    interpretation_result: AIProviderInterpretationResult | None = Field(
        default=None, repr=False
    )
    attempts: tuple[AIProviderExecutionAttempt, ...]
    usage: AIProviderAggregatedUsage
    lifecycle: AIProviderExecutionLifecycle
    diagnostic: AIProviderExecutionDiagnostic | None = None

    @model_validator(mode="after")
    def shape(self):
        success = self.status is AIProviderExecutionStatus.SUCCESS
        if success != (self.gateway_result is not None) or success == (
            self.diagnostic is not None
        ):
            raise ValueError("AI provider execution-result shape is inconsistent")
        if success != (self.interpretation_result is not None):
            raise ValueError("AI provider interpretation-result shape is inconsistent")
        if (
            success
            and self.gateway_result is not self.interpretation_result.gateway_result
        ):
            raise ValueError("AI provider gateway-result identity is inconsistent")
        if self.usage.attempt_count != len(self.attempts):
            raise ValueError("AI provider execution attempt count is inconsistent")
        return self


class AIProviderExecutionEvent(FrozenModel):
    code: AIProviderObservabilityEventCode
    execution_identifier: str
    attempt_number: int | None = None
    diagnostic_code: str | None = None


class AIProviderExecutionSafeReport(FrozenModel):
    report_version: str = "1"
    execution_identifier: str
    provider_identifier: str
    model_identifier: str
    provider_model_identifier: str | None
    provider_request_identifier: str | None
    status: AIProviderExecutionStatus
    attempt_count: int
    retry_count: int
    diagnostic_code: str | None
    lifecycle: tuple[str, ...]
    usage: AIProviderAggregatedUsage
    correlation_identifier: str | None
    metadata: tuple[tuple[str, str], ...]


def opaque_payload(value: Any) -> Any:
    """Typing marker: payloads remain uninterpreted by this runtime."""

    return value
