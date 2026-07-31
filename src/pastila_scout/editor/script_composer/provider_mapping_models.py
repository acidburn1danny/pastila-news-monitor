"""Common immutable provider-request mapping contracts for Phase 6.2."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .llm_execution_models import (
    DraftLLMExecutionPlan,
    LLMExecutionValidationContext,
)
from .models import FrozenDomainModel
from .openai_mapping_models import OpenAIProviderRequestPlan


class ProviderMappingDomainModel(FrozenDomainModel):
    """Internal immutable base exposing the Phase 6.2 semantic seal."""

    @property
    def semantic_sha256(self) -> str:
        from .provider_mapping_identity import provider_mapping_fingerprint

        return provider_mapping_fingerprint(self)


class ProviderRequestPlanDescriptor(ProviderMappingDomainModel):
    """Versioned provider-mapping selection without runtime configuration."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_descriptor_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider: Literal["openai"]
    mapping_contract_version: Literal["phase-6.2-openai-v1"]


class DraftProviderRequestPlan(ProviderMappingDomainModel):
    """Typed provider-dispatched wrapper around one concrete OpenAI plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_request_plan_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider_descriptor: ProviderRequestPlanDescriptor
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_plan_reference: str = Field(strict=True, min_length=1)
    provider_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_request_plan: OpenAIProviderRequestPlan


class ProviderMappingValidationContext(ProviderMappingDomainModel):
    """Authoritative Phase 6.1 plans, context, and supported descriptors."""

    execution_plans: tuple[DraftLLMExecutionPlan, ...] = Field(min_length=1)
    execution_validation_context: LLMExecutionValidationContext
    provider_descriptors: tuple[ProviderRequestPlanDescriptor, ...] = Field(
        min_length=1
    )

    @field_validator("execution_plans", "provider_descriptors", mode="before")
    @classmethod
    def validate_collections(cls, value, info):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "provider-mapping-invalid-context-collection",
                "provider-mapping-invalid-context-collection",
            )
        try:
            items = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "provider-mapping-invalid-context-collection",
                "provider-mapping-invalid-context-collection",
            ) from error
        identity_key = "identity"
        reference_key = (
            "provider_descriptor_reference"
            if info.field_name == "provider_descriptors"
            else "execution_plan_reference"
        )
        identities = tuple(
            item.get(identity_key, "") if isinstance(item, dict) else item.identity
            for item in items
        )
        references = tuple(
            (
                item.get(reference_key, "")
                if isinstance(item, dict)
                else getattr(item, reference_key)
            )
            for item in items
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                f"provider-mapping-duplicate-{info.field_name}-identity",
                f"provider-mapping-duplicate-{info.field_name}-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                f"provider-mapping-duplicate-{info.field_name}-reference",
                f"provider-mapping-duplicate-{info.field_name}-reference",
            )
        if info.field_name == "provider_descriptors":
            providers = tuple(
                item.get("provider", "") if isinstance(item, dict) else item.provider
                for item in items
            )
            versions = tuple(
                (
                    item.get("mapping_contract_version", "")
                    if isinstance(item, dict)
                    else item.mapping_contract_version
                )
                for item in items
            )
            if len(providers) != len(set(providers)):
                raise PydanticCustomError(
                    "provider-mapping-duplicate-provider",
                    "provider-mapping-duplicate-provider",
                )
            if len(versions) != len(set(versions)):
                raise PydanticCustomError(
                    "provider-mapping-duplicate-contract-version",
                    "provider-mapping-duplicate-contract-version",
                )
        return tuple(sorted(items, key=lambda item: identities[items.index(item)]))


__all__ = (
    "DraftProviderRequestPlan",
    "ProviderMappingValidationContext",
    "ProviderRequestPlanDescriptor",
)
