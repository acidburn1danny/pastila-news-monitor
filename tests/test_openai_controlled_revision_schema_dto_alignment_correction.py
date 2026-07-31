"""Part 5K targeted schema/DTO reference alignment tests."""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter.openai.models import (
    TEXT_COMPONENT_REFERENCE_RULES,
    OpenAIControlledRevisionProviderOutput,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.projector import (
    _COMPONENT_SHAPE_INSTRUCTIONS,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.validation_diagnostics import (
    build_safe_dto_validation_diagnostics,
)
from scripts.investigate_openai_controlled_revision_contract import differential
from scripts.validate_openai_controlled_revision_e2e import (
    PART5K_OPT_IN,
    configuration,
    main,
)

OLD_SCHEMA_SHA256 = "3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c"
NEW_SCHEMA_SHA256 = "70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556"
PROMPT_SHA256 = "cb6f07d47ec80ee8dfa246e5151f4c5a625adac2372f05a7cbccf4cbc3ebbf1c"


def _text(component_type="opening", reference="opening") -> dict[str, object]:
    return {
        "component_type": component_type,
        "component_reference": reference,
        "revised_text": "x",
    }


def _story(reference="story:101") -> dict[str, object]:
    return {
        "component_type": "story",
        "component_reference": reference,
        "factual_summary": "x",
        "commentary_block_texts": ["x"],
        "ending": "x",
    }


def _cta(reference="call_to_action") -> dict[str, object]:
    return {
        "component_type": "call_to_action",
        "component_reference": reference,
        "bridge_text": "x",
    }


def _wrap(*components: dict[str, object]) -> dict[str, object]:
    return {"revised_components": list(components)}


@pytest.mark.parametrize(
    "component",
    (
        _text(),
        _story(),
        _cta(),
    ),
)
def test_k01_k03_valid_reference_type_pairs_pass_both(component) -> None:
    assert differential(_wrap(component)) == "SCHEMA_PASS_DTO_PASS"


@pytest.mark.parametrize(
    "component",
    (
        _text(reference="story:101"),
        _text(reference="call_to_action"),
        _story(reference="opening"),
        _story(reference="call_to_action"),
        _cta(reference="opening"),
        _cta(reference="story:101"),
    ),
)
def test_k04_k09_cross_category_references_fail_both(component) -> None:
    assert differential(_wrap(component)) == "SCHEMA_FAIL_DTO_FAIL"


def test_k10_invalid_generic_reference_fails_both() -> None:
    assert differential(_wrap(_text(reference="invalid"))) == "SCHEMA_FAIL_DTO_FAIL"


def test_k11_boundary_valid_transition_reference_passes_both() -> None:
    component = _text("transition", "transition:1:1")
    assert differential(_wrap(component)) == "SCHEMA_PASS_DTO_PASS"


def test_k12_boundary_invalid_transition_reference_fails_both() -> None:
    component = _text("transition", "transition:0:1")
    assert differential(_wrap(component)) == "SCHEMA_FAIL_DTO_FAIL"


def test_k13_historical_mismatch_is_now_schema_invalid() -> None:
    assert differential(_wrap(_text(reference="story:101"))) == "SCHEMA_FAIL_DTO_FAIL"


def test_k14_historical_dto_diagnostic_is_unchanged() -> None:
    with pytest.raises(ValidationError) as raised:
        OpenAIControlledRevisionProviderOutput.model_validate(
            _wrap(_text(reference="story:101"))
        )
    value = build_safe_dto_validation_diagnostics(raised.value)
    assert (
        value.total_error_count,
        value.affected_component_count,
        value.top_level_error_count,
        value.nested_error_count,
        value.union_branch_error_count,
        value.probable_primary_failure_category,
    ) == (11, 1, 1, 10, 9, "invalid_component_shape")


@pytest.mark.parametrize("component", (_text(), _story(), _cta()))
def test_k15_k17_valid_variants_remain_unchanged(component) -> None:
    assert differential(_wrap(component)) == "SCHEMA_PASS_DTO_PASS"


def test_k18_additional_properties_remain_forbidden() -> None:
    assert differential(_wrap({**_story(), "extra": "x"})) == "SCHEMA_FAIL_DTO_FAIL"


def test_k19_string_constraints_remain_unchanged() -> None:
    assert differential(_wrap({**_story(), "ending": ""})) == "SCHEMA_FAIL_DTO_FAIL"


def test_k20_array_constraints_remain_unchanged() -> None:
    assert differential(_wrap({**_story(), "commentary_block_texts": []})) == (
        "SCHEMA_PASS_DTO_PASS"
    )
    assert (
        differential(_wrap({**_story(), "commentary_block_texts": ["x"] * 101}))
        == "SCHEMA_FAIL_DTO_FAIL"
    )


def test_k21_root_component_count_remains_one_to_fifty() -> None:
    schema = json.loads(controlled_revision_schema_json())
    revised = schema["properties"]["revised_components"]
    assert (revised["minItems"], revised["maxItems"]) == (1, 50)
    components = [_story(f"story:{index}") for index in range(1, 51)]
    assert differential(_wrap(*components)) == "SCHEMA_PASS_DTO_PASS"


def test_k22_duplicate_reference_behavior_remains_dto_only() -> None:
    assert differential(_wrap(_story(), _story())) == "SCHEMA_PASS_DTO_FAIL"


def test_k23_authorization_remains_post_schema() -> None:
    assert differential(_wrap(_story("story:999"))) == "SCHEMA_PASS_DTO_PASS"


def test_k24_interpreter_still_consumes_the_provider_dto() -> None:
    from pastila_scout.editor.generation.ai_provider_adapter.openai import interpreter

    source = inspect.getsource(
        interpreter.OpenAIControlledRevisionInterpreter.interpret
    )
    assert "OpenAIControlledRevisionProviderOutput.model_validate" in source


def test_k25_reconstructor_behavior_is_unchanged() -> None:
    from pastila_scout.editor.generation.ai_provider_adapter.openai import reconstructor

    assert "reference_matches_type" not in inspect.getsource(reconstructor)


def test_k26_prompt_is_unchanged() -> None:
    assert hashlib.sha256(_COMPONENT_SHAPE_INSTRUCTIONS.encode()).hexdigest() == (
        PROMPT_SHA256
    )


def test_k27_runtime_is_not_imported_by_schema_generation() -> None:
    from pastila_scout.editor.generation.ai_provider_adapter.openai import models

    assert "runtime" not in inspect.getsource(models).casefold()


def test_k28_retry_behavior_is_unchanged() -> None:
    assert configuration("synthetic-model").retry_policy.maximum_attempts == 1


def test_k29_fallback_behavior_is_unchanged() -> None:
    assert not hasattr(configuration("synthetic-model"), "fallback_model")


def test_k30_submitted_schema_uses_all_reference_constraints() -> None:
    schema = json.loads(controlled_revision_schema_json())
    branches = schema["$defs"]["OpenAIRevisedTextComponent"]["anyOf"]
    observed = {
        branch["properties"]["component_type"]["const"]: branch["properties"][
            "component_reference"
        ]
        for branch in branches
    }
    for component_type, rule in TEXT_COMPONENT_REFERENCE_RULES.items():
        assert all(
            observed[component_type][key] == value for key, value in rule.items()
        )


def test_k31_old_fingerprint_is_rejected() -> None:
    assert hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest() != (
        OLD_SCHEMA_SHA256
    )


def test_k32_new_fingerprint_is_stable() -> None:
    assert hashlib.sha256(controlled_revision_schema_json().encode()).hexdigest() == (
        NEW_SCHEMA_SHA256
    )


def test_k33_k34_schema_contains_only_structural_rules_without_sensitive_values() -> (
    None
):
    serialized = controlled_revision_schema_json()
    assert "story:101" not in serialized
    assert "provider_output" not in serialized
    assert "source prose" not in serialized


def test_k35_k40_dry_run_performs_zero_requests(monkeypatch, capsys) -> None:
    monkeypatch.delenv(PART5K_OPT_IN, raising=False)
    for name in (
        "SCOUT_RUN_LIVE_OPENAI_PART5_RESTART",
        "SCOUT_RUN_LIVE_OPENAI_PART5C",
        "SCOUT_RUN_LIVE_OPENAI_PART5D",
        "SCOUT_RUN_LIVE_OPENAI_PART5E",
        "SCOUT_RUN_LIVE_OPENAI_PART5F",
        "SCOUT_RUN_LIVE_OPENAI_PART5G",
        "SCOUT_RUN_LIVE_OPENAI_PART5H",
    ):
        monkeypatch.delenv(name, raising=False)
    assert main() == 0
    output = capsys.readouterr().out
    assert "Corrected schema loaded: PASS" in output
    assert "Live requests: 0" in output
    assert "SDK requests: 0" in output


def test_corrected_schema_is_draft_2020_12_valid() -> None:
    Draft202012Validator.check_schema(json.loads(controlled_revision_schema_json()))
