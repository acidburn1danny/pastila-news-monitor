"""Static schema/DTO compatibility matrix for Part 5F."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter.openai.interpreter import (
    OpenAIProviderOutputValidationFailure,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
    controlled_revision_schema_json,
)
from scripts.validate_openai_controlled_revision_e2e import SafeInterpreterRecorder


def _story(reference: str = "story:101") -> dict[str, object]:
    return {
        "component_type": "story",
        "component_reference": reference,
        "factual_summary": "Rezumat sintetic.",
        "commentary_block_texts": ["Comentariu sintetic."],
        "ending": "Final sintetic.",
    }


def _payload(*components: dict[str, object]) -> dict[str, object]:
    return {"revised_components": list(components or (_story(),))}


def test_d01_perfect_provider_dto_payload_passes() -> None:
    assert OpenAIControlledRevisionProviderOutput.model_validate(_payload())


def test_d02_missing_required_field_fails() -> None:
    value = _story()
    value.pop("ending")
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_d03_extra_field_fails() -> None:
    value = _story()
    value["extra"] = "not allowed"
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_d04_wrong_component_enum_fails() -> None:
    value = _story()
    value["component_type"] = "article"
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_d05_wrong_field_type_fails() -> None:
    value = _story()
    value["commentary_block_texts"] = "not-an-array"
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_d06_no_provider_dto_field_is_nullable() -> None:
    value = _story()
    for field in tuple(value):
        candidate = dict(value)
        candidate[field] = None
        with pytest.raises(ValidationError):
            OpenAIControlledRevisionProviderOutput.model_validate(_payload(candidate))


def test_d07_null_required_top_level_field_fails() -> None:
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {"revised_components": None}
        )


def test_d08_empty_reference_list_fails() -> None:
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {"revised_components": []}
        )


def test_d09_duplicate_references_are_dto_rejected() -> None:
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            _payload(_story(), _story())
        )


def test_d10_unknown_but_well_shaped_reference_is_dto_valid() -> None:
    value = OpenAIControlledRevisionProviderOutput.model_validate(
        _payload(_story("story:999"))
    )
    assert value.revised_components[0].component_reference == "story:999"


def test_d11_additional_provider_metadata_fails() -> None:
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {**_payload(), "provider_metadata": {"safe": True}}
        )


def test_d12_alternative_component_order_is_dto_valid() -> None:
    first = _story("story:101")
    second = _story("story:102")
    value = OpenAIControlledRevisionProviderOutput.model_validate(
        _payload(second, first)
    )
    assert tuple(item.component_reference for item in value.revised_components) == (
        "story:102",
        "story:101",
    )


def test_d13_minimal_valid_text_component_passes() -> None:
    value = {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "x",
    }
    assert OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_d14_maximum_component_count_passes() -> None:
    values = tuple(_story(f"story:{index}") for index in range(1, 51))
    output = OpenAIControlledRevisionProviderOutput.model_validate(_payload(*values))
    assert len(output.revised_components) == 50


def test_d15_malformed_nested_component_fails() -> None:
    value = _story()
    value["commentary_block_texts"] = [{"text": "nested"}]
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(_payload(value))


def test_generated_schema_is_strict_and_matches_dto_field_names() -> None:
    schema = json.loads(controlled_revision_schema_json())
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["revised_components"]
    revised = schema["properties"]["revised_components"]
    assert revised["minItems"] == 1
    assert revised["maxItems"] == 50
    definitions = schema["$defs"]
    expected = {
        "OpenAIRevisedTextComponent": {
            "component_type",
            "component_reference",
            "revised_text",
        },
        "OpenAIRevisedStoryComponent": {
            "component_type",
            "component_reference",
            "factual_summary",
            "commentary_block_texts",
            "ending",
        },
        "OpenAIRevisedCallToActionComponent": {
            "component_type",
            "component_reference",
            "bridge_text",
        },
    }
    for name, fields in expected.items():
        definition = definitions[name]
        branches = definition.get("anyOf", [definition])
        for branch in branches:
            assert branch["additionalProperties"] is False
            assert set(branch["properties"]) == fields
            assert set(branch["required"]) == fields


def test_schema_cannot_express_cross_item_reference_uniqueness() -> None:
    schema = json.loads(controlled_revision_schema_json())
    revised = schema["properties"]["revised_components"]
    assert "uniqueItems" not in revised


def test_harness_recorder_retains_only_existing_safe_metadata() -> None:
    marker = "RAW-PROVIDER-VALUE-MARKER"

    class FailingInterpreter:
        def interpret(self, request, response):
            del request, response
            raise OpenAIProviderOutputValidationFailure(
                "openai_provider_output_schema_invalid",
                (("validation_stage", "provider_dto"), ("error_count", "1")),
            )

    recorder = SafeInterpreterRecorder(FailingInterpreter())
    with pytest.raises(OpenAIProviderOutputValidationFailure):
        recorder.interpret(object(), object())
    assert recorder.entered
    assert not recorder.validated
    assert dict(recorder.safe_metadata) == {
        "validation_stage": "provider_dto",
        "error_count": "1",
    }
    assert marker not in repr(recorder)
