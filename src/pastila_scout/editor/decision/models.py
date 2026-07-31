"""Immutable contracts for evidence-linked pre-writing editorial decisions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MaterialType(StrEnum):
    FACT = "fact"
    QUOTE = "quote"
    CONTEXT = "context"
    CHRONOLOGY = "chronology"
    ALLEGATION = "allegation"
    RESPONSE = "response"
    STATISTIC = "statistic"
    LEGAL_INSTITUTIONAL_DETAIL = "legal_or_institutional_detail"
    HUMAN_CONSEQUENCE = "human_consequence"
    PUBLIC_CONSEQUENCE = "public_consequence"
    CONTRADICTION = "contradiction"
    UNCERTAINTY = "uncertainty"
    SATIRE_OPPORTUNITY = "satire_opportunity"
    TRANSITION_CANDIDATE = "transition_candidate"
    DUPLICATE_REDUNDANT = "duplicate_or_redundant_material"


class FactualStatus(StrEnum):
    VERIFIED_FACT = "verified_fact"
    ATTRIBUTED_CLAIM = "attributed_claim"
    ALLEGATION = "allegation"
    DISPUTED_CLAIM = "disputed_claim"
    OPINION = "opinion"
    UNKNOWN_UNRESOLVED = "unknown_or_unresolved"


class Sensitivity(StrEnum):
    NONE = "none"
    PERSONAL = "personal"
    VULNERABLE_PERSON = "vulnerable_person"
    VICTIM = "victim"
    LEGALLY_SENSITIVE = "legally_sensitive"


class FactImportance(StrEnum):
    INDISPENSABLE = "indispensable"
    IMPORTANT = "important"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"
    REDUNDANT = "redundant"
    DISTRACTING = "distracting"
    UNSAFE_WITHOUT_CONTEXT = "unsafe_without_context"
    UNRESOLVED = "unresolved"


class EditorialAction(StrEnum):
    PRESERVE = "preserve"
    EMPHASIZE = "emphasize"
    LEAD_WITH = "lead_with"
    INTRODUCE_EARLY = "introduce_early"
    DELAY = "delay"
    COMPRESS = "compress"
    COMBINE = "combine"
    CONTEXTUALIZE = "contextualize"
    ATTRIBUTE_EXPLICITLY = "attribute_explicitly"
    QUALIFY = "qualify"
    CONTRAST = "contrast"
    RELOCATE = "relocate"
    REMOVE = "remove"
    HOLD_FOR_VERIFICATION = "hold_for_verification"
    ESCALATE_TO_EDITOR_IN_CHIEF = "escalate_to_editor_in_chief"
    NO_ACTION = "no_action"


class DecisionConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionStage(StrEnum):
    FACTUAL_SAFETY = "factual_safety"
    EDITORIAL_CORE = "editorial_core"
    INDISPENSABLE_FACTS = "indispensable_facts"
    CONSEQUENCE = "public_and_human_consequence"
    CLARITY_CONTEXT = "clarity_and_context"
    STRUCTURE_PACING = "structure_and_pacing"
    EMPHASIS = "emphasis"
    COMPRESSION = "compression"
    REMOVAL = "removal"
    UNRESOLVED_RISKS = "unresolved_risks"


class RiskType(StrEnum):
    FACTUAL_DISTORTION = "factual_distortion"
    MISLEADING_OMISSION = "misleading_omission"
    UNSUPPORTED_INFERENCE = "unsupported_inference"
    ALLEGATION_AS_FACT = "allegation_presented_as_fact"
    QUOTE_MUTATION = "quote_mutation"
    CHRONOLOGY_DISTORTION = "chronology_distortion"
    VICTIM_HARM = "victim_harm"
    PRIVACY_EXPOSURE = "privacy_exposure"
    TONAL_INSENSITIVITY = "tonal_insensitivity"
    SENSATIONALISM = "sensationalism"
    OVER_EXPLANATION = "over_explanation"
    WEAK_EDITORIAL_CORE = "weak_editorial_core"
    PACING_LOSS = "pacing_loss"
    SOURCE_CONFLICT = "source_conflict"
    MISSING_RESPONSE = "missing_response"
    MISSING_ATTRIBUTION = "missing_attribution"
    INSUFFICIENT_VERIFICATION = "insufficient_verification"
    PROFILE_PERSONA_CONFLICT = "profile_persona_conflict"


class RiskSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProductionReadiness(StrEnum):
    READY = "ready"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    BLOCKED = "blocked"


class MaterialMetadata(FrozenModel):
    key: str = Field(min_length=1)
    value: str = Field(min_length=1)


class EditorialMaterial(FrozenModel):
    material_id: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    material_type: MaterialType
    content: str = Field(min_length=1)
    factual_status: FactualStatus
    attribution: str | None = None
    chronology_position: int | None = Field(default=None, ge=0)
    related_material_ids: tuple[str, ...] = ()
    sensitivity: Sensitivity = Sensitivity.NONE
    metadata: tuple[MaterialMetadata, ...] = ()
    transformation_evidence: tuple[str, ...] = ()


class CoreElement(FrozenModel):
    statement: str = Field(min_length=1)
    material_ids: tuple[str, ...] = Field(min_length=1)


class EditorialCore(FrozenModel):
    what_happened: CoreElement
    involved_parties: CoreElement
    why_it_matters: CoreElement
    consequence: CoreElement
    central_tension: CoreElement
    factual_boundaries: tuple[CoreElement, ...] = Field(min_length=1)
    unresolved_questions: tuple[str, ...] = ()
    secondary_angles: tuple[CoreElement, ...] = ()


class EditorialDecision(FrozenModel):
    decision_id: str = Field(min_length=1)
    stage: DecisionStage
    rank: int = Field(gt=0)
    material_ids: tuple[str, ...] = Field(min_length=1)
    classification: FactImportance
    action: EditorialAction
    rationale: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    principle_ids: tuple[str, ...] = Field(min_length=1)
    tension_ids: tuple[str, ...] = ()
    confidence: DecisionConfidence
    consequence_if_ignored: str = Field(min_length=1)
    unresolved_dependencies: tuple[str, ...] = ()
    requires_editor_in_chief_review: bool = False
    preserves_attribution: bool = True
    merges_contradictory_claims: bool = False
    mutates_quote: bool = False
    infers_unsupported_motive: bool = False
    infers_unsupported_causality: bool = False
    silently_removes_uncertainty: bool = False
    factual_distortion_purpose: str | None = None


class EditorialRisk(FrozenModel):
    risk_id: str = Field(min_length=1)
    risk_type: RiskType
    severity: RiskSeverity
    affected_material_ids: tuple[str, ...] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    blocking: bool
    requires_editor_in_chief_review: bool


class EditorialDecisionPlan(FrozenModel):
    artifact_kind: str = "editorial_decision_plan"
    plan_id: str = Field(min_length=1)
    version: str
    persona_id: str
    persona_version: str
    philosophy_id: str
    philosophy_version: str
    source_material_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_material: tuple[EditorialMaterial, ...] = Field(min_length=1)
    editorial_core: EditorialCore
    decisions: tuple[EditorialDecision, ...] = Field(min_length=1)
    risks: tuple[EditorialRisk, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    blocking_issues: tuple[str, ...] = ()
    advisory_issues: tuple[str, ...] = ()
    requires_editor_in_chief_review: bool
    production_readiness: ProductionReadiness
    summary: str = Field(min_length=1)
    contains_generated_prose: bool = False
    mutates_editorial_memory: bool = False
