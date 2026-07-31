"""Focused Module 2.5 Audience Model and cross-contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.audience import (
    DEFAULT_AUDIENCE_MODEL,
    AttentionRiskType,
    AudienceAssessment,
    AudienceAttentionRisk,
    AudienceCalibration,
    AudienceEmotion,
    AudienceEmotionalCalibration,
    AudienceFatigueAssessment,
    AudienceProfileGuidance,
    AudienceReadiness,
    AudienceRiskSeverity,
    AudienceTrustRisk,
    AudienceValidationError,
    ComprehensionAssessment,
    ContextBudget,
    ContextBudgetLevel,
    FatigueType,
    PriorKnowledgeLevel,
    TrustRiskType,
    assessment_fingerprint,
    audience_model_fingerprint,
    calibration_fingerprint,
    render_audience_assessment,
    render_audience_model,
    validate_audience_assessment,
    validate_audience_model,
)
from pastila_scout.editor.audience.models import AudienceCognitiveProfile
from pastila_scout.editor.decision import (
    CoreElement,
    DecisionConfidence,
    DecisionStage,
    EditorialAction,
    EditorialCore,
    EditorialDecision,
    EditorialDecisionPlan,
    EditorialMaterial,
    EditorialRisk,
    FactImportance,
    FactualStatus,
    MaterialType,
    ProductionReadiness,
    RiskSeverity,
    RiskType,
    source_material_fingerprint,
)
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA
from pastila_scout.editor.voice import (
    DEFAULT_SATIRICAL_VOICE,
    HumorDensity,
    TonalSeriousness,
)

REQUIRED_PRINCIPLES = {
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


def _material(**changes):
    values = {
        "material_id": "m1",
        "source_reference": "source-a",
        "material_type": MaterialType.FACT,
        "content": "Instituția a anunțat măsura miercuri.",
        "factual_status": FactualStatus.VERIFIED_FACT,
    }
    values.update(changes)
    return EditorialMaterial(**values)


def _decision(**changes):
    values = {
        "decision_id": "d1",
        "stage": DecisionStage.EDITORIAL_CORE,
        "rank": 1,
        "material_ids": ("m1",),
        "classification": FactImportance.INDISPENSABLE,
        "action": EditorialAction.PRESERVE,
        "rationale": "Preserve the factual core.",
        "evidence": ("m1",),
        "principle_ids": ("truth-before-performance",),
        "confidence": DecisionConfidence.HIGH,
        "consequence_if_ignored": "The audience would lose the core fact.",
    }
    values.update(changes)
    return EditorialDecision(**values)


def _plan(material=None, decision=None, **changes):
    material = material or _material()
    decision = decision or _decision()
    element = CoreElement(statement="Măsura a fost anunțată.", material_ids=("m1",))
    core = EditorialCore(
        what_happened=element,
        involved_parties=element,
        why_it_matters=element,
        consequence=element,
        central_tension=element,
        factual_boundaries=(element,),
    )
    philosophy = DEFAULT_EDITORIAL_PERSONA.philosophy
    values = {
        "plan_id": "plan-audience",
        "version": "1.0.0",
        "persona_id": DEFAULT_EDITORIAL_PERSONA.persona_id,
        "persona_version": DEFAULT_EDITORIAL_PERSONA.version,
        "philosophy_id": philosophy.philosophy_id,
        "philosophy_version": philosophy.version,
        "source_material_fingerprint": source_material_fingerprint((material,)),
        "source_material": (material,),
        "editorial_core": core,
        "decisions": (decision,),
        "requires_editor_in_chief_review": False,
        "production_readiness": ProductionReadiness.READY,
        "summary": "Validated source assessment.",
    }
    values.update(changes)
    return EditorialDecisionPlan(**values)


def _context(**changes):
    values = {
        "budget_level": ContextBudgetLevel.MODERATE,
        "justification": "Enough context to understand the current event.",
        "required_background": ("Institution role.",),
        "optional_background": (),
        "prohibited_detours": ("Unrelated institutional history.",),
        "compression_candidates": (),
        "indispensable_explanations": ("Why the measure matters.",),
        "review_conditions": (),
        "required_context_material_ids": ("m1",),
    }
    values.update(changes)
    return ContextBudget(**values)


def _emotion(**changes):
    values = {
        "primary_intended_response": AudienceEmotion.INFORMED,
        "secondary_intended_responses": (AudienceEmotion.CURIOUS,),
        "responses_to_avoid": (),
        "factual_basis_material_ids": ("m1",),
        "emotional_ceiling": AudienceEmotion.CONCERNED,
        "tonal_seriousness": TonalSeriousness.MIXED,
        "tonal_constraints": ("Keep emotion evidence-grounded.",),
        "sensitivity_conditions": (),
        "editor_review_conditions": (),
    }
    values.update(changes)
    return AudienceEmotionalCalibration(**values)


def _guidance(**changes):
    values = {
        "guidance_id": "ag-1",
        "source_finding_ids": ("finding-1",),
        "established": True,
        "affected_dimensions": ("context_budget",),
        "proposed_tuning": ("shorter introduction",),
        "confidence": "high",
        "evidence_episode_ids": ("episode-1", "episode-2", "episode-3"),
        "fixed_boundary_compatible": True,
        "active": True,
    }
    values.update(changes)
    return AudienceProfileGuidance(**values)


def _calibration(**changes):
    values = {
        "audience_id": DEFAULT_AUDIENCE_MODEL.audience_id,
        "audience_version": DEFAULT_AUDIENCE_MODEL.version,
        "prior_knowledge": PriorKnowledgeLevel.GENERAL,
        "context_budget": _context(),
        "cognitive_profile": DEFAULT_AUDIENCE_MODEL.cognitive_profile,
        "intended_emotional_response": _emotion(),
        "voice_dimensions": DEFAULT_SATIRICAL_VOICE.calibration.dimensions,
        "attention_priorities": ("early relevance",),
        "trust_safeguards": ("visible attribution",),
        "fatigue_constraints": ("avoid repeated context",),
    }
    values.update(changes)
    return AudienceCalibration(**values)


def _assessment(**changes):
    plan = changes.pop("plan", _plan())
    values = {
        "assessment_id": "aa-1",
        "version": "1.0.0",
        "audience_id": DEFAULT_AUDIENCE_MODEL.audience_id,
        "audience_version": DEFAULT_AUDIENCE_MODEL.version,
        "decision_plan_id": plan.plan_id,
        "source_material_fingerprint": plan.source_material_fingerprint,
        "calibration": _calibration(),
        "comprehension_assessment": ComprehensionAssessment(
            summary="The core is immediately understandable."
        ),
        "context_assessment": _context(),
        "emotional_calibration": _emotion(),
        "requires_editor_in_chief_review": False,
        "audience_readiness": AudienceReadiness.READY,
        "summary": "Editorial audience assessment, not a performance forecast.",
    }
    values.update(changes)
    return AudienceAssessment(**values)


def _attention(**changes):
    values = {
        "risk_id": "ar-1",
        "risk_type": AttentionRiskType.EXCESSIVE_CONTEXT,
        "severity": AudienceRiskSeverity.LOW,
        "affected_ids": ("m1",),
        "explanation": "Optional context may be long.",
        "likely_audience_effect": "Possible attention loss.",
        "mitigation": "Compress optional context.",
        "blocking": False,
        "requires_editor_in_chief_review": False,
    }
    values.update(changes)
    return AudienceAttentionRisk(**values)


def _trust(**changes):
    values = {
        "risk_id": "tr-1",
        "risk_type": TrustRiskType.FACTUAL_OVERSTATEMENT,
        "severity": AudienceRiskSeverity.LOW,
        "affected_evidence_ids": ("m1",),
        "explanation": "Wording may overstate the source.",
        "likely_trust_consequence": "Reduced trust.",
        "mitigation": "Use proportional wording.",
        "blocking": False,
        "requires_editor_in_chief_review": False,
    }
    values.update(changes)
    return AudienceTrustRisk(**values)


def test_canonical_audience_model_validates_and_is_immutable():
    assert validate_audience_model(DEFAULT_AUDIENCE_MODEL) is DEFAULT_AUDIENCE_MODEL
    with pytest.raises(ValidationError):
        DEFAULT_AUDIENCE_MODEL.title = "Changed"  # type: ignore[misc]


def test_canonical_principles_are_complete_unique_and_ordered():
    principles = DEFAULT_AUDIENCE_MODEL.principles
    assert {item.principle_id for item in principles} == REQUIRED_PRINCIPLES
    assert len({item.principle_id for item in principles}) == len(principles)
    assert len({item.order for item in principles}) == len(principles)


def test_invalid_semantic_version_is_rejected():
    with pytest.raises(AudienceValidationError, match="semantic versioning"):
        validate_audience_model(
            DEFAULT_AUDIENCE_MODEL.model_copy(update={"version": "one"})
        )


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (AudienceCognitiveProfile, "preferred_information_density", "packed"),
        (AudienceCognitiveProfile, "maximum_recommended_context_load", "huge"),
        (ContextBudget, "budget_level", "infinite"),
        (AudienceEmotionalCalibration, "primary_intended_response", "obedient"),
        (AudienceAttentionRisk, "severity", "certain"),
        (AudienceTrustRisk, "risk_type", "invented"),
        (AudienceAssessment, "audience_readiness", "viral"),
    ],
)
def test_invalid_constrained_values_are_rejected(model, field, value):
    source = {
        AudienceCognitiveProfile: DEFAULT_AUDIENCE_MODEL.cognitive_profile,
        ContextBudget: _context(),
        AudienceEmotionalCalibration: _emotion(),
        AudienceAttentionRisk: _attention(),
        AudienceTrustRisk: _trust(),
        AudienceAssessment: _assessment(),
    }[model]
    data = source.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"primary_medium": "printed newsletter"}, "spoken content"),
        ({"models_audience_as_gullible": True}, "gullible"),
        ({"models_audience_as_captive": True}, "captive"),
        ({"models_audience_as_politically_uniform": True}, "politically uniform"),
        ({"contains_demographic_stereotyping": True}, "stereotyping"),
        ({"claims_universal_behavior": True}, "universal"),
    ],
)
def test_invalid_canonical_audience_assumptions_are_rejected(changes, message):
    with pytest.raises(AudienceValidationError, match=message):
        validate_audience_model(DEFAULT_AUDIENCE_MODEL.model_copy(update=changes))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("intelligence_implies_complete_prior_knowledge", "complete prior knowledge"),
        ("specialist_knowledge_assumed_without_context", "specialist knowledge"),
        ("previous_episode_knowledge_mandatory", "previous-episode"),
    ],
)
def test_invalid_knowledge_assumptions_are_rejected(field, message):
    knowledge = DEFAULT_AUDIENCE_MODEL.knowledge_profile.model_copy(
        update={field: True}
    )
    model = DEFAULT_AUDIENCE_MODEL.model_copy(update={"knowledge_profile": knowledge})
    with pytest.raises(AudienceValidationError, match=message):
        validate_audience_model(model)


def test_required_prohibited_assumptions_and_trust_foundations_exist():
    assert len(DEFAULT_AUDIENCE_MODEL.knowledge_profile.prohibited_assumptions) >= 7
    assert len(DEFAULT_AUDIENCE_MODEL.trust_profile.foundations) >= 9


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("permits_manipulation", "manipulation"),
        ("permits_condescension", "condescension"),
        ("permits_victim_exploitation", "victim exploitation"),
    ],
)
def test_trust_profile_cannot_relax_fixed_safeguards(field, message):
    trust = DEFAULT_AUDIENCE_MODEL.trust_profile.model_copy(update={field: True})
    model = DEFAULT_AUDIENCE_MODEL.model_copy(update={"trust_profile": trust})
    with pytest.raises(AudienceValidationError, match=message):
        validate_audience_model(model)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"manufactures_outrage": True}, "manufactured outrage"),
        ({"manufactures_fear": True}, "manufactured fear"),
        ({"exploits_grief": True}, "victim exploitation"),
        ({"amusement_targets_victims": True}, "victim exploitation"),
        ({"claims_guaranteed_emotion": True}, "guaranteed audience emotions"),
    ],
)
def test_unsafe_emotional_calibration_is_rejected(changes, message):
    emotional = _emotion(**changes)
    with pytest.raises(AudienceValidationError, match=message):
        validate_audience_assessment(
            _assessment(emotional_calibration=emotional),
            _plan(),
            DEFAULT_AUDIENCE_MODEL,
        )


def test_grave_story_cannot_target_amusement():
    emotional = _emotion(
        tonal_seriousness=TonalSeriousness.GRAVE,
        primary_intended_response=AudienceEmotion.AMUSED,
    )
    with pytest.raises(AudienceValidationError, match="grave story"):
        validate_audience_assessment(
            _assessment(emotional_calibration=emotional),
            _plan(),
            DEFAULT_AUDIENCE_MODEL,
        )


def test_guaranteed_retention_claim_is_rejected():
    risk = _attention(claims_guaranteed_retention_outcome=True)
    with pytest.raises(AudienceValidationError, match="guaranteed retention"):
        validate_audience_assessment(
            _assessment(
                attention_risks=(risk,), audience_readiness="ready_with_advisories"
            ),
            _plan(),
            DEFAULT_AUDIENCE_MODEL,
        )


@pytest.mark.parametrize(
    "comprehension",
    [
        ComprehensionAssessment(summary="Missing.", missing_indispensable_context=True),
        ComprehensionAssessment(
            summary="Unknown.", unresolved_reference_ids=("pronoun-1",)
        ),
    ],
)
def test_missing_context_and_unresolved_references_block_readiness(comprehension):
    assessment = _assessment(
        comprehension_assessment=comprehension,
        audience_readiness=AudienceReadiness.BLOCKED,
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_excessive_optional_context_creates_advisory_readiness():
    context = _context(optional_context_excessive=True)
    assessment = _assessment(
        context_assessment=context, audience_readiness="ready_with_advisories"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_critical_trust_and_blocking_attention_risks_block():
    trust = _trust(severity="critical")
    assessment = _assessment(trust_risks=(trust,), audience_readiness="blocked")
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)
    attention = _attention(blocking=True)
    assessment = _assessment(attention_risks=(attention,), audience_readiness="blocked")
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_review_required_and_advisory_risks_produce_correct_readiness():
    review = _attention(requires_editor_in_chief_review=True)
    assessment = _assessment(
        attention_risks=(review,), audience_readiness="requires_editor_review"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_minor_fatigue_sources_accumulate_as_an_advisory():
    fatigue = AudienceFatigueAssessment(
        fatigue_id="af-1",
        fatigue_type=FatigueType.REPETITION,
        severity=AudienceRiskSeverity.LOW,
        affected_elements=("d1",),
        explanation="Several small repetitions accumulate.",
        mitigation="Remove repeated explanation.",
        cumulative_effect="Combined fatigue is editorially meaningful.",
        requires_editor_in_chief_review=False,
    )
    assessment = _assessment(
        fatigue_assessments=(fatigue,), audience_readiness="ready_with_advisories"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_review_required_fatigue_propagates_editor_review():
    fatigue = AudienceFatigueAssessment(
        fatigue_id="af-2",
        fatigue_type=FatigueType.OUTRAGE,
        severity=AudienceRiskSeverity.HIGH,
        affected_elements=("d1",),
        explanation="Cumulative outrage may exhaust the audience.",
        mitigation="Reduce escalation.",
        cumulative_effect="Episode-level tonal fatigue.",
        requires_editor_in_chief_review=True,
    )
    assessment = _assessment(
        fatigue_assessments=(fatigue,), audience_readiness="requires_editor_review"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)
    advisory = _attention()
    assessment = _assessment(
        attention_risks=(advisory,), audience_readiness="ready_with_advisories"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_clean_assessment_is_ready():
    assert validate_audience_assessment(_assessment(), _plan(), DEFAULT_AUDIENCE_MODEL)


@pytest.mark.parametrize(
    "changes",
    [
        {"blocking_issues": ("Missing context.",)},
        {"advisory_issues": ("Reduce names.",)},
    ],
)
def test_ready_cannot_coexist_with_blockers_or_advisories(changes):
    with pytest.raises(AudienceValidationError, match="audience readiness"):
        validate_audience_assessment(
            _assessment(**changes), _plan(), DEFAULT_AUDIENCE_MODEL
        )


def test_decision_plan_block_and_review_states_propagate():
    risk = EditorialRisk(
        risk_id="r1",
        risk_type=RiskType.INSUFFICIENT_VERIFICATION,
        severity=RiskSeverity.CRITICAL,
        affected_material_ids=("m1",),
        explanation="Missing verification.",
        mitigation="Verify.",
        blocking=True,
        requires_editor_in_chief_review=False,
    )
    blocked = _plan(
        risks=(risk,), blocking_issues=("Blocked.",), production_readiness="blocked"
    )
    assessment = _assessment(plan=blocked, audience_readiness="blocked")
    assert validate_audience_assessment(assessment, blocked, DEFAULT_AUDIENCE_MODEL)
    decision = _decision(requires_editor_in_chief_review=True)
    review = _plan(
        decision=decision,
        requires_editor_in_chief_review=True,
        production_readiness="requires_editor_review",
    )
    assessment = _assessment(plan=review, audience_readiness="requires_editor_review")
    assert validate_audience_assessment(assessment, review, DEFAULT_AUDIENCE_MODEL)


@pytest.mark.parametrize(
    "action", [EditorialAction.HOLD_FOR_VERIFICATION, EditorialAction.REMOVE]
)
def test_held_or_removed_material_cannot_be_required_context(action):
    decision = _decision(action=action, classification=FactImportance.OPTIONAL)
    plan = _plan(decision=decision)
    with pytest.raises(AudienceValidationError, match="held or removed"):
        validate_audience_assessment(
            _assessment(plan=plan), plan, DEFAULT_AUDIENCE_MODEL
        )


def test_unsafe_material_requires_contextualize_decision():
    plan = _plan(
        decision=_decision(classification=FactImportance.UNSAFE_WITHOUT_CONTEXT)
    )
    with pytest.raises(AudienceValidationError, match="explicit contextualize"):
        validate_audience_assessment(
            _assessment(plan=plan), plan, DEFAULT_AUDIENCE_MODEL
        )


@pytest.mark.parametrize(
    "status", [FactualStatus.ALLEGATION, FactualStatus.DISPUTED_CLAIM]
)
def test_allegation_and_disputed_status_remain_visible(status):
    material = _material(factual_status=status, attribution="source-a")
    plan = _plan(material=material)
    assert validate_audience_assessment(
        _assessment(plan=plan), plan, DEFAULT_AUDIENCE_MODEL
    )
    assert plan.source_material[0].factual_status == status


def test_assessment_cannot_modify_decisions_or_generate_text():
    with pytest.raises(AudienceValidationError, match="cannot modify"):
        validate_audience_assessment(
            _assessment(modifies_editorial_decisions=True),
            _plan(),
            DEFAULT_AUDIENCE_MODEL,
        )
    with pytest.raises(AudienceValidationError, match="script or joke"):
        validate_audience_assessment(
            _assessment(contains_generated_joke_text=True),
            _plan(),
            DEFAULT_AUDIENCE_MODEL,
        )


def test_joke_before_context_is_an_attention_advisory():
    risk = _attention(risk_type=AttentionRiskType.JOKE_BEFORE_CONTEXT)
    assessment = _assessment(
        attention_risks=(risk,), audience_readiness="ready_with_advisories"
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_dense_humor_with_high_context_is_advisory():
    context = _context(budget_level=ContextBudgetLevel.HIGH)
    dimensions = DEFAULT_SATIRICAL_VOICE.calibration.dimensions.model_copy(
        update={"humor_density": HumorDensity.DENSE}
    )
    calibration = _calibration(context_budget=context, voice_dimensions=dimensions)
    assessment = _assessment(
        calibration=calibration,
        context_assessment=context,
        audience_readiness="ready_with_advisories",
    )
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


def test_emerging_guidance_cannot_change_defaults_but_established_guidance_can_tune():
    emerging = _guidance(established=False)
    calibration = _calibration(established_profile_guidance=(emerging,))
    with pytest.raises(AudienceValidationError, match="emerging"):
        validate_audience_assessment(
            _assessment(calibration=calibration), _plan(), DEFAULT_AUDIENCE_MODEL
        )
    established = _guidance()
    calibration = _calibration(established_profile_guidance=(established,))
    assert validate_audience_assessment(
        _assessment(calibration=calibration), _plan(), DEFAULT_AUDIENCE_MODEL
    )


def test_profile_guidance_retains_evidence_and_conflicts_require_review():
    guidance = _guidance(contradictory_guidance_ids=("ag-2",))
    calibration = _calibration(established_profile_guidance=(guidance,))
    assessment = _assessment(
        calibration=calibration, audience_readiness="requires_editor_review"
    )
    assert guidance.source_finding_ids and guidance.evidence_episode_ids
    assert validate_audience_assessment(assessment, _plan(), DEFAULT_AUDIENCE_MODEL)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("permits_manipulation", "permit manipulation"),
        ("permits_factual_distortion", "permit factual distortion"),
        ("overrides_victim_safeguards", "victim safeguards"),
        ("infers_demographic_traits", "demographic traits"),
    ],
)
def test_profile_guidance_cannot_override_audience_boundaries(field, message):
    guidance = _guidance(**{field: True})
    calibration = _calibration(established_profile_guidance=(guidance,))
    with pytest.raises(AudienceValidationError, match=message):
        validate_audience_assessment(
            _assessment(calibration=calibration), _plan(), DEFAULT_AUDIENCE_MODEL
        )


def test_renderers_are_deterministic_complete_and_verbatim():
    model_render = render_audience_model(DEFAULT_AUDIENCE_MODEL)
    assert model_render.encode("utf-8") == render_audience_model(
        DEFAULT_AUDIENCE_MODEL
    ).encode("utf-8")
    assessment_render = render_audience_assessment(
        _assessment(), _plan(), DEFAULT_AUDIENCE_MODEL
    )
    assert assessment_render.encode("utf-8") == render_audience_assessment(
        _assessment(), _plan(), DEFAULT_AUDIENCE_MODEL
    ).encode("utf-8")
    for section in (
        "Audience Identity",
        "Primary Medium",
        "Audience Assumptions",
        "Canonical Principles",
        "Knowledge Model",
        "Cognitive Model",
        "Context Policy",
        "Attention Policy",
        "Trust Policy",
        "Emotional Reception",
        "Fatigue Policy",
        "Relationship with Editorial Profile",
        "Editor-in-Chief Authority",
        "Fixed Boundaries",
    ):
        assert f"\n{section}\n" in model_render
    for section in (
        "Assessment Identity",
        "Audience Readiness",
        "Audience Calibration",
        "Comprehension Assessment",
        "Context Assessment",
        "Attention Risks",
        "Trust Risks",
        "Fatigue Assessment",
        "Emotional Calibration",
        "Unresolved Audience Questions",
        "Blocking Issues",
        "Advisory Issues",
        "Editor-in-Chief Review",
    ):
        assert f"\n{section}\n" in assessment_render
    assert _material().content in assessment_render
    assert "generated joke" not in assessment_render.casefold()


def test_model_calibration_and_assessment_fingerprints_are_deterministic():
    assert audience_model_fingerprint(
        DEFAULT_AUDIENCE_MODEL
    ) == audience_model_fingerprint(DEFAULT_AUDIENCE_MODEL)
    assert calibration_fingerprint(_calibration()) == calibration_fingerprint(
        _calibration()
    )
    assert assessment_fingerprint(_assessment()) == assessment_fingerprint(
        _assessment()
    )


def test_meaningful_changes_alter_fingerprints():
    principles = list(DEFAULT_AUDIENCE_MODEL.principles)
    principles[0] = principles[0].model_copy(update={"statement": "Changed."})
    assert audience_model_fingerprint(
        DEFAULT_AUDIENCE_MODEL.model_copy(update={"principles": tuple(principles)})
    ) != audience_model_fingerprint(DEFAULT_AUDIENCE_MODEL)
    changed_context = _context(budget_level=ContextBudgetLevel.HIGH)
    assert calibration_fingerprint(
        _calibration(context_budget=changed_context)
    ) != calibration_fingerprint(_calibration())
    risk = _attention()
    assessment = _assessment(
        attention_risks=(risk,), audience_readiness="ready_with_advisories"
    )
    changed = assessment.model_copy(
        update={
            "attention_risks": (
                risk.model_copy(update={"severity": AudienceRiskSeverity.HIGH}),
            )
        }
    )
    assert assessment_fingerprint(assessment) != assessment_fingerprint(changed)
    emotional = _emotion(primary_intended_response=AudienceEmotion.REFLECTIVE)
    assert assessment_fingerprint(
        _assessment(emotional_calibration=emotional)
    ) != assessment_fingerprint(_assessment())


def test_unordered_collection_order_is_neutral_but_principle_order_is_semantic():
    model = DEFAULT_AUDIENCE_MODEL.model_copy(
        update={
            "audience_assumptions": tuple(
                reversed(DEFAULT_AUDIENCE_MODEL.audience_assumptions)
            )
        }
    )
    assert audience_model_fingerprint(model) == audience_model_fingerprint(
        DEFAULT_AUDIENCE_MODEL
    )
    principles = list(DEFAULT_AUDIENCE_MODEL.principles)
    principles[0] = principles[0].model_copy(update={"order": 99})
    model = DEFAULT_AUDIENCE_MODEL.model_copy(update={"principles": tuple(principles)})
    assert audience_model_fingerprint(model) != audience_model_fingerprint(
        DEFAULT_AUDIENCE_MODEL
    )


def test_audience_package_has_no_forbidden_dependency():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path("src/pastila_scout/editor/audience").glob("*.py"))
    ).casefold()
    for forbidden in (
        "import httpx",
        "import openai",
        "pastila_scout.ai",
        "pastila_scout.database",
        "pastila_scout.cli",
        "pastila_scout.editor.generation",
        "controlled_revision_quality",
        "path.write_text",
    ):
        assert forbidden not in source
