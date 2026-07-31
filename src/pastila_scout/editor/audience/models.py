"""Immutable audience configuration, calibration, and assessment contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.editor.voice.models import TonalSeriousness, VoiceDimensions


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PriorKnowledgeLevel(StrEnum):
    MINIMAL = "minimal"
    GENERAL = "general"
    INFORMED = "informed"
    SPECIALIST = "specialist"


class InformationDensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXCESSIVE = "excessive"


class ContextLoad(StrEnum):
    MINIMAL = "minimal"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class EntityLoad(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class NumericLoad(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ChronologyComplexity(StrEnum):
    SIMPLE = "simple"
    LAYERED = "layered"
    COMPLEX = "complex"


class ConceptComplexity(StrEnum):
    FAMILIAR = "familiar"
    EXPLAINABLE = "explainable"
    SPECIALIST = "specialist"


class Tolerance(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ContextBudgetLevel(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXCEPTIONAL = "exceptional"


class AttentionRiskType(StrEnum):
    SLOW_START = "slow_start"
    DELAYED_CORE = "delayed_editorial_core"
    UNCLEAR_RELEVANCE = "unclear_relevance"
    EXCESSIVE_CONTEXT = "excessive_context"
    EXCESSIVE_ENTITIES = "excessive_entities"
    EXCESSIVE_NUMBERS = "excessive_numbers"
    ACRONYM_OVERLOAD = "acronym_overload"
    CHRONOLOGY_CONFUSION = "chronology_confusion"
    REPETITIVE_EXPLANATION = "repetitive_explanation"
    REPETITIVE_QUESTIONS = "repetitive_rhetorical_questions"
    REPETITIVE_SATIRE = "repetitive_satirical_mechanism"
    UNRESOLVED_REFERENT = "unresolved_referent"
    WEAK_TRANSITION = "weak_transition"
    ABSTRACT_LANGUAGE = "abstract_institutional_language"
    JOKE_BEFORE_CONTEXT = "joke_before_context"
    CONCLUSION_REPETITION = "conclusion_repetition"
    TONAL_WHIPLASH = "tonal_whiplash"
    INSUFFICIENT_PAYOFF = "insufficient_payoff"
    EXCESSIVE_MORALIZING = "excessive_moralizing"


class TrustRiskType(StrEnum):
    FACTUAL_OVERSTATEMENT = "factual_overstatement"
    MISLEADING_OMISSION = "misleading_omission"
    UNATTRIBUTED_CLAIM = "unattributed_claim"
    FALSE_CERTAINTY = "false_certainty"
    MANUFACTURED_OUTRAGE = "manufactured_outrage"
    SENSATIONAL_FRAMING = "sensational_framing"
    FAKE_BALANCE = "fake_balance"
    HIDDEN_UNCERTAINTY = "hidden_uncertainty"
    VICTIM_EXPLOITATION = "victim_exploitation"
    CONDESCENSION = "condescension"
    EVIDENCE_COMMENTARY_CONTRADICTION = "evidence_commentary_contradiction"
    UNSUPPORTED_MORAL_CONCLUSION = "unsupported_moral_conclusion"
    UNDISCLOSED_SATIRE = "undisclosed_satire_presented_as_fact"
    REPETITIVE_EXAGGERATION = "repetitive_exaggeration"
    PROFILE_AUDIENCE_CONFLICT = "profile_audience_conflict"


class FatigueType(StrEnum):
    ENTITY = "entity_fatigue"
    ACRONYM = "acronym_fatigue"
    NUMERIC = "numeric_fatigue"
    CONTEXT = "context_fatigue"
    REPETITION = "repetition_fatigue"
    OUTRAGE = "outrage_fatigue"
    SARCASM = "sarcasm_fatigue"
    RHETORICAL_QUESTION = "rhetorical_question_fatigue"
    INSTITUTIONAL_DETAIL = "institutional_detail_fatigue"
    CHRONOLOGY = "chronology_fatigue"
    TONAL = "tonal_fatigue"
    MORALIZING = "moralizing_fatigue"
    CALLBACK = "callback_fatigue"
    EPISODE_CONTINUITY = "episode_continuity_fatigue"


class AudienceEmotion(StrEnum):
    CURIOUS = "curious"
    INFORMED = "informed"
    SURPRISED = "surprised"
    AMUSED = "amused"
    FRUSTRATED = "frustrated"
    INDIGNANT = "indignant"
    CONCERNED = "concerned"
    EMPATHETIC = "empathetic"
    REFLECTIVE = "reflective"
    GRAVE = "grave"


class AudienceRiskSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AudienceReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class AudiencePrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    required_behaviors: tuple[str, ...] = Field(min_length=1)
    prohibited_behaviors: tuple[str, ...] = Field(min_length=1)


class AudienceKnowledgeProfile(FrozenModel):
    default_prior_knowledge: PriorKnowledgeLevel
    assumed_knowledge_categories: tuple[str, ...]
    required_context_categories: tuple[str, ...] = Field(min_length=1)
    specialist_knowledge_categories: tuple[str, ...] = Field(min_length=1)
    recurring_project_knowledge: tuple[str, ...]
    prohibited_assumptions: tuple[str, ...] = Field(min_length=1)
    intelligence_implies_complete_prior_knowledge: bool = False
    specialist_knowledge_assumed_without_context: bool = False
    previous_episode_knowledge_mandatory: bool = False


class AudienceCognitiveProfile(FrozenModel):
    preferred_information_density: InformationDensity
    maximum_recommended_context_load: ContextLoad
    maximum_recommended_entity_load: EntityLoad
    maximum_recommended_numeric_load: NumericLoad
    chronology_tolerance: ChronologyComplexity
    concept_complexity_tolerance: ConceptComplexity
    repetition_tolerance: Tolerance
    acronym_tolerance: Tolerance
    unresolved_reference_tolerance: Tolerance
    recommended_mitigation_strategies: tuple[str, ...] = Field(min_length=1)
    claims_scientifically_validated_constants: bool = False


class ContextBudget(FrozenModel):
    budget_level: ContextBudgetLevel
    justification: str = Field(min_length=1)
    required_background: tuple[str, ...]
    optional_background: tuple[str, ...]
    prohibited_detours: tuple[str, ...]
    compression_candidates: tuple[str, ...]
    indispensable_explanations: tuple[str, ...]
    review_conditions: tuple[str, ...]
    required_context_material_ids: tuple[str, ...] = ()
    optional_context_excessive: bool = False
    missing_indispensable_context: bool = False


class AudienceTrustProfile(FrozenModel):
    foundations: tuple[str, ...] = Field(min_length=1)
    permits_manipulation: bool = False
    permits_condescension: bool = False
    permits_victim_exploitation: bool = False


class AudienceAttentionRisk(FrozenModel):
    risk_id: str = Field(min_length=1)
    risk_type: AttentionRiskType
    severity: AudienceRiskSeverity
    affected_ids: tuple[str, ...] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    likely_audience_effect: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    blocking: bool
    requires_editor_in_chief_review: bool
    claims_guaranteed_retention_outcome: bool = False


class AudienceTrustRisk(FrozenModel):
    risk_id: str = Field(min_length=1)
    risk_type: TrustRiskType
    severity: AudienceRiskSeverity
    affected_evidence_ids: tuple[str, ...] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    likely_trust_consequence: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    blocking: bool
    requires_editor_in_chief_review: bool
    neutralized_for_humor_or_retention: bool = False


class AudienceEmotionalCalibration(FrozenModel):
    primary_intended_response: AudienceEmotion
    secondary_intended_responses: tuple[AudienceEmotion, ...]
    responses_to_avoid: tuple[AudienceEmotion, ...]
    factual_basis_material_ids: tuple[str, ...] = Field(min_length=1)
    emotional_ceiling: AudienceEmotion
    tonal_seriousness: TonalSeriousness
    tonal_constraints: tuple[str, ...] = Field(min_length=1)
    sensitivity_conditions: tuple[str, ...]
    editor_review_conditions: tuple[str, ...]
    manufactures_outrage: bool = False
    manufactures_fear: bool = False
    exploits_grief: bool = False
    amusement_targets_victims: bool = False
    claims_guaranteed_emotion: bool = False
    unresolved_tonal_ambiguity: bool = False


class AudienceFatigueAssessment(FrozenModel):
    fatigue_id: str = Field(min_length=1)
    fatigue_type: FatigueType
    severity: AudienceRiskSeverity
    affected_elements: tuple[str, ...] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    cumulative_effect: str = Field(min_length=1)
    requires_editor_in_chief_review: bool


class AudienceProfileGuidance(FrozenModel):
    guidance_id: str = Field(min_length=1)
    source_finding_ids: tuple[str, ...] = Field(min_length=1)
    established: bool
    affected_dimensions: tuple[str, ...] = Field(min_length=1)
    proposed_tuning: tuple[str, ...] = Field(min_length=1)
    confidence: str = Field(pattern=r"^(high|medium|low)$")
    evidence_episode_ids: tuple[str, ...] = Field(min_length=1)
    fixed_boundary_compatible: bool
    active: bool
    contradictory_guidance_ids: tuple[str, ...] = ()
    permits_manipulation: bool = False
    permits_factual_distortion: bool = False
    overrides_victim_safeguards: bool = False
    infers_demographic_traits: bool = False


class AudienceCalibration(FrozenModel):
    audience_id: str
    audience_version: str
    prior_knowledge: PriorKnowledgeLevel
    context_budget: ContextBudget
    cognitive_profile: AudienceCognitiveProfile
    intended_emotional_response: AudienceEmotionalCalibration
    voice_dimensions: VoiceDimensions
    attention_priorities: tuple[str, ...] = Field(min_length=1)
    trust_safeguards: tuple[str, ...] = Field(min_length=1)
    fatigue_constraints: tuple[str, ...] = Field(min_length=1)
    episode_specific_overrides: tuple[str, ...] = ()
    established_profile_guidance: tuple[AudienceProfileGuidance, ...] = ()
    requires_editor_in_chief_review: bool = False
    permits_factual_distortion: bool = False
    permits_manipulation: bool = False
    permits_condescension: bool = False
    assumes_unexplained_specialist_knowledge: bool = False
    erases_uncertainty: bool = False
    turns_victims_into_entertainment: bool = False
    overrides_fixed_boundaries: bool = False


class AudienceModel(FrozenModel):
    audience_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str
    title: str = Field(min_length=1)
    project: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    primary_medium: str = Field(min_length=1)
    audience_assumptions: tuple[str, ...] = Field(min_length=1)
    excluded_assumptions: tuple[str, ...] = Field(min_length=1)
    principles: tuple[AudiencePrinciple, ...] = Field(min_length=1)
    knowledge_profile: AudienceKnowledgeProfile
    cognitive_profile: AudienceCognitiveProfile
    trust_profile: AudienceTrustProfile
    default_emotional_policy: tuple[str, ...] = Field(min_length=1)
    fatigue_policy: tuple[str, ...] = Field(min_length=1)
    attention_policy: tuple[str, ...] = Field(min_length=1)
    fixed_boundaries: tuple[str, ...] = Field(min_length=1)
    models_audience_as_gullible: bool = False
    models_audience_as_captive: bool = False
    models_audience_as_politically_uniform: bool = False
    contains_demographic_stereotyping: bool = False
    claims_universal_behavior: bool = False
    contains_story_generation_procedures: bool = False
    permits_automatic_prompt_mutation: bool = False


class ComprehensionAssessment(FrozenModel):
    summary: str = Field(min_length=1)
    unresolved_reference_ids: tuple[str, ...] = ()
    missing_indispensable_context: bool = False
    unresolved_central_factual_status: bool = False
    claims_guaranteed_comprehension: bool = False


class AudienceAssessment(FrozenModel):
    artifact_kind: str = "audience_assessment"
    assessment_id: str = Field(min_length=1)
    version: str
    audience_id: str
    audience_version: str
    decision_plan_id: str
    source_material_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calibration: AudienceCalibration
    comprehension_assessment: ComprehensionAssessment
    context_assessment: ContextBudget
    attention_risks: tuple[AudienceAttentionRisk, ...] = ()
    trust_risks: tuple[AudienceTrustRisk, ...] = ()
    fatigue_assessments: tuple[AudienceFatigueAssessment, ...] = ()
    emotional_calibration: AudienceEmotionalCalibration
    unresolved_audience_questions: tuple[str, ...] = ()
    blocking_issues: tuple[str, ...] = ()
    advisory_issues: tuple[str, ...] = ()
    requires_editor_in_chief_review: bool
    audience_readiness: AudienceReadiness
    summary: str = Field(min_length=1)
    modifies_editorial_decisions: bool = False
    contains_generated_script_text: bool = False
    contains_generated_joke_text: bool = False
