"""Part 5M duplicate-reference generation investigation tests."""

from __future__ import annotations

import hashlib
import json

import pytest
from openai.types.responses import Response
from pydantic import ValidationError
from test_openai_controlled_revision_adapter import (
    Credentials,
    Factory,
    FakeSDK,
    _raw_response,
)

import scripts.investigate_openai_duplicate_reference_generation as investigation
from pastila_scout.editor.generation.ai_provider_adapter import AIProviderClientRequest
from pastila_scout.editor.generation.ai_provider_adapter.openai.client import (
    OpenAIProviderClient,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
    OpenAIResponsesPayload,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.projector import (
    _COMPONENT_SHAPE_INSTRUCTIONS,
)


def test_m01_e2e02_input_references_are_unique() -> None:
    value = investigation.reconstruct_e2e02()
    assert value["authorized_reference_count"] == 1
    assert value["unique_authorized_reference_count"] == 1


def test_m02_projection_preserves_reference_cardinality() -> None:
    value = investigation.reconstruct_e2e02()
    assert value["projected_component_count"] == value["authorized_reference_count"]


def test_m03_projection_preserves_uniqueness() -> None:
    assert investigation.reconstruct_e2e02()["projected_references_unique"] is True


def test_m04_prompt_construction_preserves_component_count() -> None:
    assert investigation.build_artifact()["input_component_count"] == 1


def test_m05_prompt_occurrence_inventory_is_deterministic() -> None:
    first = investigation.reconstruct_e2e02()["prompt_occurrences"]
    assert first == investigation.reconstruct_e2e02()["prompt_occurrences"]
    assert first["R01"]["total"] == 2


def test_m06_instruction_matrix_is_complete() -> None:
    assert len(investigation.instruction_matrix()) == 10


def test_m07_schema_does_not_create_duplicate_slots() -> None:
    schema = json.loads(controlled_revision_schema_json())
    assert "prefixItems" not in schema["properties"]["revised_components"]


def test_m08_valid_unique_payload_passes_dto() -> None:
    OpenAIControlledRevisionProviderOutput.model_validate(
        {"revised_components": [investigation._story(1)]}
    )


def test_m09_exact_duplicate_reference_fails_dto() -> None:
    outcome = investigation.duplicate_validator_audit()["cases"]["exact_duplicate"]
    assert outcome["accepted"] is False
    assert outcome["duplicate_validator"] is True


def test_m10_same_reference_different_prose_fails_dto() -> None:
    outcome = investigation.duplicate_validator_audit()["cases"][
        "different_body_same_reference"
    ]
    assert outcome["duplicate_validator"] is True


def test_m11_same_prose_different_references_passes() -> None:
    outcome = investigation.duplicate_validator_audit()["cases"][
        "same_body_different_reference"
    ]
    assert outcome["accepted"] is True


@pytest.mark.parametrize(
    "case",
    ("case_variation", "unicode_variation", "separator_variation", "prefix_variation"),
)
def test_m12_m15_variations_are_not_collapsed_as_duplicates(case: str) -> None:
    outcome = investigation.duplicate_validator_audit()["cases"][case]
    assert outcome["duplicate_validator"] is False


def test_m16_index_and_type_suffix_variations_remain_distinct() -> None:
    cases = investigation.duplicate_validator_audit()["cases"]
    assert cases["index_variation"]["accepted"] is True
    assert cases["different_type_same_suffix"]["accepted"] is True


def test_m17_duplicate_validator_emits_one_root_error() -> None:
    outcome = investigation.duplicate_validator_audit()["cases"]["exact_duplicate"]
    assert outcome["total_errors"] == 1


def test_m18_duplicate_validator_has_no_union_noise() -> None:
    outcome = investigation.duplicate_validator_audit()["cases"]["exact_duplicate"]
    assert outcome["union_errors"] == 0


def test_m19_local_json_decode_preserves_array_cardinality() -> None:
    value = {"revised_components": [investigation._story(1), investigation._story(1)]}
    decoded = json.loads(json.dumps(value))
    assert len(decoded["revised_components"]) == 2


def test_m20_dto_input_construction_does_not_copy_or_merge_array() -> None:
    evidence = investigation.local_mutation_evidence()
    assert all(evidence.values())


def test_m21_sdk_mock_path_preserves_raw_response_identity() -> None:
    raw: Response = _raw_response()
    factory = Factory(FakeSDK([raw]))
    client = OpenAIProviderClient(
        authentication_reference="env:OPENAI_API_KEY", client_factory=factory
    )
    request = AIProviderClientRequest(
        provider_identifier="openai",
        timeout_seconds=1,
        correlation_identifier="safe",
        payload=OpenAIResponsesPayload(
            model="synthetic",
            instructions="safe",
            input="{}",
            schema_document_json=controlled_revision_schema_json(),
        ),
    )
    response = client.send(request, credential_provider=Credentials())
    assert response.payload is raw


def test_m22_m24_dto_failure_prevents_downstream_mapping() -> None:
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {
                "revised_components": [
                    investigation._story(1),
                    investigation._story(1),
                ]
            }
        )


def test_m25_historical_reference_type_mismatch_remains_schema_rejected() -> None:
    from scripts.investigate_openai_controlled_revision_contract import differential

    payload = {
        "revised_components": [
            {
                "component_type": "opening",
                "component_reference": "story:1",
                "revised_text": "x",
            }
        ]
    }
    assert differential(payload) == "SCHEMA_FAIL_DTO_FAIL"


def test_m26_schema_fingerprint_is_unchanged_from_part5k() -> None:
    assert hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest() == (
        investigation.SCHEMA_SHA256
    )


def test_m27_dto_fingerprint_is_unchanged() -> None:
    assert investigation.build_artifact()["dto_fingerprint"] == investigation.DTO_SHA256


def test_m28_prompt_fingerprint_is_unchanged() -> None:
    assert hashlib.sha256(_COMPONENT_SHAPE_INSTRUCTIONS.encode()).hexdigest() == (
        investigation.PROMPT_SHA256
    )


def test_m29_m31_runtime_retry_and_fallback_remain_absent() -> None:
    source = investigation.inspect.getsource(investigation)
    assert "compose_openai" not in source
    assert "AIRetryPolicy" not in source
    assert "fallback_model" not in source


def test_m32_safe_aliasing_reveals_no_references() -> None:
    serialized = json.dumps(investigation.reconstruct_e2e02()["safe_lineage"])
    assert "story:" not in serialized
    assert "R01" in serialized


def test_m33_safe_artifact_has_only_approved_sections() -> None:
    assert set(investigation.build_artifact()) == {
        "milestone",
        "production_frozen",
        "live_request_count",
        "sdk_request_count",
        "schema_fingerprint",
        "dto_fingerprint",
        "prompt_fingerprint",
        "input_component_count",
        "input_reference_uniqueness_classification",
        "projection_uniqueness_classification",
        "prompt_mapping_classification",
        "prompt_reference_occurrence_aggregates",
        "instruction_conformance_matrix",
        "lineage",
        "fixture_classification",
        "dto_validator_audit",
        "local_mutation_classification",
        "sdk_transformation_classification",
        "safe_failure_topology",
        "diagnostic_sufficiency",
        "additional_safe_diagnostics",
        "safe_topology_prototype",
        "risk_factors",
        "perturbation_metrics",
        "hypothesis_outcomes",
        "root_conclusion",
        "final_recommendation",
    }


def test_m34_m36_artifact_contains_no_prohibited_content() -> None:
    serialized = json.dumps(investigation.build_artifact())
    for prohibited in (
        "story:",
        "provider_output",
        "prompt_body",
        "request_id",
        "sk-",
        "raw_exception",
    ):
        assert prohibited not in serialized


def test_m37_m38_dry_run_makes_zero_calls(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(investigation, "ARTIFACT_PATH", tmp_path / "artifact.json")
    assert investigation.main() == 0
    output = capsys.readouterr().out
    assert "Provider calls: 0" in output
    assert "SDK requests: 0" in output


def test_m39_m40_part5k_and_part5l_contracts_remain_available() -> None:
    from scripts.investigate_openai_controlled_revision_contract import differential
    from scripts.investigate_openai_cross_item_contract import build_artifact

    assert build_artifact()["root_conclusion"] == "CURRENT_DTO_OWNERSHIP_IS_CORRECT"
    assert (
        differential(
            {
                "revised_components": [
                    {
                        "component_type": "opening",
                        "component_reference": "story:1",
                        "revised_text": "x",
                    }
                ]
            }
        )
        == "SCHEMA_FAIL_DTO_FAIL"
    )


def test_m41_m42_artifact_and_perturbations_are_deterministic() -> None:
    assert investigation.build_artifact() == investigation.build_artifact()
    assert len(investigation.perturbation_metrics()) == 16
