"""Permanent Part 5A divergence regressions for the corrected provider DTO."""

import json

import pytest
from pydantic import ValidationError
from test_controlled_revision_contracts import _invocation

from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionProviderOutput,
    OpenAIControlledRevisionReconstructor,
    OpenAIReconstructionError,
    controlled_revision_schema_json,
)
from pastila_scout.editor.generation.models import derive_assembled_text


def _opening_patch(text="Deschidere revizuită cu diacritice românești."):
    return OpenAIControlledRevisionProviderOutput.model_validate(
        {
            "revised_components": [
                {
                    "component_type": "opening",
                    "component_reference": "opening",
                    "revised_text": text,
                }
            ]
        }
    )


def test_provider_schema_exposes_only_provider_owned_patch_fields():
    schema_text = controlled_revision_schema_json()
    schema = json.loads(schema_text)
    assert schema["required"] == ["revised_components"]
    assert schema["additionalProperties"] is False
    for forbidden in (
        "episode_id",
        "assembled_text",
        "teleprompter_text",
        "source_draft_fingerprint",
        "preservation_fingerprint",
        "contract_version",
        "gateway_result_fingerprint",
    ):
        assert forbidden not in schema_text


def test_unknown_fields_and_provider_authored_domain_state_are_rejected():
    with pytest.raises(ValidationError):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {
                "revised_components": [
                    {
                        "component_type": "opening",
                        "component_reference": "opening",
                        "revised_text": "Text revizuit.",
                    }
                ],
                "episode_id": "provider-owned",
            }
        )


@pytest.mark.parametrize(
    "forbidden_field",
    (
        "episode_id",
        "story_id",
        "component_id",
        "position",
        "from_story_id",
        "to_story_id",
        "assembled_text",
        "teleprompter_text",
        "source_draft_fingerprint",
        "preservation_fingerprint",
        "output_contract_fingerprint",
        "contract_version",
        "gateway_result_fingerprint",
        "result_fingerprint",
        "protected_content",
        "revision_scope",
    ),
)
def test_authoritative_derived_and_protected_fields_cannot_cross_dto(forbidden_field):
    component = {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "Text editorial autorizat.",
        forbidden_field: "valoare interzisă",
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {"revised_components": [component]}
        )


def test_duplicate_component_references_are_rejected_structurally():
    component = {
        "component_type": "opening",
        "component_reference": "opening",
        "revised_text": "Text revizuit.",
    }
    with pytest.raises(ValidationError, match="duplicates"):
        OpenAIControlledRevisionProviderOutput.model_validate(
            {"revised_components": [component, component]}
        )


def test_r01_and_r02_derived_text_is_computed_from_unicode_content():
    invocation = _invocation()
    revised = OpenAIControlledRevisionReconstructor().reconstruct(
        invocation, _opening_patch("Știre revizuită în limba română.")
    )
    expected = derive_assembled_text(
        opening=revised.opening,
        stories=revised.stories,
        transitions=revised.transitions,
        closing=revised.closing,
        cta=revised.cta,
    )
    assert revised.assembled_text == revised.teleprompter_text == expected


def test_r03_through_r07_authoritative_state_cannot_be_provider_authored():
    invocation = _invocation()
    source = invocation.request.source_draft
    revised = OpenAIControlledRevisionReconstructor().reconstruct(
        invocation, _opening_patch()
    )
    assert revised.episode_id == source.episode_id
    assert revised.stories == source.stories
    assert revised.transitions == source.transitions
    assert revised.closing == source.closing
    assert revised.cta == source.cta
    assert not hasattr(_opening_patch(), "source_draft_fingerprint")
    assert not hasattr(_opening_patch(), "contract_version")


def test_unknown_unauthorized_and_missing_references_fail_content_free():
    invocation = _invocation()
    unauthorized = OpenAIControlledRevisionProviderOutput.model_validate(
        {
            "revised_components": [
                {
                    "component_type": "closing",
                    "component_reference": "closing",
                    "revised_text": "Închidere revizuită.",
                }
            ]
        }
    )
    with pytest.raises(
        OpenAIReconstructionError,
        match="openai_provider_output_reference_unauthorized",
    ):
        OpenAIControlledRevisionReconstructor().reconstruct(invocation, unauthorized)

    unknown = OpenAIControlledRevisionProviderOutput.model_validate(
        {
            "revised_components": [
                {
                    "component_type": "story",
                    "component_reference": "story:999",
                    "factual_summary": "Rezumat sintetic.",
                    "commentary_block_texts": [],
                    "ending": "Final sintetic.",
                }
            ]
        }
    )
    with pytest.raises(
        OpenAIReconstructionError,
        match="openai_provider_output_reference_unknown",
    ):
        OpenAIControlledRevisionReconstructor().reconstruct(invocation, unknown)


def test_provider_output_is_immutable_and_deterministic():
    first = _opening_patch()
    second = _opening_patch()
    assert first == second
    with pytest.raises(ValidationError):
        first.revised_components = ()
