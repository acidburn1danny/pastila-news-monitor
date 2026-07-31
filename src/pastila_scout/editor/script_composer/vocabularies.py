"""Closed vocabularies for the Module 2.9 pure domain."""

from enum import StrEnum


class SpokenLanguageMode(StrEnum):
    NATURAL = "natural"
    CONVERSATIONAL = "conversational"
    FORMAL_SPOKEN = "formal_spoken"
    RESTRAINED = "restrained"
    EMPHATIC = "emphatic"


class TeleprompterMode(StrEnum):
    DISABLED = "disabled"
    STANDARD = "standard"
    CONVERSATIONAL = "conversational"
    PERFORMANCE = "performance"
    ACCESSIBILITY_FOCUSED = "accessibility_focused"


class VerbosityProfile(StrEnum):
    CONCISE = "concise"
    MODERATE = "moderate"
    EXPANDED = "expanded"
    DETAILED = "detailed"


class SentenceComplexity(StrEnum):
    LOW = "low"
    LOW_TO_MEDIUM = "low_to_medium"
    MEDIUM = "medium"
    MEDIUM_TO_HIGH = "medium_to_high"
    HIGH = "high"


class LengthTarget(StrEnum):
    VERY_SHORT = "very_short"
    SHORT = "short"
    MODERATE = "moderate"
    LONG = "long"
    VERY_LONG = "very_long"


class ParagraphDensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class DeliveryPacing(StrEnum):
    MEASURED = "measured"
    CONVERSATIONAL = "conversational"
    BRISK = "brisk"
    DYNAMIC = "dynamic"
    DELIBERATE = "deliberate"


class DeliverySpeedTarget(StrEnum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"
    VARIABLE = "variable"


class DensityLevel(StrEnum):
    NONE = "none"
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EditorialAggressiveness(StrEnum):
    RESTRAINED = "restrained"
    LOW = "low"
    MODERATE = "moderate"
    MEDIUM_HIGH = "medium_high"
    HIGH = "high"


class EmotionalIntensity(StrEnum):
    RESTRAINED = "restrained"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"


class Formality(StrEnum):
    INFORMAL = "informal"
    LOW = "low"
    BALANCED = "balanced"
    FORMAL = "formal"
    HIGHLY_FORMAL = "highly_formal"


class ColloquialismLevel(StrEnum):
    PROHIBITED = "prohibited"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class VocabularyAccessibility(StrEnum):
    GENERAL_PUBLIC = "general_public"
    INFORMED_GENERAL_PUBLIC = "informed_general_public"
    SPECIALIST = "specialist"
    EXPERT = "expert"


class AssumedKnowledgeLevel(StrEnum):
    MINIMAL = "minimal"
    GENERAL = "general"
    INFORMED = "informed"
    SPECIALIST = "specialist"


class RepetitionTolerance(StrEnum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PreferredOpeningStyle(StrEnum):
    DIRECT_CONTEXT = "direct_context"
    CONVERSATIONAL_HOOK = "conversational_hook"
    FACTUAL_HOOK = "factual_hook"
    RHETORICAL_HOOK = "rhetorical_hook"
    TENSION_FIRST = "tension_first"
    REFLECTIVE_OPENING = "reflective_opening"
    INHERITED = "inherited_from_composition_plan"


class PreferredClosingStyle(StrEnum):
    CONCISE_CLOSURE = "concise_closure"
    REFLECTIVE_CLOSURE = "reflective_closure"
    RHETORICAL_CLOSURE = "rhetorical_closure"
    CALLBACK_CLOSURE = "callback_closure"
    RESTRAINED_PUNCHLINE = "restrained_punchline"
    REFLECTIVE_PUNCHLINE = "reflective_punchline"
    UNRESOLVED_CLOSURE = "unresolved_closure"
    INHERITED = "inherited_from_composition_plan"


class ProviderExecutionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    MALFORMED_RESPONSE = "malformed_response"
    SCHEMA_MISMATCH = "schema_mismatch"
    LINEAGE_MISMATCH = "lineage_mismatch"
    UNKNOWN = "unknown"


class ProviderFailureReason(StrEnum):
    NONE = "none"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    MALFORMED_PAYLOAD = "malformed_payload"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    LINEAGE_VALIDATION_FAILED = "lineage_validation_failed"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    PROVIDER_INTERNAL_ERROR = "provider_internal_error"
    UNKNOWN_PROVIDER_FAILURE = "unknown_provider_failure"


class ProviderResponseValidationStatus(StrEnum):
    NOT_VALIDATED = "not_validated"
    ACCEPTED = "accepted"
    ACCEPTED_PARTIAL = "accepted_partial"
    REJECTED = "rejected"


class ProviderResponseAcceptanceStatus(StrEnum):
    ACCEPTED = "accepted"
    ACCEPTED_PARTIAL = "accepted_partial"
    REJECTED = "rejected"


class ProviderGeneratedUnitKind(StrEnum):
    SENTENCE = "sentence"
    TRANSITION = "transition"
    CALLBACK = "callback"


class RevisionAuthorityType(StrEnum):
    SYSTEM = "system"
    EDITOR = "editor"
    EDITOR_IN_CHIEF = "editor_in_chief"


class RevisionType(StrEnum):
    REGENERATION = "regeneration"
    EDITORIAL_REVISION = "editorial_revision"
    FACTUAL_CORRECTION = "factual_correction"
    LEGAL_CORRECTION = "legal_correction"
    TONAL_CORRECTION = "tonal_correction"
    DELIVERY_CORRECTION = "delivery_correction"
    FORMATTING_CORRECTION = "formatting_correction"


class RevisionScope(StrEnum):
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    BEAT = "beat"
    TRANSITION = "transition"
    CALLBACK = "callback"
    SEGMENT = "segment"
    COMPLETE_DRAFT = "complete_draft"


class RevisionExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    PARTIAL = "partial"


class DeliveryAnnotationSemanticEffect(StrEnum):
    SEMANTIC = "semantic"
    PRESENTATION_ONLY = "presentation_only"


class DraftReadiness(StrEnum):
    BLOCKED = "blocked"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    READY_FOR_EDITORIAL_REVIEW = "ready_for_editorial_review"


class FindingSeverity(StrEnum):
    ERROR = "error"
    REVIEW = "review"
    WARNING = "warning"
    ADVISORY = "advisory"


class ClaimType(StrEnum):
    FACT = "fact"
    ATTRIBUTED_CLAIM = "attributed_claim"
    ALLEGATION = "allegation"
    ESTIMATE = "estimate"
    INTERPRETATION = "interpretation"
    QUOTATION = "quotation"
    EDITORIAL_OPINION_BASIS = "editorial_opinion_basis"


class SentenceKind(StrEnum):
    FACTUAL = "factual"
    ATTRIBUTED = "attributed"
    ALLEGATION = "allegation"
    ESTIMATE = "estimate"
    INTERPRETATION = "interpretation"
    EDITORIAL_OPINION = "editorial_opinion"
    RHETORICAL_QUESTION = "rhetorical_question"
    SATIRE = "satire"
    JOKE = "joke"
    TRANSITION = "transition"
    CALLBACK = "callback"


class SatirePermissionState(StrEnum):
    PROHIBITED = "prohibited"
    RESTRICTED = "restricted"
    PERMITTED = "permitted"
    EXPLICITLY_REQUIRED = "explicitly_required"


class SatireScope(StrEnum):
    TARGET = "target"
    BEAT = "beat"
    SEGMENT = "segment"
    EPISODE = "episode"


class ConstraintSeverity(StrEnum):
    BLOCKING = "blocking"
    REVIEW = "review"
    ADVISORY = "advisory"


class CertaintyLevel(StrEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNCERTAIN = "uncertain"


class AllegationStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    ALLEGED = "alleged"
    DISPUTED = "disputed"
    ATTRIBUTED_ALLEGATION = "attributed_allegation"


class QuotationStatus(StrEnum):
    NOT_QUOTATION = "not_quotation"
    EXACT = "exact"
    INDIRECT = "indirect"


class SourceSpanUsageType(StrEnum):
    FACTUAL_SUPPORT = "factual_support"
    ATTRIBUTION = "attribution"
    QUOTATION = "quotation"
    ALLEGATION_CONTEXT = "allegation_context"
    ESTIMATE_CONTEXT = "estimate_context"
    NAME_PRESERVATION = "name_preservation"
    NUMBER_PRESERVATION = "number_preservation"
    CHRONOLOGY_SUPPORT = "chronology_support"


class ExactnessRequirement(StrEnum):
    EXACT = "exact"
    MEANING_PRESERVING = "meaning_preserving"
    CONTEXTUAL = "contextual"


class AttributionForm(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    REPORTED = "reported"
    ALLEGED = "alleged"
    ESTIMATED = "estimated"
    INSTITUTIONAL = "institutional"
    QUOTED = "quoted"


class DeliveryAnnotationType(StrEnum):
    PAUSE = "pause"
    EMPHASIS = "emphasis"
    PACE = "pace"
    PRONUNCIATION = "pronunciation"
    BREATH = "breath"
    STRESS = "stress"
    TONAL_SHIFT = "tonal_shift"
    ATTRIBUTION_PAUSE = "attribution_pause"
    PRONUNCIATION_DISAMBIGUATION = "pronunciation_disambiguation"
    INTERPRETIVE_STRESS = "interpretive_stress"
    EPISODE_ARC_TONAL_SHIFT = "episode_arc_tonal_shift"
    TELEPROMPTER_LINE_WRAP = "teleprompter_line_wrap"
    VISUAL_SPACING = "visual_spacing"
    DISPLAY_GROUPING = "display_grouping"
    SCREEN_ONLY_EMPHASIS = "screen_only_emphasis"


class TransitionRealizationType(StrEnum):
    CONTINUATION = "continuation"
    ESCALATION = "escalation"
    CONTRAST = "contrast"
    HARD_CUT = "hard_cut"
    TONE_SHIFT = "tone_shift"
    COMIC_RELIEF = "comic_relief"
    CALLBACK = "callback"


class ScriptSegmentRole(StrEnum):
    OPENING = "opening"
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    CONTRAST = "contrast"
    ESCALATION = "escalation"
    CONTEXT = "context"
    COMIC_RELIEF = "comic_relief"
    RESET = "reset"
    CLOSING = "closing"


class ScriptBeatRole(StrEnum):
    ORIENTATION = "orientation"
    FACT = "fact"
    CONTEXT = "context"
    EVIDENCE = "evidence"
    ATTRIBUTION = "attribution"
    CONSEQUENCE = "consequence"
    CONTRAST = "contrast"
    ESCALATION = "escalation"
    ABSURDITY = "absurdity"
    SATIRICAL_OPPORTUNITY = "satirical_opportunity"
    RISK_BOUNDARY = "risk_boundary"
    CALLBACK_SETUP = "callback_setup"
    CALLBACK_RESOLUTION = "callback_resolution"
    PAYOFF_POSITION = "payoff_position"
    REFLECTION = "reflection"
    CLOSURE = "closure"


class GenerationInstructionType(StrEnum):
    SEGMENT_REALIZATION = "segment_realization"
    BEAT_REALIZATION = "beat_realization"
    CLAIM_BINDING = "claim_binding"
    ATTRIBUTION = "attribution"
    TRANSITION_REALIZATION = "transition_realization"
    CALLBACK_REALIZATION = "callback_realization"
    TONE = "tone"
    DELIVERY = "delivery"


class GenerationConstraintType(StrEnum):
    FACTUAL = "factual"
    LEGAL = "legal"
    ATTRIBUTION = "attribution"
    DIGNITY = "dignity"
    SENSITIVITY = "sensitivity"
    STRUCTURE = "structure"
    ORDERING = "ordering"
    TONE = "tone"
    VOICE = "voice"
    AUDIENCE = "audience"
    LANGUAGE = "language"
    PRONUNCIATION = "pronunciation"
    DELIVERY = "delivery"
    SATIRE = "satire"
    TRANSITION = "transition"
    CALLBACK = "callback"
    STABILIZATION = "stabilization"
    REVISION = "revision"


class AuthorityLevel(StrEnum):
    FACTUAL_INTEGRITY = "factual_integrity"
    LEGAL_PRECISION = "legal_precision"
    ATTRIBUTION = "attribution"
    EDITOR_IN_CHIEF = "editor_in_chief"
    DIGNITY_SENSITIVITY = "dignity_sensitivity"
    EDITORIAL_DECISION = "editorial_decision"
    STORY_ARCHITECTURE = "story_architecture"
    COMPOSITION_PLAN = "composition_plan"
    LANGUAGE_REALIZATION = "language_realization"


class GenerationDecisionType(StrEnum):
    SEGMENT_REALIZATION = "segment_realization"
    BEAT_REALIZATION = "beat_realization"
    CLAIM_BINDING = "claim_binding"
    ATTRIBUTION = "attribution"
    TRANSITION_REALIZATION = "transition_realization"
    CALLBACK_REALIZATION = "callback_realization"
    TONE = "tone"
    DELIVERY = "delivery"
    CONFLICT_RESOLUTION = "conflict_resolution"


class ConflictResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    REQUIRES_REVIEW = "requires_review"
    BLOCKED = "blocked"


class BindingValidationStatus(StrEnum):
    NOT_VALIDATED = "not_validated"
    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"


class TextSpanBindingClassification(StrEnum):
    CLAIM = "claim"
    ATTRIBUTION = "attribution"
    QUOTATION = "quotation"
    DELIVERY = "delivery"
    EVIDENCE = "evidence"


class SourceVerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    REJECTED = "rejected"


class ProfileContradictionResult(StrEnum):
    OVERRIDDEN = "overridden"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"
    ADVISORY = "advisory"


class RevisionResultDisposition(StrEnum):
    REPLACEMENT = "replacement"
    INSPECTION_ONLY = "inspection_only"
    NONE = "none"


__all__ = tuple(
    name
    for name, value in globals().copy().items()
    if not name.startswith("_")
    and isinstance(value, type)
    and value.__module__ == __name__
)
