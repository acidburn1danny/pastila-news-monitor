"""Immutable deterministic section-composition contracts for Phase 4.3."""

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .claim_binding_models import (
    ClaimBindingRequirement,
    ClaimBindingRole,
    ClaimBindingValidationContext,
    DraftClaimBindingPlan,
)
from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel

ReferenceToken = str


class SectionCompositionDomainModel(FrozenDomainModel):
    """Internal base exposing the Phase 4.3 canonical representation."""

    @property
    def semantic_sha256(self) -> str:
        from .section_composition_identity import section_composition_fingerprint

        return section_composition_fingerprint(self)


class ComposedClaim(SectionCompositionDomainModel):
    """One exact structural projection of an authoritative claim binding."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    composed_claim_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_claim_binding_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    source_claim_binding_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_claim_binding_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    section_reference: str = Field(strict=True, min_length=1)
    claim_reference: str = Field(strict=True, min_length=1)
    requirement: ClaimBindingRequirement
    role: ClaimBindingRole | str
    ordinal: int = Field(strict=True, ge=0)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value):
        """Reuse the frozen ClaimBinding role contract without redefining it."""

        from .claim_binding_models import ClaimBinding

        return ClaimBinding.validate_role(value)


class ComposedSection(SectionCompositionDomainModel):
    """One nonempty, ordered projection of a section binding set."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    composed_section_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_section_binding_set_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    source_section_binding_set_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_section_binding_set_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    section_reference: str = Field(strict=True, min_length=1)
    composed_claims: tuple[ComposedClaim, ...] = Field(min_length=1)


class DraftSectionCompositionPlan(SectionCompositionDomainModel):
    """Complete immutable structural composition of one claim-binding plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    composition_plan_reference: str = Field(strict=True, min_length=1, max_length=200)
    source_claim_binding_plan_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    source_claim_binding_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    source_claim_binding_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    normalized_input_reference: str = Field(strict=True, min_length=1)
    composed_sections: tuple[ComposedSection, ...] = ()


class SectionCompositionValidationContext(SectionCompositionDomainModel):
    """Authoritative Phase 4.2 plans and their frozen validation context."""

    claim_binding_plans: tuple[DraftClaimBindingPlan, ...] = Field(min_length=1)
    claim_binding_validation_context: ClaimBindingValidationContext

    @field_validator("claim_binding_plans", mode="before")
    @classmethod
    def validate_and_order_plans(cls, value):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "section-composition-invalid-context-collection",
                "section-composition-invalid-context-collection",
            )
        try:
            plans = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "section-composition-invalid-context-collection",
                "section-composition-invalid-context-collection",
            ) from error
        if any(not isinstance(item, (dict, DraftClaimBindingPlan)) for item in plans):
            raise PydanticCustomError(
                "section-composition-invalid-context-member",
                "section-composition-invalid-context-member",
            )
        identities = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in plans
        )
        references = tuple(
            (
                item.get("plan_reference", "")
                if isinstance(item, dict)
                else item.plan_reference
            )
            for item in plans
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                "section-composition-duplicate-context-plan-identity",
                "section-composition-duplicate-context-plan-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "section-composition-duplicate-context-plan-reference",
                "section-composition-duplicate-context-plan-reference",
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
    "ComposedClaim",
    "ComposedSection",
    "DraftSectionCompositionPlan",
    "SectionCompositionValidationContext",
)
