"""Storage-independent contracts for advisory AI event verification."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VerificationStatus = Literal[
    "success",
    "cache_hit",
    "disabled",
    "missing_api_key",
    "provider_error",
    "invalid_response",
    "retry_exhausted",
]
CacheStatus = Literal["hit", "miss", "corrupt", "not_checked"]
DecisionReason = Literal[
    "verified",
    "score_below_threshold",
    "provider_unavailable",
    "schema_validation_failed",
    "provider_failed",
    "insufficient_context",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VerificationArticle(_FrozenModel):
    """Confirmed article facts supplied to a verifier."""

    article_id: int
    event_id: int
    normalized_title: str
    summary: str | None
    published_at: str | None
    source_id: str
    source_name: str
    url: str
    categories: tuple[str, ...] = ()


class EventVerificationRequest(_FrozenModel):
    """One deterministic candidate pair, independent of persistence."""

    left: VerificationArticle
    right: VerificationArticle
    deterministic_similarity: float = Field(ge=0, le=1)


class ProviderVerificationDecision(_FrozenModel):
    """Strict provider response schema."""

    same_event: bool
    ai_similarity_score: int = Field(ge=0, le=100, strict=True)
    same_people: bool | None
    same_institution: bool | None
    same_location: bool | None
    same_context: bool | None
    reasoning: str = Field(min_length=1, max_length=1000)


class AIUsageDiagnostics(_FrozenModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    provider_latency_ms: float | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)


class AICacheDiagnostics(_FrozenModel):
    status: CacheStatus = "not_checked"
    fingerprint_version: str = "verification-v1"
    prompt_version: str
    schema_version: str = "event-verification-v1"
    provider: str
    model: str
    created_at: datetime | None = None
    cache_age_seconds: float | None = Field(default=None, ge=0)


class VerificationDecisionMetadata(_FrozenModel):
    confirmed: bool
    reason: DecisionReason
    threshold: int = 85
    score: int = Field(ge=0, le=100)


class AIVerificationResult(_FrozenModel):
    """Typed verification result, including non-AI fallback states."""

    same_event: bool
    ai_similarity_score: int = Field(ge=0, le=100)
    same_people: bool | None
    same_institution: bool | None
    same_location: bool | None
    same_context: bool | None
    reasoning: str
    provider: str
    model: str
    prompt_version: str
    status: VerificationStatus
    requested_at: datetime
    retry_count: int = Field(ge=0)
    cache_status: CacheStatus
    usage: AIUsageDiagnostics = AIUsageDiagnostics()
    cache_diagnostics: AICacheDiagnostics | None = None


class VerificationRecord(_FrozenModel):
    request: EventVerificationRequest
    result: AIVerificationResult
    confirmed_same_event: bool
    decision: VerificationDecisionMetadata | None = None


class VerificationRunReport(_FrozenModel):
    generated_at: datetime
    database_path: str
    candidate_pairs: int
    ai_requests: int
    cache_hits: int
    cache_misses: int
    confirmed_same_event_pairs: int
    rejected_pairs: int
    unavailable_results: int
    failed_requests: int
    retries: int
    usage: AIUsageDiagnostics = AIUsageDiagnostics()
    records: tuple[VerificationRecord, ...]
