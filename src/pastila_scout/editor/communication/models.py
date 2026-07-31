"""Immutable language-neutral spoken communication policy contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    """Strict immutable base for public communication contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CommunicationRiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CommunicationRiskType(StrEnum):
    LISTENER_OVERLOAD = "listener_overload"
    MEMORY_OVERLOAD = "memory_overload"
    ATTENTION_COLLAPSE = "attention_collapse"
    ORIENTATION_LOSS = "orientation_loss"
    REFERENCE_AMBIGUITY = "reference_ambiguity"
    CALLBACK_OVERLOAD = "callback_overload"
    TRANSITION_OVERLOAD = "transition_overload"
    RHYTHM_MONOTONY = "rhythm_monotony"
    PAUSE_STARVATION = "pause_starvation"
    PAUSE_EXCESS = "pause_excess"
    EMOTION_INSTABILITY = "emotion_instability"
    COMMUNICATION_FRAGMENTATION = "communication_fragmentation"
    LATE_CLARIFICATION = "late_clarification"
    PREMATURE_COMPLEXITY = "premature_complexity"
    TELEPROMPTER_OVERLOAD = "teleprompter_overload"


class CommunicationReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class CommunicationPrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class WorkingMemoryModel(FrozenModel):
    concept_capacity: int = Field(gt=0)
    entity_capacity: int = Field(gt=0)
    reference_capacity: int = Field(gt=0)
    context_capacity: int = Field(gt=0)
    number_capacity: int = Field(gt=0)
    carry_over_capacity: int = Field(gt=0)
    overload_thresholds: tuple[str, ...] = Field(min_length=1)
    recovery_strategy: tuple[str, ...] = Field(min_length=1)
    claims_neuroscientific_precision: bool = False


class CommunicationFlowModel(FrozenModel):
    orientation_flow: tuple[str, ...] = Field(min_length=1)
    fact_flow: tuple[str, ...] = Field(min_length=1)
    context_flow: tuple[str, ...] = Field(min_length=1)
    consequence_flow: tuple[str, ...] = Field(min_length=1)
    emotion_flow: tuple[str, ...] = Field(min_length=1)
    reflection_flow: tuple[str, ...] = Field(min_length=1)
    satire_flow: tuple[str, ...] = Field(min_length=1)
    payoff_flow: tuple[str, ...] = Field(min_length=1)
    closure_flow: tuple[str, ...] = Field(min_length=1)


class RhythmModel(FrozenModel):
    information_rhythm: str
    attention_rhythm: str
    sentence_rhythm: str
    breathing_rhythm: str
    contrast_rhythm: str
    reflection_rhythm: str
    callback_rhythm: str
    payoff_rhythm: str
    closing_rhythm: str
    serves_comprehension: bool = True


class PauseModel(FrozenModel):
    micro_pause: str
    thinking_pause: str
    contrast_pause: str
    emotion_pause: str
    callback_pause: str
    gravity_pause: str
    closure_pause: str
    defines_punctuation: bool = False


class AttentionModel(FrozenModel):
    attention_gain: str
    attention_preservation: str
    attention_recovery: str
    attention_fatigue: str
    attention_reset: str
    attention_overload: str
    predicts_listener_behavior: bool = False


class OrientationModel(FrozenModel):
    topic_orientation: str
    speaker_orientation: str
    timeline_orientation: str
    entity_orientation: str
    context_orientation: str
    reasoning_orientation: str


class ReferenceContinuityModel(FrozenModel):
    reference_introduction: str
    reference_continuation: str
    reference_retirement: str
    reference_refresh: str
    ambiguity_prevention: str
    listener_recall: str


class CommunicationContinuityModel(FrozenModel):
    topic_continuity: str
    reasoning_continuity: str
    context_continuity: str
    emotion_continuity: str
    satirical_continuity: str
    closing_continuity: str


class CommunicationTransitionModel(FrozenModel):
    fact: str
    context: str
    contrast: str
    cause: str
    effect: str
    chronology: str
    reflection: str
    satire: str
    callback: str
    payoff: str
    contains_transition_wording: bool = False


class PayoffTimingModel(FrozenModel):
    minimum_setup_units: int = Field(gt=0)
    maximum_setup_units: int = Field(gt=0)
    recognition_dependency: str
    reflection_spacing: str
    callback_spacing: str
    premature_payoff_prevention: str


class EmotionTimingModel(FrozenModel):
    curiosity: str
    surprise: str
    concern: str
    frustration: str
    humor: str
    gravity: str
    reflection: str
    relief: str
    contains_emotional_wording: bool = False


class TeleprompterCognitionModel(FrozenModel):
    reading_continuity: str
    visual_continuity: str
    breathing_continuity: str
    working_memory_continuity: str
    scan_continuity: str
    contains_formatting_rules: bool = False


class CommunicationRisk(FrozenModel):
    risk_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    risk_type: CommunicationRiskType
    severity: CommunicationRiskSeverity
    affected_models: tuple[str, ...] = Field(min_length=1)
    editorial_explanation: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    blocking: bool
    requires_editor_in_chief_review: bool


class CommunicationProfileGuidance(FrozenModel):
    guidance_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    source_finding_ids: tuple[str, ...] = Field(min_length=1)
    evidence_episode_ids: tuple[str, ...] = Field(min_length=1)
    established: bool
    active: bool
    tuning_dimensions: tuple[str, ...] = Field(min_length=1)
    proposed_tuning: tuple[str, ...] = Field(min_length=1)
    fixed_boundary_compatible: bool
    changes_story_architecture: bool = False
    changes_factual_content: bool = False
    overrides_voice: bool = False
    overrides_audience: bool = False
    overrides_persona_or_philosophy: bool = False
    implements_learning: bool = False


class SpokenCommunicationEngine(FrozenModel):
    communication_engine_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str
    title: str
    project: str
    language: str
    medium: str
    purpose: str
    core_assumptions: tuple[str, ...] = Field(min_length=1)
    principles: tuple[CommunicationPrinciple, ...] = Field(min_length=1)
    working_memory: WorkingMemoryModel
    communication_flow: CommunicationFlowModel
    rhythm: RhythmModel
    pauses: PauseModel
    attention: AttentionModel
    orientation: OrientationModel
    references: ReferenceContinuityModel
    continuity: CommunicationContinuityModel
    transitions: CommunicationTransitionModel
    payoff_timing: PayoffTimingModel
    emotion_timing: EmotionTimingModel
    teleprompter_cognition: TeleprompterCognitionModel
    supported_profile_dimensions: tuple[str, ...] = Field(min_length=1)
    editor_in_chief_authority: str
    fixed_boundaries: tuple[str, ...] = Field(min_length=1)
    contains_generated_language: bool = False
    contains_language_specific_rules: bool = False
    contains_generation_procedures: bool = False
    implements_learning: bool = False


class CommunicationAssessment(FrozenModel):
    artifact_kind: str = "spoken_communication_assessment"
    assessment_id: str = Field(min_length=1)
    version: str
    communication_engine_id: str
    communication_engine_version: str
    story_architecture_id: str
    story_architecture_version: str
    story_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    risks: tuple[CommunicationRisk, ...] = ()
    profile_guidance: tuple[CommunicationProfileGuidance, ...] = ()
    blocking_issues: tuple[str, ...] = ()
    advisory_issues: tuple[str, ...] = ()
    requires_editor_in_chief_review: bool
    readiness: CommunicationReadiness
    summary: str = Field(min_length=1)
    modifies_story_architecture: bool = False
    modifies_upstream_contracts: bool = False
    contains_generated_language: bool = False
    contains_generated_dialogue: bool = False
    contains_generated_transition: bool = False
    contains_generated_joke: bool = False
    contains_generated_hook: bool = False
    contains_generated_punchline: bool = False
    contains_language_specific_behavior: bool = False
    contains_teleprompter_formatting: bool = False
