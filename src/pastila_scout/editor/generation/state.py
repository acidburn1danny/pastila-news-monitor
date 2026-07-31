"""Deeply immutable accepted-component state for controlled generation."""

from collections.abc import Mapping
from typing import Any

from pydantic import Field, field_validator

from pastila_scout.editor.generation.models import FrozenModel, GeneratedCallbackAnchor


class StorySummaryRecord(FrozenModel):
    """Immutable story-summary mapping entry with deterministic ordering."""

    story_id: int
    text: str


class EpisodeGenerationState(FrozenModel):
    revision: int = Field(default=0, ge=0)
    accepted_component_ids: tuple[str, ...] = ()
    generated_story_ids: tuple[int, ...] = ()
    used_humor_mechanisms: tuple[str, ...] = ()
    used_expression_families: tuple[str, ...] = ()
    used_reference_families: tuple[str, ...] = ()
    used_vocatives: int = 0
    profanity_usage: int = 0
    rhetorical_question_functions: tuple[str, ...] = ()
    ending_types: tuple[str, ...] = ()
    transition_types: tuple[str, ...] = ()
    emotional_position: int = 0
    story_factual_summaries: tuple[StorySummaryRecord, ...] = ()
    story_ending_summaries: tuple[StorySummaryRecord, ...] = ()
    registered_callback_anchors: tuple[GeneratedCallbackAnchor, ...] = ()
    executed_callback_ids: tuple[str, ...] = ()
    opening_references: tuple[int, ...] = ()
    protected_payoffs_teased: tuple[str, ...] = ()
    accepted_warnings: tuple[str, ...] = ()

    @field_validator("story_factual_summaries", "story_ending_summaries", mode="before")
    @classmethod
    def normalize_summaries(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, Mapping):
            return tuple(
                {"story_id": int(story_id), "text": text}
                for story_id, text in sorted(
                    value.items(), key=lambda item: int(item[0])
                )
            )
        return tuple(sorted(value or (), key=_summary_id))

    @field_validator("registered_callback_anchors", mode="before")
    @classmethod
    def normalize_anchors(cls, value: Any) -> tuple[Any, ...]:
        return tuple(sorted(value or (), key=_anchor_id))

    def factual_summary(self, story_id: int) -> str:
        return _summary(self.story_factual_summaries, story_id)

    def ending_summary(self, story_id: int) -> str:
        return _summary(self.story_ending_summaries, story_id)

    def accept_story(self, item_id, result):
        factual = _replace_summary(
            self.story_factual_summaries, result.story_id, result.factual_summary
        )
        endings = _replace_summary(
            self.story_ending_summaries, result.story_id, result.ending
        )
        anchors = tuple(
            sorted(
                (*self.registered_callback_anchors, *result.generated_callback_anchors),
                key=lambda anchor: anchor.callback_id,
            )
        )
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "accepted_component_ids": (*self.accepted_component_ids, item_id),
                "generated_story_ids": (*self.generated_story_ids, result.story_id),
                "used_humor_mechanisms": (
                    *self.used_humor_mechanisms,
                    *result.used_humor_mechanisms,
                ),
                "used_expression_families": (
                    *self.used_expression_families,
                    *result.used_expression_families,
                ),
                "used_reference_families": (
                    *self.used_reference_families,
                    *result.used_reference_families,
                ),
                "used_vocatives": self.used_vocatives + result.used_vocatives,
                "profanity_usage": self.profanity_usage + result.profanity_usage,
                "rhetorical_question_functions": (
                    *self.rhetorical_question_functions,
                    *result.rhetorical_question_functions,
                ),
                "ending_types": (*self.ending_types, result.ending_type),
                "emotional_position": self.emotional_position + 1,
                "story_factual_summaries": factual,
                "story_ending_summaries": endings,
                "registered_callback_anchors": anchors,
                "accepted_warnings": (*self.accepted_warnings, *result.warnings),
            }
        )

    def accept_transition(self, item_id, result):
        anchors = self._consume_callbacks(result.callback_usage)
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "accepted_component_ids": (*self.accepted_component_ids, item_id),
                "transition_types": (*self.transition_types, result.transition_type),
                "executed_callback_ids": (
                    *self.executed_callback_ids,
                    *result.callback_usage,
                ),
                "registered_callback_anchors": anchors,
                "accepted_warnings": (*self.accepted_warnings, *result.warnings),
            }
        )

    def accept_opening(self, item_id, result):
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "accepted_component_ids": (*self.accepted_component_ids, item_id),
                "opening_references": result.referenced_story_ids,
                "protected_payoffs_teased": result.teased_reveal_ids,
                "accepted_warnings": (*self.accepted_warnings, *result.warnings),
            }
        )

    def accept_component(self, item_id, warnings=(), callbacks=()):
        anchors = self._consume_callbacks(callbacks)
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "accepted_component_ids": (*self.accepted_component_ids, item_id),
                "executed_callback_ids": (*self.executed_callback_ids, *callbacks),
                "registered_callback_anchors": anchors,
                "accepted_warnings": (*self.accepted_warnings, *warnings),
            }
        )

    def _consume_callbacks(self, callback_ids):
        used = frozenset(callback_ids)
        return tuple(
            (
                anchor.model_copy(update={"current_uses": anchor.current_uses + 1})
                if anchor.callback_id in used
                else anchor
            )
            for anchor in self.registered_callback_anchors
        )

    def available_callback_ids(self, target_id):
        return tuple(
            anchor.callback_id
            for anchor in self.registered_callback_anchors
            if target_id in anchor.allowed_target_component_ids
            and anchor.current_uses < anchor.maximum_uses
        )


def _summary(records: tuple[StorySummaryRecord, ...], story_id: int) -> str:
    try:
        return next(record.text for record in records if record.story_id == story_id)
    except StopIteration as exc:
        raise KeyError(story_id) from exc


def _replace_summary(records, story_id, text):
    retained = tuple(record for record in records if record.story_id != story_id)
    return tuple(
        sorted(
            (*retained, StorySummaryRecord(story_id=story_id, text=text)),
            key=lambda item: item.story_id,
        )
    )


def _summary_id(value: Any) -> int:
    if isinstance(value, StorySummaryRecord):
        return value.story_id
    if isinstance(value, Mapping):
        return int(value["story_id"])
    return int(value[0])


def _anchor_id(value: Any) -> str:
    if isinstance(value, GeneratedCallbackAnchor):
        return value.callback_id
    if isinstance(value, Mapping):
        return str(value["callback_id"])
    raise TypeError("callback anchors must be models or mappings")
