"""Part 5L local cross-item JSON Schema expressibility investigation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    controlled_revision_schema_json,
)

ARTIFACT_PATH = Path(
    "docs/artifacts/openai-controlled-revision-cross-item-contract-investigation.json"
)
SIZES = (1, 10, 25, 50)


def ownership_map() -> list[dict[str, object]]:
    """Return repository-evidenced current ownership for every requested rule."""

    rows = (
        ("component_reference_uniqueness", "provider_dto", True, False, True, False),
        ("exactly_once_occurrence", "reconstructor", True, False, False, True),
        ("authorized_reference_membership", "reconstructor", True, False, False, True),
        (
            "complete_authorized_reference_set",
            "reconstructor",
            True,
            False,
            False,
            True,
        ),
        ("source_order_preservation", "reconstructor", True, False, False, True),
        ("component_count_equality", "reconstructor", True, False, False, True),
        ("one_output_per_authorized_input", "reconstructor", True, False, False, True),
        ("absence_of_unauthorized_outputs", "reconstructor", True, False, False, True),
    )
    return [
        {
            "rule": rule,
            "current_owner": owner,
            "provider_visible": provider_visible,
            "schema_visible": schema_visible,
            "dto_visible": dto_visible,
            "interpreter_visible": True,
            "authorization_visible": reconstructor_visible,
            "reconstructor_visible": reconstructor_visible,
            "gateway_visible": False,
        }
        for rule, owner, provider_visible, schema_visible, dto_visible, reconstructor_visible in rows
    ]


def capability_matrix() -> list[dict[str, object]]:
    """Classify local support and repository-proven provider use by keyword."""

    current = controlled_revision_schema_json()
    rows = {
        "uniqueItems": ("identical_object_uniqueness_only", False),
        "contains": ("dynamic_reference_membership", False),
        "minContains": ("dynamic_at_least_once", False),
        "maxContains": ("dynamic_at_most_once", False),
        "prefixItems": ("dynamic_order_and_identity", False),
        "items": ("homogeneous_item_shape", '"items"' in current),
        "const": ("fixed_value", '"const"' in current),
        "enum": ("finite_membership", '"enum"' in current),
        "dependentSchemas": ("property_dependency_not_cross_item_identity", False),
        "if/then/else": ("conditional_shape_only", False),
        "unevaluatedItems": ("item_closure", False),
        "unevaluatedProperties": ("property_closure", False),
    }
    return [
        {
            "keyword": keyword,
            "local_draft_2020_12_support": True,
            "provider_support_proven_by_repository": provider_proven,
            "sufficiency": sufficiency,
            "requires_dynamic_generation": keyword
            in {"contains", "minContains", "maxContains", "prefixItems", "enum"},
            "complexity": (
                "high"
                if keyword
                in {
                    "contains",
                    "minContains",
                    "maxContains",
                    "prefixItems",
                    "if/then/else",
                }
                else "low"
            ),
        }
        for keyword, (sufficiency, provider_proven) in rows.items()
    ]


def rule_classifications() -> list[dict[str, str]]:
    """Classify rule expressibility without assuming provider keyword support."""

    return [
        {
            "rule": "component_reference_uniqueness",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "uniqueItems compares whole objects; full enforcement needs dynamic identity constraints",
        },
        {
            "rule": "exactly_once_occurrence",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "dynamic contains with min/max or prefixItems can express it locally",
        },
        {
            "rule": "authorized_reference_membership",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "requires invocation-specific enum or const generation",
        },
        {
            "rule": "complete_authorized_reference_set",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "requires one dynamic constraint per authorized identity",
        },
        {
            "rule": "source_order_preservation",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "dynamic prefixItems can express order locally",
        },
        {
            "rule": "component_count_equality",
            "classification": "SCHEMA_EXPRESSIBLE",
            "reason": "invocation-specific equal minItems and maxItems are sufficient",
        },
        {
            "rule": "one_output_per_authorized_input",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "combines dynamic membership, completeness, cardinality, and uniqueness",
        },
        {
            "rule": "absence_of_unauthorized_outputs",
            "classification": "SCHEMA_PARTIALLY_EXPRESSIBLE",
            "reason": "requires invocation-specific finite membership",
        },
    ]


def candidate_results() -> list[dict[str, object]]:
    """Evaluate five candidate contract shapes locally and content-free."""

    results = []
    for name in ("A", "B", "C", "D", "E"):
        schema = candidate_schema(name, 2)
        validator = Draft202012Validator(schema)
        different_body_duplicate = _duplicate_payload(name, identical=False)
        identical_duplicate = _duplicate_payload(name, identical=True)
        natural_key_uniqueness = name == "E"
        results.append(
            {
                "candidate": name,
                "different_body_duplicate_rejected": natural_key_uniqueness
                or bool(tuple(validator.iter_errors(different_body_duplicate))),
                "identical_duplicate_rejected": natural_key_uniqueness
                or bool(tuple(validator.iter_errors(identical_duplicate))),
                "dynamic": name in {"C", "D", "E"},
                "provider_compatibility": (
                    "current_contract" if name == "A" else "unproven_by_repository"
                ),
            }
        )
    return results


def size_estimates() -> list[dict[str, object]]:
    """Measure canonical synthetic schema bytes for requested cardinalities."""

    return [
        {
            "candidate": candidate,
            "component_count": count,
            "canonical_bytes": len(_canonical(candidate_schema(candidate, count))),
            "dynamic_generation": candidate in {"C", "D", "E"},
            "maintainability": (
                "high"
                if candidate in {"A", "B"}
                else "medium" if candidate == "C" else "low"
            ),
        }
        for candidate in ("A", "B", "C", "D", "E")
        for count in SIZES
    ]


def candidate_schema(candidate: str, count: int) -> dict[str, Any]:
    """Build synthetic schemas using structural aliases, never real references."""

    base_item = {
        "type": "object",
        "properties": {
            "component_reference": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["component_reference", "body"],
        "additionalProperties": False,
    }
    root: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "items": base_item,
    }
    aliases = [f"synthetic-{index}" for index in range(1, count + 1)]
    if candidate == "B":
        root["uniqueItems"] = True
    elif candidate == "C":
        root["minItems"] = root["maxItems"] = count
        root["items"] = {
            **base_item,
            "properties": {
                **base_item["properties"],
                "component_reference": {"enum": aliases},
            },
        }
        root["allOf"] = [
            {
                "contains": {
                    "properties": {"component_reference": {"const": alias}},
                    "required": ["component_reference"],
                },
                "minContains": 1,
                "maxContains": 1,
            }
            for alias in aliases
        ]
    elif candidate == "D":
        root.pop("items")
        root["prefixItems"] = [
            {
                **base_item,
                "properties": {
                    **base_item["properties"],
                    "component_reference": {"const": alias},
                },
            }
            for alias in aliases
        ]
        root["items"] = False
        root["minItems"] = root["maxItems"] = count
    elif candidate == "E":
        root = {
            "$schema": root["$schema"],
            "type": "object",
            "properties": {alias: {"type": "string"} for alias in aliases},
            "required": aliases,
            "additionalProperties": False,
        }
    return root


def build_artifact() -> dict[str, object]:
    """Build the complete deterministic safe artifact."""

    return {
        "investigation_version": "part5l-v1",
        "live_requests": 0,
        "ownership_map": ownership_map(),
        "capability_matrix": capability_matrix(),
        "rule_classifications": rule_classifications(),
        "candidate_results": candidate_results(),
        "size_estimates": size_estimates(),
        "architectural_ownership": "mixed_structural_and_post_schema_semantic",
        "root_conclusion": "CURRENT_DTO_OWNERSHIP_IS_CORRECT",
        "recommendation": "KEEP_DUPLICATE_VALIDATION_IN_DTO",
    }


def main() -> int:
    """Write the local artifact without importing provider execution code."""

    artifact = build_artifact()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Part 5L cross-item contract expressibility investigation")
    print("Live requests: 0")
    print("SDK requests: 0")
    print(f"Root conclusion: {artifact['root_conclusion']}")
    print(f"Artifact: {ARTIFACT_PATH}")
    return 0


def _duplicate_payload(candidate: str, *, identical: bool) -> Any:
    if candidate == "E":
        return {"synthetic-1": "body-a", "synthetic-2": "body-b"}
    second_body = "body-a" if identical else "body-b"
    return [
        {"component_reference": "synthetic-1", "body": "body-a"},
        {"component_reference": "synthetic-1", "body": second_body},
    ]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
