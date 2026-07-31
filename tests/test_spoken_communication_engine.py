"""Focused Module 2.7A Spoken Communication Engine tests."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from pastila_scout.editor.communication import (
    CANONICAL_COMMUNICATION_PRINCIPLES,
    DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
    SUPPORTED_PROFILE_DIMENSIONS,
    CommunicationAssessment,
    CommunicationProfileGuidance,
    CommunicationReadiness,
    CommunicationRisk,
    CommunicationRiskSeverity,
    CommunicationRiskType,
    CommunicationValidationError,
    communication_assessment_fingerprint,
    communication_engine_fingerprint,
    communication_profile_guidance_fingerprint,
    communication_risk_collection_fingerprint,
    render_attention,
    render_communication_assessment,
    render_communication_flow,
    render_continuity,
    render_emotion_timing,
    render_orientation,
    render_pauses,
    render_rhythm,
    render_spoken_communication_engine,
    render_teleprompter_cognition,
    render_transitions,
    render_working_memory,
    validate_communication_assessment,
    validate_spoken_communication_engine,
    working_memory_fingerprint,
)
from pastila_scout.editor.story import StoryArchitecturePlan, story_plan_fingerprint


def _story_plan() -> StoryArchitecturePlan:
    return StoryArchitecturePlan.model_construct(
        architecture_id="pastila-acida-spoken-satirical-story-architecture",
        version="1.0.0",
        summary="Approved reference-only Story Architecture Plan.",
    )


def _assessment(**changes: object) -> CommunicationAssessment:
    story_plan = _story_plan()
    values = {
        "assessment_id": "communication-assessment-1",
        "version": "1.0.0",
        "communication_engine_id": DEFAULT_SPOKEN_COMMUNICATION_ENGINE.communication_engine_id,
        "communication_engine_version": DEFAULT_SPOKEN_COMMUNICATION_ENGINE.version,
        "story_architecture_id": story_plan.architecture_id,
        "story_architecture_version": story_plan.version,
        "story_plan_fingerprint": story_plan_fingerprint(story_plan),
        "requires_editor_in_chief_review": False,
        "readiness": CommunicationReadiness.READY,
        "summary": "The approved architecture can travel clearly through speech.",
    }
    values.update(changes)
    return CommunicationAssessment(**values)


def _guidance(**changes: object) -> CommunicationProfileGuidance:
    values = {
        "guidance_id": "communication-guidance-1",
        "source_finding_ids": ("finding-1",),
        "evidence_episode_ids": ("episode-1", "episode-2"),
        "established": True,
        "active": True,
        "tuning_dimensions": ("preferred_pacing",),
        "proposed_tuning": ("Reduce sustained high information density.",),
        "fixed_boundary_compatible": True,
    }
    values.update(changes)
    return CommunicationProfileGuidance(**values)


def _risk(**changes: object) -> CommunicationRisk:
    values = {
        "risk_id": "communication-risk-1",
        "risk_type": CommunicationRiskType.REFERENCE_AMBIGUITY,
        "severity": CommunicationRiskSeverity.LOW,
        "affected_models": ("references",),
        "editorial_explanation": "Several references remain active.",
        "mitigation": "Refresh the relevant reference before progression.",
        "blocking": False,
        "requires_editor_in_chief_review": False,
    }
    values.update(changes)
    return CommunicationRisk(**values)


def test_canonical_engine_validates_with_frozen_identity():
    engine = DEFAULT_SPOKEN_COMMUNICATION_ENGINE
    assert validate_spoken_communication_engine(engine) is engine
    assert engine.communication_engine_id == "pastila-acida-spoken-communication-engine"
    assert engine.version == "1.0.0"
    assert engine.language == "language-neutral"
    with pytest.raises(ValidationError):
        engine.title = "Changed"  # type: ignore[misc]


def test_all_twenty_canonical_principles_exist_in_explicit_order():
    principles = DEFAULT_SPOKEN_COMMUNICATION_ENGINE.principles
    assert len(principles) == 20
    assert tuple(item.principle_id for item in principles) == tuple(
        identifier for identifier, _ in CANONICAL_COMMUNICATION_PRINCIPLES
    )
    assert tuple(item.order for item in principles) == tuple(range(1, 21))


@pytest.mark.parametrize(
    "attribute",
    (
        "working_memory",
        "communication_flow",
        "rhythm",
        "pauses",
        "attention",
        "orientation",
        "references",
        "continuity",
        "transitions",
        "payoff_timing",
        "emotion_timing",
        "teleprompter_cognition",
    ),
)
def test_all_canonical_policy_models_are_present_and_immutable(attribute: str):
    model = getattr(DEFAULT_SPOKEN_COMMUNICATION_ENGINE, attribute)
    assert model.model_dump()
    with pytest.raises(ValidationError):
        setattr(model, next(iter(type(model).model_fields)), "changed")


def test_working_memory_capacities_are_positive_editorial_heuristics():
    model = DEFAULT_SPOKEN_COMMUNICATION_ENGINE.working_memory
    assert (
        min(
            model.concept_capacity,
            model.entity_capacity,
            model.reference_capacity,
            model.context_capacity,
            model.number_capacity,
            model.carry_over_capacity,
        )
        > 0
    )
    bad = DEFAULT_SPOKEN_COMMUNICATION_ENGINE.model_copy(
        update={
            "working_memory": model.model_copy(
                update={"claims_neuroscientific_precision": True}
            )
        }
    )
    with pytest.raises(CommunicationValidationError, match="neuroscience"):
        validate_spoken_communication_engine(bad)


@pytest.mark.parametrize(
    ("update", "message"),
    (
        ({"version": "v1"}, "semantic versioning"),
        ({"language": "Romanian"}, "language-neutral"),
        ({"contains_generated_language": True}, "cannot generate"),
        ({"contains_language_specific_rules": True}, "cannot generate"),
        ({"contains_generation_procedures": True}, "cannot generate"),
        ({"implements_learning": True}, "cannot generate"),
    ),
)
def test_engine_rejects_version_generation_language_specificity_and_learning(
    update: dict[str, object], message: str
):
    with pytest.raises(CommunicationValidationError, match=message):
        validate_spoken_communication_engine(
            DEFAULT_SPOKEN_COMMUNICATION_ENGINE.model_copy(update=update)
        )


def test_payoff_pause_transition_attention_and_teleprompter_boundaries():
    engine = DEFAULT_SPOKEN_COMMUNICATION_ENGINE
    cases = (
        engine.model_copy(
            update={
                "payoff_timing": engine.payoff_timing.model_copy(
                    update={"minimum_setup_units": 9}
                )
            }
        ),
        engine.model_copy(
            update={
                "pauses": engine.pauses.model_copy(update={"defines_punctuation": True})
            }
        ),
        engine.model_copy(
            update={
                "transitions": engine.transitions.model_copy(
                    update={"contains_transition_wording": True}
                )
            }
        ),
        engine.model_copy(
            update={
                "attention": engine.attention.model_copy(
                    update={"predicts_listener_behavior": True}
                )
            }
        ),
        engine.model_copy(
            update={
                "teleprompter_cognition": engine.teleprompter_cognition.model_copy(
                    update={"contains_formatting_rules": True}
                )
            }
        ),
    )
    for candidate in cases:
        with pytest.raises(CommunicationValidationError):
            validate_spoken_communication_engine(candidate)


def test_all_profile_integration_points_are_exposed_without_learning():
    assert set(DEFAULT_SPOKEN_COMMUNICATION_ENGINE.supported_profile_dimensions) == set(
        SUPPORTED_PROFILE_DIMENSIONS
    )
    assessment = _assessment(profile_guidance=(_guidance(),))
    assert (
        validate_communication_assessment(
            assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, _story_plan()
        )
        is assessment
    )


@pytest.mark.parametrize(
    "change",
    (
        {"established": False},
        {"tuning_dimensions": ("unknown_dimension",)},
        {"fixed_boundary_compatible": False},
        {"changes_story_architecture": True},
        {"changes_factual_content": True},
        {"overrides_voice": True},
        {"overrides_audience": True},
        {"overrides_persona_or_philosophy": True},
        {"implements_learning": True},
    ),
)
def test_profile_guidance_cannot_cross_fixed_boundaries(change: dict[str, object]):
    assessment = _assessment(profile_guidance=(_guidance(**change),))
    with pytest.raises(CommunicationValidationError):
        validate_communication_assessment(
            assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, _story_plan()
        )


def test_assessment_preserves_story_architecture_identity_and_fingerprint():
    assessment = _assessment()
    assert (
        validate_communication_assessment(
            assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, _story_plan()
        )
        is assessment
    )
    for update in (
        {"story_architecture_id": "wrong"},
        {"story_plan_fingerprint": "0" * 64},
        {"modifies_story_architecture": True},
        {"modifies_upstream_contracts": True},
    ):
        with pytest.raises(CommunicationValidationError):
            validate_communication_assessment(
                assessment.model_copy(update=update),
                DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
                _story_plan(),
            )


@pytest.mark.parametrize(
    "field",
    (
        "contains_generated_language",
        "contains_generated_dialogue",
        "contains_generated_transition",
        "contains_generated_joke",
        "contains_generated_hook",
        "contains_generated_punchline",
        "contains_language_specific_behavior",
        "contains_teleprompter_formatting",
    ),
)
def test_assessment_rejects_generation_language_rules_and_formatting(field: str):
    with pytest.raises(CommunicationValidationError):
        validate_communication_assessment(
            _assessment(**{field: True}),
            DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
            _story_plan(),
        )


def test_readiness_is_derived_for_clean_advisory_review_and_blocked_assessments():
    cases = (
        _assessment(),
        _assessment(
            risks=(_risk(),), readiness=CommunicationReadiness.READY_WITH_ADVISORIES
        ),
        _assessment(
            risks=(_risk(requires_editor_in_chief_review=True),),
            readiness=CommunicationReadiness.REQUIRES_EDITOR_REVIEW,
        ),
        _assessment(
            risks=(_risk(severity=CommunicationRiskSeverity.CRITICAL, blocking=True),),
            readiness=CommunicationReadiness.BLOCKED,
        ),
    )
    for assessment in cases:
        assert (
            validate_communication_assessment(
                assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, _story_plan()
            )
            is assessment
        )
    with pytest.raises(CommunicationValidationError, match="readiness"):
        validate_communication_assessment(
            cases[-1].model_copy(update={"readiness": CommunicationReadiness.READY}),
            DEFAULT_SPOKEN_COMMUNICATION_ENGINE,
            _story_plan(),
        )


def test_duplicate_risk_and_guidance_identifiers_are_rejected():
    for assessment in (
        _assessment(risks=(_risk(), _risk())),
        _assessment(profile_guidance=(_guidance(), _guidance())),
    ):
        with pytest.raises(CommunicationValidationError, match="duplicate"):
            validate_communication_assessment(
                assessment, DEFAULT_SPOKEN_COMMUNICATION_ENGINE, _story_plan()
            )


def test_every_renderer_is_deterministic_utf8_and_policy_only():
    engine = DEFAULT_SPOKEN_COMMUNICATION_ENGINE
    renderers = (
        lambda: render_spoken_communication_engine(engine),
        lambda: render_working_memory(engine),
        lambda: render_communication_flow(engine.communication_flow),
        lambda: render_rhythm(engine),
        lambda: render_attention(engine),
        lambda: render_orientation(engine),
        lambda: render_continuity(engine),
        lambda: render_transitions(engine),
        lambda: render_pauses(engine),
        lambda: render_emotion_timing(engine),
        lambda: render_teleprompter_cognition(engine),
        lambda: render_communication_assessment(_assessment(), engine, _story_plan()),
    )
    for renderer in renderers:
        first = renderer()
        assert first == renderer()
        first.encode("utf-8")
        assert "timestamp" not in first.lower()
    canonical = render_spoken_communication_engine(engine)
    assert "Canonical Principles" in canonical
    assert "Editor-in-Chief Authority" in canonical
    assert "Fixed Boundaries" in canonical


def test_semantic_fingerprints_are_deterministic_and_meaning_sensitive():
    engine = DEFAULT_SPOKEN_COMMUNICATION_ENGINE
    assert communication_engine_fingerprint(engine) == communication_engine_fingerprint(
        engine.model_copy(deep=True)
    )
    changed = engine.model_copy(
        update={
            "working_memory": engine.working_memory.model_copy(
                update={"concept_capacity": engine.working_memory.concept_capacity + 1}
            )
        }
    )
    assert communication_engine_fingerprint(engine) != communication_engine_fingerprint(
        changed
    )
    assert working_memory_fingerprint(
        engine.working_memory
    ) != working_memory_fingerprint(changed.working_memory)
    assert communication_assessment_fingerprint(
        _assessment()
    ) == communication_assessment_fingerprint(_assessment().model_copy(deep=True))


def test_unordered_risk_and_guidance_fingerprints_are_normalized():
    risk_two = _risk(risk_id="communication-risk-2")
    guidance_two = _guidance(guidance_id="communication-guidance-2")
    assert communication_risk_collection_fingerprint(
        (_risk(), risk_two)
    ) == communication_risk_collection_fingerprint((risk_two, _risk()))
    assert communication_profile_guidance_fingerprint(
        (_guidance(), guidance_two)
    ) == communication_profile_guidance_fingerprint((guidance_two, _guidance()))


def test_package_has_no_ai_network_persistence_cli_or_language_specific_dependency():
    from pastila_scout.editor import communication

    modules = " ".join(
        getattr(getattr(communication, name), "__module__", "")
        for name in communication.__all__
    )
    source = " ".join(
        inspect.getsource(getattr(communication, name))
        for name in communication.__all__
        if inspect.isfunction(getattr(communication, name))
    ).lower()
    for forbidden in ("openai", "httpx", "sqlite", "requests", "cli"):
        assert forbidden not in modules
    assert "romanian-specific" not in source
    assert "english-specific" not in source
