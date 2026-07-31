"""Immutable provider-neutral LLM execution-planning contracts for Phase 6.1."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel
from .prompt_rendering_models import (
    DraftRenderedPromptPlan,
    RenderedPromptValidationContext,
)

ExecutionRole = Literal["instruction", "context", "generation"]


class LLMExecutionDomainModel(FrozenDomainModel):
    """Internal immutable base exposing the Phase 6.1 semantic seal."""

    @property
    def semantic_sha256(self) -> str:
        from .llm_execution_identity import llm_execution_fingerprint

        return llm_execution_fingerprint(self)


class LLMExecutionMessage(LLMExecutionDomainModel):
    """One provider-neutral message eligible for later execution."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_message_reference: str = Field(strict=True, min_length=1, max_length=200)
    rendered_message_reference: str = Field(strict=True, min_length=1)
    rendered_message_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_message_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_section_reference: str = Field(strict=True, min_length=1)
    rendered_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_plan_reference: str = Field(strict=True, min_length=1)
    rendered_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_role: ExecutionRole
    execution_text: str = Field(strict=True, min_length=1)
    ordinal: int = Field(strict=True, ge=0)


class LLMExecutionRequest(LLMExecutionDomainModel):
    """One ordered execution unit derived from one rendered section."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_request_reference: str = Field(strict=True, min_length=1, max_length=200)
    rendered_section_reference: str = Field(strict=True, min_length=1)
    rendered_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    rendered_plan_reference: str = Field(strict=True, min_length=1)
    rendered_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_ordinal: int = Field(strict=True, ge=0)
    execution_messages: tuple[LLMExecutionMessage, ...] = ()


class DraftLLMExecutionPlan(LLMExecutionDomainModel):
    """Complete provider-neutral execution plan for one rendered prompt plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(strict=True, min_length=1, max_length=200)
    rendered_plan_reference: str = Field(strict=True, min_length=1)
    rendered_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    rendered_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_plan_reference: str = Field(strict=True, min_length=1)
    request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    normalized_input_identity: str = Field(pattern=IDENTITY_PATTERN)
    normalized_input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_requests: tuple[LLMExecutionRequest, ...] = ()


class LLMExecutionValidationContext(LLMExecutionDomainModel):
    """Authoritative Phase 5.2 plans and their frozen validation context."""

    rendered_prompt_plans: tuple[DraftRenderedPromptPlan, ...] = Field(min_length=1)
    rendered_prompt_validation_context: RenderedPromptValidationContext

    @field_validator("rendered_prompt_plans", mode="before")
    @classmethod
    def validate_and_order_plans(cls, value):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "llm-execution-invalid-context-collection",
                "llm-execution-invalid-context-collection",
            )
        try:
            plans = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "llm-execution-invalid-context-collection",
                "llm-execution-invalid-context-collection",
            ) from error
        if any(not isinstance(item, (dict, DraftRenderedPromptPlan)) for item in plans):
            raise PydanticCustomError(
                "llm-execution-invalid-context-member",
                "llm-execution-invalid-context-member",
            )
        identities = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in plans
        )
        references = tuple(
            (
                item.get("rendered_plan_reference", "")
                if isinstance(item, dict)
                else item.rendered_plan_reference
            )
            for item in plans
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                "llm-execution-duplicate-context-plan-identity",
                "llm-execution-duplicate-context-plan-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "llm-execution-duplicate-context-plan-reference",
                "llm-execution-duplicate-context-plan-reference",
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
    "DraftLLMExecutionPlan",
    "LLMExecutionMessage",
    "LLMExecutionRequest",
    "LLMExecutionValidationContext",
)
