"""Immutable OpenAI execution-result contracts for Phase 6.3."""

from typing import Literal

from pydantic import Field

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel

FinishReason = Literal["stop", "length", "content_filter"]


class OpenAIProviderResultDomainModel(FrozenDomainModel):
    """Internal immutable base for concrete Phase 6.3 results."""

    @property
    def semantic_sha256(self) -> str:
        from .openai_result_identity import openai_result_fingerprint

        return openai_result_fingerprint(self)


class OpenAIProviderResponseMessage(OpenAIProviderResultDomainModel):
    """One deterministic generated message owned by one provider request."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_response_message_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider_response_reference: str = Field(strict=True, min_length=1)
    provider_request_plan_reference: str = Field(strict=True, min_length=1)
    provider_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_plan_reference: str = Field(strict=True, min_length=1)
    openai_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    openai_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_reference: str = Field(strict=True, min_length=1)
    openai_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    openai_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_request_reference: str = Field(strict=True, min_length=1)
    execution_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    ordinal: int = Field(strict=True, ge=0)
    generated_text: str = Field(strict=True, min_length=1)
    finish_reason: FinishReason


class OpenAIProviderResponse(OpenAIProviderResultDomainModel):
    """One ordered response corresponding to one OpenAI provider request."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_response_reference: str = Field(strict=True, min_length=1, max_length=200)
    provider_request_plan_reference: str = Field(strict=True, min_length=1)
    provider_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_plan_reference: str = Field(strict=True, min_length=1)
    openai_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    openai_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_reference: str = Field(strict=True, min_length=1)
    openai_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    openai_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_request_reference: str = Field(strict=True, min_length=1)
    execution_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    response_ordinal: int = Field(strict=True, ge=0)
    messages: tuple[OpenAIProviderResponseMessage, ...] = Field(min_length=1)


class OpenAIProviderExecutionResult(OpenAIProviderResultDomainModel):
    """Complete deterministic OpenAI result for one provider request plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_provider_execution_result_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider: Literal["openai"]
    provider_request_plan_reference: str = Field(strict=True, min_length=1)
    provider_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_plan_reference: str = Field(strict=True, min_length=1)
    openai_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    openai_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    responses: tuple[OpenAIProviderResponse, ...] = ()


__all__ = (
    "OpenAIProviderExecutionResult",
    "OpenAIProviderResponse",
    "OpenAIProviderResponseMessage",
)
