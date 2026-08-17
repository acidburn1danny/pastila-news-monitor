"""Structured deterministic prompt protocol and fingerprints."""

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum, StrEnum
from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import (
    FrozenModel,
    GenerationComponentType,
    GenerationMode,
)


class PromptLayer(StrEnum):
    IMMUTABLE_RULES = "immutable_rules"
    EPISODE_CONTEXT = "episode_context"
    COMPONENT_CONTEXT = "component_context"
    APPROVED_FACTS = "approved_facts"
    FORBIDDEN_CLAIMS = "forbidden_claims"
    EDITORIAL_INTENTIONS = "editorial_intentions"
    CONVERSATION_INTENTIONS = "conversation_intentions"
    VOICE_INTENTIONS = "voice_intentions"
    EPISODE_STATE = "episode_state"
    OUTPUT_SCHEMA = "output_schema"
    GENERATION_TASK = "generation_task"
    VALIDATION_FAILURES = "validation_failures"
    CORRECTIVE_INSTRUCTIONS = "corrective_instructions"


class PromptCanonicalizationError(TypeError):
    """Raised when semantic prompt input cannot be serialized deterministically."""


class PromptSection(FrozenModel):
    layer: PromptLayer
    title: str
    content: str


class GenerationPrompt(FrozenModel):
    component_type: GenerationComponentType
    sections: tuple[PromptSection, ...]
    output_schema_name: str
    prompt_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def text(self):
        return "\n\n".join(
            f"[{section.layer.value}] {section.title}\n{section.content}"
            for section in self.sections
        )

    @model_validator(mode="after")
    def ordered(self):
        order = list(PromptLayer)
        indexes = [order.index(section.layer) for section in self.sections]
        if indexes != sorted(indexes):
            raise ValueError("prompt layers must use fixed protocol order")
        return self


class PromptBuilder:
    """Build prompts from normalized JSON sections, never raw blueprints."""

    def build(
        self,
        *,
        component_type,
        episode_context,
        component_context,
        state,
        output_schema,
        mode=GenerationMode.STANDARD,
        failures=(),
    ):
        facts = _unordered(getattr(component_context, "approved_facts", ()))
        forbidden = _unordered(getattr(component_context, "forbidden_claims", ()))
        editorial = getattr(component_context, "editorial_plan", {})
        conversation = getattr(component_context, "conversation_plan", {})
        voice = getattr(
            component_context,
            "voice_plan",
            getattr(component_context, "voice_profile", {}),
        )
        values = [
            (
                PromptLayer.IMMUTABLE_RULES,
                "Generator rules",
                {
                    "two_phases": True,
                    "facts_only_in_summary": True,
                    "no_markdown": True,
                    "no_cross_story_facts": True,
                    "mode": mode.value,
                    "minimal_safe": mode is GenerationMode.MINIMAL_SAFE,
                },
            ),
            (
                PromptLayer.EPISODE_CONTEXT,
                "Episode context",
                _episode_prompt_context(episode_context),
            ),
            (
                PromptLayer.COMPONENT_CONTEXT,
                "Local context",
                _component_local_context(component_context),
            ),
            (PromptLayer.APPROVED_FACTS, "Approved facts", facts),
            (PromptLayer.FORBIDDEN_CLAIMS, "Forbidden claims", forbidden),
            (
                PromptLayer.EDITORIAL_INTENTIONS,
                "Editorial intentions",
                _semantic_projection(editorial, _EDITORIAL_FIELDS),
            ),
            (
                PromptLayer.CONVERSATION_INTENTIONS,
                "Conversation intentions",
                _conversation_prompt_intent(conversation),
            ),
            (
                PromptLayer.VOICE_INTENTIONS,
                "Voice ceilings",
                _without_application_identity(voice),
            ),
            (PromptLayer.EPISODE_STATE, "Accepted state", _active_state(state)),
            (
                PromptLayer.OUTPUT_SCHEMA,
                "Structured output schema",
                {
                    "native_schema": output_schema.__name__,
                    "return_only_structured_result": True,
                },
            ),
            (
                PromptLayer.GENERATION_TASK,
                "Local task",
                {"component": component_type.value},
            ),
        ]
        if failures:
            values.extend(
                (
                    (
                        PromptLayer.VALIDATION_FAILURES,
                        "Previous validation failures",
                        tuple(sorted(failures)),
                    ),
                    (
                        PromptLayer.CORRECTIVE_INSTRUCTIONS,
                        "Corrective constraints",
                        _corrective_constraints(
                            component_context=component_context,
                            failures=failures,
                            minimal_safe=mode is GenerationMode.MINIMAL_SAFE,
                        ),
                    ),
                )
            )
        sections = tuple(
            PromptSection(layer=layer, title=title, content=_canonical(content))
            for layer, title, content in values
        )
        semantic = _canonical(
            {
                "component": component_type,
                "schema": output_schema.__name__,
                "sections": sections,
            }
        )
        fingerprint = "sha256:" + hashlib.sha256(semantic.encode("utf-8")).hexdigest()
        return GenerationPrompt(
            component_type=component_type,
            sections=sections,
            output_schema_name=output_schema.__name__,
            prompt_fingerprint=fingerprint,
        )


def _canonical(value: Any) -> str:
    value = canonicalize(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _corrective_constraints(*, component_context, failures, minimal_safe):
    errors = set(failures)
    constraints = {
        "correct_only_failures": True,
        "preserve_valid_sections": True,
        "minimal_safe": minimal_safe,
    }
    if any("malformed structured output" in item.casefold() for item in errors):
        constraints["structured_output_repair"] = (
            "Return exactly one JSON object matching the supplied schema; "
            "no markdown fences or prose outside JSON."
        )
    if "word_budget_exceeded" in errors:
        constraints["maximum_content_words"] = getattr(
            component_context, "word_budget", None
        )
        constraints["counted_content_fields"] = (
            "factual_summary",
            "commentary_blocks[].text",
            "ending",
        )
        actual = next(
            (
                int(item.rsplit(":", 1)[1])
                for item in errors
                if item.startswith("word_budget_actual:")
            ),
            None,
        )
        if actual is not None:
            constraints["previous_content_words"] = actual
            constraints["minimum_words_to_remove"] = max(
                0, actual - constraints["maximum_content_words"]
            )
    return constraints


def canonicalize(value: Any) -> Any:
    """Convert supported semantic values into deterministic JSON-compatible data."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PromptCanonicalizationError("non-finite floats are unsupported")
        return value
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if hasattr(value, "model_dump"):
        return canonicalize(value.model_dump(mode="python"))
    if is_dataclass(value) and not isinstance(value, type):
        return canonicalize(asdict(value))
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            canonical_key = _canonical_key(key)
            if canonical_key in normalized:
                raise PromptCanonicalizationError("canonical mapping keys collide")
            normalized[canonical_key] = canonicalize(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        members = [canonicalize(item) for item in value]
        return sorted(members, key=_canonical_json_value)
    raise PromptCanonicalizationError(
        f"unsupported prompt value type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _canonical_key(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, str):
        return value
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return json.dumps(value, allow_nan=False, separators=(",", ":"))
    raise PromptCanonicalizationError(
        f"unsupported prompt mapping key type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _canonical_json_value(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _unordered(values: Any) -> tuple[Any, ...]:
    """Canonicalize collections whose contract does not assign positional meaning."""

    return tuple(
        sorted(values, key=lambda item: _canonical_json_value(canonicalize(item)))
    )


def _component_local_context(value: Any) -> Any:
    if not hasattr(value, "model_dump"):
        return value
    projected = value.model_dump(
        mode="python",
        exclude={
            "approved_facts",
            "forbidden_claims",
            "editorial_plan",
            "conversation_plan",
            "voice_plan",
            "voice_profile",
            "flow_position",
            "runtime_budget",
            "story_id",
        },
    )
    toolkit = projected.get("optional_editorial_toolkit")
    if isinstance(toolkit, dict):
        projected["optional_editorial_toolkit"] = _compact_toolkit(toolkit)
    return projected


_EDITORIAL_FIELDS = (
    "angles",
    "intent",
    "levels",
    "mandatory",
    "narrative_function",
    "recent_episode_reference",
)


def _episode_prompt_context(value: Any) -> Any:
    if not hasattr(value, "model_dump"):
        return value
    data = value.model_dump(mode="python")
    voice = data.get("episode_voice_profile", {})
    return {
        "audience_relationship": data.get("audience_relationship"),
        "episode_theme": data.get("episode_theme"),
        "episode_voice": _semantic_projection(
            voice,
            (
                "audience_respect_invariants",
                "dominant_register",
                "emotional_arc",
                "ending_register",
                "global_humor_ceiling",
                "profanity_ceiling",
            ),
        ),
        "global_budgets": data.get("global_budgets", {}),
    }


def _conversation_prompt_intent(value: Any) -> Any:
    data = canonicalize(value)
    if not isinstance(data, dict):
        return data
    projected = _without_application_identity(data)
    summary = projected.get("factual_summary")
    if isinstance(summary, dict):
        projected["factual_summary"] = {
            key: item
            for key, item in summary.items()
            if key
            not in {
                "central_event_id",
                "evidence_references",
                "prohibited_unsupported_claims",
            }
        }
    return projected


def _without_application_identity(value: Any) -> Any:
    data = canonicalize(value)
    if not isinstance(data, dict):
        return data
    return {
        key: item
        for key, item in data.items()
        if key not in {"event_id", "intent_id", "position", "source_report_id"}
    }


def _semantic_projection(value: Any, fields: tuple[str, ...]) -> Any:
    data = canonicalize(value)
    if not isinstance(data, dict):
        return data
    return {key: data[key] for key in fields if key in data}


def _active_state(value: Any) -> Any:
    data = canonicalize(value)
    if not isinstance(data, dict):
        return data
    return {
        key: item
        for key, item in data.items()
        if item is not None and item not in (0, False, "", [], {})
    }


def _compact_toolkit(toolkit: dict[str, Any]) -> dict[str, Any]:
    compact = {}
    for section in (
        "expressions",
        "controlled_terms",
        "comedy_devices",
        "signature_devices",
    ):
        values = toolkit.get(section, ())
        if values:
            compact[section] = tuple(
                {key: item[key] for key in ("text", "affordance") if key in item}
                for item in values
            )
    rules = toolkit.get("usage_instruction", {})
    if isinstance(rules, dict):
        compact["rules"] = tuple(key for key, enabled in rules.items() if enabled)
    return compact
