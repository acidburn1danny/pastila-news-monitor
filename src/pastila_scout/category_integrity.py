"""Deterministic Scout category-integrity rules."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

CATEGORY_ORDER = (
    "Politica",
    "Social",
    "Economie",
    "Conspiratii",
    "CanCan",
    "Diverse",
    "Externe",
)

_ENGLISH_MARKERS = frozenset(
    {
        "after",
        "already",
        "allegedly",
        "all",
        "admits",
        "amid",
        "and",
        "announces",
        "before",
        "are",
        "as",
        "at",
        "behind",
        "best",
        "brother",
        "calls",
        "coding",
        "coming",
        "confesses",
        "could",
        "dead",
        "death",
        "debuts",
        "deliver",
        "details",
        "detailing",
        "does",
        "faces",
        "for",
        "from",
        "gets",
        "has",
        "hard",
        "have",
        "help",
        "helped",
        "her",
        "his",
        "how",
        "inside",
        "introduces",
        "into",
        "is",
        "isn't",
        "make",
        "makes",
        "mandatory",
        "marriage",
        "journey",
        "launch",
        "minister",
        "merging",
        "movie",
        "more",
        "needs",
        "new",
        "of",
        "on",
        "open",
        "out",
        "over",
        "prime",
        "reveals",
        "really",
        "redesigned",
        "reportedly",
        "says",
        "shares",
        "separate",
        "service",
        "sources",
        "star",
        "stay",
        "startup",
        "story",
        "sued",
        "talks",
        "tears",
        "than",
        "that",
        "the",
        "their",
        "this",
        "to",
        "users",
        "while",
        "up",
        "was",
        "wanted",
        "what",
        "when",
        "where",
        "who",
        "why",
        "wife",
        "will",
        "with",
        "years",
        "you",
        "your",
    }
)
_ROMANIAN_MARKERS = frozenset(
    {
        "al",
        "ale",
        "au",
        "care",
        "ce",
        "cu",
        "cum",
        "de",
        "din",
        "dupa",
        "este",
        "fost",
        "la",
        "lui",
        "nou",
        "noua",
        "pentru",
        "pe",
        "prin",
        "si",
        "soc",
        "sunt",
        "un",
        "unei",
        "unui",
    }
)
_QUOTED = re.compile(r'"[^"\n]+"|“[^”\n]+”|„[^”\n]+”')
_TOKEN = re.compile(r"[A-Za-zÀ-ž]+(?:['’][A-Za-zÀ-ž]+)?")


def is_clearly_english_title(title: str) -> bool:
    """Return true only for a headline with strong, unambiguous English evidence."""

    if type(title) is not str or not title.strip():
        return False
    unquoted = _QUOTED.sub(" ", title)
    tokens = tuple(_normalized_token(value) for value in _TOKEN.findall(unquoted))
    tokens = tuple(value for value in tokens if len(value) > 1)
    if len(tokens) < 3:
        return False
    english = sum(value in _ENGLISH_MARKERS for value in tokens)
    romanian = sum(value in _ROMANIAN_MARKERS for value in tokens)
    romanian += int(any(character in "ăâîșțĂÂÎȘȚ" for character in unquoted))
    return english >= 2 and english >= romanian + 2


def article_categories(title: str, categories: Iterable[str]) -> frozenset[str]:
    """Return authoritative categories for one article title."""

    if is_clearly_english_title(title):
        return frozenset({"Externe"})
    return frozenset(categories)


def _normalized_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
