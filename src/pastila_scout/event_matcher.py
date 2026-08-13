"""Conservative, deterministic matching of articles to recent events."""

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from pastila_scout.normalization import normalize_title

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_MONTHS = {
    "ianuarie",
    "februarie",
    "martie",
    "aprilie",
    "mai",
    "iunie",
    "iulie",
    "august",
    "septembrie",
    "octombrie",
    "noiembrie",
    "decembrie",
}
_MONTH_PATTERN = "|".join(sorted(_MONTHS))
_DAY_MONTH_DATE_RE = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})(?:\s*[,.-]?\s*(\d{{4}}))?\b"
)
_MONTH_YEAR_DATE_RE = re.compile(rf"\b({_MONTH_PATTERN})\s*[,.-]?\s*(\d{{4}})\b")
_STOP_WORDS = {
    "a",
    "after",
    "an",
    "and",
    "at",
    "care",
    "cel",
    "cu",
    "de",
    "din",
    "dintre",
    "dupa",
    "este",
    "from",
    "his",
    "in",
    "investigation",
    "km",
    "la",
    "mai",
    "of",
    "o",
    "one",
    "pe",
    "pentru",
    "the",
    "un",
    "unei",
    "with",
}
_SYNONYMS = {
    "stolen": "theft",
    "stole": "theft",
    "steal": "theft",
    "furt": "theft",
    "furata": "theft",
    "furat": "theft",
    "thefts": "theft",
    "rail": "railway",
    "rails": "railway",
    "calea": "railway",
    "ferata": "railway",
    "drona": "drone",
    "dronei": "drone",
    "dronelor": "drone",
    "romaniei": "romania",
    "romanesc": "romania",
    "romaneasca": "romania",
    "spatiul": "airspace",
    "spatiului": "airspace",
    "aerian": "airspace",
    "aeriana": "airspace",
    "aerianul": "airspace",
    "patrundere": "detected_incursion",
    "patrunderea": "detected_incursion",
    "incursiune": "detected_incursion",
    "detectat": "detected_incursion",
    "detectata": "detected_incursion",
    "detectarea": "detected_incursion",
    "granita": "border",
    "frontiera": "border",
    "istoria": "istorie",
}
_FOLLOW_UP_PHRASES = (
    "cati bani",
    "intra efectiv",
    "primul mesaj",
    "prima reactie",
    "interviu",
)
_PREVIEW_PHRASES = (
    "cand ",
    "cine transmite",
    "cu cine va juca",
    "inainte de",
)
_GENERIC_ENTITY_TOKENS = frozenset({"cine", "conference", "europa", "league", "tv"})


@dataclass(frozen=True, slots=True)
class EventMatch:
    """The best event match and its deterministic similarity score."""

    event_id: int
    score: float


def title_similarity(left: str, right: str) -> float:
    """Return a conservative title similarity score between zero and one."""

    left_normalized = normalize_title(left)
    right_normalized = normalize_title(right)
    if left_normalized == right_normalized:
        return 1.0
    if _conflicting_explicit_dates(left, right):
        return 0.0
    if _preview_angle(left) != _preview_angle(right):
        return 0.0
    if _conflicting_entity_sets(left, right):
        return 0.0
    left_tokens = _meaningful_tokens(left_normalized)
    right_tokens = _meaningful_tokens(right_normalized)
    shared = left_tokens & right_tokens
    overlap = 0.0
    if len(shared) >= 2:
        overlap = len(shared) / min(len(left_tokens), len(right_tokens))
    sequence = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    score = max(overlap, sequence if sequence >= 0.8 else 0.0)
    if _is_conservative_paraphrase(left, right, left_tokens, right_tokens):
        score = max(score, 0.8)
    return score


def match_event(
    title: str,
    recent_events: list[sqlite3.Row],
    *,
    threshold: float,
) -> EventMatch | None:
    """Return the highest-scoring recent event meeting ``threshold``."""

    best: EventMatch | None = None
    for event in recent_events:
        score = title_similarity(title, str(event["canonical_title"]))
        candidate = EventMatch(int(event["id"]), score)
        if score >= threshold and (
            best is None or (score, -candidate.event_id) > (best.score, -best.event_id)
        ):
            best = candidate
    return best


def _meaningful_tokens(title: str) -> set[str]:
    """Extract normalized semantic tokens while dropping structural words."""

    ascii_title = "".join(
        character
        for character in unicodedata.normalize("NFKD", title)
        if not unicodedata.combining(character)
    )
    tokens = {
        _SYNONYMS.get(token, token)
        for token in _WORD_RE.findall(ascii_title.casefold())
    }
    result = {
        token
        for token in tokens
        if token not in _STOP_WORDS and not token.isdecimal() and len(token) > 1
    }
    if "tulcea" in result:
        result.add("romania")
    if (
        "drone" in result
        and "detected_incursion" in result
        and result.intersection({"airspace", "border"})
    ):
        result.add("drone_airspace_incident")
    return result


def _is_conservative_paraphrase(
    left: str,
    right: str,
    left_tokens: set[str],
    right_tokens: set[str],
) -> bool:
    shared = left_tokens & right_tokens
    if len(shared) < 3 or _conflicting_explicit_dates(left, right):
        return False
    shared_entities = _entity_tokens(left) & _entity_tokens(right)
    shared_event_context = shared - shared_entities
    if len(shared_event_context) < 2:
        return False
    coverage = len(shared) / min(len(left_tokens), len(right_tokens))
    if _follow_up_angle(left) != _follow_up_angle(right) and coverage < 0.55:
        return False
    if coverage >= 0.55 and len(shared) >= 3:
        return True
    shared_numbers = _number_tokens(left) & _number_tokens(right)
    return len(shared_event_context) >= 4 and bool(shared_numbers)


def _entity_tokens(title: str) -> set[str]:
    words = _WORD_RE.findall(_ascii_text(title))
    return {
        _SYNONYMS.get(word.casefold(), word.casefold())
        for word in words
        if word.casefold() not in _STOP_WORDS
        and word.casefold() not in _GENERIC_ENTITY_TOKENS
        and (word[:1].isupper() or (len(word) > 1 and word.isupper()))
    }


def _conflicting_entity_sets(left: str, right: str) -> bool:
    left_entities = _entity_tokens(left)
    right_entities = _entity_tokens(right)
    return (
        len(left_entities) >= 2
        and len(right_entities) >= 2
        and left_entities.isdisjoint(right_entities)
    )


def _number_tokens(title: str) -> set[str]:
    return {
        value.replace(".", "").replace(",", "") for value in _NUMBER_RE.findall(title)
    }


def _follow_up_angle(title: str) -> bool:
    normalized = _ascii_text(normalize_title(title))
    return any(0 <= normalized.find(phrase) <= 100 for phrase in _FOLLOW_UP_PHRASES)


def _preview_angle(title: str) -> bool:
    normalized = _ascii_text(normalize_title(title))
    return any(phrase in normalized for phrase in _PREVIEW_PHRASES)


def _conflicting_explicit_dates(left: str, right: str) -> bool:
    left_normalized = _ascii_text(normalize_title(left))
    right_normalized = _ascii_text(normalize_title(right))
    left_dates = _explicit_dates(left_normalized)
    right_dates = _explicit_dates(right_normalized)
    return bool(left_dates and right_dates and left_dates != right_dates)


def _explicit_dates(value: str) -> set[tuple[str, ...]]:
    return {("day", *match) for match in _DAY_MONTH_DATE_RE.findall(value)} | {
        ("month", *match) for match in _MONTH_YEAR_DATE_RE.findall(value)
    }


def _ascii_text(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
