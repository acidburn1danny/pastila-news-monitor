"""Editorial knowledge evolution lifecycle, history, and validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.controlled_revision_quality.knowledge_evolution import (
    EntryHistory,
    EvolutionTrigger,
    KnowledgeEvolutionHistory,
    LifecycleState,
    deserialize_history,
    evolution_history_fingerprint,
    next_state,
    serialize_history,
    statistics,
    validate_evolution_history,
)
from scripts.build_knowledge_evolution import (
    HISTORY_PATH,
    STATISTICS_PATH,
    TIMELINE_PATH,
    build_evolution_history,
    build_timeline,
)

ROOT = Path.cwd()


def _history() -> KnowledgeEvolutionHistory:
    return build_evolution_history(ROOT)


def test_supported_lifecycle_transitions_are_deterministic():
    assert (
        next_state(LifecycleState.PROPOSED, EvolutionTrigger.STATUS_TRANSITION)
        == LifecycleState.ACTIVE
    )
    assert (
        next_state(LifecycleState.ACTIVE, EvolutionTrigger.EXPERIMENT_CONFIRMED)
        == LifecycleState.SUPPORTED
    )
    assert (
        next_state(LifecycleState.REFINED, EvolutionTrigger.EXPERIMENT_CONFIRMED)
        == LifecycleState.SUPPORTED
    )
    assert (
        next_state(LifecycleState.ACTIVE, EvolutionTrigger.EXPERIMENT_REFINED)
        == LifecycleState.REFINED
    )


def test_invalid_lifecycle_transition_is_rejected():
    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        next_state(LifecycleState.INVALIDATED, EvolutionTrigger.EXPERIMENT_CONFIRMED)


def test_all_current_knowledge_entries_are_backfilled():
    history = _history()

    assert len(history.histories) == 8
    assert {item.knowledge_id for item in history.histories} == {
        f"EK-{number:03d}" for number in range(1, 9)
    }
    assert all(
        item.events[0].previous_state.status == LifecycleState.PROPOSED
        for item in history.histories
    )
    assert all(
        item.events[0].new_state.status == LifecycleState.ACTIVE
        for item in history.histories
    )


def test_ek002_records_explicit_h3_refinement_without_entry_rewrite():
    history = _history()
    ek002 = next(item for item in history.histories if item.knowledge_id == "EK-002")

    assert len(ek002.events) == 2
    assert ek002.current_state.status == LifecycleState.REFINED
    assert ek002.refinements == 1
    assert ek002.events[-1].trigger == EvolutionTrigger.EXPERIMENT_REFINED
    assert ek002.events[-1].supporting_experiments == (
        "20260728-161607-openai-gpt-4.1-mini-7h4",
    )
    assert ek002.entry_version == 1


def test_other_entries_remain_active_without_fabricated_confirmation():
    history = _history()
    others = [item for item in history.histories if item.knowledge_id != "EK-002"]

    assert all(item.current_state.status == LifecycleState.ACTIVE for item in others)
    assert all(item.confirmations == item.contradictions == 0 for item in others)


def test_evidence_accumulates_monotonically():
    history = _history()

    for item in history.histories:
        counts = [event.new_state.cumulative_evidence_count for event in item.events]
        assert counts == sorted(counts)
        assert counts[0] > 0
    ek002 = next(item for item in history.histories if item.knowledge_id == "EK-002")
    assert (
        ek002.events[1].new_state.cumulative_evidence_count
        > ek002.events[0].new_state.cumulative_evidence_count
    )


def test_confidence_transition_requires_evidence():
    event = _history().histories[0].events[0]
    data = event.model_dump(mode="json")
    data["confidence_after"] = "HIGH"
    data["new_state"]["confidence"] = "HIGH"
    data["supporting_experiments"] = []
    data["trigger"] = "CONFIDENCE_UPDATED"
    with pytest.raises(ValidationError, match="requires experiment evidence"):
        type(event).model_validate(data)


def test_non_creation_event_requires_an_experiment():
    event = _history().histories[0].events[0]
    data = event.model_dump(mode="json")
    data["trigger"] = "EVIDENCE_ADDED"
    data["supporting_experiments"] = []
    with pytest.raises(ValidationError, match="requires supporting experiment"):
        type(event).model_validate(data)


def test_broken_manifest_link_is_reported():
    history = _history()
    entry = history.histories[0]
    event = entry.events[0].model_copy(
        update={"supporting_manifests": ("docs/artifacts/not-present.json",)}
    )
    changed_entry = entry.model_copy(update={"events": (event,)})
    changed_history = history.model_copy(
        update={"histories": (changed_entry, *history.histories[1:])}
    )

    diagnostics = validate_evolution_history(changed_history, ROOT)

    assert not diagnostics.valid
    assert (
        "missing evolution evidence: docs/artifacts/not-present.json"
        in diagnostics.errors
    )


def test_duplicate_evolution_event_is_rejected():
    item = _history().histories[0]
    with pytest.raises(ValidationError, match="duplicate evolution event"):
        EntryHistory.model_validate(
            {**item.model_dump(mode="json"), "events": [item.events[0], item.events[0]]}
        )


def test_version_mismatch_is_rejected():
    event = _history().histories[0].events[0]
    data = event.model_dump(mode="json")
    data["new_state"]["evolution_version"] = 9
    with pytest.raises(ValidationError, match="evolution version mismatch"):
        type(event).model_validate(data)


def test_broken_timeline_ordering_is_rejected():
    item = next(item for item in _history().histories if item.knowledge_id == "EK-002")
    events = [
        item.events[0].model_copy(update={"timestamp": "2099-01-01T00:00:00+00:00"}),
        item.events[1],
    ]
    with pytest.raises(ValidationError, match="broken timeline ordering"):
        EntryHistory.model_validate({**item.model_dump(mode="json"), "events": events})


def test_history_fingerprints_and_evidence_validate():
    history = _history()
    diagnostics = validate_evolution_history(history, ROOT)

    assert diagnostics.valid
    assert diagnostics.histories_validated == 8
    assert diagnostics.events_validated == 9
    assert diagnostics.relationships_validated == 6
    assert diagnostics.artifacts_validated > 0
    assert history.history_fingerprint == evolution_history_fingerprint(history)


def test_history_corruption_is_detected():
    history = _history().model_copy(update={"history_fingerprint": "0" * 64})

    assert not validate_evolution_history(history, ROOT).valid
    assert (
        "evolution history fingerprint mismatch"
        in validate_evolution_history(history, ROOT).errors
    )


def test_relationship_history_backfills_current_relationships():
    history = _history()

    assert len(history.relationship_history) == 6
    assert all(item.action == "ADDED" for item in history.relationship_history)
    assert any(
        item.source_id == "EK-008" and item.target_id == "EK-002"
        for item in history.relationship_history
    )


def test_timeline_is_deterministically_ordered():
    first = build_timeline(_history())
    second = build_timeline(_history())

    assert first == second
    assert first["event_count"] == 15
    keys = [
        (item["timestamp"], item.get("event_id", item.get("relationship_event_id")))
        for item in first["events"]
    ]
    assert keys == sorted(keys)


def test_statistics_reconcile_to_current_states_and_events():
    result = statistics(_history())

    assert result["knowledge_entries"] == 8
    assert result["evolution_events"] == 9
    assert result["relationship_events"] == 6
    assert result["states"]["ACTIVE"] == 7
    assert result["states"]["REFINED"] == 1
    assert result["states"]["SUPPORTED"] == 0
    assert result["confirmation_statistics"]["refinements"] == 1


def test_history_serialization_deserialization_round_trip(tmp_path: Path):
    path = tmp_path / "history.json"
    history = _history()
    serialize_history(path, history)

    assert deserialize_history(path) == history


def test_checked_in_history_timeline_and_statistics_match_builders():
    checked = deserialize_history(HISTORY_PATH)
    expected = _history()
    timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    stats = json.loads(STATISTICS_PATH.read_text(encoding="utf-8"))

    assert checked == expected
    assert timeline == build_timeline(expected)
    assert stats == statistics(expected)


def test_evolution_artifacts_are_offline_and_secret_free():
    text = json.dumps(_history().model_dump(mode="json"), ensure_ascii=False).casefold()

    assert _history().provider_requests == 0
    assert _history().network_calls == 0
    assert _history().benchmark_executions == 0
    assert _history().benchmark_replays == 0
    for forbidden in ("api_key", "access_token", "bearer ", "c:\\users\\"):
        assert forbidden not in text
