"""Immutable deterministic semantic LLM-request contracts for Phase 5.1."""

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel
from .section_composition_models import (
    DraftSectionCompositionPlan,
    SectionCompositionValidationContext,
)


class LLMRequestDomainModel(FrozenDomainModel):
    """Internal immutable base exposing the Phase 5.1 semantic seal."""

    @property
    def semantic_sha256(self) -> str:
        from .llm_request_identity import llm_request_fingerprint

        return llm_request_fingerprint(self)


class LLMRequestClaim(LLMRequestDomainModel):
    """Self-contained semantic request projection of one composed claim."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_claim_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_composed_claim_reference: str = Field(strict=True, min_length=1)
    source_composed_claim_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composed_claim_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_composed_section_reference: str = Field(strict=True, min_length=1)
    source_composed_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composed_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_composition_plan_reference: str = Field(strict=True, min_length=1)
    source_composition_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    section_reference: str = Field(strict=True, min_length=1)
    claim_reference: str = Field(strict=True, min_length=1)
    requirement: str = Field(strict=True, pattern=r"^(?:required|optional)$")
    role: str = Field(strict=True, min_length=1)
    ordinal: int = Field(strict=True, ge=0)


class LLMRequestSection(LLMRequestDomainModel):
    """Complete semantic generation request for one composed section."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_section_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_composed_section_reference: str = Field(strict=True, min_length=1)
    source_composed_section_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composed_section_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_composition_plan_reference: str = Field(strict=True, min_length=1)
    source_composition_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    section_reference: str = Field(strict=True, min_length=1)
    request_claims: tuple[LLMRequestClaim, ...] = Field(min_length=1)


class DraftLLMRequestPlan(LLMRequestDomainModel):
    """Complete self-contained semantic request plan for one composed draft."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_plan_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_composition_plan_reference: str = Field(strict=True, min_length=1)
    source_composition_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    request_sections: tuple[LLMRequestSection, ...] = ()


class LLMRequestValidationContext(LLMRequestDomainModel):
    """Authoritative Phase 4.3 plans and their frozen validation context."""

    composition_plans: tuple[DraftSectionCompositionPlan, ...] = Field(min_length=1)
    section_composition_validation_context: SectionCompositionValidationContext

    @field_validator("composition_plans", mode="before")
    @classmethod
    def validate_and_order_plans(cls, value):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "llm-request-invalid-context-collection",
                "llm-request-invalid-context-collection",
            )
        try:
            plans = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "llm-request-invalid-context-collection",
                "llm-request-invalid-context-collection",
            ) from error
        if any(
            not isinstance(item, (dict, DraftSectionCompositionPlan)) for item in plans
        ):
            raise PydanticCustomError(
                "llm-request-invalid-context-member",
                "llm-request-invalid-context-member",
            )
        identities = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in plans
        )
        references = tuple(
            (
                item.get("composition_plan_reference", "")
                if isinstance(item, dict)
                else item.composition_plan_reference
            )
            for item in plans
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                "llm-request-duplicate-context-plan-identity",
                "llm-request-duplicate-context-plan-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "llm-request-duplicate-context-plan-reference",
                "llm-request-duplicate-context-plan-reference",
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
    "DraftLLMRequestPlan",
    "LLMRequestClaim",
    "LLMRequestSection",
    "LLMRequestValidationContext",
)
