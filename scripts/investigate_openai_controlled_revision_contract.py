"""Static, content-free Part 5J contract conformance investigation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

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

ARTIFACT_PATH = Path(
    "docs/artifacts/openai-controlled-revision-contract-conformance.json"
)
OLD_SCHEMA_SHA256 = "3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c"
SCHEMA_SHA256 = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
DTO_SHA256 = "3973409a1069fd0d9b965aeddb554604dda452bdb570631c443056288fdca6ee"
LIVE_SIGNATURE = (11, 1, 10, 9, 0, False, "invalid_component_shape", 1)


@dataclass(frozen=True, slots=True)
class SafeSignature:
    total_errors: int
    top_level_errors: int
    nested_errors: int
    union_errors: int
    model_validator_errors: int
    duplicate_validator: bool
    primary_category: str
    affected_components: int

    def tuple(self) -> tuple[object, ...]:
        return tuple(asdict(self).values())


def schema_document() -> dict[str, Any]:
    """Return a fresh copy of the exact submitted schema."""

    return json.loads(controlled_revision_schema_json())


def schema_accepts(payload: dict[str, object]) -> bool:
    """Validate against the exact Draft 2020-12-compatible provider schema."""

    return not tuple(Draft202012Validator(schema_document()).iter_errors(payload))


def dto_accepts(payload: dict[str, object]) -> bool:
    """Validate against the frozen provider DTO."""

    try:
        OpenAIControlledRevisionProviderOutput.model_validate(payload)
    except ValidationError:
        return False
    return True


def differential(payload: dict[str, object]) -> str:
    """Classify schema and DTO acceptance independently."""

    schema = schema_accepts(payload)
    dto = dto_accepts(payload)
    return f"SCHEMA_{'PASS' if schema else 'FAIL'}_DTO_{'PASS' if dto else 'FAIL'}"


def safe_signature(payload: dict[str, object]) -> SafeSignature | None:
    """Return content-free diagnostics, or None for DTO-valid payloads."""

    try:
        OpenAIControlledRevisionProviderOutput.model_validate(payload)
    except ValidationError as error:
        value = build_safe_dto_validation_diagnostics(error)
        return SafeSignature(
            value.total_error_count,
            value.top_level_error_count,
            value.nested_error_count,
            value.union_branch_error_count,
            value.model_validator_error_count,
            value.duplicate_reference_validator_triggered,
            value.probable_primary_failure_category,
            value.affected_component_count,
        )
    return None


def synthetic_cases() -> dict[str, dict[str, object]]:
    """Build deterministic synthetic structural cases without editorial content."""

    text = _text()
    story = _story()
    cta = _cta()
    return {
        "J01_missing_required_body": _wrap(_without(story, "ending")),
        "J02_wrong_body_field": _wrap(
            _without({**cta, "revised_text": "x"}, "bridge_text")
        ),
        "J03_text_type_story_body": _wrap({**story, "component_type": "opening"}),
        "J04_story_type_text_body": _wrap({**text, "component_type": "story"}),
        "J05_cta_type_text_body": _wrap({**text, "component_type": "call_to_action"}),
        "J06_valid_plus_foreign": _wrap({**story, "revised_text": "x"}),
        "J07_empty_required": _wrap({**story, "ending": ""}),
        "J08_too_short_required": _wrap({**text, "revised_text": ""}),
        "J09_empty_commentary": _wrap({**story, "commentary_block_texts": []}),
        "J10_empty_commentary_item": _wrap({**story, "commentary_block_texts": [""]}),
        "J11_null_required": _wrap({**story, "ending": None}),
        "J12_missing_component_type": _wrap(_without(story, "component_type")),
        "J13_unknown_component_type": _wrap({**story, "component_type": "unknown"}),
        "J14_text_reference_validator": _wrap(
            {**text, "component_reference": "story:101"}
        ),
        "J15_duplicate_reference": _wrap(story, dict(story)),
    }


def differential_cases() -> dict[str, tuple[dict[str, object], str | None]]:
    """Return D01-D20 payloads and post-schema ownership where applicable."""

    story = _story()
    text = _text()
    cta = _cta()
    return {
        "D01_valid_text": (_wrap(text), None),
        "D02_valid_story": (_wrap(story), None),
        "D03_valid_cta": (_wrap(cta), None),
        "D04_story_missing_ending": (_wrap(_without(story, "ending")), None),
        "D05_story_with_revised_text": (_wrap({**story, "revised_text": "x"}), None),
        "D06_text_with_story_fields": (
            _wrap({**text, "factual_summary": "x", "ending": "x"}),
            None,
        ),
        "D07_cta_wrong_body": (
            _wrap(_without({**cta, "revised_text": "x"}, "bridge_text")),
            None,
        ),
        "D08_empty_factual_summary": (_wrap({**story, "factual_summary": ""}), None),
        "D09_empty_ending": (_wrap({**story, "ending": ""}), None),
        "D10_empty_commentary": (_wrap({**story, "commentary_block_texts": []}), None),
        "D11_empty_commentary_item": (
            _wrap({**story, "commentary_block_texts": [""]}),
            None,
        ),
        "D12_null_body": (_wrap({**story, "ending": None}), None),
        "D13_unknown_type": (_wrap({**story, "component_type": "unknown"}), None),
        "D14_missing_type": (_wrap(_without(story, "component_type")), None),
        "D15_extra_field": (_wrap({**story, "unknown_field": "x"}), None),
        "D16_duplicate_references": (_wrap(story, dict(story)), "DTO_MODEL_VALIDATION"),
        "D17_source_type_mismatch": (
            _wrap({**text, "component_reference": "story:101"}),
            "DTO_MODEL_VALIDATION",
        ),
        "D18_wrong_order": (_wrap(cta, story), "POST_SCHEMA_SEMANTIC_CONTRACT"),
        "D19_missing_authorized": (_wrap(story), "POST_SCHEMA_SEMANTIC_CONTRACT"),
        "D20_additional_unauthorized": (
            _wrap(story, cta),
            "POST_SCHEMA_SEMANTIC_CONTRACT",
        ),
    }


def contract_inventory() -> dict[str, object]:
    """Create the content-free field-level inventory from the submitted schema."""

    schema = schema_document()
    variants = {}
    for name, definition in sorted(schema["$defs"].items()):
        branch = definition.get("anyOf", [definition])[0]
        fields = {}
        required = set(branch["required"])
        for field, definition in sorted(branch["properties"].items()):
            fields[field] = {
                "required": field in required,
                "type": definition.get("type"),
                "literal": definition.get("const") or definition.get("enum"),
                "minimum_length": definition.get("minLength"),
                "maximum_length": definition.get("maxLength"),
                "minimum_items": definition.get("minItems"),
                "maximum_items": definition.get("maxItems"),
                "pattern_present": "pattern" in definition,
            }
        variants[name] = {
            "fields": fields,
            "additional_properties": branch["additionalProperties"],
            "custom_validator": (
                "reference_matches_type"
                if name == "OpenAIRevisedTextComponent"
                else None
            ),
        }
    return {
        "root_required": schema["required"],
        "root_additional_properties": schema["additionalProperties"],
        "minimum_components": schema["properties"]["revised_components"]["minItems"],
        "maximum_components": schema["properties"]["revised_components"]["maxItems"],
        "union_keyword": "anyOf",
        "discriminator": None,
        "branch_order": list(schema["$defs"]),
        "variants": variants,
        "root_custom_validator": "unique_references",
    }


def conformance_matrix() -> list[dict[str, object]]:
    """Map field and semantic-rule ownership across frozen contract layers."""

    variants = {
        "text": ("component_type", "component_reference", "revised_text"),
        "story": (
            "component_type",
            "component_reference",
            "factual_summary",
            "commentary_block_texts",
            "ending",
        ),
        "cta": ("component_type", "component_reference", "bridge_text"),
    }
    rows = [
        {
            "variant": variant,
            "field": field,
            "provider_instruction": "required",
            "schema_status": "required",
            "dto_status": "required",
            "validator_status": "field_validation",
            "interpreter_use": "dto_validation",
            "reconstructor_use": "read",
            "classification": "ALIGNED",
        }
        for variant, fields in variants.items()
        for field in fields
    ]
    rows.extend(
        (
            {
                "variant": "text",
                "field": "reference_to_type_correspondence",
                "provider_instruction": "required",
                "schema_status": "not_expressed",
                "dto_status": "required",
                "validator_status": "reference_matches_type",
                "interpreter_use": "dto_validation",
                "reconstructor_use": "dispatch_and_lookup",
                "classification": "DTO_VALIDATOR_ONLY_RULE",
            },
            {
                "variant": "root",
                "field": "reference_uniqueness",
                "provider_instruction": "required",
                "schema_status": "not_expressed",
                "dto_status": "required",
                "validator_status": "unique_references",
                "interpreter_use": "dto_validation",
                "reconstructor_use": "not_applicable",
                "classification": "DTO_VALIDATOR_ONLY_RULE",
            },
            {
                "variant": "root",
                "field": "authorized_reference_exact_set",
                "provider_instruction": "required",
                "schema_status": "not_expressed",
                "dto_status": "not_expressed",
                "validator_status": "not_applicable",
                "interpreter_use": "reconstructor_delegation",
                "reconstructor_use": "required",
                "classification": "RECONSTRUCTOR_ONLY_EXPECTATION",
            },
        )
    )
    return rows


def build_artifact() -> dict[str, object]:
    """Build the deterministic safe investigation artifact."""

    signatures = {}
    exact = []
    for name, payload in synthetic_cases().items():
        signature = safe_signature(payload)
        signatures[name] = asdict(signature) if signature else None
        if signature and signature.tuple() == LIVE_SIGNATURE:
            exact.append(name)
    differentials = {
        name: {
            "classification": differential(payload),
            "downstream_owner": owner,
        }
        for name, (payload, owner) in differential_cases().items()
    }
    schema = controlled_revision_schema_json()
    dto_schema = json.dumps(
        OpenAIControlledRevisionProviderOutput.model_json_schema(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "investigation_version": "part5j-v1",
        "schema_sha256": _sha256(schema),
        "previous_schema_sha256": OLD_SCHEMA_SHA256,
        "dto_sha256": _sha256(dto_schema),
        "prompt_contract_sha256": _sha256(_COMPONENT_SHAPE_INSTRUCTIONS),
        "inventory": contract_inventory(),
        "conformance_matrix": conformance_matrix(),
        "synthetic_signatures": signatures,
        "exact_live_signature_matches": exact,
        "differential_cases": differentials,
        "post_schema_rules": [
            "authorized_reference_membership",
            "complete_authorized_reference_set",
            "source_type_preservation",
            "source_order_preservation",
            "story_commentary_cardinality_matches_source",
        ],
    }


def main() -> int:
    """Write the deterministic artifact without network or SDK activity."""

    artifact = build_artifact()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Part 5J contract conformance investigation")
    print("Live requests: 0")
    print(
        f"Schema fingerprint: {'PASS' if artifact['schema_sha256'] == SCHEMA_SHA256 else 'FAIL'}"
    )
    print(
        f"DTO fingerprint: {'PASS' if artifact['dto_sha256'] == DTO_SHA256 else 'FAIL'}"
    )
    print(f"Exact signature matches: {len(artifact['exact_live_signature_matches'])}")
    print(f"Artifact: {ARTIFACT_PATH}")
    return 0


def _text() -> dict[str, object]:
    return {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "x",
    }


def _story() -> dict[str, object]:
    return {
        "component_type": "story",
        "component_reference": "story:101",
        "factual_summary": "x",
        "commentary_block_texts": ["x"],
        "ending": "x",
    }


def _cta() -> dict[str, object]:
    return {
        "component_type": "call_to_action",
        "component_reference": "call_to_action",
        "bridge_text": "x",
    }


def _wrap(*components: dict[str, object]) -> dict[str, object]:
    return {"revised_components": list(components)}


def _without(value: dict[str, object], field: str) -> dict[str, object]:
    return {key: item for key, item in value.items() if key != field}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
