"""Private controlled models for deterministic commentary voice execution."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.contracts.editor_output import EditorAgentOutputV1


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConversationRegister(StrEnum):
    DIRECT_COMPANION = "direct_companion"
    SHARED_DISBELIEF = "shared_disbelief"
    SHARED_FRUSTRATION = "shared_frustration"
    MOCK_CONFIDANT = "mock_confidant"
    SERIOUS_COMPANION = "serious_companion"
    CONTROLLED_OUTRAGE = "controlled_outrage"
    REFLECTIVE_COMPANION = "reflective_companion"


class OralityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarkerFamily(StrEnum):
    ATTENTION = "attention"
    DISBELIEF = "disbelief"
    CONFESSION = "confession"
    RESET = "reset"
    ESCALATION = "escalation"
    CLARIFICATION = "clarification"
    COMPLICITY = "complicity"
    SERIOUS_TURN = "serious_turn"


class VocativeMarkerFamily(StrEnum):
    BAI = "bai"
    MAI = "mai"
    MA = "ma"
    BA = "ba"
    FRATE = "frate"


class RhetoricalQuestionFunction(StrEnum):
    EXPOSE_CONTRADICTION = "expose_contradiction"
    INVITE_AUDIENCE = "invite_audience"
    CHALLENGE_PRIORITY = "challenge_priority"
    ACCOUNTABILITY = "accountability"
    ABSURDITY = "absurdity"
    DISBELIEF = "disbelief"
    REFLECTION = "reflection"
    CONSEQUENCE_BRIDGE = "consequence_bridge"


class CuriosityTrigger(StrEnum):
    NONE = "none"
    EARLY = "early"
    MID = "mid"
    LATE = "late"


class HumorIntensity(StrEnum):
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    STRONG = "strong"
    ROAST = "roast"


class HumorEscalationPattern(StrEnum):
    SINGLE = "single"
    TWO_STEP = "two_step"
    THREE_STEP = "three_step"
    DIALOGUE = "dialogue"
    CALLBACK = "callback"
    ENUMERATION = "enumeration"
    FALSE_SERIOUSNESS = "false_seriousness"


class SarcasmIntensity(StrEnum):
    NONE = "none"
    SUBTLE = "subtle"
    CLEAR = "clear"
    SHARP = "sharp"
    BRUTAL_CONTROLLED = "brutal_controlled"


class RoastEligibility(StrEnum):
    PROHIBITED = "prohibited"
    INSTITUTION_ONLY = "institution_only"
    BEHAVIOR_ONLY = "behavior_only"
    SITUATION_ONLY = "situation_only"
    PERSON_ALLOWED = "person_allowed"
    FULL_ROAST_ALLOWED = "full_roast_allowed"


class ProtectedDimension(StrEnum):
    PHYSICAL_HARM = "physical_harm"
    MEDICAL_CONDITION = "medical_condition"
    DISABILITY = "disability"
    POVERTY = "poverty"
    AGE = "age"
    MINOR = "minor"
    BEREAVEMENT = "bereavement"
    ABUSE = "abuse"
    INVOLUNTARY_VULNERABILITY = "involuntary_vulnerability"


class EmpathyMode(StrEnum):
    ACKNOWLEDGE = "acknowledge"
    CENTER_AFFECTED_PEOPLE = "center_affected_people"
    PROTECTIVE = "protective"
    REFLECTIVE = "reflective"


class SeriousnessResetFunction(StrEnum):
    RESTORE_FACTS = "restore_facts"
    ACKNOWLEDGE_HARM = "acknowledge_harm"
    LOWER_TEMPERATURE = "lower_temperature"
    PREPARE_CONSEQUENCE = "prepare_consequence"


class DirectLanguageLevel(StrEnum):
    CLEAN = "clean"
    INFORMAL = "informal"
    EDGY = "edgy"
    PROFANE_LIGHT = "profane_light"
    PROFANE_DIRECT = "profane_direct"


class RomanianExpressionType(StrEnum):
    PROVERB = "proverb"
    TRADITIONAL_SAYING = "traditional_saying"
    POPULAR_EXPRESSION = "popular_expression"
    MODERN_SAYING = "modern_saying"
    CULTURAL_REFERENCE = "cultural_reference"
    TWISTED_PROVERB = "twisted_proverb"


class RomanianExpressionFunction(StrEnum):
    GROUND_ABSURDITY = "ground_absurdity"
    BUILD_COMPLICITY = "build_complicity"
    MARK_CONTRADICTION = "mark_contradiction"
    RESET_TONE = "reset_tone"
    SUPPORT_CALLBACK = "support_callback"


class RomanianReferenceType(StrEnum):
    BUREAUCRATIC = "bureaucratic"
    CULTURAL = "cultural"
    EVERYDAY = "everyday"
    HISTORICAL = "historical"
    POP_CULTURE = "pop_culture"


class CallbackType(StrEnum):
    STORY_CALLBACK = "story_callback"
    EPISODE_CALLBACK = "episode_callback"
    SERIES_CALLBACK = "series_callback"
    RUNNING_GAG = "running_gag"


class PerspectiveShiftType(StrEnum):
    EVERYDAY = "everyday"
    BUREAUCRATIC = "bureaucratic"
    FINANCIAL = "financial"
    FAMILY = "family"
    ROMANIAN_REALITY = "Romanian_reality"
    INTERNATIONAL = "international"


class EmotionalTemperature(StrEnum):
    CALM = "calm"
    AMUSED = "amused"
    ANNOYED = "annoyed"
    DISAPPOINTED = "disappointed"
    FRUSTRATED = "frustrated"
    OUTRAGED = "outraged"
    SAD = "sad"
    REFLECTIVE = "reflective"


class AbsurdReveal(StrEnum):
    NONE = "none"
    SMALL = "small"
    MEDIUM = "medium"
    MAJOR = "major"


class EndingVoice(StrEnum):
    PUNCHLINE = "punchline"
    REFLECTION = "reflection"
    PUNCHLINE_THEN_REFLECTION = "punchline_then_reflection"
    OPEN_QUESTION = "open_question"
    CALLBACK = "callback"
    TRANSITION_BRIDGE = "transition_bridge"
    SERIOUS_CONCLUSION = "serious_conclusion"


class AudienceKnowledgeLevel(StrEnum):
    EVERYBODY_KNOWS = "everybody_knows"
    LIKELY_KNOWS = "likely_knows"
    NEEDS_CONTEXT = "needs_context"


class MechanismType(StrEnum):
    RHETORICAL_QUESTION = "rhetorical_question"
    DIALOGUE = "dialogue"
    PROVERB = "proverb"
    TWISTED_PROVERB = "twisted_proverb"
    CULTURAL_REFERENCE = "cultural_reference"
    COMPARISON = "comparison"
    CALLBACK = "callback"
    VOCATIVE = "vocative"
    PROFANITY = "profanity"
    ABSURD_REVEAL = "absurd_reveal"
    SERIOUSNESS_RESET = "seriousness_reset"


class OralityProfile(_FrozenModel):
    level: OralityLevel = OralityLevel.HIGH
    fragmentation: OralityLevel
    interruptions: OralityLevel
    connector_suppression: OralityLevel
    conversational_density: OralityLevel


class SentenceRhythmPlan(_FrozenModel):
    rhythm: str
    fragment_ratio: str
    pause_density: OralityLevel
    escalation_rhythm: str
    reset_rhythm: str


class MarkerPlan(_FrozenModel):
    families: tuple[MarkerFamily, ...]
    maximum_markers: int = Field(ge=0)


class VocativeMarkerPolicy(_FrozenModel):
    allowed_families: tuple[VocativeMarkerFamily, ...]
    prohibited_in_factual_summary: bool
    maximum_per_story: int = Field(ge=0)
    minimum_beats_between_uses: int = Field(ge=1)
    prohibit_consecutive_usage: bool


class RhetoricalQuestionPlan(_FrozenModel):
    functions: tuple[RhetoricalQuestionFunction, ...]
    maximum_count: int = Field(ge=0)


class CuriosityPlan(_FrozenModel):
    trigger: CuriosityTrigger
    reveal_required: bool


class RomanianExpressionPlan(_FrozenModel):
    expression_type: RomanianExpressionType | None
    function: RomanianExpressionFunction | None
    tone: str
    maximum_count: int = Field(ge=0, le=1)


class CallbackPlan(_FrozenModel):
    callback_type: CallbackType | None
    target_event_id: int | None = Field(default=None, gt=0)
    maximum_count: int = Field(ge=0, le=1)


class PerspectiveShiftPlan(_FrozenModel):
    primary: PerspectiveShiftType
    secondary: PerspectiveShiftType | None


class AbsurdRevealPlan(_FrozenModel):
    level: AbsurdReveal
    after_factual_anchor: bool


class MechanismBudget(_FrozenModel):
    mechanism: MechanismType
    maximum_per_story: int = Field(ge=0)
    maximum_per_episode: int = Field(ge=0)


class AntiRepetitionPlan(_FrozenModel):
    budgets: tuple[MechanismBudget, ...]
    intentional_callback_exception: bool


class StoryVoicePlan(_FrozenModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    conversation_register: ConversationRegister
    orality: OralityProfile
    sentence_rhythm: SentenceRhythmPlan
    markers: MarkerPlan
    vocatives: VocativeMarkerPolicy
    rhetorical_questions: RhetoricalQuestionPlan
    curiosity: CuriosityPlan
    humor_intensity: HumorIntensity
    humor_escalation: HumorEscalationPattern
    sarcasm_ceiling: SarcasmIntensity
    roast_eligibility: RoastEligibility
    protected_dimensions: tuple[ProtectedDimension, ...]
    empathy_mode: EmpathyMode
    seriousness_reset: SeriousnessResetFunction
    direct_language_ceiling: DirectLanguageLevel
    profanity_ceiling: DirectLanguageLevel
    romanian_expression: RomanianExpressionPlan
    romanian_reference: RomanianReferenceType
    callback: CallbackPlan
    perspective_shift: PerspectiveShiftPlan
    emotional_temperature: EmotionalTemperature
    absurd_reveal: AbsurdRevealPlan
    ending_voice: EndingVoice
    audience_knowledge: AudienceKnowledgeLevel
    audience_relationship: str = Field(pattern="^intelligent_peer$")
    prohibited_voice_modes: tuple[str, ...] = Field(min_length=1)
    safety_invariants: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def protect_sensitive_dimensions(self) -> StoryVoicePlan:
        if self.protected_dimensions and self.roast_eligibility in {
            RoastEligibility.PERSON_ALLOWED,
            RoastEligibility.FULL_ROAST_ALLOWED,
        }:
            raise ValueError("protected dimensions prohibit person-level roast")
        return self


class EpisodeExpressionBudget(_FrozenModel):
    maximum_total: int = Field(ge=0)
    maximum_twisted_proverbs: int = Field(ge=0)


class EpisodeVoicePlan(_FrozenModel):
    source_report_id: str
    flow_order: tuple[int, ...]
    stories: tuple[StoryVoicePlan, ...]
    dominant_register: ConversationRegister
    global_humor_ceiling: HumorIntensity
    profanity_ceiling: DirectLanguageLevel
    emotional_arc: tuple[EmotionalTemperature, ...]
    callback_budget: int = Field(ge=0)
    vocative_budget: int = Field(ge=0)
    expression_budget: EpisodeExpressionBudget
    anti_repetition: AntiRepetitionPlan
    ending_register: ConversationRegister
    consistency_plan: tuple[str, ...]
    audience_respect_invariants: tuple[str, ...]

    @model_validator(mode="after")
    def validate_order(self) -> EpisodeVoicePlan:
        if tuple(story.event_id for story in self.stories) != self.flow_order:
            raise ValueError("voice stories must preserve optimized flow order")
        return self


class VoiceDecision(_FrozenModel):
    rule: str
    event_id: int | None = None
    code: str
    values: tuple[str, ...] = ()


class VoiceDecisionTrace(_FrozenModel):
    input_flow_order: tuple[int, ...]
    decisions: tuple[VoiceDecision, ...]
    fallbacks: tuple[VoiceDecision, ...]
    validation_checks: tuple[str, ...]


@dataclass(frozen=True)
class VoiceBuildResult:
    output: EditorAgentOutputV1
    plan: EpisodeVoicePlan
    trace: VoiceDecisionTrace
