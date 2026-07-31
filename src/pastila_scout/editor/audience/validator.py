"""Audience Model and cross-contract assessment validation."""

from __future__ import annotations

import re

from pastila_scout.editor.audience.models import (
    AudienceAssessment,
    AudienceEmotion,
    AudienceModel,
    TrustRiskType,
)
from pastila_scout.editor.audience.readiness import determine_audience_readiness
from pastila_scout.editor.decision.models import (
    EditorialAction,
    EditorialDecisionPlan,
    FactImportance,
)
from pastila_scout.editor.decision.validator import validate_decision_plan
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA, EditorialPersona
from pastila_scout.editor.voice import DEFAULT_SATIRICAL_VOICE, SatiricalVoice
from pastila_scout.editor.voice.validator import validate_satirical_voice

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_REQUIRED_PRINCIPLES = frozenset(
    {
        "audience-is-intelligent",
        "intelligence-not-prior-knowledge",
        "proportionate-context",
        "audience-listens",
        "attention-is-finite",
        "reason-to-care",
        "respect-through-clarity",
        "do-not-lecture",
        "do-not-manipulate-emotion",
        "trust-over-impact",
        "accepts-strong-voice",
        "rejects-artificial-neutrality",
        "prefers-concrete-information",
        "purposeful-repetition",
        "humor-supports-comprehension",
        "audience-agency",
        "story-specific-calibration",
        "editor-in-chief-audience-authority",
    }
)
_REQUIRED_PROHIBITED_ASSUMPTIONS = frozenset(
    {
        "knowing all acronyms",
        "knowing all named officials",
        "knowing previous episodes",
        "knowing institutional procedures",
        "knowing the chronology of a developing story",
        "knowing why an administrative detail matters",
        "sharing the project's political conclusions in advance",
    }
)
_REQUIRED_TRUST = frozenset(
    {
        "factual fidelity",
        "clear attribution",
        "transparent uncertainty",
        "proportional framing",
        "correction readiness",
        "consistency",
        "respect for victims",
        "distinction between fact and commentary",
        "avoidance of manipulation",
    }
)


class AudienceValidationError(ValueError):
    """Raised when audience assumptions or assessments violate fixed boundaries."""


def validate_audience_model(model: AudienceModel) -> AudienceModel:
    errors: list[str] = []
    if not _SEMVER.fullmatch(model.version):
        errors.append("Audience Model version must use semantic versioning")
    ids = [item.principle_id for item in model.principles]
    if len(ids) != len(set(ids)):
        errors.append("duplicate audience principle identifiers")
    orders = [item.order for item in model.principles]
    if len(orders) != len(set(orders)):
        errors.append("audience principle order must be explicit and unique")
    missing = _REQUIRED_PRINCIPLES.difference(ids)
    if missing:
        errors.append(
            "required audience principles are missing: " + ", ".join(sorted(missing))
        )
    if "spoken" not in model.primary_medium.casefold():
        errors.append("primary medium must identify spoken content")
    if model.models_audience_as_gullible:
        errors.append("audience cannot be modeled as gullible")
    if model.models_audience_as_captive:
        errors.append("audience cannot be modeled as captive")
    if model.models_audience_as_politically_uniform:
        errors.append("audience cannot be modeled as politically uniform")
    if model.contains_demographic_stereotyping:
        errors.append("demographic stereotyping is prohibited")
    if model.claims_universal_behavior:
        errors.append("universal audience behavior claims are prohibited")
    knowledge = model.knowledge_profile
    if knowledge.intelligence_implies_complete_prior_knowledge:
        errors.append("intelligence cannot imply complete prior knowledge")
    if knowledge.specialist_knowledge_assumed_without_context:
        errors.append("specialist knowledge cannot be assumed without context")
    if knowledge.previous_episode_knowledge_mandatory:
        errors.append("previous-episode knowledge cannot be mandatory")
    if not _REQUIRED_PROHIBITED_ASSUMPTIONS.issubset(knowledge.prohibited_assumptions):
        errors.append("required prohibited audience assumptions are missing")
    if not _REQUIRED_TRUST.issubset(model.trust_profile.foundations):
        errors.append("required audience trust foundations are missing")
    if model.trust_profile.permits_manipulation:
        errors.append("Audience Model cannot permit manipulation")
    if model.trust_profile.permits_condescension:
        errors.append("Audience Model cannot permit condescension")
    if model.trust_profile.permits_victim_exploitation:
        errors.append("Audience Model cannot permit victim exploitation")
    if model.cognitive_profile.claims_scientifically_validated_constants:
        errors.append("cognitive limits are not scientifically validated constants")
    if model.contains_story_generation_procedures:
        errors.append("Audience Model cannot contain story generation procedures")
    if model.permits_automatic_prompt_mutation:
        errors.append("Audience Model cannot permit automatic prompt mutation")
    if errors:
        raise AudienceValidationError("; ".join(errors))
    return model


def validate_audience_assessment(
    assessment: AudienceAssessment,
    plan: EditorialDecisionPlan,
    model: AudienceModel,
    voice: SatiricalVoice = DEFAULT_SATIRICAL_VOICE,
    persona: EditorialPersona = DEFAULT_EDITORIAL_PERSONA,
) -> AudienceAssessment:
    validate_audience_model(model)
    validate_satirical_voice(voice)
    validate_decision_plan(plan, persona)
    errors: list[str] = []
    if not _SEMVER.fullmatch(assessment.version):
        errors.append("Audience Assessment version must use semantic versioning")
    if (
        assessment.audience_id != model.audience_id
        or assessment.audience_version != model.version
    ):
        errors.append("Audience Model identity or version mismatch")
    if assessment.decision_plan_id != plan.plan_id:
        errors.append("Decision Plan identifier mismatch")
    if assessment.source_material_fingerprint != plan.source_material_fingerprint:
        errors.append("source material fingerprint mismatch")
    if assessment.calibration.audience_id != model.audience_id:
        errors.append("calibration audience identifier mismatch")
    calibration = assessment.calibration
    for field, message in (
        (
            calibration.permits_factual_distortion,
            "calibration cannot permit factual distortion",
        ),
        (calibration.permits_manipulation, "calibration cannot permit manipulation"),
        (calibration.permits_condescension, "calibration cannot permit condescension"),
        (
            calibration.assumes_unexplained_specialist_knowledge,
            "calibration cannot assume unexplained specialist knowledge",
        ),
        (calibration.erases_uncertainty, "calibration cannot erase uncertainty"),
        (
            calibration.turns_victims_into_entertainment,
            "calibration cannot turn victims into entertainment",
        ),
        (
            calibration.overrides_fixed_boundaries,
            "calibration cannot override fixed boundaries",
        ),
    ):
        if field:
            errors.append(message)
    for guidance in calibration.established_profile_guidance:
        if not guidance.established:
            errors.append("emerging profile guidance cannot tune canonical defaults")
        if not guidance.source_finding_ids or not guidance.evidence_episode_ids:
            errors.append("profile guidance must retain finding and episode evidence")
        if not guidance.fixed_boundary_compatible:
            errors.append("profile guidance must remain fixed-boundary compatible")
        if guidance.permits_manipulation:
            errors.append("profile guidance cannot permit manipulation")
        if guidance.permits_factual_distortion:
            errors.append("profile guidance cannot permit factual distortion")
        if guidance.overrides_victim_safeguards:
            errors.append("profile guidance cannot override victim safeguards")
        if guidance.infers_demographic_traits:
            errors.append("demographic traits cannot be inferred from verdicts")
    emotional = assessment.emotional_calibration
    if emotional.manufactures_outrage:
        errors.append("manufactured outrage is prohibited")
    if emotional.manufactures_fear:
        errors.append("manufactured fear is prohibited")
    if emotional.exploits_grief or emotional.amusement_targets_victims:
        errors.append("victim exploitation is prohibited")
    if emotional.claims_guaranteed_emotion:
        errors.append("emotional assessment cannot claim guaranteed audience emotions")
    if (
        emotional.tonal_seriousness.value == "grave"
        and emotional.primary_intended_response == AudienceEmotion.AMUSED
    ):
        errors.append("grave story cannot target amusement as primary response")
    known_material = {item.material_id: item for item in plan.source_material}
    if not set(emotional.factual_basis_material_ids).issubset(known_material):
        errors.append("emotional calibration references unknown factual basis")
    for risk in assessment.attention_risks:
        if risk.claims_guaranteed_retention_outcome:
            errors.append("attention assessment cannot claim guaranteed retention")
    for risk in assessment.trust_risks:
        if risk.neutralized_for_humor_or_retention:
            errors.append("trust risks cannot be neutralized for humor or retention")
        if risk.risk_type == TrustRiskType.MANUFACTURED_OUTRAGE and not risk.blocking:
            errors.append("manufactured outrage trust risk must remain blocking")
    required_context = set(assessment.context_assessment.required_context_material_ids)
    actions = {
        material_id: decision
        for decision in plan.decisions
        for material_id in decision.material_ids
    }
    for material_id in required_context:
        decision = actions.get(material_id)
        if decision and decision.action in {
            EditorialAction.HOLD_FOR_VERIFICATION,
            EditorialAction.REMOVE,
        }:
            errors.append("held or removed material cannot become required context")
        if (
            decision
            and decision.classification == FactImportance.UNSAFE_WITHOUT_CONTEXT
            and decision.action != EditorialAction.CONTEXTUALIZE
        ):
            errors.append("unsafe material requires an explicit contextualize decision")
    if assessment.modifies_editorial_decisions:
        errors.append("Audience Assessment cannot modify Editorial Decisions")
    if (
        assessment.contains_generated_script_text
        or assessment.contains_generated_joke_text
    ):
        errors.append(
            "Audience Assessment cannot contain generated script or joke text"
        )
    expected = determine_audience_readiness(assessment, plan)
    if assessment.audience_readiness != expected:
        errors.append(
            f"audience readiness must be {expected.value}, not {assessment.audience_readiness.value}"
        )
    if assessment.artifact_kind != "audience_assessment":
        errors.append("invalid Audience Assessment artifact kind")
    if errors:
        raise AudienceValidationError("; ".join(errors))
    return assessment
