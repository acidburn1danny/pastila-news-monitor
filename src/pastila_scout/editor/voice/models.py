"""Immutable Satirical Voice configuration and opportunity contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MechanismType(StrEnum):
    IRONY = "irony"
    SARCASM = "sarcasm"
    CONTRAST = "contrast"
    UNDERSTATEMENT = "understatement"
    OVERSTATEMENT = "overstatement"
    RHETORICAL_QUESTION = "rhetorical_question"
    CALLBACK = "callback"
    REVERSAL = "reversal"
    LITERALIZATION = "literalization"
    BUREAUCRATIC_LANGUAGE_PARODY = "bureaucratic_language_parody"
    OFFICIAL_CLAIM_CONTRAST = "official_claim_contrast"
    ANALOGY = "analogy"
    ANTI_CLIMAX = "anti_climax"
    ESCALATION = "escalation"
    RULE_OF_THREE = "rule_of_three"
    DEADPAN_OBSERVATION = "deadpan_observation"
    ABSURD_CONSEQUENCE = "absurd_consequence"
    SOCIAL_OBSERVATION = "social_observation"
    DELAYED_PAYOFF = "delayed_payoff"


class SatiricalTargetType(StrEnum):
    DECISION = "decision"
    BEHAVIOR = "behavior"
    PUBLIC_CLAIM = "public_claim"
    CONTRADICTION = "contradiction"
    INSTITUTION = "institution"
    POLICY = "policy"
    ABUSE_OF_AUTHORITY = "abuse_of_authority"
    INCOMPETENCE = "incompetence"
    HYPOCRISY = "hypocrisy"
    PROPAGANDA = "propaganda"
    BUREAUCRATIC_DYSFUNCTION = "bureaucratic_dysfunction"
    SOCIAL_DYSFUNCTION = "social_dysfunction"
    MEDIA_FRAMING = "media_framing"
    PERPETRATOR_CONDUCT = "perpetrator_conduct"
    PUBLIC_CONSEQUENCE = "public_consequence"


class SensitiveSubjectType(StrEnum):
    VICTIMS = "victims"
    CHILDREN = "children"
    SEVERE_ILLNESS = "people_with_severe_illness"
    DISASTER_AFFECTED = "people_affected_by_disasters"
    EXPLOITED_PERSONS = "exploited_persons"
    PRIVATE_INDIVIDUALS = "private_individuals_without_public_responsibility"
    PROTECTED_CHARACTERISTICS = "protected_personal_characteristics"
    GRIEF_SUFFERING = "grief_and_suffering"


class SarcasmIntensity(StrEnum):
    RESTRAINED = "restrained"
    MODERATE = "moderate"
    STRONG = "strong"


class EmotionalTemperature(StrEnum):
    CALM = "calm"
    CONCERNED = "concerned"
    FRUSTRATED = "frustrated"
    INDIGNANT = "indignant"
    GRAVE = "grave"


class ConversationalProximity(StrEnum):
    DIRECT = "direct"
    COLLABORATIVE = "collaborative"
    REFLECTIVE = "reflective"


class HumorDensity(StrEnum):
    SPARSE = "sparse"
    BALANCED = "balanced"
    DENSE = "dense"


class TonalSeriousness(StrEnum):
    LIGHT = "light"
    MIXED = "mixed"
    SERIOUS = "serious"
    GRAVE = "grave"


class VoiceConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SatiricalRiskType(StrEnum):
    VICTIM_TARGETING = "victim_targeting"
    VULNERABLE_PERSON_MOCKERY = "vulnerable_person_mockery"
    FACTUAL_DISTORTION = "factual_distortion"
    UNSUPPORTED_ACCUSATION = "unsupported_accusation"
    MOTIVE_INVENTION = "motive_invention"
    JOKE_BEFORE_CONTEXT = "joke_before_context"
    TONAL_INSENSITIVITY = "tonal_insensitivity"
    CRUELTY = "cruelty"
    DEHUMANIZATION = "dehumanization"
    GENERIC_INSULT = "generic_insult"
    SENSATIONALISM = "sensationalism"
    REPETITIVE_MECHANISM = "repetitive_mechanism"
    EXCESSIVE_DENSITY = "excessive_density"
    JOKE_EXPLANATION = "joke_explanation"
    AUDIENCE_CONDESCENSION = "audience_condescension"
    UNNATURAL_PHRASING = "imported_or_unnatural_phrasing"
    DETACHED_FROM_CORE = "satire_detached_from_editorial_core"
    POLITICAL_PROPAGANDA = "political_propaganda"
    FALSE_EQUIVALENCE = "false_equivalence"
    PROFILE_PERSONA_CONFLICT = "profile_persona_conflict"


class SatiricalRiskSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VoiceDimensions(FrozenModel):
    sarcasm_intensity: SarcasmIntensity
    emotional_temperature: EmotionalTemperature
    conversational_proximity: ConversationalProximity
    humor_density: HumorDensity
    tonal_seriousness: TonalSeriousness


class SatiricalVoicePrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    required_behaviors: tuple[str, ...] = Field(min_length=1)
    prohibited_behaviors: tuple[str, ...] = Field(min_length=1)


class SatiricalMechanism(FrozenModel):
    mechanism_id: MechanismType
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    appropriate_uses: tuple[str, ...] = Field(min_length=1)
    misuse_risks: tuple[str, ...] = Field(min_length=1)
    factual_prerequisites: tuple[str, ...] = Field(min_length=1)
    tonal_constraints: tuple[str, ...] = Field(min_length=1)


class SatiricalVoiceCalibration(FrozenModel):
    dimensions: VoiceDimensions
    allowed_mechanisms: tuple[MechanismType, ...] = Field(min_length=1)
    disallowed_mechanisms: tuple[MechanismType, ...] = ()
    valid_targets: tuple[SatiricalTargetType, ...] = Field(min_length=1)
    protected_subjects: tuple[SensitiveSubjectType, ...] = Field(min_length=1)
    required_factual_prerequisites: tuple[str, ...] = Field(min_length=1)
    tonal_constraints: tuple[str, ...] = Field(min_length=1)
    escalation_conditions: tuple[str, ...] = Field(min_length=1)
    editor_review_conditions: tuple[str, ...] = Field(min_length=1)


class SatiricalVoice(FrozenModel):
    voice_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str
    title: str = Field(min_length=1)
    project: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    characteristics: tuple[str, ...] = Field(min_length=1)
    excluded_identities: tuple[str, ...] = Field(min_length=1)
    principles: tuple[SatiricalVoicePrinciple, ...] = Field(min_length=1)
    mechanisms: tuple[SatiricalMechanism, ...] = Field(min_length=1)
    calibration: SatiricalVoiceCalibration
    fixed_boundaries: tuple[str, ...] = Field(min_length=1)
    profile_may_tune_dimensions: bool = True
    emerging_trends_may_mutate_voice: bool = False
    profile_may_override_factuality: bool = False
    profile_may_target_protected_subjects: bool = False
    contains_personality_imitation: bool = False
    contains_fictional_biography: bool = False
    contains_generation_procedures: bool = False
    permits_automatic_prompt_mutation: bool = False


class VoiceProfileGuidance(FrozenModel):
    established: bool
    dimensions: VoiceDimensions
    permits_factual_distortion: bool = False
    permits_protected_subject_targeting: bool = False
    overrides_fixed_boundaries: bool = False


class SatiricalOpportunity(FrozenModel):
    opportunity_id: str = Field(min_length=1)
    supported_material_ids: tuple[str, ...] = Field(min_length=1)
    editorial_core_element_ids: tuple[str, ...] = Field(min_length=1)
    decision_ids: tuple[str, ...] = Field(min_length=1)
    risk_ids: tuple[str, ...] = ()
    target_type: SatiricalTargetType
    target_description: str = Field(min_length=1)
    supported_mechanisms: tuple[MechanismType, ...] = Field(min_length=1)
    factual_basis: tuple[str, ...] = Field(min_length=1)
    contradiction_or_absurdity: str = Field(min_length=1)
    intended_editorial_function: str = Field(min_length=1)
    sensitivity: SensitiveSubjectType | None = None
    tonal_limit: TonalSeriousness
    recommended_dimensions: VoiceDimensions
    confidence: VoiceConfidence
    prohibited_interpretations: tuple[str, ...] = Field(min_length=1)
    requires_editor_in_chief_review: bool
    targets_sensitive_subject: bool = False
    permits_factual_distortion: bool = False
    contains_unsupported_accusation: bool = False
    invents_motive: bool = False
    generic_insult_is_sole_mechanism: bool = False
    detached_from_editorial_core: bool = False
    contains_generated_joke_text: bool = False
    preserves_attribution: bool = True
    preserves_dispute_status: bool = True


class SatiricalRisk(FrozenModel):
    risk_id: str = Field(min_length=1)
    risk_type: SatiricalRiskType
    severity: SatiricalRiskSeverity
    affected_opportunity_ids: tuple[str, ...] = ()
    affected_material_ids: tuple[str, ...] = ()
    explanation: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    blocking: bool
    requires_editor_in_chief_review: bool
