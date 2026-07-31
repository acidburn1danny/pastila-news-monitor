"""Independent extracted-output authority contracts for Phase 6.3."""

from typing import Literal

from pydantic import Field

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel

ExtractedFinishReason = Literal["stop", "length", "content_filter"]


class ExtractedResultDomainModel(FrozenDomainModel):
    """Internal immutable base for extracted-result authority."""

    @property
    def semantic_sha256(self) -> str:
        from .extracted_result_identity import extracted_result_fingerprint

        return extracted_result_fingerprint(self)


class OpenAIExtractedResponseMessage(ExtractedResultDomainModel):
    """One independently extracted message with complete direct ownership."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    extracted_response_message_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    extracted_response_reference: str = Field(strict=True, min_length=1)
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
    finish_reason: ExtractedFinishReason


class OpenAIExtractedResponse(ExtractedResultDomainModel):
    """One ordered extracted response owned by one Phase 6.2 request."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    extracted_response_reference: str = Field(strict=True, min_length=1, max_length=200)
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
    messages: tuple[OpenAIExtractedResponseMessage, ...] = Field(min_length=1)


class OpenAIExtractedExecutionResult(ExtractedResultDomainModel):
    """Independent extracted authority for one Phase 6.2 provider plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    extracted_execution_result_reference: str = Field(
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
    responses: tuple[OpenAIExtractedResponse, ...] = ()


__all__ = (
    "OpenAIExtractedExecutionResult",
    "OpenAIExtractedResponse",
    "OpenAIExtractedResponseMessage",
)
