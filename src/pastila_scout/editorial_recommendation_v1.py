"""Deterministic editorial recommendation over an existing Scout candidate pool."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime

_CAPS = {"Politica": 2, "Social": 3, "CanCan": 1, "Diverse": 3, "Externe": 2}
_PUBLIC = (
    "guvern",
    "presed",
    "parlament",
    "ministr",
    "primar",
    "politi",
    "institut",
    "statul",
    "autoritat",
    "administrat",
    "spital",
    "scoala",
    "justit",
    "legea",
    "legi",
    "legii",
    "legile",
    "legisl",
    "taxa",
    "taxe",
    "impozit",
    "buget",
    "se schimba regul",
    "noi reguli",
    "regulament",
    "uniunea europeana",
    "ue",
    "interes public",
    "serviciu public",
    "bani public",
    "public policy",
    "government",
    "white house",
    "congress",
    "court",
)
_CONTROVERSY = (
    "scandal",
    "corupt",
    "anchet",
    "dosar",
    "acuz",
    "fraud",
    "conflict",
    "controvers",
    "protest",
    "demis",
    "interzis",
    "abuz",
    "criza",
    "criticat",
    "investigat",
    "hypocr",
    "contradict",
    "lies",
    "threat",
    "war",
)
_SOCIAL = (
    "copil",
    "elev",
    "profesor",
    "medic",
    "pacient",
    "familie",
    "familia",
    "familiei",
    "familii",
    "angajat",
    "pension",
    "salari",
    "sarac",
    "victim",
    "mort",
    "morti",
    "moarte",
    "ranit",
    "sigurant",
    "sanatat",
    "educat",
    "locuint",
    "comunit",
    "discrimin",
    "human",
)
_ABSURD = (
    "absurd",
    "bizar",
    "incredibil",
    "neobisnuit",
    "halucinant",
    "ridicol",
    "surprinz",
    "socant",
    "straniu",
    "din greseala",
    "fake",
)
_PERSONALITY = (
    "milionar",
    "divort",
    "nunta",
    "iubit",
    "iubita",
    "relatie",
    "showbiz",
    "roast",
)
_SPORT = (
    "fotbal",
    "meci",
    "scor",
    "liga",
    "campionat",
    "calific",
    "turneu",
    "gol",
    "transfer",
    "antrenor",
    "sportiv",
    "atlet",
    "inot",
    "tenis",
    "echipa",
)
_SPORT_ROUTINE = (
    "scor",
    "rezultat",
    "calific",
    "clasament",
    "etapa",
    "meci",
    "transfer",
    "victorie",
    "infrangere",
    "gol",
    "finala",
    "semifinala",
    "antrenament",
)
_LOTO_ROUTINE = ("numere", "extragere", "report", "jackpot", "premiu", "castig")
_OTHER_ROUTINE = (
    "horoscop",
    "reteta",
    "prognoza meteo",
    "meteo pentru",
    "sfaturi pentru",
    "trucuri pentru",
    "rezultate financiare trimestriale",
)
_CELEBRITY_PROMO = (
    "imagini cu",
    "fotografii cu",
    "imagini adorabile",
    "performanta uriasa",
    "a publicat",
    "a postat",
    "topit dupa",
    "revine in",
)
_EXACT_TERMS = frozenset(
    {
        "court",
        "fake",
        "familia",
        "familie",
        "familiei",
        "familii",
        "gol",
        "legea",
        "legi",
        "legii",
        "legile",
        "lies",
        "moarte",
        "mort",
        "morti",
        "ue",
        "war",
    }
)


@dataclass(frozen=True, slots=True)
class EditorialCandidateV1:
    event_id: int
    title: str
    summary: str
    category: str
    source_count: int
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class EditorialEvidenceV1:
    event_id: int
    category: str
    source_count: int
    last_seen_at: datetime
    eligible: bool
    exclusion_reason: str | None
    public_interest: bool
    satire_roast: bool
    social_impact: bool
    absurdity: bool
    controversy: bool
    institutional: bool
    personality: bool
    routine_sport: bool
    routine_loto: bool
    editorial_score: int
    explanation: str
    recommendation_rank: int | None = None
    disposition: str = "eligible"


@dataclass(frozen=True, slots=True)
class EpisodeRecommendationV1:
    recommendations: tuple[EditorialEvidenceV1, ...]
    evaluations: tuple[EditorialEvidenceV1, ...]
    available_slots: int


def recommend_episode_v1(
    candidates: tuple[EditorialCandidateV1, ...],
) -> EpisodeRecommendationV1:
    """Recommend an advisory episode slate without mutating the supplied pool."""
    if len({item.event_id for item in candidates}) != len(candidates):
        raise ValueError("Duplicate editorial candidate")
    evaluated = tuple(_evaluate(item) for item in candidates)
    ranked = sorted((item for item in evaluated if item.eligible), key=_rank_key)
    selected: list[EditorialEvidenceV1] = []
    counts = {category: 0 for category in _CAPS}
    for category, target in (("Politica", 2), ("CanCan", 1)):
        for item in (value for value in ranked if value.category == category):
            if counts[category] == target:
                break
            selected.append(item)
            counts[category] += 1
    for item in ranked:
        if len(selected) == 10:
            break
        if item in selected or item.category not in _CAPS:
            continue
        if counts[item.category] < _CAPS[item.category]:
            selected.append(item)
            counts[item.category] += 1
    selected.sort(key=_rank_key)
    rank_by_id = {item.event_id: rank for rank, item in enumerate(selected, 1)}
    selected_ids = set(rank_by_id)
    final = []
    for item in evaluated:
        if item.event_id in selected_ids:
            final.append(
                replace(
                    item,
                    recommendation_rank=rank_by_id[item.event_id],
                    disposition="recommended",
                )
            )
        elif not item.eligible:
            final.append(item)
        elif counts.get(item.category, 0) >= _CAPS.get(item.category, 0):
            final.append(replace(item, disposition="eligible_but_category_cap_reached"))
        else:
            final.append(replace(item, disposition="eligible_but_below_episode_cutoff"))
    by_id = {item.event_id: item for item in final}
    recommendations = tuple(by_id[item.event_id] for item in selected)
    evaluations = tuple(sorted(final, key=lambda item: item.event_id))
    return EpisodeRecommendationV1(recommendations, evaluations, 10 - len(selected))


def _evaluate(candidate: EditorialCandidateV1) -> EditorialEvidenceV1:
    if (
        type(candidate.event_id) is not int
        or candidate.event_id <= 0
        or candidate.category not in _CAPS
        or type(candidate.source_count) is not int
        or candidate.source_count <= 0
        or type(candidate.last_seen_at) is not datetime
        or candidate.last_seen_at.utcoffset() is None
    ):
        raise ValueError("Invalid editorial candidate")
    text = _plain(f"{candidate.title} {candidate.summary}")
    controversy = _has(text, _CONTROVERSY)
    public_interest = _has(text, _PUBLIC)
    social = _has(text, _SOCIAL)
    absurdity = _has(text, _ABSURD)
    personality = _has(text, _PERSONALITY)
    sport = _has(text, _SPORT)
    routine_sport = (
        sport
        and _has(text, _SPORT_ROUTINE)
        and not (controversy or public_interest or absurdity)
    )
    loto = _has(text, ("loto", "loteria")) or (
        _has(text, ("joker",))
        and _has(text, ("numere", "extragere", "report", "jackpot"))
    )
    routine_loto = (
        loto
        and _has(text, _LOTO_ROUTINE)
        and not (controversy or public_interest or absurdity)
    )
    other_routine = _has(text, _OTHER_ROUTINE) and not (
        controversy or public_interest or social or absurdity
    )
    generic_celebrity_promotion = (
        candidate.category == "CanCan"
        and _has(text, _CELEBRITY_PROMO)
        and not (controversy or public_interest or absurdity or personality)
    )
    has_positive_evidence = any(
        (public_interest, social, absurdity, controversy, personality)
    )
    reason = (
        "routine_loto"
        if routine_loto
        else "routine_sport"
        if routine_sport
        else "routine_low_value"
        if other_routine
        else "generic_celebrity_promotion"
        if generic_celebrity_promotion
        else "insufficient_editorial_evidence"
        if not has_positive_evidence and candidate.source_count < 2
        else None
    )
    institutional = public_interest
    satire = controversy or absurdity or personality
    fit = sum((public_interest, social, absurdity, controversy, personality))
    score = fit * 6 + min(candidate.source_count, 10) * 2
    signals = [
        label
        for present, label in (
            (institutional, "institutie/interes public"),
            (controversy, "contradictie/controversa"),
            (social, "impact social"),
            (absurdity, "incident neobisnuit"),
            (personality, "monden/roast"),
        )
        if present
    ]
    explanation = f"{candidate.source_count} surse"
    if signals:
        explanation += "; " + "; ".join(signals)
    if reason:
        explanation += f"; exclus: {reason}"
    elif not signals:
        explanation += "; relevanta generala"
    return EditorialEvidenceV1(
        candidate.event_id,
        candidate.category,
        candidate.source_count,
        candidate.last_seen_at,
        reason is None,
        reason,
        public_interest,
        satire,
        social,
        absurdity,
        controversy,
        institutional,
        personality,
        routine_sport,
        routine_loto,
        score,
        explanation,
        disposition="excluded" if reason else "eligible",
    )


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(
        r"\s+", " ", "".join(c for c in normalized if not unicodedata.combining(c))
    )


def _has(text: str, terms: tuple[str, ...]) -> bool:
    return any(
        re.search(
            rf"(?<!\w){re.escape(term)}" + (r"(?!\w)" if term in _EXACT_TERMS else ""),
            text,
        )
        for term in terms
    )


def _rank_key(item: EditorialEvidenceV1) -> tuple[int, int, float, int]:
    return (
        -item.editorial_score,
        -item.source_count,
        -item.last_seen_at.timestamp(),
        item.event_id,
    )


__all__ = [
    "EditorialCandidateV1",
    "EditorialEvidenceV1",
    "EpisodeRecommendationV1",
    "recommend_episode_v1",
]
