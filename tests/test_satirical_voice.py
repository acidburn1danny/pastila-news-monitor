"""Focused Module 2.4 Satirical Voice contract and compatibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

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
    EmotionalTemperature,
    HumorDensity,
    MechanismType,
    SarcasmIntensity,
    SatiricalOpportunity,
    SatiricalRisk,
    SatiricalRiskSeverity,
    SatiricalRiskType,
    SatiricalTargetType,
    SatiricalVoiceValidationError,
    SensitiveSubjectType,
    TonalSeriousness,
    VoiceConfidence,
    VoiceDimensions,
    VoiceProfileGuidance,
    apply_profile_guidance,
    opportunity_fingerprint,
    render_opportunity,
    render_satirical_voice,
    risk_collection_fingerprint,
    validate_satirical_opportunity,
    validate_satirical_voice,
    voice_fingerprint,
)

REQUIRED_PRINCIPLES = {
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


def _dimensions(**changes) -> VoiceDimensions:
    values = DEFAULT_SATIRICAL_VOICE.calibration.dimensions.model_dump()
    values.update(changes)
    return VoiceDimensions(**values)


def _material(**changes) -> EditorialMaterial:
    values = {
        "material_id": "m1",
        "source_reference": "source-a",
        "material_type": MaterialType.FACT,
        "content": "Instituția a anunțat măsura miercuri.",
        "factual_status": FactualStatus.VERIFIED_FACT,
        "chronology_position": 1,
    }
    values.update(changes)
    return EditorialMaterial(**values)


def _decision(**changes) -> EditorialDecision:
    values = {
        "decision_id": "d1",
        "stage": DecisionStage.EDITORIAL_CORE,
        "rank": 1,
        "material_ids": ("m1",),
        "classification": FactImportance.INDISPENSABLE,
        "action": EditorialAction.PRESERVE,
        "rationale": "This is the supported editorial core.",
        "evidence": ("m1",),
        "principle_ids": ("truth-before-performance",),
        "confidence": DecisionConfidence.HIGH,
        "consequence_if_ignored": "The account would lose its factual core.",
    }
    values.update(changes)
    return EditorialDecision(**values)


def _plan(material=None, decision=None, **changes) -> EditorialDecisionPlan:
    material = material or _material()
    decision = decision or _decision()
    core_element = CoreElement(
        statement="Măsura a fost anunțată.", material_ids=("m1",)
    )
    core = EditorialCore(
        what_happened=core_element,
        involved_parties=core_element,
        why_it_matters=core_element,
        consequence=core_element,
        central_tension=core_element,
        factual_boundaries=(core_element,),
    )
    philosophy = DEFAULT_EDITORIAL_PERSONA.philosophy
    values = {
        "plan_id": "plan-voice",
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
        "summary": "Safe evidence-linked plan.",
    }
    values.update(changes)
    return EditorialDecisionPlan(**values)


def _opportunity(**changes) -> SatiricalOpportunity:
    values = {
        "opportunity_id": "so-1",
        "supported_material_ids": ("m1",),
        "editorial_core_element_ids": ("what_happened", "central_tension"),
        "decision_ids": ("d1",),
        "target_type": SatiricalTargetType.INSTITUTION,
        "target_description": "The institution's supported public conduct.",
        "supported_mechanisms": (MechanismType.IRONY,),
        "factual_basis": ("Instituția a anunțat măsura miercuri.",),
        "contradiction_or_absurdity": "The announced measure conflicts with its stated goal.",
        "intended_editorial_function": "Expose the supported contradiction.",
        "tonal_limit": TonalSeriousness.MIXED,
        "recommended_dimensions": _dimensions(),
        "confidence": VoiceConfidence.HIGH,
        "prohibited_interpretations": ("Do not imply unsupported criminal intent.",),
        "requires_editor_in_chief_review": False,
    }
    values.update(changes)
    return SatiricalOpportunity(**values)


def test_canonical_satirical_voice_validates():
    assert validate_satirical_voice(DEFAULT_SATIRICAL_VOICE) is DEFAULT_SATIRICAL_VOICE


def test_all_voice_models_are_immutable():
    with pytest.raises(ValidationError):
        DEFAULT_SATIRICAL_VOICE.title = "Changed"  # type: ignore[misc]


def test_all_canonical_principles_exist():
    assert {
        item.principle_id for item in DEFAULT_SATIRICAL_VOICE.principles
    } == REQUIRED_PRINCIPLES


def test_all_canonical_mechanisms_exist():
    assert {item.mechanism_id for item in DEFAULT_SATIRICAL_VOICE.mechanisms} == set(
        MechanismType
    )


def test_all_target_types_exist():
    assert set(DEFAULT_SATIRICAL_VOICE.calibration.valid_targets) == set(
        SatiricalTargetType
    )


def test_all_sensitive_subject_types_exist():
    assert set(DEFAULT_SATIRICAL_VOICE.calibration.protected_subjects) == set(
        SensitiveSubjectType
    )


def test_duplicate_principle_identifiers_are_rejected():
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(
        update={
            "principles": (
                *DEFAULT_SATIRICAL_VOICE.principles,
                DEFAULT_SATIRICAL_VOICE.principles[0],
            )
        }
    )
    with pytest.raises(SatiricalVoiceValidationError, match="duplicate.*principle"):
        validate_satirical_voice(voice)


def test_duplicate_mechanism_identifiers_are_rejected():
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(
        update={
            "mechanisms": (
                *DEFAULT_SATIRICAL_VOICE.mechanisms,
                DEFAULT_SATIRICAL_VOICE.mechanisms[0],
            )
        }
    )
    with pytest.raises(
        SatiricalVoiceValidationError, match="duplicate satirical mechanism"
    ):
        validate_satirical_voice(voice)


def test_invalid_semantic_version_is_rejected():
    with pytest.raises(SatiricalVoiceValidationError, match="semantic versioning"):
        validate_satirical_voice(
            DEFAULT_SATIRICAL_VOICE.model_copy(update={"version": "one"})
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sarcasm_intensity", "extreme"),
        ("emotional_temperature", "furious"),
        ("conversational_proximity", "remote"),
        ("humor_density", "constant"),
        ("tonal_seriousness", "comic"),
    ],
)
def test_invalid_voice_dimensions_are_rejected(field, value):
    data = _dimensions().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        VoiceDimensions.model_validate(data)


def test_rendering_and_fingerprint_are_deterministic():
    assert render_satirical_voice(DEFAULT_SATIRICAL_VOICE).encode(
        "utf-8"
    ) == render_satirical_voice(DEFAULT_SATIRICAL_VOICE).encode("utf-8")
    assert voice_fingerprint(DEFAULT_SATIRICAL_VOICE) == voice_fingerprint(
        DEFAULT_SATIRICAL_VOICE
    )


def test_principle_and_mechanism_changes_alter_fingerprint():
    principles = list(DEFAULT_SATIRICAL_VOICE.principles)
    principles[0] = principles[0].model_copy(update={"statement": "Changed."})
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(update={"principles": tuple(principles)})
    assert voice_fingerprint(voice) != voice_fingerprint(DEFAULT_SATIRICAL_VOICE)
    mechanisms = list(DEFAULT_SATIRICAL_VOICE.mechanisms)
    mechanisms[0] = mechanisms[0].model_copy(update={"definition": "Changed."})
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(update={"mechanisms": tuple(mechanisms)})
    assert voice_fingerprint(voice) != voice_fingerprint(DEFAULT_SATIRICAL_VOICE)


def test_unordered_collection_order_does_not_alter_fingerprint():
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(
        update={
            "characteristics": tuple(reversed(DEFAULT_SATIRICAL_VOICE.characteristics)),
            "principles": tuple(reversed(DEFAULT_SATIRICAL_VOICE.principles)),
            "mechanisms": tuple(reversed(DEFAULT_SATIRICAL_VOICE.mechanisms)),
        }
    )
    assert voice_fingerprint(voice) == voice_fingerprint(DEFAULT_SATIRICAL_VOICE)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {
                "sensitivity": SensitiveSubjectType.VICTIMS,
                "targets_sensitive_subject": True,
            },
            "victims",
        ),
        (
            {
                "sensitivity": SensitiveSubjectType.EXPLOITED_PERSONS,
                "targets_sensitive_subject": True,
            },
            "vulnerable",
        ),
        ({"permits_factual_distortion": True}, "factual distortion"),
        ({"contains_unsupported_accusation": True}, "unsupported accusation"),
        ({"invents_motive": True}, "motive invention"),
        (
            {
                "sensitivity": SensitiveSubjectType.PROTECTED_CHARACTERISTICS,
                "targets_sensitive_subject": True,
            },
            "protected characteristics",
        ),
        ({"detached_from_editorial_core": True}, "detached from Editorial Core"),
        ({"generic_insult_is_sole_mechanism": True}, "generic insult"),
    ],
)
def test_unsafe_satirical_opportunities_are_rejected(changes, message):
    with pytest.raises(SatiricalVoiceValidationError, match=message):
        validate_satirical_opportunity(
            _opportunity(**changes), _plan(), DEFAULT_SATIRICAL_VOICE
        )


def test_blocked_plan_cannot_support_opportunity():
    risk = EditorialRisk(
        risk_id="r-plan",
        risk_type=RiskType.INSUFFICIENT_VERIFICATION,
        severity=RiskSeverity.CRITICAL,
        affected_material_ids=("m1",),
        explanation="Central verification missing.",
        mitigation="Verify.",
        blocking=True,
        requires_editor_in_chief_review=False,
    )
    plan = _plan(
        risks=(risk,),
        blocking_issues=("Missing verification.",),
        production_readiness="blocked",
    )
    with pytest.raises(SatiricalVoiceValidationError, match="blocked Decision Plan"):
        validate_satirical_opportunity(_opportunity(), plan, DEFAULT_SATIRICAL_VOICE)


@pytest.mark.parametrize(
    "action", [EditorialAction.HOLD_FOR_VERIFICATION, EditorialAction.REMOVE]
)
def test_held_or_removed_material_cannot_support_opportunity(action):
    plan = _plan(
        decision=_decision(action=action, classification=FactImportance.OPTIONAL)
    )
    with pytest.raises(SatiricalVoiceValidationError, match="removed or held"):
        validate_satirical_opportunity(_opportunity(), plan, DEFAULT_SATIRICAL_VOICE)


def test_unsafe_without_context_requires_contextualization():
    plan = _plan(
        decision=_decision(classification=FactImportance.UNSAFE_WITHOUT_CONTEXT)
    )
    with pytest.raises(
        SatiricalVoiceValidationError, match="requires contextualization"
    ):
        validate_satirical_opportunity(_opportunity(), plan, DEFAULT_SATIRICAL_VOICE)


def test_unresolved_central_claim_cannot_support_high_confidence():
    material = _material(factual_status=FactualStatus.UNKNOWN_UNRESOLVED)
    with pytest.raises(SatiricalVoiceValidationError, match="unresolved central claim"):
        validate_satirical_opportunity(
            _opportunity(), _plan(material=material), DEFAULT_SATIRICAL_VOICE
        )


def test_allegations_and_disputed_claims_preserve_status_and_attribution():
    allegation = _material(
        material_type=MaterialType.ALLEGATION,
        factual_status=FactualStatus.ALLEGATION,
        attribution="source-a",
    )
    assert validate_satirical_opportunity(
        _opportunity(), _plan(material=allegation), DEFAULT_SATIRICAL_VOICE
    )
    disputed = _material(
        factual_status=FactualStatus.DISPUTED_CLAIM, attribution="source-a"
    )
    with pytest.raises(SatiricalVoiceValidationError, match="preserve dispute status"):
        validate_satirical_opportunity(
            _opportunity(preserves_dispute_status=False),
            _plan(material=disputed),
            DEFAULT_SATIRICAL_VOICE,
        )


def test_serious_dense_humor_requires_editor_review():
    opportunity = _opportunity(
        tonal_limit=TonalSeriousness.SERIOUS,
        recommended_dimensions=_dimensions(
            tonal_seriousness=TonalSeriousness.SERIOUS, humor_density=HumorDensity.DENSE
        ),
    )
    with pytest.raises(
        SatiricalVoiceValidationError, match="requires Editor-in-Chief review"
    ):
        validate_satirical_opportunity(opportunity, _plan(), DEFAULT_SATIRICAL_VOICE)


def test_grave_material_defaults_to_restrained_sparse_satire():
    opportunity = _opportunity(
        tonal_limit=TonalSeriousness.GRAVE,
        recommended_dimensions=_dimensions(
            tonal_seriousness=TonalSeriousness.GRAVE,
            sarcasm_intensity=SarcasmIntensity.RESTRAINED,
            emotional_temperature=EmotionalTemperature.GRAVE,
            humor_density=HumorDensity.SPARSE,
        ),
    )
    assert validate_satirical_opportunity(opportunity, _plan(), DEFAULT_SATIRICAL_VOICE)


def test_emerging_profile_trend_cannot_mutate_voice():
    guidance = VoiceProfileGuidance(
        established=False, dimensions=_dimensions(humor_density="dense")
    )
    assert (
        apply_profile_guidance(DEFAULT_SATIRICAL_VOICE, guidance)
        == DEFAULT_SATIRICAL_VOICE.calibration
    )


def test_established_profile_guidance_may_tune_dimensions():
    guidance = VoiceProfileGuidance(
        established=True, dimensions=_dimensions(humor_density="sparse")
    )
    assert (
        apply_profile_guidance(
            DEFAULT_SATIRICAL_VOICE, guidance
        ).dimensions.humor_density
        == HumorDensity.SPARSE
    )


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("permits_protected_subject_targeting", "victim targeting"),
        ("permits_factual_distortion", "factual distortion"),
        ("overrides_fixed_boundaries", "fixed boundaries"),
    ],
)
def test_profile_guidance_cannot_override_fixed_voice_safety(field, message):
    guidance = VoiceProfileGuidance(
        established=True, dimensions=_dimensions(), **{field: True}
    )
    with pytest.raises(SatiricalVoiceValidationError, match=message):
        apply_profile_guidance(DEFAULT_SATIRICAL_VOICE, guidance)


def test_opportunity_cannot_contain_generated_joke_text():
    with pytest.raises(SatiricalVoiceValidationError, match="generated joke text"):
        validate_satirical_opportunity(
            _opportunity(contains_generated_joke_text=True),
            _plan(),
            DEFAULT_SATIRICAL_VOICE,
        )


def test_voice_renderer_includes_all_required_sections():
    rendered = render_satirical_voice(DEFAULT_SATIRICAL_VOICE)
    for section in (
        "Voice Identity",
        "Purpose",
        "Voice Characteristics",
        "Canonical Principles",
        "Satirical Mechanisms",
        "Valid Targets",
        "Protected and Sensitive Subjects",
        "Default Voice Dimensions",
        "Fixed Boundaries",
        "Relationship with Editorial Profile",
        "Editor-in-Chief Authority",
    ):
        assert f"\n{section}\n" in rendered


def test_opportunity_renderer_sections_and_verbatim_evidence():
    rendered = render_opportunity(_opportunity(), _plan(), DEFAULT_SATIRICAL_VOICE)
    for section in (
        "Opportunity Identity",
        "Evidence",
        "Target",
        "Editorial Function",
        "Supported Mechanisms",
        "Tonal Limits",
        "Sensitivity",
        "Risks",
        "Confidence",
        "Editor-in-Chief Review",
    ):
        assert f"\n{section}\n" in rendered
    assert _material().content in rendered


def test_voice_fingerprint_changes_with_protected_subject_policy():
    calibration = DEFAULT_SATIRICAL_VOICE.calibration.model_copy(
        update={"protected_subjects": (SensitiveSubjectType.VICTIMS,)}
    )
    voice = DEFAULT_SATIRICAL_VOICE.model_copy(update={"calibration": calibration})
    assert voice_fingerprint(voice) != voice_fingerprint(DEFAULT_SATIRICAL_VOICE)


def test_opportunity_fingerprint_changes_with_evidence():
    assert opportunity_fingerprint(_opportunity()) != opportunity_fingerprint(
        _opportunity(factual_basis=("Changed evidence.",))
    )


def test_risk_fingerprint_changes_with_severity():
    risk = SatiricalRisk(
        risk_id="sr1",
        risk_type=SatiricalRiskType.TONAL_INSENSITIVITY,
        severity=SatiricalRiskSeverity.LOW,
        affected_opportunity_ids=("so-1",),
        explanation="Tone may be too light.",
        mitigation="Use restraint.",
        blocking=False,
        requires_editor_in_chief_review=False,
    )
    changed = risk.model_copy(update={"severity": SatiricalRiskSeverity.HIGH})
    assert risk_collection_fingerprint((risk,)) != risk_collection_fingerprint(
        (changed,)
    )


def test_no_personality_imitation_or_fictional_biography():
    assert not DEFAULT_SATIRICAL_VOICE.contains_personality_imitation
    assert not DEFAULT_SATIRICAL_VOICE.contains_fictional_biography


def test_voice_package_has_no_forbidden_dependency():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path("src/pastila_scout/editor/voice").glob("*.py"))
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
