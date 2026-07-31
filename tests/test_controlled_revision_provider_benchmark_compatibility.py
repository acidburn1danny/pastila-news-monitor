"""Part 7B offline provider-benchmark corpus compatibility tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.controlled_revision_quality import (
    build_synthetic_corpus,
    load_benchmark_pricing,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_editorial_acceptance_specification,
    build_production_invocation,
    production_benchmark_configuration,
    project_production_request,
    validate_provider_compatibility,
)
from scripts.validate_openai_controlled_revision_e2e import configuration

PRICING = Path("config/controlled-revision-provider-pricing-v1.yaml")
SCHEMA_SHA = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"


def test_frozen_corpus_identity_is_preserved() -> None:
    corpus = build_synthetic_corpus()
    assert tuple(item.scenario_key for item in corpus) == tuple(
        f"SYN-{number:02d}" for number in range(1, 25)
    )
    assert len({item.category for item in corpus}) == 12
    assert tuple(item.category for item in corpus[::2]) == tuple(
        item.category for item in corpus[1::2]
    )


def test_every_scenario_has_concrete_instruction_and_valid_target_subset() -> None:
    for scenario in build_synthetic_corpus():
        assert len(scenario.revision_instruction) >= 20
        assert scenario.authorized_components == ("story:101",)
        assert scenario.acceptance_specification.allowed_editable_targets == (
            "story:101",
        )


def test_all_scenarios_pass_production_authorization_and_request_generation() -> None:
    results = tuple(
        validate_provider_compatibility(item) for item in build_synthetic_corpus()
    )
    assert len(results) == 24
    assert all(item.compatible for item in results)


def test_production_invocations_preserve_instruction_and_source_identity() -> None:
    for scenario in build_synthetic_corpus():
        invocation = build_production_invocation(scenario)
        assert invocation.request.source_draft is scenario.source_draft
        assert (
            invocation.request.revision_instructions.editorial_instruction
            == scenario.revision_instruction
        )
        assert len(invocation.request.revision_targets) == 1


def test_provider_request_projection_constructs_dto_without_transport(
    monkeypatch,
) -> None:
    def forbidden_transport(*args, **kwargs):
        raise AssertionError("SDK construction is forbidden")

    monkeypatch.setattr("openai.OpenAI", forbidden_transport)
    projected = tuple(
        project_production_request(item) for item in build_synthetic_corpus()
    )
    assert len(projected) == 24
    assert all(item.client_request.payload is not None for item in projected)


def test_production_configuration_exactly_matches_part5n() -> None:
    current = production_benchmark_configuration()
    frozen = configuration("gpt-4.1-mini")
    assert current == frozen
    assert current.retry_policy.maximum_attempts == 1


def test_every_scenario_has_deterministic_acceptance_specification() -> None:
    for scenario in build_synthetic_corpus():
        local = scenario.acceptance_specification
        production = build_editorial_acceptance_specification(scenario)
        assert local.minimum_length > 0
        assert local.maximum_length >= local.minimum_length
        assert production.target_references == scenario.authorized_components
        assert production.required_numeric_values == ("40",)
        assert production.required_dates == ("miercuri",)


def test_no_change_acceptance_is_explicit() -> None:
    cases = [
        item
        for item in build_synthetic_corpus()
        if item.category.value == "NO_CHANGE_REQUIRED"
    ]
    assert all(item.acceptance_specification.expected_no_op for item in cases)
    assert all(
        not build_editorial_acceptance_specification(item).require_meaningful_revision
        for item in cases
    )


def test_versioned_pricing_is_resolvable_and_reproducible() -> None:
    pricing = load_benchmark_pricing(PRICING)
    assert pricing.contract_version == "controlled-revision-provider-pricing-v1"
    assert pricing.model == "gpt-4.1-mini"
    assert pricing.input_per_1m_tokens == 0.40
    assert pricing.cached_input_per_1m_tokens == 0.10
    assert pricing.output_per_1m_tokens == 1.60
    assert (
        pricing.estimate_cost(
            input_tokens=1_000_000,
            cached_input_tokens=0,
            output_tokens=1_000_000,
        )
        == 2.0
    )


@pytest.mark.parametrize(
    "values",
    [
        {"input_tokens": -1, "cached_input_tokens": 0, "output_tokens": 0},
        {"input_tokens": 1, "cached_input_tokens": 2, "output_tokens": 0},
    ],
)
def test_pricing_rejects_invalid_accounting(values) -> None:
    with pytest.raises(ValueError, match="token|cached input"):
        load_benchmark_pricing(PRICING).estimate_cost(**values)


def test_compatibility_results_and_artifacts_are_content_free() -> None:
    records = [
        asdict(validate_provider_compatibility(item))
        for item in build_synthetic_corpus()
    ]
    serialized = json.dumps(records, sort_keys=True)
    for forbidden in (
        "Instituția",
        "revision_instruction",
        "provider_output",
        "component_reference",
        "api_key",
    ):
        assert forbidden not in serialized


def test_schema_fingerprint_remains_frozen() -> None:
    assert (
        hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()
        == SCHEMA_SHA
    )
