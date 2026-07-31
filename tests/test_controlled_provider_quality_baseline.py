from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderExecutionFailureKind,
)
from pastila_scout.editor.generation.controlled_revision_quality.history import (
    BenchmarkHistory,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from scripts.run_controlled_provider_quality_baseline import (
    EXPECTED_SCHEMA_FINGERPRINT,
    OperationalOutcome,
    TrialResult,
    _failure_outcome,
    aggregate_results,
    build_artifact,
    history_entry,
    main,
    schema_fingerprint,
    write_artifact_atomic,
)


def _trial(number: int, *, usable: bool = True) -> TrialResult:
    quality = {
        "structural_validity": True,
        "dto_validity": True,
        "authorization_validity": True,
        "reconstruction_validity": True,
        "episode_draft_validity": True,
        "editorial_acceptance": usable,
        "meaning_preservation": True,
        "protected_structure_preservation": True,
        "quote_preservation": True,
        "numeric_fact_preservation": True,
        "temporal_fact_preservation": True,
        "source_authority_preservation": True,
        "no_op_compliance": True,
        "instruction_compliance": True,
        "revision_proportionality": True,
    }
    return TrialResult(
        f"SYN-{number:02d}",
        f"CATEGORY-{(number - 1) // 2:02d}",
        OperationalOutcome.PIPELINE_SUCCESS,
        None,
        1,
        0,
        0,
        float(number),
        100,
        20,
        None,
        None,
        120,
        0.000072,
        quality,
        usable,
        "USABLE_REVISION" if usable else "EDITORIAL_UNDER_REVISION",
    )


def test_schema_fingerprint_is_frozen() -> None:
    assert schema_fingerprint() == EXPECTED_SCHEMA_FINGERPRINT


def test_aggregate_includes_quality_operational_latency_tokens_and_cost() -> None:
    aggregate = aggregate_results((_trial(1), _trial(2, usable=False)))
    assert aggregate["scenario_count"] == 2
    assert aggregate["usable_revision_rate"] == 0.5
    assert aggregate["provider_requests"] == 2
    assert aggregate["retry_count"] == 0
    assert aggregate["fallback_count"] == 0
    assert aggregate["latency_ms"]["p95"] == 2.0
    assert aggregate["tokens"]["billable_total"] == 240


def test_external_failure_is_excluded_from_quality_metrics() -> None:
    failed = TrialResult(
        "SYN-02",
        "CATEGORY-00",
        OperationalOutcome.PROVIDER_TIMEOUT,
        "provider_timeout",
        1,
        0,
        0,
        30_000,
        0,
        0,
        None,
        None,
        0,
        0,
        None,
        None,
        None,
    )
    aggregate = aggregate_results((_trial(1), failed))
    assert aggregate["scenario_count"] == 2
    assert aggregate["quality_sample_count"] == 1
    assert aggregate["usable_revision_rate"] == 1.0


def test_interpretation_and_reconstruction_rejections_are_classified_safely() -> None:
    assert (
        _failure_outcome(AIProviderExecutionFailureKind.SCHEMA)
        is OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
    )
    assert (
        _failure_outcome(AIProviderExecutionFailureKind.INVALID_GATEWAY_PROJECTION)
        is OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
    )


def test_complete_artifact_and_history_entry_are_content_free() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    trials = tuple(_trial(number) for number in range(1, 25))
    artifact = build_artifact(
        "20260728-143015-openai-gpt-4.1-mini",
        "2026-07-28T14:30:15+00:00",
        pricing,
        trials,
    )
    assert artifact["root_conclusion"] == "CONTROLLED_PROVIDER_BASELINE_COMPLETE"
    assert artifact["aggregate"]["category_count"] == 12
    entry = history_entry(artifact)
    assert entry.provider_requests == 24
    assert entry.retry_count == 0
    serialized = json.dumps(artifact)
    assert "source_draft" not in serialized
    assert "revision_instruction" not in serialized


def test_atomic_artifact_write_is_utf8(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    write_artifact_atomic(path, {"root_conclusion": "ÎNCHEIAT"})
    assert json.loads(path.read_text(encoding="utf-8"))["root_conclusion"] == "ÎNCHEIAT"


def test_live_execution_is_opt_in(monkeypatch, capsys) -> None:
    monkeypatch.delenv("SCOUT_RUN_LIVE_PROVIDER_BASELINE", raising=False)
    assert main() == 0
    assert "disabled" in capsys.readouterr().out


def test_history_entry_validates_against_versioned_history_model() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    artifact = build_artifact(
        "20260728-143015-openai-gpt-4.1-mini",
        "2026-07-28T14:30:15+00:00",
        pricing,
        tuple(_trial(number) for number in range(1, 25)),
    )
    history = BenchmarkHistory(history=(history_entry(artifact),))
    assert history.schema_version == 1


def test_trial_rejects_negative_usage() -> None:
    with pytest.raises(ValueError):
        TrialResult(
            "SYN-01",
            "CATEGORY",
            OperationalOutcome.PIPELINE_SUCCESS,
            None,
            1,
            0,
            0,
            1,
            -1,
            0,
            None,
            None,
            0,
            0,
            {},
            True,
            None,
        )
