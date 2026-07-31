"""Focused Module 2.7B Romanian Conversational Engine tests."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from pastila_scout.editor.communication import (
    DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
    CommunicationAssessment,
    CommunicationReadiness,
    communication_assessment_fingerprint,
)
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA
from pastila_scout.editor.romanian_conversation import (
    CANONICAL_PRINCIPLE_TITLES,
    DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE,
    AuthenticityState,
    ConversationalAuthenticityAssessment,
    ConversationalReadiness,
    CorrectionCategory,
    CorrectionIntegrationPoint,
    CorrectionScope,
    FindingSeverity,
    GuidanceScope,
    GuidanceStatus,
    RegisterAssessment,
    RomanianConversationalAssessment,
    RomanianConversationalRisk,
    RomanianConversationValidationError,
    RomanianProfileGuidance,
    SocialRegister,
    assessment_fingerprint,
    correction_integration_fingerprint,
    engine_fingerprint,
    pattern_collection_fingerprint,
    profile_guidance_fingerprint,
    render_romanian_conversational_assessment,
    render_romanian_conversational_engine,
    risk_collection_fingerprint,
    validate_correction_integration_point,
    validate_romanian_conversational_assessment,
    validate_romanian_conversational_engine,
)
from pastila_scout.editor.story import StoryArchitecturePlan, story_plan_fingerprint


def _story() -> StoryArchitecturePlan:
    philosophy = DEFAULT_EDITORIAL_PERSONA.philosophy
    return StoryArchitecturePlan.model_construct(
        architecture_id="pastila-acida-spoken-satirical-story-architecture",
        version="1.0.0",
        persona_id=DEFAULT_EDITORIAL_PERSONA.persona_id,
        philosophy_id=philosophy.philosophy_id,
        voice_id="pastila-acida-romanian-spoken-satirical-commentary",
        audience_id="pastila-acida-core-audience",
        decision_plan_id="decision-plan-1",
    )


def _communication(
    story: StoryArchitecturePlan | None = None, **changes: object
) -> CommunicationAssessment:
    story = story or _story()
    values = {
        "assessment_id": "communication-1",
        "version": "1.0.0",
        "communication_engine_id": DEFAULT_SPOKEN_COMMUNICATION_ENGINE.communication_engine_id,
        "communication_engine_version": DEFAULT_SPOKEN_COMMUNICATION_ENGINE.version,
        "story_architecture_id": story.architecture_id,
        "story_architecture_version": story.version,
        "story_plan_fingerprint": story_plan_fingerprint(story),
        "requires_editor_in_chief_review": False,
        "readiness": CommunicationReadiness.READY,
        "summary": "Approved spoken communication policy assessment.",
    }
    values.update(changes)
    return CommunicationAssessment(**values)


def _auth(
    communication: CommunicationAssessment, **changes: object
) -> ConversationalAuthenticityAssessment:
    values = {
        "assessment_id": "authenticity-1",
        "engine_id": DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE.conversational_engine_id,
        "engine_fingerprint": engine_fingerprint(
            DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
        ),
        "communication_assessment_id": communication.assessment_id,
        "communication_assessment_fingerprint": communication_assessment_fingerprint(
            communication
        ),
        "evaluated_reference_identifiers": ("ref-1",),
        "authenticity_state": AuthenticityState.AUTHENTIC,
        "findings": (),
        "risks": (),
        "advisories": (),
        "evidence_references": ("ref-1",),
        "profile_guidance_references": (),
        "readiness": ConversationalReadiness.READY,
    }
    values.update(changes)
    return ConversationalAuthenticityAssessment(**values)


def _assessment(**changes: object) -> RomanianConversationalAssessment:
    story = _story()
    communication = _communication(story)
    values = {
        "assessment_id": "romanian-assessment-1",
        "version": "1.0.0",
        "engine_id": DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE.conversational_engine_id,
        "engine_version": DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE.version,
        "engine_fingerprint": engine_fingerprint(
            DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
        ),
        "communication_assessment_id": communication.assessment_id,
        "communication_assessment_fingerprint": communication_assessment_fingerprint(
            communication
        ),
        "story_architecture_plan_id": story.architecture_id,
        "story_architecture_plan_fingerprint": story_plan_fingerprint(story),
        "persona_id": story.persona_id,
        "philosophy_id": story.philosophy_id,
        "voice_id": story.voice_id,
        "audience_id": story.audience_id,
        "decision_plan_id": story.decision_plan_id,
        "evaluated_reference_identifiers": ("ref-1",),
        "authenticity_assessment": _auth(communication),
        "selected_register": SocialRegister.NEUTRAL_CONVERSATIONAL,
        "register_assessment": RegisterAssessment(
            selected_register=SocialRegister.NEUTRAL_CONVERSATIONAL,
            context_compatible=True,
            audience_compatible=True,
            persona_compatible=True,
            voice_compatible=True,
            severity_compatible=True,
            socially_credible=True,
            public_broadcast_suitable=True,
        ),
        "readiness": ConversationalReadiness.READY,
    }
    values.update(changes)
    return RomanianConversationalAssessment(**values)


def _validate(assessment: RomanianConversationalAssessment):
    story = _story()
    return validate_romanian_conversational_assessment(
        assessment, DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE, _communication(story), story
    )


def _risk(**changes: object) -> RomanianConversationalRisk:
    values = {
        "risk_id": "risk-1",
        "risk_type": "minor_cadence",
        "severity": FindingSeverity.LOW,
        "affected_policy_identifiers": ("romanian-rhythm-realization",),
        "explanation": "Minor cadence concern.",
        "evidence_references": ("ref-1",),
        "mitigation_direction": "Review cadence without replacement wording.",
        "blocking": False,
        "requires_editor_review": False,
    }
    values.update(changes)
    return RomanianConversationalRisk(**values)


def _guidance(**changes: object) -> RomanianProfileGuidance:
    values = {
        "guidance_id": "guidance-1",
        "dimension": "preferred_conversational_register",
        "value": "neutral_conversational",
        "strength": "medium",
        "status": GuidanceStatus.ESTABLISHED,
        "evidence_references": ("finding-1",),
        "episode_references": ("episode-1",),
        "editor_confirmed": False,
        "scope": GuidanceScope.FORMAT_SPECIFIC,
        "conflict_rules": (),
        "fixed_boundary_compatible": True,
    }
    values.update(changes)
    return RomanianProfileGuidance(**values)


def test_canonical_identity_principles_public_contract_and_immutability():
    engine = DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
    assert validate_romanian_conversational_engine(engine) is engine
    assert (
        engine.conversational_engine_id
        == "pastila-acida-romanian-conversational-engine"
    )
    assert (engine.language, engine.language_code) == ("Romanian", "ro-RO")
    assert len(engine.principles) == len(CANONICAL_PRINCIPLE_TITLES) == 36
    assert tuple(item.order for item in engine.principles) == tuple(range(1, 37))
    with pytest.raises(ValidationError):
        engine.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "field",
    (
        "syntax_policy",
        "word_order_policy",
        "ellipsis_policy",
        "fragment_policy",
        "repetition_policy",
        "connector_policy",
        "colloquial_policy",
        "slang_policy",
        "jargon_policy",
        "lexical_naturalness_policy",
        "translated_construction_policy",
        "press_language_policy",
        "bureaucratic_language_policy",
        "academic_language_policy",
        "legal_precision_policy",
        "entity_reference_policy",
        "demonstrative_policy",
        "emphasis_policy",
        "rhythm_realization_policy",
        "repair_policy",
        "satire_integration_policy",
        "sensitivity_policy",
        "teleprompter_realization_policy",
    ),
)
def test_every_policy_is_bounded_immutable_and_non_generative(field: str):
    policy = getattr(DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE, field)
    assert policy.supported_features and not policy.permits_generated_wording
    with pytest.raises(ValidationError):
        policy.policy_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "update",
    (
        {"version": "v1"},
        {"language_code": "en-US"},
        {"contains_generation_procedures": True},
        {"implements_learning": True},
        {"contains_unbounded_dictionary": True},
    ),
)
def test_engine_rejects_invalid_identity_generation_learning_and_unbounded_dictionary(
    update: dict[str, object],
):
    with pytest.raises(RomanianConversationValidationError):
        validate_romanian_conversational_engine(
            DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE.model_copy(update=update)
        )


def test_register_hierarchy_and_bounded_catalogues_are_canonical():
    engine = DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
    assert engine.register_policy.preferred_registers[:2] == (
        SocialRegister.NEUTRAL_CONVERSATIONAL,
        SocialRegister.POLISHED_CONVERSATIONAL,
    )
    assert SocialRegister.JOURNALISTIC in engine.register_policy.discouraged_registers
    assert (
        SocialRegister.PERFORMATIVE_SLANG
        in engine.register_policy.discouraged_registers
    )
    assert len(engine.conversational_patterns) == 27
    assert len(engine.canonical_reference_catalogue) == 15
    assert all(
        len(example) <= 100
        for pattern in engine.conversational_patterns
        for example in pattern.examples
    )
    assert all(not item.claims_ai_authorship for item in engine.ai_likeness_indicators)


def test_clean_authentic_assessment_validates():
    assert _validate(_assessment()).readiness == ConversationalReadiness.READY


@pytest.mark.parametrize(
    "update",
    (
        {"engine_fingerprint": "0" * 64},
        {"communication_assessment_fingerprint": "0" * 64},
        {"story_architecture_plan_fingerprint": "0" * 64},
        {"persona_id": "wrong"},
        {"modifies_upstream_contracts": True},
        {"contains_generated_text": True},
        {"contains_replacement_language": True},
    ),
)
def test_assessment_rejects_lineage_mutation_and_generation(update: dict[str, object]):
    with pytest.raises(RomanianConversationValidationError):
        _validate(_assessment(**update))


def test_context_dependent_authenticity_and_street_register_require_review():
    base = _assessment()
    contextual = base.model_copy(
        update={
            "authenticity_assessment": base.authenticity_assessment.model_copy(
                update={
                    "authenticity_state": AuthenticityState.CONTEXT_DEPENDENT,
                    "readiness": ConversationalReadiness.REQUIRES_EDITOR_REVIEW,
                }
            ),
            "readiness": ConversationalReadiness.REQUIRES_EDITOR_REVIEW,
        }
    )
    assert (
        _validate(contextual).readiness
        == ConversationalReadiness.REQUIRES_EDITOR_REVIEW
    )
    street_register = base.register_assessment.model_copy(
        update={
            "selected_register": SocialRegister.STREET_INFLUENCED,
            "requires_editor_review": True,
        }
    )
    street = base.model_copy(
        update={
            "selected_register": SocialRegister.STREET_INFLUENCED,
            "register_assessment": street_register,
            "readiness": ConversationalReadiness.REQUIRES_EDITOR_REVIEW,
        }
    )
    assert _validate(street).readiness == ConversationalReadiness.REQUIRES_EDITOR_REVIEW


def test_readiness_block_review_advisory_and_manual_consistency():
    advisory = _assessment(
        risks=(_risk(),), readiness=ConversationalReadiness.READY_WITH_ADVISORIES
    )
    review = _assessment(
        risks=(_risk(severity=FindingSeverity.HIGH, requires_editor_review=True),),
        readiness=ConversationalReadiness.REQUIRES_EDITOR_REVIEW,
    )
    blocked = _assessment(
        risks=(_risk(severity=FindingSeverity.CRITICAL, blocking=True),),
        readiness=ConversationalReadiness.BLOCKED,
    )
    for item in (advisory, review, blocked):
        assert _validate(item) is item
    with pytest.raises(RomanianConversationValidationError, match="readiness"):
        _validate(
            blocked.model_copy(update={"readiness": ConversationalReadiness.READY})
        )


@pytest.mark.parametrize(
    "update",
    (
        {"status": GuidanceStatus.OBSERVED},
        {"status": GuidanceStatus.EMERGING},
        {"status": GuidanceStatus.DEPRECATED},
        {"status": GuidanceStatus.REJECTED},
    ),
)
def test_non_active_guidance_statuses_remain_accepted_but_nonoperative(
    update: dict[str, object],
):
    assert _validate(_assessment(profile_guidance=(_guidance(**update),)))


def test_established_and_confirmed_explicit_guidance_validate_but_boundaries_hold():
    assert _validate(_assessment(profile_guidance=(_guidance(),)))
    explicit = _guidance(
        status=GuidanceStatus.EXPLICIT_EDITOR_RULE, editor_confirmed=True
    )
    assert _validate(_assessment(profile_guidance=(explicit,)))
    for guidance in (
        _guidance(dimension="unknown"),
        _guidance(fixed_boundary_compatible=False),
        _guidance(attempts_upstream_override=True),
        _guidance(status=GuidanceStatus.EXPLICIT_EDITOR_RULE, editor_confirmed=False),
    ):
        with pytest.raises(RomanianConversationValidationError):
            _validate(_assessment(profile_guidance=(guidance,)))


def test_correction_handoff_preserves_references_and_never_learns_or_persists():
    point = CorrectionIntegrationPoint(
        correction_id="correction-1",
        original_reference="ref-original",
        edited_reference="ref-edited",
        editor_explanation="Word order was marked.",
        correction_category=CorrectionCategory.WORD_ORDER,
        correction_scope=CorrectionScope.LOCAL,
        explicit_permanence=False,
        episode_provenance=("episode-1",),
        text_region_provenance=("region-1",),
        accepted_direction="Prefer direct order locally.",
        rejected_direction="Avoid marked inversion locally.",
    )
    assert validate_correction_integration_point(point) is point
    assert point.original_reference and point.edited_reference
    permanent = point.model_copy(
        update={"correction_scope": CorrectionScope.PERMANENT_PROJECT_RULE}
    )
    with pytest.raises(RomanianConversationValidationError, match="explicit"):
        validate_correction_integration_point(permanent)
    for flag in (
        "performs_learning",
        "performs_persistence",
        "mutates_canonical_engine",
        "contains_generated_replacement_prose",
    ):
        with pytest.raises(RomanianConversationValidationError):
            validate_correction_integration_point(point.model_copy(update={flag: True}))


def test_rendering_is_deterministic_utf8_bounded_and_reference_only():
    engine = DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
    first = render_romanian_conversational_engine(engine)
    assert first == render_romanian_conversational_engine(engine)
    assert "Română" not in first  # canonical identity uses Romanian and ro-RO
    assert "Instituția" not in first
    first.encode("utf-8")
    assessment = render_romanian_conversational_assessment(
        _assessment(), engine, _communication(), _story()
    )
    assert assessment == render_romanian_conversational_assessment(
        _assessment(), engine, _communication(), _story()
    )
    assert (
        "timestamp" not in assessment.lower()
        and "replacement wording" not in assessment.lower()
    )


def test_fingerprints_preserve_semantic_order_and_normalize_unordered_collections():
    engine = DEFAULT_ROMANIAN_CONVERSATIONAL_ENGINE
    assert engine_fingerprint(engine) == engine_fingerprint(
        engine.model_copy(deep=True)
    )
    changed = engine.model_copy(
        update={"principles": tuple(reversed(engine.principles))}
    )
    assert engine_fingerprint(engine) != engine_fingerprint(changed)
    assert pattern_collection_fingerprint(
        engine.conversational_patterns
    ) != pattern_collection_fingerprint(tuple(reversed(engine.conversational_patterns)))
    risk2 = _risk(risk_id="risk-2")
    assert risk_collection_fingerprint((_risk(), risk2)) == risk_collection_fingerprint(
        (risk2, _risk())
    )
    guidance2 = _guidance(guidance_id="guidance-2")
    assert profile_guidance_fingerprint(
        (_guidance(), guidance2)
    ) == profile_guidance_fingerprint((guidance2, _guidance()))
    assert assessment_fingerprint(_assessment()) == assessment_fingerprint(
        _assessment().model_copy(deep=True)
    )


def test_correction_fingerprint_normalizes_reference_collection_order():
    assert correction_integration_fingerprint(
        ("a", "b")
    ) == correction_integration_fingerprint(("b", "a"))


def test_no_forbidden_runtime_or_generation_dependencies():
    from pastila_scout.editor import romanian_conversation

    modules = " ".join(
        getattr(getattr(romanian_conversation, name), "__module__", "")
        for name in romanian_conversation.__all__
    )
    source = " ".join(
        inspect.getsource(getattr(romanian_conversation, name))
        for name in romanian_conversation.__all__
        if inspect.isfunction(getattr(romanian_conversation, name))
    ).lower()
    for forbidden in ("openai", "httpx", "sqlite", "requests", "cli"):
        assert forbidden not in modules
    assert "generate_script" not in source and "network" not in source
