"""Offline contract tests for invocation-specific exact-reference schemas."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_controlled_revision_contracts import FP, _invocation
from test_openai_controlled_revision_adapter import (
    _configuration,
    _execution,
    _raw_response,
)

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderClientResponse,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionInterpreter,
    OpenAIControlledRevisionProjector,
    OpenAIControlledRevisionProviderOutput,
    OpenAIControlledRevisionReconstructor,
    OpenAIReconstructionError,
    controlled_revision_schema_json,
    projected_controlled_revision_schema_json,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionTarget,
    RevisionTargetType,
)


def _target(target_type: RevisionTargetType, **identity: int):
    return ControlledRevisionTarget.build(
        target_type=target_type,
        upstream_target_fingerprint=FP,
        **identity,
    )


def _references(document: str) -> tuple[str, ...]:
    schema = json.loads(document)
    return tuple(
        definition["properties"]["component_reference"]["const"]
        for definition in schema["$defs"].values()
    )


def _all_targets() -> tuple[ControlledRevisionTarget, ...]:
    return (
        _target(RevisionTargetType.OPENING),
        _target(RevisionTargetType.STORY, story_id=101),
        _target(RevisionTargetType.TRANSITION, from_story_id=101, to_story_id=202),
        _target(RevisionTargetType.CLOSING),
        _target(RevisionTargetType.CALL_TO_ACTION),
    )


def test_single_reference_projection_is_exact_and_cardinality_bound():
    document = projected_controlled_revision_schema_json(
        (_target(RevisionTargetType.OPENING),)
    )
    schema = json.loads(document)

    assert _references(document) == ("opening",)
    assert schema["properties"]["revised_components"]["minItems"] == 1
    assert schema["properties"]["revised_components"]["maxItems"] == 1


def test_every_structural_reference_variant_is_projected_exactly():
    document = projected_controlled_revision_schema_json(_all_targets())

    assert _references(document) == (
        "opening",
        "story:101",
        "transition:101:202",
        "closing",
        "call_to_action",
    )
    assert "story:999" not in document
    for definition in json.loads(document)["$defs"].values():
        reference = definition["properties"]["component_reference"]
        assert set(reference) >= {"const"}
        assert "pattern" not in reference
        assert "enum" not in reference


def test_projection_preserves_non_reference_dto_constraints():
    base = json.loads(controlled_revision_schema_json())
    projected = json.loads(
        projected_controlled_revision_schema_json(
            (_target(RevisionTargetType.STORY, story_id=101),)
        )
    )
    branch = next(iter(projected["$defs"].values()))
    base_branch = base["$defs"]["OpenAIRevisedStoryComponent"]

    assert branch["required"] == base_branch["required"]
    assert branch["additionalProperties"] is False
    assert (
        branch["properties"]["factual_summary"]
        == base_branch["properties"]["factual_summary"]
    )
    assert (
        branch["properties"]["commentary_block_texts"]
        == base_branch["properties"]["commentary_block_texts"]
    )


def test_empty_duplicate_and_noncanonical_projection_inputs_fail_closed():
    opening = _target(RevisionTargetType.OPENING)
    closing = _target(RevisionTargetType.CLOSING)

    with pytest.raises(ValueError, match="requires targets"):
        projected_controlled_revision_schema_json(())
    with pytest.raises(ValueError, match="duplicates"):
        projected_controlled_revision_schema_json((opening, opening))
    with pytest.raises(ValueError, match="not canonical"):
        projected_controlled_revision_schema_json((closing, opening))


def test_projection_is_deterministic_and_reference_sensitive():
    first = projected_controlled_revision_schema_json(_all_targets())
    second = projected_controlled_revision_schema_json(_all_targets())
    changed = projected_controlled_revision_schema_json(
        (_target(RevisionTargetType.STORY, story_id=102),)
    )

    assert first == second
    assert first != changed


def test_base_schema_is_immutable_and_sequential_invocations_are_isolated():
    base_before = controlled_revision_schema_json()
    opening = projected_controlled_revision_schema_json(
        (_target(RevisionTargetType.OPENING),)
    )
    story = projected_controlled_revision_schema_json(
        (_target(RevisionTargetType.STORY, story_id=101),)
    )

    assert _references(opening) == ("opening",)
    assert _references(story) == ("story:101",)
    assert controlled_revision_schema_json() == base_before


def test_concurrent_invocation_schemas_do_not_leak_references():
    target_sets = (
        (_target(RevisionTargetType.OPENING),),
        (_target(RevisionTargetType.STORY, story_id=101),),
        (_target(RevisionTargetType.TRANSITION, from_story_id=101, to_story_id=202),),
        (_target(RevisionTargetType.CLOSING),),
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        documents = tuple(
            executor.map(projected_controlled_revision_schema_json, target_sets)
        )

    assert tuple(_references(document) for document in documents) == (
        ("opening",),
        ("story:101",),
        ("transition:101:202",),
        ("closing",),
    )


@pytest.mark.parametrize(
    "component",
    (
        {
            "component_type": "opening",
            "component_reference": "opening",
            "revised_text": "Deschidere nouă.",
        },
        {
            "component_type": "story",
            "component_reference": "story:101",
            "factual_summary": "Rezumat.",
            "commentary_block_texts": [],
            "ending": "Final.",
        },
        {
            "component_type": "transition",
            "component_reference": "transition:101:202",
            "revised_text": "Tranziție.",
        },
        {
            "component_type": "closing",
            "component_reference": "closing",
            "revised_text": "Încheiere.",
        },
        {
            "component_type": "call_to_action",
            "component_reference": "call_to_action",
            "bridge_text": "Pod editorial.",
        },
    ),
)
def test_projected_component_shapes_remain_compatible_with_provider_dto(component):
    parsed = OpenAIControlledRevisionProviderOutput.model_validate(
        {"revised_components": [component]}
    )
    assert (
        parsed.revised_components[0].component_reference
        == component["component_reference"]
    )


def test_production_request_uses_current_invocation_schema_and_preserves_transport():
    execution = _execution()
    projected = OpenAIControlledRevisionProjector(_configuration()).project(execution)
    payload = projected.client_request.payload
    arguments = payload.request_arguments()
    schema = arguments["text"]["format"]["schema"]

    assert tuple(
        item["properties"]["component_reference"]["const"]
        for item in schema["$defs"].values()
    ) == ("opening",)
    assert arguments["model"] == "synthetic-model"
    assert arguments["text"]["format"]["strict"] is True
    assert "authorized controlled revision" in arguments["instructions"]
    assert payload.schema_fingerprint == payload.schema_fingerprint


def test_offline_valid_response_reaches_unchanged_reconstruction():
    execution = _execution()
    result = OpenAIControlledRevisionInterpreter().interpret(
        execution,
        AIProviderClientResponse(payload=_raw_response(execution.invocation)),
    )
    assert result.gateway_result.revised_draft.opening != (
        execution.invocation.request.source_draft.opening
    )


@pytest.mark.parametrize(
    "reference",
    ("closing", "story:999", "Opening", "opening ", "opening:changed"),
)
def test_final_authorization_still_rejects_non_authorized_references(reference):
    invocation = _invocation()
    component_type = "closing" if reference == "closing" else "opening"
    if component_type == "opening" and reference.startswith("story:"):
        component = {
            "component_type": "story",
            "component_reference": reference,
            "factual_summary": "Rezumat.",
            "commentary_block_texts": [],
            "ending": "Final.",
        }
    else:
        component = {
            "component_type": component_type,
            "component_reference": reference,
            "revised_text": "Text.",
        }
    try:
        output = OpenAIControlledRevisionProviderOutput.model_validate(
            {"revised_components": [component]}
        )
    except ValueError:
        return
    with pytest.raises(OpenAIReconstructionError):
        OpenAIControlledRevisionReconstructor().reconstruct(invocation, output)


def test_projected_schema_size_is_bounded_at_contract_maximum():
    targets = tuple(
        _target(RevisionTargetType.STORY, story_id=story_id)
        for story_id in range(1, 51)
    )
    document = projected_controlled_revision_schema_json(targets)

    assert len(document.encode("utf-8")) < 1_000_000
    assert len(_references(document)) == 50
