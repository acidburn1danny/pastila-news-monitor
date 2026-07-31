"""Private explainability contracts for deterministic episode-flow optimization."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.contracts.editor_output import EditorAgentOutputV1
from pastila_scout.contracts.scout_editor import RankedEditorialEvent


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FlowDecisionOutcome(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"


class FlowReason(_FrozenModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class FlowDecision(_FrozenModel):
    rule: str = Field(min_length=1)
    outcome: FlowDecisionOutcome
    reason: FlowReason
    event_ids: tuple[int, ...] = ()
    positions: tuple[int, ...] = ()
    contribution: float = 0.0
    hard: bool = False


class FlowObjectiveBreakdown(_FrozenModel):
    hard_constraints_satisfied: bool
    mandatory_placement: float
    opening_strength: float
    ending_strength: float
    early_momentum: float
    category_rhythm: float
    tone_rhythm: float
    score_cliff: float
    continuity: float
    inherited_strength: float

    def comparison_values(self) -> tuple[float, ...]:
        """Return the frozen lexicographic objective hierarchy."""

        return (
            float(self.hard_constraints_satisfied),
            self.mandatory_placement,
            self.opening_strength,
            self.ending_strength,
            self.early_momentum,
            self.category_rhythm,
            self.tone_rhythm,
            self.score_cliff,
            self.continuity,
            self.inherited_strength,
        )


class FlowCandidate(_FrozenModel):
    event_ids: tuple[int, ...]
    objective: FlowObjectiveBreakdown


class RuntimeAllocation(_FrozenModel):
    event_id: int = Field(gt=0)
    position: int = Field(gt=0)
    seconds: int = Field(ge=0)
    weight: float = Field(ge=0)
    reason: FlowReason


class FlowDecisionTrace(_FrozenModel):
    initial_order: tuple[int, ...]
    final_order: tuple[int, ...]
    evaluated_candidate_count: int = Field(ge=0)
    summarized_alternatives: tuple[FlowCandidate, ...]
    applied_rules: tuple[FlowDecision, ...]
    hard_constraint_failures: tuple[FlowDecision, ...]
    adjacency_decisions: tuple[FlowDecision, ...]
    opening_decision: FlowDecision | None
    ending_decision: FlowDecision | None
    runtime_allocations: tuple[RuntimeAllocation, ...]
    winning_objective: FlowObjectiveBreakdown | None


@dataclass(frozen=True)
class FlowOptimizationResult:
    """Revised public output plus private, non-fingerprinted flow diagnostics."""

    output: EditorAgentOutputV1
    trace: FlowDecisionTrace


@dataclass(frozen=True)
class FlowEnvironment:
    """Public-only immutable context shared by flow rules."""

    all_selected: tuple[RankedEditorialEvent, ...]
    mandatory_event_ids: frozenset[int]
    avoid_recent_event_ids: frozenset[int]
    previous_episode_reference: str | None
    preferred_categories: frozenset[str]
