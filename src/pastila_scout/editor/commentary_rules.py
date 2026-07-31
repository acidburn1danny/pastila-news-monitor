"""Replaceable deterministic rules for private commentary plans."""

from collections import Counter
from typing import ClassVar

from pastila_scout.contracts.scout_editor import RankedEditorialEvent
from pastila_scout.editor.blueprint_models import EditorialAngle
from pastila_scout.editor.commentary_models import (
    AudienceEmotion,
    AudienceStrategy,
    CommentaryBeat,
    ComparisonDomain,
    HumorSensitivity,
    IronyMechanism,
    ProtectedTarget,
    PunchlineFunction,
    SatireTarget,
    Sensitivity,
    Takeaway,
)


def _explicit(event: RankedEditorialEvent, key: str):
    return event.extensions.get(key) if event.extensions else None


class SensitivityRule:
    name = "SensitivityRule"

    def assign(self, event: RankedEditorialEvent) -> tuple[Sensitivity, bool]:
        value = _explicit(event, "sensitivity")
        try:
            return Sensitivity(value), False
        except (TypeError, ValueError):
            return Sensitivity.ORDINARY, True


class SatireTargetRule:
    name = "SatireTargetRule"

    def assign(self, event, angles) -> tuple[SatireTarget, ...]:
        if EditorialAngle.HYPOCRISY in angles:
            return (SatireTarget.HYPOCRISY, SatireTarget.CONTRADICTORY_PROMISES)
        if "Politica" in event.categories:
            return (SatireTarget.PERFORMATIVE_POLITICS, SatireTarget.PUBLIC_POSTURING)
        if "Conspiratii" in event.categories:
            return (SatireTarget.PROPAGANDA,)
        if "Economie" in event.categories:
            return (SatireTarget.MISPLACED_PRIORITIES, SatireTarget.SYSTEMIC_FAILURE)
        if EditorialAngle.INCOMPETENCE in angles:
            return (SatireTarget.INCOMPETENCE, SatireTarget.AVOIDABLE_CHAOS)
        if EditorialAngle.ABSURDITY in angles:
            return (SatireTarget.INSTITUTIONAL_ABSURDITY,)
        return (SatireTarget.SYSTEMIC_FAILURE,)


class ProtectedTargetRule:
    name = "ProtectedTargetRule"
    _sensitive: ClassVar[dict[Sensitivity, tuple[ProtectedTarget, ...]]] = {
        Sensitivity.TRAGEDY: (ProtectedTarget.VICTIMS, ProtectedTarget.BEREAVED_PEOPLE),
        Sensitivity.VULNERABLE_PEOPLE: (ProtectedTarget.VULNERABLE_PEOPLE,),
        Sensitivity.CHILDREN: (
            ProtectedTarget.CHILDREN,
            ProtectedTarget.UNINVOLVED_FAMILY_MEMBERS,
        ),
        Sensitivity.MEDICAL: (
            ProtectedTarget.PATIENTS,
            ProtectedTarget.VULNERABLE_PEOPLE,
        ),
        Sensitivity.VIOLENCE: (ProtectedTarget.VICTIMS,),
        Sensitivity.DEATH: (ProtectedTarget.VICTIMS, ProtectedTarget.BEREAVED_PEOPLE),
        Sensitivity.DISASTER: (
            ProtectedTarget.VICTIMS,
            ProtectedTarget.ORDINARY_PEOPLE_AFFECTED,
        ),
    }

    def assign(self, event, sensitivity):
        explicit = _explicit(event, "protected_targets")
        if isinstance(explicit, (list, tuple)):
            try:
                return tuple(dict.fromkeys(ProtectedTarget(item) for item in explicit))
            except ValueError:
                pass
        if sensitivity in self._sensitive:
            return self._sensitive[sensitivity]
        if "Social" in event.categories or "Economie" in event.categories:
            return (ProtectedTarget.ORDINARY_PEOPLE_AFFECTED,)
        return ()


class IronyMechanismRule:
    name = "IronyMechanismRule"

    def assign(self, targets, sensitivity):
        if sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED):
            return (IronyMechanism.UNDERSTATEMENT, IronyMechanism.DEADPAN)
        if (
            SatireTarget.HYPOCRISY in targets
            or SatireTarget.CONTRADICTORY_PROMISES in targets
        ):
            return (IronyMechanism.CONTRADICTION, IronyMechanism.PROMISE_VS_REALITY)
        if SatireTarget.INSTITUTIONAL_ABSURDITY in targets:
            return (IronyMechanism.LITERALIZATION, IronyMechanism.ABSURD_ENUMERATION)
        return (IronyMechanism.FALSE_ADMIRATION, IronyMechanism.RHETORICAL_QUESTION)


class AudienceConversationRule:
    name = "AudienceConversationRule"

    def assign(self, event):
        if "Economie" in event.categories:
            return AudienceStrategy.SHARED_FRUSTRATION
        if "Social" in event.categories:
            return AudienceStrategy.RECOGNITION_OF_INJUSTICE
        if "Politica" in event.categories:
            return AudienceStrategy.COLLECTIVE_QUESTION
        return AudienceStrategy.SHARED_DISBELIEF


class WhyItMattersRule:
    name = "WhyItMattersRule"

    def assign(self, event):
        mapping = {
            "Politica": Takeaway.DEMOCRATIC_CONSEQUENCE,
            "Social": Takeaway.SOCIAL_CONSEQUENCE,
            "Economie": Takeaway.ECONOMIC_CONSEQUENCE,
            "Externe": Takeaway.CIVIC_CONSEQUENCE,
            "Conspiratii": Takeaway.DEMOCRATIC_CONSEQUENCE,
            "CanCan": Takeaway.CULTURAL_PATTERN,
        }
        primary = next(
            (mapping[c] for c in event.categories if c in mapping),
            Takeaway.SYSTEMIC_PATTERN,
        )
        secondary = (
            (Takeaway.ROMANIA_SPECIFIC_PATTERN,)
            if "Externe" not in event.categories
            else ()
        )
        return primary, secondary


class EverydayComparisonRule:
    name = "EverydayComparisonRule"

    def assign(self, event, sensitivity):
        if sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED):
            return None, None, "sensitivity_disallows_comparison", False
        mapping = {
            "Politica": (
                ComparisonDomain.GOVERNMENT_COUNTER,
                "public_claim_to_daily_bureaucracy",
            ),
            "Economie": (ComparisonDomain.ANAF, "public_cost_to_household_experience"),
            "Social": (
                ComparisonDomain.PUBLIC_TRANSPORT,
                "system_failure_to_shared_daily_experience",
            ),
            "CanCan": (
                ComparisonDomain.NEIGHBORHOOD_WEDDING,
                "spectacle_to_familiar_ritual",
            ),
            "Diverse": (ComparisonDomain.QUEUE, "avoidable_chaos_to_familiar_delay"),
        }
        for category in event.categories:
            if category in mapping:
                primary, reason = mapping[category]
                return primary, None, reason, True
        return None, None, "no_safe_category_mapping", True


class EmpathyRule:
    name = "EmpathyRule"

    def assign(self, protected, sensitivity, event):
        if sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED):
            emotion = (
                AudienceEmotion.FEAR
                if sensitivity in (Sensitivity.VIOLENCE, Sensitivity.MEDICAL)
                else AudienceEmotion.HELPLESSNESS
            )
            return emotion, AudienceEmotion.INJUSTICE, True, HumorSensitivity.PROHIBITED
        if "Economie" in event.categories:
            return (
                AudienceEmotion.FRUSTRATION,
                AudienceEmotion.EXHAUSTION,
                bool(protected),
                HumorSensitivity.CAREFUL,
            )
        return (
            AudienceEmotion.DISBELIEF,
            AudienceEmotion.FRUSTRATION,
            bool(protected),
            HumorSensitivity.STANDARD,
        )


class CommentaryBeatRule:
    name = "CommentaryBeatRule"

    def assign(self, sensitivity, comparison, empathy_required, has_next):
        sensitive = sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED)
        beats = [CommentaryBeat.FACTUAL_ANCHOR, CommentaryBeat.WHY_IT_MATTERS]
        if sensitive:
            beats += [
                CommentaryBeat.EMPATHY_ACKNOWLEDGMENT,
                CommentaryBeat.AUDIENCE_QUESTION,
            ]
        else:
            beats += [
                CommentaryBeat.IRONIC_OBSERVATION,
                CommentaryBeat.ABSURDITY_EXPLANATION,
                CommentaryBeat.SARCASTIC_TURN,
            ]
            if comparison:
                beats.append(CommentaryBeat.EVERYDAY_COMPARISON)
            if empathy_required:
                beats.append(CommentaryBeat.EMPATHY_ACKNOWLEDGMENT)
            beats += [CommentaryBeat.PUNCHLINE_SETUP, CommentaryBeat.PUNCHLINE]
        if has_next:
            beats.append(CommentaryBeat.TRANSITION_SETUP)
        return tuple(beats)


class PunchlinePlanRule:
    name = "PunchlinePlanRule"

    def assign(self, target, sensitivity, callback):
        if sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED):
            return (
                PunchlineFunction.CONTROLLED_UNDERSTATEMENT,
                "institution_vs_public_consequence",
            )
        if callback is not None:
            return PunchlineFunction.CALLBACK, "repeated_episode_pattern"
        if target is SatireTarget.MISPLACED_PRIORITIES:
            return PunchlineFunction.EXPOSE_PRIORITY_FAILURE, "priority_vs_public_need"
        if target in (SatireTarget.HYPOCRISY, SatireTarget.CONTRADICTORY_PROMISES):
            return PunchlineFunction.CLOSE_CONTRADICTION, "public_claim_vs_outcome"
        return PunchlineFunction.SUMMARIZE_ABSURDITY, "institution_vs_function"


class TransitionPlanRule:
    name = "TransitionPlanRule"


class FactualSummaryPlanRule:
    name = "FactualSummaryPlanRule"


class EvidenceDisciplineRule:
    name = "EvidenceDisciplineRule"


class EpisodeConsistencyRule:
    name = "EpisodeConsistencyRule"

    @staticmethod
    def dominant(values):
        counts = Counter(values)
        return min(counts, key=lambda value: (-counts[value], value.value))
