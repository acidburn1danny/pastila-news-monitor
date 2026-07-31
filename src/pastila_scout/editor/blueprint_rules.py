"""Replaceable deterministic rules for private editorial blueprint assignment."""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import RankedEditorialEvent
from pastila_scout.editor.blueprint_models import (
    AudienceQuestion,
    ClosingBlueprint,
    ClosingEffect,
    ContinuityBlueprint,
    EditorialAngle,
    EditorialTheme,
    EmotionalTrajectory,
    EpisodeTension,
    EpisodeThesis,
    EvidenceDiscipline,
    EvidenceReference,
    FinalEmotionalEffect,
    FinalSatiricalEffect,
    NarrativeFunction,
    OpenerFunction,
    OpeningBlueprint,
    ProhibitedFraming,
    SafeFactField,
    SegmentIntent,
    SegmentLevels,
    TransitionIntent,
    UnresolvedQuestionRole,
)
from pastila_scout.editor.rules import ai_dimension

CATEGORY_ORDER = (
    "Politica",
    "Social",
    "Conspiratii",
    "Economie",
    "CanCan",
    "Externe",
    "Diverse",
)
CATEGORY_THEMES = {
    "Politica": EditorialTheme.POLITICAL_ACCOUNTABILITY,
    "Social": EditorialTheme.SOCIAL_CONSEQUENCE,
    "Conspiratii": EditorialTheme.CONSPIRACY_AND_PROPAGANDA,
    "Economie": EditorialTheme.ECONOMIC_PRESSURE,
    "CanCan": EditorialTheme.PUBLIC_ABSURDITY,
    "Externe": EditorialTheme.EXTERNAL_AFFAIRS,
    "Diverse": EditorialTheme.CIVIC_RELEVANCE,
}
SAFE_FACTS = (
    SafeFactField.CANONICAL_TITLE,
    SafeFactField.CANONICAL_SUMMARY,
    SafeFactField.PUBLICATION_BOUNDS,
    SafeFactField.CATEGORIES,
    SafeFactField.SOURCE_PROVENANCE,
)
PROHIBITED_FRAMING = (
    ProhibitedFraming.UNSUPPORTED_CAUSALITY,
    ProhibitedFraming.UNVERIFIED_MOTIVE,
    ProhibitedFraming.INVENTED_QUOTE,
    ProhibitedFraming.EXAGGERATED_CERTAINTY,
    ProhibitedFraming.SOURCE_CONFLATION,
)


class BlueprintRule(Protocol):
    name: str


class EpisodeThemeRule:
    name = "episode_theme"

    def assign(
        self,
        events: tuple[RankedEditorialEvent, ...],
        levels: tuple[SegmentLevels, ...],
        context: EpisodeContextV1,
        closing_effect: ClosingEffect,
    ) -> EpisodeThesis:
        counts = Counter(category for event in events for category in event.categories)
        ranked_categories = sorted(
            counts,
            key=lambda category: (
                -counts[category],
                CATEGORY_ORDER.index(category),
            ),
        )
        themes = []
        for category in ranked_categories:
            theme = CATEGORY_THEMES[category]
            if theme not in themes:
                themes.append(theme)
        dominant = themes[0] if themes else EditorialTheme.MIXED_PUBLIC_AFFAIRS
        secondary = themes[1] if len(themes) > 1 else None
        satire = _average_level(tuple(item.satire_level for item in levels))
        seriousness = _average_level(tuple(item.tension_level for item in levels))
        return EpisodeThesis(
            dominant_theme=dominant,
            secondary_theme=secondary,
            episode_tension=_episode_tension(dominant, satire, seriousness),
            emotional_trajectory=_trajectory(levels),
            satire_intensity=satire,
            seriousness_balance=seriousness,
            intended_closing_effect=closing_effect,
            context_theme_reference=context.theme,
        )


class SegmentIntentRule:
    name = "segment_intent"

    def assign(
        self,
        event: RankedEditorialEvent,
        *,
        position: int,
        count: int,
        public_transition: str | None,
        levels: SegmentLevels,
    ) -> SegmentIntent:
        if position == 1:
            return SegmentIntent.ESTABLISH_CONTEXT
        if position == count:
            return (
                SegmentIntent.CLOSE_WITH_ABSURDITY
                if levels.satire_level >= 4
                else SegmentIntent.CLOSE_WITH_REFLECTION
            )
        mapping = {
            "escalation": SegmentIntent.ESCALATE,
            "contrast": SegmentIntent.CONTRAST,
            "comic_relief": SegmentIntent.RELIEVE_TENSION,
            "callback": SegmentIntent.RETURN_TO_CORE_THEME,
            "continuation": SegmentIntent.DEMONSTRATE_CONSEQUENCE,
            "tone_shift": SegmentIntent.BROADEN_SCOPE,
            "hard_cut": SegmentIntent.INTRODUCE_CONFLICT,
        }
        if position == count - 1:
            return SegmentIntent.PREPARE_CLOSING
        return mapping.get(public_transition, SegmentIntent.BROADEN_SCOPE)


class EditorialAngleRule:
    name = "editorial_angle"

    def assign(self, event: RankedEditorialEvent) -> tuple[EditorialAngle, ...]:
        angles: list[EditorialAngle] = []

        def add(value: EditorialAngle) -> None:
            if value not in angles and len(angles) < 3:
                angles.append(value)

        for category in CATEGORY_ORDER:
            if category not in event.categories:
                continue
            if category == "Politica":
                add(EditorialAngle.ACCOUNTABILITY)
                add(EditorialAngle.POLITICAL_CONTRADICTION)
            elif category == "Social":
                add(EditorialAngle.SOCIAL_IMPACT)
                add(EditorialAngle.HUMAN_CONSEQUENCE)
            elif category == "Economie":
                add(EditorialAngle.ECONOMIC_PRESSURE)
                add(EditorialAngle.PUBLIC_COST)
            elif category == "Conspiratii":
                add(EditorialAngle.PROPAGANDA)
                add(EditorialAngle.SYSTEMIC_PATTERN)
            elif category == "CanCan":
                add(EditorialAngle.ABSURDITY)
            else:
                add(EditorialAngle.CIVIC_RELEVANCE)
        if ai_dimension(event, "absurdity") >= 7:
            add(EditorialAngle.ABSURDITY)
        if not angles:
            add(EditorialAngle.CIVIC_RELEVANCE)
        return tuple(angles)


class NarrativeFunctionRule:
    name = "narrative_function"

    def assign(
        self, *, position: int, count: int, public_role: str
    ) -> NarrativeFunction:
        if position == 1:
            return NarrativeFunction.OPENER
        if position == count:
            return NarrativeFunction.CLOSER
        if position == count - 1:
            return NarrativeFunction.PENULTIMATE_SETUP
        mapping = {
            "escalation": NarrativeFunction.ESCALATION,
            "contrast": NarrativeFunction.CONTRAST,
            "comic_relief": NarrativeFunction.RELIEF,
            "callback": NarrativeFunction.CALLBACK,
            "development": NarrativeFunction.EVIDENCE,
        }
        if position == 2:
            return NarrativeFunction.FOUNDATION
        return mapping.get(public_role, NarrativeFunction.BRIDGE)


class EnergyCurveRule:
    name = "energy_curve"

    def assign(self, event: RankedEditorialEvent) -> SegmentLevels:
        importance = ai_dimension(event, "importance")
        public_interest = ai_dimension(event, "public_interest")
        virality = ai_dimension(event, "virality")
        satirical = ai_dimension(event, "satirical_potential")
        absurdity = ai_dimension(event, "absurdity")
        emotional = ai_dimension(event, "emotional_impact")
        if event.ai_editorial_score is None:
            fallback = _score_level(event.final_score)
            return SegmentLevels(
                tension_level=fallback,
                energy_level=fallback,
                satire_level=max(1, fallback - 1),
                emotional_weight=fallback,
            )
        return SegmentLevels(
            tension_level=_pair_level(importance, public_interest),
            energy_level=_triple_level(importance, virality, satirical),
            satire_level=_pair_level(absurdity, satirical),
            emotional_weight=_pair_level(emotional, public_interest),
        )


class TransitionIntentRule:
    name = "transition_intent"

    def assign(
        self, public_transition: str, *, enters_closer: bool
    ) -> TransitionIntent:
        if enters_closer and public_transition not in {"comic_relief", "callback"}:
            return TransitionIntent.PREPARE_FINALE
        mapping = {
            "continuation": TransitionIntent.PRESERVE_TOPIC,
            "contrast": TransitionIntent.SHARPEN_CONTRAST,
            "escalation": TransitionIntent.RAISE_STAKES,
            "hard_cut": TransitionIntent.RESET_ENERGY,
            "tone_shift": TransitionIntent.WIDEN_SCOPE,
            "comic_relief": TransitionIntent.RELEASE_TENSION,
            "callback": TransitionIntent.CALLBACK_TO_PREVIOUS,
        }
        return mapping.get(public_transition, TransitionIntent.WIDEN_SCOPE)


class OpeningBlueprintRule:
    name = "opening_blueprint"

    def assign(
        self,
        event: RankedEditorialEvent,
        tension: EpisodeTension,
        handoff: TransitionIntent | None,
        context: EpisodeContextV1,
    ) -> OpeningBlueprint:
        if event.event_id in context.mandatory_event_ids:
            function = OpenerFunction.MANDATORY_ANCHOR
        elif "Politica" in event.categories:
            function = OpenerFunction.INSTITUTIONAL_FOCUS
        elif ai_dimension(event, "public_interest") >= 8:
            function = OpenerFunction.AUDIENCE_RELEVANCE
        else:
            function = OpenerFunction.ESTABLISH_STAKES
        question = (
            AudienceQuestion.WHO_IS_ACCOUNTABLE
            if "Politica" in event.categories
            else (
                AudienceQuestion.WHO_IS_AFFECTED
                if "Social" in event.categories
                else AudienceQuestion.WHY_IT_MATTERS
            )
        )
        return OpeningBlueprint(
            event_id=event.event_id,
            opener_function=function,
            primary_audience_question=question,
            tension_introduced=tension,
            facts_to_establish=SAFE_FACTS,
            prohibited_framing=PROHIBITED_FRAMING,
            handoff_intent=handoff,
        )


class ClosingBlueprintRule:
    name = "closing_blueprint"

    def assign(
        self,
        event: RankedEditorialEvent,
        levels: SegmentLevels,
        closing_effect: ClosingEffect,
        transition_intent: TransitionIntent | None,
        previous_event_id: int | None,
    ) -> ClosingBlueprint:
        callback = (
            previous_event_id
            if transition_intent == TransitionIntent.CALLBACK_TO_PREVIOUS
            else None
        )
        emotional = (
            FinalEmotionalEffect.RELIEF
            if closing_effect == ClosingEffect.ABSURDITY
            else (
                FinalEmotionalEffect.CONCERN
                if levels.tension_level >= 4
                else FinalEmotionalEffect.REFLECTION
            )
        )
        satirical = (
            FinalSatiricalEffect.CALLBACK
            if callback is not None
            else (
                FinalSatiricalEffect.ABSURD_RESOLUTION
                if closing_effect == ClosingEffect.ABSURDITY
                else (
                    FinalSatiricalEffect.INSTITUTIONAL_CRITIQUE
                    if "Politica" in event.categories
                    else FinalSatiricalEffect.IRONIC_DISTANCE
                )
            )
        )
        unresolved = (
            UnresolvedQuestionRole.ACCOUNTABILITY_QUESTION
            if "Politica" in event.categories
            else (
                UnresolvedQuestionRole.CONSEQUENCE_QUESTION
                if levels.tension_level >= 4
                else UnresolvedQuestionRole.NONE
            )
        )
        return ClosingBlueprint(
            event_id=event.event_id,
            closing_mode=closing_effect,
            callback_target_event_id=callback,
            final_emotional_effect=emotional,
            final_satirical_effect=satirical,
            unresolved_question_role=unresolved,
            land_on=closing_effect,
        )


class EvidenceDisciplineRule:
    name = "evidence_discipline"

    def assign(self, event: RankedEditorialEvent) -> EvidenceDiscipline:
        provenance = tuple(
            EvidenceReference(
                source_id=item.source_id,
                url=item.url,
                title=item.title,
                published_at=(
                    item.published_at.isoformat() if item.published_at else None
                ),
            )
            for item in sorted(
                event.source_provenance,
                key=lambda value: (value.source_id, value.url, value.title),
            )
        )
        return EvidenceDiscipline(
            safe_fact_fields=SAFE_FACTS,
            provenance=provenance,
            prohibited_framing=PROHIBITED_FRAMING,
        )


class ContinuityRule:
    name = "continuity"

    def assign(
        self,
        event_ids: tuple[int, ...],
        context: EpisodeContextV1,
    ) -> ContinuityBlueprint:
        selected = set(event_ids)
        return ContinuityBlueprint(
            previous_episode_reference=context.previous_episode_reference,
            recent_event_ids_present=tuple(
                sorted(selected.intersection(context.avoid_recent_event_ids))
            ),
            mandatory_event_ids_present=tuple(
                sorted(selected.intersection(context.mandatory_event_ids))
            ),
            excluded_event_ids_present=tuple(
                sorted(selected.intersection(context.excluded_event_ids))
            ),
            requested_episode_size=context.target_story_count,
        )


def closing_effect_for(
    event: RankedEditorialEvent,
    levels: SegmentLevels,
    transition_intent: TransitionIntent | None,
) -> ClosingEffect:
    if transition_intent == TransitionIntent.CALLBACK_TO_PREVIOUS:
        return ClosingEffect.CALLBACK
    if levels.satire_level >= 4:
        return ClosingEffect.ABSURDITY
    if levels.tension_level >= 4:
        return ClosingEffect.CONSEQUENCE
    if "Politica" in event.categories:
        return ClosingEffect.WARNING
    return ClosingEffect.REFLECTION


def _pair_level(first: int, second: int) -> int:
    return max(1, min(5, 1 + (first + second) // 5))


def _triple_level(first: int, second: int, third: int) -> int:
    return max(1, min(5, 1 + (first + second + third) // 8))


def _score_level(score: float) -> int:
    return max(1, min(5, int(score // 20) + 1))


def _average_level(values: tuple[int, ...]) -> int:
    if not values:
        return 1
    return max(1, min(5, (sum(values) + len(values) // 2) // len(values)))


def _trajectory(levels: tuple[SegmentLevels, ...]) -> EmotionalTrajectory:
    if not levels:
        return EmotionalTrajectory.VARIED
    if levels[-1].satire_level >= levels[0].satire_level + 2:
        return EmotionalTrajectory.GRAVE_TO_RELIEF
    if all(item.tension_level >= 4 for item in levels):
        return EmotionalTrajectory.STEADY_GRAVE
    if levels[-1].tension_level > levels[0].tension_level:
        return EmotionalTrajectory.ESCALATING
    if levels[-1].tension_level < levels[0].tension_level:
        return EmotionalTrajectory.REFLECTIVE_CLOSE
    return EmotionalTrajectory.VARIED


def _episode_tension(
    theme: EditorialTheme, satire: int, seriousness: int
) -> EpisodeTension:
    if satire >= 4 and seriousness >= 3:
        return EpisodeTension.ABSURDITY_VS_SERIOUSNESS
    mapping = {
        EditorialTheme.POLITICAL_ACCOUNTABILITY: EpisodeTension.INSTITUTIONAL_ACCOUNTABILITY,
        EditorialTheme.SOCIAL_CONSEQUENCE: EpisodeTension.SOCIAL_DISRUPTION,
        EditorialTheme.ECONOMIC_PRESSURE: EpisodeTension.ECONOMIC_PRESSURE,
        EditorialTheme.CIVIC_RELEVANCE: EpisodeTension.PUBLIC_CONSEQUENCE,
    }
    return mapping.get(theme, EpisodeTension.MIXED)
