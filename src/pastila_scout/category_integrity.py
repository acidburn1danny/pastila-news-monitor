"""Deterministic Scout category-integrity rules."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

CATEGORY_ORDER = (
    "Politica",
    "Social",
    "CanCan",
    "Diverse",
    "Externe",
)
DOMESTIC_TIE_ORDER = (
    "Social",
    "CanCan",
    "Diverse",
    "Politica",
)

AUTHORITATIVE_SOURCE_CATEGORIES = {
    "cancan": "CanCan",
    "click": "CanCan",
}

_LEGACY_CATEGORY_MAP = {"Economie": "Diverse", "Conspiratii": "CanCan"}

_DOMESTIC_MARKERS = {
    "Politica": frozenset(
        {
            "alegeri",
            "candidat",
            "coalitie",
            "guvern",
            "guvernul",
            "ministru",
            "parlament",
            "partid",
            "politic",
            "presedinte",
            "presedintie",
            "senat",
        }
    ),
    "Social": frozenset(
        {
            "accident",
            "concediat",
            "crima",
            "educatie",
            "loto",
            "loteria",
            "sanatate",
            "scoala",
        }
    ),
    "CanCan": frozenset(
        {
            "actor",
            "artista",
            "cantaret",
            "celebr",
            "divort",
            "iubit",
            "relatie",
            "vedeta",
            "conspiratie",
            "dezinformare",
            "fake",
            "manipulare",
        }
    ),
    "Diverse": frozenset({"incategorizabil"}),
}

_ENGLISH_MARKERS = frozenset(
    {
        "after",
        "already",
        "allegedly",
        "all",
        "about",
        "admits",
        "amid",
        "and",
        "announces",
        "before",
        "became",
        "are",
        "as",
        "at",
        "behind",
        "best",
        "brother",
        "by",
        "calls",
        "cancels",
        "coding",
        "coming",
        "confesses",
        "could",
        "dead",
        "death",
        "debuts",
        "deliver",
        "detail",
        "details",
        "detailing",
        "does",
        "down",
        "entire",
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
        "its",
        "it's",
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
        "now",
        "of",
        "on",
        "open",
        "orders",
        "out",
        "outside",
        "over",
        "prime",
        "president",
        "reveals",
        "really",
        "redesigned",
        "reportedly",
        "says",
        "shares",
        "so",
        "separate",
        "service",
        "series",
        "seasons",
        "show",
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
        "they",
        "this",
        "through",
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
    english += sum(_english_word_shape(value) for value in tokens)
    romanian = sum(value in _ROMANIAN_MARKERS for value in tokens)
    romanian += int(any(character in "ăâîșțĂÂÎȘȚ" for character in unquoted))
    return english >= 2 and english >= romanian + 2


def article_category(
    title: str,
    categories: Iterable[str],
    *,
    source_id: str | None = None,
    source_is_externe: bool = False,
) -> str | None:
    """Resolve one authoritative semantic category for an article."""

    available = frozenset(
        normalized
        for category in categories
        if (normalized := normalize_category(category)) is not None
    )
    if is_clearly_english_title(title) or source_is_externe:
        return "Externe"
    authoritative = AUTHORITATIVE_SOURCE_CATEGORIES.get(source_id or "")
    if authoritative is not None and authoritative in available:
        return authoritative
    domestic = available.difference({"Externe"})
    if len(domestic) == 1:
        return next(iter(domestic))
    tokens = frozenset(_normalized_token(value) for value in _TOKEN.findall(title))
    scores = {
        category: len(tokens & markers)
        for category, markers in _DOMESTIC_MARKERS.items()
        if category in domestic
    }
    if "Social" in domestic:
        scores["Social"] = scores.get("Social", 0) + int(
            "concediat" in tokens
            or "angajat" in tokens
            and bool(tokens & {"cafea", "despagubiri"})
        )
        scores["Social"] += int(
            bool(tokens & {"festival", "festivalul", "festivalului", "untold"})
            and bool(tokens & {"flux", "logistica", "vizitatori"})
        )
    strongest = max(scores.values(), default=0)
    if strongest:
        winners = {category for category, score in scores.items() if score == strongest}
        return next(category for category in DOMESTIC_TIE_ORDER if category in winners)
    if domestic & set(_DOMESTIC_MARKERS):
        return "Diverse"
    return min(available, key=lambda value: (value.casefold(), value), default=None)


def normalize_category(value: object) -> str | None:
    """Map legacy category evidence into the five-category product contract."""

    text = str(value)
    if text == "Toate" or text == "all":
        return None
    text = _LEGACY_CATEGORY_MAP.get(text, text)
    return text if text in CATEGORY_ORDER else None


def _normalized_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )


def _english_word_shape(value: str) -> bool:
    return (
        len(value) >= 5
        and value.endswith(("ed", "ing"))
        or "'" in value
        or "’" in value
    )
