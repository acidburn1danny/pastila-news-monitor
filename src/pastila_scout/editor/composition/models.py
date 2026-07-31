"""Immutable contracts for deterministic editorial composition planning."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
CUSTOM_PATTERN = r"^custom:[a-z0-9]+(?:-[a-z0-9]+)*$"


class FrozenModel(BaseModel):
    """Strict immutable composition contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)

    @model_validator(mode="after")
    def reject_generated_language_and_prose(self):
        """Enforce reference-only strings at the persistent contract boundary."""
        if getattr(self, "contains_generated_language", False):
            raise ValueError("generated language is forbidden")
        for name, value in self.__dict__.items():
            if name.endswith("fingerprint"):
                continue
            if any(
                any(character.isspace() for character in item)
                for item in _strings(value)
            ):
                raise ValueError(f"{name} must be a reference or controlled token")
        return self

    @property
    def canonical_identifier(self) -> str:
        for name in self.__class__.model_fields:
            if name.endswith("_id") and (value := getattr(self, name, None)):
                return str(value)
        return self.__class__.__name__

    @property
    def semantic_sha256(self) -> str:
        from .fingerprint import artifact_fingerprint

        return artifact_fingerprint(self)

    def render(self) -> str:
        from .render import render_artifact

        return render_artifact(self)


class CompositionReadiness(StrEnum):
    BLOCKED = "blocked"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"
    READY_WITH_ADVISORIES = "ready_with_advisories"
    READY = "ready"


class FindingSeverity(StrEnum):
    ERROR = "error"
    REVIEW = "review"
    WARNING = "warning"
    ADVISORY = "advisory"


class SegmentRole(StrEnum):
    OPENING = "opening"
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    CONTRAST = "contrast"
    ESCALATION = "escalation"
    CONTEXT = "context"
    COMIC_RELIEF = "comic_relief"
    RESET = "reset"
    CLOSING = "closing"


class BeatType(StrEnum):
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


class TransitionType(StrEnum):
    CONTINUATION = "continuation"
    ESCALATION = "escalation"
    CONTRAST = "contrast"
    HARD_CUT = "hard_cut"
    TONE_SHIFT = "tone_shift"
    COMIC_RELIEF = "comic_relief"
    CALLBACK = "callback"


class ArcFunction(StrEnum):
    ORIENTATION = "orientation"
    BUILD = "build"
    ESCALATION = "escalation"
    PEAK = "peak"
    STABILIZATION = "stabilization"
    RELIEF = "relief"
    RESET = "reset"
    REFLECTION = "reflection"
    RESOLUTION = "resolution"
    CLOSURE = "closure"


class ArcIntensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    PEAK = "peak"


class PriorityLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EmphasisLevel(StrEnum):
    CRITICAL = "critical"
    STRONG = "strong"
    NORMAL = "normal"
    LIGHT = "light"
    DEEMPHASIZED = "deemphasized"


class Pace(StrEnum):
    SLOW = "slow"
    MEASURED = "measured"
    MODERATE = "moderate"
    BRISK = "brisk"
    RAPID = "rapid"


class Density(StrEnum):
    LIGHT = "light"
    BALANCED = "balanced"
    DENSE = "dense"


class GuidanceApplication(StrEnum):
    APPLIED = "applied"
    PARTIALLY_APPLIED = "partially_applied"
    NOT_APPLICABLE = "not_applicable"
    BLOCKED_BY_HIGHER_PRIORITY = "blocked_by_higher_priority"
    CONFLICTED = "conflicted"
    REQUIRES_EDITOR_REVIEW = "requires_editor_review"


class GuidanceStatus(StrEnum):
    EMERGING = "emerging"
    ESTABLISHED = "established"
    EXPLICIT_EDITOR_RULE = "explicit_editor_rule"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class UpstreamDependencyReference(FrozenModel):
    dependency_id: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    module_version: str = Field(pattern=SEMVER_PATTERN)
    semantic_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    readiness: CompositionReadiness = CompositionReadiness.READY
    compatible: bool = True
    canonical_mutation: bool = False


class ApprovedSegmentInput(FrozenModel):
    segment_id: str = Field(min_length=1)
    event_reference: str = Field(min_length=1)
    story_reference: str = Field(min_length=1)
    position: int = Field(ge=1)
    role: SegmentRole
    mandatory: bool = True
    excluded: bool = False
    fact_references: tuple[str, ...] = Field(min_length=1)
    source_provenance_references: tuple[str, ...] = Field(min_length=1)
    risk_references: tuple[str, ...] = ()
    category_references: tuple[str, ...] = ()
    sensitive: bool = False
    grave: bool = False
    unresolved_fact_references: tuple[str, ...] = ()
    legal_constraint_references: tuple[str, ...] = ()
    attribution_references: tuple[str, ...] = ()
    explicit_arc_function: str | None = None

    @field_validator("explicit_arc_function")
    @classmethod
    def validate_arc_function(cls, value: str | None) -> str | None:
        return _validate_controlled_or_custom(value, ArcFunction)


class CompositionGuidanceReference(FrozenModel):
    guidance_id: str = Field(min_length=1)
    preference_reference: str = Field(min_length=1)
    status: GuidanceStatus
    scope_references: tuple[str, ...] = ()
    source_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    mandatory: bool = False


class CompositionInputBundle(FrozenModel):
    input_bundle_id: str = Field(min_length=1)
    episode_reference: str = Field(min_length=1)
    selection_reference: str = Field(min_length=1)
    blueprint_reference: str = Field(min_length=1)
    memory_reference: str = Field(min_length=1)
    persona_reference: str = Field(min_length=1)
    philosophy_reference: str = Field(min_length=1)
    decision_framework_reference: str = Field(min_length=1)
    voice_reference: str = Field(min_length=1)
    audience_reference: str = Field(min_length=1)
    story_architecture_reference: str = Field(min_length=1)
    spoken_communication_reference: str = Field(min_length=1)
    romanian_conversational_reference: str = Field(min_length=1)
    language_guidance_reference: str = Field(min_length=1)
    upstream_dependencies: tuple[UpstreamDependencyReference, ...] = Field(min_length=1)
    approved_segments: tuple[ApprovedSegmentInput, ...] = Field(min_length=1)
    language_guidance: tuple[CompositionGuidanceReference, ...] = ()
    excluded_story_references: tuple[str, ...] = ()
    mandatory_story_references: tuple[str, ...] = ()
    input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class CompositionDecision(FrozenModel):
    decision_id: str = Field(min_length=1)
    decision_type: str = Field(min_length=1)
    target_references: tuple[str, ...] = Field(min_length=1)
    candidate_options: tuple[str, ...]
    selected_option: str = Field(min_length=1)
    applied_rule_references: tuple[str, ...] = Field(min_length=1)
    rejected_rule_references: tuple[str, ...] = ()
    conflict_references: tuple[str, ...] = ()
    precedence_result: str = Field(min_length=1)
    reason_references: tuple[str, ...] = Field(min_length=1)
    readiness_impact: CompositionReadiness = CompositionReadiness.READY
    decision_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class CompositionBeat(FrozenModel):
    beat_id: str = Field(min_length=1)
    beat_type: BeatType
    position: int = Field(ge=1)
    source_fact_references: tuple[str, ...] = Field(min_length=1)
    editorial_intent_references: tuple[str, ...] = Field(min_length=1)
    priority_reference: str = Field(min_length=1)
    tone_reference: str = Field(min_length=1)
    emphasis_reference: str = Field(min_length=1)
    delivery_constraint_references: tuple[str, ...] = ()
    risk_references: tuple[str, ...] = ()
    dependency_beat_ids: tuple[str, ...] = ()
    decision_trace: tuple[str, ...] = Field(min_length=1)
    beat_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


class BeatSequence(FrozenModel):
    beat_sequence_id: str = Field(min_length=1)
    segment_plan_id: str = Field(min_length=1)
    ordered_beat_ids: tuple[str, ...] = Field(min_length=1)
    beats: tuple[CompositionBeat, ...] = Field(min_length=1)
    sequence_constraints: tuple[str, ...] = ()
    sequence_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class SegmentPlan(FrozenModel):
    segment_plan_id: str = Field(min_length=1)
    segment_reference: str = Field(min_length=1)
    event_reference: str = Field(min_length=1)
    story_reference: str = Field(min_length=1)
    position: int = Field(ge=1)
    segment_role: SegmentRole
    estimated_duration_seconds: int = Field(ge=1)
    beat_sequence: BeatSequence
    editorial_priority_references: tuple[str, ...] = Field(min_length=1)
    tone_reference: str = Field(min_length=1)
    emphasis_references: tuple[str, ...] = Field(min_length=1)
    rhythm_guidance_references: tuple[str, ...] = Field(min_length=1)
    delivery_constraint_references: tuple[str, ...] = ()
    transition_in_reference: str | None = None
    transition_out_reference: str | None = None
    callback_references: tuple[str, ...] = ()
    guidance_references: tuple[str, ...] = ()
    risk_references: tuple[str, ...] = ()
    source_provenance_references: tuple[str, ...] = Field(min_length=1)
    decision_trace: tuple[str, ...] = Field(min_length=1)
    segment_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


class ArcStep(FrozenModel):
    arc_step_id: str = Field(min_length=1)
    position: int = Field(ge=1)
    arc_function: str = Field(min_length=1)
    segment_references: tuple[str, ...] = ()
    intensity: ArcIntensity
    required: bool = True
    transition_expectation: str | None = None
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    reason_references: tuple[str, ...] = Field(min_length=1)
    decision_trace: tuple[str, ...] = Field(min_length=1)
    arc_step_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False
    structural_boundary_permitted: bool = False

    @field_validator("arc_function")
    @classmethod
    def validate_arc_function(cls, value: str) -> str:
        return _validate_controlled_or_custom(value, ArcFunction) or value


class ArcSegmentBinding(FrozenModel):
    binding_id: str = Field(min_length=1)
    segment_reference: str = Field(min_length=1)
    primary_arc_step_reference: str = Field(min_length=1)
    secondary_arc_step_references: tuple[str, ...] = ()
    binding_type: str = "primary"
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    reason_references: tuple[str, ...] = Field(min_length=1)
    decision_trace: tuple[str, ...] = Field(min_length=1)
    binding_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ArcConstraint(FrozenModel):
    arc_constraint_id: str = Field(min_length=1)
    constraint_type: str = Field(min_length=1)
    target_references: tuple[str, ...] = Field(min_length=1)
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    severity: FindingSeverity
    mandatory: bool
    reason_references: tuple[str, ...] = Field(min_length=1)
    readiness_impact: CompositionReadiness
    constraint_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ArcConflict(FrozenModel):
    arc_conflict_id: str = Field(min_length=1)
    conflict_type: str = Field(min_length=1)
    arc_step_references: tuple[str, ...]
    segment_references: tuple[str, ...]
    competing_rule_references: tuple[str, ...] = Field(min_length=1)
    competing_alternatives: tuple[str, ...] = Field(min_length=1)
    applied_precedence: str = Field(min_length=1)
    selected_resolution: str | None = None
    rejected_alternatives: tuple[str, ...] = ()
    reason_references: tuple[str, ...] = Field(min_length=1)
    readiness_impact: CompositionReadiness
    editor_review_required: bool
    resolved: bool
    arc_conflict_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class EpisodeArc(FrozenModel):
    episode_arc_id: str = Field(min_length=1)
    composition_plan_reference: str = Field(min_length=1)
    episode_reference: str = Field(min_length=1)
    ordered_arc_step_ids: tuple[str, ...] = Field(min_length=1)
    arc_steps: tuple[ArcStep, ...] = Field(min_length=1)
    segment_bindings: tuple[ArcSegmentBinding, ...] = Field(min_length=1)
    arc_constraints: tuple[ArcConstraint, ...] = ()
    source_references: tuple[str, ...] = Field(min_length=1)
    decision_trace: tuple[str, ...] = Field(min_length=1)
    arc_conflicts: tuple[ArcConflict, ...] = ()
    arc_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


class TransitionPlan(FrozenModel):
    transition_plan_id: str = Field(min_length=1)
    from_segment_id: str = Field(min_length=1)
    to_segment_id: str = Field(min_length=1)
    transition_type: TransitionType
    relationship_references: tuple[str, ...] = Field(min_length=1)
    tone_change_reference: str | None = None
    rhythm_change_reference: str | None = None
    continuity_constraints: tuple[str, ...] = ()
    prohibited_implications: tuple[str, ...] = ()
    from_arc_step_reference: str = Field(min_length=1)
    to_arc_step_reference: str = Field(min_length=1)
    arc_compatibility: bool = True
    arc_constraint_references: tuple[str, ...] = ()
    decision_trace: tuple[str, ...] = Field(min_length=1)
    transition_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


class CallbackPlan(FrozenModel):
    callback_plan_id: str = Field(min_length=1)
    setup_segment_id: str = Field(min_length=1)
    resolution_segment_id: str = Field(min_length=1)
    setup_beat_reference: str = Field(min_length=1)
    resolution_beat_reference: str = Field(min_length=1)
    shared_context_references: tuple[str, ...] = Field(min_length=1)
    factual_continuity_references: tuple[str, ...] = Field(min_length=1)
    callback_role: str = Field(min_length=1)
    risk_references: tuple[str, ...] = ()
    arc_setup_step_reference: str = Field(min_length=1)
    arc_resolution_step_reference: str = Field(min_length=1)
    arc_contribution: str = Field(min_length=1)
    arc_compatibility: bool = True
    decision_trace: tuple[str, ...] = Field(min_length=1)
    callback_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


class EditorialPriority(FrozenModel):
    priority_id: str = Field(min_length=1)
    priority_type: str = Field(min_length=1)
    priority_level: PriorityLevel
    target_references: tuple[str, ...] = Field(min_length=1)
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    reason_references: tuple[str, ...] = Field(min_length=1)
    conflicting_priority_references: tuple[str, ...] = ()
    resolution_reference: str | None = None
    mandatory: bool
    priority_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class ToneStep(FrozenModel):
    tone_step_id: str = Field(min_length=1)
    segment_reference: str = Field(min_length=1)
    arc_step_reference: str = Field(min_length=1)
    tone_mode: str = Field(min_length=1)
    intensity: ArcIntensity
    gravity_level: PriorityLevel
    satirical_permission: str = Field(min_length=1)
    sensitivity_constraints: tuple[str, ...] = ()
    reason_references: tuple[str, ...] = Field(min_length=1)


class ToneProgression(FrozenModel):
    tone_progression_id: str = Field(min_length=1)
    episode_arc_id: str = Field(min_length=1)
    ordered_tone_steps: tuple[ToneStep, ...] = Field(min_length=1)
    source_voice_references: tuple[str, ...] = Field(min_length=1)
    source_audience_references: tuple[str, ...] = Field(min_length=1)
    story_severity_references: tuple[str, ...] = ()
    transition_constraints: tuple[str, ...] = ()
    tone_conflicts: tuple[str, ...] = ()
    arc_conflict_references: tuple[str, ...] = ()
    tone_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class EmphasisEntry(FrozenModel):
    emphasis_id: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    target_reference: str = Field(min_length=1)
    emphasis_level: EmphasisLevel
    reason_references: tuple[str, ...] = Field(min_length=1)
    source_rule_references: tuple[str, ...] = Field(min_length=1)
    must_preserve: bool
    must_not_overstate: bool


class EmphasisMap(FrozenModel):
    emphasis_map_id: str = Field(min_length=1)
    entries: tuple[EmphasisEntry, ...] = Field(min_length=1)
    emphasis_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class RhythmGuidance(FrozenModel):
    rhythm_guidance_id: str = Field(min_length=1)
    segment_reference: str = Field(min_length=1)
    pace: Pace
    density: Density
    pause_requirements: tuple[str, ...] = ()
    beat_spacing: str = Field(min_length=1)
    complexity_limit: int = Field(ge=1)
    teleprompter_constraints: tuple[str, ...] = ()
    source_communication_references: tuple[str, ...] = Field(min_length=1)
    source_language_guidance_references: tuple[str, ...] = ()
    reason_references: tuple[str, ...] = Field(min_length=1)
    rhythm_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class DeliveryConstraint(FrozenModel):
    constraint_id: str = Field(min_length=1)
    constraint_type: str = Field(min_length=1)
    target_references: tuple[str, ...] = Field(min_length=1)
    severity: FindingSeverity
    source_policy_references: tuple[str, ...] = Field(min_length=1)
    reason_references: tuple[str, ...] = Field(min_length=1)
    mandatory: bool
    constraint_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class GuidanceTraceEntry(FrozenModel):
    trace_id: str = Field(min_length=1)
    output_reference: str = Field(min_length=1)
    output_type: str = Field(min_length=1)
    upstream_module_id: str = Field(min_length=1)
    upstream_artifact_reference: str = Field(min_length=1)
    upstream_rule_reference: str = Field(min_length=1)
    upstream_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    application_type: GuidanceApplication
    precedence: int = Field(ge=1)
    decision_reference: str = Field(min_length=1)
    compatibility_status: str = Field(min_length=1)


class GuidanceTraceability(FrozenModel):
    traceability_id: str = Field(min_length=1)
    entries: tuple[GuidanceTraceEntry, ...] = Field(min_length=1)
    orphan_guidance_references: tuple[str, ...] = ()
    unused_mandatory_guidance: tuple[str, ...] = ()
    traceability_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class CompositionConflict(FrozenModel):
    conflict_id: str = Field(min_length=1)
    conflict_type: str = Field(min_length=1)
    affected_references: tuple[str, ...] = Field(min_length=1)
    competing_rule_references: tuple[str, ...] = Field(min_length=1)
    precedence_rules: tuple[str, ...] = Field(min_length=1)
    resolution_status: str = Field(min_length=1)
    selected_resolution: str | None = None
    editor_review_required: bool
    reason_references: tuple[str, ...] = Field(min_length=1)
    conflict_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)


class UnresolvedConstraint(FrozenModel):
    unresolved_constraint_id: str = Field(min_length=1)
    constraint_reference: str = Field(min_length=1)
    affected_references: tuple[str, ...] = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    severity: FindingSeverity
    editor_review_required: bool
    blocking: bool
    source_references: tuple[str, ...] = Field(min_length=1)


class CompositionValidationFinding(FrozenModel):
    finding_id: str = Field(min_length=1)
    finding_code: str = Field(min_length=1)
    severity: FindingSeverity
    artifact_reference: str = Field(min_length=1)
    field_reference: str | None = None
    related_references: tuple[str, ...] = ()
    message_reference: str = Field(min_length=1)
    blocking: bool
    editor_review_required: bool


class CompositionPlan(FrozenModel):
    composition_plan_id: str = Field(min_length=1)
    composition_engine_id: str = Field(min_length=1)
    composition_engine_version: str = Field(pattern=SEMVER_PATTERN)
    input_bundle_id: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    episode_reference: str = Field(min_length=1)
    ordered_segment_ids: tuple[str, ...] = Field(min_length=1)
    segment_plans: tuple[SegmentPlan, ...] = Field(min_length=1)
    episode_arc: EpisodeArc
    transition_plans: tuple[TransitionPlan, ...] = ()
    callback_plans: tuple[CallbackPlan, ...] = ()
    editorial_priorities: tuple[EditorialPriority, ...] = Field(min_length=1)
    tone_progression: ToneProgression
    emphasis_map: EmphasisMap
    rhythm_guidance: tuple[RhythmGuidance, ...] = Field(min_length=1)
    delivery_constraints: tuple[DeliveryConstraint, ...] = ()
    guidance_traceability: GuidanceTraceability
    decisions: tuple[CompositionDecision, ...] = Field(min_length=1)
    conflicts: tuple[CompositionConflict, ...] = ()
    warnings: tuple[str, ...] = ()
    unresolved_constraints: tuple[UnresolvedConstraint, ...] = ()
    validation_findings: tuple[CompositionValidationFinding, ...] = ()
    readiness: CompositionReadiness
    composition_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    contains_generated_language: bool = False


def _validate_controlled_or_custom(
    value: str | None, enum: type[StrEnum]
) -> str | None:
    if value is None or value in {item.value for item in enum}:
        return value
    import re

    if not re.fullmatch(CUSTOM_PATTERN, value):
        raise ValueError(f"unsupported {enum.__name__}: {value}")
    return value


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, BaseModel):
        for nested in value.__dict__.values():
            yield from _strings(nested)
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _strings(nested)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for nested in value:
            yield from _strings(nested)


__all__ = tuple(
    name
    for name, value in globals().items()
    if not name.startswith("_") and getattr(value, "__module__", None) == __name__
)
