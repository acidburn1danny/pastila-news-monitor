"""Part 7B.1 append-only provider benchmark history tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.controlled_revision_quality import (
    BenchmarkHistory,
    BenchmarkHistoryEntry,
    BenchmarkHistoryError,
    append_benchmark_history,
    create_benchmark_history,
    load_benchmark_history,
)


def _entry(
    benchmark_id: str = "20260728-143015-openai-gpt-4.1-mini",
    benchmark_date: str = "2026-07-28T14:30:15+03:00",
    **updates,
) -> BenchmarkHistoryEntry:
    values = {
        "benchmark_id": benchmark_id,
        "benchmark_date": benchmark_date,
        "benchmark_version": "controlled-provider-baseline-v1",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_version": "controlled-revision-v1",
        "schema_fingerprint": "a" * 64,
        "pricing_version": "openai-gpt-4-1-mini-2026-07-28",
        "scenario_count": 24,
        "category_count": 12,
        "usable_revision_rate": 0.5,
        "editorial_acceptance_rate": 0.6,
        "dto_pass_rate": 0.7,
        "meaning_preservation_rate": 0.8,
        "average_latency_ms": 1000,
        "p95_latency_ms": 1500,
        "average_prompt_tokens": 500,
        "average_completion_tokens": 100,
        "average_reasoning_tokens": None,
        "average_cost_per_scenario": 0.001,
        "average_cost_per_usable_revision": 0.002,
        "total_benchmark_cost": 0.024,
        "provider_requests": 24,
        "retry_count": 0,
        "fallback_count": 0,
        "root_conclusion": "CONTROLLED_PROVIDER_BASELINE_COMPLETE",
    }
    values.update(updates)
    return BenchmarkHistoryEntry.model_validate(values)


def test_empty_history_creation_is_versioned_and_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    first = create_benchmark_history(path)
    original = path.read_bytes()
    second = create_benchmark_history(path)
    assert first == second == BenchmarkHistory(schema_version=1, history=())
    assert path.read_bytes() == original
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "history": [],
        "schema_version": 1,
    }


def test_append_preserves_previous_entry_exactly(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    first = _entry()
    second = _entry(
        "20260729-143015-openai-gpt-4.1-mini",
        "2026-07-29T14:30:15+03:00",
    )
    after_first = append_benchmark_history(path, first)
    frozen_previous = after_first.history[0].model_dump_json()
    after_second = append_benchmark_history(path, second)
    assert len(after_second.history) == 2
    assert after_second.history[0].model_dump_json() == frozen_previous
    assert load_benchmark_history(path) == after_second


def test_duplicate_benchmark_id_is_rejected_without_write(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    entry = _entry()
    append_benchmark_history(path, entry)
    original = path.read_bytes()
    with pytest.raises(BenchmarkHistoryError, match="duplicate"):
        append_benchmark_history(path, entry)
    assert path.read_bytes() == original


def test_out_of_order_date_is_rejected_without_write(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_benchmark_history(
        path,
        _entry(
            "20260729-143015-openai-gpt-4.1-mini",
            "2026-07-29T14:30:15+03:00",
        ),
    )
    original = path.read_bytes()
    with pytest.raises(BenchmarkHistoryError, match="ordering"):
        append_benchmark_history(path, _entry())
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "update",
    [
        {"benchmark_id": "invalid"},
        {"benchmark_date": "2026-07-28"},
        {"schema_fingerprint": "short"},
        {"usable_revision_rate": 1.1},
        {"provider_requests": -1},
    ],
)
def test_entry_schema_validation_rejects_invalid_values(update) -> None:
    with pytest.raises(ValidationError):
        _entry(**update)


def test_invalid_root_and_duplicate_loaded_entries_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    entry = _entry().model_dump(mode="json")
    path.write_text(
        json.dumps({"schema_version": 1, "history": [entry, entry]}),
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkHistoryError, match="invalid"):
        load_benchmark_history(path)


def test_additive_unknown_fields_remain_readable_and_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    entry = _entry(future_metric=7)
    history = BenchmarkHistory.model_validate(
        {"schema_version": 1, "history": [entry], "future_root": "bounded"}
    )
    path.write_text(history.model_dump_json(), encoding="utf-8")
    loaded = load_benchmark_history(path)
    assert loaded.model_extra == {"future_root": "bounded"}
    assert loaded.history[0].model_extra == {"future_metric": 7}


def test_history_and_entries_are_immutable() -> None:
    entry = _entry()
    history = BenchmarkHistory(history=(entry,))
    with pytest.raises(ValidationError):
        entry.model = "changed"
    with pytest.raises(ValidationError):
        history.history = ()


def test_checked_in_history_preserves_prior_baselines_and_appends_experiment() -> None:
    path = Path("docs/artifacts/controlled-provider-quality-history.json")
    history = load_benchmark_history(path)
    assert history.schema_version == 1
    assert len(history.history) == 5
    entry = history.history[0]
    assert entry.benchmark_id == "20260728-092119-openai-gpt-4.1-mini"
    assert entry.scenario_count == 24
    assert entry.category_count == 12
    assert entry.provider_requests == 24
    assert entry.retry_count == 0
    assert entry.fallback_count == 0
    assert entry.root_conclusion == "INSUFFICIENT_SAMPLE"
    v2 = history.history[1]
    assert v2.benchmark_id == "20260728-102323-openai-gpt-4.1-mini-v2"
    assert v2.scenario_count == 24
    assert v2.category_count == 12
    assert v2.provider_requests == 24
    assert v2.retry_count == 0
    assert v2.fallback_count == 0
    assert v2.root_conclusion == "PROVIDER_REFERENCE_CONTRACT_FAILURE"
    part_7c2 = history.history[2]
    assert part_7c2.benchmark_id == "20260728-120420-openai-gpt-4.1-mini-7c2"
    assert part_7c2.provider_requests == 24
    assert part_7c2.retry_count == 0
    assert part_7c2.fallback_count == 0
    assert part_7c2.root_conclusion == "REFERENCE_CONTRACT_REMEDIATION_EFFECTIVE"
    part_7h = history.history[3]
    assert part_7h.benchmark_id == "20260728-125848-openai-gpt-4.1-mini-7h"
    assert part_7h.provider_requests == 24
    assert part_7h.retry_count == 0
    assert part_7h.fallback_count == 0
    assert part_7h.root_conclusion == (
        "CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION"
    )
    part_7h2 = history.history[4]
    assert part_7h2.benchmark_id == "20260728-144134-openai-gpt-4.1-mini-7h2"
    assert part_7h2.provider_requests == 24
    assert part_7h2.retry_count == 0
    assert part_7h2.fallback_count == 0
    assert part_7h2.root_conclusion == "H2_PROMPT_INEFFECTIVE"
