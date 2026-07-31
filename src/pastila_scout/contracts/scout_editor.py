"""Public, provider-neutral Scout ranking input for the Editor Agent."""

from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from pastila_scout.contracts.common import (
    ALLOWED_CATEGORIES,
    EDITORIAL_CONTRACT_VERSION,
    SCOUT_INPUT_VERSION,
    ContractModel,
    ExtensibleContractModel,
    NonEmptyText,
    SourceReference,
)


class RankingParameters(ContractModel):
    days: int = Field(gt=0)
    category_filter: str | None = None
    limit: int | None = Field(default=None, gt=0)
    top: int = Field(gt=0)
    minimum_score: float = Field(ge=0, le=100)
    ai_enabled: bool


class EventCounts(ContractModel):
    eligible: int = Field(ge=0)
    processed: int = Field(ge=0)
    reported: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> EventCounts:
        if not self.reported <= self.processed <= self.eligible:
            raise ValueError(
                "event counts must satisfy reported <= processed <= eligible"
            )
        return self


class PublicScoreComponent(ContractModel):
    raw_input: float
    normalized_value: float = Field(ge=0, le=1)
    weighted_contribution: float = Field(ge=0)
    maximum_contribution: float = Field(ge=0)
    explanation: NonEmptyText


class DeterministicScoreBreakdown(ContractModel):
    supporting_articles: PublicScoreComponent
    source_diversity: PublicScoreComponent
    source_credibility: PublicScoreComponent
    recency: PublicScoreComponent
    national_relevance: PublicScoreComponent
    category_weight: PublicScoreComponent
    title_strength: PublicScoreComponent


class PublicDeterministicScore(ContractModel):
    score: float = Field(ge=0, le=100)
    schema_version: NonEmptyText
    components: DeterministicScoreBreakdown


class PublicAIEditorialDimensions(ContractModel):
    importance: int = Field(ge=0, le=10)
    virality: int = Field(ge=0, le=10)
    absurdity: int = Field(ge=0, le=10)
    satirical_potential: int = Field(ge=0, le=10)
    public_interest: int = Field(ge=0, le=10)
    emotional_impact: int = Field(ge=0, le=10)
    originality: int = Field(ge=0, le=10)


class PublicAIEditorialScore(ContractModel):
    score: float = Field(ge=0, le=100)
    dimensions: PublicAIEditorialDimensions


class PublicationBounds(ContractModel):
    first_published_at: datetime | None = None
    last_published_at: datetime | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> PublicationBounds:
        if (
            self.first_published_at is not None
            and self.last_published_at is not None
            and self.first_published_at > self.last_published_at
        ):
            raise ValueError("first publication must not follow last publication")
        return self


class RankedEditorialEvent(ExtensibleContractModel):
    rank: int = Field(gt=0)
    score_rank: int = Field(gt=0)
    event_id: int = Field(gt=0)
    canonical_title: NonEmptyText
    canonical_summary: NonEmptyText
    publication_bounds: PublicationBounds
    categories: tuple[str, ...] = Field(min_length=1, max_length=3)
    source_count: int = Field(gt=0)
    article_count: int = Field(gt=0)
    source_provenance: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)
    provenance_truncated: bool
    deterministic_score: PublicDeterministicScore
    ai_editorial_score: PublicAIEditorialScore | None = None
    final_score: float = Field(ge=0, le=100)
    recommendation: str = Field(pattern="^(STRONG_PICK|POSSIBLE_PICK|BACKUP|SKIP)$")
    scout_recommendation_reason: NonEmptyText
    editorial_risks: tuple[NonEmptyText, ...] = Field(default=(), max_length=20)
    score_basis: NonEmptyText

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("categories must be unique")
        invalid = set(value).difference(ALLOWED_CATEGORIES)
        if invalid:
            raise ValueError(f"unsupported categories: {sorted(invalid)}")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> RankedEditorialEvent:
        if self.source_count > self.article_count:
            raise ValueError("source_count cannot exceed article_count")
        if self.provenance_truncated != (
            self.article_count > len(self.source_provenance)
        ):
            raise ValueError("provenance_truncated does not match article_count")
        return self


HashText = Annotated[
    str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$", strict=True)
]
ReportId = Annotated[
    str,
    StringConstraints(
        pattern=r"^scout-editor-input-v1:sha256:[0-9a-f]{64}$", strict=True
    ),
]


class ScoutEditorInputV1(ExtensibleContractModel):
    contract_version: str = Field(
        default=SCOUT_INPUT_VERSION, pattern="^scout-editor-input-v1$"
    )
    editorial_contract_version: str = Field(
        default=EDITORIAL_CONTRACT_VERSION,
        pattern="^scout-editorial-semantics-v1$",
    )
    generated_at: datetime
    report_id: ReportId
    content_fingerprint: HashText
    scout_version: NonEmptyText
    ranking_schema_version: NonEmptyText
    source_run_id: str = Field(
        pattern=r"^(poll-run:[1-9][0-9]*|snapshot:sha256:[0-9a-f]{64})$"
    )
    ranking_parameters: RankingParameters
    event_counts: EventCounts
    ranked_events: tuple[RankedEditorialEvent, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def validate_rankings(self) -> ScoutEditorInputV1:
        if self.event_counts.reported != len(self.ranked_events):
            raise ValueError("reported count must equal ranked event count")
        ids = [event.event_id for event in self.ranked_events]
        ranks = [event.rank for event in self.ranked_events]
        if len(ids) != len(set(ids)):
            raise ValueError("ranked event IDs must be unique")
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("rank must be contiguous and ordered from one")
        return self
