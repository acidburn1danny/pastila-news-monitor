"""Replaceable deterministic rules for private voice execution plans."""

from typing import ClassVar

from pastila_scout.editor.commentary_models import (
    AudienceEmotion,
    CommentaryBeat,
    HumorSensitivity,
    IronyMechanism,
    Sensitivity,
    StoryCommentaryBlueprint,
)
from pastila_scout.editor.voice_models import (
    AbsurdReveal,
    AudienceKnowledgeLevel,
    CallbackType,
    ConversationRegister,
    CuriosityTrigger,
    DirectLanguageLevel,
    EmotionalTemperature,
    EmpathyMode,
    EndingVoice,
    HumorEscalationPattern,
    HumorIntensity,
    MarkerFamily,
    PerspectiveShiftType,
    ProtectedDimension,
    RhetoricalQuestionFunction,
    RoastEligibility,
    RomanianExpressionFunction,
    RomanianExpressionType,
    RomanianReferenceType,
    SarcasmIntensity,
    SeriousnessResetFunction,
)

SENSITIVE = {
    Sensitivity.TRAGEDY,
    Sensitivity.VULNERABLE_PEOPLE,
    Sensitivity.CHILDREN,
    Sensitivity.MEDICAL,
    Sensitivity.VIOLENCE,
    Sensitivity.DEATH,
    Sensitivity.DISASTER,
}


class ConversationRegisterRule:
    name = "ConversationRegisterRule"

    def assign(self, story: StoryCommentaryBlueprint) -> ConversationRegister:
        if story.sensitivity in SENSITIVE:
            return ConversationRegister.SERIOUS_COMPANION
        mapping = {
            "shared_disbelief": ConversationRegister.SHARED_DISBELIEF,
            "shared_frustration": ConversationRegister.SHARED_FRUSTRATION,
            "recognition_of_injustice": ConversationRegister.CONTROLLED_OUTRAGE,
        }
        return mapping.get(
            story.audience_strategy.value, ConversationRegister.DIRECT_COMPANION
        )


class HumorRule:
    name = "HumorRule"

    def assign(self, story):
        if story.empathy.humor_sensitivity is HumorSensitivity.PROHIBITED:
            return HumorIntensity.NONE, HumorEscalationPattern.SINGLE
        if story.empathy.humor_sensitivity is HumorSensitivity.RESTRICTED:
            return HumorIntensity.LIGHT, HumorEscalationPattern.SINGLE
        if IronyMechanism.ABSURD_ENUMERATION in story.irony_mechanisms:
            return HumorIntensity.STRONG, HumorEscalationPattern.ENUMERATION
        if story.punchline.callback_event_id:
            return HumorIntensity.MODERATE, HumorEscalationPattern.CALLBACK
        return HumorIntensity.MODERATE, HumorEscalationPattern.TWO_STEP


class ProtectedDimensionRule:
    name = "ProtectedDimensionRule"
    _mapping: ClassVar[dict[Sensitivity, tuple[ProtectedDimension, ...]]] = {
        Sensitivity.TRAGEDY: (
            ProtectedDimension.PHYSICAL_HARM,
            ProtectedDimension.BEREAVEMENT,
        ),
        Sensitivity.VULNERABLE_PEOPLE: (ProtectedDimension.INVOLUNTARY_VULNERABILITY,),
        Sensitivity.CHILDREN: (ProtectedDimension.MINOR, ProtectedDimension.AGE),
        Sensitivity.MEDICAL: (ProtectedDimension.MEDICAL_CONDITION,),
        Sensitivity.VIOLENCE: (
            ProtectedDimension.PHYSICAL_HARM,
            ProtectedDimension.ABUSE,
        ),
        Sensitivity.DEATH: (
            ProtectedDimension.PHYSICAL_HARM,
            ProtectedDimension.BEREAVEMENT,
        ),
        Sensitivity.DISASTER: (
            ProtectedDimension.PHYSICAL_HARM,
            ProtectedDimension.INVOLUNTARY_VULNERABILITY,
        ),
    }

    def assign(self, story):
        return self._mapping.get(story.sensitivity, ())


class RoastEligibilityRule:
    name = "RoastEligibilityRule"

    def assign(self, event, story, protected):
        if protected or story.sensitivity in SENSITIVE:
            return RoastEligibility.PROHIBITED
        extensions = event.extensions or {}
        explicit_absurdity = bool(extensions.get("explicit_absurdity", False))
        meaningful_agency = bool(extensions.get("meaningful_agency", False))
        behavior_target = bool(extensions.get("behavior_is_target", False))
        severe_harm = bool(extensions.get("severe_harm", False))
        if (
            explicit_absurdity
            and meaningful_agency
            and behavior_target
            and not severe_harm
        ):
            return RoastEligibility.BEHAVIOR_ONLY
        return RoastEligibility.INSTITUTION_ONLY


class EmpathyVoiceRule:
    name = "EmpathyVoiceRule"

    def assign(self, story):
        if story.sensitivity in SENSITIVE:
            return EmpathyMode.PROTECTIVE, SarcasmIntensity.NONE
        if story.empathy.explicit_acknowledgment_required:
            return EmpathyMode.ACKNOWLEDGE, SarcasmIntensity.SUBTLE
        return EmpathyMode.REFLECTIVE, SarcasmIntensity.CLEAR


class EmotionalTemperatureRule:
    name = "EmotionalTemperatureRule"

    def assign(self, story):
        if story.sensitivity in {
            Sensitivity.TRAGEDY,
            Sensitivity.DEATH,
            Sensitivity.DISASTER,
        }:
            return EmotionalTemperature.SAD
        mapping = {
            AudienceEmotion.FRUSTRATION: EmotionalTemperature.FRUSTRATED,
            AudienceEmotion.ANGER: EmotionalTemperature.OUTRAGED,
            AudienceEmotion.DISAPPOINTMENT: EmotionalTemperature.DISAPPOINTED,
            AudienceEmotion.FEAR: EmotionalTemperature.REFLECTIVE,
        }
        return mapping.get(story.empathy.primary_emotion, EmotionalTemperature.AMUSED)


class ExpressionRule:
    name = "ExpressionRule"

    def assign(self, story):
        if story.sensitivity in SENSITIVE:
            return None, None, "restrained"
        if story.everyday_comparison.primary:
            return (
                RomanianExpressionType.POPULAR_EXPRESSION,
                RomanianExpressionFunction.GROUND_ABSURDITY,
                "informal",
            )
        return (
            RomanianExpressionType.MODERN_SAYING,
            RomanianExpressionFunction.BUILD_COMPLICITY,
            "conversational",
        )


class CallbackRule:
    name = "CallbackRule"

    def assign(self, story):
        if story.punchline.callback_event_id:
            return CallbackType.EPISODE_CALLBACK, story.punchline.callback_event_id, 1
        return None, None, 0


class VoiceMechanicsRule:
    name = "VoiceMechanicsRule"

    @staticmethod
    def markers(story):
        families = [MarkerFamily.ATTENTION, MarkerFamily.COMPLICITY]
        if story.sensitivity in SENSITIVE:
            families = [MarkerFamily.SERIOUS_TURN, MarkerFamily.CLARIFICATION]
        return tuple(families)

    @staticmethod
    def question(story):
        if story.sensitivity in SENSITIVE:
            return RhetoricalQuestionFunction.CONSEQUENCE_BRIDGE
        if IronyMechanism.CONTRADICTION in story.irony_mechanisms:
            return RhetoricalQuestionFunction.EXPOSE_CONTRADICTION
        return RhetoricalQuestionFunction.DISBELIEF

    @staticmethod
    def curiosity(story):
        return (
            CuriosityTrigger.NONE
            if story.sensitivity in SENSITIVE
            else CuriosityTrigger.MID
        )

    @staticmethod
    def perspective(story):
        if story.everyday_comparison.primary:
            return PerspectiveShiftType.EVERYDAY
        return PerspectiveShiftType.ROMANIAN_REALITY

    @staticmethod
    def absurd_reveal(story):
        if story.sensitivity in SENSITIVE:
            return AbsurdReveal.NONE
        if CommentaryBeat.ABSURDITY_EXPLANATION in story.beats:
            return AbsurdReveal.MEDIUM
        return AbsurdReveal.SMALL

    @staticmethod
    def ending(story, final):
        if story.sensitivity in SENSITIVE:
            return (
                EndingVoice.SERIOUS_CONCLUSION
                if final
                else EndingVoice.TRANSITION_BRIDGE
            )
        if story.punchline.callback_event_id:
            return EndingVoice.CALLBACK
        return EndingVoice.PUNCHLINE if final else EndingVoice.TRANSITION_BRIDGE

    @staticmethod
    def reference(story):
        if story.everyday_comparison.primary:
            return RomanianReferenceType.EVERYDAY
        return RomanianReferenceType.BUREAUCRATIC

    @staticmethod
    def knowledge(event):
        return (
            AudienceKnowledgeLevel.NEEDS_CONTEXT
            if event.article_count == 1
            else AudienceKnowledgeLevel.LIKELY_KNOWS
        )

    @staticmethod
    def reset(story):
        return (
            SeriousnessResetFunction.ACKNOWLEDGE_HARM
            if story.sensitivity in SENSITIVE
            else SeriousnessResetFunction.RESTORE_FACTS
        )

    @staticmethod
    def language(story):
        if story.sensitivity in SENSITIVE:
            return DirectLanguageLevel.CLEAN
        return DirectLanguageLevel.EDGY
