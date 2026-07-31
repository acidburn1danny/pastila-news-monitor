"""Immutable deterministic prompt-rendering contracts for Phase 5.2."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .llm_request_models import DraftLLMRequestPlan, LLMRequestValidationContext
from .models import FrozenDomainModel

RenderingRole = Literal["instruction", "context", "generation"]


class RenderedPromptDomainModel(FrozenDomainModel):
    """Internal immutable base exposing the Phase 5.2 semantic seal."""

    @property
    def semantic_sha256(self) -> str:
        from .prompt_rendering_identity import rendered_prompt_fingerprint

        return rendered_prompt_fingerprint(self)


class RenderedPromptMessage(RenderedPromptDomainModel):
    """One canonical provider-neutral rendering of a request claim."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_message_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_request_claim_reference: str = Field(strict=True, min_length=1)
    source_request_claim_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_claim_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_request_section_reference: str = Field(strict=True, min_length=1)
    source_request_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_request_plan_reference: str = Field(strict=True, min_length=1)
    source_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendering_role: RenderingRole
    rendered_text: str = Field(strict=True, min_length=1)
    ordinal: int = Field(strict=True, ge=0)


class RenderedPromptSection(RenderedPromptDomainModel):
    """One ordered collection of canonically rendered request messages."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_section_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_request_section_reference: str = Field(strict=True, min_length=1)
    source_request_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_request_plan_reference: str = Field(strict=True, min_length=1)
    source_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    rendered_messages: tuple[RenderedPromptMessage, ...] = Field(min_length=1)


class DraftRenderedPromptPlan(RenderedPromptDomainModel):
    """Complete provider-neutral canonical rendering of one request plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_plan_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_request_plan_reference: str = Field(strict=True, min_length=1)
    source_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    rendered_sections: tuple[RenderedPromptSection, ...] = ()


class RenderedPromptValidationContext(RenderedPromptDomainModel):
    """Authoritative Phase 5.1 plans and their frozen validation context."""

    request_plans: tuple[DraftLLMRequestPlan, ...] = Field(min_length=1)
    llm_request_validation_context: LLMRequestValidationContext

    @field_validator("request_plans", mode="before")
    @classmethod
    def validate_and_order_plans(cls, value):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "prompt-rendering-invalid-context-collection",
                "prompt-rendering-invalid-context-collection",
            )
        try:
            plans = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "prompt-rendering-invalid-context-collection",
                "prompt-rendering-invalid-context-collection",
            ) from error
        if any(not isinstance(item, (dict, DraftLLMRequestPlan)) for item in plans):
            raise PydanticCustomError(
                "prompt-rendering-invalid-context-member",
                "prompt-rendering-invalid-context-member",
            )
        identities = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in plans
        )
        references = tuple(
            (
                item.get("request_plan_reference", "")
                if isinstance(item, dict)
                else item.request_plan_reference
            )
            for item in plans
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                "prompt-rendering-duplicate-context-plan-identity",
                "prompt-rendering-duplicate-context-plan-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "prompt-rendering-duplicate-context-plan-reference",
                "prompt-rendering-duplicate-context-plan-reference",
            )
        return tuple(
            sorted(
                plans,
                key=lambda item: (
                    item.get("identity", "")
                    if isinstance(item, dict)
                    else item.identity
                ),
            )
        )


__all__ = (
    "DraftRenderedPromptPlan",
    "RenderedPromptMessage",
    "RenderedPromptSection",
    "RenderedPromptValidationContext",
)
