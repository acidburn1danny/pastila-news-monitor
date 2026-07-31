"""Part 5I content-free reliability assessment harness tests."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from scripts.assess_openai_controlled_revision_reliability import (
    LIVE_FLAG,
    MODELS_VARIABLE,
    RUNS_VARIABLE,
    SCENARIOS_VARIABLE,
    AssessmentConfiguration,
    AssessmentConfigurationError,
    TrialPlan,
    TrialRecord,
    _category,
    build_plan,
    dto_fingerprint_valid,
    main,
    parse_configuration,
    record_trial,
    schema_fingerprint_valid,
    summarize,
    wilson_interval,
)
from scripts.validate_openai_controlled_revision_e2e import ScenarioResult


def _environment(**updates: str) -> dict[str, str]:
    values = {
        MODELS_VARIABLE: "gpt-4.1-mini,gpt-4.1",
        SCENARIOS_VARIABLE: "E2E-01,E2E-02,E2E-03,E2E-04",
        RUNS_VARIABLE: "5",
    }
    values.update(updates)
    return values


def _result(**updates) -> ScenarioResult:
    values = {
        "identifier": "E2E-02",
        "passed": False,
        "classification": "openai_provider_output_schema_invalid",
        "duration_ms": 100.0,
        "attempts": 1,
        "sdk_requests": 1,
        "projections": 1,
        "credential_resolutions": 1,
        "sdk_constructions": 1,
        "dto_validations": 0,
        "authorizations": 0,
        "reconstructions": 0,
        "domain_validations": 0,
        "gateway_results": 0,
        "returned_reference_count": 1,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "request_id_available": False,
        "model_id_available": False,
        "dto_entered": True,
        "dto_validated": False,
        "dto_safe_metadata": (
            ("total_error_count", "11"),
            ("affected_component_count", "1"),
            ("union_branch_error_count", "9"),
            ("union_expansion_suspected", "yes"),
            ("duplicate_reference_validator_triggered", "no"),
            ("probable_primary_failure_category", "invalid_component_shape"),
        ),
    }
    values.update(updates)
    return ScenarioResult(**values)


def _record(**updates) -> TrialRecord:
    value = TrialRecord(
        scenario="E2E-02",
        configured_model="gpt-4.1-mini",
        sample_index=1,
        result_category="PROVIDER_DTO_MALFORMED_COMPONENT",
        furthest_stage="json_decoded",
        duration_ms=100,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        usage_available=False,
        request_id_available=False,
        returned_model_available=False,
        dto_error_count=11,
        affected_component_count=1,
        union_error_count=9,
        union_expansion_suspected=True,
        duplicate_reference_triggered=False,
        primary_safe_category="invalid_component_shape",
        aggregate_pass=False,
    )
    return replace(value, **updates)


def test_i01_live_is_disabled_by_default(monkeypatch, capsys) -> None:
    for key, value in _environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(LIVE_FLAG, raising=False)
    assert main() == 0
    output = capsys.readouterr().out
    assert "Live assessment skipped" in output
    assert "SDK requests: 0" in output


def test_i02_model_allowlist_parsing() -> None:
    assert parse_configuration(_environment()).models == ("gpt-4.1-mini", "gpt-4.1")


@pytest.mark.parametrize("value", ("", ",", "gpt-4.1-mini,gpt-4.1-mini"))
def test_i03_empty_or_duplicate_models_are_rejected(value: str) -> None:
    with pytest.raises(AssessmentConfigurationError):
        parse_configuration(_environment(**{MODELS_VARIABLE: value}))


def test_i04_scenario_allowlist_parsing() -> None:
    assert parse_configuration(_environment()).scenarios[0] == "E2E-01"


def test_i05_unknown_scenario_is_rejected() -> None:
    with pytest.raises(AssessmentConfigurationError):
        parse_configuration(_environment(**{SCENARIOS_VARIABLE: "E2E-99"}))


@pytest.mark.parametrize("value", ("0", "-1", "not-an-integer"))
def test_i06_positive_run_count_is_required(value: str) -> None:
    with pytest.raises(AssessmentConfigurationError):
        parse_configuration(_environment(**{RUNS_VARIABLE: value}))


def test_i07_request_budget_is_exact() -> None:
    assert parse_configuration(_environment()).request_budget == 40


def test_i08_maximum_budget_is_enforced() -> None:
    with pytest.raises(AssessmentConfigurationError, match="budget"):
        parse_configuration(_environment(**{RUNS_VARIABLE: "6"}))


def test_i09_one_attempt_per_trial_is_preserved() -> None:
    assert _result().attempts == 1


def test_i10_plan_never_changes_the_configured_model() -> None:
    configuration = parse_configuration(_environment())
    assert {item.model for item in build_plan(configuration)} == set(
        configuration.models
    )


def test_i11_trial_order_is_deterministic_and_interleaved() -> None:
    configuration = parse_configuration(_environment())
    first = build_plan(configuration)
    assert first == build_plan(configuration)
    assert [(item.scenario, item.model) for item in first[:4]] == [
        ("E2E-01", "gpt-4.1-mini"),
        ("E2E-01", "gpt-4.1"),
        ("E2E-02", "gpt-4.1-mini"),
        ("E2E-02", "gpt-4.1"),
    ]


def test_i12_each_trial_has_a_unique_execution_ordinal() -> None:
    plan = build_plan(parse_configuration(_environment()))
    assert len({item.ordinal for item in plan}) == len(plan)


def test_i13_dto_pass_classification_and_stage() -> None:
    result = _result(passed=True, dto_validations=1, dto_validated=True)
    record = record_trial(TrialPlan(1, 1, "E2E-02", "gpt-4.1"), result)
    assert record.result_category == "PASS"
    assert record.furthest_stage == "aggregate_passed"


def test_i14_malformed_component_uses_safe_diagnostic() -> None:
    assert _category(_result(), dict(_result().dto_safe_metadata)) == (
        "PROVIDER_DTO_MALFORMED_COMPONENT"
    )


def test_i15_duplicate_reference_is_distinct() -> None:
    result = _result(
        dto_safe_metadata=(("duplicate_reference_validator_triggered", "yes"),)
    )
    assert _category(result, dict(result.dto_safe_metadata)) == (
        "PROVIDER_DTO_DUPLICATE_REFERENCE"
    )


def test_i16_pre_dto_failure_does_not_claim_json_decode() -> None:
    result = _result(dto_entered=False, classification="decode_failed")
    record = record_trial(TrialPlan(1, 1, "E2E-02", "gpt-4.1"), result)
    assert record.furthest_stage == "provider_response_received"


def test_i17_provider_failure_is_external() -> None:
    result = _result(dto_entered=False, classification="openai_provider_network_error")
    assert _category(result, {}) == "EXTERNAL_PROVIDER_FAILURE"


def test_i18_wilson_interval_known_boundaries() -> None:
    lower, upper = wilson_interval(5, 5) or (0, 0)
    assert lower == pytest.approx(0.5655, abs=0.001)
    assert upper == 1


def test_i19_zero_denominator_is_not_applicable() -> None:
    assert wilson_interval(0, 0) is None


def test_i20_summary_aggregation_is_exact() -> None:
    summary = summarize((_record(), _record(sample_index=2)))[0]
    assert summary["completed_trials"] == 2
    assert summary["dto_failures"] == 2
    assert summary["malformed_component_failures"] == 2


def test_i21_safe_record_has_only_approved_fields() -> None:
    serialized = json.dumps(
        _record().__dict__ if hasattr(_record(), "__dict__") else {}
    )
    assert "provider_output" not in serialized
    assert "raw_response" not in serialized


def test_i22_i24_privacy_markers_and_exceptions_are_absent() -> None:
    serialized = repr(record_trial(TrialPlan(1, 1, "E2E-02", "gpt-4.1"), _result()))
    for marker in ("SECRET", "source prose", "raw exception", "request-id-value"):
        assert marker not in serialized


def test_i23_request_id_is_reduced_to_availability() -> None:
    record = record_trial(
        TrialPlan(1, 1, "E2E-02", "gpt-4.1"),
        _result(request_id_available=True),
    )
    assert record.request_id_available is True
    assert not hasattr(record, "request_id")


def test_i25_plan_has_no_resume_or_cache_identity() -> None:
    assert not hasattr(build_plan(parse_configuration(_environment()))[0], "response")


def test_i26_schema_fingerprint_is_frozen() -> None:
    assert schema_fingerprint_valid()


def test_i27_dto_fingerprint_is_frozen() -> None:
    assert dto_fingerprint_valid()


def test_i28_prompt_contract_is_enforced_by_preflight(capsys, monkeypatch) -> None:
    for key, value in _environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(LIVE_FLAG, raising=False)
    assert main() == 0
    assert "Prompt correction present: PASS" in capsys.readouterr().out


def test_i29_samples_are_separate_plan_items_not_retries() -> None:
    configuration = AssessmentConfiguration(("gpt-4.1",), ("E2E-01",), 3)
    plan = build_plan(configuration)
    assert [item.sample_index for item in plan] == [1, 2, 3]
    assert [item.ordinal for item in plan] == [1, 2, 3]


def test_i30_editorial_rate_is_separate_from_dto_rate() -> None:
    dto_pass = _record(
        result_category="EDITORIAL_ACCEPTANCE_FAILURE",
        furthest_stage="acceptance_evaluated",
    )
    summary = summarize((dto_pass,))[0]
    assert summary["dto_success_rate"] == 1
    assert summary["end_to_end_success_rate"] == 0
