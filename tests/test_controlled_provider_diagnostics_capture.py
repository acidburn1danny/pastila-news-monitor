from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderClientResponse,
    AIProviderExecutionRequest,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.client import (
    OpenAIProviderClient,
)
from pastila_scout.editor.generation.controlled_revision_quality.benchmark import (
    build_synthetic_corpus,
)
from pastila_scout.editor.generation.controlled_revision_quality.pricing import (
    load_benchmark_pricing,
)
from pastila_scout.editor.generation.controlled_revision_quality.provider_diagnostics import (
    MALFORMED_REFERENCE,
    CostStatus,
    DiagnosticFailureStage,
    FirstInvalidReferenceKind,
    ProviderDiagnosticsArtifact,
    ProviderOperationalOutcome,
    ProviderTrialDiagnostic,
    TotalTokensSource,
    aggregate_provider_diagnostics,
    build_reference_diagnostic,
    build_usage_diagnostic,
    calculate_cost,
    hash_provider_request_id,
    write_diagnostics_artifact_atomic,
)
from scripts.controlled_provider_diagnostics_capture import (
    CapturingOpenAIInterpreter,
    CapturingProviderClient,
    EarlyProviderCapture,
)
from scripts.controlled_revision_benchmark_compatibility import (
    build_production_invocation,
    production_benchmark_configuration,
)
from scripts.run_controlled_provider_quality_baseline import (
    EXPECTED_SCHEMA_FINGERPRINT,
    _failure_stage,
    _provider_failure_outcome,
    schema_fingerprint,
)

REGISTRY = frozenset({"opening", "closing", "story:101", "story:102"})


def _references(produced, *, required=None):
    return build_reference_diagnostic(
        authorized=("story:101",),
        produced=tuple(produced),
        recognized_registry=REGISTRY,
        required=required,
    )


def _trial(reference, *, outcome=ProviderOperationalOutcome.PIPELINE_SUCCESS):
    usage = build_usage_diagnostic(prompt=100, completion=20, total=120)
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    return ProviderTrialDiagnostic(
        scenario_id="SYN-01",
        category="MINIMAL_CLARITY",
        provider="openai",
        model="gpt-4.1-mini",
        operational_outcome=outcome,
        failure_stage=(
            DiagnosticFailureStage.NONE
            if outcome is ProviderOperationalOutcome.PIPELINE_SUCCESS
            else DiagnosticFailureStage.REFERENCE_MAPPING
        ),
        references=_references(reference),
        provider_latency_ms=25,
        usage=usage,
        cost=calculate_cost(usage, pricing),
        provider_request_id_hash=hash_provider_request_id("request-secret"),
    )


def test_authorized_reference_success() -> None:
    result = _references(("story:101",))
    assert result.reference_precision == 1
    assert result.reference_recall == 1
    assert not result.unknown_references
    assert not result.unauthorized_references


def test_unknown_reference_is_ordered_and_counts_against_precision() -> None:
    result = _references(("story:999", "story:101"))
    assert result.unknown_references == ("story:999",)
    assert result.first_invalid_reference == "story:999"
    assert result.first_invalid_reference_kind is FirstInvalidReferenceKind.UNKNOWN
    assert result.reference_precision == 0.5
    assert result.reference_recall == 1


def test_known_but_unauthorized_reference() -> None:
    result = _references(("story:102",))
    assert result.unauthorized_references == ("story:102",)
    assert result.first_invalid_reference_kind is FirstInvalidReferenceKind.UNAUTHORIZED
    assert result.missing_authorized_references == ("story:101",)


def test_duplicate_and_provider_order_are_preserved() -> None:
    result = _references(("story:101", "story:101"))
    assert result.provider_produced_references_ordered == (
        "story:101",
        "story:101",
    )
    assert result.duplicate_provider_references == ("story:101",)
    assert result.first_invalid_reference_kind is FirstInvalidReferenceKind.DUPLICATE


def test_malformed_reference_uses_bounded_sentinel() -> None:
    canary = "private episode prose that must never persist"
    result = _references((canary,))
    assert result.provider_produced_references_ordered == (MALFORMED_REFERENCE,)
    assert result.first_invalid_reference_kind is FirstInvalidReferenceKind.MALFORMED
    assert canary not in result.model_dump_json()


def test_no_op_optional_reference_has_undefined_recall() -> None:
    result = _references((), required=())
    assert result.reference_precision is None
    assert result.reference_recall is None


def test_usage_null_and_derived_total_semantics() -> None:
    unavailable = build_usage_diagnostic(prompt=None, completion=None, total=None)
    assert unavailable.total_tokens_source is TotalTokensSource.UNAVAILABLE
    assert unavailable.effective_total_tokens is None
    derived = build_usage_diagnostic(prompt=10, completion=4, total=None)
    assert derived.derived_total_tokens == 14
    assert derived.total_tokens_source is TotalTokensSource.BENCHMARK_DERIVED


def test_cached_input_cost_uses_frozen_price() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    usage = build_usage_diagnostic(
        prompt=1000, completion=100, total=1100, cached_prompt_tokens=500
    )
    cost = calculate_cost(usage, pricing)
    assert cost.cost_status is CostStatus.CALCULATED
    assert cost.estimated_cost_usd == pytest.approx(0.00041)


def test_unknown_usage_produces_unknown_cost_not_zero() -> None:
    pricing = load_benchmark_pricing(
        Path("config/controlled-revision-provider-pricing-v1.yaml")
    )
    cost = calculate_cost(
        build_usage_diagnostic(prompt=None, completion=None, total=None), pricing
    )
    assert cost.cost_status is CostStatus.INSUFFICIENT_USAGE
    assert cost.estimated_cost_usd is None


def test_early_capture_survives_dto_rejection_and_hashes_request_id() -> None:
    scenario = build_synthetic_corpus()[0]
    invocation = build_production_invocation(scenario)
    request = AIProviderExecutionRequest(
        execution_identifier="execution",
        invocation=invocation,
        provider_identifier="openai",
        model_identifier="gpt-4.1-mini",
    )
    raw = SimpleNamespace(
        output_text=json.dumps(
            {
                "revised_components": [
                    {"component_reference": "story:999", "private": "secret prose"}
                ]
            }
        ),
        usage=SimpleNamespace(
            input_tokens=90,
            output_tokens=10,
            total_tokens=100,
            input_tokens_details=SimpleNamespace(cached_tokens=20, audio_tokens=None),
            output_tokens_details=SimpleNamespace(
                reasoning_tokens=3, audio_tokens=None
            ),
        ),
        id="raw-provider-request-id",
    )
    capture = EarlyProviderCapture(provider_response_received=True)

    class RejectingInterpreter:
        def interpret(self, request, response):
            raise ValueError("DTO rejected")

    wrapper = CapturingOpenAIInterpreter(RejectingInterpreter(), capture)
    with pytest.raises(ValueError, match="DTO rejected"):
        wrapper.interpret(request, AIProviderClientResponse(payload=raw, latency_ms=7))
    assert capture.usage.prompt_tokens == 90
    assert capture.references.unknown_references == ("story:999",)
    assert capture.provider_latency_ms == 7
    assert capture.provider_request_id_hash != "raw-provider-request-id"
    serialized = json.dumps(capture.references.model_dump(mode="json"))
    assert "secret prose" not in serialized


def test_client_wrapper_times_success_and_failure_without_retry() -> None:
    ticks = iter((1.0, 1.025, 2.0, 2.05))

    class Delegate:
        calls = 0

        def send(self, request, *, credential_provider):
            self.calls += 1
            if self.calls == 2:
                raise TimeoutError
            return AIProviderClientResponse(payload=object())

    delegate = Delegate()
    capture = EarlyProviderCapture()
    wrapper = CapturingProviderClient(delegate, capture, clock=lambda: next(ticks))
    wrapper.send(object(), credential_provider=object())
    assert capture.provider_latency_ms == pytest.approx(25)
    with pytest.raises(TimeoutError):
        wrapper.send(object(), credential_provider=object())
    assert capture.provider_latency_ms == pytest.approx(50)
    assert delegate.calls == 2


@pytest.mark.parametrize(
    ("code", "received", "outcome"),
    (
        ("provider_timeout", False, ProviderOperationalOutcome.PROVIDER_TIMEOUT),
        (
            "provider_rate_limited",
            False,
            ProviderOperationalOutcome.PROVIDER_RATE_LIMIT,
        ),
        (
            "provider_unavailable",
            False,
            ProviderOperationalOutcome.PROVIDER_SERVICE_FAILURE,
        ),
        (
            "provider_transport_failed",
            False,
            ProviderOperationalOutcome.PROVIDER_TRANSPORT_FAILURE,
        ),
        (
            "openai_provider_output_schema_invalid",
            True,
            ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
        ),
        ("unexpected", False, ProviderOperationalOutcome.BENCHMARK_INTERNAL_FAILURE),
    ),
)
def test_bounded_failure_classification(code, received, outcome) -> None:
    assert _provider_failure_outcome(code, received) is outcome


def test_dto_and_reference_failure_stages() -> None:
    safe = ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY
    assert (
        _failure_stage("openai_provider_output_schema_invalid", safe)
        is DiagnosticFailureStage.PROVIDER_DTO_VALIDATION
    )
    assert (
        _failure_stage("openai_provider_output_reference_unknown", safe)
        is DiagnosticFailureStage.REFERENCE_MAPPING
    )


def test_aggregate_reference_confusion_usage_cost_and_latency() -> None:
    aggregate = aggregate_provider_diagnostics(
        (
            _trial(("story:101",)),
            _trial(
                ("story:102",),
                outcome=ProviderOperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
            ),
        )
    )
    assert aggregate["reference_confusion_matrix"] == {
        "story:101 -> story:101": 1,
        "story:101 -> story:102": 1,
    }
    assert aggregate["usage_availability_rate"] == 1
    assert aggregate["cost_calculability_rate"] == 1
    assert aggregate["provider_latency_ms"]["mean"] == 25


def test_atomic_utf8_artifact_and_failed_replace_preserves_prior_file(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "diagnostics.json"
    artifact = ProviderDiagnosticsArtifact(
        schema_fingerprint=EXPECTED_SCHEMA_FINGERPRINT,
        pricing_version="openai-gpt-4-1-mini-2026-07-28",
    )
    write_diagnostics_artifact_atomic(path, artifact)
    original = path.read_bytes()
    assert json.loads(original)["trials"] == []

    def fail_replace(self, target):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError):
        write_diagnostics_artifact_atomic(path, artifact)
    assert path.read_bytes() == original


def test_frozen_schema_corpus_retry_and_model_guarantees() -> None:
    corpus = build_synthetic_corpus()
    configuration = production_benchmark_configuration()
    assert schema_fingerprint() == EXPECTED_SCHEMA_FINGERPRINT
    assert len(corpus) == 24
    assert len({item.category for item in corpus}) == 12
    assert configuration.model_identifier == "gpt-4.1-mini"
    assert configuration.retry_policy.maximum_attempts == 1
    assert '"max_retries": 0' in inspect.getsource(OpenAIProviderClient.send)


def test_request_id_hash_is_stable_and_one_way() -> None:
    value = hash_provider_request_id("request-123")
    assert value == hash_provider_request_id("request-123")
    assert value.startswith("sha256:")
    assert "request-123" not in value


def test_empty_checked_in_diagnostics_artifact_is_versioned_and_valid() -> None:
    payload = json.loads(
        Path("docs/artifacts/controlled-provider-quality-diagnostics.json").read_text(
            encoding="utf-8"
        )
    )
    artifact = ProviderDiagnosticsArtifact.model_validate(payload)
    assert artifact.schema_version == 1
    assert artifact.trials == ()
    assert artifact.aggregate is None
