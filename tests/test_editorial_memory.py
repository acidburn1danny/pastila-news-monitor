"""Tests for deterministic, cumulative Editor-in-Chief verdict learning."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.memory import (
    EditorialMemory,
    VerdictInput,
    load_memory,
    process_verdict,
    save_memory,
)
from pastila_scout.editor.memory.models import SectionScore


def _verdict(episode: str, comment: str, score: float = 8) -> VerdictInput:
    return VerdictInput(
        episode_id=episode,
        timestamp=f"2026-08-{int(episode):02d}T12:00:00+00:00",
        overall_score=score,
        comments=(comment,),
    )


def test_episode_verdict_extracts_positive_and_negative_observations():
    result = process_verdict(
        _verdict(
            "1",
            "Very good episode. Story 3 should be shorter. Excellent ending.",
        )
    )

    assert result.verdict_summary.observations_created == 2
    assert result.verdict_summary.positive_findings == ("Ending: excellent",)
    assert result.verdict_summary.negative_findings == ("Story Structure: negative",)
    assert len(result.memory.observations) == 2


def test_granular_scores_influence_observation_strength():
    verdict = VerdictInput(
        episode_id="1",
        timestamp="2026-08-01T12:00:00+00:00",
        section_scores=(SectionScore(section="Introduction", score=3),),
        comments=("Intro too long.",),
    )

    result = process_verdict(verdict)

    assert result.memory.observations[0].strength == "high"
    assert result.memory.observations[0].affected_section == "Introduction"


def test_neutral_or_unclassified_comment_does_not_create_observation():
    result = process_verdict(_verdict("1", "Episode reviewed yesterday."))

    assert result.verdict_summary.observations_created == 0
    assert result.memory.observations == ()


def test_single_verdict_never_changes_profile():
    result = process_verdict(_verdict("1", "Intro too long."))

    assert result.editorial_profile.current_weaknesses == ()
    assert result.editorial_profile.emerging_trends == ()
    assert result.candidate_findings == ()
    assert result.editorial_profile.profile_version == 1


def test_two_distinct_episodes_create_only_an_emerging_trend():
    first = process_verdict(_verdict("1", "Intro too long."))
    second = process_verdict(_verdict("2", "Intro too long."), first.memory)

    assert second.editorial_profile.current_weaknesses == ()
    assert second.editorial_profile.emerging_trends == ("Introduction: too long",)
    assert second.candidate_findings == ()


def test_three_distinct_episodes_create_profile_preference_and_candidate():
    memory = EditorialMemory()
    for episode in ("1", "2", "3"):
        result = process_verdict(_verdict(episode, "Intro too long."), memory)
        memory = result.memory

    assert result.editorial_profile.current_weaknesses == ("Introduction: too long",)
    assert result.editorial_profile.emerging_trends == ()
    assert result.candidate_findings[0].occurrence_count == 3
    assert result.candidate_findings[0].episode_ids == ("1", "2", "3")
    assert result.candidate_findings[0].recommendation == (
        "possible_editorial_improvement"
    )


def test_repeated_positive_pattern_becomes_a_strength():
    memory = EditorialMemory()
    for episode in ("1", "2", "3"):
        result = process_verdict(_verdict(episode, "Excellent transitions."), memory)
        memory = result.memory

    assert result.editorial_profile.current_strengths == ("Transitions: excellent",)
    assert result.candidate_findings[0].recommendation == "potential_prompt_experiment"


def test_duplicate_verdict_is_idempotent():
    verdict = _verdict("1", "Excellent ending.")
    first = process_verdict(verdict)
    second = process_verdict(verdict, first.memory)

    assert second.memory == first.memory
    assert second.memory_update.observations_added == 0
    assert second.verdict_summary.observations_created == 0


def test_reinforcement_is_reported_for_a_new_episode():
    first = process_verdict(_verdict("1", "Excellent ending."))
    second = process_verdict(_verdict("2", "Excellent ending."), first.memory)

    assert second.memory_update.existing_observations_reinforced == 1


def test_processing_is_deterministic():
    verdict = _verdict("1", "Intro too long. Excellent ending.")

    assert process_verdict(verdict) == process_verdict(verdict)


def test_unicode_memory_round_trip_is_utf8(tmp_path: Path):
    path = tmp_path / "memorie-editorială.json"
    memory = process_verdict(_verdict("1", "Ritmul este prea lent.")).memory

    save_memory(path, memory)

    assert load_memory(path) == memory
    assert "Ritmul este prea lent" in path.read_text(encoding="utf-8")


def test_missing_memory_file_returns_empty_state(tmp_path: Path):
    assert load_memory(tmp_path / "missing.json") == EditorialMemory()


def test_invalid_empty_comment_is_rejected():
    with pytest.raises(ValidationError, match="cannot be empty"):
        VerdictInput(
            episode_id="1",
            timestamp="2026-08-01T12:00:00+00:00",
            comments=("  ",),
        )


def test_memory_has_no_prompt_or_knowledge_base_mutation_surface():
    fields = EditorialMemory.model_fields

    assert "prompt" not in fields
    assert "knowledge_base" not in fields
    assert "benchmark" not in fields
