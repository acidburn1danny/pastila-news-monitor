"""Part 5N safe operational-result invariants."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_openai_controlled_revision_e2e import configuration

ARTIFACT = Path(
    "docs/artifacts/openai-controlled-revision-final-operational-validation.json"
)


def _artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_exactly_four_canonical_scenarios_completed() -> None:
    artifact = _artifact()
    assert artifact["requests"] == 4
    assert [item["scenario"] for item in artifact["scenarios"]] == [
        "E2E-01",
        "E2E-02",
        "E2E-03",
        "E2E-04",
    ]


def test_every_scenario_terminated_safely() -> None:
    assert all(item["runtime_terminated_safely"] for item in _artifact()["scenarios"])


def test_every_outcome_uses_the_operational_taxonomy() -> None:
    allowed = {
        "PIPELINE_SUCCESS",
        "PROVIDER_OUTPUT_REJECTED_SAFELY",
        "EXTERNAL_PROVIDER_FAILURE",
    }
    assert all(
        item["operational_classification"] in allowed
        for item in _artifact()["scenarios"]
    )


def test_downstream_stages_are_reached_only_after_dto_pass() -> None:
    for item in _artifact()["scenarios"]:
        if not item["dto_pass"]:
            assert item["authorization_reached"] is False
            assert item["reconstruction_reached"] is False
            assert item["episode_draft_reached"] is False
            assert item["gateway_reached"] is False


def test_pipeline_success_reached_every_stage() -> None:
    success = _artifact()["scenarios"][0]
    assert success["dto_pass"] is True
    assert success["authorization_reached"] is True
    assert success["reconstruction_reached"] is True
    assert success["episode_draft_reached"] is True
    assert success["gateway_reached"] is True
    assert success["acceptance_reached"] is True


def test_editorial_failure_is_operationally_valid() -> None:
    success = _artifact()["scenarios"][0]
    assert success["operational_classification"] == "PIPELINE_SUCCESS"
    assert success["editorial_acceptance_pass"] is False


def test_safe_rejections_have_safe_categories() -> None:
    rejected = _artifact()["scenarios"][1:]
    assert all(item["safe_failure_category"] for item in rejected)


def test_aggregate_counts_are_consistent() -> None:
    artifact = _artifact()
    assert artifact["dto_passes"] + artifact["dto_failures"] == artifact["requests"]
    assert artifact["pipeline_successes"] + artifact["safe_rejections"] == 4
    assert artifact["external_failures"] == artifact["runtime_failures"] == 0


def test_retry_and_fallback_counts_are_zero() -> None:
    artifact = _artifact()
    assert artifact["retries"] == artifact["fallbacks"] == 0
    assert configuration("synthetic-model").retry_policy.maximum_attempts == 1


def test_artifact_contains_no_prohibited_content() -> None:
    serialized = ARTIFACT.read_text(encoding="utf-8")
    for prohibited in (
        "provider_output",
        "prompt_body",
        "request_id",
        "credential",
        "component_reference_value",
        "source_prose",
        "revised_prose",
    ):
        assert prohibited not in serialized
