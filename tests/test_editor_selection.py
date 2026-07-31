"""Focused tests for the deterministic Milestone 6C.1 selection engine."""

import json
from pathlib import Path

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import assign_scout_input_identity
from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
)
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor import SelectionEngine


def public_input(
    specs: list[dict[str, object]],
) -> ScoutEditorInputV1:
    template = sample_scout_input().ranked_events[0].model_dump(mode="json")
    events: list[dict[str, object]] = []
    for rank, spec in enumerate(specs, start=1):
        event = json.loads(json.dumps(template))
        event_id = int(spec.get("event_id", rank))
        event.update(
            {
                "rank": rank,
                "score_rank": int(spec.get("score_rank", rank)),
                "event_id": event_id,
                "canonical_title": f"Evenimentul {event_id}",
                "canonical_summary": f"Rezumatul confirmat {event_id}.",
                "categories": spec.get("categories", ["Diverse"]),
                "final_score": float(spec.get("score", 70 - rank)),
                "recommendation": spec.get("recommendation", "POSSIBLE_PICK"),
                "source_count": 1,
                "article_count": 1,
                "provenance_truncated": False,
            }
        )
        source_id = str(spec.get("source_id", f"source-{event_id}"))
        event["source_provenance"] = [
            {
                "source_id": source_id,
                "source_name": f"Sursa {source_id}",
                "url": f"https://example.ro/{event_id}",
                "title": f"Articolul {event_id}",
                "published_at": spec.get(
                    "published_at", f"2026-07-{20 + rank:02d}T10:00:00Z"
                ),
            }
        ]
        ai = event["ai_editorial_score"]
        if ai is not None:
            dimensions = ai["dimensions"]
            dimensions.update(spec.get("dimensions", {}))
        events.append(event)
    data = sample_scout_input().model_dump(mode="python")
    data["event_counts"] = {
        "eligible": len(events),
        "processed": len(events),
        "reported": len(events),
    }
    data["ranked_events"] = events
    return assign_scout_input_identity(data)


def profile(
    *,
    target: int,
    backups: int = 0,
    category_constraints: dict[str, dict[str, object]] | None = None,
    maximum_per_category: int | None = None,
    minimum_source_diversity: int = 1,
) -> SelectionProfileV1:
    data = sample_selection_profile().model_dump(mode="json")
    data.update(
        {
            "target_story_count": target,
            "backup_count": backups,
            "category_constraints": category_constraints or {},
            "maximum_stories_from_one_category": maximum_per_category or target,
            "minimum_source_diversity": minimum_source_diversity,
        }
    )
    return SelectionProfileV1.model_validate_json(json.dumps(data))


def context(
    *,
    target: int,
    runtime: int | None = None,
    mandatory: tuple[int, ...] = (),
    excluded: tuple[int, ...] = (),
) -> EpisodeContextV1:
    data = sample_episode_context().model_dump(mode="json")
    data.update(
        {
            "target_story_count": target,
            "target_runtime": {
                "unit": "seconds",
                "value": runtime if runtime is not None else target * 120,
            },
            "mandatory_event_ids": list(mandatory),
            "excluded_event_ids": list(excluded),
            "avoid_recent_event_ids": [],
        }
    )
    return EpisodeContextV1.model_validate_json(json.dumps(data))


def selected_ids(result: object) -> list[int]:
    proposal = result.output.episode_proposal
    assert proposal is not None
    return [story.event_id for story in proposal.selected_stories]


def test_mandatory_event_wins_score_preference() -> None:
    scout = public_input(
        [
            {"event_id": 1, "score": 95},
            {"event_id": 2, "score": 90},
            {"event_id": 3, "score": 55},
        ]
    )

    result = SelectionEngine().select(
        scout, profile(target=2), context(target=2, mandatory=(3,))
    )

    assert 3 in selected_ids(result)
    assert any(
        item.event_id == 3 and item.reason.code == "mandatory_event"
        for item in result.trace.decisions
    )


def test_excluded_event_is_never_selected_or_used_as_backup() -> None:
    scout = public_input([{"event_id": 1, "score": 99}, {"event_id": 2, "score": 70}])

    result = SelectionEngine().select(
        scout,
        profile(target=1, backups=1),
        context(target=1, excluded=(1,)),
    )

    assert selected_ids(result) == [2]
    assert 1 not in result.trace.backup_event_ids
    assert 1 in result.trace.rejected_event_ids


def test_insufficient_candidates_returns_partial_proposal() -> None:
    scout = public_input([{"event_id": 1}, {"event_id": 2}])

    result = SelectionEngine().select(scout, profile(target=3), context(target=3))

    assert result.output.status == "insufficient_candidates"
    assert len(selected_ids(result)) == 2
    assert result.output.episode_proposal is not None
    assert result.output.episode_proposal.warnings[0].code == "insufficient_candidates"


def test_runtime_overflow_is_an_explicit_preflight_conflict() -> None:
    scout = public_input([{"event_id": 1}, {"event_id": 2}])

    result = SelectionEngine().select(
        scout, profile(target=2), context(target=2, runtime=100)
    )

    assert result.output.status == "invalid_input"
    assert result.output.episode_proposal is None
    assert result.trace.conflicts[0].reason.code == "runtime_overflow"


def test_category_balancing_uses_preference_and_maximum_independently() -> None:
    scout = public_input(
        [
            {"event_id": 1, "score": 95, "categories": ["Politica"]},
            {"event_id": 2, "score": 90, "categories": ["Politica"]},
            {"event_id": 3, "score": 60, "categories": ["Social"]},
        ]
    )
    constraints = {
        "Politica": {
            "minimum": 0,
            "preferred": 1,
            "maximum": 1,
            "minimum_policy": "soft",
            "extensions": {},
        },
        "Social": {
            "minimum": 1,
            "preferred": 1,
            "maximum": 1,
            "minimum_policy": "hard",
            "extensions": {},
        },
    }

    result = SelectionEngine().select(
        scout,
        profile(target=2, category_constraints=constraints, maximum_per_category=1),
        context(target=2),
    )

    assert set(selected_ids(result)) == {1, 3}
    assert 2 in result.trace.rejected_event_ids


def test_backup_generation_maps_each_backup_to_selected_story() -> None:
    scout = public_input(
        [
            {"event_id": 1, "score": 90, "categories": ["Politica"]},
            {"event_id": 2, "score": 80, "categories": ["Social"]},
            {"event_id": 3, "score": 75, "categories": ["Politica"]},
            {"event_id": 4, "score": 70, "categories": ["Social"]},
        ]
    )

    result = SelectionEngine().select(
        scout, profile(target=2, backups=2), context(target=2)
    )
    proposal = result.output.episode_proposal
    assert proposal is not None

    assert len(proposal.backup_stories) == 2
    assert all(
        item.replacement_for in selected_ids(result) for item in proposal.backup_stories
    )
    assert proposal.rejection_summary.backups == 2


def test_baseline_order_flow_runtime_and_confidence_are_deterministic() -> None:
    scout = public_input(
        [
            {
                "event_id": 1,
                "score": 80,
                "categories": ["Politica"],
                "dimensions": {"importance": 10, "public_interest": 10},
            },
            {
                "event_id": 2,
                "score": 90,
                "categories": ["Social"],
                "dimensions": {"importance": 5, "public_interest": 5},
            },
            {
                "event_id": 3,
                "score": 70,
                "categories": ["Diverse"],
                "dimensions": {"absurdity": 10, "satirical_potential": 10},
            },
        ]
    )

    result = SelectionEngine().select(
        scout, profile(target=3), context(target=3, runtime=361)
    )
    proposal = result.output.episode_proposal
    assert proposal is not None

    assert selected_ids(result) == [1, 2, 3]
    assert proposal.episode_flow[0].role == "opening"
    assert proposal.episode_flow[-1].role == "closing"
    assert proposal.episode_flow[-1].expected_transition_type == "hard_cut"
    assert proposal.estimated_total_runtime.value == 361
    assert (
        sum(item.suggested_treatment_length.value for item in proposal.selected_stories)
        == 361
    )
    assert all(
        0 <= item.editorial_confidence <= 100 for item in proposal.selected_stories
    )


def test_conflicting_mandatory_category_constraints_are_not_silently_overridden() -> (
    None
):
    scout = public_input(
        [
            {"event_id": 1, "categories": ["Politica"]},
            {"event_id": 2, "categories": ["Politica"]},
        ]
    )
    constraints = {
        "Politica": {
            "minimum": 0,
            "preferred": 1,
            "maximum": 1,
            "minimum_policy": "soft",
            "extensions": {},
        }
    }

    result = SelectionEngine().select(
        scout,
        profile(target=2, category_constraints=constraints, maximum_per_category=1),
        context(target=2, mandatory=(1, 2)),
    )

    assert result.output.status == "invalid_input"
    assert result.output.episode_proposal is None
    assert any(
        conflict.reason.code == "mandatory_category_conflict"
        for conflict in result.trace.conflicts
    )


def test_identical_inputs_produce_byte_identical_outputs_and_traces() -> None:
    scout = public_input([{"event_id": 1}, {"event_id": 2}, {"event_id": 3}])
    selection_profile = profile(target=2, backups=1)
    episode_context = context(target=2)
    engine = SelectionEngine()

    first = engine.select(scout, selection_profile, episode_context)
    second = engine.select(scout, selection_profile, episode_context)

    assert first.output.model_dump_json() == second.output.model_dump_json()
    assert first.trace.model_dump_json() == second.trace.model_dump_json()
    assert first.output.generated_at == scout.generated_at


def test_decision_trace_partitions_candidates_and_records_every_rule() -> None:
    scout = public_input(
        [
            {"event_id": 1, "score": 90},
            {"event_id": 2, "score": 80},
            {"event_id": 3, "score": 70},
        ]
    )
    engine = SelectionEngine()

    result = engine.select(scout, profile(target=1, backups=1), context(target=1))

    partition = (
        set(result.trace.selected_event_ids)
        | set(result.trace.backup_event_ids)
        | set(result.trace.rejected_event_ids)
    )
    assert partition == {1, 2, 3}
    selected_event = result.trace.selected_event_ids[0]
    applied_rules = {
        decision.rule
        for decision in result.trace.decisions
        if decision.event_id == selected_event
    }
    assert {rule.name for rule in engine.rules}.issubset(applied_rules)
    assert "editorial_confidence" in applied_rules


def test_editor_engine_depends_only_on_public_contract_boundary() -> None:
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pastila_scout/editor").glob("*.py")
    )

    assert "pastila_scout.models" not in contents
    assert "pastila_scout.database" not in contents
    assert "pastila_scout.ai" not in contents
    assert "pastila_scout.core" not in contents
