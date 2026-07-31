"""Composable deterministic rules for editorial candidate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from typing import Protocol

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import RankedEditorialEvent
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.models import (
    DecisionOutcome,
    EditorialDecision,
    EditorialReason,
)


@dataclass(frozen=True)
class SelectionState:
    """Immutable view of the partial selection presented to each rule."""

    selected: tuple[RankedEditorialEvent, ...]
    category_counts: dict[str, int]
    source_ids: frozenset[str]
    target_runtime_seconds: int
    minimum_story_seconds: int


class EditorialRule(Protocol):
    """Independent candidate rule used by the selection engine."""

    name: str

    def evaluate(
        self,
        candidate: RankedEditorialEvent,
        state: SelectionState,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> EditorialDecision: ...


class EditorialConstraint(EditorialRule, Protocol):
    """Marker protocol for rules capable of hard candidate rejection."""

    can_reject: bool


def decision(
    rule: str,
    candidate: RankedEditorialEvent,
    outcome: DecisionOutcome,
    code: str,
    message: str,
    *,
    contribution: float = 0,
    hard: bool = False,
) -> EditorialDecision:
    return EditorialDecision(
        rule=rule,
        outcome=outcome,
        reason=EditorialReason(code=code, message=message),
        event_id=candidate.event_id,
        contribution=contribution,
        hard=hard,
    )


class MandatoryInclusionRule:
    name = "mandatory_inclusion"

    def evaluate(self, candidate, state, profile, context):
        if candidate.event_id in context.mandatory_event_ids:
            return decision(
                self.name,
                candidate,
                DecisionOutcome.APPLIED,
                "mandatory_event",
                "Episode context requires this event.",
                contribution=10_000,
                hard=True,
            )
        return decision(
            self.name,
            candidate,
            DecisionOutcome.NOT_APPLICABLE,
            "not_mandatory",
            "Event is not mandatory.",
        )


class ExcludedEventsRule:
    name = "excluded_events"
    can_reject = True

    def evaluate(self, candidate, state, profile, context):
        if candidate.event_id in context.excluded_event_ids:
            return decision(
                self.name,
                candidate,
                DecisionOutcome.REJECTED,
                "excluded_event",
                "Episode context excludes this event.",
                hard=True,
            )
        return decision(
            self.name,
            candidate,
            DecisionOutcome.NOT_APPLICABLE,
            "not_excluded",
            "Event is not excluded.",
        )


class RecentEpisodeRule:
    name = "recent_episode_avoidance"

    def evaluate(self, candidate, state, profile, context):
        if candidate.event_id in context.avoid_recent_event_ids:
            return decision(
                self.name,
                candidate,
                DecisionOutcome.APPLIED,
                "recently_used",
                "Event is deprioritized because it was recently used.",
                contribution=-1_000,
            )
        return decision(
            self.name,
            candidate,
            DecisionOutcome.NOT_APPLICABLE,
            "not_recently_used",
            "Event is not marked as recently used.",
        )


class CategoryBalanceRule:
    name = "category_balance"
    can_reject = True

    def evaluate(self, candidate, state, profile, context):
        for category in candidate.categories:
            count = state.category_counts.get(category, 0)
            constraint = profile.category_constraints.get(category)
            maximum = min(
                profile.maximum_stories_from_one_category,
                (
                    constraint.maximum
                    if constraint
                    else profile.maximum_stories_from_one_category
                ),
            )
            if count >= maximum:
                return decision(
                    self.name,
                    candidate,
                    DecisionOutcome.REJECTED,
                    "category_maximum_reached",
                    f"Category maximum reached for {category}.",
                    hard=True,
                )
        contribution = 0.0
        needed: list[str] = []
        for category in candidate.categories:
            constraint = profile.category_constraints.get(category)
            if (
                constraint
                and state.category_counts.get(category, 0) < constraint.preferred
            ):
                contribution += 100
                needed.append(category)
        return decision(
            self.name,
            candidate,
            DecisionOutcome.APPLIED,
            "category_preference" if needed else "category_available",
            (
                f"Event supports preferred categories: {', '.join(needed)}."
                if needed
                else "Event remains within category limits."
            ),
            contribution=contribution,
        )


class DiversityRule:
    name = "source_diversity"

    def evaluate(self, candidate, state, profile, context):
        candidate_sources = {item.source_id for item in candidate.source_provenance}
        new_sources = len(candidate_sources.difference(state.source_ids))
        multiplier = (
            1000 if len(state.source_ids) < profile.minimum_source_diversity else 10
        )
        return decision(
            self.name,
            candidate,
            DecisionOutcome.APPLIED,
            "new_sources" if new_sources else "no_new_sources",
            f"Event adds {new_sources} new representative sources.",
            contribution=float(new_sources * multiplier),
        )


class FreshnessRule:
    name = "freshness"

    def evaluate(self, candidate, state, profile, context):
        return decision(
            self.name,
            candidate,
            DecisionOutcome.APPLIED,
            "publication_recency",
            "Publication time is used as a deterministic tie-breaker.",
        )


class ScorePreferenceRule:
    name = "score_preference"

    def evaluate(self, candidate, state, profile, context):
        return decision(
            self.name,
            candidate,
            DecisionOutcome.APPLIED,
            "scout_final_score",
            "Scout final score is preserved as the base preference.",
            contribution=candidate.final_score,
        )


class RuntimeBudgetRule:
    name = "runtime_budget"
    can_reject = True

    def evaluate(self, candidate, state, profile, context):
        minimum_runtime = (len(state.selected) + 1) * state.minimum_story_seconds
        if minimum_runtime > state.target_runtime_seconds:
            return decision(
                self.name,
                candidate,
                DecisionOutcome.REJECTED,
                "runtime_budget_exceeded",
                "Minimum treatment length would exceed the episode runtime.",
                hard=True,
            )
        return decision(
            self.name,
            candidate,
            DecisionOutcome.APPLIED,
            "runtime_available",
            "Episode runtime can accommodate the minimum treatment length.",
        )


DEFAULT_RULES: tuple[EditorialRule, ...] = (
    MandatoryInclusionRule(),
    ExcludedEventsRule(),
    RecentEpisodeRule(),
    CategoryBalanceRule(),
    DiversityRule(),
    FreshnessRule(),
    ScorePreferenceRule(),
    RuntimeBudgetRule(),
)


def ai_dimension(event: RankedEditorialEvent, name: str) -> int:
    """Read an optional public AI dimension without requiring an AI provider."""

    if event.ai_editorial_score is None:
        return 0
    return int(getattr(event.ai_editorial_score.dimensions, name))


class BackupQualityRule:
    """Order backups and map them to the closest selected editorial role."""

    name = "backup_quality"

    @staticmethod
    def order_key(event: RankedEditorialEvent) -> tuple[object, ...]:
        published = event.publication_bounds.last_published_at
        if published is not None and published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        timestamp = published.timestamp() if published is not None else float("-inf")
        return -event.final_score, -timestamp, event.score_rank, event.event_id

    @staticmethod
    def replacement_key(
        backup: RankedEditorialEvent, selected: RankedEditorialEvent
    ) -> tuple[object, ...]:
        return (
            -len(set(backup.categories).intersection(selected.categories)),
            abs(backup.final_score - selected.final_score),
            selected.rank,
            selected.event_id,
        )


class EditorialConfidenceRule:
    """Calculate episode suitability without changing inherited Scout scores."""

    name = "editorial_confidence"

    @staticmethod
    def calculate(
        event: RankedEditorialEvent,
        *,
        mandatory: bool,
        supports_category_preference: bool,
        backup: bool = False,
    ) -> int:
        value = round(event.final_score)
        if mandatory:
            value += 10
        if supports_category_preference:
            value += 5
        if backup:
            value -= 5
        value -= min(10, len(event.editorial_risks) * 2)
        return max(0, min(100, value))
