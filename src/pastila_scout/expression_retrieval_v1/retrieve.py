from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from .models import (
    ComedyDeviceRecordV1,
    ControlledTermRecordV1,
    EditorialRetrievalContextV1,
    EpisodeVoiceStateV1,
    ExpressionCatalogV1,
    ExpressionRecordV1,
    PaletteItemReasonV1,
    PaletteItemV1,
    RetrievalTraceItemV1,
    RetrievalTraceV1,
    StoryVoicePaletteV1,
)
from .normalize import diacritic_insensitive_tokens_v1, retrieval_tokens_v1


class StoryComedyBudgetV1(StrEnum):
    DISABLED = "COMEDY_DISABLED"
    LOW = "COMEDY_LOW"
    NORMAL = "COMEDY_NORMAL"
    HIGH = "COMEDY_HIGH"


class ControlledTermUsageRoleV1(StrEnum):
    FACTUAL_CONTEXT = "factual_context"
    DECORATIVE_CONTEXT = "decorative_context"


def controlled_term_usage_role_v1(
    record: ControlledTermRecordV1,
) -> ControlledTermUsageRoleV1:
    if (
        "generational_language" in record.domains
        or "generational-marker" in record.risk_tags
    ):
        return ControlledTermUsageRoleV1.DECORATIVE_CONTEXT
    return ControlledTermUsageRoleV1.FACTUAL_CONTEXT


def story_comedy_budget_v1(
    context: EditorialRetrievalContextV1,
) -> StoryComedyBudgetV1:
    if context.comedy_disabled or context.victim_sensitive or context.tragedy_sensitive:
        return StoryComedyBudgetV1.DISABLED
    if context.humor_intensity <= 1:
        return StoryComedyBudgetV1.LOW
    if context.humor_intensity >= 3:
        return StoryComedyBudgetV1.HIGH
    return StoryComedyBudgetV1.NORMAL


def _strong_thresholds(budget: StoryComedyBudgetV1) -> tuple[int, int]:
    if budget is StoryComedyBudgetV1.LOW:
        return 6, 6
    if budget is StoryComedyBudgetV1.NORMAL:
        return 6, 6
    if budget is StoryComedyBudgetV1.HIGH:
        return 6, 6
    return 100, 100


def _context_tags(context: EditorialRetrievalContextV1) -> frozenset[str]:
    tags = set(context.topic_tags) | set(context.categories) | set(context.keywords)
    for name in (
        "bureaucracy",
        "patronage",
        "unfinished_project",
        "disinformation",
        "entertainment",
        "international",
        "political_context",
        "meme_context",
    ):
        if getattr(context, name):
            tags.add(name.removesuffix("_context"))
    if context.region:
        tags.add(context.region.casefold())
    return frozenset(tag.casefold() for tag in tags)


def _temporal_enabled(
    enabled: bool,
    active_from: datetime | None,
    active_until: datetime | None,
    now: datetime,
) -> bool:
    if not enabled:
        return False
    moment = now if now.tzinfo else now.replace(tzinfo=UTC)
    return not (
        (active_from is not None and moment < active_from)
        or (active_until is not None and moment > active_until)
    )


def _expression_score(
    record: ExpressionRecordV1,
    context: EditorialRetrievalContextV1,
    state: EpisodeVoiceStateV1,
    now: datetime,
) -> tuple[int | None, tuple[str, ...], tuple[tuple[str, int], ...]]:
    if record.owner_class == "REJECT_EDITOR" or not _temporal_enabled(
        record.enabled, record.active_from, record.active_until, now
    ):
        return None, ("hard_gate",), ()
    if context.victim_sensitive or context.tragedy_sensitive:
        return None, ("humor_safety_gate",), ()
    if record.raw and (
        not context.raw_eligible
        or context.victim_sensitive
        or context.tragedy_sensitive
        or context.profanity_ceiling < 2
    ):
        return None, ("raw_gate",), ()
    if record.regionalism and (
        context.region is None
        or context.region.casefold()
        not in {region.casefold() for region in record.regions}
    ):
        return None, ("region_gate",), ()
    if record.meme and not (context.meme_context or context.entertainment):
        return None, ("meme_gate",), ()
    if record.expression_id in state.used_expression_ids:
        return None, ("max_per_episode_gate",), ()
    context_tokens = retrieval_tokens_v1(
        context.title,
        context.summary,
        *context.keywords,
        *context.topic_tags,
        *context.categories,
    )
    context_ascii = diacritic_insensitive_tokens_v1(
        context.title, context.summary, *context.keywords, *context.topic_tags
    )
    record_tokens = retrieval_tokens_v1(
        record.text, record.semantic_gloss, *record.keywords, *record.semantic_families
    )
    record_ascii = diacritic_insensitive_tokens_v1(
        record.text, record.semantic_gloss, *record.keywords, *record.semantic_families
    )
    overlap = len(context_tokens & record_tokens)
    explicit_text_match = (
        record.text.casefold()
        in " ".join((context.title, context.summary, *context.keywords)).casefold()
    )
    if not overlap:
        overlap = min(1, len(context_ascii & record_ascii))
    tag_overlap = len(
        _context_tags(context) & {tag.casefold() for tag in record.semantic_families}
    )
    semantic = min(4, overlap + tag_overlap * 2)
    context_match = min(3, tag_overlap * 2 + int(overlap > 0))
    owner_fit = 2 if record.owner_class == "KEEP_DEFAULT" else 1
    naturalness = 2 if record.owner_class in {"KEEP_DEFAULT", "SPECIAL_MEME"} else 1
    repetition = (
        -3 if set(record.semantic_families) & set(state.used_expression_families) else 0
    )
    risk = (
        -4 if context.victim_sensitive and "victim_targeting" in record.risk_tags else 0
    )
    components = (
        ("semantic_context", semantic),
        ("context_match", context_match),
        ("owner_fit", owner_fit),
        ("naturalness_currentness", naturalness),
        ("repetition_penalty", repetition),
        ("risk_penalty", risk),
    )
    score = sum(value for _, value in components)
    threshold = 4 if record.owner_class.startswith("SPECIAL") else 3
    if score < threshold or semantic == 0:
        return None, ("insufficient_relevance",), components
    reasons = ["owner_class", "stable_tiebreak"]
    if overlap:
        reasons.append("keyword_match")
    if explicit_text_match:
        reasons.append("explicit_text_match")
    if tag_overlap:
        reasons.append("semantic_family_match")
    if record.regionalism:
        reasons.append("region_match")
    if repetition:
        reasons.append("repetition_penalty")
    return score, tuple(reasons), components


def _controlled_gate(
    record: ControlledTermRecordV1,
    context: EditorialRetrievalContextV1,
    state: EpisodeVoiceStateV1,
    now: datetime,
) -> tuple[int | None, tuple[str, ...]]:
    if not _temporal_enabled(
        record.enabled, record.active_from, record.active_until, now
    ):
        return None, ("temporal_gate",)
    usage = dict(state.controlled_term_usage).get(record.term_id, 0)
    if usage >= record.max_per_episode:
        return None, ("max_per_episode_gate",)
    tags = _context_tags(context)
    term = record.term.casefold()
    eligible = bool(tags & {domain.casefold() for domain in record.domains})
    if term == "fake news":
        eligible = context.disinformation or bool(
            tags & {"conspiracy", "explicit_denial"}
        )
    elif term == "sinecură":
        eligible = context.patronage or bool(tags & {"appointments", "clientelism"})
    elif term in {"suveranist", "pesedaurii", "pesedizat"}:
        story_tokens = retrieval_tokens_v1(
            context.title, context.summary, *context.keywords
        )
        term_tokens = retrieval_tokens_v1(record.term)
        eligible = context.political_context and bool(story_tokens & term_tokens)
    elif term == "vibe-ul":
        eligible = context.meme_context or context.entertainment
    if not eligible:
        return None, ("context_gate",)
    score = 6 + min(3, len(tags & {domain.casefold() for domain in record.domains}))
    return score, ("context_gate_passed", "temporal_gate_passed", "stable_tiebreak")


def _device_score(
    record: ComedyDeviceRecordV1,
    context: EditorialRetrievalContextV1,
    state: EpisodeVoiceStateV1,
) -> tuple[int | None, tuple[str, ...]]:
    if record.device_id in state.used_device_ids:
        return None, ("max_per_episode_gate",)
    if (context.tragedy_sensitive or context.victim_sensitive) and set(
        record.risk_tags
    ) & {"roast", "victim_targeting", "raw"}:
        return None, ("tragedy_gate",)
    tags = _context_tags(context)
    matches = tags & {
        item.casefold() for item in (*record.semantic_affordances, *record.best_for)
    }
    if not matches:
        return None, ("insufficient_relevance",)
    score = 5 + min(3, len(matches))
    if record.family in state.used_device_families:
        score -= 3
    if score < 4:
        return None, ("repetition_penalty",)
    return score, ("semantic_family_match", "context_gate_passed", "stable_tiebreak")


def retrieve_story_voice_palette_with_trace_v1(
    *,
    catalog: ExpressionCatalogV1,
    context: EditorialRetrievalContextV1,
    episode_state: EpisodeVoiceStateV1,
    now: datetime | None = None,
) -> tuple[StoryVoicePaletteV1, RetrievalTraceV1]:
    moment = now or datetime.now(UTC)
    budget = story_comedy_budget_v1(context)
    expression_threshold, device_threshold = _strong_thresholds(budget)
    trace: list[RetrievalTraceItemV1] = []
    expression_scores: list[tuple[int, str, PaletteItemV1]] = []
    surfaces = {
        item.source_expression_id: item.surface for item in catalog.preferred_surfaces
    }
    for record in catalog.expressions:
        score, reasons, components = _expression_score(
            record, context, episode_state, moment
        )
        selected = score is not None
        trace.append(
            RetrievalTraceItemV1(record.expression_id, selected, reasons, score)
        )
        if (
            selected
            and score is not None
            and (
                "explicit_text_match" in reasons
                or (
                    score >= expression_threshold and "semantic_family_match" in reasons
                )
            )
        ):
            expression_scores.append(
                (
                    -score,
                    record.expression_id,
                    PaletteItemV1(
                        authority_id=record.expression_id,
                        display_text=surfaces.get(record.expression_id)
                        or record.preferred_surface
                        or record.text,
                        family=record.semantic_families[0]
                        if record.semantic_families
                        else "expression",
                        reason=PaletteItemReasonV1(reasons, components, score),
                    ),
                )
            )
    expression_scores.sort(key=lambda item: (item[0], item[1]))
    tools: list[tuple[int, str, str, PaletteItemV1]] = []
    for record in catalog.controlled_terms:
        score, reasons = _controlled_gate(record, context, episode_state, moment)
        trace.append(
            RetrievalTraceItemV1(record.term_id, score is not None, reasons, score)
        )
        if score is not None:
            tools.append(
                (
                    -score,
                    record.term_id,
                    "controlled",
                    PaletteItemV1(
                        record.term_id,
                        record.term,
                        record.domains[0],
                        PaletteItemReasonV1(
                            reasons, (("context_match", score),), score
                        ),
                    ),
                )
            )
    for record in catalog.comedy_devices:
        score, reasons = _device_score(record, context, episode_state)
        trace.append(
            RetrievalTraceItemV1(record.device_id, score is not None, reasons, score)
        )
        if score is not None and score >= device_threshold:
            section = "signature" if record.signature_capable else "device"
            tools.append(
                (
                    -score,
                    record.device_id,
                    section,
                    PaletteItemV1(
                        record.device_id,
                        record.structure,
                        record.family,
                        PaletteItemReasonV1(
                            reasons, (("context_match", score),), score
                        ),
                    ),
                )
            )
    controlled_candidates = sorted(
        (item for item in tools if item[2] == "controlled"),
        key=lambda item: (item[0], item[1]),
    )
    comedy = [(*item[:2], "expression", item[2]) for item in expression_scores] + [
        (item[0] - 2, item[1], item[2], item[3])
        for item in tools
        if item[2] != "controlled"
    ]
    comedy.sort(key=lambda item: (item[0], item[1]))
    primary = comedy[:1] if budget is not StoryComedyBudgetV1.DISABLED else []
    term_records = {item.term_id: item for item in catalog.controlled_terms}
    suppressed_decorative_ids = {
        item[1]
        for item in controlled_candidates
        if primary
        and controlled_term_usage_role_v1(term_records[item[1]])
        is ControlledTermUsageRoleV1.DECORATIVE_CONTEXT
    }
    controlled = [
        item
        for item in controlled_candidates
        if item[1] not in suppressed_decorative_ids
    ][:1]
    if suppressed_decorative_ids:
        trace = [
            (
                RetrievalTraceItemV1(
                    item.authority_id,
                    False,
                    ("decorative_controlled_term_mutually_exclusive_with_comedy_tool",),
                    item.score,
                )
                if item.authority_id in suppressed_decorative_ids
                else item
            )
            for item in trace
        ]
    palette = StoryVoicePaletteV1(
        event_id=context.event_id,
        expressions=tuple(item[3] for item in primary if item[2] == "expression"),
        controlled_terms=tuple(item[3] for item in controlled),
        comedy_devices=tuple(item[3] for item in primary if item[2] == "device"),
        signature_devices=tuple(item[3] for item in primary if item[2] == "signature"),
    )
    return palette, RetrievalTraceV1(tuple(trace))


def retrieve_story_voice_palette_v1(
    *,
    catalog: ExpressionCatalogV1,
    context: EditorialRetrievalContextV1,
    episode_state: EpisodeVoiceStateV1,
    now: datetime | None = None,
) -> StoryVoicePaletteV1:
    palette, _ = retrieve_story_voice_palette_with_trace_v1(
        catalog=catalog,
        context=context,
        episode_state=episode_state,
        now=now,
    )
    return palette


__all__ = (
    "ControlledTermUsageRoleV1",
    "StoryComedyBudgetV1",
    "controlled_term_usage_role_v1",
    "retrieve_story_voice_palette_v1",
    "retrieve_story_voice_palette_with_trace_v1",
    "story_comedy_budget_v1",
)
