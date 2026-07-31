from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from pastila_scout.editor.generation.controlled_revision_quality.provider_diagnostics import (
    DiagnosticFailureStage,
    ProviderDiagnosticsArtifact,
    ProviderOperationalOutcome,
    ProviderTrialDiagnostic,
    build_reference_diagnostic,
    build_usage_diagnostic,
    calculate_cost,
)
from scripts.run_controlled_provider_quality_baseline import (
    OperationalOutcome,
    TrialResult,
)
from scripts.run_controlled_provider_quality_baseline_v2 import (
    EXPECTED_SCHEMA_FINGERPRINT,
    build_history_entry,
    build_v2_artifacts,
    preflight,
    schema_fingerprint,
)


def _result(number: int, *, success: bool) -> TrialResult:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    usage = build_usage_diagnostic(prompt=100, completion=20, total=120)
    reference = build_reference_diagnostic(
        authorized=("story:101",),
        produced=(("story:101",) if success else ("story:999",)),
        recognized_registry=frozenset({"story:101"}),
    )
    provider = ProviderTrialDiagnostic(
        scenario_id=f"SYN-{number:02d}",
        category=f"CATEGORY_{(number - 1) // 2:02d}",
        provider="openai",
        model="gpt-4.1-mini",
        operational_outcome=(
            ProviderOperationalOutcome.PIPELINE_SUCCESS
            if success
            else ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
        ),
        failure_code=None if success else "openai_provider_output_reference_unknown",
        failure_stage=(
            DiagnosticFailureStage.NONE
            if success
            else DiagnosticFailureStage.REFERENCE_MAPPING
        ),
        references=reference,
        provider_latency_ms=float(number),
        usage=usage,
        cost=calculate_cost(usage, pricing),
    )
    quality = (
        {
            "structural_validity": True,
            "dto_validity": True,
            "authorization_validity": True,
            "reconstruction_validity": True,
            "episode_draft_validity": True,
            "editorial_acceptance": True,
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
        if success
        else None
    )
    return TrialResult(
        scenario_id=f"SYN-{number:02d}",
        category=provider.category,
        outcome=(
            OperationalOutcome.PIPELINE_SUCCESS
            if success
            else OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
        ),
        diagnostic_code=provider.failure_code,
        provider_requests=1,
        retry_count=0,
        fallback_count=0,
        latency_ms=float(number),
        prompt_tokens=100,
        completion_tokens=20,
        reasoning_tokens=None,
        cached_prompt_tokens=None,
        billable_tokens=120,
        estimated_cost=provider.cost.estimated_cost_usd or 0,
        quality=quality,
        usable_revision=True if success else None,
        failure_category="USABLE_REVISION" if success else None,
        provider_diagnostic=provider,
    )


def test_preflight_validates_all_frozen_inputs_without_provider_calls(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "scripts.run_controlled_provider_quality_baseline_v2.BASELINE_PATH",
        tmp_path / "baseline-v2.json",
    )
    monkeypatch.setattr(
        "scripts.run_controlled_provider_quality_baseline_v2.DIAGNOSTICS_PATH",
        tmp_path / "diagnostics-v2.json",
    )
    monkeypatch.setattr(
        "scripts.run_controlled_provider_quality_baseline_v2.REPORT_PATH",
        tmp_path / "report-v2.md",
    )
    pricing, corpus = preflight("20990101-000000-openai-gpt-4.1-mini-v2")
    assert pricing.pricing_version == "openai-gpt-4-1-mini-2026-07-28"
    assert len(corpus) == 24
    assert schema_fingerprint() == EXPECTED_SCHEMA_FINGERPRINT


def test_instrumented_artifacts_reconcile_and_keep_null_quality() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    results = tuple(_result(number, success=False) for number in range(1, 25))
    artifact, diagnostics = build_v2_artifacts(
        "20260728-153000-openai-gpt-4.1-mini-v2",
        "2026-07-28T15:30:00+00:00",
        pricing,
        results,
    )
    assert artifact["provider_request_count"] == 24
    assert artifact["retry_count"] == 0
    assert artifact["fallback_count"] == 0
    assert artifact["quality_sample_status"] == "INSUFFICIENT"
    assert artifact["quality_metrics"]["usable_revision_rate"] is None
    assert artifact["pipeline_funnel"]["provider_responses_received"] == 24
    assert artifact["reference_metrics"]["unknown_scenarios"] == 24
    assert len(diagnostics.trials) == 24


def test_sufficient_quality_sample_establishes_valid_baseline() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    results = tuple(_result(number, success=number <= 12) for number in range(1, 25))
    artifact, _ = build_v2_artifacts(
        "20260728-153000-openai-gpt-4.1-mini-v2",
        "2026-07-28T15:30:00+00:00",
        pricing,
        results,
    )
    assert artifact["quality_sample_status"] == "SUFFICIENT"
    assert artifact["root_conclusion"] == "VALID_QUALITY_BASELINE"
    assert artifact["pipeline_funnel"]["pipeline_successes"] == 12


def test_v2_history_entry_preserves_nullable_metrics_and_additive_fields() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    artifact, _ = build_v2_artifacts(
        "20260728-153000-openai-gpt-4.1-mini-v2",
        "2026-07-28T15:30:00+00:00",
        pricing,
        tuple(_result(number, success=False) for number in range(1, 25)),
    )
    entry = build_history_entry(artifact)
    assert entry.usable_revision_rate is None
    assert entry.model_extra["pipeline_success_count"] == 0
    assert entry.model_extra["quality_sample_status"] == "INSUFFICIENT"


def test_v2_artifacts_are_content_free() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    artifact, diagnostics = build_v2_artifacts(
        "20260728-153000-openai-gpt-4.1-mini-v2",
        "2026-07-28T15:30:00+00:00",
        pricing,
        tuple(_result(number, success=False) for number in range(1, 25)),
    )
    payload = json.dumps(
        {"baseline": artifact, "diagnostics": diagnostics.model_dump(mode="json")}
    ).casefold()
    assert not any(
        value in payload
        for value in ("source_draft", "assembled_text", "api_key", "bearer ")
    )


def test_checked_in_official_v2_artifacts_reconcile_and_validate() -> None:
    baseline_path = Path("docs/artifacts/controlled-provider-quality-baseline-v2.json")
    diagnostics_path = Path(
        "docs/artifacts/controlled-provider-quality-diagnostics-v2.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    diagnostics = ProviderDiagnosticsArtifact.model_validate_json(
        diagnostics_path.read_text(encoding="utf-8")
    )
    assert baseline["benchmark_id"] == diagnostics.benchmark_id
    assert baseline["provider_request_count"] == 24
    assert baseline["retry_count"] == 0
    assert baseline["fallback_count"] == 0
    assert sum(baseline["operational_outcome_distribution"].values()) == 24
    assert len(baseline["trials"]) == len(diagnostics.trials) == 24
    assert baseline["root_conclusion"] == "PROVIDER_REFERENCE_CONTRACT_FAILURE"


def test_official_v2_usage_cost_references_and_hashes_are_complete() -> None:
    baseline = json.loads(
        Path("docs/artifacts/controlled-provider-quality-baseline-v2.json").read_text(
            encoding="utf-8"
        )
    )
    assert baseline["usage_metrics"]["available_scenarios"] == 24
    assert baseline["cost_metrics"]["calculable_scenarios"] == 24
    assert baseline["reference_metrics"]["missing_scenarios"] == 24
    hashes = [item["provider_request_id_hash"] for item in baseline["trials"]]
    assert all(value is None or value.startswith("sha256:") for value in hashes)
    assert all(
        item["operational_outcome"] == "PROVIDER_OUTPUT_REJECTED_SAFELY"
        for item in baseline["trials"]
    )


def test_official_v2_privacy_and_historical_v1_immutability() -> None:
    v2 = Path("docs/artifacts/controlled-provider-quality-baseline-v2.json").read_text(
        encoding="utf-8"
    )
    assert not any(
        value in v2.casefold()
        for value in (
            "source_draft",
            "assembled_text",
            "api_key",
            "bearer ",
            "response_body",
        )
    )
    import hashlib

    historical = Path("docs/artifacts/controlled-provider-quality-baseline.json")
    assert (
        hashlib.sha256(historical.read_bytes()).hexdigest()
        == "197732b1994a69144b158b9b8997dc4fa8f5503c583d4ac06ec3e27532736e00"
    )
