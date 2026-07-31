"""Tests for the deterministic Pastila Acida private voice model."""

import inspect
from enum import StrEnum

from test_editorial_blueprint import pipeline

from pastila_scout.contracts.identity import assign_scout_input_identity
from pastila_scout.editor import (
    CommentaryBlueprintBuilder,
    EditorialBlueprintBuilder,
    EpisodeFlowOptimizer,
    SelectionEngine,
    VoiceModelBuilder,
    voice_models,
)
from pastila_scout.editor.voice_models import (
    ConversationRegister,
    DirectLanguageLevel,
    EndingVoice,
    HumorIntensity,
    MechanismType,
    OralityLevel,
    ProtectedDimension,
    RoastEligibility,
    SarcasmIntensity,
)


def voice_pipeline(specs, *, extensions=None):
    scout, profile, context, _, flow, generic = pipeline(specs)
    if extensions:
        data = scout.model_dump(
            mode="json", exclude={"report_id", "content_fingerprint"}
        )
        for event, values in zip(data["ranked_events"], extensions, strict=True):
            event["extensions"] = values
        scout = assign_scout_input_identity(data)
        selection = SelectionEngine().select(scout, profile, context)
        flow = EpisodeFlowOptimizer().optimize(scout, profile, context, selection)
        generic = EditorialBlueprintBuilder().build(scout, profile, context, flow)
    commentary = CommentaryBlueprintBuilder().build(
        scout, profile, context, flow, generic.blueprint
    )
    result = VoiceModelBuilder().build(
        scout,
        profile,
        context,
        flow,
        generic.blueprint,
        commentary.blueprint,
    )
    return scout, flow, generic, commentary, result


def test_default_voice_is_oral_peer_conversation_without_public_mutation() -> None:
    _, flow, _, commentary, result = voice_pipeline([{"event_id": 1}])
    story = result.plan.stories[0]

    assert story.orality.level == OralityLevel.HIGH
    assert story.audience_relationship == "intelligent_peer"
    assert "news_presenter" in story.prohibited_voice_modes
    assert result.output.model_dump(mode="json") == flow.output.model_dump(mode="json")
    assert commentary.output.model_dump(mode="json") == result.output.model_dump(
        mode="json"
    )


def test_sensitive_tragedy_reduces_humor_and_protects_victims() -> None:
    *_, result = voice_pipeline(
        [{"event_id": 1}], extensions=[{"sensitivity": "tragedy"}]
    )
    story = result.plan.stories[0]

    assert story.conversation_register == ConversationRegister.SERIOUS_COMPANION
    assert story.humor_intensity == HumorIntensity.NONE
    assert story.sarcasm_ceiling == SarcasmIntensity.NONE
    assert story.roast_eligibility == RoastEligibility.PROHIBITED
    assert ProtectedDimension.BEREAVEMENT in story.protected_dimensions
    assert story.profanity_ceiling == DirectLanguageLevel.CLEAN
    assert story.ending_voice == EndingVoice.SERIOUS_CONCLUSION


def test_absurd_victim_roast_rule_requires_all_explicit_conditions() -> None:
    *_, allowed = voice_pipeline(
        [{"event_id": 1}],
        extensions=[
            {
                "explicit_absurdity": True,
                "meaningful_agency": True,
                "behavior_is_target": True,
                "severe_harm": False,
            }
        ],
    )
    *_, denied = voice_pipeline(
        [{"event_id": 1}],
        extensions=[{"explicit_absurdity": True, "meaningful_agency": False}],
    )

    assert allowed.plan.stories[0].roast_eligibility == RoastEligibility.BEHAVIOR_ONLY
    assert denied.plan.stories[0].roast_eligibility == RoastEligibility.INSTITUTION_ONLY


def test_expression_callback_vocative_and_repetition_budgets_are_shared() -> None:
    *_, result = voice_pipeline([{"event_id": 1}, {"event_id": 2}, {"event_id": 3}])

    assert result.plan.expression_budget.maximum_total == sum(
        story.romanian_expression.maximum_count for story in result.plan.stories
    )
    assert result.plan.vocative_budget == sum(
        story.vocatives.maximum_per_story for story in result.plan.stories
    )
    assert result.plan.callback_budget == 1
    assert result.plan.stories[-1].callback.target_event_id == result.plan.flow_order[0]
    assert {budget.mechanism for budget in result.plan.anti_repetition.budgets} == set(
        MechanismType
    )


def test_order_trace_and_episode_consistency_are_complete() -> None:
    *_, commentary, result = voice_pipeline(
        [{"event_id": 1}, {"event_id": 2}, {"event_id": 3}]
    )

    assert result.plan.flow_order == commentary.blueprint.flow_order
    assert (
        tuple(story.event_id for story in result.plan.stories) == result.plan.flow_order
    )
    assert result.trace.input_flow_order == result.plan.flow_order
    assert len(result.trace.decisions) == len(result.plan.stories) * 4
    assert "audience_respect" in result.trace.validation_checks
    assert result.plan.audience_respect_invariants


def test_identical_inputs_produce_identical_voice_plan_and_trace() -> None:
    *_, first = voice_pipeline([{"event_id": 1}, {"event_id": 2}])
    *_, second = voice_pipeline([{"event_id": 1}, {"event_id": 2}])

    assert first.plan.model_dump(mode="json") == second.plan.model_dump(mode="json")
    assert first.trace.model_dump(mode="json") == second.trace.model_dump(mode="json")


def test_controlled_vocabulary_members_are_unique_and_nonempty() -> None:
    enum_types = tuple(
        value
        for _, value in inspect.getmembers(voice_models, inspect.isclass)
        if issubclass(value, StrEnum) and value is not StrEnum
    )
    for enum_type in enum_types:
        values = [item.value for item in enum_type]
        assert values and len(values) == len(set(values))
