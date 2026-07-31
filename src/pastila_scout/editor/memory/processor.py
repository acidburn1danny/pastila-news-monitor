"""Deterministic verdict interpretation and cumulative pattern detection."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict

from pastila_scout.editor.memory.models import (
    CandidateFinding,
    EditorialCategory,
    EditorialMemory,
    EditorialMemoryUpdate,
    EditorialObservation,
    EditorialPattern,
    EditorialProfile,
    ObservationStrength,
    Recommendation,
    Sentiment,
    VerdictInput,
    VerdictProcessingResult,
    VerdictSummary,
)

PROFILE_EVIDENCE_THRESHOLD = 3
CANDIDATE_EVIDENCE_THRESHOLD = 3

_CATEGORY_TERMS: tuple[tuple[EditorialCategory, tuple[str, ...]], ...] = (
    (EditorialCategory.INTRODUCTION, ("intro", "introduc")),
    (EditorialCategory.TRANSITIONS, ("tranzi", "transition")),
    (EditorialCategory.ENDING, ("final", "ending", "încheier", "incheier")),
    (EditorialCategory.PACING, ("ritm", "pacing", "lent", "slow")),
    (EditorialCategory.PUNCHLINES, ("poant", "punchline")),
    (EditorialCategory.SARCASM, ("sarcas",)),
    (EditorialCategory.IRONY, ("ironi",)),
    (EditorialCategory.HUMOR, ("umor", "comic", "amuzant", "funny")),
    (EditorialCategory.EXPLANATION, ("explic", "technical", "tehnic")),
    (EditorialCategory.CONTEXT_LENGTH, ("prea lung", "too long", "context")),
    (EditorialCategory.STORY_ORDERING, ("ordine", "ordering")),
    (EditorialCategory.STORY_SELECTION, ("selec", "aleger")),
    (EditorialCategory.STORY_STRUCTURE, ("story", "poveste", "subiect")),
    (EditorialCategory.NARRATIVE_FLOW, ("flow", "nara", "cursiv")),
    (EditorialCategory.EMOTIONAL_IMPACT, ("emo",)),
    (EditorialCategory.POLITICAL_COMMENTARY, ("politic",)),
    (EditorialCategory.AUDIENCE_ENGAGEMENT, ("public", "audien", "engagement")),
)
_NEGATIVE_TERMS = (
    "prea ",
    "too ",
    "weak",
    "slab",
    "poor",
    "prost",
    "agresiv",
    "not enough",
    "insuficient",
    "should be shorter",
    "slow",
)
_POSITIVE_TERMS = (
    "excelent",
    "excellent",
    "foarte bun",
    "very good",
    "bun",
    "good",
    "great",
    "strong",
    "puternic",
    "loved",
    "mi-a plăcut",
    "mi-a placut",
)
_HIGH_TERMS = ("excelent", "excellent", "foarte", "very", "great", "loved")


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w\săâîșț]", " ", normalized)
    return " ".join(normalized.split())


def _sentiment(text: str) -> Sentiment | None:
    negative = any(term in text for term in _NEGATIVE_TERMS)
    positive = any(term in text for term in _POSITIVE_TERMS)
    if negative == positive:
        return None
    return Sentiment.NEGATIVE if negative else Sentiment.POSITIVE


def _category(text: str) -> EditorialCategory | None:
    return next(
        (
            category
            for category, terms in _CATEGORY_TERMS
            if any(x in text for x in terms)
        ),
        None,
    )


def _strength(text: str, score: float | None) -> ObservationStrength:
    if any(term in text for term in _HIGH_TERMS) or (
        score is not None and (score <= 3 or score >= 9)
    ):
        return ObservationStrength.HIGH
    if score is not None and (score <= 5 or score >= 8):
        return ObservationStrength.MEDIUM
    return ObservationStrength.LOW


def _score_for(verdict: VerdictInput, category: EditorialCategory) -> float | None:
    needle = category.value.casefold()
    for item in verdict.section_scores:
        section = item.section.casefold()
        if needle in section or section in needle:
            return item.score
    return verdict.overall_score


def _finding(category: EditorialCategory, sentiment: Sentiment, text: str) -> str:
    qualifiers = (
        "too long",
        "prea lung",
        "too much explanation",
        "explică prea mult",
        "explica prea mult",
        "weak",
        "slab",
        "aggressive",
        "agresiv",
        "slow",
        "excellent",
        "excelent",
        "lent",
        "strong",
        "puternic",
        "good",
        "bun",
    )
    qualifier = next((item for item in qualifiers if item in text), sentiment.value)
    return f"{category.value}: {qualifier}"


def interpret_verdict(verdict: VerdictInput) -> tuple[EditorialObservation, ...]:
    """Extract supported editorial observations from explicit verdict comments."""

    observations: list[EditorialObservation] = []
    for comment in verdict.comments:
        for sentence in filter(None, re.split(r"(?<=[.!?])\s+|[;\n]+", comment)):
            text = _normalized_text(sentence)
            category = _category(text)
            sentiment = _sentiment(text)
            if category is None or sentiment is None:
                continue
            normalized_finding = _finding(category, sentiment, text)
            identity = (
                f"{verdict.episode_id}\x1f{verdict.timestamp}\x1f"
                f"{sentence}\x1f{normalized_finding}"
            )
            identifier = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            observations.append(
                EditorialObservation(
                    observation_id=f"EO-{identifier}",
                    episode_id=verdict.episode_id,
                    timestamp=verdict.timestamp,
                    category=category,
                    sentiment=sentiment,
                    strength=_strength(text, _score_for(verdict, category)),
                    affected_section=category.value,
                    original_comment=sentence.strip(),
                    normalized_finding=normalized_finding,
                )
            )
    return tuple(observations)


def detect_patterns(memory: EditorialMemory) -> tuple[EditorialPattern, ...]:
    """Aggregate observations by stable finding and distinct episode."""

    grouped: dict[
        tuple[EditorialCategory, str, Sentiment], list[EditorialObservation]
    ] = defaultdict(list)
    for item in memory.observations:
        grouped[(item.category, item.normalized_finding, item.sentiment)].append(item)
    patterns = []
    for (category, finding, sentiment), items in sorted(
        grouped.items(), key=lambda item: tuple(str(value) for value in item[0])
    ):
        episodes = tuple(sorted({item.episode_id for item in items}))
        patterns.append(
            EditorialPattern(
                category=category,
                normalized_finding=finding,
                sentiment=sentiment,
                occurrence_count=len(items),
                episode_ids=episodes,
                supporting_observation_ids=tuple(
                    sorted(item.observation_id for item in items)
                ),
                confidence=min(100, 20 + 20 * len(episodes)),
            )
        )
    return tuple(patterns)


def _profile(patterns: tuple[EditorialPattern, ...], version: int) -> EditorialProfile:
    established = [
        item for item in patterns if len(item.episode_ids) >= PROFILE_EVIDENCE_THRESHOLD
    ]
    strengths = tuple(
        item.normalized_finding
        for item in established
        if item.sentiment == Sentiment.POSITIVE
    )
    weaknesses = tuple(
        item.normalized_finding
        for item in established
        if item.sentiment == Sentiment.NEGATIVE
    )
    emerging = tuple(
        item.normalized_finding
        for item in patterns
        if 1 < len(item.episode_ids) < PROFILE_EVIDENCE_THRESHOLD
    )
    return EditorialProfile(
        profile_version=version,
        current_strengths=strengths,
        current_weaknesses=weaknesses,
        emerging_trends=emerging,
    )


def process_verdict(
    verdict: VerdictInput, memory: EditorialMemory | None = None
) -> VerdictProcessingResult:
    """Learn from one verdict without changing any generation or prompt behavior."""

    current = memory or EditorialMemory()
    extracted = interpret_verdict(verdict)
    known_ids = {item.observation_id for item in current.observations}
    added = tuple(item for item in extracted if item.observation_id not in known_ids)
    reinforced = sum(
        1
        for item in added
        if any(
            old.normalized_finding == item.normalized_finding
            and old.sentiment == item.sentiment
            for old in current.observations
        )
    )
    observations = tuple(
        sorted((*current.observations, *added), key=lambda x: x.observation_id)
    )
    intermediate = EditorialMemory(observations=observations, profile=current.profile)
    patterns = detect_patterns(intermediate)
    proposed_profile = _profile(patterns, current.profile.profile_version)
    profile_changed = proposed_profile.model_dump(
        exclude={"profile_version"}
    ) != current.profile.model_dump(exclude={"profile_version"})
    profile = proposed_profile.model_copy(
        update={
            "profile_version": current.profile.profile_version + int(profile_changed)
        }
    )
    updated = EditorialMemory(observations=observations, profile=profile)
    candidates = tuple(
        CandidateFinding(
            **item.model_dump(),
            recommendation=(
                Recommendation.POSSIBLE_EDITORIAL_IMPROVEMENT
                if item.sentiment == Sentiment.NEGATIVE
                else Recommendation.POTENTIAL_PROMPT_EXPERIMENT
            ),
        )
        for item in patterns
        if len(item.episode_ids) >= CANDIDATE_EVIDENCE_THRESHOLD
    )
    return VerdictProcessingResult(
        verdict_summary=VerdictSummary(
            overall_score=verdict.overall_score,
            positive_findings=tuple(
                item.normalized_finding
                for item in added
                if item.sentiment == Sentiment.POSITIVE
            ),
            negative_findings=tuple(
                item.normalized_finding
                for item in added
                if item.sentiment == Sentiment.NEGATIVE
            ),
            observations_created=len(added),
        ),
        memory_update=EditorialMemoryUpdate(
            observations_added=len(added),
            existing_observations_reinforced=reinforced,
            editorial_categories_updated=tuple(sorted({x.category for x in added})),
        ),
        editorial_profile=profile,
        candidate_findings=candidates,
        memory=updated,
    )
