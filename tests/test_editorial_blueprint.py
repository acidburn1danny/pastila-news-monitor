"""Focused tests for the deterministic Milestone 6C.3 blueprint layer."""

import json
from pathlib import Path

from test_editor_selection import context, profile, public_input

from pastila_scout.contracts.editor_output import validate_editor_output_against_input
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import assign_scout_input_identity
from pastila_scout.editor import (
    EditorialBlueprintBuilder,
    EpisodeFlowOptimizer,
    SelectionEngine,
)
from pastila_scout.editor.blueprint_models import (
    EditorialAngle,
    EditorialTheme,
    EmotionalTrajectory,
    NarrativeFunction,
    SegmentIntent,
    TransitionIntent,
)
from pastila_scout.editor.blueprint_rules import (
    EnergyCurveRule,
    SegmentIntentRule,
    TransitionIntentRule,
)


def pipeline(
    specs: list[dict[str, object]],
    *,
    target: int | None = None,
    backups: int = 0,
    mandatory: tuple[int, ...] = (),
    avoid_recent: tuple[int, ...] = (),
    previous_reference: str | None = None,
    theme: str | None = None,
):
    size = target or len(specs)
    scout = public_input(specs)
    selection_profile = profile(target=size, backups=backups)
    episode_context = context(target=size, mandatory=mandatory)
    if avoid_recent or previous_reference is not None or theme is not None:
        data = episode_context.model_dump(mode="json")
        data["avoid_recent_event_ids"] = list(avoid_recent)
        data["previous_episode_reference"] = previous_reference
        data["theme"] = theme
        episode_context = EpisodeContextV1.model_validate_json(json.dumps(data))
    selection = SelectionEngine().select(scout, selection_profile, episode_context)
    flow = EpisodeFlowOptimizer().optimize(
        scout, selection_profile, episode_context, selection
    )
    result = EditorialBlueprintBuilder().build(
        scout, selection_profile, episode_context, flow
    )
    return scout, selection_profile, episode_context, selection, flow, result


def test_episode_theme_uses_category_frequency_and_controlled_order() -> None:
    *_, result = pipeline(
        [
            {"event_id": 1, "categories": ["Social"]},
            {"event_id": 2, "categories": ["Social", "Politica"]},
            {"event_id": 3, "categories": ["Economie"]},
        ],
        theme="campanie-saptamanala",
    )

    assert result.blueprint.thesis.dominant_theme == EditorialTheme.SOCIAL_CONSEQUENCE
    assert (
        result.blueprint.thesis.secondary_theme
        == EditorialTheme.POLITICAL_ACCOUNTABILITY
    )
    assert result.blueprint.thesis.context_theme_reference == "campanie-saptamanala"


def test_every_segment_receives_one_controlled_intent_and_function() -> None:
    *_, result = pipeline([{"event_id": 1}, {"event_id": 2}, {"event_id": 3}])

    assert result.blueprint.segments[0].intent == SegmentIntent.ESTABLISH_CONTEXT
    assert result.blueprint.segments[0].narrative_function == NarrativeFunction.OPENER
    assert result.blueprint.segments[-1].intent in {
        SegmentIntent.CLOSE_WITH_ABSURDITY,
        SegmentIntent.CLOSE_WITH_REFLECTION,
    }
    assert result.blueprint.segments[-1].narrative_function == NarrativeFunction.CLOSER


def test_editorial_angles_derive_only_from_categories_and_public_dimensions() -> None:
    *_, result = pipeline(
        [
            {
                "event_id": 1,
                "categories": ["Politica", "Economie"],
                "dimensions": {"absurdity": 9},
            }
        ]
    )
    angles = result.blueprint.segments[0].angles

    assert angles == (
        EditorialAngle.ACCOUNTABILITY,
        EditorialAngle.POLITICAL_CONTRADICTION,
        EditorialAngle.ECONOMIC_PRESSURE,
    )


def test_opening_blueprint_uses_codes_references_and_prohibited_framing() -> None:
    *_, result = pipeline([{"event_id": 1, "categories": ["Politica"]}], mandatory=(1,))
    opening = result.blueprint.opening
    assert opening is not None

    assert opening.event_id == 1
    assert opening.opener_function == "mandatory_anchor"
    assert opening.primary_audience_question == "who_is_accountable"
    assert "canonical_summary" in opening.facts_to_establish
    assert "invented_quote" in opening.prohibited_framing


def test_absurd_closer_uses_controlled_closing_blueprint_without_punchline() -> None:
    *_, result = pipeline(
        [
            {"event_id": 1, "score": 90},
            {
                "event_id": 2,
                "score": 65,
                "dimensions": {"absurdity": 10, "satirical_potential": 10},
            },
        ]
    )
    closing = result.blueprint.closing
    assert closing is not None

    assert closing.event_id == result.blueprint.flow_order[-1]
    assert closing.closing_mode == "absurdity"
    assert closing.final_satirical_effect == "absurd_resolution"


def test_energy_and_tension_levels_follow_documented_public_dimension_formula() -> None:
    event = public_input(
        [
            {
                "event_id": 1,
                "dimensions": {
                    "importance": 10,
                    "public_interest": 10,
                    "virality": 8,
                    "satirical_potential": 6,
                    "absurdity": 2,
                    "emotional_impact": 5,
                },
            }
        ]
    ).ranked_events[0]

    levels = EnergyCurveRule().assign(event)

    assert levels.tension_level == 5
    assert levels.energy_level == 4
    assert levels.satire_level == 2
    assert levels.emotional_weight == 4


def test_comic_relief_curve_and_transition_intent_are_controlled() -> None:
    *_, result = pipeline(
        [
            {
                "event_id": 1,
                "dimensions": {
                    "importance": 10,
                    "public_interest": 10,
                    "absurdity": 1,
                },
            },
            {
                "event_id": 2,
                "dimensions": {"absurdity": 10, "satirical_potential": 10},
            },
        ]
    )

    assert (
        result.blueprint.thesis.emotional_trajectory
        == EmotionalTrajectory.GRAVE_TO_RELIEF
    )
    assert result.blueprint.transitions[0].intent == TransitionIntent.RELEASE_TENSION


def test_grave_episode_does_not_force_comic_relief() -> None:
    *_, result = pipeline(
        [
            {
                "event_id": 1,
                "dimensions": {
                    "importance": 10,
                    "public_interest": 10,
                    "absurdity": 1,
                    "satirical_potential": 1,
                },
            },
            {
                "event_id": 2,
                "dimensions": {
                    "importance": 9,
                    "public_interest": 9,
                    "absurdity": 1,
                    "satirical_potential": 1,
                },
            },
        ]
    )

    assert (
        result.blueprint.thesis.emotional_trajectory == EmotionalTrajectory.STEADY_GRAVE
    )
    assert result.blueprint.closing.closing_mode != "absurdity"
    assert all(
        transition.intent != TransitionIntent.RELEASE_TENSION
        for transition in result.blueprint.transitions
    )


def test_transition_intent_mapping_is_deterministic() -> None:
    rule = TransitionIntentRule()

    assert rule.assign("continuation", enters_closer=False) == "preserve_topic"
    assert rule.assign("contrast", enters_closer=False) == "sharpen_contrast"
    assert rule.assign("escalation", enters_closer=False) == "raise_stakes"
    assert rule.assign("hard_cut", enters_closer=False) == "reset_energy"
    assert rule.assign("comic_relief", enters_closer=False) == "release_tension"
    assert rule.assign("callback", enters_closer=False) == "callback_to_previous"


def test_callback_and_previous_episode_continuity_are_copied_not_inferred() -> None:
    *_, result = pipeline(
        [
            {"event_id": 1, "score": 90},
            {"event_id": 2, "score": 80},
            {"event_id": 3, "score": 70},
        ],
        avoid_recent=(3,),
        previous_reference="episode-previous",
    )

    assert result.blueprint.continuity.previous_episode_reference == "episode-previous"
    assert result.blueprint.continuity.recent_event_ids_present == (3,)
    callback_transitions = [
        item
        for item in result.blueprint.transitions
        if item.intent == TransitionIntent.CALLBACK_TO_PREVIOUS
    ]
    assert result.blueprint.flow_order.index(3) > 0
    assert callback_transitions


def test_evidence_references_exist_exactly_in_public_scout_provenance() -> None:
    scout, *_, result = pipeline([{"event_id": 1}, {"event_id": 2}])
    events = {event.event_id: event for event in scout.ranked_events}

    for segment in result.blueprint.segments:
        expected = {
            (item.source_id, item.url, item.title)
            for item in events[segment.event_id].source_provenance
        }
        actual = {
            (item.source_id, item.url, item.title)
            for item in segment.evidence.provenance
        }
        assert actual == expected


def test_deterministic_only_event_uses_explicit_curve_fallback() -> None:
    scout = public_input([{"event_id": 1, "score": 72}])
    data = scout.model_dump(mode="python")
    event = data["ranked_events"][0]
    event["ai_editorial_score"] = None
    event["score_basis"] = "deterministic_only"
    data["ranking_parameters"]["ai_enabled"] = False
    scout = assign_scout_input_identity(data)
    selection_profile = profile(target=1)
    episode_context = context(target=1)
    selection = SelectionEngine().select(scout, selection_profile, episode_context)
    flow = EpisodeFlowOptimizer().optimize(
        scout, selection_profile, episode_context, selection
    )

    result = EditorialBlueprintBuilder().build(
        scout, selection_profile, episode_context, flow
    )

    assert result.trace.fallbacks[0].reason.code == "deterministic_score_fallback"
    assert result.blueprint.segments[0].levels.tension_level == 4


def test_segment_intent_fallback_is_stable() -> None:
    event = public_input([{"event_id": 1}]).ranked_events[0]
    levels = EnergyCurveRule().assign(event)
    rule = SegmentIntentRule()

    first = rule.assign(
        event,
        position=2,
        count=4,
        public_transition="custom:unknown-safe",
        levels=levels,
    )
    second = rule.assign(
        event,
        position=2,
        count=4,
        public_transition="custom:unknown-safe",
        levels=levels,
    )

    assert first == second == SegmentIntent.BROADEN_SCOPE


def test_identical_inputs_produce_identical_blueprints_and_traces() -> None:
    specs = [{"event_id": 1}, {"event_id": 2}, {"event_id": 3}]
    first = pipeline(specs)[-1]
    second = pipeline(specs)[-1]

    assert first.blueprint.model_dump_json() == second.blueprint.model_dump_json()
    assert first.trace.model_dump_json() == second.trace.model_dump_json()
    assert first.output.model_dump_json() == second.output.model_dump_json()


def test_blueprint_order_and_trace_are_complete_and_stable() -> None:
    *_, result = pipeline([{"event_id": 3}, {"event_id": 1}, {"event_id": 2}])

    assert result.blueprint.flow_order == tuple(
        segment.event_id for segment in result.blueprint.segments
    )
    assert result.trace.input_flow_order == result.blueprint.flow_order
    assert len(result.trace.segment_intent_decisions) == 3
    assert len(result.trace.angle_decisions) == 3
    assert len(result.trace.curve_decisions) == 3
    assert len(result.trace.evidence_decisions) == 3
    assert not result.trace.conflicts


def test_full_pipeline_keeps_public_output_valid_and_unchanged() -> None:
    scout, selection_profile, episode_context, _, flow, result = pipeline(
        [{"event_id": 1}, {"event_id": 2}, {"event_id": 3}],
        target=2,
        backups=1,
    )

    assert result.output.model_dump_json() == flow.output.model_dump_json()
    validate_editor_output_against_input(
        result.output,
        scout,
        selection_profile=selection_profile,
        episode_context=episode_context,
    )
    assert len(result.blueprint.segments) == 2


def test_blueprint_layer_is_architecturally_isolated() -> None:
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pastila_scout/editor").glob("blueprint_*.py")
    )

    assert "pastila_scout.models" not in contents
    assert "pastila_scout.database" not in contents
    assert "pastila_scout.ai" not in contents
    assert "pastila_scout.core" not in contents
