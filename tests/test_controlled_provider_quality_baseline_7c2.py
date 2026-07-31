"""Offline validation for the Part 7C.2 execution gate and artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_controlled_provider_quality_baseline_v2 import _result

from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    project_production_request,
)
from scripts.run_controlled_provider_quality_baseline_7c2 import (
    ProjectionInvariantError,
    _history_entry,
    build_artifacts,
    dry_run_projection,
    projection_checkpoint,
)


def test_dry_run_checks_actual_requests_for_all_frozen_scenarios():
    records = dry_run_projection(build_synthetic_corpus())

    assert len(records) == 24
    assert all(item["count_equality"] for item in records)
    assert all(item["set_equality"] for item in records)
    assert all(not item["duplicate_projected_references"] for item in records)


def test_projection_checkpoint_uses_authoritative_targets_and_transport_schema():
    scenario = build_synthetic_corpus()[0]
    invocation = build_production_invocation(scenario)
    projected = project_production_request(scenario, invocation)

    record = projection_checkpoint(
        scenario.scenario_key, invocation, projected.client_request
    )

    assert record["authorized_reference_count"] == len(
        invocation.request.revision_targets
    )
    assert record["count_equality"] is True
    assert record["set_equality"] is True


def test_projection_checkpoint_rejects_tampered_effective_schema_before_transport():
    scenario = build_synthetic_corpus()[0]
    invocation = build_production_invocation(scenario)
    projected = project_production_request(scenario, invocation)
    payload = projected.client_request.payload
    schema = json.loads(payload.schema_document_json)
    first = next(iter(schema["$defs"].values()))
    first["properties"]["component_reference"]["const"] = "story:999"
    tampered_payload = payload.model_copy(
        update={
            "schema_document_json": json.dumps(
                schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        }
    )
    client_request = projected.client_request.model_copy(
        update={"payload": tampered_payload}
    )

    with pytest.raises(ProjectionInvariantError):
        projection_checkpoint(scenario.scenario_key, invocation, client_request)


def test_post_remediation_artifact_is_comparable_and_history_is_additive():
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    results = tuple(_result(number, success=True) for number in range(1, 25))
    checkpoints = dry_run_projection(build_synthetic_corpus())

    artifact, diagnostics = build_artifacts(
        "20260728-180000-openai-gpt-4.1-mini-7c2",
        "2026-07-28T18:00:00+00:00",
        pricing,
        results,
        checkpoints,
    )
    history = _history_entry(artifact)

    assert artifact["official_baseline"] is True
    assert artifact["projection_checkpoint"]["all_scenarios_passed"] is True
    assert artifact["reference_metrics"]["exact_reference_compliance_rate"] == 1
    assert artifact["root_conclusion"] == "REFERENCE_CONTRACT_REMEDIATION_EFFECTIVE"
    assert artifact["comparison_with_part_7c_1"]["authorization_passes"] == [0, 24]
    assert history.model_extra["official_baseline"] is True
    assert len(diagnostics.trials) == 24
    assert "api_key" not in json.dumps(artifact).casefold()
