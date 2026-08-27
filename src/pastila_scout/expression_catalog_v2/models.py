"""Read-only Voice V2 expression inventory contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA256_PATTERN = r"^[0-9a-f]{64}$"
ZERO_SHA256 = "0" * 64


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdjudicationStatusV2(StrEnum):
    APPROVED_CANDIDATE_SCOPE = "approved_candidate_scope"
    EVIDENCE_ONLY = "evidence_only"
    CANDIDATE_OWNER_REVIEW = "candidate_owner_review"


class RenderabilityStatusV2(StrEnum):
    EXACT_V1_SURFACE = "exact_v1_surface"
    APPROVED_CLOSED_SURFACE = "approved_closed_surface"
    UNAVAILABLE = "unavailable"


class ApprovedSurfaceV2(FrozenModel):
    surface_id: str = Field(min_length=1)
    expression_id: str = Field(min_length=1)
    exact_surface: str = Field(min_length=1)
    surface_utf8_sha256: str = Field(pattern=SHA256_PATTERN)
    placement: str = Field(min_length=1)
    person_tense: str = Field(min_length=1)
    expression_family_identity: str | None = None
    equivalence_group_identity: str | None = None
    pool_identity: str | None = None
    requires_preceding_authority_binding: bool = False
    requires_preceding_operator: Literal[False] = False
    requires_following_operator: Literal[False] = False
    runtime_morphology: Literal[False] = False
    episode_family_ceiling: int = Field(ge=1)
    adjacent_story_family_reuse: Literal[False] = False
    cross_episode_cooldown: int = Field(ge=0)
    production_active: Literal[False] = False


class AdjudicatedScopeV2(FrozenModel):
    review_order: int = Field(ge=1)
    disposition: AdjudicationStatusV2
    relationship_pool: str | None = None
    required_atoms: tuple[str, ...] = ()
    prohibited_binding: str | None = None
    grammar_mode: str | None = None
    authority_treatment: str | None = None
    scope_identity: str = Field(min_length=1)
    owner_statement: str = Field(min_length=1)


class ExpressionInventoryRecordV2(FrozenModel):
    expression_id: str = Field(min_length=1)
    source_surface_utf8_sha256: str = Field(pattern=SHA256_PATTERN)
    legacy_metadata_sha256: str = Field(pattern=SHA256_PATTERN)
    legacy_owner_class: str = Field(min_length=1)
    legacy_semantic_families: tuple[str, ...] = ()
    legacy_risk_tags: tuple[str, ...] = ()
    legacy_preferred_surface_ids: tuple[str, ...] = ()
    legacy_productive_family_ids: tuple[str, ...] = ()
    review_group: str = Field(min_length=1)
    adjudication_status: AdjudicationStatusV2
    renderability_status: RenderabilityStatusV2
    adjudicated_scope: AdjudicatedScopeV2 | None = None
    approved_surface_ids: tuple[str, ...] = ()
    production_active: Literal[False] = False

    @model_validator(mode="after")
    def validate_state(self):
        if self.adjudication_status is AdjudicationStatusV2.CANDIDATE_OWNER_REVIEW:
            if self.adjudicated_scope is not None:
                raise ValueError("unreviewed expression cannot have adjudicated scope")
            if self.renderability_status is not RenderabilityStatusV2.UNAVAILABLE:
                raise ValueError("unreviewed expression must remain unavailable")
        elif self.adjudicated_scope is None:
            raise ValueError("reviewed expression requires adjudicated scope")
        if self.adjudication_status is AdjudicationStatusV2.EVIDENCE_ONLY:
            if self.renderability_status is not RenderabilityStatusV2.UNAVAILABLE:
                raise ValueError("evidence-only expression must remain unavailable")
            if self.approved_surface_ids:
                raise ValueError(
                    "evidence-only expression cannot have approved surfaces"
                )
        if self.renderability_status is RenderabilityStatusV2.APPROVED_CLOSED_SURFACE:
            if not self.approved_surface_ids:
                raise ValueError("closed-surface renderability requires a surface")
        elif self.approved_surface_ids:
            raise ValueError("approved surfaces require closed-surface renderability")
        return self


class PreferredSurfaceEvidenceV2(FrozenModel):
    surface_id: str = Field(min_length=1)
    source_expression_id: str = Field(min_length=1)
    surface_utf8_sha256: str = Field(pattern=SHA256_PATTERN)
    relation_type: str = Field(min_length=1)
    source_resolves_to_packaged_expression: bool
    ambiguity_codes: tuple[str, ...] = ()
    voice_v2_authorized: Literal[False] = False


class ProductiveFamilyEvidenceV2(FrozenModel):
    family_id: str = Field(min_length=1)
    members: tuple[str, ...] = Field(min_length=1)
    evidence_sha256: str = Field(pattern=SHA256_PATTERN)
    voice_v2_productive: Literal[False] = False


class OwnerReviewQueueItemV2(FrozenModel):
    review_order: int = Field(ge=1)
    expression_id: str = Field(min_length=1)
    review_group: str = Field(min_length=1)
    legacy_metadata_only: Literal[True] = True
    semantic_approval_inferred: Literal[False] = False


class ExpressionCatalogOverlayV2(FrozenModel):
    schema_name: Literal["pastilaacida-voice-expression-catalog-overlay"] = (
        "pastilaacida-voice-expression-catalog-overlay"
    )
    schema_version: Literal["2"] = "2"
    catalog_v1_file_sha256: str = Field(pattern=SHA256_PATTERN)
    catalog_v1_content_sha256: str = Field(pattern=SHA256_PATTERN)
    records: tuple[ExpressionInventoryRecordV2, ...] = Field(min_length=1)
    approved_surfaces: tuple[ApprovedSurfaceV2, ...] = ()
    preferred_surface_evidence: tuple[PreferredSurfaceEvidenceV2, ...] = ()
    productive_family_evidence: tuple[ProductiveFamilyEvidenceV2, ...] = ()
    owner_review_queue: tuple[OwnerReviewQueueItemV2, ...] = ()
    production_activations: Literal[0] = 0
    overlay_identity: str = Field(default=ZERO_SHA256, pattern=SHA256_PATTERN)


__all__ = [
    "ZERO_SHA256",
    "AdjudicatedScopeV2",
    "AdjudicationStatusV2",
    "ApprovedSurfaceV2",
    "ExpressionCatalogOverlayV2",
    "ExpressionInventoryRecordV2",
    "OwnerReviewQueueItemV2",
    "PreferredSurfaceEvidenceV2",
    "ProductiveFamilyEvidenceV2",
    "RenderabilityStatusV2",
]
