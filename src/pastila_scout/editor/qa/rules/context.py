"""Privacy-safe immutable rule context derived from an editorial request."""

import re
import unicodedata

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft, FrozenModel
from pastila_scout.editor.qa.models import (
    EditorialReviewRequest,
    ReviewScope,
    fingerprint,
)
from pastila_scout.editor.qa.rules.policy import DeterministicEditorialRulePolicy

NORMALIZATION_VERSION = "editorial-text-v1"


def visible_text(value: str) -> str:
    """Normalize Unicode and spacing for exact, language-independent comparison."""

    return " ".join(unicodedata.normalize("NFC", value).split())


def comparison_text(value: str) -> str:
    return visible_text(value).casefold()


class TextMetrics(FrozenModel):
    character_count: int = Field(ge=0)
    visible_character_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    paragraph_count: int = Field(ge=0)
    line_count: int = Field(ge=0)
    question_mark_count: int = Field(ge=0)
    exclamation_mark_count: int = Field(ge=0)

    @classmethod
    def from_text(cls, text: str):
        visible = visible_text(text)
        lines = text.splitlines()
        paragraphs = [part for part in re.split(r"(?:\r?\n){2,}", text) if part.strip()]
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", visible) if part]
        return cls(
            character_count=len(text),
            visible_character_count=sum(not char.isspace() for char in text),
            word_count=len(re.findall(r"\b[\w'-]+\b", visible, re.UNICODE)),
            sentence_count=len(sentences) if visible else 0,
            paragraph_count=len(paragraphs),
            line_count=len(lines),
            question_mark_count=text.count("?"),
            exclamation_mark_count=text.count("!"),
        )


class ComponentTextEntry(FrozenModel):
    scope: ReviewScope
    component_id: str
    order: int = Field(ge=0)
    text: str
    metrics: TextMetrics
    transition_from_story_position: int | None = Field(default=None, gt=0)
    transition_to_story_position: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def transition_location_is_consistent(self):
        positions = (
            self.transition_from_story_position,
            self.transition_to_story_position,
        )
        if self.scope is ReviewScope.TRANSITION:
            if None in positions:
                raise ValueError("transition entry requires both story positions")
            if self.transition_from_story_position >= self.transition_to_story_position:
                raise ValueError("transition entry positions must increase")
            expected = (
                f"transition-{self.transition_from_story_position:02d}-"
                f"{self.transition_to_story_position:02d}"
            )
            if self.component_id != expected:
                raise ValueError("transition component ID disagrees with positions")
        elif any(value is not None for value in positions):
            raise ValueError("non-transition entry cannot contain transition positions")
        return self


class CTAPlacementEntry(FrozenModel):
    placement: str
    after_story_id: int | None


class RuleContext(FrozenModel):
    episode_draft: EpisodeDraft = Field(exclude=True)
    episode_draft_fingerprint: str
    requested_scope: ReviewScope
    target_component_ids: tuple[str, ...]
    policy: DeterministicEditorialRulePolicy
    component_texts: tuple[ComponentTextEntry, ...]
    story_ids: tuple[int, ...]
    transition_pairs: tuple[tuple[int, int], ...]
    cta_placement: CTAPlacementEntry | None
    normalization_version: str = NORMALIZATION_VERSION
    context_fingerprint: str

    @field_validator("target_component_ids")
    @classmethod
    def targets_unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("target component IDs must be unique")
        return tuple(sorted(value))

    @classmethod
    def from_request(
        cls,
        request: EditorialReviewRequest,
        policy: DeterministicEditorialRulePolicy | None = None,
    ):
        policy = policy or DeterministicEditorialRulePolicy()
        draft = request.episode_draft
        entries: list[ComponentTextEntry] = [
            _entry(ReviewScope.OPENING, "opening", 0, draft.opening)
        ]
        order = 1
        transition_by_from = {item.from_story_id: item for item in draft.transitions}
        for position, story in enumerate(draft.stories, start=1):
            entries.append(
                _entry(
                    ReviewScope.STORY,
                    f"story-{position:02d}",
                    order,
                    story.text,
                )
            )
            order += 1
            transition = transition_by_from.get(story.story_id)
            if transition is not None:
                entries.append(
                    _entry(
                        ReviewScope.TRANSITION,
                        f"transition-{position:02d}-{position + 1:02d}",
                        order,
                        transition.text,
                        transition_from_story_position=position,
                        transition_to_story_position=position + 1,
                    )
                )
                order += 1
        entries.append(_entry(ReviewScope.CLOSING, "closing", order, draft.closing))
        # Static CTA text is deliberately absent from every rule index and fingerprint.
        cta = (
            CTAPlacementEntry(
                placement=draft.cta.placement.value,
                after_story_id=draft.cta.after_story_id,
            )
            if draft.cta
            else None
        )
        draft_fp = fingerprint(
            {
                "episode_id": draft.episode_id,
                "components": entries,
                "story_ids": tuple(item.story_id for item in draft.stories),
                "transition_pairs": tuple(
                    (item.from_story_id, item.to_story_id) for item in draft.transitions
                ),
                "cta_placement": cta,
            }
        )
        payload = {
            "episode_draft_fingerprint": draft_fp,
            "requested_scope": request.scope,
            "target_component_ids": tuple(sorted(request.component_ids)),
            "policy_fingerprint": policy.policy_fingerprint,
            "component_texts": entries,
            "normalization_version": NORMALIZATION_VERSION,
            "cta_placement": cta,
        }
        return cls(
            episode_draft=draft,
            episode_draft_fingerprint=draft_fp,
            requested_scope=request.scope,
            target_component_ids=tuple(sorted(request.component_ids)),
            policy=policy,
            component_texts=tuple(entries),
            story_ids=tuple(item.story_id for item in draft.stories),
            transition_pairs=tuple(
                (item.from_story_id, item.to_story_id) for item in draft.transitions
            ),
            cta_placement=cta,
            context_fingerprint=fingerprint(payload),
        )

    def target_entries(
        self, scopes: tuple[ReviewScope, ...]
    ) -> tuple[ComponentTextEntry, ...]:
        values = tuple(item for item in self.component_texts if item.scope in scopes)
        if self.requested_scope is not ReviewScope.EPISODE:
            values = tuple(
                item
                for item in values
                if item.component_id in self.target_component_ids
            )
        return values


def _entry(
    scope: ReviewScope,
    component_id: str,
    order: int,
    text: str,
    *,
    transition_from_story_position: int | None = None,
    transition_to_story_position: int | None = None,
) -> ComponentTextEntry:
    return ComponentTextEntry(
        scope=scope,
        component_id=component_id,
        order=order,
        text=text,
        metrics=TextMetrics.from_text(text),
        transition_from_story_position=transition_from_story_position,
        transition_to_story_position=transition_to_story_position,
    )
