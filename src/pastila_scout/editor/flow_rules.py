"""Replaceable objective rules and constraints for deterministic episode flow."""

from __future__ import annotations

from datetime import UTC
from itertools import pairwise
from typing import Protocol

from pastila_scout.contracts.scout_editor import RankedEditorialEvent
from pastila_scout.editor.flow_models import FlowEnvironment
from pastila_scout.editor.rules import ai_dimension


class FlowRule(Protocol):
    name: str

    def score(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> float: ...


class FlowConstraint(Protocol):
    name: str

    def validate(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> str | None: ...


class SelectedSetConstraint:
    name = "selected_set_preservation"

    def validate(self, order, environment):
        if {event.event_id for event in order} != {
            event.event_id for event in environment.all_selected
        }:
            return "Flow order must preserve the selected event set."
        return None


class MandatoryPlacementRule:
    name = "mandatory_placement"

    def score(self, order, environment):
        size = len(order)
        return sum(
            size - position
            for position, event in enumerate(order)
            if event.event_id in environment.mandatory_event_ids
        )


class OpeningStrengthFlowRule:
    name = "opening_strength"

    def score(self, order, environment):
        if not order:
            return 0.0
        event = order[0]
        freshness = _freshness_rank(event, environment.all_selected)
        category = (
            5
            if set(event.categories).intersection(environment.preferred_categories)
            else 0
        )
        mandatory = 10 if event.event_id in environment.mandatory_event_ids else 0
        repetition = -15 if event.event_id in environment.avoid_recent_event_ids else 0
        return (
            ai_dimension(event, "importance") * 4
            + ai_dimension(event, "public_interest") * 4
            + event.final_score * 0.5
            + freshness
            + category
            + mandatory
            + repetition
        )


class EndingStrengthFlowRule:
    name = "ending_strength"

    def score(self, order, environment):
        if len(order) != len(environment.all_selected) or not order:
            return 0.0
        event = order[-1]
        callback = (
            8
            if environment.previous_episode_reference
            and event.event_id in environment.avoid_recent_event_ids
            else 0
        )
        return (
            ai_dimension(event, "absurdity") * 4
            + ai_dimension(event, "satirical_potential") * 4
            + ai_dimension(event, "public_interest") * 2
            + event.final_score * 0.2
            + callback
        )


class EarlyMomentumFlowRule:
    name = "early_episode_momentum"

    def score(self, order, environment):
        if len(order) < 2:
            return 0.0
        first, second = order[:2]
        second_energy = _energy(second)
        breadth = 8 if not set(first.categories).intersection(second.categories) else 0
        escalation = 8 if second_energy > _energy(first) else 0
        low_energy_penalty = -12 if second_energy < 12 else 0
        return second_energy + breadth + escalation + low_energy_penalty


class CategoryRhythmFlowRule:
    name = "category_rhythm"

    def score(self, order, environment):
        total = 0.0
        for previous, current in pairwise(order):
            overlap = set(previous.categories).intersection(current.categories)
            if not overlap:
                total += 12
            elif _continuation_is_justified(previous, current):
                total -= 2
            else:
                total -= 18
        return total


class ToneRhythmFlowRule:
    name = "tone_rhythm"

    def score(self, order, environment):
        total = 0.0
        for previous, current in pairwise(order):
            previous_tone = _tone(previous)
            current_tone = _tone(current)
            total += 8 if previous_tone != current_tone else -8
        return total


class ScoreCliffFlowRule:
    name = "score_cliff"

    def score(self, order, environment):
        total = 0.0
        for previous, current in pairwise(order):
            cliff = previous.final_score - current.final_score
            if cliff > 25:
                total += 4 if ai_dimension(current, "absurdity") >= 8 else -20
        return total


class ContinuityFlowRule:
    name = "previous_episode_continuity"

    def score(self, order, environment):
        if not environment.avoid_recent_event_ids:
            return 0.0
        return sum(
            -20 if event.event_id in environment.avoid_recent_event_ids else 0
            for event in order[:2]
        )


class InheritedStrengthFlowRule:
    name = "inherited_editorial_strength"

    def score(self, order, environment):
        size = len(order)
        return sum(
            event.final_score * (size - position) / max(1, size)
            for position, event in enumerate(order)
        )


DEFAULT_FLOW_RULES: tuple[FlowRule, ...] = (
    MandatoryPlacementRule(),
    OpeningStrengthFlowRule(),
    EndingStrengthFlowRule(),
    EarlyMomentumFlowRule(),
    CategoryRhythmFlowRule(),
    ToneRhythmFlowRule(),
    ScoreCliffFlowRule(),
    ContinuityFlowRule(),
    InheritedStrengthFlowRule(),
)

DEFAULT_FLOW_CONSTRAINTS: tuple[FlowConstraint, ...] = (SelectedSetConstraint(),)


def transition_type(
    previous: RankedEditorialEvent,
    current: RankedEditorialEvent,
    environment: FlowEnvironment,
) -> tuple[str, str]:
    """Return one frozen transition value and its deterministic reason code."""

    if (
        environment.previous_episode_reference
        and current.event_id in environment.avoid_recent_event_ids
    ):
        return "callback", "previous_episode_callback"
    if _is_grave(previous) and ai_dimension(current, "absurdity") >= 8:
        return "comic_relief", "grave_to_comic_relief"
    overlap = set(previous.categories).intersection(current.categories)
    if overlap and _continuation_is_justified(previous, current):
        return "continuation", "category_continuation"
    if _energy(current) > _energy(previous) + 3:
        return "escalation", "energy_escalation"
    if not overlap:
        return "contrast", "category_contrast"
    if previous.final_score - current.final_score > 25:
        return "hard_cut", "score_cliff_hard_cut"
    if _tone(previous) != _tone(current):
        return "tone_shift", "tone_change"
    return "hard_cut", "deterministic_separation"


def _freshness_rank(
    event: RankedEditorialEvent, selected: tuple[RankedEditorialEvent, ...]
) -> int:
    def timestamp(item: RankedEditorialEvent) -> float:
        value = item.publication_bounds.last_published_at
        if value is None:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.timestamp()

    ordered = sorted(
        selected,
        key=lambda item: (
            item.publication_bounds.last_published_at is None,
            -timestamp(item),
            item.rank,
            item.event_id,
        ),
    )
    return len(ordered) - ordered.index(event)


def _energy(event: RankedEditorialEvent) -> float:
    return (
        ai_dimension(event, "importance")
        + ai_dimension(event, "virality")
        + ai_dimension(event, "satirical_potential")
        + event.final_score / 10
    )


def _is_grave(event: RankedEditorialEvent) -> bool:
    return (
        ai_dimension(event, "importance") + ai_dimension(event, "public_interest") >= 16
        and ai_dimension(event, "absurdity") <= 3
    )


def _tone(event: RankedEditorialEvent) -> str:
    if (
        ai_dimension(event, "absurdity") >= 7
        or ai_dimension(event, "satirical_potential") >= 8
    ):
        return "comic"
    if _is_grave(event):
        return "grave"
    if "Politica" in event.categories:
        return "political"
    if "Social" in event.categories:
        return "social"
    if "Economie" in event.categories:
        return "economic"
    return "neutral"


def _continuation_is_justified(
    previous: RankedEditorialEvent, current: RankedEditorialEvent
) -> bool:
    return (
        bool(set(previous.categories).intersection(current.categories))
        and abs(previous.final_score - current.final_score) <= 15
    )
