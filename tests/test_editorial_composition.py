"""Focused tests for Scout Editor Module 2.8."""

import pytest
from pydantic import ValidationError

from pastila_scout.editor.composition import *


def _dependency(module_id, readiness=CompositionReadiness.READY):
    return UpstreamDependencyReference(
        dependency_id=f"dependency-{module_id}",
        module_id=module_id,
        module_version="1.0.0",
        semantic_fingerprint=(module_id.encode().hex() + "0" * 64)[:64],
        readiness=readiness,
    )


def _segment(
    segment_id,
    position,
    role,
    *,
    arc_function=None,
    grave=False,
    legal=False,
):
    return ApprovedSegmentInput(
        segment_id=segment_id,
        event_reference=f"event-{position}",
        story_reference=f"story-{position}",
        position=position,
        role=role,
        fact_references=(f"fact-{position}-1", f"fact-{position}-2"),
        source_provenance_references=(f"source-{position}",),
        risk_references=("grave-material",) if grave else (),
        grave=grave,
        unresolved_fact_references=(f"unresolved-{position}",) if legal else (),
        legal_constraint_references=(f"legal-{position}",) if legal else (),
        attribution_references=(f"attribution-{position}",) if legal else (),
        explicit_arc_function=arc_function,
    )


def _bundle(*, dependency_readiness=CompositionReadiness.READY, stabilization=False):
    segments = (
        _segment("opening", 1, SegmentRole.OPENING),
        _segment(
            "middle",
            2,
            SegmentRole.PRIMARY,
            arc_function="stabilization" if stabilization else None,
            legal=stabilization,
        ),
        _segment("closing", 3, SegmentRole.CLOSING),
    )
    values = {
        "input_bundle_id": "input-1",
        "episode_reference": "episode-1",
        "selection_reference": "selection-1",
        "blueprint_reference": "blueprint-1",
        "memory_reference": "memory-1",
        "persona_reference": "persona-1",
        "philosophy_reference": "philosophy-1",
        "decision_framework_reference": "decision-1",
        "voice_reference": "voice-1",
        "audience_reference": "audience-1",
        "story_architecture_reference": "architecture-1",
        "spoken_communication_reference": "communication-1",
        "romanian_conversational_reference": "romanian-1",
        "language_guidance_reference": "guidance-1",
        "upstream_dependencies": tuple(
            _dependency(
                module,
                dependency_readiness if index == 0 else CompositionReadiness.READY,
            )
            for index, module in enumerate(REQUIRED_UPSTREAM_MODULES)
        ),
        "approved_segments": segments,
        "mandatory_story_references": tuple(item.story_reference for item in segments),
        "input_fingerprint": "0" * 64,
    }
    probe = CompositionInputBundle(**values)
    values["input_fingerprint"] = artifact_fingerprint(probe)
    return CompositionInputBundle(**values)


def test_contracts_are_immutable_strict_and_versioned():
    bundle = _bundle()
    assert bundle.version == "1.0.0"
    assert bundle.canonical_identifier == "input-1"
    with pytest.raises(ValidationError):
        bundle.episode_reference = "changed"
    with pytest.raises(ValidationError):
        CompositionInputBundle(**bundle.model_dump(), unknown=True)


@pytest.mark.parametrize("value", tuple(item.value for item in ArcFunction))
def test_all_baseline_arc_functions(value):
    step = _arc_step(value)
    assert step.arc_function == value


def test_custom_arc_function_validation():
    assert _arc_step("custom:second-build").arc_function == "custom:second-build"
    with pytest.raises(ValidationError):
        _arc_step("custom:Bad Value")


@pytest.mark.parametrize("value", tuple(ArcIntensity))
def test_all_arc_intensities(value):
    assert _arc_step("build", intensity=value).intensity == value


def _arc_step(function="build", intensity=ArcIntensity.MODERATE):
    values = {
        "arc_step_id": "step-1",
        "position": 1,
        "arc_function": function,
        "segment_references": ("segment-plan-opening",),
        "intensity": intensity,
        "source_rule_references": ("story-architecture",),
        "reason_references": ("structural-role",),
        "decision_trace": ("decision-1",),
        "arc_step_fingerprint": "0" * 64,
    }
    probe = ArcStep(**values)
    values["arc_step_fingerprint"] = artifact_fingerprint(probe)
    return ArcStep(**values)


def _reseal(value, fingerprint_field, **updates):
    probe = value.model_copy(update={**updates, fingerprint_field: "0" * 64}, deep=True)
    return probe.model_copy(
        update={fingerprint_field: artifact_fingerprint(probe)}, deep=True
    )


def test_composition_is_deterministic_structural_and_complete():
    first = compose(_bundle())
    second = compose(_bundle().model_copy(deep=True))
    assert first == second
    assert first.composition_fingerprint == second.composition_fingerprint
    assert first.ordered_segment_ids == tuple(
        item.segment_plan_id for item in first.segment_plans
    )
    assert len(first.episode_arc.segment_bindings) == len(first.segment_plans)
    assert all(not item.contains_generated_language for item in first.segment_plans)
    assert validate_composition_plan(first, _bundle()) == ()


def test_rendering_and_fingerprinting_are_canonical_unicode_safe():
    bundle = _bundle()
    renamed = bundle.model_copy(update={"episode_reference": "Pastila Acidă"})
    assert "Pastila Acidă" in renamed.render()
    dependency = bundle.upstream_dependencies[0]
    reversed_bundle = bundle.model_copy(
        update={"upstream_dependencies": tuple(reversed(bundle.upstream_dependencies))}
    )
    assert artifact_fingerprint(bundle) == artifact_fingerprint(reversed_bundle)
    assert (
        dependency.semantic_sha256 == dependency.model_copy(deep=True).semantic_sha256
    )


def test_meaningful_segment_order_changes_fingerprint():
    bundle = _bundle()
    changed = bundle.model_copy(
        update={"approved_segments": tuple(reversed(bundle.approved_segments))}
    )
    assert artifact_fingerprint(bundle) != artifact_fingerprint(changed)


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (CompositionReadiness.BLOCKED, CompositionReadiness.BLOCKED),
        (
            CompositionReadiness.REQUIRES_EDITOR_REVIEW,
            CompositionReadiness.REQUIRES_EDITOR_REVIEW,
        ),
        (
            CompositionReadiness.READY_WITH_ADVISORIES,
            CompositionReadiness.READY_WITH_ADVISORIES,
        ),
        (CompositionReadiness.READY, CompositionReadiness.READY),
    ),
)
def test_dependency_readiness_propagates(state, expected):
    bundle = _bundle(dependency_readiness=state)
    assert derive_readiness(bundle, ()) == expected


def test_missing_duplicate_and_mutated_dependencies_rejected():
    bundle = _bundle()
    assert any(
        item.finding_code == "missing-dependency"
        for item in validate_input_bundle(
            bundle.model_copy(
                update={"upstream_dependencies": bundle.upstream_dependencies[:-1]}
            )
        )
    )
    duplicate = bundle.upstream_dependencies + (bundle.upstream_dependencies[0],)
    assert any(
        item.finding_code == "duplicate-dependency"
        for item in validate_input_bundle(
            bundle.model_copy(update={"upstream_dependencies": duplicate})
        )
    )
    mutated = bundle.upstream_dependencies[0].model_copy(
        update={"canonical_mutation": True}
    )
    assert any(
        item.finding_code == "canonical-mutation"
        for item in validate_input_bundle(
            bundle.model_copy(
                update={
                    "upstream_dependencies": (mutated,)
                    + bundle.upstream_dependencies[1:]
                }
            )
        )
    )


def test_episode_arc_positions_bindings_and_order_are_enforced():
    bundle = _bundle()
    plan = compose(bundle)
    arc = plan.episode_arc
    bad_steps = tuple(
        item.model_copy(update={"position": 3}) if index == 1 else item
        for index, item in enumerate(arc.arc_steps)
    )
    findings = validate_episode_arc(
        arc.model_copy(update={"arc_steps": bad_steps}), plan.segment_plans
    )
    assert any(item.finding_code == "noncontiguous-arc-steps" for item in findings)
    missing = arc.model_copy(update={"segment_bindings": arc.segment_bindings[:-1]})
    findings = validate_episode_arc(missing, plan.segment_plans)
    assert any(item.finding_code == "invalid-primary-arc-binding" for item in findings)


def test_beat_dependency_and_fingerprint_validation():
    plan = compose(_bundle())
    sequence = plan.segment_plans[0].beat_sequence
    beat = sequence.beats[0].model_copy(update={"dependency_beat_ids": ("unknown",)})
    findings = validate_beat_sequence(
        sequence.model_copy(update={"beats": (beat,) + sequence.beats[1:]})
    )
    assert any(item.finding_code == "unknown-beat-dependency" for item in findings)


def test_stabilization_is_distinct_and_preserves_constraints():
    plan = compose(_bundle(stabilization=True))
    step = plan.episode_arc.arc_steps[1]
    assert step.arc_function == ArcFunction.STABILIZATION
    assert "preserve-unresolved-constraints" in step.reason_references
    assert plan.tone_progression.ordered_tone_steps[1].tone_mode == "neutral"
    assert validate_composition_plan(plan, _bundle(stabilization=True)) == ()


def test_language_guidance_lifecycle_and_scope_are_preserved():
    bundle = _bundle()
    guidance = tuple(
        CompositionGuidanceReference(
            guidance_id=f"guidance-{status.value}",
            preference_reference=f"preference-{status.value}",
            status=status,
            scope_references=("middle",),
            source_fingerprint="c" * 64,
        )
        for status in GuidanceStatus
    )
    values = bundle.model_dump()
    values.update(language_guidance=guidance, input_fingerprint="0" * 64)
    probe = CompositionInputBundle(**values)
    values["input_fingerprint"] = artifact_fingerprint(probe)
    guided = CompositionInputBundle(**values)
    plan = compose(guided)
    middle = plan.segment_plans[1]
    assert set(middle.guidance_references) == {
        "guidance-established",
        "guidance-explicit_editor_rule",
    }
    assert not plan.segment_plans[0].guidance_references
    traced = {
        item.output_reference: item.application_type
        for item in plan.guidance_traceability.entries
        if item.output_type == "language-guidance"
    }
    assert traced["guidance-emerging"] == GuidanceApplication.REQUIRES_EDITOR_REVIEW
    assert traced["guidance-archived"] == GuidanceApplication.NOT_APPLICABLE
    assert traced["guidance-deprecated"] == GuidanceApplication.NOT_APPLICABLE
    assert traced["guidance-rejected"] == GuidanceApplication.NOT_APPLICABLE


def test_callback_setup_must_precede_resolution():
    bundle = _bundle()
    plan = compose(bundle)
    values = {
        "callback_plan_id": "callback-1",
        "setup_segment_id": plan.segment_plans[2].segment_plan_id,
        "resolution_segment_id": plan.segment_plans[0].segment_plan_id,
        "setup_beat_reference": plan.segment_plans[2].beat_sequence.beats[0].beat_id,
        "resolution_beat_reference": plan.segment_plans[0]
        .beat_sequence.beats[0]
        .beat_id,
        "shared_context_references": ("context-1",),
        "factual_continuity_references": ("fact-1",),
        "callback_role": "resolution",
        "arc_setup_step_reference": plan.episode_arc.arc_steps[2].arc_step_id,
        "arc_resolution_step_reference": plan.episode_arc.arc_steps[0].arc_step_id,
        "arc_contribution": "closure",
        "decision_trace": ("decision-callback-1",),
        "callback_fingerprint": "0" * 64,
    }
    probe = CallbackPlan(**values)
    values["callback_fingerprint"] = artifact_fingerprint(probe)
    callback = CallbackPlan(**values)
    findings = validate_episode_arc(
        plan.episode_arc,
        plan.segment_plans,
        callbacks=(callback,),
    )
    assert any(item.finding_code == "callback-order-invalid" for item in findings)


@pytest.mark.parametrize("bad_reason", ("relief", "reset", "false-resolution"))
def test_invalid_stabilization_purpose_is_visible(bad_reason):
    bundle = _bundle(stabilization=True)
    plan = compose(bundle)
    step = plan.episode_arc.arc_steps[1]
    bad = step.model_copy(update={"reason_references": (bad_reason,)})
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                bad,
                plan.episode_arc.arc_steps[2],
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(
        item.finding_code == "invalid-stabilization-purpose" for item in findings
    )


def test_sensitive_relief_is_blocked():
    bundle = _bundle()
    sensitive = _segment(
        "middle",
        2,
        SegmentRole.COMIC_RELIEF,
        arc_function="relief",
        grave=True,
    )
    segments = (bundle.approved_segments[0], sensitive, bundle.approved_segments[2])
    values = bundle.model_dump()
    values.update(approved_segments=segments, input_fingerprint="0" * 64)
    probe = CompositionInputBundle(**values)
    values["input_fingerprint"] = artifact_fingerprint(probe)
    grave_bundle = CompositionInputBundle(**values)
    plan = compose(grave_bundle)
    assert plan.tone_progression.ordered_tone_steps[1].tone_mode == "serious"
    findings = validate_episode_arc(
        plan.episode_arc, plan.segment_plans, plan.tone_progression
    )
    assert any(item.finding_code == "sensitive-relief-conflict" for item in findings)


def test_manual_readiness_and_generated_language_cannot_bypass_validation():
    bundle = _bundle()
    plan = compose(bundle)
    invalid = plan.model_copy(
        update={
            "readiness": CompositionReadiness.READY,
            "contains_generated_language": True,
        }
    )
    findings = validate_composition_plan(invalid, bundle)
    codes = {item.finding_code for item in findings}
    assert "generated-language" in codes
    assert "readiness-mismatch" in codes


def test_no_provider_persistence_network_or_callback_registry_dependencies():
    import pastila_scout.editor.composition as package

    modules = " ".join(
        getattr(getattr(package, name), "__module__", "") for name in dir(package)
    )
    for forbidden in ("openai", "httpx", "sqlite", "requests", "callbackregistry"):
        assert forbidden not in modules.lower()


def test_exact_dependency_identity_and_version_are_enforced():
    bundle = _bundle()
    extra = _dependency("unapproved-upstream")
    findings = validate_input_bundle(
        bundle.model_copy(
            update={"upstream_dependencies": bundle.upstream_dependencies + (extra,)}
        )
    )
    assert any(item.finding_code == "unexpected-dependency" for item in findings)
    incompatible = bundle.upstream_dependencies[0].model_copy(
        update={"module_version": "2.0.0"}
    )
    findings = validate_input_bundle(
        bundle.model_copy(
            update={
                "upstream_dependencies": (incompatible,)
                + bundle.upstream_dependencies[1:]
            }
        )
    )
    assert any(
        item.finding_code == "incompatible-dependency-version" for item in findings
    )


def test_arc_membership_matches_one_primary_binding():
    plan = compose(_bundle())
    arc = plan.episode_arc
    duplicated = _reseal(
        arc.arc_steps[1],
        "arc_step_fingerprint",
        segment_references=(
            arc.arc_steps[0].segment_references[0],
            arc.arc_steps[1].segment_references[0],
        ),
    )
    changed = arc.model_copy(
        update={"arc_steps": (arc.arc_steps[0], duplicated, arc.arc_steps[2])}
    )
    findings = validate_episode_arc(changed, plan.segment_plans)
    assert any(
        item.finding_code == "contradictory-arc-step-membership" for item in findings
    )


def test_empty_structural_boundary_requires_permission():
    plan = compose(_bundle())
    step = _reseal(
        plan.episode_arc.arc_steps[1],
        "arc_step_fingerprint",
        segment_references=(),
        required=False,
        structural_boundary_permitted=False,
    )
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                step,
                plan.episode_arc.arc_steps[2],
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(
        item.finding_code == "unauthorized-structural-boundary" for item in findings
    )


def test_stabilization_missing_reason_and_source_requires_review():
    plan = compose(_bundle(stabilization=True))
    step = plan.episode_arc.arc_steps[1].model_copy(
        update={"reason_references": (), "source_rule_references": ()}
    )
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                step,
                plan.episode_arc.arc_steps[2],
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(item.finding_code == "stabilization-without-reason" for item in findings)


def test_stabilization_cannot_hide_mandatory_constraints():
    plan = compose(_bundle(stabilization=True))
    step = _reseal(
        plan.episode_arc.arc_steps[1],
        "arc_step_fingerprint",
        reason_references=("consolidate-confirmed-facts",),
    )
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                step,
                plan.episode_arc.arc_steps[2],
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(
        item.finding_code == "stabilization-constraint-preservation"
        for item in findings
    )


def test_stabilization_to_resolution_requires_upstream_support():
    plan = compose(_bundle(stabilization=True))
    resolution = _reseal(
        plan.episode_arc.arc_steps[2],
        "arc_step_fingerprint",
        arc_function="resolution",
        source_rule_references=("story-architecture",),
    )
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                plan.episode_arc.arc_steps[1],
                resolution,
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(
        item.finding_code == "unsupported-stabilization-resolution"
        and item.editor_review_required
        for item in findings
    )


def test_serious_high_gravity_stabilization_is_valid():
    plan = compose(_bundle(stabilization=True))
    tone_step = plan.tone_progression.ordered_tone_steps[1].model_copy(
        update={
            "tone_mode": "serious",
            "intensity": ArcIntensity.HIGH,
            "gravity_level": PriorityLevel.HIGH,
        }
    )
    tone = _reseal(
        plan.tone_progression,
        "tone_fingerprint",
        ordered_tone_steps=(
            plan.tone_progression.ordered_tone_steps[0],
            tone_step,
            plan.tone_progression.ordered_tone_steps[2],
        ),
    )
    findings = validate_episode_arc(plan.episode_arc, plan.segment_plans, tone)
    assert not any("stabilization" in item.finding_code for item in findings)


def test_generated_language_and_prose_are_rejected_by_models():
    values = _arc_step().model_dump()
    values["contains_generated_language"] = True
    with pytest.raises(ValidationError, match="generated language"):
        ArcStep(**values)
    values = _arc_step().model_dump()
    values["reason_references"] = ("This is generated episode prose.",)
    with pytest.raises(ValidationError, match="reference or controlled token"):
        ArcStep(**values)


def test_nonadjacent_transition_is_rejected():
    plan = compose(_bundle())
    transition = _reseal(
        plan.transition_plans[0],
        "transition_fingerprint",
        to_segment_id=plan.segment_plans[2].segment_plan_id,
        to_arc_step_reference=plan.episode_arc.arc_steps[2].arc_step_id,
    )
    findings = validate_episode_arc(
        plan.episode_arc,
        plan.segment_plans,
        transitions=(transition,),
    )
    assert any(item.finding_code == "nonadjacent-transition" for item in findings)


def test_unresolved_mandatory_constraint_blocks_readiness():
    bundle = _bundle()
    plan = compose(bundle)
    unresolved = UnresolvedConstraint(
        unresolved_constraint_id="unresolved-1",
        constraint_reference="legal-1",
        affected_references=(plan.segment_plans[1].segment_plan_id,),
        reason_code="mandatory-legal-boundary",
        severity=FindingSeverity.ERROR,
        editor_review_required=False,
        blocking=True,
        source_references=("decision-framework",),
    )
    invalid = _reseal(
        plan,
        "composition_fingerprint",
        unresolved_constraints=(unresolved,),
        readiness=CompositionReadiness.READY,
    )
    codes = {item.finding_code for item in validate_composition_plan(invalid, bundle)}
    assert "unresolved-mandatory-constraint" in codes
    assert "readiness-mismatch" in codes


def test_public_api_excludes_imported_and_private_helpers():
    import pastila_scout.editor.composition as package

    assert not hasattr(package, "BaseModel")
    assert not hasattr(package, "_sealed")
    assert package.COMPOSITION_ENGINE_VERSION == "1.0.0"


def test_editorial_precedence_is_complete_and_ordered():
    assert EDITORIAL_PRECEDENCE == (
        "factual-integrity",
        "legal-precision",
        "attribution",
        "editor-in-chief",
        "safety-and-dignity",
        "approved-editorial-decision",
        "story-architecture",
        "spoken-communication",
        "romanian-conversational",
        "persona-and-philosophy",
        "editorial-voice",
        "audience",
        "established-learned-guidance",
        "emerging-learned-guidance",
        "optional-composition-optimization",
    )


def test_nested_semantics_are_canonical_and_ignore_volatile_fields():
    left = {
        "payload": {"z": {"beta", "alpha"}, "a": {"value": 1}},
        "generated_at": "2026-01-01T00:00:00Z",
        "composition_fingerprint": "a" * 64,
    }
    right = {
        "composition_fingerprint": "b" * 64,
        "generated_at": "2030-01-01T00:00:00Z",
        "payload": {"a": {"value": 1}, "z": {"alpha", "beta"}},
    }
    assert canonical_json(left) == canonical_json(right)
    assert artifact_fingerprint(left) == artifact_fingerprint(right)


def test_forced_peak_without_explicit_support_requires_review():
    plan = compose(_bundle())
    step = _reseal(
        plan.episode_arc.arc_steps[1],
        "arc_step_fingerprint",
        arc_function=ArcFunction.PEAK,
        source_rule_references=("story-architecture",),
    )
    arc = plan.episode_arc.model_copy(
        update={
            "arc_steps": (
                plan.episode_arc.arc_steps[0],
                step,
                plan.episode_arc.arc_steps[2],
            )
        }
    )
    findings = validate_episode_arc(arc, plan.segment_plans)
    assert any(
        item.finding_code == "unsupported-forced-peak" and item.editor_review_required
        for item in findings
    )


def test_transition_requires_unsupported_causation_boundary():
    plan = compose(_bundle())
    transition = _reseal(
        plan.transition_plans[0],
        "transition_fingerprint",
        prohibited_implications=(),
    )
    findings = validate_episode_arc(
        plan.episode_arc,
        plan.segment_plans,
        transitions=(transition,),
    )
    assert any(
        item.finding_code == "unsupported-causation-boundary" for item in findings
    )


def test_beat_cannot_introduce_fact_outside_approved_segment():
    bundle = _bundle()
    plan = compose(bundle)
    beat = (
        plan.segment_plans[0]
        .beat_sequence.beats[0]
        .model_copy(update={"source_fact_references": ("invented-fact",)})
    )
    sequence = plan.segment_plans[0].beat_sequence.model_copy(
        update={"beats": (beat,) + plan.segment_plans[0].beat_sequence.beats[1:]}
    )
    segment = plan.segment_plans[0].model_copy(update={"beat_sequence": sequence})
    changed = plan.model_copy(
        update={"segment_plans": (segment,) + plan.segment_plans[1:]}
    )
    assert any(
        item.finding_code == "unsupported-beat-fact"
        for item in validate_composition_plan(changed, bundle)
    )


def test_stored_validation_findings_cannot_bypass_computed_validation():
    bundle = _bundle()
    plan = compose(bundle)
    injected = CompositionValidationFinding(
        finding_id="finding-external",
        finding_code="external-claim",
        severity=FindingSeverity.WARNING,
        artifact_reference=plan.composition_plan_id,
        message_reference="external-claim",
        blocking=False,
        editor_review_required=False,
    )
    changed = plan.model_copy(update={"validation_findings": (injected,)})
    assert any(
        item.finding_code == "validation-findings-mismatch"
        for item in validate_composition_plan(changed, bundle)
    )
