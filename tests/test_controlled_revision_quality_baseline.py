"""Part 7A deterministic quality baseline tests."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.controlled_revision_quality import (
    BenchmarkMode,
    FailureCategory,
    RevisionBenchmarkRunner,
    ScenarioCategory,
    build_synthetic_corpus,
    evaluate_scenario,
)
from pastila_scout.editor.generation.controlled_revision_quality.evaluators import (
    change_ratio,
    normalized_text,
    preserves_numeric_values,
    preserves_values,
)

SCHEMA_SHA = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"


def test_corpus_has_two_cases_per_required_category() -> None:
    corpus = build_synthetic_corpus()
    assert len(corpus) == 24
    assert Counter(item.category for item in corpus) == {
        category: 2 for category in ScenarioCategory
    }
    for category in ScenarioCategory:
        cases = [item for item in corpus if item.category is category]
        assert any(item.expected_usable for item in cases)
        assert any(
            item.expected_failure_category is not FailureCategory.USABLE_REVISION
            for item in cases
        )


def test_corpus_uses_only_synthetic_property_expectations() -> None:
    serialized = json.dumps(
        [item.model_dump(mode="json") for item in build_synthetic_corpus()],
        ensure_ascii=False,
    )
    assert "http://" not in serialized and "https://" not in serialized
    assert "provider_output" not in serialized
    assert "prompt_body" not in serialized.casefold()


def test_all_scenario_expectations_match_evaluator() -> None:
    evaluations = tuple(evaluate_scenario(item) for item in build_synthetic_corpus())
    assert all(item.consistency_passed for item in evaluations)


def test_each_failure_edge_maps_to_one_bounded_category() -> None:
    results = [evaluate_scenario(item) for item in build_synthetic_corpus()]
    assert all(isinstance(item.failure_category, FailureCategory) for item in results)
    assert (
        sum(
            item.failure_category is FailureCategory.USABLE_REVISION for item in results
        )
        == 12
    )


@pytest.mark.parametrize(
    ("category", "failure"),
    [
        (ScenarioCategory.QUOTE_PRESERVATION, FailureCategory.QUOTE_MUTATION),
        (
            ScenarioCategory.NUMERIC_FACT_PRESERVATION,
            FailureCategory.NUMERIC_FACT_MUTATION,
        ),
        (
            ScenarioCategory.TEMPORAL_FACT_PRESERVATION,
            FailureCategory.TEMPORAL_FACT_MUTATION,
        ),
        (
            ScenarioCategory.PROTECTED_STRUCTURE,
            FailureCategory.PROTECTED_STRUCTURE_MUTATION,
        ),
        (ScenarioCategory.SOURCE_AUTHORITY, FailureCategory.SOURCE_AUTHORITY_DRIFT),
        (ScenarioCategory.NO_CHANGE_REQUIRED, FailureCategory.UNNECESSARY_REWRITE),
    ],
)
def test_required_deterministic_failure_evaluators(category, failure) -> None:
    case = next(
        item
        for item in build_synthetic_corpus()
        if item.category is category and item.expected_failure_category is failure
    )
    assert evaluate_scenario(case).failure_category is failure


def test_normalization_and_protected_token_checks_are_unicode_deterministic() -> None:
    assert normalized_text("  ȘTIRE\n nouă ") == "știre nouă"
    assert preserves_values("Instituția confirmă", ("instituția",))
    assert preserves_numeric_values("Sunt 40 și 3,5 unități", ("40", "3,5"))


def test_change_ratio_is_deterministic_and_bounded() -> None:
    first = change_ratio("text sintetic", "text sintetic clar")
    assert first == change_ratio("text sintetic", "text sintetic clar")
    assert 0 <= first <= 1


def test_aggregate_result_is_immutable_content_free_and_complete() -> None:
    result = RevisionBenchmarkRunner().run()
    assert result.scenario_count == 24
    assert result.category_count == 12
    assert result.usable_revision_rate == 15 / 24
    assert result.evaluation_duration_ms == 0
    assert result.consistency_checks == ("scenario_expectations_match",)
    serialized = result.model_dump_json()
    for forbidden in (
        "synthetic-quality-case",
        "assembled_text",
        "revision_instruction",
        "component_reference",
        "provider_output",
        "http",
    ):
        assert forbidden not in serialized
    with pytest.raises(ValidationError):
        result.scenario_count = 1


def test_identical_runs_are_byte_deterministic() -> None:
    first = RevisionBenchmarkRunner().run().model_dump_json()
    second = RevisionBenchmarkRunner().run().model_dump_json()
    assert first == second


def test_future_provider_seam_is_present_but_disabled() -> None:
    with pytest.raises(RuntimeError, match="disabled"):
        RevisionBenchmarkRunner(BenchmarkMode.FUTURE_PROVIDER).run()


def test_failure_taxonomy_is_exact_and_complete() -> None:
    assert len(FailureCategory) == 21
    assert FailureCategory.USABLE_REVISION.value == "USABLE_REVISION"


def test_schema_fingerprint_is_frozen_and_no_transport_is_imported() -> None:
    digest = hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()
    assert digest == SCHEMA_SHA
