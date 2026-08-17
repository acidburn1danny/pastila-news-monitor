"""Narrow, provider-neutral Editor adapter for story voice palettes."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from pastila_scout.contracts.scout_editor import RankedEditorialEvent

if TYPE_CHECKING:
    from pastila_scout.editor.commentary_models import StoryCommentaryBlueprint
    from pastila_scout.editor.voice_models import StoryVoicePlan

from .catalog import load_catalog_v1
from .errors import ExpressionCatalogErrorV1
from .models import (
    EditorialRetrievalContextV1,
    EpisodeVoiceStateV1,
    ExpressionCatalogV1,
    PaletteItemV1,
    StoryVoicePaletteV1,
)
from .retrieve import retrieve_story_voice_palette_v1

_LOG = logging.getLogger(__name__)
_TEMPLATE_SLOT = re.compile(r"\{([^{}]+)\}")
_TOKEN = re.compile(r"[0-9A-Za-zĂÂÎȘȚăâîșț]+", re.UNICODE)

_REGIONAL_SOURCE_REGIONS = {
    "stiridecluj": "Ardeal",
    "monitorul_cluj": "Ardeal",
    "monitorulcj": "Ardeal",
    "turnulsfatului": "Ardeal",
    "bistriteanul": "Ardeal",
}
_BUREAUCRACY = frozenset(
    {"aviz", "autorizatie", "birocratie", "dosar", "ghiseu", "permis"}
)
_PATRONAGE = frozenset({"clientelism", "numire", "numiri", "pile"})
_UNFINISHED = frozenset({"abandonat", "neterminat", "nefinalizat", "santier"})
_DISINFORMATION = frozenset({"dezinformare", "fake news", "negationism", "conspiratie"})
_TRAGEDY = frozenset(
    {"accident", "deces", "decedat", "mort", "victima", "victime", "tragedie"}
)


def _tokens(*values: str) -> frozenset[str]:
    return frozenset(
        token.casefold() for value in values for token in _TOKEN.findall(value)
    )


def _contains(text: str, vocabulary: frozenset[str]) -> bool:
    folded = text.casefold()
    tokens = _tokens(text)
    return bool(tokens & vocabulary) or any(
        " " in item and item in folded for item in vocabulary
    )


def _region(source_ids: tuple[str, ...]) -> str | None:
    regions = {
        region
        for source_id in source_ids
        if (region := _REGIONAL_SOURCE_REGIONS.get(source_id.casefold())) is not None
    }
    return next(iter(regions)) if len(regions) == 1 else None


def build_editorial_retrieval_context_v1(
    *,
    event: RankedEditorialEvent,
    episode_position: int,
    commentary: StoryCommentaryBlueprint,
    voice: StoryVoicePlan,
) -> EditorialRetrievalContextV1:
    """Project only reliable Editor inputs into the deterministic retrieval context."""

    text = f"{event.canonical_title} {event.canonical_summary}"
    source_ids = tuple(item.source_id for item in event.source_provenance)
    source_names = tuple(item.source_name for item in event.source_provenance)
    categories = tuple(event.categories)
    political = "Politica" in categories
    international = "Externe" in categories
    entertainment = "CanCan" in categories
    protected = tuple(item.value for item in voice.protected_dimensions)
    protected_targets = {item.value for item in commentary.protected_targets}
    victim_sensitive = bool(
        protected_targets
        & {
            "victims",
            "vulnerable_people",
            "children",
            "patients",
            "bereaved_people",
        }
    )
    tragedy = commentary.empathy.humor_sensitivity.value in {
        "restricted",
        "prohibited",
    } and _contains(text, _TRAGEDY)
    humor = {
        "none": 0,
        "light": 1,
        "moderate": 2,
        "strong": 3,
        "roast": 4,
    }[voice.humor_intensity.value]
    profanity = {
        "clean": 0,
        "informal": 1,
        "edgy": 2,
        "profane_light": 3,
        "profane_direct": 4,
    }[voice.profanity_ceiling.value]
    satire = {item.value for item in commentary.satire_targets}
    topic_tags = tuple(sorted(satire))
    return EditorialRetrievalContextV1(
        event_id=str(event.event_id),
        title=event.canonical_title,
        summary=event.canonical_summary,
        categories=categories,
        source_ids=source_ids,
        source_names=source_names,
        source_count=event.source_count,
        episode_position=episode_position,
        keywords=tuple(sorted(_tokens(event.canonical_title))),
        topic_tags=topic_tags,
        protected_dimensions=protected,
        humor_intensity=humor,
        roast_eligible=voice.roast_eligibility.value != "prohibited",
        profanity_ceiling=profanity,
        raw_eligible=profanity >= 2 and not victim_sensitive and not tragedy,
        victim_sensitive=victim_sensitive,
        tragedy_sensitive=tragedy,
        bureaucracy=_contains(text, _BUREAUCRACY) or "absurd_bureaucracy" in satire,
        patronage=_contains(text, _PATRONAGE),
        unfinished_project=_contains(text, _UNFINISHED),
        disinformation=_contains(text, _DISINFORMATION) or "propaganda" in satire,
        entertainment=entertainment,
        international=international,
        region=_region(source_ids),
        political_context=political,
        meme_context=entertainment,
        comedy_disabled=(
            voice.humor_intensity.value == "none"
            and voice.roast_eligibility.value == "prohibited"
        ),
    )


def build_story_voice_palette_for_editor_v1(
    *,
    event: RankedEditorialEvent,
    episode_position: int,
    commentary: StoryCommentaryBlueprint,
    voice: StoryVoicePlan,
    episode_state: EpisodeVoiceStateV1 | None = None,
    catalog_loader: Callable[[], ExpressionCatalogV1] = load_catalog_v1,
) -> StoryVoicePaletteV1:
    """Retrieve a palette, degrading expected local data failures to empty."""

    event_id = str(getattr(event, "event_id", "unknown"))
    try:
        context = build_editorial_retrieval_context_v1(
            event=event,
            episode_position=episode_position,
            commentary=commentary,
            voice=voice,
        )
        return retrieve_story_voice_palette_v1(
            catalog=catalog_loader(),
            context=context,
            episode_state=episode_state or EpisodeVoiceStateV1(),
        )
    except ExpressionCatalogErrorV1:
        _LOG.warning("expression_palette_unavailable:catalog")
    except TypeError, ValueError, AttributeError:
        _LOG.warning("expression_palette_unavailable:context")
    return StoryVoicePaletteV1.empty(event_id)


def serialize_story_voice_palette_v1(palette: StoryVoicePaletteV1) -> dict[str, object]:
    """Return the compact structured toolkit included in the story prompt."""

    def item(value: PaletteItemV1, *, templates: bool) -> dict[str, object]:
        projected: dict[str, object] = {
            "id": value.authority_id,
            "affordance": value.family,
        }
        slots = _TEMPLATE_SLOT.findall(value.display_text) if templates else []
        if not slots:
            projected["text"] = value.display_text
            return projected
        projected.update(
            template_parts=tuple(_TEMPLATE_SLOT.split(value.display_text)[::2]),
            slots=tuple(slots),
            rendering_instruction=(
                "Fill every slot with concrete story-specific wording, join the "
                "parts in order, and output neither slot names nor placeholder "
                "notation. Omit this optional tool if it cannot be filled naturally."
            ),
        )
        return projected

    def items(
        values: tuple[PaletteItemV1, ...], *, templates: bool = False
    ) -> tuple[dict[str, object], ...]:
        return tuple(item(value, templates=templates) for value in values)

    return {
        "expressions": items(palette.expressions),
        "controlled_terms": items(palette.controlled_terms),
        "comedy_devices": items(palette.comedy_devices, templates=True),
        "signature_devices": items(palette.signature_devices, templates=True),
        "usage_instruction": {
            "optional": True,
            "may_use_none": True,
            "never_force": True,
            "maximum_comedy_tools": 1,
            "never_chain_tools": True,
            "use_each_offered_tool_at_most_once": True,
            "integrate_naturally_without_introduction_or_quotation": True,
            "controlled_terms_are_optional_contextual_vocabulary": True,
            "unresolved_placeholders_forbidden": True,
            "skip_template_if_it_cannot_be_filled_naturally": True,
            "preserve_facts": True,
            "do_not_invent_attribution": True,
            "do_not_target_victims_or_tragedy": True,
            "respect_voice_plan_limits": True,
        },
    }


__all__ = (
    "build_editorial_retrieval_context_v1",
    "build_story_voice_palette_for_editor_v1",
    "serialize_story_voice_palette_v1",
)
