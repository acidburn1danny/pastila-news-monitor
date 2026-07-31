"""Focused coverage for deterministic Milestone 6C.2 flow optimization."""

import json
from pathlib import Path

from test_editor_selection import context, profile, public_input

from pastila_scout.contracts.editor_output import validate_editor_output_against_input
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.editor import EpisodeFlowOptimizer, SelectionEngine


def optimize(
    specs: list[dict[str, object]],
    *,
    target: int | None = None,
    backups: int = 0,
    runtime: int | None = None,
    mandatory: tuple[int, ...] = (),
    avoid_recent: tuple[int, ...] = (),
    previous_reference: str | None = None,
):
    size = target or len(specs)
    scout = public_input(specs)
    selection_profile = profile(target=size, backups=backups)
    episode_context = context(
        target=size,
        runtime=runtime,
        mandatory=mandatory,
    )
    if avoid_recent or previous_reference is not None:
        data = episode_context.model_dump(mode="json")
        data["avoid_recent_event_ids"] = list(avoid_recent)
        data["previous_episode_reference"] = previous_reference
        episode_context = EpisodeContextV1.model_validate_json(json.dumps(data))
    selection = SelectionEngine().select(scout, selection_profile, episode_context)
    result = EpisodeFlowOptimizer().optimize(
        scout, selection_profile, episode_context, selection
    )
    return scout, selection_profile, episode_context, selection, result


def proposal(result):
    value = result.output.episode_proposal
    assert value is not None
    return value


def order(result) -> list[int]:
    return [story.event_id for story in proposal(result).selected_stories]


def test_selected_and_backup_sets_and_inherited_values_remain_unchanged() -> None:
    scout, _, _, selection, result = optimize(
        [
            {"event_id": 1, "score": 90},
            {"event_id": 2, "score": 80},
            {"event_id": 3, "score": 70},
            {"event_id": 4, "score": 60},
        ],
        target=2,
        backups=2,
    )
    before = proposal(selection)
    after = proposal(result)

    assert {item.event_id for item in before.selected_stories} == {
        item.event_id for item in after.selected_stories
    }
    assert {item.event_id for item in before.backup_stories} == {
        item.event_id for item in after.backup_stories
    }
    source = {event.event_id: event for event in scout.ranked_events}
    for story in after.selected_stories:
        assert story.canonical_title == source[story.event_id].canonical_title
        assert (
            story.inherited_scout_scores.final_score
            == source[story.event_id].final_score
        )
        assert story.source_references == source[story.event_id].source_provenance


def test_strong_non_political_story_can_open() -> None:
    _, _, _, _, result = optimize(
        [
            {
                "event_id": 1,
                "score": 96,
                "categories": ["Politica"],
                "dimensions": {"importance": 3, "public_interest": 3},
            },
            {
                "event_id": 2,
                "score": 90,
                "categories": ["Social"],
                "dimensions": {"importance": 10, "public_interest": 10},
            },
            {"event_id": 3, "score": 75, "categories": ["Diverse"]},
        ]
    )

    assert order(result)[0] == 2
    assert result.trace.opening_decision.event_ids == (2,)


def test_political_story_opens_when_objectively_strongest() -> None:
    _, _, _, _, result = optimize(
        [
            {
                "event_id": 1,
                "score": 95,
                "categories": ["Politica"],
                "dimensions": {"importance": 10, "public_interest": 10},
            },
            {
                "event_id": 2,
                "score": 90,
                "categories": ["Social"],
                "dimensions": {"importance": 6, "public_interest": 6},
            },
        ]
    )

    assert order(result)[0] == 1


def test_category_repetition_is_avoided_when_an_alternative_exists() -> None:
    _, _, _, _, result = optimize(
        [
            {"event_id": 1, "score": 90, "categories": ["Politica"]},
            {"event_id": 2, "score": 80, "categories": ["Politica"]},
            {"event_id": 3, "score": 70, "categories": ["Social"]},
        ]
    )
    optimized_order = order(result)

    assert abs(optimized_order.index(1) - optimized_order.index(2)) > 1


def test_same_category_continuation_is_justified_and_typed() -> None:
    _, _, _, _, result = optimize(
        [
            {"event_id": 1, "score": 85, "categories": ["Economie"]},
            {"event_id": 2, "score": 80, "categories": ["Economie"]},
        ]
    )

    assert proposal(result).episode_flow[1].expected_transition_type == "continuation"
    assert result.trace.adjacency_decisions[0].reason.code == "category_continuation"


def test_grave_to_absurd_story_uses_comic_relief() -> None:
    _, _, _, _, result = optimize(
        [
            {
                "event_id": 1,
                "score": 90,
                "dimensions": {
                    "importance": 10,
                    "public_interest": 10,
                    "absurdity": 1,
                },
            },
            {
                "event_id": 2,
                "score": 65,
                "dimensions": {"absurdity": 10, "satirical_potential": 10},
            },
        ]
    )

    assert order(result) == [1, 2]
    assert proposal(result).episode_flow[1].expected_transition_type == "comic_relief"


def test_score_cliff_requires_an_explicit_transition() -> None:
    _, _, _, _, result = optimize(
        [
            {
                "event_id": 1,
                "score": 99,
                "dimensions": {"importance": 10, "public_interest": 10},
            },
            {
                "event_id": 2,
                "score": 55,
            },
            {
                "event_id": 3,
                "score": 75,
                "dimensions": {"absurdity": 10, "satirical_potential": 10},
            },
            {"event_id": 4, "score": 88},
        ]
    )
    optimized_order = order(result)
    strongest_position = optimized_order.index(1)

    assert optimized_order[strongest_position + 1] != 2


def test_memorable_absurd_story_is_preferred_as_closer() -> None:
    _, _, _, _, result = optimize(
        [
            {"event_id": 1, "score": 95},
            {"event_id": 2, "score": 90},
            {
                "event_id": 3,
                "score": 65,
                "dimensions": {
                    "absurdity": 10,
                    "satirical_potential": 10,
                    "public_interest": 8,
                },
            },
        ]
    )

    assert order(result)[-1] == 3
    assert result.trace.ending_decision.event_ids == (3,)


def test_runtime_allocation_is_weighted_and_exact() -> None:
    _, _, context_value, _, result = optimize(
        [
            {"event_id": 1, "score": 95},
            {"event_id": 2, "score": 80},
            {"event_id": 3, "score": 60},
        ],
        runtime=421,
        mandatory=(2,),
    )
    optimized = proposal(result)

    assert optimized.estimated_total_runtime.value == context_value.target_runtime.value
    assert (
        sum(
            item.suggested_treatment_length.value for item in optimized.selected_stories
        )
        == 421
    )
    assert sum(item.seconds for item in result.trace.runtime_allocations) == 421
    assert all(item.seconds >= 60 for item in result.trace.runtime_allocations)


def test_impossible_runtime_returns_explicit_conflict_without_dropping_stories() -> (
    None
):
    scout = public_input([{"event_id": 1}, {"event_id": 2}])
    selection_profile = profile(target=2)
    valid_context = context(target=2, runtime=240)
    selection = SelectionEngine().select(scout, selection_profile, valid_context)
    impossible_context = context(target=2, runtime=100)

    result = EpisodeFlowOptimizer().optimize(
        scout, selection_profile, impossible_context, selection
    )

    assert result.output.status == "invalid_input"
    assert (
        result.trace.hard_constraint_failures[0].reason.code
        == "flow_runtime_impossible"
    )
    assert {item.event_id for item in proposal(result).selected_stories} == {1, 2}


def test_previous_episode_event_is_kept_away_from_opening_when_unavoidable() -> None:
    _, _, _, _, result = optimize(
        [
            {"event_id": 1, "score": 90},
            {"event_id": 2, "score": 85},
            {"event_id": 3, "score": 80},
        ],
        avoid_recent=(1,),
        previous_reference="episode-previous",
    )

    assert order(result)[0] != 1


def test_identical_inputs_are_reproducible_with_stable_ties() -> None:
    specs = [
        {"event_id": 1, "score": 80},
        {"event_id": 2, "score": 80},
        {"event_id": 3, "score": 80},
    ]
    first = optimize(specs)[-1]
    second = optimize(specs)[-1]

    assert first.output.model_dump_json() == second.output.model_dump_json()
    assert first.trace.model_dump_json() == second.trace.model_dump_json()
    assert order(first) == order(second)


def test_trace_contains_objectives_alternatives_adjacencies_and_runtime() -> None:
    _, _, _, _, result = optimize([{"event_id": 1}, {"event_id": 2}, {"event_id": 3}])

    assert result.trace.evaluated_candidate_count > 0
    assert result.trace.summarized_alternatives
    assert result.trace.winning_objective is not None
    assert len(result.trace.adjacency_decisions) == 2
    assert len(result.trace.runtime_allocations) == 3
    assert {item.rule for item in result.trace.applied_rules} >= {
        "opening_strength",
        "ending_strength",
        "category_rhythm",
        "score_cliff",
    }


def test_full_contract_pipeline_passes_cross_document_validation() -> None:
    scout, selection_profile, episode_context, _, result = optimize(
        [
            {"event_id": 1, "score": 90},
            {"event_id": 2, "score": 80},
            {"event_id": 3, "score": 70},
        ],
        target=2,
        backups=1,
    )

    validate_editor_output_against_input(
        result.output,
        scout,
        selection_profile=selection_profile,
        episode_context=episode_context,
    )


def test_flow_layer_is_architecturally_isolated() -> None:
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pastila_scout/editor").glob("flow_*.py")
    )

    assert "pastila_scout.models" not in contents
    assert "pastila_scout.database" not in contents
    assert "pastila_scout.ai" not in contents
    assert "pastila_scout.core" not in contents
