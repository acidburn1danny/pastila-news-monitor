"""Private controlled models for deterministic editorial blueprints."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.contracts.editor_output import EditorAgentOutputV1


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EditorialTheme(StrEnum):
    POLITICAL_ACCOUNTABILITY = "political_accountability"
    SOCIAL_CONSEQUENCE = "social_consequence"
    ECONOMIC_PRESSURE = "economic_pressure"
    EXTERNAL_AFFAIRS = "external_affairs"
    CONSPIRACY_AND_PROPAGANDA = "conspiracy_and_propaganda"
    PUBLIC_ABSURDITY = "public_absurdity"
    CIVIC_RELEVANCE = "civic_relevance"
    MIXED_PUBLIC_AFFAIRS = "mixed_public_affairs"


class EpisodeTension(StrEnum):
    INSTITUTIONAL_ACCOUNTABILITY = "institutional_accountability"
    PUBLIC_CONSEQUENCE = "public_consequence"
    ECONOMIC_PRESSURE = "economic_pressure"
    SOCIAL_DISRUPTION = "social_disruption"
    ABSURDITY_VS_SERIOUSNESS = "absurdity_vs_seriousness"
    MIXED = "mixed"


class EmotionalTrajectory(StrEnum):
    STEADY_GRAVE = "steady_grave"
    ESCALATING = "escalating"
    GRAVE_TO_RELIEF = "grave_to_relief"
    VARIED = "varied"
    REFLECTIVE_CLOSE = "reflective_close"


class ClosingEffect(StrEnum):
    ABSURDITY = "absurdity"
    CONSEQUENCE = "consequence"
    REFLECTION = "reflection"
    WARNING = "warning"
    CALLBACK = "callback"


class SegmentIntent(StrEnum):
    ESTABLISH_CONTEXT = "establish_context"
    INTRODUCE_CONFLICT = "introduce_conflict"
    EXPOSE_CONTRADICTION = "expose_contradiction"
    DEMONSTRATE_CONSEQUENCE = "demonstrate_consequence"
    BROADEN_SCOPE = "broaden_scope"
    ESCALATE = "escalate"
    HUMANIZE = "humanize"
    CONTRAST = "contrast"
    RELIEVE_TENSION = "relieve_tension"
    RETURN_TO_CORE_THEME = "return_to_core_theme"
    PREPARE_CLOSING = "prepare_closing"
    CLOSE_WITH_ABSURDITY = "close_with_absurdity"
    CLOSE_WITH_REFLECTION = "close_with_reflection"


class EditorialAngle(StrEnum):
    ACCOUNTABILITY = "accountability"
    INSTITUTIONAL_FAILURE = "institutional_failure"
    PUBLIC_COST = "public_cost"
    POLITICAL_CONTRADICTION = "political_contradiction"
    SOCIAL_IMPACT = "social_impact"
    ECONOMIC_PRESSURE = "economic_pressure"
    HYPOCRISY = "hypocrisy"
    ABSURDITY = "absurdity"
    INCOMPETENCE = "incompetence"
    ABUSE_OF_POWER = "abuse_of_power"
    HUMAN_CONSEQUENCE = "human_consequence"
    PROPAGANDA = "propaganda"
    SYSTEMIC_PATTERN = "systemic_pattern"
    CIVIC_RELEVANCE = "civic_relevance"


class NarrativeFunction(StrEnum):
    OPENER = "opener"
    FOUNDATION = "foundation"
    ESCALATION = "escalation"
    EVIDENCE = "evidence"
    CONTRAST = "contrast"
    BRIDGE = "bridge"
    RELIEF = "relief"
    CALLBACK = "callback"
    PENULTIMATE_SETUP = "penultimate_setup"
    CLOSER = "closer"


class TransitionIntent(StrEnum):
    PRESERVE_TOPIC = "preserve_topic"
    WIDEN_SCOPE = "widen_scope"
    SHARPEN_CONTRAST = "sharpen_contrast"
    RAISE_STAKES = "raise_stakes"
    RESET_ENERGY = "reset_energy"
    RELEASE_TENSION = "release_tension"
    CALLBACK_TO_PREVIOUS = "callback_to_previous"
    PREPARE_FINALE = "prepare_finale"


class SafeFactField(StrEnum):
    CANONICAL_TITLE = "canonical_title"
    CANONICAL_SUMMARY = "canonical_summary"
    PUBLICATION_BOUNDS = "publication_bounds"
    CATEGORIES = "categories"
    SOURCE_PROVENANCE = "source_provenance"


class ProhibitedFraming(StrEnum):
    UNSUPPORTED_CAUSALITY = "unsupported_causality"
    UNVERIFIED_MOTIVE = "unverified_motive"
    INVENTED_QUOTE = "invented_quote"
    EXAGGERATED_CERTAINTY = "exaggerated_certainty"
    SOURCE_CONFLATION = "source_conflation"


class AudienceQuestion(StrEnum):
    WHO_IS_AFFECTED = "who_is_affected"
    WHAT_CHANGED = "what_changed"
    WHO_IS_ACCOUNTABLE = "who_is_accountable"
    WHY_IT_MATTERS = "why_it_matters"
    WHAT_FOLLOWS = "what_follows"


class OpenerFunction(StrEnum):
    ESTABLISH_STAKES = "establish_stakes"
    AUDIENCE_RELEVANCE = "audience_relevance"
    INSTITUTIONAL_FOCUS = "institutional_focus"
    IMMEDIATE_CONTRAST = "immediate_contrast"
    MANDATORY_ANCHOR = "mandatory_anchor"


class FinalEmotionalEffect(StrEnum):
    RELIEF = "relief"
    CONCERN = "concern"
    REFLECTION = "reflection"
    URGENCY = "urgency"
    AMBIGUITY = "ambiguity"


class FinalSatiricalEffect(StrEnum):
    NONE = "none"
    IRONIC_DISTANCE = "ironic_distance"
    ABSURD_RESOLUTION = "absurd_resolution"
    INSTITUTIONAL_CRITIQUE = "institutional_critique"
    CALLBACK = "callback"


class UnresolvedQuestionRole(StrEnum):
    NONE = "none"
    CIVIC_QUESTION = "civic_question"
    ACCOUNTABILITY_QUESTION = "accountability_question"
    CONSEQUENCE_QUESTION = "consequence_question"


class BlueprintDecisionOutcome(StrEnum):
    APPLIED = "applied"
    CONFLICT = "conflict"
    FALLBACK = "fallback"


class BlueprintReason(_FrozenModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class BlueprintDecision(_FrozenModel):
    rule: str = Field(min_length=1)
    outcome: BlueprintDecisionOutcome
    reason: BlueprintReason
    event_ids: tuple[int, ...] = ()
    assigned_values: tuple[str, ...] = ()


class EvidenceReference(_FrozenModel):
    source_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published_at: str | None = None


class EvidenceDiscipline(_FrozenModel):
    safe_fact_fields: tuple[SafeFactField, ...]
    provenance: tuple[EvidenceReference, ...]
    prohibited_framing: tuple[ProhibitedFraming, ...]


class SegmentLevels(_FrozenModel):
    tension_level: int = Field(ge=1, le=5)
    energy_level: int = Field(ge=1, le=5)
    satire_level: int = Field(ge=1, le=5)
    emotional_weight: int = Field(ge=1, le=5)


class SegmentBlueprint(_FrozenModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    intent: SegmentIntent
    angles: tuple[EditorialAngle, ...] = Field(min_length=1, max_length=3)
    narrative_function: NarrativeFunction
    levels: SegmentLevels
    evidence: EvidenceDiscipline
    mandatory: bool
    recent_episode_reference: bool


class TransitionBlueprint(_FrozenModel):
    from_event_id: int = Field(gt=0)
    to_event_id: int = Field(gt=0)
    public_transition_type: str = Field(min_length=1)
    intent: TransitionIntent
    reason_code: str = Field(min_length=1)


class EpisodeThesis(_FrozenModel):
    dominant_theme: EditorialTheme
    secondary_theme: EditorialTheme | None
    episode_tension: EpisodeTension
    emotional_trajectory: EmotionalTrajectory
    satire_intensity: int = Field(ge=1, le=5)
    seriousness_balance: int = Field(ge=1, le=5)
    intended_closing_effect: ClosingEffect
    context_theme_reference: str | None


class OpeningBlueprint(_FrozenModel):
    event_id: int = Field(gt=0)
    opener_function: OpenerFunction
    primary_audience_question: AudienceQuestion
    tension_introduced: EpisodeTension
    facts_to_establish: tuple[SafeFactField, ...]
    prohibited_framing: tuple[ProhibitedFraming, ...]
    handoff_intent: TransitionIntent | None


class ClosingBlueprint(_FrozenModel):
    event_id: int = Field(gt=0)
    closing_mode: ClosingEffect
    callback_target_event_id: int | None = Field(default=None, gt=0)
    final_emotional_effect: FinalEmotionalEffect
    final_satirical_effect: FinalSatiricalEffect
    unresolved_question_role: UnresolvedQuestionRole
    land_on: ClosingEffect


class ContinuityBlueprint(_FrozenModel):
    previous_episode_reference: str | None
    recent_event_ids_present: tuple[int, ...]
    mandatory_event_ids_present: tuple[int, ...]
    excluded_event_ids_present: tuple[int, ...]
    requested_episode_size: int = Field(gt=0)


class EditorialBlueprint(_FrozenModel):
    source_report_id: str = Field(min_length=1)
    flow_order: tuple[int, ...]
    thesis: EpisodeThesis
    segments: tuple[SegmentBlueprint, ...]
    transitions: tuple[TransitionBlueprint, ...]
    opening: OpeningBlueprint | None
    closing: ClosingBlueprint | None
    continuity: ContinuityBlueprint

    @model_validator(mode="after")
    def validate_structure(self) -> EditorialBlueprint:
        segment_ids = tuple(segment.event_id for segment in self.segments)
        if segment_ids != self.flow_order:
            raise ValueError("blueprint segments must match flow order")
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("blueprint segment IDs must be unique")
        if len(self.transitions) != max(0, len(segment_ids) - 1):
            raise ValueError("every adjacency requires one transition blueprint")
        for index, transition in enumerate(self.transitions):
            if (
                transition.from_event_id != segment_ids[index]
                or transition.to_event_id != segment_ids[index + 1]
            ):
                raise ValueError("transition blueprint does not match flow adjacency")
        if segment_ids:
            if self.opening is None or self.opening.event_id != segment_ids[0]:
                raise ValueError("opening blueprint must target the first segment")
            if self.closing is None or self.closing.event_id != segment_ids[-1]:
                raise ValueError("closing blueprint must target the last segment")
        return self


class BlueprintDecisionTrace(_FrozenModel):
    input_flow_order: tuple[int, ...]
    applied_rules: tuple[BlueprintDecision, ...]
    assigned_episode_themes: tuple[BlueprintDecision, ...]
    segment_intent_decisions: tuple[BlueprintDecision, ...]
    angle_decisions: tuple[BlueprintDecision, ...]
    curve_decisions: tuple[BlueprintDecision, ...]
    transition_intent_decisions: tuple[BlueprintDecision, ...]
    opening_decision: BlueprintDecision | None
    closing_decision: BlueprintDecision | None
    evidence_decisions: tuple[BlueprintDecision, ...]
    conflicts: tuple[BlueprintDecision, ...]
    fallbacks: tuple[BlueprintDecision, ...]


@dataclass(frozen=True)
class BlueprintBuildResult:
    """Unchanged public output plus private blueprint and trace."""

    output: EditorAgentOutputV1
    blueprint: EditorialBlueprint
    trace: BlueprintDecisionTrace
