"""Immutable contracts for evidence-governed editorial language learning."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = "1.0.0"

    @property
    def canonical_identifier(self) -> str:
        """Return the artifact's stable domain identifier."""
        for name in self.__class__.model_fields:
            if name.endswith("_id") and (value := getattr(self, name, None)):
                return str(value)
        return self.__class__.__name__

    def render(self) -> str:
        """Render this artifact canonically without runtime provenance."""
        from pastila_scout.editor.language_learning.render import render_artifact

        return render_artifact(self)

    def validate_contract(self):
        """Validate universal identity and forbidden-content invariants."""
        from pastila_scout.editor.language_learning.validator import validate_artifact

        return validate_artifact(self)

    @property
    def semantic_sha256(self) -> str:
        """Return the artifact's semantic SHA-256 fingerprint."""
        from pastila_scout.editor.language_learning.fingerprint import (
            artifact_fingerprint,
        )

        return artifact_fingerprint(self)


class PreferenceStatus(StrEnum):
    CANDIDATE = "candidate"
    EMERGING = "emerging"
    ESTABLISHED = "established"
    EXPLICIT_EDITOR_RULE = "explicit_editor_rule"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ConfidenceState(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class LearningReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class ObservationScope(StrEnum):
    LOCAL = "local"
    STORY = "story"
    EPISODE = "episode"
    FORMAT = "format"
    CATEGORY = "category"
    SERIES = "series"
    PROJECT = "project"
    PERMANENT_EDITOR_RULE = "permanent_editor_rule"


class DecayState(StrEnum):
    ACTIVE = "active"
    STABLE = "stable"
    AGING = "aging"
    WEAKENING = "weakening"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ConflictType(StrEnum):
    DIRECT = "direct_contradiction"
    PARTIAL = "partial_contradiction"
    SCOPE = "scope_contradiction"
    CONTEXT = "context_contradiction"
    EDITOR_OVERRIDE = "editor_override"
    DEPRECATED = "deprecated_conflict"
    SUPERSEDED = "superseded_conflict"
    TEMPORAL = "temporal_conflict"
    PROMOTION = "promotion_conflict"


class OperationType(StrEnum):
    INSERT = "insert"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    SPLIT = "split"
    MERGE = "merge"
    COMPRESS = "compress"
    EXPAND = "expand"
    CLARIFY = "clarify"
    REORDER = "reorder"
    DELAY = "delay"
    ADVANCE = "advance"
    RENAME_REFERENCE = "rename_reference"
    NORMALIZE = "normalize"
    RESTORE = "restore"
    PROTECT = "protect"
    REMOVE_CONNECTOR = "remove_connector"
    SHORTEN_SENTENCE = "shorten_sentence"
    REORDER_CLAUSE = "reorder_clause"
    MOVE_EVIDENCE = "move_evidence"
    DELAY_PAYOFF = "delay_payoff"
    COMPRESS_EXPLANATION = "compress_explanation"
    REDUCE_REPETITION = "reduce_repetition"
    SIMPLIFY_REFERENCE = "simplify_reference"
    REMOVE_PRESS_LANGUAGE = "remove_press_language"
    REMOVE_BUREAUCRATIC_LANGUAGE = "remove_bureaucratic_language"
    IMPROVE_RHYTHM = "improve_rhythm"
    IMPROVE_PACING = "improve_pacing"
    IMPROVE_ORIENTATION = "improve_orientation"
    IMPROVE_CLARITY = "improve_clarity"


class LanguageDimension(StrEnum):
    SYNTAX = "syntax"
    WORD_ORDER = "word_order"
    SENTENCE_LENGTH = "sentence_length"
    SENTENCE_GROUPING = "sentence_grouping"
    CONNECTOR = "connector"
    ELLIPSIS = "ellipsis"
    FRAGMENTATION = "fragmentation"
    REPETITION = "repetition"
    LEXICAL_NATURALNESS = "lexical_naturalness"
    COLLOQUIALISM = "colloquialism"
    SLANG = "slang"
    JARGON = "jargon"
    BUREAUCRATIC_LANGUAGE = "bureaucratic_language"
    PRESS_LANGUAGE = "press_language"
    ACADEMIC_LANGUAGE = "academic_language"
    TRANSLATED_CONSTRUCTION = "translated_construction"
    ENTITY_REFERENCE = "entity_reference"
    DEMONSTRATIVE = "demonstrative"
    CLARITY = "clarity"
    ORIENTATION = "orientation"
    RHYTHM = "rhythm"
    PACING = "pacing"
    TELEPROMPTER = "teleprompter"
    PAYOFF = "payoff"
    CALLBACK = "callback"
    SATIRE = "satire"
    HUMOR = "humor"
    GRAVITY = "gravity"
    EMOTION = "emotion"
    LEGAL_PRECISION = "legal_precision"
    SENSITIVITY = "sensitivity"
    POST_PAYOFF_EXPLANATION = "post_payoff_explanation"
    OVER_EXPLANATION = "over_explanation"
    UNDER_EXPLANATION = "under_explanation"
    EDITORIAL_DIRECTNESS = "editorial_directness"


class EditorialIntentCategory(StrEnum):
    INCREASE_CLARITY = "increase_clarity"
    REDUCE_CLARITY_LOSS = "reduce_clarity_loss"
    REDUCE_FORMALITY = "reduce_formality"
    INCREASE_FORMALITY = "increase_formality"
    REDUCE_REPETITION = "reduce_repetition"
    IMPROVE_RHYTHM = "improve_rhythm"
    IMPROVE_PACING = "improve_pacing"
    PROTECT_PAYOFF = "protect_payoff"
    DELAY_SATIRE = "delay_satire"
    ADVANCE_FACT = "advance_fact"
    DELAY_FACT = "delay_fact"
    INCREASE_DIRECTNESS = "increase_directness"
    REDUCE_EXPLANATION = "reduce_explanation"
    INCREASE_EXPLANATION = "increase_explanation"
    IMPROVE_ORIENTATION = "improve_orientation"
    RESTORE_LEGAL_PRECISION = "restore_legal_precision"
    REDUCE_JOURNALISTIC_LANGUAGE = "reduce_journalistic_language"
    REDUCE_BUREAUCRATIC_LANGUAGE = "reduce_bureaucratic_language"
    REDUCE_ACADEMIC_LANGUAGE = "reduce_academic_language"
    INCREASE_CONVERSATIONAL_NATURALNESS = "increase_conversational_naturalness"
    PROTECT_DIGNITY = "protect_dignity"
    IMPROVE_TELEPROMPTER = "improve_teleprompter"
    IMPROVE_CALLBACK = "improve_callback"
    IMPROVE_TRANSITION = "improve_transition"
    OTHER = "other"


class ObservationDimension(FrozenModel):
    dimension_id: str


class EditorialIntentModel(FrozenModel):
    intent_id: str
    category: str
    explanation_reference: str
    contains_generated_language: bool = False


class LanguageEditOperation(FrozenModel):
    operation_id: str
    operation_type: OperationType
    affected_dimension: str
    intent_reference: str
    semantic_effect: str
    contains_wording: bool = False


class LanguageEditEdge(FrozenModel):
    predecessor_operation_id: str
    successor_operation_id: str


class LanguageEditGraph(FrozenModel):
    graph_id: str
    source_reference: str
    target_reference: str
    ordered_operations: tuple[LanguageEditOperation, ...] = Field(min_length=1)
    dependency_edges: tuple[LanguageEditEdge, ...] = ()
    semantic_groups: tuple[str, ...] = ()
    operation_lineage: tuple[str, ...] = ()
    editor_intent_references: tuple[str, ...] = Field(min_length=1)
    graph_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    contains_text: bool = False


class EditorialObservation(FrozenModel):
    observation_id: str
    edit_graph_reference: str
    editor_intent_reference: str
    affected_policy_identifiers: tuple[str, ...]
    affected_language_dimensions: tuple[str, ...] = Field(min_length=1)
    episode_reference: str
    story_reference: str
    editor_reference: str
    scope: ObservationScope
    provenance_reference: str = Field(min_length=1)
    provenance_timestamp: str | None = None
    semantic_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    validated_editor_correction: bool = True

    @property
    def affected_dimensions(self) -> tuple[str, ...]:
        """Normative alias retained alongside the original field name."""
        return self.affected_language_dimensions


class ObservationAggregation(FrozenModel):
    aggregation_id: str
    observation_identifiers: tuple[str, ...] = Field(min_length=1)
    grouping_dimensions: tuple[str, ...]
    support_count: int = Field(ge=1)
    episode_count: int = Field(ge=1)
    story_count: int = Field(ge=1)
    consistency: float = Field(ge=0, le=1)
    creates_guidance: bool = False


class EvidenceChain(FrozenModel):
    evidence_id: str
    observation_identifiers: tuple[str, ...] = Field(min_length=1)
    episode_identifiers: tuple[str, ...] = Field(min_length=1)
    story_identifiers: tuple[str, ...] = Field(min_length=1)
    edit_graph_identifiers: tuple[str, ...] = Field(min_length=1)
    editor_confirmations: tuple[str, ...] = ()
    explicit_editor_rules: tuple[str, ...] = ()
    chronological_references: tuple[str, ...] = Field(min_length=1)


class CounterEvidence(FrozenModel):
    counter_evidence_id: str
    conflicting_observation_identifiers: tuple[str, ...] = ()
    non_edited_example_references: tuple[str, ...] = ()
    reverted_preference_identifiers: tuple[str, ...] = ()
    editor_rejection_references: tuple[str, ...] = ()
    explicit_override_references: tuple[str, ...] = ()
    contradiction_count: int = Field(ge=0)


class ConfidencePolicy(FrozenModel):
    observation_weight: float = 0.25
    episode_diversity_weight: float = 0.15
    story_diversity_weight: float = 0.15
    context_diversity_weight: float = 0.1
    confirmation_weight: float = 0.15
    consistency_weight: float = 0.2
    counter_evidence_penalty: float = 0.25
    conflict_penalty: float = 0.2


class ConfidenceModel(FrozenModel):
    score: int = Field(ge=0, le=100)
    state: ConfidenceState
    observation_count: int = Field(ge=0)
    episode_diversity: int = Field(ge=0)
    story_diversity: int = Field(ge=0)
    context_diversity: int = Field(ge=0)
    editor_confirmation: bool
    explicit_editor_rule: bool
    counter_evidence_count: int = Field(ge=0)
    consistency: float = Field(ge=0, le=1)
    recency: float = Field(default=1.0, ge=0, le=1)
    scope_stability: float = Field(default=1.0, ge=0, le=1)
    conflict_count: int = Field(default=0, ge=0)
    explanation_references: tuple[str, ...]
    derived: bool = True


class LearningEvidence(FrozenModel):
    evidence_id: str
    observation_references: tuple[str, ...] = Field(min_length=1)
    episode_references: tuple[str, ...]
    story_references: tuple[str, ...]
    edit_graph_references: tuple[str, ...]
    editor_confirmations: tuple[str, ...]
    explicit_rules: tuple[str, ...]
    counter_evidence_references: tuple[str, ...]
    support_count: int = Field(ge=1)
    contradiction_count: int = Field(ge=0)
    confidence_contribution: int


class LearningCandidate(FrozenModel):
    candidate_id: str
    origin_observations: tuple[str, ...] = Field(min_length=1)
    confidence: ConfidenceModel
    support: int = Field(ge=1)
    counter_support: int = Field(ge=0)
    affected_language_dimensions: tuple[str, ...]
    suggested_scope: ObservationScope
    review_required: bool
    eligible: bool
    conflict_references: tuple[str, ...] = ()
    supporting_evidence_references: tuple[str, ...] = Field(default=(), min_length=0)
    counter_evidence_references: tuple[str, ...] = ()
    inactive: bool = True


class PreferenceConflict(FrozenModel):
    conflict_id: str
    conflict_type: ConflictType
    preference_identifiers: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[str, ...]
    explanation_references: tuple[str, ...]
    requires_editor_review: bool
    resolved: bool = False
    predecessor_preference_id: str | None = None
    successor_preference_id: str | None = None
    confidence_impact: int = Field(default=0, le=0)
    resolution_status: str = "unresolved"


class PreferenceDecayPolicy(FrozenModel):
    first_observation: str
    last_observation: str
    last_confirmation: str | None
    observation_count: int = Field(ge=1)
    episode_count: int = Field(ge=1)
    story_count: int = Field(ge=1)
    time_since_confirmation: int = Field(ge=0)
    consistency: float = Field(ge=0, le=1)
    counter_evidence_ratio: float = Field(ge=0, le=1)
    editor_confirmation: bool
    explicit_rule: bool
    deprecation_reason: str | None
    activity_status: DecayState
    confidence_adjustment: int = Field(default=0, le=0)
    influence_score: int = Field(default=100, ge=0, le=100)
    recommendation_priority: int = Field(default=100, ge=0, le=100)


class LearningExplanation(FrozenModel):
    explanation_id: str
    why_learned: tuple[str, ...]
    why_rejected: tuple[str, ...]
    why_promoted: tuple[str, ...]
    why_deprecated: tuple[str, ...]
    confidence_change_reasons: tuple[str, ...]
    conflict_reasons: tuple[str, ...]
    explicit_rule_reasons: tuple[str, ...]
    scope_change_reasons: tuple[str, ...]
    contains_generated_prose: bool = False


class EditorialPreference(FrozenModel):
    preference_id: str
    language_dimension: str
    editorial_intent: str
    status: PreferenceStatus
    confidence: ConfidenceModel
    evidence_chain: EvidenceChain
    counter_evidence: CounterEvidence
    scope: ObservationScope
    activation_rules: tuple[str, ...]
    deprecation_rules: tuple[str, ...]
    supersession_rules: tuple[str, ...]
    compatibility_references: tuple[str, ...]
    requires_editor_review: bool
    explanation: LearningExplanation
    predecessor_preference_ids: tuple[str, ...] = ()
    successor_preference_ids: tuple[str, ...] = ()

    @property
    def lifecycle_state(self) -> PreferenceStatus:
        return self.status


class PreferenceSupersession(FrozenModel):
    supersession_id: str
    old_preference_id: str
    new_preference_id: str
    reason_reference: str
    editor_confirmation: bool
    support_evidence: tuple[str, ...] = Field(min_length=1)


class PreferenceAggregationPolicy(FrozenModel):
    minimum_observations: int = 3
    minimum_episodes: int = 2
    minimum_diversity: int = 2
    minimum_consistency: float = 0.7
    maximum_counter_evidence_ratio: float = 0.3
    minimum_confidence: int = 60
    editor_confirmation_requirement: bool = False


class LearningCandidatePolicy(FrozenModel):
    candidate_eligibility: tuple[str, ...]
    candidate_expiration: tuple[str, ...]
    candidate_review: tuple[str, ...]
    candidate_rejection: tuple[str, ...]
    candidate_promotion: tuple[str, ...]
    candidate_conflict_detection: tuple[str, ...]


class PreferencePromotionPolicy(FrozenModel):
    emerging_threshold: int = 60
    established_threshold: int = 80
    required_observations: int = 3
    maximum_counter_ratio: float = 0.3


class PreferenceDeprecationPolicy(FrozenModel):
    manual_deprecation: bool = True
    automatic_weakening: bool = True
    conflict_deprecation: bool = True
    replacement: bool = True
    supersession: bool = True
    editor_override: bool = True


class ConflictEngine(FrozenModel):
    supported_conflicts: tuple[ConflictType, ...]
    deletes_evidence: bool = False
    invents_preferences: bool = False
    preserves_lineage: bool = True


class CounterEvidencePolicy(FrozenModel):
    sources: tuple[str, ...]
    always_reduces_confidence: bool = True
    erases_observations: bool = False


class PreferenceLifecyclePolicy(FrozenModel):
    allowed_transitions: tuple[str, ...]


class ProfileMaturityModel(FrozenModel):
    state: str
    evidence_count: int
    episode_diversity: int
    story_diversity: int
    confidence: ConfidenceState
    derived_from_elapsed_time_only: bool = False


class EditorialLanguageProfile(FrozenModel):
    profile_id: str
    editor_identity: str
    learning_engine_id: str
    profile_version: str
    active_preferences: tuple[EditorialPreference, ...]
    emerging_preferences: tuple[EditorialPreference, ...]
    explicit_rules: tuple[EditorialPreference, ...]
    deprecated_preferences: tuple[EditorialPreference, ...]
    rejected_preferences: tuple[EditorialPreference, ...]
    archived_preferences: tuple[EditorialPreference, ...] = ()
    conflicts: tuple[PreferenceConflict, ...]
    profile_confidence: ConfidenceModel
    profile_maturity: ProfileMaturityModel
    observation_count: int
    candidate_count: int
    established_count: int
    emerging_count: int
    deprecated_count: int
    explicit_rule_count: int
    conflict_count: int
    counter_evidence_count: int
    profile_explanation: LearningExplanation
    profile_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    contains_generated_text: bool = False


class LearnedGuidance(FrozenModel):
    guidance_id: str
    source_preference_id: str
    status: PreferenceStatus
    confidence: ConfidenceModel
    scope: ObservationScope
    supported_dimensions: tuple[str, ...]
    requires_editor_review: bool
    compatibility_references: tuple[str, ...]
    advisory_only: bool = True
    contains_language: bool = False


class GuidanceProjection(FrozenModel):
    projection_id: str
    profile_id: str
    guidance: tuple[LearnedGuidance, ...]
    preference_identifiers: tuple[str, ...]
    compatibility_references: tuple[str, ...]
    advisory_only: bool = True


class UpstreamCompatibilityReference(FrozenModel):
    """Immutable identity snapshot for one canonical upstream dependency."""

    module_id: str = Field(min_length=1)
    module_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    semantic_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    readiness: LearningReadiness = LearningReadiness.READY


class LearningCompatibilitySnapshot(FrozenModel):
    """Reference-only proof that learning did not mutate upstream systems."""

    snapshot_id: str = Field(min_length=1)
    dependencies: tuple[UpstreamCompatibilityReference, ...] = Field(min_length=1)
    canonical_mutation: bool = False


class CorrectionImportContract(FrozenModel):
    import_id: str
    original_reference: str
    edited_reference: str
    language_edit_graph: LanguageEditGraph
    editor_intent: EditorialIntentModel
    editor_explanation_reference: str
    scope: ObservationScope
    explicit_permanence: bool
    episode_reference: str
    story_reference: str
    editor_reference: str
    validated: bool = True
    contains_text: bool = False


class LearningSession(FrozenModel):
    session_id: str
    engine_version: str
    profile_version: str
    observations_imported: tuple[str, ...]
    candidates_created: tuple[str, ...]
    preferences_promoted: tuple[str, ...]
    preferences_deprecated: tuple[str, ...]
    conflicts_detected: tuple[str, ...]
    profile_changes: tuple[str, ...]
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    readiness: LearningReadiness
    blocking_issues: tuple[str, ...] = ()
    review_issues: tuple[str, ...] = ()
    advisory_issues: tuple[str, ...] = ()
    compatibility: LearningCompatibilitySnapshot | None = None


class EditorialLanguageLearningEngine(FrozenModel):
    learning_engine_id: str
    version: str
    title: str
    project: str
    language: str
    learning_scope: str
    editor: str
    principles: tuple[str, ...]
    confidence_policy: ConfidencePolicy
    aggregation_policy: PreferenceAggregationPolicy
    candidate_policy: LearningCandidatePolicy
    promotion_policy: PreferencePromotionPolicy
    deprecation_policy: PreferenceDeprecationPolicy
    conflict_engine: ConflictEngine
    counter_evidence_policy: CounterEvidencePolicy
    lifecycle_policy: PreferenceLifecyclePolicy
    fixed_boundaries: tuple[str, ...]
    contains_generation: bool = False
    runtime_persistence: bool = False
