"""Deterministic STORY wrapper for the neutral Core V1.2 prose boundary."""

from __future__ import annotations

import json
import re

from pastila_scout.editor.generation.models import (
    AuthoredCommentaryBlockResult,
    ClosingGenerationResult,
    OpeningGenerationResult,
    StoryAuthoredContentResult,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import GenerationPrompt, PromptLayer
from pastila_scout.editor.generation.semantic_draft_v2 import (
    CoreFactualSummaryGenerationResultV2,
)

_SENTENCE = re.compile(r".+?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)
_FINITE_SENTENCE_ENDPOINT = re.compile(r"[.!?…](?:[\"'’”»)\]]*)$")


def adapt_core_v1_2_factual_summary_v2_prose(
    prose: str,
) -> CoreFactualSummaryGenerationResultV2:
    """Preserve one clean Core factual-summary surface byte-for-byte."""

    if type(prose) is not str or not prose or prose != prose.strip():
        raise ValueError("Core V1.2 V2 factual prose is invalid")
    return CoreFactualSummaryGenerationResultV2(text=prose)


def adapt_core_v1_2_story_prose(
    prose: str, prompt: GenerationPrompt
) -> StoryAuthoredContentResult:
    """Wrap V1.2 prose using only prose and factual IDs already in the prompt."""
    if type(prose) is not str or not prose.strip():
        raise ValueError("Core V1.2 prose is empty")
    facts = _section_json(prompt, PromptLayer.APPROVED_FACTS)
    fact_ids = tuple(
        item["fact_id"]
        for item in facts
        if type(item) is dict and type(item.get("fact_id")) is str
    )
    if not fact_ids or len(fact_ids) != len(set(fact_ids)):
        raise ValueError("Core V1.2 factual identity mapping is unavailable")
    factual, commentary, ending = _partition(prose.strip())
    return StoryAuthoredContentResult(
        factual_summary=factual,
        commentary_blocks=(
            AuthoredCommentaryBlockResult(
                block_type=prompt.component_type.value,
                text=commentary,
                sequence=1,
                source_fact_ids=fact_ids,
                satire_target_ids=(),
                protected_target_ids=(),
            ),
        ),
        ending=ending,
        ending_type="completed",
        declared_fact_usage=fact_ids,
    )


def adapt_core_v1_2_non_story_prose(prose: str, prompt: GenerationPrompt, schema):
    """Wrap V1.2 prose for a supported non-STORY component, failing closed."""
    if type(prose) is not str or not prose.strip() or prose != prose.strip():
        raise ValueError("Core V1.2 authored prose is invalid")
    context = _section_json(prompt, PromptLayer.COMPONENT_CONTEXT)
    if type(context) is not dict:
        raise ValueError("Core V1.2 component context is unavailable")
    if schema is OpeningGenerationResult:
        plan = _mapping(context, "opening_plan")
        accepted = _integer_tuple(context, "accepted_story_ids")
        mechanism = _text(plan, "opener_function")
        return OpeningGenerationResult(
            text=prose,
            referenced_story_ids=accepted,
            opening_mechanism=mechanism,
            declared_plan_references=(mechanism,),
        )
    if schema is ClosingGenerationResult:
        if _is_structured_non_prose_surface(prose):
            raise ValueError("Core V1.2 Closing prose is structurally empty or non-prose")
        if not _FINITE_SENTENCE_ENDPOINT.search(prose):
            raise ValueError("Core V1.2 Closing prose has no finite sentence endpoint")
        plan = _mapping(context, "closing_plan")
        mechanism = _text(plan, "closing_mode")
        return ClosingGenerationResult(
            text=prose,
            callback_executions=(),
            closing_mechanism=mechanism,
            declared_plan_references=(mechanism,),
        )
    if schema is TransitionGenerationResult:
        plan = _mapping(context, "transition_plan")
        transition_type = _text(plan, "public_transition_type")
        reference = _text(plan, "reason_code")
        return TransitionGenerationResult(
            from_story_id=_integer(context, "from_story_id"),
            to_story_id=_integer(context, "to_story_id"),
            text=prose,
            transition_type=transition_type,
            callback_usage=(),
            declared_plan_references=(reference,),
            fact_references=(),
        )
    raise ValueError("Core V1.2 result type is not adapter-authorized")


def _is_structured_non_prose_surface(prose: str) -> bool:
    try:
        decoded = json.loads(prose)
    except (json.JSONDecodeError, TypeError):
        return False
    return not isinstance(decoded, str)


def _section_json(prompt: GenerationPrompt, layer: PromptLayer):
    sections = tuple(item for item in prompt.sections if item.layer is layer)
    if len(sections) != 1:
        raise ValueError("Core V1.2 prompt authority is incomplete")
    return json.loads(sections[0].content)


def _mapping(value, key):
    result = value.get(key)
    if type(result) is not dict:
        raise ValueError(f"Core V1.2 {key} mapping is unavailable")
    return result


def _text(value, key):
    result = value.get(key)
    if type(result) is not str or not result:
        raise ValueError(f"Core V1.2 {key} value is unavailable")
    return result


def _integer(value, key):
    result = value.get(key)
    if type(result) is not int:
        raise ValueError(f"Core V1.2 {key} value is unavailable")
    return result


def _integer_tuple(value, key):
    result = value.get(key)
    if (
        type(result) is not list
        or not result
        or any(type(item) is not int for item in result)
    ):
        raise ValueError(f"Core V1.2 {key} values are unavailable")
    return tuple(result)


def _partition(prose: str) -> tuple[str, str, str]:
    sentences = tuple(item.strip() for item in _SENTENCE.findall(prose) if item.strip())
    if len(sentences) >= 3:
        return sentences[0], " ".join(sentences[1:-1]), sentences[-1]
    words = prose.split()
    if len(words) < 3:
        raise ValueError("Core V1.2 prose cannot fill the STORY contract without invention")
    first = max(1, len(words) // 3)
    second = max(first + 1, (len(words) * 2) // 3)
    return " ".join(words[:first]), " ".join(words[first:second]), " ".join(words[second:])


__all__ = (
    "adapt_core_v1_2_factual_summary_v2_prose",
    "adapt_core_v1_2_non_story_prose",
    "adapt_core_v1_2_story_prose",
)
