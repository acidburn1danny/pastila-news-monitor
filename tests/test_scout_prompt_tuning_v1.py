from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.ai.editorial_scoring import EDITORIAL_SCORING_INSTRUCTIONS
from pastila_scout.scout_prompt_tuning_v1 import (
    TuningActualV1,
    TuningProviderOutputV1,
    build_tuning_prompt,
    evaluate_tuning_run,
    load_tuning_dataset,
    run_tuning,
    save_tuning_result,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "tests/fixtures/scout_prompt_tuning_v1.json"


def _actual(dataset, **changes):
    return TuningProviderOutputV1(
        cases=tuple(
            TuningActualV1(
                id=case.id,
                relevant=changes.get(case.id, {}).get("relevant", case.expected.relevant),
                category=changes.get(case.id, {}).get("category", case.expected.category),
                priority=changes.get(case.id, {}).get("priority", case.expected.priority),
                duplicate_group=changes.get(case.id, {}).get(
                    "duplicate_group", case.expected.duplicate_group
                ),
            )
            for case in dataset.cases
        )
    )


def test_representative_dataset_is_small_valid_and_balanced() -> None:
    dataset = load_tuning_dataset(DATASET)
    assert len(dataset.cases) == 24
    assert {item.expected.relevant for item in dataset.cases} == {True, False}
    assert {item.expected.priority for item in dataset.cases} == {
        "high",
        "medium",
        "low",
    }
    groups = [item.expected.duplicate_group for item in dataset.cases]
    assert groups.count("fiscal-1") == groups.count("quake-1") == 2


def test_dataset_rejects_duplicate_ids_and_invalid_priority(tmp_path: Path) -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["cases"][1]["id"] = payload["cases"][0]["id"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_tuning_dataset(path)
    payload["cases"][1]["id"] = "case-002"
    payload["cases"][1]["expected"]["priority"] = "urgent"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_tuning_dataset(path)


def test_metrics_classify_fp_fn_category_duplicate_and_priority() -> None:
    dataset = load_tuning_dataset(DATASET)
    actual = _actual(
        dataset,
        **{
            "case-001": {"relevant": False, "priority": "medium"},
            "case-009": {"relevant": True, "category": "Diverse"},
            "case-013": {"duplicate_group": None},
        },
    )
    metrics = evaluate_tuning_run(dataset, actual)
    assert metrics["false_negatives"] == ["case-001"]
    assert metrics["false_positives"] == ["case-009"]
    assert metrics["relevance"] == {"correct": 22, "total": 24}
    assert metrics["category"] == {"correct": 23, "total": 24}
    assert metrics["duplicate"] == {"correct": 22, "total": 24}
    assert metrics["priority"] == {"correct": 23, "total": 24}


def test_prompt_reuses_production_instruction_and_identity_changes_by_variant() -> None:
    dataset = load_tuning_dataset(DATASET)
    current = build_tuning_prompt(dataset)
    candidate = build_tuning_prompt(
        dataset, variant="candidate-a", override="Penalizează clickbait-ul fără fapte."
    )
    assert current.startswith(EDITORIAL_SCORING_INSTRUCTIONS)
    assert current != candidate
    assert '"case-001"' in current
    assert "Politica, Social, Conspiratii, Economie, CanCan, Externe, Diverse" in current
    assert "even when relevant is false" in current
    assert "Use Politica for government/law/public contracts" in current


def test_run_is_ollama_identified_serializable_and_never_calls_openai(tmp_path: Path) -> None:
    dataset = load_tuning_dataset(DATASET)
    calls = []

    def ollama_only(prompt: str) -> str:
        calls.append(prompt)
        return _actual(dataset).model_dump_json()

    result = run_tuning(
        dataset=dataset,
        model="qwen3:8b",
        base_url="http://localhost:11434",
        timeout=30.0,
        execute=ollama_only,
        now=lambda: datetime(2026, 8, 13, 12, tzinfo=UTC),
    )
    assert len(calls) == 1
    assert result["provider"] == "ollama"
    assert result["model"] == "qwen3:8b"
    assert result["metrics"]["relevance"] == {"correct": 24, "total": 24}
    assert len(result["prompt_sha256"]) == len(result["dataset_sha256"]) == 64
    output = tmp_path / "result.json"
    save_tuning_result(output, result)
    assert json.loads(output.read_text(encoding="utf-8"))["provider"] == "ollama"


def test_result_requires_exact_case_identity() -> None:
    dataset = load_tuning_dataset(DATASET)
    actual = _actual(dataset)
    shortened = TuningProviderOutputV1(cases=actual.cases[:-1])
    with pytest.raises(ValueError, match="identity"):
        evaluate_tuning_run(dataset, shortened)
