"""Immutable deterministic claim-binding contracts for Module 2.9 Phase 4.2."""

import re
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .canonical import canonical_json, semantic_fingerprint
from .defaults import CUSTOM_PATTERN, FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .draft_models import DraftStructure, DraftValidationContext
from .models import FrozenDomainModel


class ClaimBindingRequirement(StrEnum):
    """Whether a binding fulfills required or optional draft inventory."""

    REQUIRED = "required"
    OPTIONAL = "optional"


class ClaimBindingRole(StrEnum):
    """Closed built-in structural roles for claims inside draft sections."""

    SECTION_ANCHOR = "section_anchor"
    SECTION_CONTEXT = "section_context"
    SECTION_DEVELOPMENT = "section_development"
    SECTION_COUNTERPOINT = "section_counterpoint"
    SECTION_CONCLUSION = "section_conclusion"


ReferenceToken = Annotated[str, Field(strict=True, min_length=1)]
_PROHIBITED_CUSTOM_ROLE_SEGMENTS = frozenset(
    {
        "anthropic",
        "execution",
        "gemini",
        "generated",
        "llm",
        "openai",
        "prompt",
        "provider",
        "runtime",
    }
)


class ClaimBindingDomainModel(FrozenDomainModel):
    """Internal base with a Phase 4.2 self-excluding semantic fingerprint."""

    @property
    def semantic_sha256(self) -> str:
        return claim_binding_semantic_fingerprint(self)

    def canonical_json(self) -> str:
        return canonical_json(self)


class ClaimBinding(ClaimBindingDomainModel):
    """One explicit structural assignment of a claim to a draft section."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    binding_reference: ReferenceToken
    draft_reference: ReferenceToken
    section_reference: ReferenceToken
    claim_reference: ReferenceToken
    requirement: ClaimBindingRequirement
    role: ClaimBindingRole | str
    ordinal: int = Field(strict=True, ge=0)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value):
        raw = getattr(value, "value", value)
        built_ins = {item.value for item in ClaimBindingRole}
        custom_valid = isinstance(raw, str) and re.fullmatch(CUSTOM_PATTERN, raw)
        if custom_valid:
            custom_valid = not (
                set(raw.removeprefix("custom:").split("-"))
                & _PROHIBITED_CUSTOM_ROLE_SEGMENTS
            )
        if raw not in built_ins and not custom_valid:
            raise PydanticCustomError(
                "claim-binding-unknown-role", "claim-binding-unknown-role"
            )
        return value


class SectionClaimBindingSet(ClaimBindingDomainModel):
    """All emitted claim bindings for exactly one draft section."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    binding_set_reference: ReferenceToken
    draft_reference: ReferenceToken
    section_reference: ReferenceToken
    bindings: tuple[ClaimBinding, ...] = Field(min_length=1)


class DraftClaimBindingPlan(ClaimBindingDomainModel):
    """Complete deterministic claim-binding artifact for one frozen draft."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    plan_reference: ReferenceToken
    draft_reference: ReferenceToken
    draft_fingerprint: str = Field(strict=True, pattern=FINGERPRINT_PATTERN)
    normalized_input_reference: ReferenceToken
    section_binding_sets: tuple[SectionClaimBindingSet, ...] = ()


class ClaimBindingValidationContext(ClaimBindingDomainModel):
    """Immutable authoritative drafts and their existing ownership context."""

    drafts: tuple[DraftStructure, ...] = Field(min_length=1)
    draft_validation_context: DraftValidationContext

    @field_validator("drafts", mode="before")
    @classmethod
    def validate_and_order_drafts(cls, value):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "claim-binding-invalid-context-collection",
                "claim-binding-invalid-context-collection",
            )
        try:
            values = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "claim-binding-invalid-context-collection",
                "claim-binding-invalid-context-collection",
            ) from error
        if any(not isinstance(item, (dict, DraftStructure)) for item in values):
            raise PydanticCustomError(
                "claim-binding-invalid-context-member",
                "claim-binding-invalid-context-member",
            )
        references = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in values
        )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "claim-binding-duplicate-context-draft-identity",
                "claim-binding-duplicate-context-draft-identity",
            )
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.get("identity", "")
                    if isinstance(item, dict)
                    else item.identity
                ),
            )
        )


def claim_binding_semantic_fingerprint(value: ClaimBindingDomainModel) -> str:
    """Return the frozen canonical SHA-256 seal excluding only its own seal."""

    return semantic_fingerprint(
        _claim_binding_semantic_payload(value, exclude_fingerprint=True)
    )


def _claim_binding_semantic_payload(
    value: ClaimBindingDomainModel, *, exclude_fingerprint: bool
) -> dict:
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, SectionClaimBindingSet):
        payload["bindings"] = {
            str(index): binding for index, binding in enumerate(value.bindings)
        }
    elif isinstance(value, DraftClaimBindingPlan):
        payload["section_binding_sets"] = {
            str(index): binding_set
            for index, binding_set in enumerate(value.section_binding_sets)
        }
    return payload


__all__ = (
    "ClaimBinding",
    "ClaimBindingRequirement",
    "ClaimBindingRole",
    "ClaimBindingValidationContext",
    "DraftClaimBindingPlan",
    "SectionClaimBindingSet",
    "claim_binding_semantic_fingerprint",
)
