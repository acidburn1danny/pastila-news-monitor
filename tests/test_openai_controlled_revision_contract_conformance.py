"""Part 5J static schema/DTO/prompt conformance investigation tests."""

from __future__ import annotations

import json
from dataclasses import asdict

from scripts.investigate_openai_controlled_revision_contract import (
    DTO_SHA256,
    LIVE_SIGNATURE,
    SCHEMA_SHA256,
    build_artifact,
    conformance_matrix,
    contract_inventory,
    differential,
    differential_cases,
    dto_accepts,
    safe_signature,
    schema_document,
    synthetic_cases,
)


def _classification(name: str) -> str:
    payload, _ = differential_cases()[name]
    return differential(payload)


def test_j01_contract_inventory_is_deterministic() -> None:
    assert contract_inventory() == contract_inventory()


def test_j02_schema_fingerprint_is_stable() -> None:
    assert build_artifact()["schema_sha256"] == SCHEMA_SHA256


def test_j03_dto_fingerprint_is_stable() -> None:
    assert build_artifact()["dto_sha256"] == DTO_SHA256


def test_j04_prompt_fields_match_dto_fields() -> None:
    rows = [row for row in conformance_matrix() if row["classification"] == "ALIGNED"]
    assert {row["field"] for row in rows} >= {
        "component_type",
        "component_reference",
        "revised_text",
        "factual_summary",
        "commentary_block_texts",
        "ending",
        "bridge_text",
    }


def test_j05_text_variant_schema_and_dto_align() -> None:
    assert _classification("D01_valid_text") == "SCHEMA_PASS_DTO_PASS"


def test_j06_story_variant_schema_and_dto_align() -> None:
    assert _classification("D02_valid_story") == "SCHEMA_PASS_DTO_PASS"


def test_j07_cta_variant_schema_and_dto_align() -> None:
    assert _classification("D03_valid_cta") == "SCHEMA_PASS_DTO_PASS"


def test_j08_additional_properties_are_forbidden_by_both() -> None:
    assert _classification("D15_extra_field") == "SCHEMA_FAIL_DTO_FAIL"


def test_j09_required_fields_align() -> None:
    assert _classification("D04_story_missing_ending") == "SCHEMA_FAIL_DTO_FAIL"


def test_j10_minimum_string_lengths_align() -> None:
    assert _classification("D08_empty_factual_summary") == "SCHEMA_FAIL_DTO_FAIL"


def test_j11_array_cardinality_aligns() -> None:
    schema = schema_document()["$defs"]["OpenAIRevisedStoryComponent"]
    field = schema["properties"]["commentary_block_texts"]
    assert field.get("minItems") is None
    assert field["maxItems"] == 100
    assert _classification("D10_empty_commentary") == "SCHEMA_PASS_DTO_PASS"


def test_j12_component_type_literals_align() -> None:
    assert _classification("D13_unknown_type") == "SCHEMA_FAIL_DTO_FAIL"


def test_j13_union_has_three_ordered_anyof_branches_without_discriminator() -> None:
    inventory = contract_inventory()
    assert inventory["union_keyword"] == "anyOf"
    assert inventory["discriminator"] is None
    assert len(inventory["branch_order"]) == 3


def test_j14_nonmatching_branch_errors_are_reduced() -> None:
    signature = safe_signature(synthetic_cases()["J01_missing_required_body"])
    assert signature is not None
    assert signature.union_errors > 0


def test_j15_missing_field_signature_is_content_free() -> None:
    signature = safe_signature(synthetic_cases()["J01_missing_required_body"])
    assert signature and signature.primary_category == "missing_required_field"


def test_j16_foreign_field_signature_is_classified() -> None:
    signature = safe_signature(synthetic_cases()["J06_valid_plus_foreign"])
    assert signature and signature.primary_category == "extra_field"


def test_j17_wrong_body_signature_is_not_dto_valid() -> None:
    assert not dto_accepts(synthetic_cases()["J04_story_type_text_body"])


def test_j18_too_short_signature_is_constraint_violation() -> None:
    signature = safe_signature(synthetic_cases()["J07_empty_required"])
    assert signature and signature.primary_category == "constraint_violation"


def test_j19_component_model_validator_signature_is_exact_live_match() -> None:
    signature = safe_signature(synthetic_cases()["J14_text_reference_validator"])
    assert signature and signature.tuple() == LIVE_SIGNATURE


def test_j20_duplicate_reference_signature_is_independent() -> None:
    signature = safe_signature(synthetic_cases()["J15_duplicate_reference"])
    assert signature and signature.duplicate_validator


def test_j21_exact_live_signature_comparison_has_one_match() -> None:
    assert build_artifact()["exact_live_signature_matches"] == [
        "J14_text_reference_validator"
    ]


def test_j22_signature_is_unique_within_required_synthetic_matrix() -> None:
    assert len(build_artifact()["exact_live_signature_matches"]) == 1


def test_j23_historical_schema_dto_mismatch_is_now_aligned() -> None:
    assert _classification("D17_source_type_mismatch") == "SCHEMA_FAIL_DTO_FAIL"


def test_j24_no_schema_fail_dto_pass_case_exists() -> None:
    assert all(
        differential(payload) != "SCHEMA_FAIL_DTO_PASS"
        for payload, _ in differential_cases().values()
    )


def test_j25_post_schema_semantic_rules_are_separate() -> None:
    assert differential_cases()["D19_missing_authorized"][1] == (
        "POST_SCHEMA_SEMANTIC_CONTRACT"
    )


def test_j26_interpreter_expectation_is_dto_validation() -> None:
    assert all(row["interpreter_use"] for row in conformance_matrix())


def test_j27_reconstructor_expectations_are_mapped() -> None:
    rows = conformance_matrix()
    assert any(row["reconstructor_use"] == "dispatch_and_lookup" for row in rows)
    assert any(row["reconstructor_use"] == "required" for row in rows)


def test_j28_safe_signatures_contain_no_values() -> None:
    serialized = json.dumps(
        {
            name: asdict(value) if value else None
            for name, payload in synthetic_cases().items()
            if (value := safe_signature(payload))
        }
    )
    assert "synthetic" not in serialized
    assert "revised_text" not in serialized


def test_j29_safe_signatures_contain_no_references() -> None:
    serialized = json.dumps(build_artifact()["synthetic_signatures"])
    assert "story:101" not in serialized
    assert '"component_reference":' not in serialized


def test_j30_safe_artifact_contains_no_provider_content() -> None:
    artifact = json.dumps(build_artifact())
    assert "provider_output" not in artifact
    assert "raw_response" not in artifact
    assert "prompt_body" not in artifact


def test_j31_safe_artifact_top_level_keys_are_approved() -> None:
    assert set(build_artifact()) == {
        "investigation_version",
        "schema_sha256",
        "previous_schema_sha256",
        "dto_sha256",
        "prompt_contract_sha256",
        "inventory",
        "conformance_matrix",
        "synthetic_signatures",
        "exact_live_signature_matches",
        "differential_cases",
        "post_schema_rules",
    }


def test_j32_no_live_execution_flag_exists() -> None:
    import scripts.investigate_openai_controlled_revision_contract as investigation

    assert not hasattr(investigation, "LIVE_FLAG")


def test_j33_investigation_has_no_sdk_execution_entrypoint() -> None:
    import scripts.investigate_openai_controlled_revision_contract as investigation

    assert not hasattr(investigation, "execute_scenario")


def test_j34_production_prompt_fingerprint_is_frozen() -> None:
    assert build_artifact()["prompt_contract_sha256"] == (
        "cb6f07d47ec80ee8dfa246e5151f4c5a625adac2372f05a7cbccf4cbc3ebbf1c"
    )


def test_j35_production_schema_fingerprint_remains_frozen() -> None:
    assert build_artifact()["schema_sha256"] == SCHEMA_SHA256


def test_j36_production_dto_fingerprint_remains_frozen() -> None:
    assert build_artifact()["dto_sha256"] == DTO_SHA256


def test_j37_investigation_does_not_import_runtime_composition() -> None:
    import inspect

    import scripts.investigate_openai_controlled_revision_contract as investigation

    assert "compose_openai" not in inspect.getsource(investigation)


def test_j38_investigation_has_no_retry_or_fallback_configuration() -> None:
    import inspect

    import scripts.investigate_openai_controlled_revision_contract as investigation

    source = inspect.getsource(investigation)
    assert "AIRetryPolicy" not in source
    assert "fallback" not in source.casefold()


def test_j39_part5g_diagnostics_preserve_exact_known_topology() -> None:
    signature = safe_signature(synthetic_cases()["J14_text_reference_validator"])
    assert signature and signature.tuple() == LIVE_SIGNATURE


def test_j40_full_report_artifact_is_deterministic() -> None:
    assert build_artifact() == build_artifact()
