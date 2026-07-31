"""Cross-contract safety validation for Story Architecture."""

from __future__ import annotations

import re

from pastila_scout.editor.audience import AudienceAssessment, AudienceModel
from pastila_scout.editor.audience.fingerprint import assessment_fingerprint
from pastila_scout.editor.audience.validator import validate_audience_assessment
from pastila_scout.editor.decision import (
    EditorialAction,
    EditorialDecisionPlan,
    FactImportance,
)
from pastila_scout.editor.decision.fingerprint import decision_plan_fingerprint
from pastila_scout.editor.decision.validator import validate_decision_plan
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA
from pastila_scout.editor.story.defaults import (
    CANONICAL_PATTERN_IDS,
    CANONICAL_PRINCIPLE_IDS,
)
from pastila_scout.editor.story.models import (
    NarrativeFunction,
    NarrativeStage,
    PayoffType,
    StoryArchitecture,
    StoryArchitecturePlan,
    StoryUnitType,
    TransitionRelationshipType,
)
from pastila_scout.editor.story.readiness import determine_story_readiness
from pastila_scout.editor.voice import SatiricalOpportunity, SatiricalVoice
from pastila_scout.editor.voice.validator import validate_satirical_opportunity

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_CORE_IDS = {
    "what_happened",
    "involved_parties",
    "why_it_matters",
    "consequence",
    "central_tension",
    "factual_boundaries",
    "secondary_angles",
}


class StoryArchitectureValidationError(ValueError):
    pass


def validate_story_architecture(architecture: StoryArchitecture) -> StoryArchitecture:
    errors = []
    if not _SEMVER.fullmatch(architecture.version):
        errors.append("Story Architecture version must use semantic versioning")
    for values, label in (
        (architecture.principles, "principle"),
        (architecture.patterns, "pattern"),
    ):
        identifiers = [getattr(x, f"{label}_id") for x in values]
        orders = [x.order for x in values]
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"duplicate architecture {label} identifiers")
        if len(orders) != len(set(orders)):
            errors.append(f"architecture {label} order must be unique")
    if {item.principle_id for item in architecture.principles} != set(
        CANONICAL_PRINCIPLE_IDS
    ):
        errors.append("all canonical Story Architecture principles are required")
    if {item.pattern_id for item in architecture.patterns} != set(
        CANONICAL_PATTERN_IDS
    ):
        errors.append("all canonical Story Patterns are required")
    if tuple(architecture.stage_order) != tuple(NarrativeStage):
        errors.append("canonical narrative stage order is incomplete or unstable")
    if set(architecture.supported_unit_types) != set(StoryUnitType):
        errors.append("supported Story Unit types are incomplete")
    if set(architecture.supported_functions) != set(NarrativeFunction):
        errors.append("supported narrative functions are incomplete")
    if architecture.emerging_guidance_may_mutate_architecture:
        errors.append("emerging profile guidance cannot mutate canonical architecture")
    if architecture.contains_generation_procedures:
        errors.append("Story Architecture cannot contain generation procedures")
    if errors:
        raise StoryArchitectureValidationError("; ".join(errors))
    return architecture


def _has_cycle(graph):
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, ())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_story_plan(
    plan: StoryArchitecturePlan,
    architecture: StoryArchitecture,
    decision_plan: EditorialDecisionPlan,
    audience_assessment: AudienceAssessment,
    audience_model: AudienceModel,
    voice: SatiricalVoice,
    opportunities: tuple[SatiricalOpportunity, ...] = (),
) -> StoryArchitecturePlan:
    validate_story_architecture(architecture)
    validate_decision_plan(decision_plan, DEFAULT_EDITORIAL_PERSONA)
    validate_audience_assessment(
        audience_assessment, decision_plan, audience_model, voice
    )
    errors = []
    if (
        plan.architecture_id != architecture.architecture_id
        or plan.version != architecture.version
    ):
        errors.append("Story Architecture identity or version mismatch")
    if not _SEMVER.fullmatch(plan.version):
        errors.append("Story Architecture Plan version must use semantic versioning")
    if plan.decision_plan_id != decision_plan.plan_id:
        errors.append("Decision Plan identifier mismatch")
    if plan.audience_assessment_id != audience_assessment.assessment_id:
        errors.append("Audience Assessment identifier mismatch")
    if plan.source_material_fingerprint != decision_plan.source_material_fingerprint:
        errors.append("source material fingerprint mismatch")
    if plan.decision_plan_fingerprint != decision_plan_fingerprint(decision_plan):
        errors.append("Decision Plan fingerprint mismatch")
    if plan.audience_assessment_fingerprint != assessment_fingerprint(
        audience_assessment
    ):
        errors.append("Audience Assessment fingerprint mismatch")
    philosophy = DEFAULT_EDITORIAL_PERSONA.philosophy
    if (plan.persona_id, plan.persona_version) != (
        DEFAULT_EDITORIAL_PERSONA.persona_id,
        DEFAULT_EDITORIAL_PERSONA.version,
    ):
        errors.append("Editorial Persona identity mismatch")
    if (plan.philosophy_id, plan.philosophy_version) != (
        philosophy.philosophy_id,
        philosophy.version,
    ):
        errors.append("Editorial Philosophy identity mismatch")
    if (plan.voice_id, plan.voice_version) != (voice.voice_id, voice.version):
        errors.append("Satirical Voice identity mismatch")
    if (plan.audience_id, plan.audience_version) != (
        audience_model.audience_id,
        audience_model.version,
    ):
        errors.append("Audience Model identity mismatch")
    pattern_ids = {pattern.pattern_id for pattern in architecture.patterns}
    if plan.selected_pattern.selected_pattern_id not in pattern_ids:
        errors.append("selected Story Pattern is not canonical")
    if plan.selected_pattern.decision_plan_id != decision_plan.plan_id:
        errors.append("Story Pattern Selection Decision Plan mismatch")
    if (
        plan.selected_pattern.audience_assessment_id
        != audience_assessment.assessment_id
    ):
        errors.append("Story Pattern Selection Audience Assessment mismatch")
    units = {x.unit_id: x for x in plan.story_units}
    if len(units) != len(plan.story_units):
        errors.append("duplicate story unit identifiers")
    for values, attribute, label in (
        (plan.transitions, "transition_id", "transition"),
        (plan.secondary_angles, "angle_id", "secondary angle"),
        (plan.context_placements, "placement_id", "context placement"),
        (plan.consequence_plans, "consequence_id", "consequence"),
        (plan.satire_placements, "placement_id", "satire placement"),
        (plan.architecture_risks, "risk_id", "architecture risk"),
    ):
        identifiers = [getattr(item, attribute) for item in values]
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"duplicate {label} identifiers")
    material = {x.material_id: x for x in decision_plan.source_material}
    decisions = {x.decision_id: x for x in decision_plan.decisions}
    if not set(plan.selected_pattern.supporting_decision_ids).issubset(decisions):
        errors.append("Story Pattern Selection references unknown decisions")
    if not set(plan.selected_pattern.supporting_core_element_ids).issubset(_CORE_IDS):
        errors.append("Story Pattern Selection references unknown core elements")
    opportunity_map = {x.opportunity_id: x for x in opportunities}
    for opportunity in opportunities:
        validate_satirical_opportunity(opportunity, decision_plan, voice)
    for unit in plan.story_units:
        if not set(unit.source_material_ids).issubset(material):
            errors.append(f"unit {unit.unit_id} references unknown material")
        if not set(unit.editorial_decision_ids).issubset(decisions):
            errors.append(f"unit {unit.unit_id} references unknown decision")
        if not set(unit.editorial_core_element_ids).issubset(_CORE_IDS):
            errors.append(f"unit {unit.unit_id} references unknown core element")
        if not set(unit.satirical_opportunity_ids).issubset(opportunity_map):
            errors.append(
                f"unit {unit.unit_id} references unknown Satirical Opportunity"
            )
        refs = set(unit.prerequisite_unit_ids) | set(unit.required_context_unit_ids)
        if not refs.issubset(units):
            errors.append(f"unit {unit.unit_id} references unknown prerequisite unit")
        if (
            unit.unit_type.value in {"allegation", "dispute"}
            and not unit.requires_attribution
        ):
            errors.append(f"unit {unit.unit_id} must preserve attribution")
    graph = {x.unit_id: x.prerequisite_unit_ids for x in plan.story_units}
    if _has_cycle(graph):
        errors.append("circular story unit prerequisite graph")
    spine = plan.primary_narrative_spine.ordered_unit_ids
    if plan.primary_spine_count != 1:
        errors.append("exactly one primary narrative spine is required")
    if not set(plan.primary_narrative_spine.editorial_core_element_ids).issubset(
        _CORE_IDS
    ):
        errors.append("primary narrative spine references unknown core elements")
    if not set(spine).issubset(units):
        errors.append("primary narrative spine references unknown units")
    positions = {unit_id: index for index, unit_id in enumerate(spine)}
    for unit_id in spine:
        if unit_id not in units:
            continue
        for prerequisite in units[unit_id].prerequisite_unit_ids:
            if (
                prerequisite in positions
                and positions[prerequisite] >= positions[unit_id]
            ):
                errors.append("primary spine order violates prerequisites")
    if not set(plan.opening_plan.supported_unit_ids).issubset(units):
        errors.append("opening references unsupported units")
    if any(
        unit_id not in set(spine[:2])
        for unit_id in plan.opening_plan.supported_unit_ids
    ):
        errors.append("opening units must begin the primary narrative spine")
    if not any(
        set(units[x].editorial_core_element_ids) & _CORE_IDS
        for x in spine[:2]
        if x in units
    ):
        errors.append("primary Editorial Core must appear early")
    removed_held = {
        mid
        for decision in decision_plan.decisions
        if decision.action
        in {EditorialAction.REMOVE, EditorialAction.HOLD_FOR_VERIFICATION}
        for mid in decision.material_ids
    }
    used_material = {
        mid for unit in plan.story_units for mid in unit.source_material_ids
    }
    used_material |= {
        mid for x in plan.consequence_plans for mid in x.supporting_material_ids
    }
    if used_material & removed_held:
        errors.append("held or removed material cannot re-enter Story Architecture")
    unsafe = {
        mid
        for decision in decision_plan.decisions
        if decision.classification == FactImportance.UNSAFE_WITHOUT_CONTEXT
        and decision.action != EditorialAction.CONTEXTUALIZE
        for mid in decision.material_ids
    }
    if unsafe & used_material:
        errors.append(
            "unsafe material requires contextualization before architecture use"
        )
    indispensable = {
        mid
        for decision in decision_plan.decisions
        if decision.classification == FactImportance.INDISPENSABLE
        for mid in decision.material_ids
    }
    if not indispensable.issubset(used_material):
        errors.append("indispensable factual setup is absent")
    for transition in plan.transitions:
        if transition.from_unit_id not in units or transition.to_unit_id not in units:
            errors.append("transition references unknown units")
        if (
            transition.relationship_type == TransitionRelationshipType.CAUSAL
            and not transition.has_causal_evidence
        ):
            errors.append("causal transition requires causal evidence")
        if transition.distorts_chronology:
            errors.append("chronology distortion is prohibited")
        if transition.to_unit_id in units:
            target = units[transition.to_unit_id]
            if transition.from_unit_id in target.prohibited_predecessor_unit_ids:
                errors.append("transition violates prohibited predecessor constraint")
        if transition.from_unit_id in units:
            source = units[transition.from_unit_id]
            if transition.to_unit_id in source.prohibited_successor_unit_ids:
                errors.append("transition violates prohibited successor constraint")
    for placement in plan.context_placements:
        if (
            not set(placement.context_unit_ids).issubset(units)
            or placement.trigger_unit_id not in units
        ):
            errors.append("context placement references unknown units")
        trigger_position = positions.get(placement.trigger_unit_id, len(spine))
        if any(
            positions.get(unit_id, trigger_position) >= trigger_position
            for unit_id in placement.context_unit_ids
        ):
            errors.append("indispensable context must precede its dependency")
    for placement in plan.satire_placements:
        if not set(placement.satirical_opportunity_ids).issubset(opportunity_map):
            errors.append("satire placement requires valid Satirical Opportunity")
        if not set(placement.prerequisite_unit_ids).issubset(positions):
            errors.append("satire placement prerequisite is missing")
        if not set(placement.target_unit_ids).issubset(units):
            errors.append("satire placement references unknown target units")
        satire_position = min(
            (
                positions.get(unit_id, len(spine))
                for unit_id in placement.target_unit_ids
            ),
            default=len(spine),
        )
        if any(
            positions.get(unit_id, satire_position) >= satire_position
            for unit_id in placement.prerequisite_unit_ids
        ):
            errors.append("satire cannot precede required factual setup")
        for opportunity_id in placement.satirical_opportunity_ids:
            opportunity = opportunity_map.get(opportunity_id)
            if (
                opportunity
                and opportunity.requires_editor_in_chief_review
                and not placement.requires_editor_in_chief_review
            ):
                errors.append(
                    "review-required Satirical Opportunity must propagate review"
                )
    mechanism_uses = [
        mechanism
        for placement in plan.satire_placements
        for mechanism in placement.allowed_mechanisms
    ]
    repeated_mechanism = len(mechanism_uses) != len(set(mechanism_uses))
    fatigue_risk_present = any(
        risk.risk_type.value == "mechanism_repetition"
        for risk in plan.architecture_risks
    )
    if repeated_mechanism and not fatigue_risk_present:
        errors.append("repeated satirical mechanisms require a fatigue risk")
    if not set(plan.payoff_plan.setup_unit_ids).issubset(positions):
        errors.append("payoff requires prior setup")
    payoff_position = max(
        (positions.get(x, -1) for x in plan.payoff_plan.supporting_unit_ids),
        default=len(spine),
    )
    if any(
        positions.get(x, payoff_position) >= payoff_position
        for x in plan.payoff_plan.setup_unit_ids
    ):
        errors.append("payoff setup must precede payoff")
    if plan.payoff_plan.payoff_type == PayoffType.CALLBACK_PAYOFF and not any(
        NarrativeFunction.ENABLE_SATIRE
        in (units[x].primary_function, *units[x].secondary_functions)
        for x in plan.payoff_plan.setup_unit_ids
        if x in units
    ):
        errors.append("callback payoff requires callback-capable setup")
    if plan.payoff_plan.introduces_unsupported_facts:
        errors.append("payoff cannot introduce unsupported facts")
    if plan.payoff_plan.explains_joke:
        errors.append("payoff cannot explain the joke")
    takeaway = plan.audience_takeaway
    if not set(takeaway.supporting_unit_ids).issubset(units):
        errors.append("audience takeaway must be evidence-linked")
    if (
        takeaway.commands_political_opinion
        or takeaway.guarantees_emotion
        or takeaway.erases_uncertainty
    ):
        errors.append(
            "audience takeaway cannot command opinion, guarantee emotion, or erase uncertainty"
        )
    for consequence in plan.consequence_plans:
        if (
            not consequence.supporting_material_ids
            and not consequence.supporting_core_element_ids
        ):
            errors.append("consequence must be evidence-linked")
        if not set(consequence.supporting_material_ids).issubset(material):
            errors.append("consequence references unknown material")
        if consequence.turns_human_consequence_into_spectacle:
            errors.append("human consequence cannot become spectacle")
    for guidance in plan.profile_guidance:
        if not guidance.established:
            errors.append("emerging profile guidance cannot tune architecture")
        if not guidance.source_finding_ids or not guidance.evidence_episode_ids:
            errors.append("profile guidance must retain evidence identifiers")
        if not guidance.fixed_boundary_compatible or any(
            (
                guidance.removes_indispensable_facts,
                guidance.distorts_chronology_or_causality,
                guidance.overrides_voice_safeguards,
                guidance.overrides_audience_safeguards,
            )
        ):
            errors.append(
                "profile guidance cannot override fixed architecture safeguards"
            )
    if any(
        angle.risk_of_competing_with_primary_spine
        and not angle.requires_editor_in_chief_review
        for angle in plan.secondary_angles
    ):
        errors.append("competing secondary angle requires Editor-in-Chief review")
    if any(
        (
            plan.changes_factual_status,
            plan.changes_editorial_decisions,
            plan.changes_audience_assessment,
            plan.creates_satirical_opportunities,
            plan.contains_generated_prose,
            plan.contains_generated_hook,
            plan.contains_generated_transition,
            plan.contains_generated_joke,
            plan.contains_generated_punchline,
        )
    ):
        errors.append(
            "Story Architecture cannot mutate upstream contracts or generate prose"
        )
    expected = determine_story_readiness(plan, decision_plan, audience_assessment)
    if plan.readiness != expected:
        errors.append(
            f"architecture readiness must be {expected.value}, not {plan.readiness.value}"
        )
    if errors:
        raise StoryArchitectureValidationError("; ".join(errors))
    return plan
