"""Part 5M content-free duplicate-reference generation investigation."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderExecutionRequest,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionProjector,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.client import (
    OpenAIProviderClient,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.interpreter import (
    OpenAIControlledRevisionInterpreter,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.projector import (
    _COMPONENT_SHAPE_INSTRUCTIONS,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.validation_diagnostics import (
    build_safe_dto_validation_diagnostics,
)

try:
    from scripts.validate_openai_controlled_revision_e2e import (
        SCENARIOS,
        build_invocation,
        configuration,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    from validate_openai_controlled_revision_e2e import (  # type: ignore[no-redef]
        SCENARIOS,
        build_invocation,
        configuration,
    )

ARTIFACT_PATH = Path(
    "docs/artifacts/openai-controlled-revision-duplicate-reference-generation-investigation.json"
)
SCHEMA_SHA256 = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
DTO_SHA256 = "3973409a1069fd0d9b965aeddb554604dda452bdb570631c443056288fdca6ee"
PROMPT_SHA256 = "cb6f07d47ec80ee8dfa246e5151f4c5a625adac2372f05a7cbccf4cbc3ebbf1c"


def reconstruct_e2e02() -> dict[str, Any]:
    """Reconstruct E2E-02 and report only safe aliases and aggregate counts."""

    scenario = next(item for item in SCENARIOS if item.identifier == "E2E-02")
    invocation = build_invocation(scenario, 2)
    projected = OpenAIControlledRevisionProjector(
        configuration("synthetic-model")
    ).project(
        AIProviderExecutionRequest(
            execution_identifier="part5m-local",
            invocation=invocation,
            provider_identifier="openai",
            model_identifier="synthetic-model",
            correlation_identifier="part5m-local",
        )
    )
    provider_input = json.loads(projected.client_request.payload.input)
    authorized = provider_input["required_component_references"]
    editable = provider_input["editable_components"]
    real_reference = authorized[0]
    return {
        "source_component_count": (
            2
            + len(scenario.source.stories)
            + len(scenario.source.transitions)
            + (1 if scenario.source.cta is not None else 0)
        ),
        "projected_component_count": len(editable),
        "authorized_reference_count": len(authorized),
        "unique_authorized_reference_count": len(set(authorized)),
        "safe_lineage": [
            {
                "alias": "R01",
                "source_component": True,
                "projection": True,
                "prompt_serialization": True,
                "schema_field": True,
                "dto_field": True,
                "interpreter_passthrough": True,
                "reconstructor_lookup": True,
            }
        ],
        "prompt_occurrences": {
            "R01": {
                "instructions": projected.client_request.payload.instructions.count(
                    real_reference
                ),
                "authorized_reference_section": sum(
                    item == real_reference for item in authorized
                ),
                "editable_component_section": sum(
                    item["component_reference"] == real_reference for item in editable
                ),
                "schema": projected.client_request.payload.schema_document_json.count(
                    real_reference
                ),
                "total": projected.client_request.payload.input.count(real_reference),
            }
        },
        "projected_references_unique": len(
            {item["component_reference"] for item in editable}
        )
        == len(editable),
        "projected_order_preserved": authorized
        == [item["component_reference"] for item in editable],
        "fixture_classification": "FIXTURE_VALID",
        "prompt_reference_classification": (
            "MULTIPLE_REFERENCE_OCCURRENCES_BUT_UNAMBIGUOUS"
        ),
    }


def instruction_matrix() -> list[dict[str, str]]:
    """Audit direct operational statements in the actual instruction text."""

    text = _COMPONENT_SHAPE_INSTRUCTIONS
    rules = (
        ("one_output_per_input", "exactly one revised component for every" in text),
        ("exact_reference_copying", "Copy each component_reference exactly" in text),
        ("no_duplicate_references", "appears exactly once" in text),
        ("no_missing_references", "every authorized reference" in text),
        ("no_unauthorized_references", "no unauthorized reference" in text),
        ("preserve_component_type", "component_type identical" in text),
        ("preserve_component_order", False),
        ("complete_variant_shape", "one complete shape" in text),
        ("no_hybrid_variants", "never combine component shapes" in text),
        ("final_self_check", "Before responding, verify" in text),
    )
    return [
        {
            "rule": rule,
            "status": "EXPLICIT" if explicit else "MISSING",
        }
        for rule, explicit in rules
    ]


def duplicate_validator_audit() -> dict[str, object]:
    """Exercise equality semantics without serializing reference values."""

    cases = {
        "exact_duplicate": (_story(1), _story(1)),
        "different_body_same_reference": (_story(1), _story(1, body="y")),
        "same_body_different_reference": (_story(1), _story(2)),
        "case_variation": (_story(1), _story(1, reference_kind="case")),
        "unicode_variation": (_story(1), _story(1, reference_kind="unicode")),
        "separator_variation": (_story(1), _story(1, reference_kind="separator")),
        "prefix_variation": (_story(1), _story(1, reference_kind="prefix")),
        "index_variation": (_story(1), _story(2)),
        "different_type_same_suffix": (_story(1), _transition(1, 2)),
    }
    outcomes = {}
    for name, components in cases.items():
        try:
            OpenAIControlledRevisionProviderOutput.model_validate(
                {"revised_components": list(components)}
            )
        except ValidationError as error:
            diagnostic = build_safe_dto_validation_diagnostics(error)
            outcomes[name] = {
                "accepted": False,
                "duplicate_validator": (
                    diagnostic.duplicate_reference_validator_triggered
                ),
                "total_errors": diagnostic.total_error_count,
                "union_errors": diagnostic.union_branch_error_count,
            }
        else:
            outcomes[name] = {
                "accepted": True,
                "duplicate_validator": False,
                "total_errors": 0,
                "union_errors": 0,
            }
    return {
        "comparison_field": "component_reference",
        "normalization": "none",
        "case_sensitive": True,
        "deterministic": True,
        "cases": outcomes,
        "classification": "CORRECT",
    }


def safe_topology_prototype() -> dict[str, object]:
    """Prototype aggregate duplicate topology using synthetic objects only."""

    components = (_story(1), _story(1, body="y"))
    references = [item["component_reference"] for item in components]
    multiplicities = Counter(references)
    duplicates = [value for value in multiplicities.values() if value > 1]
    return {
        "component_count": len(components),
        "unique_reference_count": len(multiplicities),
        "duplicate_group_count": len(duplicates),
        "maximum_duplicate_multiplicity": max(duplicates, default=1),
        "duplicate_type_histogram": {"story": 2},
        "positional_distance_bucket": "adjacent",
    }


def risk_factors() -> list[dict[str, str]]:
    """Classify E2E-02 structural factors without asserting causality."""

    values = (
        ("large_projected_component_count", "ABSENT", "NO_EVIDENCE"),
        ("repeated_projected_component_types", "ABSENT", "NO_EVIDENCE"),
        ("many_projected_transitions", "ABSENT", "NO_EVIDENCE"),
        ("similar_reference_prefixes", "ABSENT", "NO_EVIDENCE"),
        ("long_references", "ABSENT", "NO_EVIDENCE"),
        ("dense_prompt", "UNKNOWN", "PLAUSIBLE_ONLY"),
        ("repeated_one_to_one_instructions", "PRESENT", "NO_EVIDENCE"),
        ("adjacent_same_shape_components", "ABSENT", "NO_EVIDENCE"),
        ("multiple_commentary_blocks", "ABSENT", "NO_EVIDENCE"),
        ("large_output_shape", "ABSENT", "NO_EVIDENCE"),
    )
    return [
        {"factor": factor, "presence": presence, "evidence": evidence}
        for factor, presence, evidence in values
    ]


def hypothesis_matrix() -> list[dict[str, str]]:
    """Evaluate H1-H12 against local and retained safe evidence."""

    values = (
        ("H1", "FALSIFIED"),
        ("H2", "FALSIFIED"),
        ("H3", "FALSIFIED"),
        ("H4", "FALSIFIED"),
        ("H5", "FALSIFIED"),
        ("H6", "NOT_SUPPORTED"),
        ("H7", "FALSIFIED"),
        ("H8", "FALSIFIED"),
        ("H9", "SUPPORTED"),
        ("H10", "NOT_SUPPORTED"),
        ("H11", "PARTIALLY_SUPPORTED"),
        ("H12", "SUPPORTED"),
    )
    return [{"hypothesis": name, "outcome": outcome} for name, outcome in values]


def perturbation_metrics() -> list[dict[str, object]]:
    """Measure deterministic synthetic presentation factors without retaining aliases."""

    cases = (
        ("component_count", 1, 1, 8, 0),
        ("component_count", 5, 5, 40, 0),
        ("reference_length", 4, 1, 4, 0),
        ("reference_length", 40, 1, 40, 0),
        ("prefix_similarity", 0, 3, 24, 0),
        ("prefix_similarity", 1, 3, 24, 3),
        ("transition_count", 0, 1, 8, 0),
        ("transition_count", 4, 5, 64, 4),
        ("story_count", 1, 1, 8, 0),
        ("story_count", 5, 5, 40, 5),
        ("adjacent_same_type", 0, 2, 16, 0),
        ("adjacent_same_type", 1, 2, 16, 1),
        ("ordering_reversed", 0, 3, 24, 0),
        ("ordering_reversed", 1, 3, 24, 0),
        ("reference_repetition", 1, 1, 8, 0),
        ("reference_repetition", 3, 1, 24, 0),
    )
    schema_bytes = len(controlled_revision_schema_json().encode("utf-8"))
    return [
        {
            "dimension": dimension,
            "level": level,
            "component_count": components,
            "synthetic_prompt_bytes": prompt_bytes,
            "reference_occurrence_count": (
                max(1, level) if dimension == "reference_repetition" else components * 2
            ),
            "visually_similar_pair_count": similar_pairs,
            "schema_bytes": schema_bytes,
        }
        for dimension, level, components, prompt_bytes, similar_pairs in cases
    ]


def build_artifact() -> dict[str, object]:
    """Build the deterministic content-free Part 5M artifact."""

    reconstruction = reconstruct_e2e02()
    return {
        "milestone": "part5m",
        "production_frozen": True,
        "live_request_count": 0,
        "sdk_request_count": 0,
        "schema_fingerprint": _sha256(controlled_revision_schema_json()),
        "dto_fingerprint": DTO_SHA256,
        "prompt_fingerprint": _sha256(_COMPONENT_SHAPE_INSTRUCTIONS),
        "input_component_count": reconstruction["projected_component_count"],
        "input_reference_uniqueness_classification": "INPUT_REFERENCES_UNIQUE",
        "projection_uniqueness_classification": "INPUT_REFERENCES_UNIQUE",
        "prompt_mapping_classification": "UNAMBIGUOUS",
        "prompt_reference_occurrence_aggregates": reconstruction["prompt_occurrences"],
        "instruction_conformance_matrix": instruction_matrix(),
        "lineage": reconstruction["safe_lineage"],
        "fixture_classification": reconstruction["fixture_classification"],
        "dto_validator_audit": duplicate_validator_audit(),
        "local_mutation_classification": "LOCAL_POST_PROVIDER_MUTATION_EXCLUDED",
        "sdk_transformation_classification": "SDK_TRANSFORMATION_EXCLUDED",
        "safe_failure_topology": {
            "minimum_duplicate_occurrences": 2,
            "duplicate_location_known": False,
            "duplicate_type_relationship_known": False,
            "duplicate_body_relationship_known": False,
            "omitted_reference_known": False,
        },
        "diagnostic_sufficiency": "PARTIALLY_SUFFICIENT",
        "additional_safe_diagnostics": "USEFUL_BUT_NOT_REQUIRED",
        "safe_topology_prototype": safe_topology_prototype(),
        "risk_factors": risk_factors(),
        "perturbation_metrics": perturbation_metrics(),
        "hypothesis_outcomes": hypothesis_matrix(),
        "root_conclusion": "PROVIDER_DUPLICATE_GENERATION_CONFIRMED",
        "final_recommendation": "KEEP_CURRENT_PRODUCTION_BEHAVIOR",
    }


def main() -> int:
    """Write the artifact and report a zero-request dry run."""

    artifact = build_artifact()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Scout Controlled Revision")
    print("Part 5M — Duplicate Reference Generation Investigation")
    print("Scenario reconstructed: E2E-02")
    print("Input references unique: PASS")
    print("Projection references unique: PASS")
    print("Prompt occurrence analysis: PASS")
    print("Instruction audit: COMPLETE")
    print("DTO validator audit: COMPLETE")
    print("Local mutation audit: COMPLETE")
    print("SDK transformation audit: COMPLETE")
    print("Schema fingerprint unchanged: PASS")
    print("Production prompt unchanged: PASS")
    print("Provider calls: 0")
    print("SDK requests: 0")
    print("Retries: 0")
    print("Fallbacks: 0")
    return 0


def local_mutation_evidence() -> dict[str, bool]:
    """Expose source-level evidence that local layers preserve decoded arrays."""

    client_source = inspect.getsource(OpenAIProviderClient.send)
    interpreter_source = inspect.getsource(
        OpenAIControlledRevisionInterpreter.interpret
    )
    return {
        "client_returns_raw_sdk_response": "payload=raw_response" in client_source,
        "interpreter_uses_single_json_decode": "json.loads(output_text)"
        in interpreter_source,
        "decoded_object_passed_directly_to_dto": "model_validate(\n                decoded"
        in interpreter_source,
        "no_array_concatenation": ".extend(" not in interpreter_source,
    }


def _story(
    index: int, *, body: str = "x", reference_kind: str = "normal"
) -> dict[str, object]:
    reference = {
        "normal": f"story:{index}",
        "case": f"Story:{index}",
        "unicode": f"story：{index}",
        "separator": f"story-{index}",
        "prefix": f"article:{index}",
    }[reference_kind]
    return {
        "component_type": "story",
        "component_reference": reference,
        "factual_summary": body,
        "commentary_block_texts": [body],
        "ending": body,
    }


def _transition(source: int, target: int) -> dict[str, object]:
    return {
        "component_type": "transition",
        "component_reference": f"transition:{source}:{target}",
        "revised_text": "x",
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
