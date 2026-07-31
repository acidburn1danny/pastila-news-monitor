"""Part 5L local cross-item contract expressibility tests."""

from __future__ import annotations

import inspect
import json

from jsonschema import Draft202012Validator

import scripts.investigate_openai_cross_item_contract as investigation


def _candidate(name: str) -> dict[str, object]:
    return next(
        item for item in investigation.candidate_results() if item["candidate"] == name
    )


def _rule(name: str) -> dict[str, str]:
    return next(
        item for item in investigation.rule_classifications() if item["rule"] == name
    )


def test_ownership_map_covers_every_requested_rule() -> None:
    assert {item["rule"] for item in investigation.ownership_map()} == {
        "component_reference_uniqueness",
        "exactly_once_occurrence",
        "authorized_reference_membership",
        "complete_authorized_reference_set",
        "source_order_preservation",
        "component_count_equality",
        "one_output_per_authorized_input",
        "absence_of_unauthorized_outputs",
    }


def test_current_uniqueness_owner_is_provider_dto() -> None:
    row = investigation.ownership_map()[0]
    assert row["current_owner"] == "provider_dto"
    assert row["dto_visible"] is True
    assert row["schema_visible"] is False


def test_downstream_authority_rules_are_reconstructor_owned() -> None:
    rows = investigation.ownership_map()[1:]
    assert all(item["reconstructor_visible"] for item in rows)


def test_capability_matrix_covers_required_keywords() -> None:
    assert {item["keyword"] for item in investigation.capability_matrix()} == {
        "uniqueItems",
        "contains",
        "minContains",
        "maxContains",
        "prefixItems",
        "items",
        "const",
        "enum",
        "dependentSchemas",
        "if/then/else",
        "unevaluatedItems",
        "unevaluatedProperties",
    }


def test_current_schema_proves_only_currently_used_provider_keywords() -> None:
    values = {item["keyword"]: item for item in investigation.capability_matrix()}
    assert values["items"]["provider_support_proven_by_repository"] is True
    assert values["const"]["provider_support_proven_by_repository"] is True
    assert values["contains"]["provider_support_proven_by_repository"] is False


def test_unique_items_rejects_only_identical_objects() -> None:
    result = _candidate("B")
    assert result["identical_duplicate_rejected"] is True
    assert result["different_body_duplicate_rejected"] is False


def test_current_schema_rejects_neither_duplicate_form() -> None:
    result = _candidate("A")
    assert result["identical_duplicate_rejected"] is False
    assert result["different_body_duplicate_rejected"] is False


def test_dynamic_contains_design_rejects_reference_duplicates() -> None:
    result = _candidate("C")
    assert result["different_body_duplicate_rejected"] is True
    assert result["dynamic"] is True


def test_prefix_items_design_rejects_wrong_identity_at_position() -> None:
    assert _candidate("D")["different_body_duplicate_rejected"] is True


def test_keyed_object_has_natural_key_uniqueness() -> None:
    assert _candidate("E")["different_body_duplicate_rejected"] is True


def test_every_synthetic_candidate_schema_is_draft_2020_12_valid() -> None:
    for candidate in "ABCDE":
        Draft202012Validator.check_schema(investigation.candidate_schema(candidate, 2))


def test_component_count_equality_is_directly_expressible() -> None:
    assert _rule("component_count_equality")["classification"] == "SCHEMA_EXPRESSIBLE"


def test_reference_uniqueness_is_only_partially_expressible_generically() -> None:
    assert _rule("component_reference_uniqueness")["classification"] == (
        "SCHEMA_PARTIALLY_EXPRESSIBLE"
    )


def test_authorized_membership_requires_dynamic_generation() -> None:
    assert "invocation-specific" in _rule("authorized_reference_membership")["reason"]


def test_size_estimates_cover_all_candidates_and_counts() -> None:
    values = investigation.size_estimates()
    assert len(values) == 20
    assert {item["component_count"] for item in values} == {1, 10, 25, 50}


def test_dynamic_schema_size_grows_with_component_count() -> None:
    values = [
        item for item in investigation.size_estimates() if item["candidate"] == "C"
    ]
    assert values[0]["canonical_bytes"] < values[-1]["canonical_bytes"]


def test_static_schema_size_is_constant() -> None:
    values = [
        item for item in investigation.size_estimates() if item["candidate"] == "A"
    ]
    assert len({item["canonical_bytes"] for item in values}) == 1


def test_provider_compatibility_is_not_claimed_for_new_keywords() -> None:
    for candidate in "BCDE":
        assert _candidate(candidate)["provider_compatibility"] == (
            "unproven_by_repository"
        )


def test_artifact_selects_one_root_conclusion_and_recommendation() -> None:
    artifact = investigation.build_artifact()
    assert artifact["root_conclusion"] == "CURRENT_DTO_OWNERSHIP_IS_CORRECT"
    assert artifact["recommendation"] == "KEEP_DUPLICATE_VALIDATION_IN_DTO"


def test_artifact_is_deterministic() -> None:
    assert investigation.build_artifact() == investigation.build_artifact()


def test_artifact_contains_only_safe_top_level_sections() -> None:
    assert set(investigation.build_artifact()) == {
        "investigation_version",
        "live_requests",
        "ownership_map",
        "capability_matrix",
        "rule_classifications",
        "candidate_results",
        "size_estimates",
        "architectural_ownership",
        "root_conclusion",
        "recommendation",
    }


def test_artifact_contains_no_payload_or_reference_values() -> None:
    serialized = json.dumps(investigation.build_artifact())
    for prohibited in (
        "synthetic-1",
        "body-a",
        "provider_output",
        "raw_response",
        "request_id",
        "credential",
    ):
        assert prohibited not in serialized


def test_investigation_has_no_live_or_sdk_execution_path() -> None:
    source = inspect.getsource(investigation)
    assert "OpenAIProviderClient" not in source
    assert "execute_scenario" not in source
    assert not hasattr(investigation, "LIVE_FLAG")


def test_main_reports_zero_requests(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(investigation, "ARTIFACT_PATH", tmp_path / "artifact.json")
    assert investigation.main() == 0
    output = capsys.readouterr().out
    assert "Live requests: 0" in output
    assert "SDK requests: 0" in output


def test_investigation_does_not_mutate_production_schema() -> None:
    before = investigation.controlled_revision_schema_json()
    investigation.build_artifact()
    assert investigation.controlled_revision_schema_json() == before
