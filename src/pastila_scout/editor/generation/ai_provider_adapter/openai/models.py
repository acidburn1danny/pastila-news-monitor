"""Immutable OpenAI-specific request and structured-output models."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Literal

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.generation.revision import (
    ControlledRevisionTarget,
    RevisionTargetType,
)

TEXT_COMPONENT_REFERENCE_RULES = {
    "opening": {"const": "opening"},
    "transition": {"pattern": r"^transition:[1-9][0-9]*:[1-9][0-9]*$"},
    "closing": {"const": "closing"},
}
STORY_REFERENCE_PATTERN = r"^story:[1-9][0-9]*$"


class OpenAIRevisedTextComponent(FrozenModel):
    """Provider-authored text for one simple authorized component."""

    component_type: Literal["opening", "transition", "closing"]
    component_reference: str = Field(min_length=1, max_length=100)
    revised_text: str = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def reference_matches_type(self):
        valid = {
            "opening": self.component_reference == "opening",
            "closing": self.component_reference == "closing",
            "transition": bool(
                re.fullmatch(
                    TEXT_COMPONENT_REFERENCE_RULES["transition"]["pattern"],
                    self.component_reference,
                )
            ),
        }
        if not valid[self.component_type]:
            raise ValueError("provider component reference has invalid shape")
        return self


class OpenAIRevisedStoryComponent(FrozenModel):
    """Provider-authored prose mapped onto one authoritative story structure."""

    component_type: Literal["story"]
    component_reference: str = Field(pattern=STORY_REFERENCE_PATTERN)
    factual_summary: str = Field(min_length=1, max_length=100_000)
    commentary_block_texts: tuple[str, ...] = Field(max_length=100)
    ending: str = Field(min_length=1, max_length=100_000)


class OpenAIRevisedCallToActionComponent(FrozenModel):
    """Provider-authored CTA bridge; placement and static text remain authoritative."""

    component_type: Literal["call_to_action"]
    component_reference: Literal["call_to_action"]
    bridge_text: str = Field(min_length=1, max_length=100_000)


OpenAIRevisedComponent = (
    OpenAIRevisedTextComponent
    | OpenAIRevisedStoryComponent
    | OpenAIRevisedCallToActionComponent
)


class OpenAIControlledRevisionProviderOutput(FrozenModel):
    """Strict provider-owned patch with no authoritative or derived domain state."""

    revised_components: tuple[OpenAIRevisedComponent, ...] = Field(
        min_length=1, max_length=50
    )

    @model_validator(mode="after")
    def unique_references(self):
        references = tuple(item.component_reference for item in self.revised_components)
        if len(references) != len(set(references)):
            raise ValueError("provider component references contain duplicates")
        return self


class OpenAIExpectedOutputContractProjection(FrozenModel):
    """Explicit provider-facing projection of authoritative output obligations."""

    output_type: str
    episode_draft_contract_version: str
    source_draft_fingerprint: str
    preservation_fingerprint: str
    require_distinct_draft_identity: bool
    output_contract_fingerprint: str


class OpenAIResponsesPayload(FrozenModel):
    """Immutable semantic payload for one synchronous Responses API request."""

    model: str = Field(min_length=1)
    instructions: str = Field(min_length=1, repr=False)
    input: str = Field(min_length=1, repr=False)
    schema_document_json: str = Field(min_length=1, repr=False)
    schema_name: str = "controlled_revision_patch_v1"

    def request_arguments(self) -> dict[str, Any]:
        """Return fresh SDK arguments so callers cannot mutate this payload."""

        return {
            "model": self.model,
            "instructions": self.instructions,
            "input": self.input,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": self.schema_name,
                    "schema": json.loads(self.schema_document_json),
                    "strict": True,
                }
            },
            "store": False,
        }

    @property
    def schema_fingerprint(self) -> str:
        """Return the deterministic effective-schema identity."""

        return hashlib.sha256(self.schema_document_json.encode()).hexdigest()


def controlled_revision_schema_json() -> str:
    """Return the canonical strict schema used for OpenAI revision output."""

    schema = OpenAIControlledRevisionProviderOutput.model_json_schema()
    _align_text_reference_types(schema)
    _require_all_object_properties(schema)
    return json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def projected_controlled_revision_schema_json(
    revision_targets: tuple[ControlledRevisionTarget, ...],
) -> str:
    """Purely project the invocation-authorized targets into the base DTO schema."""

    if not revision_targets:
        raise ValueError("controlled revision schema projection requires targets")
    if revision_targets != tuple(
        sorted(revision_targets, key=lambda target: target.canonical_key)
    ):
        raise ValueError("controlled revision schema targets are not canonical")
    references = tuple(target.canonical_reference for target in revision_targets)
    if len(references) != len(set(references)):
        raise ValueError("controlled revision schema targets contain duplicates")

    schema = json.loads(controlled_revision_schema_json())
    base_definitions = schema["$defs"]
    projected_definitions: dict[str, dict[str, Any]] = {}
    item_branches = []
    for index, target in enumerate(revision_targets, 1):
        definition_name = f"AuthorizedRevisionComponent{index:02d}"
        branch = _project_target_branch(base_definitions, target)
        projected_definitions[definition_name] = branch
        item_branches.append({"$ref": f"#/$defs/{definition_name}"})
    schema["$defs"] = projected_definitions
    revised = schema["properties"]["revised_components"]
    revised["items"] = {"anyOf": item_branches}
    revised["minItems"] = len(revision_targets)
    revised["maxItems"] = len(revision_targets)
    _validate_projected_references(schema, references)
    return json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _project_target_branch(
    definitions: dict[str, Any], target: ControlledRevisionTarget
) -> dict[str, Any]:
    if target.target_type is RevisionTargetType.STORY:
        branch = deepcopy(definitions["OpenAIRevisedStoryComponent"])
    elif target.target_type is RevisionTargetType.CALL_TO_ACTION:
        branch = deepcopy(definitions["OpenAIRevisedCallToActionComponent"])
    elif target.target_type in {
        RevisionTargetType.OPENING,
        RevisionTargetType.TRANSITION,
        RevisionTargetType.CLOSING,
    }:
        text = definitions["OpenAIRevisedTextComponent"]
        branch = deepcopy(
            next(
                item
                for item in text["anyOf"]
                if item["properties"]["component_type"].get("const")
                == target.target_type.value
            )
        )
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError("unsupported controlled revision schema target")
    reference = branch["properties"]["component_reference"]
    for constraint in ("enum", "pattern"):
        reference.pop(constraint, None)
    reference["const"] = target.canonical_reference
    return branch


def _validate_projected_references(
    schema: dict[str, Any], expected: tuple[str, ...]
) -> None:
    projected = tuple(
        definition["properties"]["component_reference"].get("const")
        for definition in schema["$defs"].values()
    )
    revised = schema["properties"]["revised_components"]
    if (
        projected != expected
        or revised["minItems"] != len(expected)
        or revised["maxItems"] != len(expected)
    ):
        raise ValueError("controlled revision projected schema integrity failure")


def _align_text_reference_types(schema: dict[str, Any]) -> None:
    """Express the DTO text reference/type validator in provider-visible branches."""

    name = "OpenAIRevisedTextComponent"
    original = schema["$defs"][name]
    branches = []
    for component_type, reference_rule in TEXT_COMPONENT_REFERENCE_RULES.items():
        branch = deepcopy(original)
        branch["title"] = f"{name}_{component_type}"
        branch["properties"]["component_type"].pop("enum", None)
        branch["properties"]["component_type"]["const"] = component_type
        reference = branch["properties"]["component_reference"]
        reference.update(reference_rule)
        branches.append(branch)
    schema["$defs"][name] = {
        "title": original["title"],
        "description": original["description"],
        "anyOf": branches,
    }


def _require_all_object_properties(node: Any) -> None:
    """Make Pydantic defaults explicit for OpenAI strict-schema compatibility."""

    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = sorted(properties)
            node["additionalProperties"] = False
        for value in node.values():
            _require_all_object_properties(value)
    elif isinstance(node, list):
        for value in node:
            _require_all_object_properties(value)
