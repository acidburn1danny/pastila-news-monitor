"""Part 5G safe nested DTO validation diagnostic matrix."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    OpenAIControlledRevisionProviderOutput,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.validation_diagnostics import (
    _canonical_error_type,
    build_safe_dto_validation_diagnostics,
)


def _story(reference: str = "story:101") -> dict[str, object]:
    return {
        "component_type": "story",
        "component_reference": reference,
        "factual_summary": "Rezumat sintetic.",
        "commentary_block_texts": ["Comentariu sintetic."],
        "ending": "Final sintetic.",
    }


def _text() -> dict[str, object]:
    return {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "Deschidere sintetică.",
    }


def _cta() -> dict[str, object]:
    return {
        "component_type": "call_to_action",
        "component_reference": "call_to_action",
        "bridge_text": "Punte sintetică.",
    }


def _validate(*components: dict[str, object]):
    return OpenAIControlledRevisionProviderOutput.model_validate(
        {"revised_components": list(components)}
    )


def _diagnostics(*components: dict[str, object]):
    with pytest.raises(ValidationError) as raised:
        _validate(*components)
    return build_safe_dto_validation_diagnostics(raised.value)


@pytest.mark.parametrize("component", (_text(), _story(), _cta()))
def test_g01_g03_valid_component_shapes_emit_no_diagnostics(component) -> None:
    assert _validate(component)


@pytest.mark.parametrize(
    "field", ("factual_summary", "commentary_block_texts", "ending")
)
def test_g04_g06_missing_story_fields_are_primary(field: str) -> None:
    component = _story()
    component.pop(field)
    diagnostic = _diagnostics(component)
    assert diagnostic.probable_primary_failure_category == "missing_required_field"
    assert diagnostic.union_expansion_suspected
    assert diagnostic.union_branch_error_count > 0
    assert any(field in location for location, _ in diagnostic.location_shape_histogram)


def test_g07_wrong_component_literal_is_safely_classified() -> None:
    component = _story()
    component["component_type"] = "unknown"
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["literal_error"] >= 1


@pytest.mark.parametrize(
    ("base", "label"),
    ((_text(), "story"), (_story(), "opening"), (_cta(), "story")),
)
def test_g08_g10_mislabeled_shapes_are_rejected_without_values(base, label) -> None:
    component = dict(base)
    component["component_type"] = label
    diagnostic = _diagnostics(component)
    assert diagnostic.total_error_count > 0
    assert diagnostic.union_expansion_suspected


def test_g11_unknown_nested_field_is_extra_forbidden() -> None:
    component = _story()
    component["UNIQUE-SECRET-FIELD"] = "UNIQUE-SECRET-VALUE"
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["extra_forbidden"] >= 1
    assert any(
        "unknown_field" in location
        for location, _ in diagnostic.location_shape_histogram
    )
    assert "UNIQUE-SECRET" not in repr(diagnostic.safe_metadata())


def test_g12_wrong_nested_primitive_type_is_safe() -> None:
    component = _story()
    component["commentary_block_texts"] = "not-a-list"
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["list_type"] >= 1
    assert diagnostic.probable_primary_failure_category == "invalid_nested_type"


def test_g13_commentary_cardinality_is_safe_constraint() -> None:
    component = _story()
    component["commentary_block_texts"] = ["x"] * 101
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["too_long"] >= 1
    assert diagnostic.probable_primary_failure_category == "constraint_violation"


def test_g14_empty_required_string_is_safe_constraint() -> None:
    component = _story()
    component["ending"] = ""
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["string_too_short"] >= 1


def test_g15_reference_pattern_is_reported_without_value() -> None:
    marker = "story:SECRET-REFERENCE-991"
    component = _story(marker)
    diagnostic = _diagnostics(component)
    assert dict(diagnostic.error_type_histogram)["pattern_mismatch"] >= 1
    assert marker not in repr(diagnostic.safe_metadata())


def test_g16_g25_duplicate_model_validator_is_distinct() -> None:
    diagnostic = _diagnostics(_story(), _story())
    assert diagnostic.duplicate_reference_validator_triggered
    assert diagnostic.model_validator_error_count == 1
    assert (
        diagnostic.probable_primary_failure_category == "duplicate_component_reference"
    )
    assert dict(diagnostic.location_shape_histogram)["model_validator"] == 1


def test_g17_multiple_malformed_components_report_distribution() -> None:
    first = _story("story:101")
    second = _story("story:102")
    first.pop("ending")
    second.pop("factual_summary")
    diagnostic = _diagnostics(first, second)
    assert diagnostic.affected_component_count == 2
    assert diagnostic.multi_component_distribution
    assert not diagnostic.single_component_concentration


def test_g18_one_defect_exposes_union_expansion_without_counting_each_as_primary() -> (
    None
):
    component = _story()
    component.pop("ending")
    diagnostic = _diagnostics(component)
    assert diagnostic.single_component_concentration
    assert diagnostic.union_expansion_suspected
    assert diagnostic.union_branch_error_count >= 1
    assert diagnostic.probable_primary_failure_category == "missing_required_field"


def test_g19_independent_primary_error_categories_remain_visible() -> None:
    component = _story()
    component.pop("ending")
    component["commentary_block_texts"] = "invalid"
    diagnostic = _diagnostics(component)
    histogram = dict(diagnostic.error_type_histogram)
    assert histogram["missing"] >= 1
    assert histogram["list_type"] >= 1


def test_g20_unknown_error_type_has_repository_owned_fallback() -> None:
    assert _canonical_error_type("future_library_error", "unknown_location") == (
        "unknown_validation_error"
    )


def test_g21_g23_inputs_context_messages_and_indexes_never_serialize() -> None:
    markers = (
        "SOURCE-PROSE-MARKER",
        "REVISED-PROSE-MARKER",
        "PROMPT-MARKER",
        "RAW-INPUT-MARKER",
        "RAW-CONTEXT-MARKER",
        "RAW-EXCEPTION-MARKER",
        "REQUEST-ID-MARKER",
        "CREDENTIAL-MARKER",
    )
    component = _story("story:RAW-INPUT-MARKER")
    component["RAW-CONTEXT-MARKER"] = "REVISED-PROSE-MARKER"
    serialized = json.dumps(dict(_diagnostics(component).safe_metadata()))
    assert all(marker not in serialized for marker in markers)
    assert "[0]" not in serialized
    assert ".0" not in serialized
    assert "revised_components[*]" in serialized


def test_g24_component_positions_are_counted_but_never_exposed() -> None:
    first = _story("story:101")
    second = _story("story:102")
    first.pop("ending")
    second.pop("ending")
    diagnostic = _diagnostics(first, second)
    serialized = repr(diagnostic.safe_metadata())
    assert diagnostic.affected_component_count == 2
    assert "revised_components[*]" in serialized
    assert "revised_components.0" not in serialized
    assert "revised_components.1" not in serialized
