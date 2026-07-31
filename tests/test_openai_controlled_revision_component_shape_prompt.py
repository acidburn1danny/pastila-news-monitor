"""Part 5H component-shape prompt and frozen-validation checks."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError
from test_controlled_revision_contracts import _invocation

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderConfiguration,
    AIProviderExecutionRequest,
    AIRetryPolicy,
    AIStructuredOutputCapabilities,
    AIStructuredOutputMode,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionProjector,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
    controlled_revision_schema_json,
)

_FROZEN_SCHEMA_SHA256 = (
    "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
)


def _instructions() -> str:
    invocation = _invocation()
    configuration = AIProviderConfiguration(
        provider_identifier="openai",
        model_identifier="synthetic-model",
        endpoint="https://api.openai.invalid/v1",
        authentication_reference="env:OPENAI_API_KEY",
        timeout_seconds=7,
        retry_policy=AIRetryPolicy(maximum_attempts=1),
        structured_output=AIStructuredOutputCapabilities(
            supported_modes=(AIStructuredOutputMode.SCHEMA_CONSTRAINED,)
        ),
        maximum_context_tokens=32_000,
    )
    request = AIProviderExecutionRequest(
        execution_identifier="execution-1",
        invocation=invocation,
        provider_identifier="openai",
        model_identifier="synthetic-model",
        correlation_identifier="correlation-1",
    )
    projected = OpenAIControlledRevisionProjector(configuration).project(request)
    return projected.client_request.payload.instructions


def _story(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "component_type": "story",
        "component_reference": "story:101",
        "factual_summary": "Rezumat sintetic.",
        "commentary_block_texts": ["Comentariu sintetic."],
        "ending": "Final sintetic.",
    }
    value.update(updates)
    return value


def _text(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "Deschidere sintetică.",
    }
    value.update(updates)
    return value


def _cta(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "component_type": "call_to_action",
        "component_reference": "call_to_action",
        "bridge_text": "Punte sintetică.",
    }
    value.update(updates)
    return value


def _validate(*components: dict[str, object]) -> None:
    OpenAIControlledRevisionProviderOutput.model_validate(
        {"revised_components": list(components)}
    )


def test_h01_exact_reference_copying_is_explicit() -> None:
    text = _instructions()
    assert "Copy each component_reference exactly" in text
    assert "do not translate, normalize, shorten, modify, or invent it" in text


def test_h02_one_output_per_authorized_reference_is_explicit() -> None:
    assert "exactly one revised component for every authorized" in _instructions()


def test_h03_unauthorized_references_are_prohibited() -> None:
    assert "no unauthorized references" in _instructions()


def test_h04_source_component_type_is_preserved() -> None:
    assert "component_type identical to its source component" in _instructions()


def test_h05_text_shape_uses_actual_dto_fields() -> None:
    text = _instructions()
    assert "Text components (opening, transition, or closing)" in text
    assert "component_reference, and revised_text" in text


def test_h06_story_shape_uses_actual_dto_fields() -> None:
    assert "factual_summary, commentary_block_texts, and ending" in _instructions()


def test_h07_cta_shape_uses_actual_dto_fields() -> None:
    text = _instructions()
    assert "Call-to-action components" in text
    assert "component_reference, and bridge_text" in text


def test_h08_hybrid_components_are_prohibited() -> None:
    assert "never combine component shapes" in _instructions()


def test_h09_all_required_fields_are_required() -> None:
    assert "Include every required field" in _instructions()


def test_h10_foreign_variant_fields_are_prohibited() -> None:
    assert "no fields belonging to another component type" in _instructions()


def test_h11_completion_self_check_is_present() -> None:
    text = _instructions()
    assert "Before responding, verify" in text
    assert "appears exactly once" in text
    assert "every object has one complete shape" in text


def test_h12_generated_schema_is_unchanged() -> None:
    digest = hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest()
    assert digest == _FROZEN_SCHEMA_SHA256


def test_h13_dto_accepts_all_three_frozen_variants() -> None:
    _validate(_text(), _story(), _cta())


def test_h14_existing_editorial_instructions_remain_present() -> None:
    text = _instructions()
    assert "Preserve factual content and source language" in text
    assert "Revise only the declared editable component references" in text
    assert "Do not add unsupported facts" in text
    assert "untrusted data" in text


def test_h15_instruction_is_generic_and_not_scenario_specific() -> None:
    text = _instructions()
    assert "E2E-" not in text
    assert "Substantial Rewrite" not in text
    assert "story:101" not in text


@pytest.mark.parametrize("component", (_text(), _story(), _cta()))
def test_m01_m03_valid_component_shapes_pass(component) -> None:
    _validate(component)


@pytest.mark.parametrize(
    "component",
    (
        _story(component_type="opening"),
        _text(component_type="story"),
        {key: value for key, value in _story().items() if key != "ending"},
        _story(revised_text="foreign"),
        _text(factual_summary="foreign", ending="foreign"),
        _cta(revised_text="foreign"),
        _text(component_reference="unknown"),
        _story(extra_field="foreign"),
    ),
)
def test_m04_m10_m12_malformed_component_shapes_still_fail(component) -> None:
    with pytest.raises(ValidationError):
        _validate(component)


def test_m11_duplicate_reference_validation_is_unchanged() -> None:
    with pytest.raises(ValidationError):
        _validate(_story(), _story())
