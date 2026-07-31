"""Conservative, deterministic matching of articles to recent events."""

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from pastila_scout.normalization import normalize_title

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_STOP_WORDS = {
    "a",
    "after",
    "an",
    "and",
    "at",
    "de",
    "din",
    "dupa",
    "from",
    "in",
    "investigation",
    "km",
    "la",
    "of",
    "o",
    "pe",
    "pentru",
    "the",
    "un",
    "unei",
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
}


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
    left_tokens = _meaningful_tokens(left_normalized)
    right_tokens = _meaningful_tokens(right_normalized)
    shared = left_tokens & right_tokens
    overlap = 0.0
    if len(shared) >= 2:
        overlap = len(shared) / min(len(left_tokens), len(right_tokens))
    sequence = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    return max(overlap, sequence if sequence >= 0.8 else 0.0)


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
    tokens = {_SYNONYMS.get(token, token) for token in _WORD_RE.findall(ascii_title)}
    return {
        token
        for token in tokens
        if token not in _STOP_WORDS and not token.isdecimal() and len(token) > 1
    }
