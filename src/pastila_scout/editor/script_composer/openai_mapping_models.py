"""Immutable OpenAI-shaped request-mapping contracts for Phase 6.2."""

from typing import Literal

from pydantic import Field

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel


class OpenAIMappingDomainModel(FrozenDomainModel):
    """Internal immutable base exposing the Phase 6.2 semantic seal."""

    @property
    def semantic_sha256(self) -> str:
        from .openai_mapping_identity import openai_mapping_fingerprint

        return openai_mapping_fingerprint(self)


class OpenAIProviderMessage(OpenAIMappingDomainModel):
    """One exact OpenAI-compatible projection of an execution message."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_message_reference: str = Field(strict=True, min_length=1, max_length=200)
    execution_message_reference: str = Field(strict=True, min_length=1)
    execution_message_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_message_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_request_reference: str = Field(strict=True, min_length=1)
    execution_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    role: Literal["developer", "user"]
    content: str = Field(strict=True, min_length=1)
    ordinal: int = Field(strict=True, ge=0)


class OpenAIProviderRequest(OpenAIMappingDomainModel):
    """One ordered OpenAI-compatible request without runtime configuration."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_reference: str = Field(strict=True, min_length=1, max_length=200)
    execution_request_reference: str = Field(strict=True, min_length=1)
    execution_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_ordinal: int = Field(strict=True, ge=0)
    messages: tuple[OpenAIProviderMessage, ...] = ()


class OpenAIProviderRequestPlan(OpenAIMappingDomainModel):
    """Complete deterministic OpenAI mapping for an execution plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_plan_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider_descriptor_reference: str = Field(strict=True, min_length=1)
    provider_descriptor_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_descriptor_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    requests: tuple[OpenAIProviderRequest, ...] = ()


__all__ = (
    "OpenAIProviderMessage",
    "OpenAIProviderRequest",
    "OpenAIProviderRequestPlan",
)
