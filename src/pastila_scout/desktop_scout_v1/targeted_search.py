"""Deterministic local projection for strict ``Ultima Ora`` searches."""

from __future__ import annotations

import math
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_MAX_RESULTS = 10
# A single adjacent transposition in a six-letter name scores 0.83 with
# SequenceMatcher. Fuzzy support is still bounded by the separate exact-match gate.
_FUZZY_THRESHOLD = 0.83
_GENERIC = {
    "a",
    "an",
    "and",
    "breaking",
    "de",
    "din",
    "during",
    "for",
    "in",
    "la",
    "live",
    "news",
    "of",
    "ora",
    "pe",
    "pentru",
    "si",
    "stire",
    "the",
    "to",
    "ultima",
    "vizita",
    "visit",
}
_SYNONYMS = {
    "catastrofa": "disaster",
    "dezastru": "disaster",
    "dezastrul": "disaster",
    "teheran": "iran",
    "tehran": "iran",
}


@dataclass(frozen=True, slots=True)
class _ArticleScore:
    value: int
    published_at: datetime
    source_id: str


@dataclass(frozen=True, slots=True)
class _EventScore:
    event_id: int
    relevance: int
    matching_sources: int
    latest_relevant_at: datetime


def project_targeted_event_ids(
    *,
    database_path: Path,
    query: str,
    now: datetime,
    excluded_source_ids: tuple[str, ...] = (),
) -> tuple[int, ...]:
    """Return strict relevant event identities in deterministic rank order."""

    if (
        type(database_path) is not type(Path())
        or type(query) is not str
        or not query
        or type(now) is not datetime
        or now.tzinfo is None
        or type(excluded_source_ids) is not tuple
        or any(type(value) is not str or not value for value in excluded_source_ids)
    ):
        raise ValueError("Invalid targeted projection input")
    current = now.astimezone(UTC)
    cutoff = current - timedelta(hours=48)
    query_tokens = _significant_tokens(query)
    if len(query_tokens) < 2 or not database_path.is_file():
        return ()

    grouped: dict[int, list[_ArticleScore]] = {}
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT event_id, source_id, title, summary, published_at
               FROM articles
               WHERE event_id IS NOT NULL
                 AND published_at IS NOT NULL
                 AND julianday(published_at) >= julianday(?)
                 AND julianday(published_at) <= julianday(?)
               ORDER BY event_id, id""",
            (cutoff.isoformat(), current.isoformat()),
        ).fetchall()
    for row in rows:
        if str(row["source_id"]) in excluded_source_ids:
            continue
        published = _timestamp(row["published_at"])
        if published is None or published < cutoff or published > current:
            continue
        score = _score_article(
            query_tokens,
            title=str(row["title"]),
            summary="" if row["summary"] is None else str(row["summary"]),
        )
        if score is None:
            continue
        grouped.setdefault(int(row["event_id"]), []).append(
            _ArticleScore(score, published, str(row["source_id"]))
        )

    ranked = []
    for event_id, articles in grouped.items():
        ranked.append(
            _EventScore(
                event_id=event_id,
                relevance=max(item.value for item in articles),
                matching_sources=len({item.source_id for item in articles}),
                latest_relevant_at=max(item.published_at for item in articles),
            )
        )
    ranked.sort(
        key=lambda item: (
            -item.relevance,
            -item.matching_sources,
            -item.latest_relevant_at.timestamp(),
            item.event_id,
        )
    )
    return tuple(item.event_id for item in ranked[:_MAX_RESULTS])


def _score_article(
    query_tokens: tuple[str, ...], *, title: str, summary: str
) -> int | None:
    title_tokens = _significant_tokens(title)
    evidence_tokens = tuple(
        dict.fromkeys((*title_tokens, *_significant_tokens(summary)))
    )
    evidence_set = set(evidence_tokens)
    exact = {token for token in query_tokens if token in evidence_set}
    unmatched = [token for token in query_tokens if token not in exact]
    fuzzy = _fuzzy_matches(unmatched, evidence_set - exact)
    matched = len(exact) + len(fuzzy)
    required = 2 if len(query_tokens) == 2 else math.ceil(len(query_tokens) * 0.75)
    minimum_exact = 1 if len(query_tokens) == 2 else 2
    phrase = " ".join(query_tokens) in " ".join(evidence_tokens)
    if not phrase and (matched < required or len(exact) < minimum_exact):
        return None
    title_matches = sum(token in set(title_tokens) for token in query_tokens)
    return (
        matched * 1000 // len(query_tokens)
        + len(exact) * 200 // len(query_tokens)
        + title_matches * 150 // len(query_tokens)
        + (300 if phrase else 0)
    )


def _fuzzy_matches(query_tokens: list[str], evidence_tokens: set[str]) -> set[str]:
    matched = set()
    available = {token for token in evidence_tokens if len(token) >= 5}
    for query_token in query_tokens:
        if len(query_token) < 5:
            continue
        candidate = max(
            available,
            key=lambda token: SequenceMatcher(
                None, query_token, token, autojunk=False
            ).ratio(),
            default=None,
        )
        if (
            candidate is not None
            and SequenceMatcher(None, query_token, candidate, autojunk=False).ratio()
            >= _FUZZY_THRESHOLD
        ):
            matched.add(query_token)
            available.remove(candidate)
    return matched


def _significant_tokens(value: str) -> tuple[str, ...]:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", value).casefold()
        if not unicodedata.combining(character)
    )
    tokens = (_SYNONYMS.get(token, token) for token in _WORD_RE.findall(normalized))
    return tuple(
        dict.fromkeys(
            token
            for token in tokens
            if token not in _GENERIC and (len(token) > 1 or token.isdecimal())
        )
    )


def _timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC)
    except TypeError, ValueError:
        return None


__all__: tuple[str, ...] = ()
