"""Aggregate deterministic quality metrics without retaining scenario prose."""

from __future__ import annotations

from collections import Counter

from .results import BenchmarkResult, ScenarioEvaluation
from .scenario import ScenarioCategory


def aggregate_benchmark(
    evaluations: tuple[ScenarioEvaluation, ...], *, duration_ms: float = 0
) -> BenchmarkResult:
    if not evaluations:
        raise ValueError("benchmark requires at least one evaluation")
    count = len(evaluations)
    rate = (
        lambda attribute: sum(
            bool(getattr(item.dimensions, attribute)) for item in evaluations
        )
        / count
    )
    failures = Counter(item.failure_category for item in evaluations)
    category_scores = tuple(
        (
            category,
            sum(
                item.usable_revision
                for item in evaluations
                if item.category is category
            )
            / sum(item.category is category for item in evaluations),
        )
        for category in ScenarioCategory
        if any(item.category is category for item in evaluations)
    )
    dimension_rates = tuple(
        rate(name)
        for name in (
            "structural_validity",
            "dto_validity",
            "authorization_validity",
            "reconstruction_validity",
            "episode_draft_validity",
            "editorial_acceptance",
            "meaning_preservation",
            "protected_structure_preservation",
            "quote_preservation",
            "numeric_fact_preservation",
            "temporal_fact_preservation",
            "source_authority_preservation",
            "no_op_compliance",
            "instruction_compliance",
            "revision_proportionality",
        )
    )
    return BenchmarkResult(
        scenario_count=count,
        category_count=len(category_scores),
        usable_revision_rate=sum(item.usable_revision for item in evaluations) / count,
        structural_pass_rate=rate("structural_validity"),
        dto_pass_rate=rate("dto_validity"),
        authorization_pass_rate=rate("authorization_validity"),
        reconstruction_pass_rate=rate("reconstruction_validity"),
        episode_draft_pass_rate=rate("episode_draft_validity"),
        editorial_pass_rate=rate("editorial_acceptance"),
        meaning_preservation_rate=rate("meaning_preservation"),
        quote_preservation_rate=rate("quote_preservation"),
        numeric_preservation_rate=rate("numeric_fact_preservation"),
        temporal_preservation_rate=rate("temporal_fact_preservation"),
        protected_structure_preservation_rate=rate("protected_structure_preservation"),
        instruction_compliance_rate=rate("instruction_compliance"),
        no_op_compliance_rate=rate("no_op_compliance"),
        failure_counts=tuple(sorted(failures.items(), key=lambda item: item[0].value)),
        category_scores=category_scores,
        overall_score=sum(dimension_rates) / len(dimension_rates) * 100,
        evaluation_duration_ms=duration_ms,
        consistency_checks=(
            (
                "scenario_expectations_match"
                if all(item.consistency_passed for item in evaluations)
                else "scenario_expectation_mismatch"
            ),
        ),
    )
