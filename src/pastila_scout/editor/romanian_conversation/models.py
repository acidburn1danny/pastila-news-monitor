"""Immutable Romanian conversational-policy contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthenticityState(StrEnum):
    AUTHENTIC = "authentic"
    ACCEPTABLE = "acceptable"
    MARKED = "marked"
    ARTIFICIAL = "artificial"
    CONTEXT_DEPENDENT = "context_dependent"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class SocialRegister(StrEnum):
    NEUTRAL_CONVERSATIONAL = "neutral_conversational"
    POLISHED_CONVERSATIONAL = "polished_conversational"
    INFORMAL_CONVERSATIONAL = "informal_conversational"
    FAMILIAR = "familiar"
    RESTRAINED_COLLOQUIAL = "restrained_colloquial"
    STREET_INFLUENCED = "street_influenced"
    FORMAL_SPOKEN = "formal_spoken"
    CEREMONIAL = "ceremonial"
    JOURNALISTIC = "journalistic"
    BUREAUCRATIC = "bureaucratic"
    ACADEMIC = "academic"
    LEGAL = "legal"
    INTERNET_NATIVE = "internet_native"
    PERFORMATIVE_SLANG = "performative_slang"


class ConversationalReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class FindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuidanceStatus(StrEnum):
    OBSERVED = "observed"
    EMERGING = "emerging"
    ESTABLISHED = "established"
    EXPLICIT_EDITOR_RULE = "explicit_editor_rule"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class GuidanceScope(StrEnum):
    PROJECT_GLOBAL = "project_global"
    FORMAT_SPECIFIC = "format_specific"
    EPISODE_TYPE = "episode_type"
    STORY_SEVERITY = "story_severity"
    STORY_CATEGORY = "story_category"
    ENTITY_TYPE = "entity_type"
    SATIRE_MODE = "satire_mode"
    LOCAL_ONLY = "local_only"


class CorrectionScope(StrEnum):
    LOCAL = "local"
    EPISODE = "episode"
    FORMAT = "format"
    CONTEXT = "context"
    PROJECT = "project"
    PERMANENT_PROJECT_RULE = "permanent_project_rule"


class CorrectionCategory(StrEnum):
    SYNTAX = "syntax"
    WORD_ORDER = "word_order"
    ELLIPSIS = "ellipsis"
    FRAGMENTATION = "fragmentation"
    REPETITION = "repetition"
    CONNECTOR = "connector"
    LEXICAL_NATURALNESS = "lexical_naturalness"
    COLLOQUIALISM = "colloquialism"
    SLANG = "slang"
    JARGON = "jargon"
    TRANSLATED_CONSTRUCTION = "translated_construction"
    PRESS_LANGUAGE = "press_language"
    BUREAUCRATIC_LANGUAGE = "bureaucratic_language"
    ACADEMIC_LANGUAGE = "academic_language"
    ENTITY_REFERENCE = "entity_reference"
    DEMONSTRATIVE = "demonstrative"
    RHYTHM = "rhythm"
    PACING = "pacing"
    TRANSITION_STYLE = "transition_style"
    RHETORICAL_QUESTION = "rhetorical_question"
    SATIRE_INTEGRATION = "satire_integration"
    PAYOFF_DELIVERY = "payoff_delivery"
    POST_PAYOFF_EXPLANATION = "post_payoff_explanation"
    EMOTIONAL_DELIVERY = "emotional_delivery"
    SENSITIVITY = "sensitivity"
    TELEPROMPTER_READABILITY = "teleprompter_readability"
    PROHIBITED_EXPRESSION = "prohibited_expression"
    PREFERRED_EXPRESSION = "preferred_expression"
    OTHER = "other"


class RomanianConversationalPrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class PolicyModel(FrozenModel):
    policy_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    supported_features: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...] = Field(min_length=1)
    review_conditions: tuple[str, ...] = ()
    permits_generated_wording: bool = False
    overrides_upstream: bool = False


class RomanianSyntaxPolicy(PolicyModel):
    complete_grammar_implementation: bool = False


class RomanianWordOrderPolicy(PolicyModel):
    permits_factual_relationship_change: bool = False
    permits_attribution_change: bool = False
    permits_claim_status_change: bool = False


class RomanianEllipsisPolicy(PolicyModel):
    permits_unrecoverable_omission: bool = False
    permits_hidden_agency: bool = False
    permits_lost_attribution: bool = False


class SpokenFragmentPolicy(PolicyModel):
    requires_spoken_function: bool = True


class RomanianRepetitionPolicy(PolicyModel):
    requires_editorial_function: bool = True


class RomanianConnectorPolicy(PolicyModel):
    connector_families: tuple[str, ...] = Field(min_length=1)
    classifications: tuple[str, ...] = Field(min_length=1)


class RegisterAcceptabilityPolicy(PolicyModel):
    story_specific: bool = True


class SocialRegisterModel(FrozenModel):
    register_model_id: str
    preferred_registers: tuple[SocialRegister, ...] = Field(min_length=1)
    context_dependent_registers: tuple[SocialRegister, ...]
    discouraged_registers: tuple[SocialRegister, ...]
    prohibited_combinations: tuple[str, ...]
    sensitivity_constraints: tuple[str, ...]
    audience_constraints: tuple[str, ...]
    voice_compatibility: tuple[str, ...]
    persona_compatibility: tuple[str, ...]
    acceptability_policy: RegisterAcceptabilityPolicy


class LexicalReferenceEntry(FrozenModel):
    entry_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    normalized_expression: str = Field(min_length=1, max_length=80)
    category: str
    status: str
    explanation: str
    context_rules: tuple[str, ...]
    severity_when_violated: FindingSeverity
    requires_editor_review: bool
    source_type: str


class LexicalNaturalnessPolicy(PolicyModel):
    categories: tuple[str, ...] = Field(min_length=1)
    reference_catalogue: tuple[LexicalReferenceEntry, ...]
    enforces_linguistic_purism: bool = False


class ColloquialLanguagePolicy(PolicyModel):
    protected_subject_safeguards: bool = True


class SlangPolicy(PolicyModel):
    permits_forced_slang: bool = False
    permits_group_imitation: bool = False


class JargonPolicy(PolicyModel):
    preserves_required_precision: bool = True


class TranslatedConstructionPolicy(PolicyModel):
    rejects_all_borrowings: bool = False


class PressLanguagePolicy(PolicyModel):
    article_style_is_default: bool = False


class BureaucraticLanguagePolicy(PolicyModel):
    permits_hidden_agency: bool = False
    preserves_quoted_official_language: bool = True


class AcademicLanguagePolicy(PolicyModel):
    academic_framing_is_default: bool = False


class LegalPrecisionPolicy(PolicyModel):
    legal_states: tuple[str, ...] = Field(min_length=1)
    permits_status_simplification: bool = False


class RomanianEntityReferencePolicy(PolicyModel):
    permits_dehumanizing_reference: bool = False
    preserves_identity: bool = True


class RomanianDemonstrativePolicy(PolicyModel):
    requires_resolvable_reference: bool = True


class RomanianEmphasisPolicy(PolicyModel):
    generates_performance_notation: bool = False


class RomanianRhythmRealizationPolicy(PolicyModel):
    communication_rhythm_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    overrides_communication_rhythm: bool = False


class ConversationalRepairPolicy(PolicyModel):
    permits_factual_status_change: bool = False
    permits_unsupported_information: bool = False
    generates_mistakes: bool = False


class RomanianSatireIntegrationPolicy(PolicyModel):
    generates_jokes: bool = False
    preserves_opportunity_ownership: bool = True


class RomanianConversationalSensitivityPolicy(PolicyModel):
    permits_victim_trivialization: bool = False
    permits_protected_subject_targeting: bool = False


class RomanianTeleprompterRealizationPolicy(PolicyModel):
    communication_teleprompter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    produces_formatting: bool = False


class ConversationalAuthenticityModel(FrozenModel):
    model_id: str
    first_hearing_naturalness: str
    conversational_plausibility: str
    social_plausibility: str
    spoken_cadence: str
    syntactic_naturalness: str
    lexical_naturalness: str
    register_coherence: str
    rhetorical_plausibility: str
    performance_plausibility: str
    artificiality_indicators: tuple[str, ...]
    predicts_all_romanian_speakers: bool = False


class RegisterAssessment(FrozenModel):
    selected_register: SocialRegister
    context_compatible: bool
    audience_compatible: bool
    persona_compatible: bool
    voice_compatible: bool
    severity_compatible: bool
    socially_credible: bool
    public_broadcast_suitable: bool
    requires_editor_review: bool = False


class RomanianConversationalPattern(FrozenModel):
    pattern_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str
    category: str
    normalized_shape: str = Field(max_length=100)
    conversational_function: str
    authenticity_classification: AuthenticityState
    register_compatibility: tuple[SocialRegister, ...]
    story_severity_compatibility: tuple[str, ...]
    voice_compatibility: tuple[str, ...]
    audience_compatibility: tuple[str, ...]
    positive_constraints: tuple[str, ...]
    negative_constraints: tuple[str, ...]
    ambiguity_risks: tuple[str, ...]
    requires_editor_review: bool
    provenance_type: str
    examples: tuple[str, ...]

    @model_validator(mode="after")
    def reject_long_examples(self) -> RomanianConversationalPattern:
        if any(len(example) > 100 for example in self.examples):
            raise ValueError(
                "conversational examples must remain short reference fragments"
            )
        return self


class AILanguageIndicator(FrozenModel):
    indicator_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    indicator_type: str
    explanation: str
    evidence_reference_ids: tuple[str, ...]
    severity: FindingSeverity
    requires_editor_review: bool
    claims_ai_authorship: bool = False


class RomanianConversationalRisk(FrozenModel):
    risk_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    risk_type: str
    severity: FindingSeverity
    affected_policy_identifiers: tuple[str, ...] = Field(min_length=1)
    explanation: str
    evidence_references: tuple[str, ...]
    mitigation_direction: str
    blocking: bool
    requires_editor_review: bool
    contains_replacement_wording: bool = False


class RomanianProfileGuidance(FrozenModel):
    guidance_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    dimension: str
    value: str
    strength: str
    status: GuidanceStatus
    evidence_references: tuple[str, ...] = Field(min_length=1)
    episode_references: tuple[str, ...] = Field(min_length=1)
    editor_confirmed: bool
    scope: GuidanceScope
    conflict_rules: tuple[str, ...]
    fixed_boundary_compatible: bool
    attempts_upstream_override: bool = False


class CorrectionIntegrationPoint(FrozenModel):
    correction_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    original_reference: str
    edited_reference: str
    editor_explanation: str
    correction_category: CorrectionCategory
    correction_scope: CorrectionScope
    explicit_permanence: bool
    episode_provenance: tuple[str, ...] = Field(min_length=1)
    text_region_provenance: tuple[str, ...] = Field(min_length=1)
    accepted_direction: str
    rejected_direction: str
    performs_learning: bool = False
    performs_persistence: bool = False
    mutates_canonical_engine: bool = False
    contains_generated_replacement_prose: bool = False


class ConversationalAuthenticityAssessment(FrozenModel):
    assessment_id: str
    engine_id: str
    engine_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    communication_assessment_id: str
    communication_assessment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_reference_identifiers: tuple[str, ...]
    authenticity_state: AuthenticityState
    findings: tuple[str, ...]
    risks: tuple[str, ...]
    advisories: tuple[str, ...]
    evidence_references: tuple[str, ...]
    profile_guidance_references: tuple[str, ...]
    readiness: ConversationalReadiness
    contains_generated_rewrite: bool = False
    contains_replacement_wording: bool = False


class RomanianConversationalEngine(FrozenModel):
    conversational_engine_id: str
    version: str
    title: str
    project: str
    language: str
    language_code: str
    jurisdiction: str
    primary_medium: str
    primary_context: str
    canonical_assumptions: tuple[str, ...]
    principles: tuple[RomanianConversationalPrinciple, ...]
    authenticity_model: ConversationalAuthenticityModel
    register_policy: SocialRegisterModel
    syntax_policy: RomanianSyntaxPolicy
    word_order_policy: RomanianWordOrderPolicy
    ellipsis_policy: RomanianEllipsisPolicy
    fragment_policy: SpokenFragmentPolicy
    repetition_policy: RomanianRepetitionPolicy
    connector_policy: RomanianConnectorPolicy
    colloquial_policy: ColloquialLanguagePolicy
    slang_policy: SlangPolicy
    jargon_policy: JargonPolicy
    lexical_naturalness_policy: LexicalNaturalnessPolicy
    translated_construction_policy: TranslatedConstructionPolicy
    press_language_policy: PressLanguagePolicy
    bureaucratic_language_policy: BureaucraticLanguagePolicy
    academic_language_policy: AcademicLanguagePolicy
    legal_precision_policy: LegalPrecisionPolicy
    entity_reference_policy: RomanianEntityReferencePolicy
    demonstrative_policy: RomanianDemonstrativePolicy
    emphasis_policy: RomanianEmphasisPolicy
    rhythm_realization_policy: RomanianRhythmRealizationPolicy
    repair_policy: ConversationalRepairPolicy
    satire_integration_policy: RomanianSatireIntegrationPolicy
    sensitivity_policy: RomanianConversationalSensitivityPolicy
    teleprompter_realization_policy: RomanianTeleprompterRealizationPolicy
    conversational_patterns: tuple[RomanianConversationalPattern, ...]
    canonical_reference_catalogue: tuple[LexicalReferenceEntry, ...]
    ai_likeness_indicators: tuple[AILanguageIndicator, ...]
    default_risk_definitions: tuple[RomanianConversationalRisk, ...]
    correction_integration_points: tuple[str, ...]
    supported_guidance_dimensions: tuple[str, ...]
    fixed_boundaries: tuple[str, ...]
    editor_authority: str
    contains_generation_procedures: bool = False
    implements_learning: bool = False
    contains_unbounded_dictionary: bool = False


class RomanianConversationalAssessment(FrozenModel):
    artifact_kind: str = "romanian_conversational_assessment"
    assessment_id: str
    version: str
    engine_id: str
    engine_version: str
    engine_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    communication_assessment_id: str
    communication_assessment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    story_architecture_plan_id: str
    story_architecture_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    persona_id: str
    philosophy_id: str
    voice_id: str
    audience_id: str
    decision_plan_id: str
    evaluated_reference_identifiers: tuple[str, ...]
    authenticity_assessment: ConversationalAuthenticityAssessment
    selected_register: SocialRegister
    register_assessment: RegisterAssessment
    syntax_findings: tuple[str, ...] = ()
    word_order_findings: tuple[str, ...] = ()
    ellipsis_findings: tuple[str, ...] = ()
    fragment_findings: tuple[str, ...] = ()
    repetition_findings: tuple[str, ...] = ()
    connector_findings: tuple[str, ...] = ()
    lexical_findings: tuple[str, ...] = ()
    colloquial_findings: tuple[str, ...] = ()
    slang_findings: tuple[str, ...] = ()
    jargon_findings: tuple[str, ...] = ()
    translated_construction_findings: tuple[str, ...] = ()
    press_language_findings: tuple[str, ...] = ()
    bureaucratic_language_findings: tuple[str, ...] = ()
    academic_language_findings: tuple[str, ...] = ()
    legal_precision_findings: tuple[str, ...] = ()
    entity_reference_findings: tuple[str, ...] = ()
    demonstrative_findings: tuple[str, ...] = ()
    emphasis_findings: tuple[str, ...] = ()
    rhythm_findings: tuple[str, ...] = ()
    repair_findings: tuple[str, ...] = ()
    satire_integration_findings: tuple[str, ...] = ()
    sensitivity_findings: tuple[str, ...] = ()
    teleprompter_findings: tuple[str, ...] = ()
    ai_likeness_indicators: tuple[AILanguageIndicator, ...] = ()
    risks: tuple[RomanianConversationalRisk, ...] = ()
    advisories: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()
    profile_guidance: tuple[RomanianProfileGuidance, ...] = ()
    dependencies: tuple[str, ...] = ()
    readiness: ConversationalReadiness
    contains_generated_text: bool = False
    contains_replacement_language: bool = False
    modifies_upstream_contracts: bool = False
