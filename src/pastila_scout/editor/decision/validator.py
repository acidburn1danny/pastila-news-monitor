"""Cross-contract and factual-safety validation for decision plans."""

from __future__ import annotations

import re

from pastila_scout.editor.decision.fingerprint import source_material_fingerprint
from pastila_scout.editor.decision.models import (
    EditorialAction,
    EditorialDecisionPlan,
    FactImportance,
    FactualStatus,
    MaterialType,
    ProductionReadiness,
    RiskSeverity,
)
from pastila_scout.editor.persona.models import EditorialPersona
from pastila_scout.editor.persona.validator import validate_persona

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class DecisionValidationError(ValueError):
    """Raised when a decision plan violates evidence or Persona contracts."""


def determine_readiness(plan: EditorialDecisionPlan) -> ProductionReadiness:
    """Derive readiness from blockers, risks, advisories, and authority needs."""

    missing_indispensable = any(
        decision.classification == FactImportance.INDISPENSABLE
        and decision.unresolved_dependencies
        for decision in plan.decisions
    )
    if (
        plan.blocking_issues
        or missing_indispensable
        or any(
            risk.blocking or risk.severity == RiskSeverity.CRITICAL
            for risk in plan.risks
        )
    ):
        return ProductionReadiness.BLOCKED
    if (
        plan.requires_editor_in_chief_review
        or any(decision.requires_editor_in_chief_review for decision in plan.decisions)
        or any(risk.requires_editor_in_chief_review for risk in plan.risks)
    ):
        return ProductionReadiness.REQUIRES_EDITOR_REVIEW
    if plan.advisory_issues or plan.risks:
        return ProductionReadiness.READY_WITH_ADVISORIES
    return ProductionReadiness.READY


def _core_references(plan: EditorialDecisionPlan) -> set[str]:
    core = plan.editorial_core
    elements = (
        core.what_happened,
        core.involved_parties,
        core.why_it_matters,
        core.consequence,
        core.central_tension,
        *core.factual_boundaries,
        *core.secondary_angles,
    )
    return {material_id for element in elements for material_id in element.material_ids}


def validate_decision_plan(
    plan: EditorialDecisionPlan, persona: EditorialPersona
) -> EditorialDecisionPlan:
    """Validate a plan against supplied material and canonical Persona semantics."""

    validate_persona(persona)
    errors: list[str] = []
    if not _SEMVER.fullmatch(plan.version):
        errors.append("decision plan version must use semantic versioning")
    material_ids = [item.material_id for item in plan.source_material]
    known_material = set(material_ids)
    if len(material_ids) != len(known_material):
        errors.append("duplicate material identifiers")
    if (
        source_material_fingerprint(plan.source_material)
        != plan.source_material_fingerprint
    ):
        errors.append("source material fingerprint mismatch")
    if not _core_references(plan).issubset(known_material):
        errors.append("editorial core references unknown material")

    philosophy = persona.philosophy
    if philosophy is None:  # Defensive; validate_persona already rejects this.
        errors.append("Persona has no Editorial Philosophy")
        valid_principles: set[str] = set()
        valid_tensions: set[str] = set()
    else:
        valid_principles = {item.principle_id for item in philosophy.principles}
        valid_tensions = {item.tension_id for item in philosophy.tensions}
        if plan.philosophy_id != philosophy.philosophy_id:
            errors.append("philosophy identifier mismatch")
        if plan.philosophy_version != philosophy.version:
            errors.append("philosophy version mismatch")
    if plan.persona_id != persona.persona_id:
        errors.append("Persona identifier mismatch")
    if plan.persona_version != persona.version:
        errors.append("Persona version mismatch")

    by_id = {item.material_id: item for item in plan.source_material}
    decision_ids = [item.decision_id for item in plan.decisions]
    if len(decision_ids) != len(set(decision_ids)):
        errors.append("duplicate decision identifiers")
    for decision in plan.decisions:
        if not set(decision.material_ids).issubset(known_material):
            errors.append(
                f"decision {decision.decision_id} references unknown material"
            )
            continue
        if not set(decision.principle_ids).issubset(valid_principles):
            errors.append(
                f"decision {decision.decision_id} references unknown principle"
            )
        if not set(decision.tension_ids).issubset(valid_tensions):
            errors.append(f"decision {decision.decision_id} references unknown tension")
        materials = [by_id[item] for item in decision.material_ids]
        if (
            decision.action == EditorialAction.REMOVE
            and decision.classification == FactImportance.INDISPENSABLE
        ):
            errors.append("indispensable facts cannot be removed")
        if (
            decision.action == EditorialAction.COMPRESS
            and not decision.preserves_attribution
        ):
            errors.append("compression must preserve attribution")
        if (
            decision.action == EditorialAction.COMBINE
            and decision.merges_contradictory_claims
        ):
            errors.append(
                "contradictory claims cannot be merged into one apparent fact"
            )
        if (
            any(item.material_type == MaterialType.QUOTE for item in materials)
            and decision.mutates_quote
        ):
            errors.append("quote mutation is prohibited")
        if decision.infers_unsupported_motive:
            errors.append("unsupported motive inference is prohibited")
        if decision.infers_unsupported_causality:
            errors.append("unsupported causal inference is prohibited")
        if decision.silently_removes_uncertainty:
            errors.append("material uncertainty cannot be silently removed")
        if decision.factual_distortion_purpose is not None:
            errors.append(
                "factual distortion is prohibited for pacing, satire, retention, or any purpose"
            )
        for material in materials:
            if (
                material.material_type == MaterialType.ALLEGATION
                and material.factual_status == FactualStatus.VERIFIED_FACT
                and not material.transformation_evidence
            ):
                errors.append("allegation cannot become verified fact without evidence")
            if (
                material.factual_status
                in {
                    FactualStatus.ATTRIBUTED_CLAIM,
                    FactualStatus.ALLEGATION,
                    FactualStatus.DISPUTED_CLAIM,
                }
                and not material.attribution
            ):
                errors.append("claims and allegations require attribution")

    risk_ids = [item.risk_id for item in plan.risks]
    if len(risk_ids) != len(set(risk_ids)):
        errors.append("duplicate risk identifiers")
    for risk in plan.risks:
        if not set(risk.affected_material_ids).issubset(known_material):
            errors.append(f"risk {risk.risk_id} references unknown material")
    expected = determine_readiness(plan)
    if plan.production_readiness != expected:
        errors.append(
            f"production readiness must be {expected.value}, not "
            f"{plan.production_readiness.value}"
        )
    if plan.artifact_kind != "editorial_decision_plan" or plan.contains_generated_prose:
        errors.append(
            "Decision Plan must not be treated as a script or generated prose"
        )
    if plan.mutates_editorial_memory:
        errors.append("Decision Plan must not mutate Editorial Memory")
    if errors:
        raise DecisionValidationError("; ".join(errors))
    return plan
