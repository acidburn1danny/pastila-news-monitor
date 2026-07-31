"""Deterministic episode assembly, CTA placement, and presentation formatting."""

import re
import textwrap

from pastila_scout.editor.commentary_models import Sensitivity
from pastila_scout.editor.generation.models import (
    CallToActionPlacementPlan,
    CTAPlacement,
    EpisodeDraft,
    derive_assembled_text,
)


def plan_cta(stories, *, static_content="", cta_type="support"):
    if not static_content or len(stories) < 2:
        return CallToActionPlacementPlan(
            placement=CTAPlacement.OMITTED,
            cta_type=cta_type,
            static_content=static_content,
        )
    sensitive = {
        story.event_id
        for story in stories
        if story.sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED)
    }
    candidates = [
        story.event_id for story in stories[:-1] if story.event_id not in sensitive
    ]
    if candidates:
        return CallToActionPlacementPlan(
            placement=CTAPlacement.AFTER_STORY,
            after_story_id=candidates[0],
            cta_type=cta_type,
            static_content=static_content,
        )
    return CallToActionPlacementPlan(
        placement=CTAPlacement.BEFORE_CLOSING,
        cta_type=cta_type,
        static_content=static_content,
    )


class DraftAssembler:
    def assemble(
        self, *, episode_id, story_order, opening, stories, transitions, closing, cta
    ):
        story_map = {story.story_id: story for story in stories}
        if len(story_map) != len(stories) or tuple(story_map) != story_order:
            raise ValueError("draft stories must be unique and in optimized order")
        ordered_stories = tuple(story_map[story_id] for story_id in story_order)
        assembled = derive_assembled_text(
            opening=opening,
            stories=ordered_stories,
            transitions=transitions,
            closing=closing,
            cta=cta,
        )
        return EpisodeDraft(
            episode_id=episode_id,
            opening=opening,
            stories=ordered_stories,
            transitions=transitions,
            closing=closing,
            cta=cta,
            assembled_text=assembled,
            teleprompter_text=assembled,
        )


class TeleprompterFormatter:
    """Change whitespace/line layout only; never rewrite lexical content."""

    def format(self, text, profile):
        paragraphs = []
        for paragraph in text.split("\n\n"):
            normalized = " ".join(paragraph.split())
            protected = re.sub(
                r"(\d+(?:[.,]\d+)?) ([A-Za-z]+)\b",
                lambda match: f"{match.group(1)}\u00a0{match.group(2)}",
                normalized,
            )
            paragraphs.append(
                textwrap.fill(
                    protected,
                    width=profile.maximum_line_length,
                    break_long_words=False,
                    break_on_hyphens=False,
                ).replace("\u00a0", " ")
            )
        return "\n\n".join(paragraphs)
