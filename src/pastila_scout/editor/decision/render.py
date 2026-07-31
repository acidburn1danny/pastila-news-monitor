"""Deterministic, non-generative rendering of Editorial Decision Plans."""

from __future__ import annotations

from pastila_scout.editor.decision.models import (
    DecisionStage,
    EditorialDecisionPlan,
)
from pastila_scout.editor.decision.validator import validate_decision_plan
from pastila_scout.editor.persona.models import EditorialPersona

_STAGE_ORDER = {stage: index for index, stage in enumerate(DecisionStage, start=1)}


def _values(values: tuple[str, ...]) -> str:
    return ", ".join(sorted(values)) if values else "None"


def render_decision_plan(plan: EditorialDecisionPlan, persona: EditorialPersona) -> str:
    """Render evidence and decisions verbatim in stable editorial order."""

    validate_decision_plan(plan, persona)
    core = plan.editorial_core
    lines = [
        "[Editorial Decision Plan]",
        "",
        "Plan Identity",
        f"Plan ID: {plan.plan_id}",
        f"Version: {plan.version}",
        f"Persona: {plan.persona_id} {plan.persona_version}",
        f"Philosophy: {plan.philosophy_id} {plan.philosophy_version}",
        f"Source fingerprint: {plan.source_material_fingerprint}",
        "",
        "Production Readiness",
        plan.production_readiness.value,
        "",
        "Editorial Core",
        f"What happened: {core.what_happened.statement} [{_values(core.what_happened.material_ids)}]",
        f"Involved: {core.involved_parties.statement} [{_values(core.involved_parties.material_ids)}]",
        f"Why it matters: {core.why_it_matters.statement} [{_values(core.why_it_matters.material_ids)}]",
        f"Consequence: {core.consequence.statement} [{_values(core.consequence.material_ids)}]",
        f"Central tension: {core.central_tension.statement} [{_values(core.central_tension.material_ids)}]",
        "Factual boundaries:",
        *[
            f"- {item.statement} [{_values(item.material_ids)}]"
            for item in sorted(core.factual_boundaries, key=lambda item: item.statement)
        ],
        "Secondary angles:",
        *[
            f"- {item.statement} [{_values(item.material_ids)}]"
            for item in sorted(core.secondary_angles, key=lambda item: item.statement)
        ],
        "",
        "Material Assessment",
    ]
    for material in sorted(plan.source_material, key=lambda item: item.material_id):
        lines.extend(
            (
                (
                    f"- {material.material_id} | {material.material_type.value} | "
                    f"{material.factual_status.value}"
                ),
                f"  Source: {material.source_reference}",
                f"  Attribution: {material.attribution or 'None'}",
                f"  Chronology: {material.chronology_position if material.chronology_position is not None else 'Unknown'}",
                f"  Content: {material.content}",
            )
        )
    lines.extend(("", "Editorial Decisions"))
    decisions = sorted(
        plan.decisions,
        key=lambda item: (_STAGE_ORDER[item.stage], item.rank, item.decision_id),
    )
    for decision in decisions:
        lines.extend(
            (
                f"- {decision.decision_id} | stage={decision.stage.value} | rank={decision.rank}",
                f"  Affected material: {_values(decision.material_ids)}",
                f"  Classification: {decision.classification.value}",
                f"  Action: {decision.action.value}",
                f"  Rationale: {decision.rationale}",
                f"  Evidence: {_values(decision.evidence)}",
                f"  Principles: {_values(decision.principle_ids)}",
                f"  Tensions: {_values(decision.tension_ids)}",
                f"  Confidence: {decision.confidence.value}",
                f"  Consequence if ignored: {decision.consequence_if_ignored}",
                f"  Unresolved dependencies: {_values(decision.unresolved_dependencies)}",
                f"  Editor-in-Chief review: {'yes' if decision.requires_editor_in_chief_review else 'no'}",
            )
        )
    lines.extend(("", "Editorial Risks"))
    for risk in sorted(plan.risks, key=lambda item: item.risk_id):
        lines.extend(
            (
                f"- {risk.risk_id} | {risk.risk_type.value} | {risk.severity.value}",
                f"  Affected material: {_values(risk.affected_material_ids)}",
                f"  Explanation: {risk.explanation}",
                f"  Mitigation: {risk.mitigation}",
                f"  Blocking: {'yes' if risk.blocking else 'no'}",
            )
        )
    lines.extend(
        (
            "",
            "Unresolved Questions",
            *[f"- {item}" for item in sorted(plan.unresolved_questions)],
            "",
            "Blocking Issues",
            *[f"- {item}" for item in sorted(plan.blocking_issues)],
            "",
            "Advisory Issues",
            *[f"- {item}" for item in sorted(plan.advisory_issues)],
            "",
            "Editor-in-Chief Review",
            "Required" if plan.requires_editor_in_chief_review else "Not required",
        )
    )
    return "\n".join(lines) + "\n"
