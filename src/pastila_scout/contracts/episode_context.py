"""Episode-specific state supplied independently of selection policy."""

from pydantic import Field, field_validator, model_validator

from pastila_scout.contracts.common import (
    EPISODE_CONTEXT_VERSION,
    DurationValue,
    ExtensibleContractModel,
    NonEmptyText,
    ShortText,
    validate_unique_positive_ids,
)


class EpisodeContextV1(ExtensibleContractModel):
    contract_version: str = Field(
        default=EPISODE_CONTEXT_VERSION, pattern="^episode-context-v1$"
    )
    episode_format: NonEmptyText
    platform: NonEmptyText
    language: NonEmptyText
    target_runtime: DurationValue
    target_story_count: int = Field(gt=0)
    audience: NonEmptyText
    pacing: NonEmptyText
    tone: tuple[NonEmptyText, ...] = Field(min_length=1)
    humor_style: tuple[NonEmptyText, ...] = ()
    factual_strictness: NonEmptyText
    political_balance: NonEmptyText
    opening_preference: NonEmptyText | None = None
    closing_preference: NonEmptyText | None = None
    presenter_notes: tuple[ShortText, ...] = Field(default=(), max_length=20)
    mandatory_event_ids: tuple[int, ...] = ()
    excluded_event_ids: tuple[int, ...] = ()
    theme: NonEmptyText | None = None
    episode_objective: NonEmptyText
    previous_episode_reference: NonEmptyText | None = None
    avoid_recent_event_ids: tuple[int, ...] = ()

    @field_validator(
        "mandatory_event_ids", "excluded_event_ids", "avoid_recent_event_ids"
    )
    @classmethod
    def validate_ids(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_unique_positive_ids(value)

    @model_validator(mode="after")
    def validate_disjoint_ids(self) -> EpisodeContextV1:
        mandatory = set(self.mandatory_event_ids)
        if mandatory.intersection(self.excluded_event_ids):
            raise ValueError("mandatory and excluded event IDs must be disjoint")
        if mandatory.intersection(self.avoid_recent_event_ids):
            raise ValueError(
                "mandatory and recently avoided event IDs must be disjoint"
            )
        return self
