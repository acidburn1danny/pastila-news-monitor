"""Immutable domain contracts for the Module 2.9 pure foundation."""

import re
import unicodedata
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from pastila_scout.editor.composition.models import CompositionPlan

from .canonical import canonical_json, semantic_fingerprint
from .defaults import (
    CUSTOM_PATTERN,
    FINGERPRINT_PATTERN,
    IDENTITY_PATTERN,
    SCRIPT_COMPOSER_ID,
    SCRIPT_COMPOSER_VERSION,
    SEMVER_PATTERN,
)
from .invariants import (
    attribution_invariant_violations,
    provider_request_invariant_violations,
    provider_response_invariant_violations,
)
from .vocabularies import *


class FrozenDomainModel(BaseModel):
    """Strict immutable base for all public Module 2.9 contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_unicode(cls, value):
        return _normalize_nfc(value)

    @model_validator(mode="after")
    def validate_reference_shape(self) -> Self:
        for name, value in self.__dict__.items():
            if "reference" in name or name.endswith("_id"):
                for item in _strings(value):
                    if any(character.isspace() for character in item):
                        raise ValueError(
                            f"{name} must contain reference tokens, not prose"
                        )
        return self

    @property
    def semantic_sha256(self) -> str:
        return semantic_fingerprint(self)

    def canonical_json(self) -> str:
        return canonical_json(self)


class AuthorityReference(FrozenDomainModel):
    authority_reference_id: str = Field(min_length=1)
    authority_type: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    authority_version: str = Field(pattern=SEMVER_PATTERN)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class CustomProfileValueDefinition(FrozenDomainModel):
    custom_value: str = Field(pattern=CUSTOM_PATTERN)
    semantic_documentation_reference: str = Field(min_length=1)
    authority_references: tuple[str, ...] = Field(min_length=1)
    compatibility_version: str = Field(pattern=SEMVER_PATTERN)


class GenerationProfile(FrozenDomainModel):
    generation_profile_id: str = Field(min_length=1)
    contract_version: str = "generation-profile-v1"
    profile_version: str = Field(pattern=SEMVER_PATTERN)
    profile_name_reference: str = Field(min_length=1)
    profile_purpose_reference: str = Field(min_length=1)
    preset_identity: str | None = None
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    spoken_language_mode: SpokenLanguageMode | str
    teleprompter_mode: TeleprompterMode | str
    verbosity_profile: VerbosityProfile | str
    sentence_complexity: SentenceComplexity | str
    sentence_length_target: LengthTarget | str
    paragraph_length_target: LengthTarget | str
    paragraph_density: ParagraphDensity | str
    delivery_pacing: DeliveryPacing | str
    delivery_speed_target: DeliverySpeedTarget | str
    humor_density: DensityLevel | str
    sarcasm_density: DensityLevel | str
    irony_density: DensityLevel | str
    rhetorical_question_density: DensityLevel | str
    analogy_density: DensityLevel | str
    callback_density: DensityLevel | str
    transition_density: DensityLevel | str
    emotional_intensity: EmotionalIntensity | str
    editorial_aggressiveness: EditorialAggressiveness | str
    formality: Formality | str
    colloquialism_level: ColloquialismLevel | str
    vocabulary_accessibility: VocabularyAccessibility | str
    assumed_knowledge_level: AssumedKnowledgeLevel | str
    claim_density: DensityLevel | str
    quotation_density: DensityLevel | str
    repetition_tolerance: RepetitionTolerance | str
    preferred_opening_style: PreferredOpeningStyle | str
    preferred_closing_style: PreferredClosingStyle | str
    allowed_sentence_pattern_references: tuple[str, ...] = ()
    prohibited_sentence_pattern_references: tuple[str, ...] = ()
    style_constraint_references: tuple[str, ...] = ()
    custom_value_definitions: tuple[CustomProfileValueDefinition, ...] = ()
    audience_model_reference: str = Field(min_length=1)
    voice_reference: str = Field(min_length=1)
    spoken_communication_reference: str = Field(min_length=1)
    romanian_conversational_reference: str = Field(min_length=1)
    language_learning_guidance_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @field_validator(
        "spoken_language_mode",
        "teleprompter_mode",
        "verbosity_profile",
        "sentence_complexity",
        "sentence_length_target",
        "paragraph_length_target",
        "paragraph_density",
        "delivery_pacing",
        "delivery_speed_target",
        "humor_density",
        "sarcasm_density",
        "irony_density",
        "rhetorical_question_density",
        "analogy_density",
        "callback_density",
        "transition_density",
        "emotional_intensity",
        "editorial_aggressiveness",
        "formality",
        "colloquialism_level",
        "vocabulary_accessibility",
        "assumed_knowledge_level",
        "claim_density",
        "quotation_density",
        "repetition_tolerance",
        "preferred_opening_style",
        "preferred_closing_style",
    )
    @classmethod
    def validate_controlled_or_custom(cls, value, info: ValidationInfo):
        allowed = _PROFILE_VOCABULARIES[info.field_name]
        raw = getattr(value, "value", value)
        if raw not in {item.value for item in allowed} and not re.fullmatch(
            CUSTOM_PATTERN, raw
        ):
            raise ValueError(
                f"invalid controlled or custom value for {info.field_name}"
            )
        return value

    @model_validator(mode="after")
    def validate_custom_values(self) -> Self:
        custom_values = {
            value
            for name, value in self.__dict__.items()
            if name not in {"custom_value_definitions"}
            and isinstance(value, str)
            and value.startswith("custom:")
        }
        definitions = {item.custom_value for item in self.custom_value_definitions}
        if custom_values != definitions:
            raise ValueError("custom values require exactly one matching definition")
        if self.preset_identity is not None and self.preset_identity not in {
            "spoken_news",
            "satirical_commentary",
            "editorial_monologue",
            "explainer",
            "documentary",
            "interview",
            "debate",
            "breaking_news",
        }:
            raise ValueError("unknown preset identity")
        return self


class GenerationInstruction(FrozenDomainModel):
    generation_instruction_id: str = Field(min_length=1)
    instruction_type: GenerationInstructionType
    target_references: tuple[str, ...] = Field(min_length=1)
    authority_level: AuthorityLevel
    instruction_reference: str = Field(min_length=1)
    required: bool
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    instruction_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationConstraint(FrozenDomainModel):
    generation_constraint_id: str = Field(min_length=1)
    constraint_type: GenerationConstraintType
    target_references: tuple[str, ...] = Field(min_length=1)
    severity: ConstraintSeverity
    mandatory: bool
    constraint_reference: str = Field(min_length=1)
    prohibited_outcomes: tuple[str, ...] = ()
    source_references: tuple[str, ...] = Field(min_length=1)
    constraint_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class SatirePermission(FrozenDomainModel):
    satire_permission_id: str = Field(min_length=1)
    target_reference: str = Field(min_length=1)
    target_scope: SatireScope
    permission_state: SatirePermissionState
    permitted_forms: tuple[str, ...] = ()
    prohibited_targets: tuple[str, ...] = ()
    prohibited_implications: tuple[str, ...] = ()
    dignity_constraint_references: tuple[str, ...] = ()
    sensitivity_constraint_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    permission_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ResolvedGenerationPolicySnapshot(FrozenDomainModel):
    resolved_generation_policy_id: str = Field(min_length=1)
    contract_version: str = "resolved-generation-policy-v1"
    policy_version: str = Field(pattern=SEMVER_PATTERN)
    source_policy_reference: str = Field(min_length=1)
    source_policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    resolved_generation_instructions: tuple[GenerationInstruction, ...] = ()
    resolved_generation_constraints: tuple[GenerationConstraint, ...] = ()
    satire_permissions: tuple[SatirePermission, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    resolution_decision_references: tuple[str, ...] = ()
    policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class VerifiedTextSpan(FrozenDomainModel):
    source_span_id: str = Field(min_length=1)
    exact_text: str = Field(min_length=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, gt=0)
    language: str = Field(min_length=2)
    quotation_eligible: bool
    approved_use_categories: tuple[str, ...] = Field(min_length=1)
    span_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("source span offsets must be supplied together")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset <= self.start_offset
        ):
            raise ValueError("source span offsets must be non-empty")
        return self


class VerifiedSourceMaterial(FrozenDomainModel):
    source_material_id: str = Field(min_length=1)
    article_reference: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published_at: str | None = None
    verified_text_spans: tuple[VerifiedTextSpan, ...] = Field(min_length=1)
    verification_status: SourceVerificationStatus
    source_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ProviderNeutralExecutionMetadata(FrozenDomainModel):
    execution_policy_reference: str = Field(min_length=1)
    response_schema_reference: str = Field(min_length=1)
    capability_references: tuple[str, ...] = ()
    reproducibility_policy_reference: str = Field(min_length=1)


class ProposedClaimBinding(FrozenDomainModel):
    approved_claim_reference: str = Field(min_length=1)
    source_span_references: tuple[str, ...] = Field(min_length=1)
    generated_start_offset: int = Field(ge=0)
    generated_end_offset: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.generated_end_offset <= self.generated_start_offset:
            raise ValueError("proposed claim binding must be non-empty")
        return self


class ProposedAttributionBinding(FrozenDomainModel):
    approved_claim_reference: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    generated_start_offset: int = Field(ge=0)
    generated_end_offset: int = Field(gt=0)


class ProposedDeliveryAnnotation(FrozenDomainModel):
    annotation_type: DeliveryAnnotationType
    annotation_value_reference: str = Field(min_length=1)
    semantic_effect: DeliveryAnnotationSemanticEffect

    @model_validator(mode="after")
    def validate_effect(self) -> Self:
        _validate_delivery_effect(self.annotation_type, self.semantic_effect)
        return self


class ProviderGeneratedUnit(FrozenDomainModel):
    provider_generated_unit_id: str = Field(pattern=IDENTITY_PATTERN)
    unit_kind: ProviderGeneratedUnitKind
    target_segment_reference: str = Field(min_length=1)
    target_beat_reference: str = Field(min_length=1)
    paragraph_ordinal: int = Field(ge=1)
    sentence_ordinal: int = Field(ge=1)
    text: str = Field(min_length=1)
    proposed_claim_bindings: tuple[ProposedClaimBinding, ...] = ()
    proposed_attribution_bindings: tuple[ProposedAttributionBinding, ...] = ()
    proposed_delivery_annotations: tuple[ProposedDeliveryAnnotation, ...] = ()
    source_instruction_references: tuple[str, ...] = ()
    unit_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ProviderGenerationRequest(FrozenDomainModel):
    provider_generation_request_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "provider-generation-request-v1"
    request_version: str = Field(pattern=SEMVER_PATTERN)
    target_episode_reference: str = Field(min_length=1)
    target_segment_references: tuple[str, ...] = Field(min_length=1)
    target_beat_references: tuple[str, ...] = Field(min_length=1)
    generation_profile_reference: str = Field(min_length=1)
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    composition_plan_reference: str = Field(min_length=1)
    composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    approved_claim_references: tuple[str, ...] = ()
    source_span_references: tuple[str, ...] = ()
    generation_instruction_references: tuple[str, ...] = ()
    generation_instructions: tuple[GenerationInstruction, ...] = ()
    generation_constraint_references: tuple[str, ...] = ()
    generation_constraints: tuple[GenerationConstraint, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    output_schema_identity: str = Field(min_length=1)
    prompt_template_identity_reference: str = Field(min_length=1)
    execution_policy_reference: str = Field(min_length=1)
    provider_neutral_execution_metadata: ProviderNeutralExecutionMetadata
    request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_reference_collections(self) -> Self:
        _raise_first_invariant(provider_request_invariant_violations(self))
        return self


class ProviderPartialResponse(FrozenDomainModel):
    provider_partial_response_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "provider-partial-response-v1"
    completed_target_references: tuple[str, ...] = ()
    missing_mandatory_target_references: tuple[str, ...] = ()
    missing_optional_target_references: tuple[str, ...] = ()
    rejected_unit_references: tuple[str, ...] = ()
    rejected_unit_target_references: tuple[str, ...] = ()
    partial_reason: str = Field(min_length=1)
    recoverable: bool
    partial_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_disjoint_targets(self) -> Self:
        _require_disjoint(
            self.completed_target_references,
            self.missing_mandatory_target_references,
            self.missing_optional_target_references,
            self.rejected_unit_target_references,
            label="partial response targets",
        )
        if len(self.rejected_unit_references) != len(
            self.rejected_unit_target_references
        ):
            raise ValueError("each rejected unit requires exactly one target")
        if len(set(self.rejected_unit_references)) != len(
            self.rejected_unit_references
        ):
            raise ValueError("rejected unit references must be unique")
        return self


class ProviderExecutionReference(FrozenDomainModel):
    provider_execution_reference_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_version: str | None = None
    prompt_template_id: str = Field(min_length=1)
    prompt_template_version: str = Field(pattern=SEMVER_PATTERN)
    output_schema_version: str = Field(min_length=1)
    request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    response_fingerprint: str | None = Field(default=None, pattern=FINGERPRINT_PATTERN)
    status: ProviderExecutionStatus
    attempt_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    provider_request_id: str | None = None
    failure_reason: ProviderFailureReason = ProviderFailureReason.NONE


class ProviderGenerationResponse(FrozenDomainModel):
    provider_generation_response_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "provider-generation-response-v1"
    response_version: str = Field(pattern=SEMVER_PATTERN)
    originating_request_identity: str = Field(pattern=IDENTITY_PATTERN)
    originating_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_execution_reference: ProviderExecutionReference
    execution_status: ProviderExecutionStatus
    structured_generated_units: tuple[ProviderGeneratedUnit, ...] = ()
    partial_response: ProviderPartialResponse | None = None
    failure_reason: ProviderFailureReason = ProviderFailureReason.NONE
    response_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    validation_status: ProviderResponseValidationStatus

    @model_validator(mode="after")
    def validate_status_consistency(self) -> Self:
        _raise_first_invariant(provider_response_invariant_violations(self))
        return self


class ProviderResponseAcceptance(FrozenDomainModel):
    provider_response_acceptance_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "provider-response-acceptance-v1"
    request_reference: str = Field(pattern=IDENTITY_PATTERN)
    request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    response_reference: str = Field(pattern=IDENTITY_PATTERN)
    response_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    acceptance_status: ProviderResponseAcceptanceStatus
    accepted_unit_references: tuple[str, ...] = ()
    rejected_unit_references: tuple[str, ...] = ()
    finding_references: tuple[str, ...] = ()
    acceptance_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_units(self) -> Self:
        _require_disjoint(
            self.accepted_unit_references,
            self.rejected_unit_references,
            label="accepted and rejected units",
        )
        return self


class ApprovedClaim(FrozenDomainModel):
    approved_claim_id: str = Field(min_length=1)
    claim_type: ClaimType
    canonical_claim: str = Field(min_length=1)
    source_span_references: tuple[str, ...] = Field(min_length=1)
    attribution_requirement_reference: str | None = None
    certainty_level: CertaintyLevel
    allegation_status: AllegationStatus
    quotation_status: QuotationStatus
    legal_constraint_references: tuple[str, ...] = ()
    allowed_transformations: tuple[str, ...] = ()
    prohibited_transformations: tuple[str, ...] = ()
    claim_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class SourceSpanReference(FrozenDomainModel):
    source_span_reference_id: str = Field(min_length=1)
    source_material_reference: str = Field(min_length=1)
    source_span_id: str = Field(min_length=1)
    approved_claim_reference: str = Field(min_length=1)
    usage_type: SourceSpanUsageType
    exactness_requirement: ExactnessRequirement
    reference_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class TextSpanReference(FrozenDomainModel):
    text_span_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "text-span-reference-v1"
    parent_sentence_reference: str = Field(pattern=IDENTITY_PATTERN)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    referenced_text: str = Field(min_length=1)
    indexing_scheme: str = "unicode_code_point_v1"
    binding_classification: TextSpanBindingClassification
    span_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_span_shape(self) -> Self:
        if self.indexing_scheme != "unicode_code_point_v1":
            raise ValueError("unsupported text span indexing scheme")
        if self.end_offset <= self.start_offset:
            raise ValueError("text span must be non-empty and half-open")
        return self


class GeneratedClaimReference(FrozenDomainModel):
    generated_claim_reference_id: str = Field(min_length=1)
    script_sentence_reference: str = Field(pattern=IDENTITY_PATTERN)
    claim_classification: ClaimType
    text_span_reference: TextSpanReference
    approved_claim_references: tuple[str, ...] = Field(min_length=1)
    source_span_references: tuple[str, ...] = Field(min_length=1)
    certainty_preserved: bool
    attribution_preserved: bool
    quotation_exact: bool
    causation_authorized: bool
    validation_status: BindingValidationStatus
    claim_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_parent(self) -> Self:
        if (
            self.text_span_reference.parent_sentence_reference
            != self.script_sentence_reference
        ):
            raise ValueError("claim text span belongs to a different sentence")
        return self


class AttributionRealization(FrozenDomainModel):
    attribution_realization_id: str = Field(min_length=1)
    script_sentence_reference: str = Field(pattern=IDENTITY_PATTERN)
    approved_claim_reference: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    required_attribution_reference: str = Field(min_length=1)
    text_span_reference: TextSpanReference
    attribution_form: AttributionForm
    attribution_preserved: bool
    attribution_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_parent(self) -> Self:
        _raise_first_invariant(attribution_invariant_violations(self))
        return self


class DeliveryAnnotation(FrozenDomainModel):
    delivery_annotation_id: str = Field(min_length=1)
    target_text_reference: str = Field(min_length=1)
    annotation_type: DeliveryAnnotationType
    annotation_value_reference: str = Field(min_length=1)
    source_guidance_references: tuple[str, ...] = Field(min_length=1)
    semantic_effect: DeliveryAnnotationSemanticEffect
    annotation_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_effect(self) -> Self:
        _validate_delivery_effect(self.annotation_type, self.semantic_effect)
        return self


class GenerationDecision(FrozenDomainModel):
    generation_decision_id: str = Field(min_length=1)
    target_references: tuple[str, ...] = Field(min_length=1)
    decision_type: GenerationDecisionType
    selected_option_reference: str = Field(min_length=1)
    rejected_option_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = Field(min_length=1)
    constraint_references: tuple[str, ...] = ()
    reason_code: str = Field(min_length=1)
    provider_response_reference: str | None = None
    decision_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationConflict(FrozenDomainModel):
    generation_conflict_id: str = Field(min_length=1)
    target_references: tuple[str, ...] = Field(min_length=1)
    conflicting_rule_references: tuple[str, ...] = Field(min_length=2)
    precedence_order: tuple[str, ...] = Field(min_length=2)
    winning_rule_reference: str = Field(min_length=1)
    rejected_rule_references: tuple[str, ...] = Field(min_length=1)
    resolution_status: ConflictResolutionStatus
    readiness_impact: DraftReadiness
    reason_code: str = Field(min_length=1)
    conflict_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ProfileContradictionTrace(FrozenDomainModel):
    contradiction_trace_id: str = Field(min_length=1)
    profile_field_reference: str = Field(min_length=1)
    profile_preference_reference: str = Field(min_length=1)
    winning_authority_reference: str = Field(min_length=1)
    winning_rule_reference: str = Field(min_length=1)
    validation_result: ProfileContradictionResult
    readiness_impact: DraftReadiness
    target_references: tuple[str, ...] = Field(min_length=1)
    reason_code: str = Field(min_length=1)


class GenerationTraceEntry(FrozenDomainModel):
    generation_trace_entry_id: str = Field(min_length=1)
    output_reference: str = Field(min_length=1)
    parent_output_reference: str | None = None
    composition_plan_references: tuple[str, ...] = Field(min_length=1)
    approved_claim_references: tuple[str, ...] = ()
    source_span_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    guidance_references: tuple[str, ...] = ()
    generation_decision_references: tuple[str, ...] = ()
    provider_execution_reference: str = Field(min_length=1)
    trace_entry_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GenerationTraceability(FrozenDomainModel):
    generation_traceability_id: str = Field(min_length=1)
    entries: tuple[GenerationTraceEntry, ...] = Field(min_length=1)
    traceability_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class DraftValidationFinding(FrozenDomainModel):
    finding_id: str = Field(min_length=1)
    finding_code: str = Field(min_length=1)
    severity: FindingSeverity
    artifact_reference: str = Field(min_length=1)
    field_reference: str | None = None
    related_references: tuple[str, ...] = ()
    message_reference: str = Field(min_length=1)
    blocking: bool
    editor_review_required: bool


class ScriptSentence(FrozenDomainModel):
    script_sentence_id: str = Field(pattern=IDENTITY_PATTERN)
    script_paragraph_reference: str = Field(pattern=IDENTITY_PATTERN)
    sentence_position: int = Field(ge=1)
    text: str = Field(min_length=1)
    sentence_kind: SentenceKind
    generated_claim_references: tuple[GeneratedClaimReference, ...] = ()
    source_span_references: tuple[str, ...] = ()
    attribution_realization_references: tuple[str, ...] = ()
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    generation_decision_references: tuple[str, ...] = ()
    generation_trace_references: tuple[str, ...] = Field(min_length=1)
    sentence_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True

    @model_validator(mode="after")
    def enforce_generated_language(self) -> Self:
        if not self.contains_generated_language:
            raise ValueError("script sentence must own generated language")
        return self


class ScriptParagraph(FrozenDomainModel):
    script_paragraph_id: str = Field(pattern=IDENTITY_PATTERN)
    script_beat_reference: str = Field(pattern=IDENTITY_PATTERN)
    paragraph_position: int = Field(ge=1)
    ordered_sentence_ids: tuple[str, ...] = Field(min_length=1)
    sentences: tuple[ScriptSentence, ...] = Field(min_length=1)
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    paragraph_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True

    @model_validator(mode="after")
    def validate_sentences(self) -> Self:
        _validate_ordered_children(
            self.ordered_sentence_ids,
            self.sentences,
            "script_sentence_id",
            "sentence_position",
            "sentences",
        )
        return self


class ScriptBeat(FrozenDomainModel):
    script_beat_id: str = Field(pattern=IDENTITY_PATTERN)
    script_segment_reference: str = Field(pattern=IDENTITY_PATTERN)
    composition_beat_reference: str = Field(min_length=1)
    beat_position: int = Field(ge=1)
    beat_role: ScriptBeatRole
    ordered_paragraph_ids: tuple[str, ...] = Field(min_length=1)
    paragraphs: tuple[ScriptParagraph, ...] = Field(min_length=1)
    approved_claim_references: tuple[str, ...] = ()
    source_span_references: tuple[str, ...] = ()
    attribution_references: tuple[str, ...] = ()
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    generation_decision_references: tuple[str, ...] = ()
    generation_trace_references: tuple[str, ...] = Field(min_length=1)
    beat_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True

    @model_validator(mode="after")
    def validate_paragraphs(self) -> Self:
        _validate_ordered_children(
            self.ordered_paragraph_ids,
            self.paragraphs,
            "script_paragraph_id",
            "paragraph_position",
            "paragraphs",
        )
        return self


class ScriptSegment(FrozenDomainModel):
    script_segment_id: str = Field(pattern=IDENTITY_PATTERN)
    composition_segment_reference: str = Field(min_length=1)
    event_reference: str = Field(min_length=1)
    story_reference: str = Field(min_length=1)
    position: int = Field(ge=1)
    segment_role: ScriptSegmentRole
    episode_arc_step_references: tuple[str, ...] = Field(min_length=1)
    ordered_script_beat_ids: tuple[str, ...] = Field(min_length=1)
    script_beats: tuple[ScriptBeat, ...] = Field(min_length=1)
    transition_in_reference: str | None = None
    transition_out_reference: str | None = None
    callback_references: tuple[str, ...] = ()
    attribution_references: tuple[str, ...] = ()
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    generation_decision_references: tuple[str, ...] = ()
    generation_trace_references: tuple[str, ...] = Field(min_length=1)
    segment_validation_findings: tuple[DraftValidationFinding, ...] = ()
    segment_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True

    @model_validator(mode="after")
    def validate_beats(self) -> Self:
        _validate_ordered_children(
            self.ordered_script_beat_ids,
            self.script_beats,
            "script_beat_id",
            "beat_position",
            "beats",
        )
        return self


class Transition(FrozenDomainModel):
    transition_realization_id: str = Field(min_length=1)
    transition_plan_reference: str = Field(min_length=1)
    from_script_segment_reference: str = Field(pattern=IDENTITY_PATTERN)
    to_script_segment_reference: str = Field(pattern=IDENTITY_PATTERN)
    transition_type: TransitionRealizationType
    text: str = Field(min_length=1)
    generated_claim_references: tuple[str, ...] = ()
    source_span_references: tuple[str, ...] = ()
    causal_restrictions_preserved: bool
    tone_restrictions_preserved: bool
    sensitivity_restrictions_preserved: bool
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    generation_trace_references: tuple[str, ...] = Field(min_length=1)
    transition_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True


class Callback(FrozenDomainModel):
    callback_realization_id: str = Field(min_length=1)
    callback_plan_reference: str = Field(min_length=1)
    setup_script_reference: str = Field(min_length=1)
    resolution_script_reference: str = Field(min_length=1)
    shared_context_references: tuple[str, ...] = Field(min_length=1)
    factual_continuity_references: tuple[str, ...] = Field(min_length=1)
    text: str = Field(min_length=1)
    tone_restrictions_preserved: bool
    sensitivity_restrictions_preserved: bool
    generation_trace_references: tuple[str, ...] = Field(min_length=1)
    callback_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True


class ScriptCompositionInputBundle(FrozenDomainModel):
    input_bundle_id: str = Field(min_length=1)
    contract_version: str = "script-composition-input-v1"
    module_id: str = SCRIPT_COMPOSER_ID
    module_version: str = SCRIPT_COMPOSER_VERSION
    episode_reference: str = Field(min_length=1)
    composition_plan: CompositionPlan
    composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    verified_sources: tuple[VerifiedSourceMaterial, ...] = Field(min_length=1)
    approved_claims: tuple[ApprovedClaim, ...] = Field(min_length=1)
    attribution_constraints: tuple[GenerationConstraint, ...] = ()
    legal_constraints: tuple[GenerationConstraint, ...] = ()
    dignity_constraints: tuple[GenerationConstraint, ...] = ()
    sensitivity_constraints: tuple[GenerationConstraint, ...] = ()
    memory_references: tuple[str, ...] = ()
    persona_reference: str = Field(min_length=1)
    philosophy_reference: str = Field(min_length=1)
    decision_framework_reference: str = Field(min_length=1)
    voice_reference: str = Field(min_length=1)
    audience_model_reference: str = Field(min_length=1)
    story_architecture_reference: str = Field(min_length=1)
    spoken_communication_reference: str = Field(min_length=1)
    romanian_conversational_reference: str = Field(min_length=1)
    language_learning_guidance_references: tuple[str, ...] = ()
    editor_in_chief_decision_references: tuple[str, ...] = ()
    generation_profile: GenerationProfile
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    resolved_generation_policy: ResolvedGenerationPolicySnapshot
    resolved_generation_policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_configuration_reference: str = Field(min_length=1)
    generation_policy_reference: str = Field(min_length=1)
    upstream_dependency_references: tuple[str, ...] = Field(min_length=1)
    input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_compatibility_references(self) -> Self:
        if self.episode_reference != self.composition_plan.episode_reference:
            raise ValueError("composition plan episode does not match input bundle")
        if (
            self.generation_profile.audience_model_reference
            != self.audience_model_reference
        ):
            raise ValueError("generation profile audience reference mismatch")
        if self.generation_profile.voice_reference != self.voice_reference:
            raise ValueError("generation profile voice reference mismatch")
        if (
            self.generation_profile.spoken_communication_reference
            != self.spoken_communication_reference
        ):
            raise ValueError("generation profile spoken communication mismatch")
        if (
            self.generation_profile.romanian_conversational_reference
            != self.romanian_conversational_reference
        ):
            raise ValueError("generation profile Romanian conversational mismatch")
        return self


class ScriptDraft(FrozenDomainModel):
    script_draft_id: str = Field(min_length=1)
    contract_version: str = "editorial-script-composer-v1"
    module_id: str = SCRIPT_COMPOSER_ID
    module_version: str = SCRIPT_COMPOSER_VERSION
    draft_version: str = Field(pattern=SEMVER_PATTERN)
    input_bundle_reference: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    composition_plan_reference: str = Field(min_length=1)
    composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    episode_reference: str = Field(min_length=1)
    applied_generation_profile_reference: str = Field(min_length=1)
    applied_generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    resolved_generation_policy_reference: str = Field(min_length=1)
    resolved_generation_policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    ordered_script_segment_ids: tuple[str, ...] = Field(min_length=1)
    script_segments: tuple[ScriptSegment, ...] = Field(min_length=1)
    transition_realizations: tuple[Transition, ...] = ()
    callback_realizations: tuple[Callback, ...] = ()
    generated_claim_references: tuple[GeneratedClaimReference, ...] = ()
    attribution_realizations: tuple[AttributionRealization, ...] = ()
    delivery_annotations: tuple[DeliveryAnnotation, ...] = ()
    generation_traceability: GenerationTraceability
    generation_decisions: tuple[GenerationDecision, ...] = ()
    generation_conflicts: tuple[GenerationConflict, ...] = ()
    unresolved_generation_constraints: tuple[GenerationConstraint, ...] = ()
    validation_findings: tuple[DraftValidationFinding, ...] = ()
    draft_readiness: DraftReadiness
    provider_execution_reference: ProviderExecutionReference
    previous_draft_reference: str | None = None
    previous_draft_fingerprint: str | None = Field(
        default=None, pattern=FINGERPRINT_PATTERN
    )
    revision_request_reference: str | None = None
    script_draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = True

    @model_validator(mode="after")
    def validate_segments(self) -> Self:
        _validate_ordered_children(
            self.ordered_script_segment_ids,
            self.script_segments,
            "script_segment_id",
            "position",
            "segments",
        )
        if not self.contains_generated_language:
            raise ValueError("script draft must contain generated language")
        if (self.previous_draft_reference is None) != (
            self.previous_draft_fingerprint is None
        ):
            raise ValueError("previous draft reference and fingerprint must be paired")
        blocked = (
            self.provider_execution_reference.status != ProviderExecutionStatus.SUCCESS
            or any(item.blocking for item in self.validation_findings)
            or any(
                item.readiness_impact == DraftReadiness.BLOCKED
                for item in self.generation_conflicts
            )
        )
        requires_review = any(
            item.editor_review_required for item in self.validation_findings
        ) or any(
            item.readiness_impact == DraftReadiness.REQUIRES_EDITOR_REVIEW
            for item in self.generation_conflicts
        )
        if blocked and self.draft_readiness != DraftReadiness.BLOCKED:
            raise ValueError("blocked upstream or validation status must propagate")
        if (
            not blocked
            and requires_review
            and self.draft_readiness != DraftReadiness.REQUIRES_EDITOR_REVIEW
        ):
            raise ValueError("editor review state must propagate")
        return self


class RevisionAuthority(FrozenDomainModel):
    revision_authority_id: str = Field(min_length=1)
    contract_version: str = "revision-authority-v1"
    authority_type: RevisionAuthorityType
    authority_reference: str = Field(min_length=1)
    authority_version: str = Field(pattern=SEMVER_PATTERN)
    authorized_revision_types: tuple[RevisionType, ...] = Field(min_length=1)
    authority_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_compatibility(self) -> Self:
        allowed = revision_types_for_authority(self.authority_type)
        if not set(self.authorized_revision_types).issubset(allowed):
            raise ValueError("authority declares incompatible revision types")
        return self


class RevisionAuthorityInputSnapshot(FrozenDomainModel):
    """Immutable semantic authority inputs used to authorize a revision."""

    composition_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    approved_claims_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    source_evidence_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    generation_profile_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    resolved_policy_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    satire_permissions_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    authority_references_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    generation_instructions_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    generation_constraints_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    structure_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    target_scope_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class RevisionRequest(FrozenDomainModel):
    revision_request_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "revision-request-v1"
    prior_script_draft_reference: str = Field(min_length=1)
    prior_script_draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    revision_scope: RevisionScope
    target_references: tuple[str, ...] = Field(min_length=1)
    revision_type: RevisionType
    requested_change_reference: str = Field(min_length=1)
    revision_reason_reference: str = Field(min_length=1)
    revision_authority: RevisionAuthority
    preserved_constraint_references: tuple[str, ...] = Field(min_length=1)
    immutable_upstream_references: tuple[str, ...] = Field(min_length=1)
    expected_readiness_impact: DraftReadiness
    updated_approved_evidence_references: tuple[str, ...] = ()
    updated_authoritative_legal_constraint_references: tuple[str, ...] = ()
    prior_authority_inputs: RevisionAuthorityInputSnapshot
    requested_authority_inputs: RevisionAuthorityInputSnapshot
    request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_authority(self) -> Self:
        if self.revision_type not in self.revision_authority.authorized_revision_types:
            raise ValueError("revision authority does not authorize requested type")
        if (
            self.revision_type == RevisionType.FACTUAL_CORRECTION
            and not self.updated_approved_evidence_references
        ):
            raise ValueError("factual corrections require approved evidence")
        if (
            self.revision_type == RevisionType.LEGAL_CORRECTION
            and not self.updated_authoritative_legal_constraint_references
        ):
            raise ValueError(
                "legal corrections require authoritative legal constraints"
            )
        if (
            self.revision_authority.authority_type == RevisionAuthorityType.SYSTEM
            and self.revision_type == RevisionType.REGENERATION
        ):
            if self.prior_authority_inputs != self.requested_authority_inputs:
                raise ValueError("system regeneration cannot change authority inputs")
            expected_scope = revision_target_scope_fingerprint(
                self.revision_scope, self.target_references
            )
            if (
                self.requested_authority_inputs.target_scope_fingerprint
                != expected_scope
            ):
                raise ValueError("system regeneration target scope mismatch")
        return self


class TextualUnitLineage(FrozenDomainModel):
    textual_unit_reference: str = Field(min_length=1)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    lineage_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class RevisionExecutionResult(FrozenDomainModel):
    revision_execution_result_id: str = Field(pattern=IDENTITY_PATTERN)
    contract_version: str = "revision-execution-result-v1"
    result_version: str = Field(pattern=SEMVER_PATTERN)
    revision_request_reference: str = Field(pattern=IDENTITY_PATTERN)
    revision_request_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    prior_draft_reference: str = Field(min_length=1)
    prior_draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    resulting_draft_reference: str | None = None
    resulting_draft_fingerprint: str | None = Field(
        default=None, pattern=FINGERPRINT_PATTERN
    )
    changed_textual_units: tuple[TextualUnitLineage, ...] = ()
    preserved_textual_units: tuple[TextualUnitLineage, ...] = ()
    removed_textual_units: tuple[TextualUnitLineage, ...] = ()
    new_textual_units: tuple[TextualUnitLineage, ...] = ()
    provider_execution_references: tuple[str, ...] = ()
    validation_findings: tuple[DraftValidationFinding, ...] = ()
    readiness: DraftReadiness
    execution_status: RevisionExecutionStatus
    resulting_draft_disposition: RevisionResultDisposition = (
        RevisionResultDisposition.NONE
    )
    result_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)

    @model_validator(mode="after")
    def validate_lineage_sets(self) -> Self:
        collections = (
            self.changed_textual_units,
            self.preserved_textual_units,
            self.removed_textual_units,
            self.new_textual_units,
        )
        _require_disjoint(
            *(
                tuple(item.textual_unit_reference for item in group)
                for group in collections
            ),
            label="revision lineage sets",
        )
        has_result = self.resulting_draft_reference is not None
        if has_result != (self.resulting_draft_fingerprint is not None):
            raise ValueError("resulting draft reference and fingerprint must be paired")
        if (
            self.execution_status
            in {
                RevisionExecutionStatus.FAILED,
                RevisionExecutionStatus.REJECTED,
            }
            and has_result
        ):
            raise ValueError("failed or rejected revision cannot expose a result draft")
        expected = {
            RevisionExecutionStatus.SUCCESS: RevisionResultDisposition.REPLACEMENT,
            RevisionExecutionStatus.PARTIAL: RevisionResultDisposition.INSPECTION_ONLY,
            RevisionExecutionStatus.FAILED: RevisionResultDisposition.NONE,
            RevisionExecutionStatus.REJECTED: RevisionResultDisposition.NONE,
        }[self.execution_status]
        if self.resulting_draft_disposition != expected:
            raise ValueError(
                "revision result disposition does not match execution status"
            )
        if self.execution_status == RevisionExecutionStatus.SUCCESS and not has_result:
            raise ValueError("successful revision requires a resulting draft")
        return self


def revision_types_for_authority(
    authority_type: RevisionAuthorityType,
) -> frozenset[RevisionType]:
    """Return the frozen compatibility matrix for a revision authority."""
    if authority_type == RevisionAuthorityType.SYSTEM:
        return frozenset(
            {
                RevisionType.REGENERATION,
                RevisionType.DELIVERY_CORRECTION,
                RevisionType.FORMATTING_CORRECTION,
            }
        )
    return frozenset(RevisionType)


def revision_target_scope_fingerprint(
    revision_scope: RevisionScope,
    target_references: tuple[str, ...],
) -> str:
    """Fingerprint the immutable scope and targets authorized for revision."""
    return semantic_fingerprint(
        {"revision_scope": revision_scope, "target_references": target_references}
    )


def _validate_ordered_children(
    ordered_ids: tuple[str, ...],
    children: tuple[FrozenDomainModel, ...],
    id_field: str,
    position_field: str,
    label: str,
) -> None:
    identities = tuple(getattr(item, id_field) for item in children)
    positions = tuple(getattr(item, position_field) for item in children)
    if identities != ordered_ids:
        raise ValueError(f"ordered {label} do not match child identities")
    if positions != tuple(range(1, len(children) + 1)):
        raise ValueError(f"{label} positions must be unique and contiguous")


def _require_disjoint(*collections: tuple[str, ...], label: str) -> None:
    seen: set[str] = set()
    for collection in collections:
        current = set(collection)
        if len(current) != len(collection) or seen & current:
            raise ValueError(f"{label} must be unique and mutually disjoint")
        seen.update(current)


def _raise_first_invariant(violations) -> None:
    if violations:
        violation = violations[0]
        raise PydanticCustomError(violation.code, violation.code)


_SEMANTIC_DELIVERY_TYPES = frozenset(
    {
        DeliveryAnnotationType.PAUSE,
        DeliveryAnnotationType.EMPHASIS,
        DeliveryAnnotationType.PACE,
        DeliveryAnnotationType.PRONUNCIATION,
        DeliveryAnnotationType.BREATH,
        DeliveryAnnotationType.STRESS,
        DeliveryAnnotationType.TONAL_SHIFT,
        DeliveryAnnotationType.ATTRIBUTION_PAUSE,
        DeliveryAnnotationType.PRONUNCIATION_DISAMBIGUATION,
        DeliveryAnnotationType.INTERPRETIVE_STRESS,
        DeliveryAnnotationType.EPISODE_ARC_TONAL_SHIFT,
    }
)


def _validate_delivery_effect(
    annotation_type: DeliveryAnnotationType,
    semantic_effect: DeliveryAnnotationSemanticEffect,
) -> None:
    expected = (
        DeliveryAnnotationSemanticEffect.SEMANTIC
        if annotation_type in _SEMANTIC_DELIVERY_TYPES
        else DeliveryAnnotationSemanticEffect.PRESENTATION_ONLY
    )
    if semantic_effect != expected:
        raise ValueError(
            "delivery annotation type and semantic effect are inconsistent"
        )


def _normalize_nfc(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return tuple(_normalize_nfc(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_normalize_nfc(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted((_normalize_nfc(item) for item in value), key=repr))
    if isinstance(value, dict):
        return {key: _normalize_nfc(item) for key, item in value.items()}
    return value


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, BaseModel):
        for item in value.__dict__.values():
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from _strings(item)


_PROFILE_VOCABULARIES = {
    "spoken_language_mode": SpokenLanguageMode,
    "teleprompter_mode": TeleprompterMode,
    "verbosity_profile": VerbosityProfile,
    "sentence_complexity": SentenceComplexity,
    "sentence_length_target": LengthTarget,
    "paragraph_length_target": LengthTarget,
    "paragraph_density": ParagraphDensity,
    "delivery_pacing": DeliveryPacing,
    "delivery_speed_target": DeliverySpeedTarget,
    "humor_density": DensityLevel,
    "sarcasm_density": DensityLevel,
    "irony_density": DensityLevel,
    "rhetorical_question_density": DensityLevel,
    "analogy_density": DensityLevel,
    "callback_density": DensityLevel,
    "transition_density": DensityLevel,
    "emotional_intensity": EmotionalIntensity,
    "editorial_aggressiveness": EditorialAggressiveness,
    "formality": Formality,
    "colloquialism_level": ColloquialismLevel,
    "vocabulary_accessibility": VocabularyAccessibility,
    "assumed_knowledge_level": AssumedKnowledgeLevel,
    "claim_density": DensityLevel,
    "quotation_density": DensityLevel,
    "repetition_tolerance": RepetitionTolerance,
    "preferred_opening_style": PreferredOpeningStyle,
    "preferred_closing_style": PreferredClosingStyle,
}


TransitionRealization = Transition
CallbackRealization = Callback

__all__ = tuple(
    name
    for name, value in globals().copy().items()
    if not name.startswith("_")
    and isinstance(value, type)
    and value.__module__ == __name__
) + (
    "CallbackRealization",
    "TransitionRealization",
    "revision_target_scope_fingerprint",
    "revision_types_for_authority",
)
