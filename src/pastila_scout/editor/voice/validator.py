"""Validation for stable Satirical Voice and evidence-linked opportunities."""

from __future__ import annotations

import re

from pastila_scout.editor.decision.models import (
    EditorialAction,
    EditorialDecisionPlan,
    FactImportance,
    FactualStatus,
    ProductionReadiness,
)
from pastila_scout.editor.decision.validator import validate_decision_plan
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA, EditorialPersona
from pastila_scout.editor.voice.models import (
    HumorDensity,
    MechanismType,
    SarcasmIntensity,
    SatiricalOpportunity,
    SatiricalRisk,
    SatiricalRiskSeverity,
    SatiricalTargetType,
    SatiricalVoice,
    SatiricalVoiceCalibration,
    SensitiveSubjectType,
    TonalSeriousness,
    VoiceProfileGuidance,
)

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_REQUIRED_PRINCIPLES = frozenset(
    {
        "sarcasm-and-irony",
        "satire-follows-facts",
        "expose-the-mechanism",
        "speak-with-audience",
        "natural-romanian-spoken-language",
        "sarcasm-has-object",
        "punch-up",
        "victims-not-joke",
        "editorially-useful-anger",
        "do-not-explain-joke",
        "density-follows-material",
        "joke-after-comprehension",
        "avoid-generic-mockery",
        "avoid-repetitive-mechanisms",
        "preserve-consequence",
        "line-earns-placement",
        "restraint-is-tool",
        "original-identity",
    }
)
_CORE_IDS = frozenset(
    {
        "what_happened",
        "involved_parties",
        "why_it_matters",
        "consequence",
        "central_tension",
        "factual_boundaries",
        "secondary_angles",
    }
)


class SatiricalVoiceValidationError(ValueError):
    """Raised for violations of voice or evidence boundaries."""


def validate_satirical_voice(voice: SatiricalVoice) -> SatiricalVoice:
    """Validate canonical identity, completeness, ordering, and fixed safeguards."""

    errors: list[str] = []
    if not _SEMVER.fullmatch(voice.version):
        errors.append("Satirical Voice version must use semantic versioning")
    principle_ids = [item.principle_id for item in voice.principles]
    if len(principle_ids) != len(set(principle_ids)):
        errors.append("duplicate Satirical Voice principle identifiers")
    missing = _REQUIRED_PRINCIPLES.difference(principle_ids)
    if missing:
        errors.append(
            "required voice principles are missing: " + ", ".join(sorted(missing))
        )
    principle_orders = [item.order for item in voice.principles]
    if len(principle_orders) != len(set(principle_orders)):
        errors.append("Satirical Voice principle order must be unique")
    mechanism_ids = [item.mechanism_id for item in voice.mechanisms]
    if len(mechanism_ids) != len(set(mechanism_ids)):
        errors.append("duplicate satirical mechanism identifiers")
    missing_mechanisms = set(MechanismType).difference(mechanism_ids)
    if missing_mechanisms:
        errors.append("required satirical mechanisms are missing")
    mechanism_orders = [item.order for item in voice.mechanisms]
    if len(mechanism_orders) != len(set(mechanism_orders)):
        errors.append("satirical mechanism order must be unique")
    if set(voice.calibration.valid_targets) != set(SatiricalTargetType):
        errors.append("canonical valid target types are incomplete")
    if set(voice.calibration.protected_subjects) != set(SensitiveSubjectType):
        errors.append("canonical protected subject types are incomplete")
    if voice.emerging_trends_may_mutate_voice:
        errors.append("emerging Editorial Profile trends cannot mutate canonical Voice")
    if voice.profile_may_override_factuality:
        errors.append("profile guidance cannot override factuality")
    if voice.profile_may_target_protected_subjects:
        errors.append("profile guidance cannot target protected subjects")
    if voice.contains_personality_imitation or voice.contains_fictional_biography:
        errors.append("personality imitation and fictional biography are prohibited")
    if voice.contains_generation_procedures:
        errors.append("Satirical Voice must not contain generation procedures")
    if voice.permits_automatic_prompt_mutation:
        errors.append("Satirical Voice must not permit automatic prompt mutation")
    if errors:
        raise SatiricalVoiceValidationError("; ".join(errors))
    return voice


def apply_profile_guidance(
    voice: SatiricalVoice, guidance: VoiceProfileGuidance
) -> SatiricalVoiceCalibration:
    """Tune dimensions only from established, boundary-safe Profile guidance."""

    validate_satirical_voice(voice)
    if not guidance.established:
        return voice.calibration
    if guidance.permits_factual_distortion:
        raise SatiricalVoiceValidationError(
            "profile guidance cannot permit factual distortion"
        )
    if guidance.permits_protected_subject_targeting:
        raise SatiricalVoiceValidationError(
            "profile guidance cannot permit victim targeting"
        )
    if guidance.overrides_fixed_boundaries:
        raise SatiricalVoiceValidationError(
            "profile guidance cannot override fixed boundaries"
        )
    return voice.calibration.model_copy(update={"dimensions": guidance.dimensions})


def validate_satirical_opportunity(
    opportunity: SatiricalOpportunity,
    plan: EditorialDecisionPlan,
    voice: SatiricalVoice,
    risks: tuple[SatiricalRisk, ...] = (),
    persona: EditorialPersona = DEFAULT_EDITORIAL_PERSONA,
) -> SatiricalOpportunity:
    """Validate that satire is supported by a safe Editorial Decision Plan."""

    validate_satirical_voice(voice)
    validate_decision_plan(plan, persona)
    errors: list[str] = []
    material_by_id = {item.material_id: item for item in plan.source_material}
    if not set(opportunity.supported_material_ids).issubset(material_by_id):
        errors.append("Satirical Opportunity references unknown material")
    if not set(opportunity.editorial_core_element_ids).issubset(_CORE_IDS):
        errors.append(
            "Satirical Opportunity references unknown Editorial Core elements"
        )
    decision_by_id = {item.decision_id: item for item in plan.decisions}
    if not set(opportunity.decision_ids).issubset(decision_by_id):
        errors.append("Satirical Opportunity references unknown decisions")
    risk_ids = {item.risk_id for item in risks}
    if not set(opportunity.risk_ids).issubset(risk_ids):
        errors.append("Satirical Opportunity references unknown satirical risks")
    if plan.production_readiness == ProductionReadiness.BLOCKED:
        errors.append("blocked Decision Plan cannot support a satire-ready opportunity")
    if (
        plan.production_readiness == ProductionReadiness.REQUIRES_EDITOR_REVIEW
        and not opportunity.requires_editor_in_chief_review
    ):
        errors.append("review-required plan requires review-required opportunity")
    materials = [
        material_by_id[item]
        for item in opportunity.supported_material_ids
        if item in material_by_id
    ]
    decisions = [
        decision_by_id[item]
        for item in opportunity.decision_ids
        if item in decision_by_id
    ]
    removed_or_held = {
        material_id
        for decision in decisions
        if decision.action
        in {EditorialAction.REMOVE, EditorialAction.HOLD_FOR_VERIFICATION}
        for material_id in decision.material_ids
    }
    if removed_or_held.intersection(opportunity.supported_material_ids):
        errors.append("removed or held material cannot support a Satirical Opportunity")
    unsafe = {
        material_id
        for decision in decisions
        if decision.classification == FactImportance.UNSAFE_WITHOUT_CONTEXT
        and decision.action != EditorialAction.CONTEXTUALIZE
        for material_id in decision.material_ids
    }
    if unsafe.intersection(opportunity.supported_material_ids):
        errors.append("unsafe-without-context material requires contextualization")
    if opportunity.confidence.value == "high" and any(
        material.factual_status == FactualStatus.UNKNOWN_UNRESOLVED
        for material in materials
    ):
        errors.append("unresolved central claim cannot support high confidence satire")
    if (
        any(
            material.factual_status == FactualStatus.ALLEGATION
            and not material.attribution
            for material in materials
        )
        or not opportunity.preserves_attribution
    ):
        errors.append("allegations must preserve attribution")
    if (
        any(
            material.factual_status == FactualStatus.DISPUTED_CLAIM
            for material in materials
        )
        and not opportunity.preserves_dispute_status
    ):
        errors.append("disputed claims must preserve dispute status")
    if opportunity.targets_sensitive_subject:
        errors.append("victims and vulnerable people cannot be satirical targets")
    if (
        opportunity.sensitivity == SensitiveSubjectType.PROTECTED_CHARACTERISTICS
        and opportunity.targets_sensitive_subject
    ):
        errors.append("protected characteristics cannot be gratuitous targets")
    if opportunity.permits_factual_distortion:
        errors.append("factual distortion for humor is prohibited")
    if opportunity.contains_unsupported_accusation:
        errors.append("unsupported accusation is prohibited")
    if opportunity.invents_motive:
        errors.append("motive invention is prohibited")
    if opportunity.detached_from_editorial_core:
        errors.append("satire detached from Editorial Core is prohibited")
    if opportunity.generic_insult_is_sole_mechanism:
        errors.append("generic insult cannot be the sole satirical mechanism")
    dimensions = opportunity.recommended_dimensions
    if (
        opportunity.tonal_limit in {TonalSeriousness.SERIOUS, TonalSeriousness.GRAVE}
        and dimensions.humor_density == HumorDensity.DENSE
        and not opportunity.requires_editor_in_chief_review
    ):
        errors.append("dense humor on serious material requires Editor-in-Chief review")
    if opportunity.tonal_limit == TonalSeriousness.GRAVE and (
        dimensions.sarcasm_intensity != SarcasmIntensity.RESTRAINED
        or dimensions.humor_density != HumorDensity.SPARSE
    ):
        errors.append("grave material defaults to restrained sparse satire")
    if opportunity.contains_generated_joke_text:
        errors.append("Satirical Opportunity cannot contain generated joke text")
    evidence_contents = {item.content for item in materials}
    if not set(opportunity.factual_basis).issubset(evidence_contents):
        errors.append(
            "opportunity factual basis must preserve supplied evidence verbatim"
        )
    if any(
        risk.severity == SatiricalRiskSeverity.CRITICAL or risk.blocking
        for risk in risks
    ):
        errors.append("blocking satirical risk prevents a satire-ready opportunity")
    if errors:
        raise SatiricalVoiceValidationError("; ".join(errors))
    return opportunity
