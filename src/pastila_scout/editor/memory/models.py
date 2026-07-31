"""Immutable public models for verdict-driven editorial memory."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrozenModel(BaseModel):
    """Strict immutable base used by the editorial-memory boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class EditorialCategory(StrEnum):
    INTRODUCTION = "Introduction"
    STORY_STRUCTURE = "Story Structure"
    STORY_SELECTION = "Story Selection"
    STORY_ORDERING = "Story Ordering"
    CONTEXT_LENGTH = "Context Length"
    EXPLANATION = "Explanation"
    SARCASM = "Sarcasm"
    IRONY = "Irony"
    HUMOR = "Humor"
    EMOTIONAL_IMPACT = "Emotional Impact"
    POLITICAL_COMMENTARY = "Political Commentary"
    NARRATIVE_FLOW = "Narrative Flow"
    TRANSITIONS = "Transitions"
    PACING = "Pacing"
    PUNCHLINES = "Punchlines"
    ENDING = "Ending"
    AUDIENCE_ENGAGEMENT = "Audience Engagement"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ObservationStrength(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Recommendation(StrEnum):
    POSSIBLE_EDITORIAL_IMPROVEMENT = "possible_editorial_improvement"
    POTENTIAL_PROMPT_EXPERIMENT = "potential_prompt_experiment"
    NO_ACTION = "no_action"


class SectionScore(FrozenModel):
    section: str = Field(min_length=1)
    score: float = Field(ge=0, le=10)


class VerdictInput(FrozenModel):
    episode_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    overall_score: float | None = Field(default=None, ge=0, le=10)
    section_scores: tuple[SectionScore, ...] = ()
    comments: tuple[str, ...] = Field(min_length=1)

    @field_validator("comments")
    @classmethod
    def comments_must_have_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(comment.strip() for comment in value)
        if any(not comment for comment in cleaned):
            raise ValueError("verdict comments cannot be empty")
        return cleaned


class EditorialObservation(FrozenModel):
    observation_id: str = Field(pattern=r"^EO-[0-9a-f]{16}$")
    episode_id: str
    timestamp: str
    category: EditorialCategory
    sentiment: Sentiment
    strength: ObservationStrength
    affected_section: str
    original_comment: str
    normalized_finding: str


class EditorialPattern(FrozenModel):
    category: EditorialCategory
    normalized_finding: str
    sentiment: Sentiment
    occurrence_count: int = Field(gt=0)
    episode_ids: tuple[str, ...]
    supporting_observation_ids: tuple[str, ...]
    confidence: int = Field(ge=0, le=100)


class CandidateFinding(EditorialPattern):
    recommendation: Recommendation


class EditorialProfile(FrozenModel):
    profile_version: int = Field(ge=1)
    current_strengths: tuple[str, ...] = ()
    current_weaknesses: tuple[str, ...] = ()
    emerging_trends: tuple[str, ...] = ()


class EditorialMemory(FrozenModel):
    schema_version: int = 1
    observations: tuple[EditorialObservation, ...] = ()
    profile: EditorialProfile = EditorialProfile(profile_version=1)


class VerdictSummary(FrozenModel):
    overall_score: float | None
    positive_findings: tuple[str, ...]
    negative_findings: tuple[str, ...]
    observations_created: int = Field(ge=0)


class EditorialMemoryUpdate(FrozenModel):
    observations_added: int = Field(ge=0)
    existing_observations_reinforced: int = Field(ge=0)
    editorial_categories_updated: tuple[EditorialCategory, ...]


class VerdictProcessingResult(FrozenModel):
    verdict_summary: VerdictSummary
    memory_update: EditorialMemoryUpdate
    editorial_profile: EditorialProfile
    candidate_findings: tuple[CandidateFinding, ...]
    memory: EditorialMemory
