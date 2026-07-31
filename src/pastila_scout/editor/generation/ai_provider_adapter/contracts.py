"""Immutable, provider-neutral AI Provider Adapter contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, SecretStr, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.generation.revision import (
    ControlledRevisionGatewayResult,
    ControlledRevisionInvocation,
)

from .errors import AIProviderAdapterError


class AIStructuredOutputMode(StrEnum):
    JSON = "json"
    TOOL_CALL = "tool_call"
    SCHEMA_CONSTRAINED = "schema_constrained"
    PROVIDER_SPECIFIC = "provider_specific"


class AIRetryPolicy(FrozenModel):
    """Adapter-owned retry limits; a client call is always one transport attempt."""

    maximum_attempts: int = Field(default=1, ge=1)
    delay_seconds: float = Field(default=0.0, ge=0)
    retry_timeouts: bool = True
    retry_rate_limits: bool = True
    retry_transport_errors: bool = True


class AIRateLimitPolicy(FrozenModel):
    maximum_requests_per_minute: int | None = Field(default=None, ge=1)
    maximum_tokens_per_minute: int | None = Field(default=None, ge=1)


class AIStructuredOutputCapabilities(FrozenModel):
    supported_modes: tuple[AIStructuredOutputMode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def canonical_modes(self):
        if len(set(self.supported_modes)) != len(self.supported_modes):
            raise ValueError("structured-output modes contain duplicates")
        if self.supported_modes != tuple(
            sorted(self.supported_modes, key=lambda value: value.value)
        ):
            raise ValueError("structured-output modes are not canonical")
        return self


class AIProviderConfiguration(FrozenModel):
    """Secret-free immutable configuration shared by future AI adapters."""

    configuration_version: str = "1"
    provider_identifier: str = Field(min_length=1, max_length=100)
    model_identifier: str = Field(min_length=1, max_length=200)
    endpoint: str | None = Field(default=None, max_length=2048)
    authentication_reference: str = Field(min_length=1, max_length=200)
    timeout_seconds: float = Field(default=30.0, gt=0)
    retry_policy: AIRetryPolicy = Field(default_factory=AIRetryPolicy)
    rate_limit_policy: AIRateLimitPolicy = Field(default_factory=AIRateLimitPolicy)
    structured_output: AIStructuredOutputCapabilities
    supports_streaming: bool = False
    maximum_context_tokens: int = Field(gt=0)
    metadata: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def safe_and_canonical(self):
        if self.configuration_version != "1":
            raise ValueError("unsupported AI provider configuration version")
        keys = tuple(key for key, _ in self.metadata)
        if len(set(keys)) != len(keys) or self.metadata != tuple(sorted(self.metadata)):
            raise ValueError("AI provider metadata is not canonical")
        forbidden = ("password=", "bearer ", "token=", "api_key=")
        serialized = " ".join(
            filter(
                None,
                (
                    self.provider_identifier,
                    self.model_identifier,
                    self.endpoint,
                    *(f"{key}={value}" for key, value in self.metadata),
                ),
            )
        ).casefold()
        if any(token in serialized for token in forbidden):
            raise ValueError("AI provider configuration contains secret material")
        return self


class AIProviderUsage(FrozenModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0)
    provider_request_identifier: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def token_total(self):
        if (
            self.prompt_tokens is not None
            and self.completion_tokens is not None
            and self.total_tokens is not None
            and self.total_tokens != self.prompt_tokens + self.completion_tokens
        ):
            raise ValueError("AI provider token totals are inconsistent")
        return self


class AIProviderClientRequest(FrozenModel):
    """Opaque transport envelope constructed only by a concrete adapter."""

    provider_identifier: str
    endpoint: str | None = None
    timeout_seconds: float = Field(gt=0)
    correlation_identifier: str | None = None
    payload: Any = Field(repr=False)


class AIProviderClientResponse(FrozenModel):
    """Opaque single-attempt response interpreted only by its adapter."""

    payload: Any = Field(repr=False)
    latency_ms: float | None = Field(default=None, ge=0)


@runtime_checkable
class AICredentialProvider(Protocol):
    """Resolve externally held credentials for the transport client only."""

    def resolve(self, authentication_reference: str) -> SecretStr: ...


@runtime_checkable
class AIProviderClient(Protocol):
    """Perform exactly one SDK/HTTP transport attempt without semantic mapping."""

    def send(
        self,
        request: AIProviderClientRequest,
        *,
        credential_provider: AICredentialProvider,
    ) -> AIProviderClientResponse: ...


@runtime_checkable
class AIProviderAdapter(Protocol):
    """Translate revision intent and normalize one gateway result."""

    configuration: AIProviderConfiguration

    def revise(
        self, invocation: ControlledRevisionInvocation
    ) -> ControlledRevisionGatewayResult: ...


class AIProviderObservabilityHook(Protocol):
    """Optional content-free metrics, trace, logging, and timing extension point."""

    def request_started(self, correlation_identifier: str | None) -> None: ...

    def request_finished(
        self,
        correlation_identifier: str | None,
        usage: AIProviderUsage | None,
    ) -> None: ...

    def request_failed(
        self,
        correlation_identifier: str | None,
        error: AIProviderAdapterError,
    ) -> None: ...


class AIProviderAdapterConstructor(Protocol):
    def __call__(
        self,
        *,
        configuration: AIProviderConfiguration,
        client: AIProviderClient,
        credential_provider: AICredentialProvider,
        observability_hook: AIProviderObservabilityHook | None,
    ) -> AIProviderAdapter: ...
