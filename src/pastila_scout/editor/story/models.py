"""Immutable evidence-linked Story Architecture contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.editor.audience.models import ContextLoad
from pastila_scout.editor.decision.models import (
    DecisionConfidence,
    FactImportance,
    RiskSeverity,
)
from pastila_scout.editor.voice.models import (
    HumorDensity,
    MechanismType,
    SarcasmIntensity,
    SensitiveSubjectType,
    TonalSeriousness,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StoryUnitType(StrEnum):
    OPENING_FACT = "opening_fact"
    OPENING_CONSEQUENCE = "opening_consequence"
    OPENING_CONTRADICTION = "opening_contradiction"
    ORIENTATION = "orientation"
    PRIMARY_FACT = "primary_fact"
    SUPPORTING_FACT = "supporting_fact"
    ATTRIBUTION = "attribution"
    ALLEGATION = "allegation"
    RESPONSE = "response"
    DISPUTE = "dispute"
    CHRONOLOGY = "chronology"
    CONTEXT = "context"
    INSTITUTIONAL_CONTEXT = "institutional_context"
    HUMAN_CONSEQUENCE = "human_consequence"
    PUBLIC_CONSEQUENCE = "public_consequence"
    STATISTIC = "statistic"
    QUOTE = "quote"
    CONTRADICTION = "contradiction"
    ESCALATION = "escalation"
    TONAL_PAUSE = "tonal_pause"
    SATIRE_SETUP = "satire_setup"
    SATIRE_BEAT = "satire_beat"
    REFLECTIVE_BEAT = "reflective_beat"
    PAYOFF = "payoff"
    UNRESOLVED_QUESTION = "unresolved_question"
    CLOSING = "closing"


class NarrativeFunction(StrEnum):
    ESTABLISH_RELEVANCE = "establish_relevance"
    ORIENT = "orient"
    ESTABLISH_EVENT = "establish_event"
    ESTABLISH_ACTOR = "establish_actor"
    PRESERVE_ATTRIBUTION = "preserve_attribution"
    CLARIFY_CHRONOLOGY = "clarify_chronology"
    EXPLAIN_CONTEXT = "explain_context"
    ESTABLISH_CONSEQUENCE = "establish_consequence"
    HUMANIZE = "humanize"
    ESTABLISH_UNCERTAINTY = "establish_uncertainty"
    PRESENT_RESPONSE = "present_response"
    PRESENT_DISPUTE = "present_dispute"
    EXPOSE_CONTRADICTION = "expose_contradiction"
    DEEPEN_CONTRADICTION = "deepen_contradiction"
    ENABLE_SATIRE = "enable_satire"
    DELIVER_SATIRE = "deliver_satire"
    REGULATE_TONE = "regulate_tone"
    RELIEVE_TENSION = "relieve_tension"
    RESTORE_SERIOUSNESS = "restore_seriousness"
    ESCALATE = "escalate"
    SYNTHESIZE = "synthesize"
    DELIVER_PAYOFF = "deliver_payoff"
    INVITE_REFLECTION = "invite_reflection"
    PRESERVE_OPEN_QUESTION = "preserve_open_question"
    CLOSE_STORY = "close_story"


class NarrativeStage(StrEnum):
    OPENING = "opening"
    ORIENTATION = "orientation"
    FACTUAL_SETUP = "factual_setup"
    CONTEXT = "context"
    CONSEQUENCE = "consequence"
    DEVELOPMENT = "development"
    CONTRADICTION = "contradiction"
    SATIRICAL_DEVELOPMENT = "satirical_development"
    ESCALATION = "escalation"
    PAYOFF = "payoff"
    CLOSURE = "closure"


STAGE_RANK = {stage: rank for rank, stage in enumerate(NarrativeStage, start=1)}


class OpeningStrategy(StrEnum):
    EVENT_FIRST = "event_first"
    CONSEQUENCE_FIRST = "consequence_first"
    CONTRADICTION_FIRST = "contradiction_first"
    VERIFIED_QUOTE_FIRST = "verified_quote_first"
    CONCRETE_DETAIL_FIRST = "concrete_detail_first"
    CHRONOLOGY_BREAK_FIRST = "chronology_break_first"
    QUESTION_FIRST = "question_first"
    RESTRAINED_GRAVITY_FIRST = "restrained_gravity_first"


class ConsequenceType(StrEnum):
    HUMAN = "human"
    PUBLIC = "public"
    FINANCIAL = "financial"
    INSTITUTIONAL = "institutional"
    DEMOCRATIC = "democratic"
    LEGAL = "legal"
    SOCIAL = "social"
    SYMBOLIC = "symbolic"
    OPERATIONAL = "operational"
    REPUTATIONAL = "reputational"


class PayoffType(StrEnum):
    FACTUAL_REVELATION = "factual_revelation"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    SATIRICAL_PAYOFF = "satirical_payoff"
    CALLBACK_PAYOFF = "callback_payoff"
    CONSEQUENCE_PAYOFF = "consequence_payoff"
    EMOTIONAL_RECOGNITION = "emotional_recognition"
    SYSTEMIC_RECOGNITION = "systemic_recognition"
    REFLECTIVE_OPEN_QUESTION = "reflective_open_question"
    RESTRAINED_CLOSE = "restrained_close"


class TransitionRelationshipType(StrEnum):
    CHRONOLOGICAL = "chronological"
    CAUSAL = "causal"
    EVIDENTIARY = "evidentiary"
    CONTRASTIVE = "contrastive"
    CONSEQUENTIAL = "consequential"
    CONTEXTUAL = "contextual"
    CLAIM_TO_RESPONSE = "claim_to_response"
    CLAIM_TO_EVIDENCE = "claim_to_evidence"
    INDIVIDUAL_TO_SYSTEMIC = "individual_to_systemic"
    SERIOUS_TO_SATIRICAL = "serious_to_satirical"
    SATIRICAL_TO_SERIOUS = "satirical_to_serious"
    SETUP_TO_PAYOFF = "setup_to_payoff"
    QUESTION_TO_RESOLUTION = "question_to_resolution"
    OPEN_QUESTION_TO_CLOSE = "open_question_to_close"


class StoryArchitectureRiskType(StrEnum):
    DELAYED_CORE = "delayed_editorial_core"
    WEAK_OPENING = "weak_opening_relevance"
    UNSUPPORTED_OPENING = "unsupported_opening"
    CONTEXT_FRONT_LOADING = "context_front_loading"
    FRAGMENTED_CONTEXT = "fragmented_context"
    CHRONOLOGY_DISTORTION = "chronology_distortion"
    CAUSAL_DISTORTION = "causal_distortion"
    BURIED_CONSEQUENCE = "buried_consequence"
    COMPETING_SPINES = "competing_narrative_spines"
    UNSUPPORTED_ESCALATION = "unsupported_escalation"
    SATIRE_BEFORE_SETUP = "satire_before_setup"
    SATIRE_DETACHED = "satire_detached_from_spine"
    MECHANISM_REPETITION = "mechanism_repetition"
    EXCESSIVE_SATIRE = "excessive_satire_density"
    TONAL_WHIPLASH = "tonal_whiplash"
    VICTIM_EXPOSURE = "victim_exposure"
    WEAK_TRANSITION = "weak_transition"
    UNRESOLVED_REFERENT = "unresolved_referent_dependency"
    PAYOFF_WITHOUT_SETUP = "payoff_without_setup"
    CLOSING_NEW_STORY = "closing_introduces_new_story"
    REPEATED_CONCLUSION = "repeated_conclusion"
    MORALIZING_CLOSE = "moralizing_close"
    UNCLEAR_TAKEAWAY = "unclear_audience_takeaway"
    PROFILE_CONFLICT = "profile_architecture_conflict"
    AUDIENCE_CONFLICT = "audience_assessment_conflict"
    DECISION_CONFLICT = "decision_plan_conflict"
    VOICE_CONFLICT = "voice_boundary_conflict"


class StoryArchitectureReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class StoryArchitecturePrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class StoryPattern(FrozenModel):
    pattern_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str
    description: str
    appropriate_conditions: tuple[str, ...]
    prohibited_conditions: tuple[str, ...]
    required_unit_types: tuple[StoryUnitType, ...]
    optional_unit_types: tuple[StoryUnitType, ...]
    required_narrative_functions: tuple[NarrativeFunction, ...]
    default_stage_sequence: tuple[NarrativeStage, ...]
    tonal_constraints: tuple[str, ...]
    audience_constraints: tuple[str, ...]
    factual_prerequisites: tuple[str, ...]
    satirical_constraints: tuple[str, ...]
    closure_expectations: tuple[str, ...]


class StoryPatternSelection(FrozenModel):
    selection_id: str
    selected_pattern_id: str
    decision_plan_id: str
    audience_assessment_id: str
    selection_rationale: str
    supporting_core_element_ids: tuple[str, ...]
    supporting_decision_ids: tuple[str, ...]
    audience_reasons: tuple[str, ...]
    tonal_reasons: tuple[str, ...]
    rejected_pattern_ids: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    confidence: DecisionConfidence
    requires_editor_in_chief_review: bool = False


class StoryUnit(FrozenModel):
    unit_id: str
    stage: NarrativeStage
    rank: int = Field(gt=0)
    source_material_ids: tuple[str, ...]
    editorial_decision_ids: tuple[str, ...]
    editorial_core_element_ids: tuple[str, ...]
    satirical_opportunity_ids: tuple[str, ...] = ()
    unit_type: StoryUnitType
    primary_function: NarrativeFunction
    secondary_functions: tuple[NarrativeFunction, ...] = ()
    factual_status_summary: str
    importance: FactImportance
    sensitivity: SensitiveSubjectType | None = None
    required_context_unit_ids: tuple[str, ...] = ()
    prerequisite_unit_ids: tuple[str, ...] = ()
    prohibited_predecessor_unit_ids: tuple[str, ...] = ()
    prohibited_successor_unit_ids: tuple[str, ...] = ()
    can_be_compressed: bool
    can_be_combined: bool
    can_be_removed: bool
    requires_verbatim_evidence: bool
    requires_attribution: bool
    requires_tonal_restraint: bool
    requires_editor_in_chief_review: bool
    notes: tuple[str, ...] = ()


class NarrativeSpine(FrozenModel):
    spine_id: str
    editorial_core_element_ids: tuple[str, ...]
    ordered_unit_ids: tuple[str, ...] = Field(min_length=1)
    central_event: str
    central_relevance: str
    central_contradiction_or_tension: str
    consequence_focus: str
    intended_progression: tuple[NarrativeFunction, ...]
    excluded_competing_angles: tuple[str, ...]
    factual_boundaries: tuple[str, ...]
    confidence: DecisionConfidence


class SecondaryAngle(FrozenModel):
    angle_id: str
    supporting_core_element_ids: tuple[str, ...]
    supporting_unit_ids: tuple[str, ...]
    editorial_value: str
    placement_limit: NarrativeStage
    may_be_removed: bool
    risk_of_competing_with_primary_spine: bool
    requires_editor_in_chief_review: bool


class StoryOpeningPlan(FrozenModel):
    strategy: OpeningStrategy
    supported_unit_ids: tuple[str, ...] = Field(min_length=1)
    reason_for_selection: str
    immediate_audience_need: str
    required_context_after_opening: tuple[str, ...]
    risks: tuple[str, ...]
    tonal_limit: TonalSeriousness
    prohibited_opening_interpretations: tuple[str, ...]
    requires_editor_in_chief_review: bool


class ContextPlacementPlan(FrozenModel):
    placement_id: str
    context_unit_ids: tuple[str, ...]
    trigger_unit_id: str
    placement_stage: NarrativeStage
    why_context_is_needed: str
    maximum_context_load: ContextLoad
    compression_required: bool
    can_be_delayed: bool
    can_be_removed: bool
    comprehension_dependency: str
    audience_fatigue_risk: str | None
    review_conditions: tuple[str, ...]


class ConsequencePlan(FrozenModel):
    consequence_id: str
    consequence_type: ConsequenceType
    supporting_material_ids: tuple[str, ...]
    supporting_core_element_ids: tuple[str, ...]
    placement_stage: NarrativeStage
    relevance_function: str
    emotional_significance: str
    factual_boundary: str
    sensitivity: SensitiveSubjectType | None
    may_lead_story: bool
    requires_context_before_use: bool
    requires_editor_in_chief_review: bool
    turns_human_consequence_into_spectacle: bool = False


class SatirePlacementPlan(FrozenModel):
    placement_id: str
    satirical_opportunity_ids: tuple[str, ...]
    prerequisite_unit_ids: tuple[str, ...]
    target_unit_ids: tuple[str, ...]
    placement_stage: NarrativeStage
    editorial_function: str
    allowed_mechanisms: tuple[MechanismType, ...]
    humor_density: HumorDensity
    sarcasm_intensity: SarcasmIntensity
    tonal_seriousness: TonalSeriousness
    protected_space_before: bool
    protected_space_after: bool
    risks: tuple[str, ...]
    requires_editor_in_chief_review: bool


class StoryPayoffPlan(FrozenModel):
    payoff_id: str
    payoff_type: PayoffType
    supporting_unit_ids: tuple[str, ...]
    setup_unit_ids: tuple[str, ...] = Field(min_length=1)
    editorial_function: str
    audience_takeaway: str
    factual_boundary: str
    tonal_limit: TonalSeriousness
    unresolved_elements: tuple[str, ...]
    closure_dependency: str
    requires_editor_in_chief_review: bool
    introduces_unsupported_facts: bool = False
    explains_joke: bool = False


class AudienceTakeaway(FrozenModel):
    takeaway_id: str
    primary_recognition: str
    supporting_core_element_ids: tuple[str, ...]
    supporting_unit_ids: tuple[str, ...]
    factual_basis: tuple[str, ...]
    emotional_register: str
    interpretive_limit: str
    prohibited_overstatement: str
    confidence: DecisionConfidence
    commands_political_opinion: bool = False
    guarantees_emotion: bool = False
    erases_uncertainty: bool = False


class StoryTransition(FrozenModel):
    transition_id: str
    from_unit_id: str
    to_unit_id: str
    relationship_type: TransitionRelationshipType
    transition_function: str
    required_information_state: tuple[str, ...]
    tonal_shift: str
    risk_if_missing: str
    requires_editor_in_chief_review: bool
    has_causal_evidence: bool = False
    distorts_chronology: bool = False


class StoryArchitectureRisk(FrozenModel):
    risk_id: str
    risk_type: StoryArchitectureRiskType
    severity: RiskSeverity
    affected_unit_ids: tuple[str, ...]
    affected_transition_ids: tuple[str, ...]
    explanation: str
    consequence: str
    mitigation: str
    blocking_status: bool
    requires_editor_in_chief_review: bool


class StoryProfileGuidance(FrozenModel):
    guidance_id: str
    source_finding_ids: tuple[str, ...]
    evidence_episode_ids: tuple[str, ...]
    established: bool
    active: bool
    affected_preferences: tuple[str, ...]
    proposed_tuning: tuple[str, ...]
    fixed_boundary_compatible: bool
    contradictory_guidance_ids: tuple[str, ...] = ()
    removes_indispensable_facts: bool = False
    distorts_chronology_or_causality: bool = False
    overrides_voice_safeguards: bool = False
    overrides_audience_safeguards: bool = False


class StoryArchitecture(FrozenModel):
    architecture_id: str
    version: str
    title: str
    project: str
    jurisdiction: str
    primary_medium: str
    purpose: str
    principles: tuple[StoryArchitecturePrinciple, ...]
    patterns: tuple[StoryPattern, ...]
    stage_order: tuple[NarrativeStage, ...]
    supported_unit_types: tuple[StoryUnitType, ...]
    supported_functions: tuple[NarrativeFunction, ...]
    opening_strategies: tuple[OpeningStrategy, ...]
    transition_relationships: tuple[TransitionRelationshipType, ...]
    consequence_types: tuple[ConsequenceType, ...]
    payoff_types: tuple[PayoffType, ...]
    fixed_boundaries: tuple[str, ...]
    emerging_guidance_may_mutate_architecture: bool = False
    contains_generation_procedures: bool = False


class StoryArchitecturePlan(FrozenModel):
    artifact_kind: str = "story_architecture_plan"
    architecture_id: str
    version: str
    persona_id: str
    persona_version: str
    philosophy_id: str
    philosophy_version: str
    voice_id: str
    voice_version: str
    audience_id: str
    audience_version: str
    decision_plan_id: str
    audience_assessment_id: str
    source_material_fingerprint: str
    decision_plan_fingerprint: str
    audience_assessment_fingerprint: str
    selected_pattern: StoryPatternSelection
    primary_narrative_spine: NarrativeSpine
    secondary_angles: tuple[SecondaryAngle, ...]
    opening_plan: StoryOpeningPlan
    story_units: tuple[StoryUnit, ...]
    transitions: tuple[StoryTransition, ...]
    context_placements: tuple[ContextPlacementPlan, ...]
    consequence_plans: tuple[ConsequencePlan, ...]
    satire_placements: tuple[SatirePlacementPlan, ...]
    payoff_plan: StoryPayoffPlan
    audience_takeaway: AudienceTakeaway
    architecture_risks: tuple[StoryArchitectureRisk, ...]
    profile_guidance: tuple[StoryProfileGuidance, ...] = ()
    unresolved_dependencies: tuple[str, ...]
    blocking_issues: tuple[str, ...]
    advisory_issues: tuple[str, ...]
    requires_editor_in_chief_review: bool
    readiness: StoryArchitectureReadiness
    summary: str
    primary_spine_count: int = 1
    primary_core_represented: bool = True
    changes_factual_status: bool = False
    changes_editorial_decisions: bool = False
    changes_audience_assessment: bool = False
    creates_satirical_opportunities: bool = False
    contains_generated_prose: bool = False
    contains_generated_hook: bool = False
    contains_generated_transition: bool = False
    contains_generated_joke: bool = False
    contains_generated_punchline: bool = False
