"""Private, controlled plans for Pastila Acida commentary preparation."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.contracts.editor_output import EditorAgentOutputV1
from pastila_scout.editor.blueprint_models import EvidenceReference, SafeFactField


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SatireTarget(StrEnum):
    HYPOCRISY = "hypocrisy"
    INCOMPETENCE = "incompetence"
    POPULISM = "populism"
    ARROGANCE = "arrogance"
    CONTRADICTORY_PROMISES = "contradictory_promises"
    ABSURD_BUREAUCRACY = "absurd_bureaucracy"
    INSTITUTIONAL_ABSURDITY = "institutional_absurdity"
    MISPLACED_PRIORITIES = "misplaced_priorities"
    PUBLIC_POSTURING = "public_posturing"
    ABUSE_OF_POWER = "abuse_of_power"
    PROPAGANDA = "propaganda"
    PERFORMATIVE_POLITICS = "performative_politics"
    SYSTEMIC_FAILURE = "systemic_failure"
    AVOIDABLE_CHAOS = "avoidable_chaos"


class ProtectedTarget(StrEnum):
    VICTIMS = "victims"
    VULNERABLE_PEOPLE = "vulnerable_people"
    CHILDREN = "children"
    PATIENTS = "patients"
    BEREAVED_PEOPLE = "bereaved_people"
    ORDINARY_PEOPLE_AFFECTED = "ordinary_people_affected"
    UNINVOLVED_FAMILY_MEMBERS = "uninvolved_family_members"


class Sensitivity(StrEnum):
    ORDINARY = "ordinary"
    ELEVATED = "elevated"
    TRAGEDY = "tragedy"
    VULNERABLE_PEOPLE = "vulnerable_people"
    CHILDREN = "children"
    MEDICAL = "medical"
    VIOLENCE = "violence"
    DEATH = "death"
    DISASTER = "disaster"


class IronyMechanism(StrEnum):
    CONTRADICTION = "contradiction"
    REVERSAL = "reversal"
    FALSE_ADMIRATION = "false_admiration"
    RHETORICAL_QUESTION = "rhetorical_question"
    UNDERSTATEMENT = "understatement"
    ESCALATION = "escalation"
    LITERALIZATION = "literalization"
    EVERYDAY_ANALOGY = "everyday_analogy"
    ABSURD_ENUMERATION = "absurd_enumeration"
    CALLBACK = "callback"
    DEADPAN = "deadpan"
    PROMISE_VS_REALITY = "promise_vs_reality"
    PRIORITY_INVERSION = "priority_inversion"


class AudienceStrategy(StrEnum):
    SHARED_DISBELIEF = "shared_disbelief"
    SHARED_FRUSTRATION = "shared_frustration"
    COMPLICITY = "complicity"
    RHETORICAL_INVITATION = "rhetorical_invitation"
    COMMON_EXPERIENCE = "common_experience"
    COLLECTIVE_QUESTION = "collective_question"
    RECOGNITION_OF_EXHAUSTION = "recognition_of_exhaustion"
    RECOGNITION_OF_INJUSTICE = "recognition_of_injustice"


class Takeaway(StrEnum):
    INSTITUTIONAL_CONSEQUENCE = "institutional_consequence"
    SOCIAL_CONSEQUENCE = "social_consequence"
    ECONOMIC_CONSEQUENCE = "economic_consequence"
    CIVIC_CONSEQUENCE = "civic_consequence"
    HUMAN_CONSEQUENCE = "human_consequence"
    DEMOCRATIC_CONSEQUENCE = "democratic_consequence"
    CULTURAL_PATTERN = "cultural_pattern"
    SYSTEMIC_PATTERN = "systemic_pattern"
    ROMANIA_SPECIFIC_PATTERN = "Romania_specific_pattern"
    DISCOURSE_REALITY = "contradiction_between_discourse_and_reality"


class ComparisonDomain(StrEnum):
    APARTMENT_ASSOCIATION = "apartment_association"
    GOVERNMENT_COUNTER = "government_counter"
    CFR = "CFR"
    ANAF = "ANAF"
    SCHOOL = "school"
    FOOTBALL = "football"
    GAMBLING = "gambling"
    NEIGHBORHOOD_WEDDING = "neighborhood_wedding"
    NEIGHBORHOOD_LIFE = "neighborhood_life"
    TRAFFIC = "traffic"
    SUPERMARKET = "supermarket"
    WORKPLACE = "workplace"
    FAMILY = "family"
    PUBLIC_TRANSPORT = "public_transport"
    QUEUE = "queue"
    LOCAL_BUREAUCRACY = "local_bureaucracy"
    HOME_REPAIRS = "home_repairs"


class AudienceEmotion(StrEnum):
    FRUSTRATION = "frustration"
    DISAPPOINTMENT = "disappointment"
    HELPLESSNESS = "helplessness"
    EXHAUSTION = "exhaustion"
    INJUSTICE = "injustice"
    ANGER = "anger"
    FEAR = "fear"
    DISBELIEF = "disbelief"
    RESIGNATION = "resignation"


class HumorSensitivity(StrEnum):
    STANDARD = "standard"
    CAREFUL = "careful"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"


class CommentaryBeat(StrEnum):
    FACTUAL_ANCHOR = "factual_anchor"
    IRONIC_OBSERVATION = "ironic_observation"
    ABSURDITY_EXPLANATION = "absurdity_explanation"
    AUDIENCE_QUESTION = "audience_question"
    WHY_IT_MATTERS = "why_it_matters"
    SARCASTIC_TURN = "sarcastic_turn"
    EVERYDAY_COMPARISON = "everyday_comparison"
    EMPATHY_ACKNOWLEDGMENT = "empathy_acknowledgment"
    ESCALATION = "escalation"
    CALLBACK = "callback"
    PUNCHLINE_SETUP = "punchline_setup"
    PUNCHLINE = "punchline"
    TRANSITION_SETUP = "transition_setup"


class PunchlineFunction(StrEnum):
    CLOSE_CONTRADICTION = "close_contradiction"
    SUMMARIZE_ABSURDITY = "summarize_absurdity"
    REVERSE_PUBLIC_CLAIM = "reverse_public_claim"
    EXPOSE_PRIORITY_FAILURE = "expose_priority_failure"
    CONNECT_TO_DAILY_LIFE = "connect_to_daily_life"
    CALLBACK = "callback"
    TRANSITION_BRIDGE = "transition_bridge"
    LEAVE_MEMORABLE_QUESTION = "leave_memorable_question"
    CONTROLLED_UNDERSTATEMENT = "controlled_understatement"


class ProhibitedJokeDirection(StrEnum):
    TARGET_VICTIMS = "target_victims"
    MINIMIZE_HARM = "minimize_harm"
    BLAME_AFFECTED = "blame_affected"
    SPECULATE_MOTIVE = "speculate_motive"
    INVENT_QUOTE = "invent_quote"
    GRAPHIC_DETAIL = "graphic_detail"
    MOCK_IDENTITY = "mock_identity"


class FactualSummaryPlan(_FrozenModel):
    mandatory_factual_points: tuple[SafeFactField, ...]
    principal_actors: tuple[str, ...]
    principal_actors_available: bool
    central_event_id: int = Field(gt=0)
    central_event_field: SafeFactField
    public_consequence: Takeaway
    relevance: Takeaway
    evidence_references: tuple[EvidenceReference, ...] = Field(min_length=1)
    prohibited_unsupported_claims: tuple[str, ...] = Field(min_length=1)
    target_sentence_count: int = Field(ge=1, le=2)


class WhyItMattersPlan(_FrozenModel):
    primary: Takeaway
    secondary: tuple[Takeaway, ...] = ()


class EverydayComparisonPlan(_FrozenModel):
    primary: ComparisonDomain | None
    secondary: ComparisonDomain | None
    relationship: str = Field(min_length=1)
    permitted: bool


class EmpathyPlan(_FrozenModel):
    affected_people: tuple[ProtectedTarget, ...]
    primary_emotion: AudienceEmotion
    secondary_emotion: AudienceEmotion | None
    explicit_acknowledgment_required: bool
    humor_sensitivity: HumorSensitivity


class PunchlinePlan(_FrozenModel):
    function: PunchlineFunction
    target: SatireTarget
    core_contradiction: str = Field(min_length=1)
    callback_event_id: int | None = Field(default=None, gt=0)
    intended_emotional_effect: AudienceEmotion
    intended_memory_effect: str = Field(min_length=1)
    prohibited_directions: tuple[ProhibitedJokeDirection, ...] = Field(min_length=1)


class CommentaryTransitionPlan(_FrozenModel):
    next_event_id: int = Field(gt=0)
    expected_transition_type: str = Field(min_length=1)
    current_anchor: SafeFactField
    next_anchor: SafeFactField
    transition_intent: str = Field(min_length=1)
    callback_event_id: int | None = Field(default=None, gt=0)
    prohibited_repetition: tuple[str, ...] = Field(min_length=1)


class StoryCommentaryBlueprint(_FrozenModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    sensitivity: Sensitivity
    factual_summary: FactualSummaryPlan
    satire_targets: tuple[SatireTarget, ...] = Field(min_length=1)
    protected_targets: tuple[ProtectedTarget, ...]
    irony_mechanisms: tuple[IronyMechanism, ...] = Field(min_length=1)
    audience_strategy: AudienceStrategy
    audience_voice: str = Field(pattern="^audience_conversation$")
    why_it_matters: WhyItMattersPlan
    everyday_comparison: EverydayComparisonPlan
    empathy: EmpathyPlan
    beats: tuple[CommentaryBeat, ...] = Field(min_length=1)
    punchline: PunchlinePlan
    transition: CommentaryTransitionPlan | None

    @model_validator(mode="after")
    def validate_targets(self) -> StoryCommentaryBlueprint:
        if {item.value for item in self.satire_targets} & {
            item.value for item in self.protected_targets
        }:
            raise ValueError("satire and protected targets must not overlap")
        return self


class RepeatedComparisonWarning(_FrozenModel):
    domain: ComparisonDomain
    event_ids: tuple[int, ...] = Field(min_length=2)


class EpisodeCommentaryBlueprint(_FrozenModel):
    source_report_id: str = Field(min_length=1)
    flow_order: tuple[int, ...]
    stories: tuple[StoryCommentaryBlueprint, ...]
    dominant_satire_target: SatireTarget
    dominant_audience_emotion: AudienceEmotion
    seriousness_humor_balance: str = Field(min_length=1)
    repeated_comparison_warnings: tuple[RepeatedComparisonWarning, ...]
    callback_opportunities: tuple[tuple[int, int], ...]
    opener_commentary_function: str = Field(min_length=1)
    closer_commentary_function: str = Field(min_length=1)
    prohibited_framing: tuple[str, ...] = Field(min_length=1)


class CommentaryDecision(_FrozenModel):
    rule: str
    event_id: int | None = None
    code: str
    values: tuple[str, ...] = ()


class CommentaryBlueprintTrace(_FrozenModel):
    input_flow_order: tuple[int, ...]
    decisions: tuple[CommentaryDecision, ...]
    fallbacks: tuple[CommentaryDecision, ...]
    validation_checks: tuple[str, ...]


@dataclass(frozen=True)
class CommentaryBuildResult:
    output: EditorAgentOutputV1
    blueprint: EpisodeCommentaryBlueprint
    trace: CommentaryBlueprintTrace
