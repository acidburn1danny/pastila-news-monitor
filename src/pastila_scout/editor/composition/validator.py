"""Structured deterministic validation for composition contracts."""

from collections import defaultdict

from .defaults import (
    COMPOSITION_ENGINE_ID,
    COMPOSITION_ENGINE_VERSION,
    REQUIRED_UPSTREAM_MODULES,
)
from .fingerprint import artifact_fingerprint
from .models import *
from .readiness import derive_readiness


class CompositionValidationError(ValueError):
    """Raised when a composition artifact cannot be accepted."""


def _finding(
    code: str,
    artifact: str,
    *,
    blocking: bool = True,
    review: bool = False,
    field: str | None = None,
    related: tuple[str, ...] = (),
) -> CompositionValidationFinding:
    severity = (
        FindingSeverity.ERROR
        if blocking
        else FindingSeverity.REVIEW if review else FindingSeverity.WARNING
    )
    return CompositionValidationFinding(
        finding_id=f"finding-{code}-{artifact}",
        finding_code=code,
        severity=severity,
        artifact_reference=artifact,
        field_reference=field,
        related_references=related,
        message_reference=f"composition-validation:{code}",
        blocking=blocking,
        editor_review_required=review,
    )


def validate_input_bundle(
    bundle: CompositionInputBundle,
) -> tuple[CompositionValidationFinding, ...]:
    findings: list[CompositionValidationFinding] = []
    dependency_ids = [item.module_id for item in bundle.upstream_dependencies]
    if len(dependency_ids) != len(set(dependency_ids)):
        findings.append(_finding("duplicate-dependency", bundle.input_bundle_id))
    required = set(REQUIRED_UPSTREAM_MODULES)
    missing = required - set(dependency_ids)
    extra = set(dependency_ids) - required
    if missing:
        findings.append(
            _finding(
                "missing-dependency",
                bundle.input_bundle_id,
                related=tuple(sorted(missing)),
            )
        )
    if extra:
        findings.append(
            _finding(
                "unexpected-dependency",
                bundle.input_bundle_id,
                related=tuple(sorted(extra)),
            )
        )
    if any(item.module_version != "1.0.0" for item in bundle.upstream_dependencies):
        findings.append(
            _finding("incompatible-dependency-version", bundle.input_bundle_id)
        )
    if any(not item.compatible for item in bundle.upstream_dependencies):
        findings.append(_finding("incompatible-dependency", bundle.input_bundle_id))
    if any(item.canonical_mutation for item in bundle.upstream_dependencies):
        findings.append(_finding("canonical-mutation", bundle.input_bundle_id))
    positions = [item.position for item in bundle.approved_segments]
    if positions != list(range(1, len(positions) + 1)):
        findings.append(_finding("invalid-segment-order", bundle.input_bundle_id))
    segment_ids = [item.segment_id for item in bundle.approved_segments]
    if len(segment_ids) != len(set(segment_ids)):
        findings.append(_finding("duplicate-segment", bundle.input_bundle_id))
    if any(item.excluded for item in bundle.approved_segments):
        findings.append(_finding("excluded-segment-present", bundle.input_bundle_id))
    stories = {item.story_reference for item in bundle.approved_segments}
    missing_mandatory = set(bundle.mandatory_story_references) - stories
    if missing_mandatory:
        findings.append(
            _finding(
                "mandatory-story-missing",
                bundle.input_bundle_id,
                related=tuple(sorted(missing_mandatory)),
            )
        )
    if stories & set(bundle.excluded_story_references):
        findings.append(_finding("excluded-story-reintroduced", bundle.input_bundle_id))
    if bundle.input_fingerprint != artifact_fingerprint(bundle):
        findings.append(_finding("input-fingerprint-mismatch", bundle.input_bundle_id))
    return tuple(findings)


def validate_beat_sequence(
    sequence: BeatSequence,
) -> tuple[CompositionValidationFinding, ...]:
    findings: list[CompositionValidationFinding] = []
    ids = [item.beat_id for item in sequence.beats]
    positions = [item.position for item in sequence.beats]
    if ids != list(sequence.ordered_beat_ids):
        findings.append(_finding("beat-order-mismatch", sequence.beat_sequence_id))
    if len(ids) != len(set(ids)) or positions != list(range(1, len(ids) + 1)):
        findings.append(_finding("invalid-beat-positions", sequence.beat_sequence_id))
    known = set(ids)
    order = {item: index for index, item in enumerate(ids)}
    for beat in sequence.beats:
        if any(item not in known for item in beat.dependency_beat_ids):
            findings.append(_finding("unknown-beat-dependency", beat.beat_id))
        if any(
            order[item] >= order[beat.beat_id]
            for item in beat.dependency_beat_ids
            if item in order
        ):
            findings.append(
                _finding("cyclic-or-reversed-beat-dependency", beat.beat_id)
            )
        if beat.contains_generated_language:
            findings.append(_finding("generated-language", beat.beat_id))
        if beat.beat_fingerprint != artifact_fingerprint(beat):
            findings.append(_finding("beat-fingerprint-mismatch", beat.beat_id))
    if sequence.sequence_fingerprint != artifact_fingerprint(sequence):
        findings.append(
            _finding("sequence-fingerprint-mismatch", sequence.beat_sequence_id)
        )
    return tuple(findings)


def validate_episode_arc(
    arc: EpisodeArc,
    segments: tuple[SegmentPlan, ...],
    tone: ToneProgression | None = None,
    transitions: tuple[TransitionPlan, ...] = (),
    callbacks: tuple[CallbackPlan, ...] = (),
) -> tuple[CompositionValidationFinding, ...]:
    findings: list[CompositionValidationFinding] = []
    step_ids = [item.arc_step_id for item in arc.arc_steps]
    positions = [item.position for item in arc.arc_steps]
    if len(step_ids) != len(set(step_ids)):
        findings.append(_finding("duplicate-arc-step", arc.episode_arc_id))
    if positions != list(range(1, len(positions) + 1)):
        findings.append(_finding("noncontiguous-arc-steps", arc.episode_arc_id))
    if step_ids != list(arc.ordered_arc_step_ids):
        findings.append(_finding("arc-order-mismatch", arc.episode_arc_id))
    known_segments = {item.segment_plan_id for item in segments}
    segment_positions = {item.segment_plan_id: item.position for item in segments}
    segment_roles = {item.segment_plan_id: item.segment_role for item in segments}
    known_facts = {
        fact
        for segment in segments
        for beat in segment.beat_sequence.beats
        for fact in beat.source_fact_references
    }
    known_steps = set(step_ids)
    primary: defaultdict[str, list[str]] = defaultdict(list)
    step_position = {item.arc_step_id: item.position for item in arc.arc_steps}
    for binding in arc.segment_bindings:
        if (
            binding.segment_reference not in known_segments
            or binding.primary_arc_step_reference not in known_steps
        ):
            findings.append(
                _finding("unknown-arc-binding-reference", binding.binding_id)
            )
            continue
        primary[binding.segment_reference].append(binding.primary_arc_step_reference)
        if binding.binding_fingerprint != artifact_fingerprint(binding):
            findings.append(
                _finding("binding-fingerprint-mismatch", binding.binding_id)
            )
    for segment_id in sorted(known_segments):
        if len(primary[segment_id]) != 1:
            findings.append(
                _finding(
                    "invalid-primary-arc-binding",
                    arc.episode_arc_id,
                    related=(segment_id,),
                )
            )
    bound_order = [
        (step_position[primary[item][0]], segment_positions[item])
        for item in sorted(known_segments, key=segment_positions.get)
        if len(primary[item]) == 1
    ]
    if bound_order != sorted(bound_order):
        findings.append(_finding("arc-reorders-segments", arc.episode_arc_id))
    for step in arc.arc_steps:
        if step.required and not step.segment_references:
            findings.append(_finding("empty-required-arc-step", step.arc_step_id))
        if (
            not step.segment_references
            and not step.required
            and not step.structural_boundary_permitted
        ):
            findings.append(
                _finding("unauthorized-structural-boundary", step.arc_step_id)
            )
        if not set(step.segment_references).issubset(known_segments):
            findings.append(_finding("unknown-arc-segment", step.arc_step_id))
        if step.contains_generated_language:
            findings.append(_finding("generated-language", step.arc_step_id))
        if step.arc_step_fingerprint != artifact_fingerprint(step):
            findings.append(_finding("arc-step-fingerprint-mismatch", step.arc_step_id))
        if step.arc_function == ArcFunction.STABILIZATION:
            findings.extend(_validate_stabilization(step, segments))
        if (
            step.arc_function == ArcFunction.PEAK
            and "peak-supported" not in step.source_rule_references
        ):
            findings.append(
                _finding(
                    "unsupported-forced-peak",
                    step.arc_step_id,
                    blocking=False,
                    review=True,
                )
            )
        if step.arc_function == ArcFunction.CLOSURE and (
            step.position != len(arc.arc_steps)
            or any(
                segment_roles.get(reference) != SegmentRole.CLOSING
                for reference in step.segment_references
            )
        ):
            findings.append(_finding("invalid-closure-placement", step.arc_step_id))
    for constraint in arc.arc_constraints:
        if constraint.constraint_fingerprint != artifact_fingerprint(constraint):
            findings.append(
                _finding(
                    "arc-constraint-fingerprint-mismatch", constraint.arc_constraint_id
                )
            )
    for conflict in arc.arc_conflicts:
        if conflict.arc_conflict_fingerprint != artifact_fingerprint(conflict):
            findings.append(
                _finding("arc-conflict-fingerprint-mismatch", conflict.arc_conflict_id)
            )
        if (
            not conflict.resolved
            and conflict.readiness_impact == CompositionReadiness.BLOCKED
        ):
            findings.append(
                _finding("unresolved-blocking-arc-conflict", conflict.arc_conflict_id)
            )
        elif not conflict.resolved:
            findings.append(
                _finding(
                    "unresolved-arc-conflict",
                    conflict.arc_conflict_id,
                    blocking=False,
                    review=True,
                )
            )
    step_membership: defaultdict[str, list[str]] = defaultdict(list)
    for step in arc.arc_steps:
        for segment_id in step.segment_references:
            step_membership[segment_id].append(step.arc_step_id)
    for segment_id in sorted(known_segments):
        if len(step_membership[segment_id]) != 1:
            findings.append(
                _finding(
                    "contradictory-arc-step-membership",
                    arc.episode_arc_id,
                    related=(segment_id,),
                )
            )
        elif len(primary[segment_id]) == 1 and (
            step_membership[segment_id][0] != primary[segment_id][0]
        ):
            findings.append(
                _finding(
                    "arc-binding-step-mismatch",
                    arc.episode_arc_id,
                    related=(segment_id,),
                )
            )
    for current, successor in zip(arc.arc_steps, arc.arc_steps[1:]):
        if (
            current.arc_function == ArcFunction.STABILIZATION
            and successor.arc_function == ArcFunction.RESOLUTION
            and "resolution-supported" not in successor.source_rule_references
        ):
            findings.append(
                _finding(
                    "unsupported-stabilization-resolution",
                    successor.arc_step_id,
                    blocking=False,
                    review=True,
                )
            )
    if tone is not None:
        findings.extend(_validate_arc_tone(arc, tone, segments))
    findings.extend(_validate_arc_transitions(arc, transitions, segment_positions))
    findings.extend(
        _validate_arc_callbacks(arc, callbacks, segment_positions, known_facts)
    )
    if arc.contains_generated_language:
        findings.append(_finding("generated-language", arc.episode_arc_id))
    if not arc.source_references or not arc.decision_trace:
        findings.append(_finding("missing-arc-traceability", arc.episode_arc_id))
    if arc.arc_fingerprint != artifact_fingerprint(arc):
        findings.append(_finding("arc-fingerprint-mismatch", arc.episode_arc_id))
    return tuple(findings)


def _validate_stabilization(
    step: ArcStep, segments: tuple[SegmentPlan, ...]
) -> list[CompositionValidationFinding]:
    findings: list[CompositionValidationFinding] = []
    reasons = set(step.reason_references) | set(step.source_rule_references)
    if not reasons:
        findings.append(
            _finding(
                "stabilization-without-reason",
                step.arc_step_id,
                blocking=False,
                review=True,
            )
        )
    forbidden = {
        "relief",
        "reset",
        "false-resolution",
        "emotional-reassurance",
        "hide-unresolved-facts",
    }
    if reasons & forbidden:
        blocking = bool(reasons & {"false-resolution", "hide-unresolved-facts"})
        findings.append(
            _finding(
                "invalid-stabilization-purpose",
                step.arc_step_id,
                blocking=blocking,
                review=not blocking,
            )
        )
    referenced = {item.segment_plan_id: item for item in segments}
    if (
        any(
            "legal" in risk or "attribution" in risk or "unresolved" in risk
            for segment_id in step.segment_references
            for risk in referenced.get(segment_id, _empty_segment()).risk_references
        )
        and "preserve-unresolved-constraints" not in reasons
    ):
        findings.append(
            _finding("stabilization-constraint-preservation", step.arc_step_id)
        )
    return findings


def _empty_segment():
    class Empty:
        risk_references: tuple[str, ...] = ()

    return Empty()


def _validate_arc_tone(
    arc: EpisodeArc, tone: ToneProgression, segments: tuple[SegmentPlan, ...]
) -> list[CompositionValidationFinding]:
    findings: list[CompositionValidationFinding] = []
    if tone.episode_arc_id != arc.episode_arc_id:
        findings.append(_finding("tone-arc-mismatch", arc.episode_arc_id))
    step_map = {item.arc_step_id: item for item in arc.arc_steps}
    sensitive = {
        item.segment_plan_id
        for item in segments
        if any(
            "sensitivity" in risk or "dignity" in risk or "grave" in risk
            for risk in item.risk_references
        )
    }
    for item in tone.ordered_tone_steps:
        step = step_map.get(item.arc_step_reference)
        if step is None:
            findings.append(_finding("unknown-tone-arc-step", item.tone_step_id))
        elif (
            step.arc_function == ArcFunction.RELIEF
            and item.segment_reference in sensitive
        ):
            findings.append(_finding("sensitive-relief-conflict", item.tone_step_id))
        elif (
            step.arc_function == ArcFunction.PEAK and item.intensity == ArcIntensity.LOW
        ):
            findings.append(
                _finding(
                    "peak-tone-ambiguity",
                    item.tone_step_id,
                    blocking=False,
                    review=True,
                )
            )
    return findings


def _validate_arc_transitions(
    arc: EpisodeArc,
    transitions: tuple[TransitionPlan, ...],
    segment_positions: dict[str, int],
) -> list[CompositionValidationFinding]:
    findings: list[CompositionValidationFinding] = []
    step_ids = set(arc.ordered_arc_step_ids)
    step_positions = {item.arc_step_id: item.position for item in arc.arc_steps}
    for item in transitions:
        if (
            item.from_segment_id not in segment_positions
            or item.to_segment_id not in segment_positions
        ):
            findings.append(
                _finding("unknown-transition-segment", item.transition_plan_id)
            )
        elif (
            segment_positions[item.to_segment_id]
            - segment_positions[item.from_segment_id]
            != 1
        ):
            findings.append(_finding("nonadjacent-transition", item.transition_plan_id))
        if (
            item.from_arc_step_reference not in step_ids
            or item.to_arc_step_reference not in step_ids
        ):
            findings.append(
                _finding("unknown-transition-arc-step", item.transition_plan_id)
            )
        elif (
            step_positions[item.to_arc_step_reference]
            - step_positions[item.from_arc_step_reference]
            != 1
        ):
            findings.append(_finding("nonadjacent-transition", item.transition_plan_id))
        if not item.arc_compatibility:
            findings.append(
                _finding(
                    "transition-arc-conflict",
                    item.transition_plan_id,
                    blocking=False,
                    review=True,
                )
            )
        if "causation" not in item.prohibited_implications:
            findings.append(
                _finding("unsupported-causation-boundary", item.transition_plan_id)
            )
        if item.contains_generated_language:
            findings.append(_finding("generated-language", item.transition_plan_id))
    return findings


def _validate_arc_callbacks(
    arc: EpisodeArc,
    callbacks: tuple[CallbackPlan, ...],
    segment_positions: dict[str, int],
    known_facts: set[str],
) -> list[CompositionValidationFinding]:
    findings: list[CompositionValidationFinding] = []
    step_ids = set(arc.ordered_arc_step_ids)
    for item in callbacks:
        if (
            item.arc_setup_step_reference not in step_ids
            or item.arc_resolution_step_reference not in step_ids
        ):
            findings.append(
                _finding("unknown-callback-arc-step", item.callback_plan_id)
            )
        if segment_positions.get(
            item.setup_segment_id, 10**9
        ) >= segment_positions.get(item.resolution_segment_id, -1):
            findings.append(_finding("callback-order-invalid", item.callback_plan_id))
        if not item.shared_context_references or not item.factual_continuity_references:
            findings.append(
                _finding("callback-continuity-missing", item.callback_plan_id)
            )
        elif not set(item.factual_continuity_references).issubset(known_facts):
            findings.append(
                _finding("callback-factual-continuity-unknown", item.callback_plan_id)
            )
        if not item.arc_compatibility:
            findings.append(
                _finding(
                    "callback-arc-conflict",
                    item.callback_plan_id,
                    blocking=False,
                    review=True,
                )
            )
    return findings


def validate_composition_plan(
    plan: CompositionPlan, bundle: CompositionInputBundle
) -> tuple[CompositionValidationFinding, ...]:
    findings = list(validate_input_bundle(bundle))
    segment_ids = [item.segment_plan_id for item in plan.segment_plans]
    approved = {
        f"segment-plan-{item.segment_id}": item for item in bundle.approved_segments
    }
    if set(segment_ids) != set(approved):
        findings.append(
            _finding("approved-membership-mismatch", plan.composition_plan_id)
        )
    if segment_ids != list(plan.ordered_segment_ids):
        findings.append(
            _finding("plan-segment-order-mismatch", plan.composition_plan_id)
        )
    if [item.position for item in plan.segment_plans] != list(
        range(1, len(plan.segment_plans) + 1)
    ):
        findings.append(
            _finding("plan-segment-position-invalid", plan.composition_plan_id)
        )
    for segment in plan.segment_plans:
        source = approved.get(segment.segment_plan_id)
        if source and (
            segment.story_reference != source.story_reference
            or segment.event_reference != source.event_reference
            or segment.position != source.position
        ):
            findings.append(
                _finding("segment-lineage-mismatch", segment.segment_plan_id)
            )
        if source:
            allowed_facts = set(source.fact_references) | set(
                source.attribution_references
            )
            if any(
                not set(beat.source_fact_references).issubset(allowed_facts)
                for beat in segment.beat_sequence.beats
            ):
                findings.append(
                    _finding("unsupported-beat-fact", segment.segment_plan_id)
                )
        findings.extend(validate_beat_sequence(segment.beat_sequence))
        if segment.contains_generated_language:
            findings.append(_finding("generated-language", segment.segment_plan_id))
        if segment.segment_fingerprint != artifact_fingerprint(segment):
            findings.append(
                _finding("segment-fingerprint-mismatch", segment.segment_plan_id)
            )
    findings.extend(
        validate_episode_arc(
            plan.episode_arc,
            plan.segment_plans,
            plan.tone_progression,
            plan.transition_plans,
            plan.callback_plans,
        )
    )
    findings.extend(_validate_auxiliary_fingerprints(plan))
    if (
        plan.composition_engine_id != COMPOSITION_ENGINE_ID
        or plan.composition_engine_version != COMPOSITION_ENGINE_VERSION
    ):
        findings.append(
            _finding("composition-engine-identity", plan.composition_plan_id)
        )
    if (
        plan.input_bundle_id != bundle.input_bundle_id
        or plan.input_fingerprint != bundle.input_fingerprint
    ):
        findings.append(_finding("composition-input-lineage", plan.composition_plan_id))
    trace_outputs = {
        item.output_reference for item in plan.guidance_traceability.entries
    }
    required_trace = set(segment_ids) | set(plan.episode_arc.ordered_arc_step_ids)
    if not required_trace.issubset(trace_outputs):
        findings.append(
            _finding("missing-guidance-traceability", plan.composition_plan_id)
        )
    if plan.contains_generated_language:
        findings.append(_finding("generated-language", plan.composition_plan_id))
    for unresolved in plan.unresolved_constraints:
        if unresolved.blocking or unresolved.severity == FindingSeverity.ERROR:
            findings.append(
                _finding(
                    "unresolved-mandatory-constraint",
                    unresolved.unresolved_constraint_id,
                )
            )
        elif unresolved.editor_review_required:
            findings.append(
                _finding(
                    "unresolved-review-constraint",
                    unresolved.unresolved_constraint_id,
                    blocking=False,
                    review=True,
                )
            )
    reported_codes = {item.finding_code for item in plan.validation_findings}
    computed_codes = {item.finding_code for item in findings}
    if reported_codes != computed_codes:
        findings.append(
            _finding("validation-findings-mismatch", plan.composition_plan_id)
        )
    if plan.composition_fingerprint != artifact_fingerprint(plan):
        findings.append(
            _finding("composition-fingerprint-mismatch", plan.composition_plan_id)
        )
    calculated = derive_readiness(bundle, tuple(findings))
    if plan.readiness != calculated:
        findings.append(_finding("readiness-mismatch", plan.composition_plan_id))
    return tuple(findings)


def _validate_auxiliary_fingerprints(
    plan: CompositionPlan,
) -> tuple[CompositionValidationFinding, ...]:
    findings: list[CompositionValidationFinding] = []
    collections = (
        (plan.transition_plans, "transition_plan_id", "transition_fingerprint"),
        (plan.callback_plans, "callback_plan_id", "callback_fingerprint"),
        (plan.editorial_priorities, "priority_id", "priority_fingerprint"),
        (plan.rhythm_guidance, "rhythm_guidance_id", "rhythm_fingerprint"),
        (plan.delivery_constraints, "constraint_id", "constraint_fingerprint"),
        (plan.decisions, "decision_id", "decision_fingerprint"),
        (plan.conflicts, "conflict_id", "conflict_fingerprint"),
    )
    for items, identity_field, fingerprint_field in collections:
        for item in items:
            if getattr(item, fingerprint_field) != artifact_fingerprint(item):
                findings.append(
                    _finding(
                        "nested-fingerprint-mismatch", getattr(item, identity_field)
                    )
                )
    singular = (
        (plan.tone_progression, "tone_progression_id", "tone_fingerprint"),
        (plan.emphasis_map, "emphasis_map_id", "emphasis_fingerprint"),
        (
            plan.guidance_traceability,
            "traceability_id",
            "traceability_fingerprint",
        ),
    )
    for item, identity_field, fingerprint_field in singular:
        if getattr(item, fingerprint_field) != artifact_fingerprint(item):
            findings.append(
                _finding("nested-fingerprint-mismatch", getattr(item, identity_field))
            )
    return tuple(findings)


def accept_composition_plan(
    plan: CompositionPlan, bundle: CompositionInputBundle
) -> CompositionPlan:
    findings = validate_composition_plan(plan, bundle)
    if findings:
        raise CompositionValidationError(
            "; ".join(sorted({item.finding_code for item in findings}))
        )
    return plan


__all__ = (
    "CompositionValidationError",
    "accept_composition_plan",
    "validate_beat_sequence",
    "validate_composition_plan",
    "validate_episode_arc",
    "validate_input_bundle",
)
