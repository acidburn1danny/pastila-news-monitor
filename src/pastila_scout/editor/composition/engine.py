"""Pure deterministic Editorial Composition Engine."""

from itertools import pairwise

from .defaults import (
    COMPOSITION_ENGINE_ID,
    COMPOSITION_ENGINE_VERSION,
    EDITORIAL_PRECEDENCE,
)
from .fingerprint import artifact_fingerprint
from .models import *
from .readiness import derive_readiness
from .validator import (
    CompositionValidationError,
    validate_composition_plan,
    validate_input_bundle,
)


def _sealed(model_type, fingerprint_field: str, **values):
    values[fingerprint_field] = "0" * 64
    probe = model_type(**values)
    return probe.model_copy(update={fingerprint_field: artifact_fingerprint(probe)})


def _arc_function(segment: ApprovedSegmentInput, index: int, total: int) -> str:
    if segment.explicit_arc_function:
        return segment.explicit_arc_function
    if segment.role == SegmentRole.OPENING or index == 1:
        return ArcFunction.ORIENTATION
    if segment.role == SegmentRole.CLOSING or index == total:
        return ArcFunction.CLOSURE
    if segment.role == SegmentRole.ESCALATION:
        return ArcFunction.ESCALATION
    if segment.role == SegmentRole.RESET:
        return ArcFunction.RESET
    if segment.role == SegmentRole.COMIC_RELIEF and not (
        segment.sensitive or segment.grave
    ):
        return ArcFunction.RELIEF
    return ArcFunction.BUILD


def _priority(segment: ApprovedSegmentInput) -> EditorialPriority:
    priority_type = (
        "legal_precision" if segment.legal_constraint_references else "factual_accuracy"
    )
    level = (
        PriorityLevel.CRITICAL
        if segment.legal_constraint_references or segment.sensitive
        else PriorityLevel.HIGH
    )
    return _sealed(
        EditorialPriority,
        "priority_fingerprint",
        priority_id=f"priority-{segment.segment_id}",
        priority_type=priority_type,
        priority_level=level,
        target_references=(f"segment-plan-{segment.segment_id}",),
        source_rule_references=EDITORIAL_PRECEDENCE,
        reason_references=segment.fact_references,
        mandatory=True,
    )


def _beats(segment: ApprovedSegmentInput) -> BeatSequence:
    plan_id = f"segment-plan-{segment.segment_id}"
    priority_id = f"priority-{segment.segment_id}"
    definitions = [(BeatType.ORIENTATION, (segment.fact_references[0],))]
    if len(segment.fact_references) > 1:
        definitions.append((BeatType.FACT, tuple(segment.fact_references[1:])))
    if segment.attribution_references:
        definitions.append((BeatType.ATTRIBUTION, segment.attribution_references))
    if segment.risk_references:
        definitions.append((BeatType.RISK_BOUNDARY, segment.fact_references))
    beats = []
    for position, (beat_type, facts) in enumerate(definitions, 1):
        beat_id = f"beat-{segment.segment_id}-{position}"
        dependencies = (
            () if position == 1 else (f"beat-{segment.segment_id}-{position - 1}",)
        )
        beats.append(
            _sealed(
                CompositionBeat,
                "beat_fingerprint",
                beat_id=beat_id,
                beat_type=beat_type,
                position=position,
                source_fact_references=facts,
                editorial_intent_references=(f"intent-{beat_type.value}",),
                priority_reference=priority_id,
                tone_reference=f"tone-{segment.segment_id}",
                emphasis_reference=f"emphasis-{segment.segment_id}",
                delivery_constraint_references=tuple(
                    f"delivery-{segment.segment_id}-{index}"
                    for index, _ in enumerate(segment.legal_constraint_references, 1)
                ),
                risk_references=tuple(
                    dict.fromkeys(
                        segment.risk_references
                        + segment.unresolved_fact_references
                        + segment.legal_constraint_references
                        + segment.attribution_references
                    )
                ),
                dependency_beat_ids=dependencies,
                decision_trace=(f"decision-segment-{segment.segment_id}",),
            )
        )
    return _sealed(
        BeatSequence,
        "sequence_fingerprint",
        beat_sequence_id=f"sequence-{segment.segment_id}",
        segment_plan_id=plan_id,
        ordered_beat_ids=tuple(item.beat_id for item in beats),
        beats=tuple(beats),
        sequence_constraints=("preserve-fact-order", "preserve-attribution"),
    )


def _segment_plan(segment: ApprovedSegmentInput) -> SegmentPlan:
    return _sealed(
        SegmentPlan,
        "segment_fingerprint",
        segment_plan_id=f"segment-plan-{segment.segment_id}",
        segment_reference=segment.segment_id,
        event_reference=segment.event_reference,
        story_reference=segment.story_reference,
        position=segment.position,
        segment_role=segment.role,
        estimated_duration_seconds=max(45, len(segment.fact_references) * 30),
        beat_sequence=_beats(segment),
        editorial_priority_references=(f"priority-{segment.segment_id}",),
        tone_reference=f"tone-{segment.segment_id}",
        emphasis_references=(f"emphasis-{segment.segment_id}",),
        rhythm_guidance_references=(f"rhythm-{segment.segment_id}",),
        delivery_constraint_references=tuple(
            f"delivery-{segment.segment_id}-{index}"
            for index, _ in enumerate(segment.legal_constraint_references, 1)
        ),
        guidance_references=(),
        risk_references=tuple(
            dict.fromkeys(
                segment.risk_references
                + segment.unresolved_fact_references
                + segment.legal_constraint_references
                + segment.attribution_references
            )
        ),
        source_provenance_references=segment.source_provenance_references,
        decision_trace=(f"decision-segment-{segment.segment_id}",),
    )


def _episode_arc(
    bundle: CompositionInputBundle,
    plan_id: str,
    segments: tuple[SegmentPlan, ...],
) -> EpisodeArc:
    steps = []
    bindings = []
    for source, segment in zip(bundle.approved_segments, segments, strict=True):
        function = _arc_function(source, source.position, len(segments))
        step_id = f"arc-step-{source.segment_id}"
        reasons = [
            f"segment-role:{source.role.value}",
            "preserve-approved-segment-order",
        ]
        source_rules = ["story-architecture", "editorial-decision-framework"]
        if function == ArcFunction.PEAK and source.explicit_arc_function:
            source_rules.append("peak-supported")
        if function == ArcFunction.STABILIZATION:
            reasons.append("consolidate-confirmed-facts")
            if (
                source.unresolved_fact_references
                or source.legal_constraint_references
                or source.attribution_references
            ):
                reasons.append("preserve-unresolved-constraints")
        intensity = (
            ArcIntensity.LOW
            if function in {ArcFunction.ORIENTATION, ArcFunction.CLOSURE}
            else (
                ArcIntensity.HIGH
                if function in {ArcFunction.ESCALATION, ArcFunction.PEAK}
                else ArcIntensity.MODERATE
            )
        )
        steps.append(
            _sealed(
                ArcStep,
                "arc_step_fingerprint",
                arc_step_id=step_id,
                position=source.position,
                arc_function=function,
                segment_references=(segment.segment_plan_id,),
                intensity=intensity,
                transition_expectation=None,
                source_rule_references=tuple(source_rules),
                reason_references=tuple(reasons),
                decision_trace=(f"decision-arc-{source.segment_id}",),
            )
        )
        bindings.append(
            _sealed(
                ArcSegmentBinding,
                "binding_fingerprint",
                binding_id=f"binding-{source.segment_id}",
                segment_reference=segment.segment_plan_id,
                primary_arc_step_reference=step_id,
                source_rule_references=("approved-segment-order",),
                reason_references=(f"segment-position:{source.position}",),
                decision_trace=(f"decision-arc-{source.segment_id}",),
            )
        )
    return _sealed(
        EpisodeArc,
        "arc_fingerprint",
        episode_arc_id=f"episode-arc-{bundle.episode_reference}",
        composition_plan_reference=plan_id,
        episode_reference=bundle.episode_reference,
        ordered_arc_step_ids=tuple(item.arc_step_id for item in steps),
        arc_steps=tuple(steps),
        segment_bindings=tuple(bindings),
        arc_constraints=_collect_constraints(bundle),
        source_references=(
            bundle.story_architecture_reference,
            bundle.decision_framework_reference,
        ),
        decision_trace=tuple(
            f"decision-arc-{item.segment_id}" for item in bundle.approved_segments
        ),
        arc_conflicts=(),
    )


def _collect_constraints(
    bundle: CompositionInputBundle,
) -> tuple[ArcConstraint, ...]:
    """Collect immutable authoritative constraints before arc planning."""
    constraints = [
        _sealed(
            ArcConstraint,
            "constraint_fingerprint",
            arc_constraint_id="arc-constraint-approved-segment-order",
            constraint_type="approved-segment-order",
            target_references=tuple(
                item.segment_id for item in bundle.approved_segments
            ),
            source_rule_references=(bundle.story_architecture_reference,),
            severity=FindingSeverity.ERROR,
            mandatory=True,
            reason_references=("authoritative-segment-order",),
            readiness_impact=CompositionReadiness.BLOCKED,
        )
    ]
    for item in bundle.approved_segments:
        if item.legal_constraint_references or item.sensitive or item.grave:
            constraints.append(
                _sealed(
                    ArcConstraint,
                    "constraint_fingerprint",
                    arc_constraint_id=f"arc-constraint-{item.segment_id}",
                    constraint_type=(
                        "legal-precision"
                        if item.legal_constraint_references
                        else "dignity-and-sensitivity"
                    ),
                    target_references=(item.segment_id,),
                    source_rule_references=(bundle.decision_framework_reference,),
                    severity=FindingSeverity.ERROR,
                    mandatory=True,
                    reason_references=("preserve-mandatory-boundary",),
                    readiness_impact=CompositionReadiness.BLOCKED,
                )
            )
    return tuple(constraints)


def _tone(bundle: CompositionInputBundle, arc: EpisodeArc) -> ToneProgression:
    step_by_segment = {
        segment: step.arc_step_id
        for step in arc.arc_steps
        for segment in step.segment_references
    }
    tones = []
    for source in bundle.approved_segments:
        segment_id = f"segment-plan-{source.segment_id}"
        tones.append(
            ToneStep(
                tone_step_id=f"tone-{source.segment_id}",
                segment_reference=segment_id,
                arc_step_reference=step_by_segment[segment_id],
                tone_mode="serious" if source.grave or source.sensitive else "neutral",
                intensity=ArcIntensity.MODERATE,
                gravity_level=(
                    PriorityLevel.HIGH if source.grave else PriorityLevel.NORMAL
                ),
                satirical_permission=(
                    "restricted" if source.grave or source.sensitive else "permitted"
                ),
                sensitivity_constraints=segment_id and source.risk_references,
                reason_references=("voice-policy", "audience-policy"),
            )
        )
    return _sealed(
        ToneProgression,
        "tone_fingerprint",
        tone_progression_id=f"tone-progression-{bundle.episode_reference}",
        episode_arc_id=arc.episode_arc_id,
        ordered_tone_steps=tuple(tones),
        source_voice_references=(bundle.voice_reference,),
        source_audience_references=(bundle.audience_reference,),
        story_severity_references=tuple(item.segment_reference for item in tones),
    )


def _transitions(
    segments: tuple[SegmentPlan, ...], arc: EpisodeArc
) -> tuple[TransitionPlan, ...]:
    arc_by_segment = {
        segment: step.arc_step_id
        for step in arc.arc_steps
        for segment in step.segment_references
    }
    transitions = []
    for left, right in pairwise(segments):
        transitions.append(
            _sealed(
                TransitionPlan,
                "transition_fingerprint",
                transition_plan_id=f"transition-{left.position}-{right.position}",
                from_segment_id=left.segment_plan_id,
                to_segment_id=right.segment_plan_id,
                transition_type=TransitionType.CONTINUATION,
                relationship_references=("approved-episode-flow",),
                continuity_constraints=("no-unsupported-causation",),
                prohibited_implications=(
                    "causation",
                    "shared-context-without-evidence",
                ),
                from_arc_step_reference=arc_by_segment[left.segment_plan_id],
                to_arc_step_reference=arc_by_segment[right.segment_plan_id],
                decision_trace=(
                    f"decision-transition-{left.position}-{right.position}",
                ),
            )
        )
    return tuple(transitions)


def _callbacks(
    bundle: CompositionInputBundle,
    segments: tuple[SegmentPlan, ...],
    arc: EpisodeArc,
) -> tuple[CallbackPlan, ...]:
    """Return no callbacks when upstream input contains no confirmed relationship."""
    del bundle, segments, arc
    return ()


def _emphasis(bundle: CompositionInputBundle) -> EmphasisMap:
    entries = tuple(
        EmphasisEntry(
            emphasis_id=f"emphasis-{item.segment_id}",
            target_type="segment",
            target_reference=f"segment-plan-{item.segment_id}",
            emphasis_level=(
                EmphasisLevel.CRITICAL
                if item.legal_constraint_references
                else EmphasisLevel.STRONG
            ),
            reason_references=item.fact_references,
            source_rule_references=("factual-priority",),
            must_preserve=True,
            must_not_overstate=True,
        )
        for item in bundle.approved_segments
    )
    return _sealed(
        EmphasisMap,
        "emphasis_fingerprint",
        emphasis_map_id=f"emphasis-{bundle.episode_reference}",
        entries=entries,
    )


def _rhythm(bundle: CompositionInputBundle) -> tuple[RhythmGuidance, ...]:
    return tuple(
        _sealed(
            RhythmGuidance,
            "rhythm_fingerprint",
            rhythm_guidance_id=f"rhythm-{item.segment_id}",
            segment_reference=f"segment-plan-{item.segment_id}",
            pace=Pace.MEASURED if item.grave or item.sensitive else Pace.MODERATE,
            density=(
                Density.DENSE if len(item.fact_references) > 3 else Density.BALANCED
            ),
            pause_requirements=("preserve-fact-separation",),
            beat_spacing="structural",
            complexity_limit=3,
            teleprompter_constraints=("bounded-clause-load",),
            source_communication_references=(bundle.spoken_communication_reference,),
            source_language_guidance_references=(bundle.language_guidance_reference,),
            reason_references=("spoken-communication-policy",),
        )
        for item in bundle.approved_segments
    )


def _delivery(bundle: CompositionInputBundle) -> tuple[DeliveryConstraint, ...]:
    result = []
    for item in bundle.approved_segments:
        for index, reference in enumerate(item.legal_constraint_references, 1):
            result.append(
                _sealed(
                    DeliveryConstraint,
                    "constraint_fingerprint",
                    constraint_id=f"delivery-{item.segment_id}-{index}",
                    constraint_type="legal_precision",
                    target_references=(f"segment-plan-{item.segment_id}",),
                    severity=FindingSeverity.ERROR,
                    source_policy_references=(reference,),
                    reason_references=("preserve-legal-meaning",),
                    mandatory=True,
                )
            )
    return tuple(result)


def _decisions(bundle: CompositionInputBundle) -> tuple[CompositionDecision, ...]:
    result = []
    for item in bundle.approved_segments:
        selected = _arc_function(item, item.position, len(bundle.approved_segments))
        result.append(
            _sealed(
                CompositionDecision,
                "decision_fingerprint",
                decision_id=f"decision-segment-{item.segment_id}",
                decision_type="segment-preservation",
                target_references=(f"segment-plan-{item.segment_id}",),
                candidate_options=(item.segment_id,),
                selected_option=item.segment_id,
                applied_rule_references=("approved-story-membership",),
                precedence_result="upstream-approved",
                reason_references=(item.story_reference,),
            )
        )
        result.append(
            _sealed(
                CompositionDecision,
                "decision_fingerprint",
                decision_id=f"decision-arc-{item.segment_id}",
                decision_type="arc-function",
                target_references=(f"arc-step-{item.segment_id}",),
                candidate_options=tuple(value.value for value in ArcFunction),
                selected_option=str(selected),
                applied_rule_references=(
                    "story-architecture",
                    "approved-segment-order",
                ),
                precedence_result="structural-role",
                reason_references=(f"segment-role:{item.role.value}",),
            )
        )
    return tuple(result)


def _traceability(
    bundle: CompositionInputBundle, segments: tuple[SegmentPlan, ...], arc: EpisodeArc
) -> GuidanceTraceability:
    dependencies = sorted(bundle.upstream_dependencies, key=lambda item: item.module_id)
    entries = []
    for index, output in enumerate(
        [item.segment_plan_id for item in segments] + list(arc.ordered_arc_step_ids), 1
    ):
        dependency = dependencies[(index - 1) % len(dependencies)]
        entries.append(
            GuidanceTraceEntry(
                trace_id=f"trace-{index}",
                output_reference=output,
                output_type=(
                    "segment" if output.startswith("segment-plan") else "arc-step"
                ),
                upstream_module_id=dependency.module_id,
                upstream_artifact_reference=dependency.dependency_id,
                upstream_rule_reference="validated-upstream-contract",
                upstream_fingerprint=dependency.semantic_fingerprint,
                application_type=GuidanceApplication.APPLIED,
                precedence=index,
                decision_reference=(
                    output.replace("segment-plan-", "decision-segment-")
                    if output.startswith("segment-plan")
                    else output.replace("arc-step-", "decision-arc-")
                ),
                compatibility_status="compatible",
            )
        )
    learning_dependency = next(
        (
            item
            for item in dependencies
            if item.module_id == "editorial-language-learning-engine"
        ),
        dependencies[0],
    )
    for guidance in sorted(bundle.language_guidance, key=lambda item: item.guidance_id):
        application = (
            GuidanceApplication.APPLIED
            if guidance.status
            in {GuidanceStatus.ESTABLISHED, GuidanceStatus.EXPLICIT_EDITOR_RULE}
            else (
                GuidanceApplication.REQUIRES_EDITOR_REVIEW
                if guidance.status == GuidanceStatus.EMERGING
                else GuidanceApplication.NOT_APPLICABLE
            )
        )
        entries.append(
            GuidanceTraceEntry(
                trace_id=f"trace-guidance-{guidance.guidance_id}",
                output_reference=guidance.guidance_id,
                output_type="language-guidance",
                upstream_module_id=learning_dependency.module_id,
                upstream_artifact_reference=guidance.preference_reference,
                upstream_rule_reference=f"guidance-status:{guidance.status.value}",
                upstream_fingerprint=guidance.source_fingerprint,
                application_type=application,
                precedence=len(entries) + 1,
                decision_reference=f"guidance-decision-{guidance.guidance_id}",
                compatibility_status="compatible",
            )
        )
    return _sealed(
        GuidanceTraceability,
        "traceability_fingerprint",
        traceability_id=f"traceability-{bundle.episode_reference}",
        entries=tuple(entries),
    )


def _applicable_guidance(
    bundle: CompositionInputBundle, segment: ApprovedSegmentInput
) -> tuple[str, ...]:
    active = {GuidanceStatus.ESTABLISHED, GuidanceStatus.EXPLICIT_EDITOR_RULE}
    return tuple(
        sorted(
            item.guidance_id
            for item in bundle.language_guidance
            if item.status in active
            and (
                not item.scope_references or segment.segment_id in item.scope_references
            )
        )
    )


def compose(bundle: CompositionInputBundle) -> CompositionPlan:
    """Build one immutable structural plan without producing episode language."""
    input_findings = validate_input_bundle(bundle)
    if input_findings:
        raise CompositionValidationError(
            "; ".join(item.finding_code for item in input_findings)
        )
    plan_id = f"composition-plan-{bundle.episode_reference}"
    segments = tuple(
        _segment_plan(item).model_copy(
            update={"guidance_references": _applicable_guidance(bundle, item)}
        )
        for item in bundle.approved_segments
    )
    segments = tuple(
        item.model_copy(update={"segment_fingerprint": artifact_fingerprint(item)})
        for item in segments
    )
    arc = _episode_arc(bundle, plan_id, segments)
    tone = _tone(bundle, arc)
    transitions = _transitions(segments, arc)
    priorities = tuple(_priority(item) for item in bundle.approved_segments)
    callbacks = _callbacks(bundle, segments, arc)
    decisions = _decisions(bundle)
    traceability = _traceability(bundle, segments, arc)
    readiness = derive_readiness(bundle, ())
    plan = _sealed(
        CompositionPlan,
        "composition_fingerprint",
        composition_plan_id=plan_id,
        composition_engine_id=COMPOSITION_ENGINE_ID,
        composition_engine_version=COMPOSITION_ENGINE_VERSION,
        input_bundle_id=bundle.input_bundle_id,
        input_fingerprint=bundle.input_fingerprint,
        episode_reference=bundle.episode_reference,
        ordered_segment_ids=tuple(item.segment_plan_id for item in segments),
        segment_plans=segments,
        episode_arc=arc,
        transition_plans=transitions,
        callback_plans=callbacks,
        editorial_priorities=priorities,
        tone_progression=tone,
        emphasis_map=_emphasis(bundle),
        rhythm_guidance=_rhythm(bundle),
        delivery_constraints=_delivery(bundle),
        guidance_traceability=traceability,
        decisions=decisions,
        readiness=readiness,
    )
    findings = validate_composition_plan(plan, bundle)
    substantive = tuple(
        item
        for item in findings
        if item.finding_code
        not in {"readiness-mismatch", "validation-findings-mismatch"}
    )
    if substantive:
        probe = plan.model_copy(
            update={
                "validation_findings": substantive,
                "readiness": derive_readiness(bundle, substantive),
                "composition_fingerprint": "0" * 64,
            }
        )
        plan = probe.model_copy(
            update={"composition_fingerprint": artifact_fingerprint(probe)}
        )
    return plan


__all__ = ("compose",)
