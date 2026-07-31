"""Common immutable provider execution-result contracts for Phase 6.3."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .defaults import FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .extracted_result_models import OpenAIExtractedExecutionResult
from .models import FrozenDomainModel
from .openai_result_models import OpenAIProviderExecutionResult
from .provider_mapping_models import (
    DraftProviderRequestPlan,
    ProviderMappingValidationContext,
)


class ProviderResultDomainModel(FrozenDomainModel):
    """Internal immutable base for common Phase 6.3 results."""

    @property
    def semantic_sha256(self) -> str:
        from .provider_result_identity import provider_result_fingerprint

        return provider_result_fingerprint(self)


class ProviderExecutionResultValidationContext(ProviderResultDomainModel):
    """Authoritative Phase 6.2 plans and their frozen validation context."""

    provider_request_plans: tuple[DraftProviderRequestPlan, ...] = Field(min_length=1)
    provider_mapping_validation_context: ProviderMappingValidationContext
    extracted_execution_results: tuple[OpenAIExtractedExecutionResult, ...] = Field(
        min_length=1
    )

    @field_validator(
        "provider_request_plans", "extracted_execution_results", mode="before"
    )
    @classmethod
    def validate_plans(cls, value, info):
        if isinstance(value, (str, bytes, dict)):
            raise PydanticCustomError(
                "provider-result-invalid-context-collection",
                "provider-result-invalid-context-collection",
            )
        try:
            plans = tuple(value)
        except TypeError as error:
            raise PydanticCustomError(
                "provider-result-invalid-context-collection",
                "provider-result-invalid-context-collection",
            ) from error
        identities = tuple(
            item.get("identity", "") if isinstance(item, dict) else item.identity
            for item in plans
        )
        reference_field = (
            "extracted_execution_result_reference"
            if info.field_name == "extracted_execution_results"
            else "provider_request_plan_reference"
        )
        references = tuple(
            (
                item.get(reference_field, "")
                if isinstance(item, dict)
                else getattr(item, reference_field)
            )
            for item in plans
        )
        if len(identities) != len(set(identities)):
            raise PydanticCustomError(
                "provider-result-duplicate-authority-identity",
                "provider-result-duplicate-authority-identity",
            )
        if len(references) != len(set(references)):
            raise PydanticCustomError(
                "provider-result-duplicate-authority-reference",
                "provider-result-duplicate-authority-reference",
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


class ProviderExecutionResult(ProviderResultDomainModel):
    """Typed generic wrapper around one concrete provider execution result."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_execution_result_reference: str = Field(
        strict=True, min_length=1, max_length=200
    )
    provider: Literal["openai"]
    execution_plan_reference: str = Field(strict=True, min_length=1)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_request_plan_reference: str = Field(strict=True, min_length=1)
    provider_request_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_request_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(strict=True, min_length=1)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_result_reference: str = Field(strict=True, min_length=1)
    provider_result_identity: str = Field(pattern=IDENTITY_PATTERN)
    provider_result_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    openai_execution_result: OpenAIProviderExecutionResult


__all__ = (
    "ProviderExecutionResult",
    "ProviderExecutionResultValidationContext",
)
