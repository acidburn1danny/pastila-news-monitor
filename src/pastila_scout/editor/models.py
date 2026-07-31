"""Internal explainability models for deterministic editorial selection."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DecisionOutcome(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"


class EditorialReason(_FrozenModel):
    """Stable reason code and non-generative explanation."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class EditorialDecision(_FrozenModel):
    """One rule's observable decision for one candidate or the whole run."""

    rule: str = Field(min_length=1)
    outcome: DecisionOutcome
    reason: EditorialReason
    event_id: int | None = Field(default=None, gt=0)
    contribution: float = 0.0
    hard: bool = False


class DecisionTrace(_FrozenModel):
    """Complete deterministic audit trail retained outside the public contract."""

    decisions: tuple[EditorialDecision, ...]
    selected_event_ids: tuple[int, ...]
    backup_event_ids: tuple[int, ...]
    rejected_event_ids: tuple[int, ...]
    conflicts: tuple[EditorialDecision, ...]
