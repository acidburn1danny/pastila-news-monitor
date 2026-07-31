"""Storage-independent contracts for editorial event ranking."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.models.ai import CacheStatus, VerificationStatus
from pastila_scout.models.event import EventSnapshot


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Recommendation(StrEnum):
    STRONG_PICK = "STRONG_PICK"
    POSSIBLE_PICK = "POSSIBLE_PICK"
    BACKUP = "BACKUP"
    SKIP = "SKIP"


class ScoreComponent(_FrozenModel):
    name: str
    raw_value: float
    normalized_value: float = Field(default=0, ge=0, le=1)
    weighted_contribution: float = Field(default=0, ge=0)
    score: float = Field(ge=0)
    maximum: float = Field(gt=0)
    reason: str


class DeterministicEventScore(_FrozenModel):
    total: float = Field(ge=0, le=100)
    schema_version: str
    components: tuple[ScoreComponent, ...]


class EditorialScoringRequest(_FrozenModel):
    event: EventSnapshot
    deterministic_score: DeterministicEventScore


class EditorialDecision(_FrozenModel):
    importance: int = Field(ge=0, le=10, strict=True)
    virality: int = Field(ge=0, le=10, strict=True)
    absurdity: int = Field(ge=0, le=10, strict=True)
    satirical_potential: int = Field(ge=0, le=10, strict=True)
    public_interest: int = Field(ge=0, le=10, strict=True)
    emotional_impact: int = Field(ge=0, le=10, strict=True)
    originality: int = Field(ge=0, le=10, strict=True)
    recommendation_reason: str = Field(min_length=1, max_length=500)
    editorial_risks: tuple[str, ...] = Field(max_length=20)


class TokenUsage(_FrozenModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    provider_latency_ms: float | None = Field(default=None, ge=0)


class EditorialCacheDiagnostics(_FrozenModel):
    status: CacheStatus = "not_checked"
    fingerprint_version: str = "editorial-v1"
    prompt_version: str
    schema_version: str
    provider: str
    model: str
    created_at: datetime | None = None
    cache_age_seconds: float | None = Field(default=None, ge=0)


class ScoreWeights(_FrozenModel):
    deterministic: float = Field(ge=0, le=1)
    ai_editorial: float = Field(ge=0, le=1)


class EditorialAIResult(_FrozenModel):
    decision: EditorialDecision | None
    ai_editorial_score: float | None = Field(default=None, ge=0, le=100)
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    status: VerificationStatus
    requested_at: datetime
    retry_count: int = Field(ge=0)
    cache_status: CacheStatus
    token_usage: TokenUsage
    cache_diagnostics: EditorialCacheDiagnostics | None = None
    error_message: str | None = None


class RankedEvent(_FrozenModel):
    rank: int = Field(ge=1)
    event: EventSnapshot
    deterministic_score: DeterministicEventScore
    ai_result: EditorialAIResult
    ai_editorial_score: float | None
    final_score: float = Field(ge=0, le=100)
    score_basis: str
    recommendation: Recommendation
    score_weights: ScoreWeights | None = None


class EventRankingReport(_FrozenModel):
    generated_at: datetime
    database_path: str
    days: int
    category: str
    events_eligible: int
    events_processed: int
    events_reported: int
    ai_requests: int
    cache_hits: int
    cache_misses: int
    failed_requests: int
    retries: int
    token_usage: TokenUsage
    rankings: tuple[RankedEvent, ...]
