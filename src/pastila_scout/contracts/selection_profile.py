"""Versioned, generic editorial selection constraints."""

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from pastila_scout.contracts.common import (
    ALLOWED_CATEGORIES,
    SELECTION_PROFILE_VERSION,
    ExtensibleContractModel,
    NonEmptyText,
)


class MinimumPolicy(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class ProviderPolicy(StrEnum):
    OPTIONAL = "optional"
    REQUIRED = "required"
    FORBIDDEN = "forbidden"


class CategoryCountConstraint(ExtensibleContractModel):
    minimum: int = Field(ge=0)
    preferred: int = Field(ge=0)
    maximum: int = Field(ge=0)
    minimum_policy: MinimumPolicy

    @model_validator(mode="after")
    def validate_order(self) -> CategoryCountConstraint:
        if not self.minimum <= self.preferred <= self.maximum:
            raise ValueError(
                "category counts must satisfy minimum <= preferred <= maximum"
            )
        return self


class SelectionProfileV1(ExtensibleContractModel):
    contract_version: str = Field(
        default=SELECTION_PROFILE_VERSION,
        pattern="^editor-selection-profile-v1$",
    )
    profile_name: NonEmptyText
    profile_version: NonEmptyText
    target_story_count: int = Field(gt=0)
    backup_count: int = Field(ge=0)
    category_constraints: dict[str, CategoryCountConstraint]
    maximum_stories_from_one_category: int = Field(gt=0)
    minimum_source_diversity: int = Field(gt=0)
    avoid_semantic_redundancy: bool
    opening_story_preference: NonEmptyText | None = None
    closing_story_preference: NonEmptyText | None = None
    provider_policy: ProviderPolicy = ProviderPolicy.OPTIONAL

    @field_validator("category_constraints")
    @classmethod
    def validate_categories(
        cls, value: dict[str, CategoryCountConstraint]
    ) -> dict[str, CategoryCountConstraint]:
        invalid = set(value).difference(ALLOWED_CATEGORIES)
        if invalid:
            raise ValueError(f"unsupported category constraints: {sorted(invalid)}")
        return value
