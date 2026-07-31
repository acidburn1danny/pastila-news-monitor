"""Deterministic reference-only Story Architecture renderers."""

from pastila_scout.editor.story.models import STAGE_RANK
from pastila_scout.editor.story.validator import (
    validate_story_architecture,
    validate_story_plan,
)


def _bullets(values):
    return [f"- {value}" for value in sorted(values)]


def render_story_architecture(architecture) -> str:
    validate_story_architecture(architecture)
    lines = [
        "[Story Architecture]",
        "",
        "Architecture Identity",
        f"{architecture.architecture_id} {architecture.version}",
        "",
        "Purpose",
        architecture.purpose,
        "",
        "Canonical Principles",
        *[
            f"{x.order}. {x.title}"
            for x in sorted(architecture.principles, key=lambda x: x.order)
        ],
        "",
        "Narrative Stages",
        *[f"{index}. {x.value}" for index, x in enumerate(architecture.stage_order, 1)],
        "",
        "Story Unit Types",
        *_bullets(x.value for x in architecture.supported_unit_types),
        "",
        "Narrative Functions",
        *_bullets(x.value for x in architecture.supported_functions),
        "",
        "Canonical Story Patterns",
        *[
            f"{x.order}. {x.title}"
            for x in sorted(architecture.patterns, key=lambda x: x.order)
        ],
        "",
        "Opening Strategies",
        *_bullets(x.value for x in architecture.opening_strategies),
        "",
        "Context Placement Policy",
        "Context follows a demonstrated comprehension dependency.",
        "",
        "Consequence Policy",
        "Consequences remain evidence-linked and proportionate.",
        "",
        "Satire Placement Policy",
        "Satire follows validated setup and opportunity.",
        "",
        "Transition Policy",
        *_bullets(x.value for x in architecture.transition_relationships),
        "",
        "Payoff Policy",
        "Every payoff resolves prior setup without unsupported facts.",
        "",
        "Audience Takeaway Policy",
        "The takeaway is evidence-linked and never commands opinion.",
        "",
        "Profile Guidance Policy",
        "Only established boundary-compatible guidance may tune architecture.",
        "",
        "Editor-in-Chief Authority",
        "The Editor-in-Chief controls the final narrative choice.",
        "",
        "Fixed Boundaries",
        *_bullets(architecture.fixed_boundaries),
    ]
    return "\n".join(lines) + "\n"


def render_pattern_selection(selection) -> str:
    return (
        "[Story Pattern Selection]\n"
        f"Selection: {selection.selection_id}\n"
        f"Pattern: {selection.selected_pattern_id}\n"
        f"Decision Plan: {selection.decision_plan_id}\n"
        f"Audience Assessment: {selection.audience_assessment_id}\n"
        f"Confidence: {selection.confidence.value}\n"
    )


def render_story_plan(
    plan,
    architecture,
    decision_plan,
    audience_assessment,
    audience_model,
    voice,
    opportunities=(),
):
    validate_story_plan(
        plan,
        architecture,
        decision_plan,
        audience_assessment,
        audience_model,
        voice,
        opportunities,
    )
    units = sorted(
        plan.story_units, key=lambda x: (STAGE_RANK[x.stage], x.rank, x.unit_id)
    )
    lines = [
        "[Story Architecture Plan]",
        "",
        "Architecture Plan Identity",
        f"{plan.architecture_id} {plan.version}",
        "",
        "Architecture Readiness",
        plan.readiness.value,
        "",
        "Upstream Contracts",
        f"Decision Plan: {plan.decision_plan_id}",
        f"Audience Assessment: {plan.audience_assessment_id}",
        "",
        "Selected Story Pattern",
        plan.selected_pattern.selected_pattern_id,
        "",
        "Primary Narrative Spine",
        *_bullets(plan.primary_narrative_spine.ordered_unit_ids),
        "",
        "Secondary Angles",
        *_bullets(x.angle_id for x in plan.secondary_angles),
        "",
        "Opening Plan",
        f"Strategy: {plan.opening_plan.strategy.value}",
        f"Units: {', '.join(plan.opening_plan.supported_unit_ids)}",
        "",
        "Ordered Story Units",
    ]
    for unit in units:
        lines.extend(
            (
                f"- {unit.unit_id} | {unit.stage.value}:{unit.rank} | {unit.unit_type.value}",
                f"  Primary function: {unit.primary_function.value}",
                f"  Secondary functions: {', '.join(x.value for x in unit.secondary_functions) or 'None'}",
                f"  Evidence: {', '.join(unit.source_material_ids)}",
                f"  Decisions: {', '.join(unit.editorial_decision_ids)}",
                f"  Core: {', '.join(unit.editorial_core_element_ids)}",
                f"  Opportunities: {', '.join(unit.satirical_opportunity_ids) or 'None'}",
                f"  Importance: {unit.importance.value}",
                f"  Prerequisites: {', '.join(unit.prerequisite_unit_ids) or 'None'}",
                f"  Context dependencies: {', '.join(unit.required_context_unit_ids) or 'None'}",
                f"  Sensitivity: {unit.sensitivity.value if unit.sensitivity else 'None'}",
                f"  Compress/combine/remove: {unit.can_be_compressed}/{unit.can_be_combined}/{unit.can_be_removed}",
                f"  Attribution/restraint/review: {unit.requires_attribution}/{unit.requires_tonal_restraint}/{unit.requires_editor_in_chief_review}",
            )
        )
    sections = (
        ("Context Placements", [x.placement_id for x in plan.context_placements]),
        ("Consequence Plans", [x.consequence_id for x in plan.consequence_plans]),
        ("Satire Placements", [x.placement_id for x in plan.satire_placements]),
        ("Story Transitions", [x.transition_id for x in plan.transitions]),
        ("Payoff Plan", [plan.payoff_plan.payoff_id]),
        ("Audience Takeaway", [plan.audience_takeaway.takeaway_id]),
        ("Architecture Risks", [x.risk_id for x in plan.architecture_risks]),
        ("Unresolved Dependencies", list(plan.unresolved_dependencies)),
        ("Blocking Issues", list(plan.blocking_issues)),
        ("Advisory Issues", list(plan.advisory_issues)),
    )
    for title, values in sections:
        lines.extend(("", title, *_bullets(values)))
    lines.extend(
        (
            "",
            "Editor-in-Chief Review",
            "Required" if plan.requires_editor_in_chief_review else "Not required",
        )
    )
    return "\n".join(lines) + "\n"
