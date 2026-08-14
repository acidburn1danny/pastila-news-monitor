"""Deterministic Scout category-integrity rules."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

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

_CANCAN_SOURCE_PRIORS = frozenset({"cancan", "click"})

_LEGACY_CATEGORY_MAP = {"Economie": "Diverse", "Conspiratii": "CanCan"}

_DOMESTIC_TOKEN_STEMS = {
    "Politica": frozenset(
        {
            "administrati",
            "aleger",
            "ambasad",
            "ambasador",
            "acciz",
            "autoritat",
            "cabinet",
            "cjue",
            "candidat",
            "coalitie",
            "cotroceni",
            "deputat",
            "diplomat",
            "executiv",
            "eurodeputat",
            "europarlamentar",
            "guvern",
            "impozit",
            "lege",
            "legisl",
            "mae",
            "mapn",
            "bnr",
            "minister",
            "ministr",
            "premier",
            "ordonant",
            "parchet",
            "partid",
            "parlament",
            "aparare",
            "nato",
            "politic",
            "presedinte",
            "presedintie",
            "prefect",
            "primar",
            "reforma",
            "deficit",
            "senat",
        }
    ),
    "Social": frozenset(
        {
            "accident",
            "admitere",
            "agres",
            "asigurar",
            "arest",
            "alert",
            "anm",
            "autostrad",
            "bacalaureat",
            "canicul",
            "cass",
            "consumator",
            "concediat",
            "condamnat",
            "crima",
            "cutremur",
            "dispar",
            "drum",
            "educatie",
            "eliberar",
            "elev",
            "epidemi",
            "evacua",
            "examen",
            "exploz",
            "furnizor",
            "furtun",
            "grindin",
            "incendi",
            "infrastructur",
            "inchisoar",
            "inund",
            "intervent",
            "jaf",
            "isu",
            "jandarm",
            "loto",
            "loteria",
            "pacient",
            "pensie",
            "pensionar",
            "pieton",
            "politist",
            "politie",
            "pompier",
            "salari",
            "salvamont",
            "sanatate",
            "scoala",
            "spital",
            "student",
            "retinut",
            "suspendat",
            "trafic",
            "tren",
            "universitat",
            "utilitat",
            "varstnic",
            "vijeli",
        }
    ),
    "CanCan": frozenset(
        {
            "actor",
            "actrit",
            "aparitie",
            "artist",
            "cantaret",
            "cantareat",
            "casator",
            "despart",
            "divort",
            "influencer",
            "logodn",
            "monden",
            "nunta",
            "prezentator",
            "prezentato",
            "relatie",
            "showbiz",
            "tenor",
            "vedet",
            "conspiratie",
            "dezinformare",
            "fake",
            "manipulare",
        }
    ),
    "Diverse": frozenset({"incategorizabil"}),
}

_DOMESTIC_PHRASES = {
    "Politica": (
        "bugetul de stat",
        "camera deputatilor",
        "cheltuieli publice",
        "comisia europeana",
        "companie de stat",
        "companii de stat",
        "companiile de stat",
        "companiilor de stat",
        "consiliu judetean",
        "consiliu local",
        "curtea constitutionala",
        "fonduri publice",
        "deficitul bugetar",
        "ministerul afacerilor externe",
        "ministerul de externe",
        "industria militara",
        "fortele aeriene romane",
        "centrala de la cernavoda",
        "centrala nucleara de la cernavoda",
        "spatiul aerian al romaniei",
        "spatiul aerian romanesc",
        "pilot de f 16",
        "piloti de f 16",
        "prim ministru",
        "proiect de lege",
        "secretar de stat",
        "statul major",
        "statului major",
        "partidul aur",
        "partidul pot",
        "partidul sos",
    ),
    "Social": (
        "cfr calatori",
        "cale ferata",
        "cod galben",
        "cod portocaliu",
        "cod rosu",
        "conditii de munca",
        "incendiu de vegetatie",
        "ro alert",
        "servicii publice",
        "transport public",
        "nu avem curent",
        "pana de curent",
        "pasapoarte pe nume false",
    ),
    "CanCan": (
        "asia express",
        "cerere in casatorie",
        "cerut o de sotie",
        "filme si seriale",
        "insula iubirii",
        "reality show",
        "vacanta vedetei",
        "vedeta tv",
        "costum de baie",
        "se mentine in forma",
    ),
    "Diverse": (),
}

_ROMANIAN_INSTITUTION_TOKENS = frozenset(
    {
        "ccr",
        "cjue",
        "csat",
        "mae",
        "mapn",
        "pnl",
        "psd",
        "udmr",
        "usr",
    }
)
_STRONG_POLITICAL_STEMS = frozenset(
    {
        "guvern",
        "mae",
        "mapn",
        "minister",
        "ministr",
        "parlament",
        "partid",
        "politic",
        "premier",
        "presedint",
    }
)
_POLITICAL_EXACT_TOKENS = frozenset(
    {"ccr", "cjue", "csat", "pnl", "psd", "udmr", "usr"}
)
_CANCAN_EXACT_TOKENS = frozenset({"iubit", "iubita", "iubitul", "iubitei"})
_STRONG_CANCAN_STEMS = frozenset(
    {
        "actor",
        "actrit",
        "artist",
        "cantaret",
        "cantareat",
        "influencer",
        "prezentator",
        "prezentato",
        "tenor",
        "vedet",
    }
)
_SOCIAL_EXACT_TOKENS = frozenset(
    {
        "anm",
        "anpc",
        "dnsc",
        "furat",
        "furata",
        "hotii",
        "hotul",
        "isu",
        "jandarmi",
        "pompieri",
        "ocpi",
        "politia",
        "politiei",
        "politie",
        "salvamont",
    }
)
_DOMESTIC_SOCIAL_AUTHORITY_TOKENS = frozenset(
    {"anm", "anpc", "dnsc", "isu", "jandarmi", "pompieri", "salvamont"}
)
_SPORTS_TOKENS = frozenset(
    {
        "antrenor",
        "campionat",
        "campion",
        "clasament",
        "cupe",
        "dinamo",
        "echipa",
        "echipei",
        "fcsb",
        "fotbal",
        "finala",
        "finale",
        "liga",
        "meci",
        "play",
        "semifinala",
        "sportiv",
        "victorie",
    }
)
_SERIOUS_SOCIAL_STEMS = frozenset(
    {
        "accident",
        "agres",
        "arest",
        "bataie",
        "batut",
        "crima",
        "dispar",
        "incendi",
        "impuscat",
        "jaf",
        "omor",
        "retinut",
        "ucis",
    }
)
_POLITICAL_ACTION_STEMS = frozenset(
    {
        "adopt",
        "anunt",
        "aproba",
        "buget",
        "convoc",
        "demit",
        "num",
        "reforma",
        "tax",
        "vot",
    }
)
_SOCIAL_ACTION_STEMS = frozenset(
    {"ajut", "caut", "ciocn", "evacua", "intern", "intrerup", "salv"}
)
_ENTERTAINMENT_ACTION_STEMS = frozenset(
    {
        "casator",
        "despart",
        "divort",
        "film",
        "interviu",
        "logodn",
        "nunta",
        "relatie",
        "show",
        "televiz",
    }
)
_LIFESTYLE_STEMS = frozenset(
    {"dieta", "horoscop", "reteta", "vacanta", "vestiment", "zodie"}
)
_POLITICAL_ROLE_STEMS = frozenset(
    {
        "deputat",
        "europarlamentar",
        "ministr",
        "parlamentar",
        "politic",
        "premier",
        "primar",
        "presedint",
        "senator",
        "vicepremier",
    }
)
_EMERGENCY_ROLE_STEMS = frozenset(
    {"jandarm", "medic", "politist", "pompier", "salvamont"}
)
_CELEBRITY_ROLE_STEMS = frozenset(
    {
        "actor",
        "actrit",
        "artist",
        "cantaret",
        "influencer",
        "prezentator",
        "tenor",
        "vedet",
    }
)
_ATHLETE_ROLE_STEMS = frozenset({"antrenor", "atlet", "fotbalist", "sportiv"})
_BUSINESS_ROLE_STEMS = frozenset(
    {"antreprenor", "ceo", "companie", "director", "firma"}
)
_FOREIGN_INSTITUTION_PHRASES = (
    "guvernul de la",
    "guvernul din",
    "ministerul de la",
    "ministerul din",
    "ministerul de externe de la",
    "presedintele statului",
    "autoritatile de la",
    "autoritatile din",
)
_FOREIGN_EXACT_TOKENS = frozenset(
    {"roma", "uk", "rusia", "ruseasca", "rusesc", "rusesti", "rusii"}
)
_FOREIGN_PHRASES = ("nordul europei", "sudul europei")
_ROMANIAN_CONTEXT_STEMS = frozenset(
    {"bucurest", "romania", "romanesc", "roman", "cotroceni"}
)
_FOREIGN_STEMS = frozenset(
    {
        "american",
        "afganistan",
        "arabia",
        "berlin",
        "bolsonaro",
        "bordeaux",
        "brazil",
        "bremen",
        "brighton",
        "britani",
        "bulgaria",
        "china",
        "crimeea",
        "columbia",
        "coreea",
        "danemarca",
        "franta",
        "germania",
        "grecia",
        "hong",
        "halkidiki",
        "houthi",
        "iran",
        "irlanda",
        "irlandez",
        "israel",
        "italia",
        "japonia",
        "kazah",
        "kiev",
        "liban",
        "macron",
        "palestin",
        "polonia",
        "rotterdam",
        "rusia",
        "spania",
        "sankt",
        "serbia",
        "sicilia",
        "sua",
        "sued",
        "taiwan",
        "teheran",
        "trump",
        "turcia",
        "ucrain",
        "ungaria",
        "venet",
        "odesa",
        "normandia",
        "cisiordania",
        "zelensk",
        "yemen",
    }
)
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
_TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True, slots=True)
class _ContextEvidence:
    """Bounded runtime evidence used only when direct title semantics are weak."""

    role_family: str | None
    action_family: str | None
    domestic_strength: int
    foreign_strength: int


def is_clearly_english_title(title: str) -> bool:
    """Return true only for a headline with strong, unambiguous English evidence."""

    if type(title) is not str or not title.strip():
        return False
    if any(marker in title for marker in ("Ã", "Ä", "È")):
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
    summary: str | None = None,
) -> str | None:
    """Resolve one authoritative semantic category for an article."""

    available = frozenset(
        normalized
        for category in categories
        if (normalized := normalize_category(category)) is not None
    )
    if is_clearly_english_title(title) or source_is_externe:
        return "Externe"
    cancan_source_prior = (source_id or "") in _CANCAN_SOURCE_PRIORS
    if cancan_source_prior and "CanCan" in available:
        # These publishers cover every semantic family. Their configured category
        # is therefore a supporting prior, not the semantic candidate boundary.
        available = available | {"Politica", "Social", "CanCan", "Diverse"}
    domestic = available.difference({"Externe"})
    if len(domestic) == 1:
        return next(iter(domestic))
    title_tokens = frozenset(tokens_in_order(title))
    title_text = " ".join(tokens_in_order(title))
    summary_tokens = frozenset(tokens_in_order(summary or ""))
    summary_text = " ".join(tokens_in_order(summary or ""))
    foreign_title = _foreign_in_romanian(title_tokens, title_text)
    domestic_context = _domestic_primary(title_tokens, title_text)
    if foreign_title and not domestic_context:
        return "Externe"
    contextual = _contextual_category(
        title_tokens,
        title_text,
        summary_tokens,
        summary_text,
        domestic,
        cancan_source_prior=cancan_source_prior,
    )
    if contextual is not None:
        return contextual
    resolved = _semantic_category(
        title,
        domestic,
        allow_foreign=False,
        cancan_source_prior=cancan_source_prior,
    )
    if resolved is not None:
        return resolved
    if summary:
        minimum_summary_score = (
            1 if _hard_domestic_summary(summary_tokens, summary_text) else 4
        )
        resolved = _semantic_category(
            summary,
            domestic,
            allow_foreign=False,
            minimum_score=minimum_summary_score,
            cancan_source_prior=cancan_source_prior,
        )
        if resolved is not None:
            return resolved
    if domestic & set(_DOMESTIC_TOKEN_STEMS):
        return "Diverse"
    return min(available, key=lambda value: (value.casefold(), value), default=None)


def _semantic_category(
    text: str,
    domestic: frozenset[str],
    *,
    allow_foreign: bool = True,
    minimum_score: int = 1,
    cancan_source_prior: bool = False,
) -> str | None:
    tokens = frozenset(tokens_in_order(text))
    normalized_title = " ".join(tokens_in_order(text))
    scores = {
        category: _family_score(tokens, normalized_title, category)
        for category in _DOMESTIC_TOKEN_STEMS
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
    if (
        cancan_source_prior
        and 0 < scores.get("CanCan", 0)
        and not _has_stem(tokens, _SERIOUS_SOCIAL_STEMS)
        and not (tokens & _SPORTS_TOKENS)
        and scores["CanCan"]
        >= max(
            (score for category, score in scores.items() if category != "CanCan"),
            default=0,
        )
    ):
        scores["CanCan"] += 1
    if scores.get("CanCan") == 1:
        # An isolated relationship/entertainment word is insufficient without
        # an aligned role, phrase, or second semantic signal.
        scores["CanCan"] = 0
    if (
        allow_foreign
        and _foreign_in_romanian(tokens, normalized_title)
        and not _domestic_primary(tokens, normalized_title)
    ):
        return "Externe"
    strongest = max(scores.values(), default=0)
    if strongest >= minimum_score:
        winners = {category for category, score in scores.items() if score == strongest}
        return next(category for category in DOMESTIC_TIE_ORDER if category in winners)
    return None


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


def tokens_in_order(value: str) -> tuple[str, ...]:
    """Return diacritic-insensitive word tokens while preserving phrase order."""

    return tuple(_normalized_token(token) for token in _TOKEN.findall(value))


def _family_score(tokens: frozenset[str], title: str, category: str) -> int:
    stems = _DOMESTIC_TOKEN_STEMS[category]
    token_score = sum(any(token.startswith(stem) for stem in stems) for token in tokens)
    phrase_score = sum(2 for phrase in _DOMESTIC_PHRASES[category] if phrase in title)
    exact_score = 0
    if category == "Politica":
        exact_score = len(tokens & _POLITICAL_EXACT_TOKENS)
    elif category == "Social":
        exact_score = len(tokens & _SOCIAL_EXACT_TOKENS)
    elif category == "CanCan":
        exact_score = len(tokens & _CANCAN_EXACT_TOKENS)
    if category == "Social" and tokens & _SPORTS_TOKENS:
        token_score -= sum(
            token.startswith(("cfr", "intervent", "universitat")) for token in tokens
        )
    authority_bonus = int(
        category == "Politica" and _has_stem(tokens, _STRONG_POLITICAL_STEMS)
    )
    authority_bonus += int(
        category == "CanCan" and _has_stem(tokens, _STRONG_CANCAN_STEMS)
    )
    return max(0, token_score) + phrase_score + exact_score + authority_bonus


def _has_stem(tokens: frozenset[str], stems: frozenset[str]) -> bool:
    return any(any(token.startswith(stem) for stem in stems) for token in tokens)


def _domestic_primary(tokens: frozenset[str], title: str) -> bool:
    if _hard_domestic_primary(tokens, title):
        return True
    has_romanian_context = _has_stem(tokens, _ROMANIAN_CONTEXT_STEMS)
    has_public_action = _family_score(tokens, title, "Politica") > 0
    return has_romanian_context and has_public_action


def _hard_domestic_primary(tokens: frozenset[str], title: str) -> bool:
    if any(
        phrase in title for phrase in _FOREIGN_INSTITUTION_PHRASES
    ) and not _has_stem(tokens, _ROMANIAN_CONTEXT_STEMS):
        return False
    if tokens & (_ROMANIAN_INSTITUTION_TOKENS | _DOMESTIC_SOCIAL_AUTHORITY_TOKENS):
        return True
    return any(
        phrase in title
        for phrase in (
            "ministerul afacerilor externe",
            "ministerul de externe",
            "premierul romaniei",
            "presedintele romaniei",
            "prim ministrul romaniei",
            "statul major",
            "statului major",
            "armata romana",
            "spatiul aerian al romaniei",
            "spatiul aerian national",
            "spatiul aerian romanesc",
            "spatiului aerian al romaniei",
            "spatiului aerian romanesc",
        )
    )


def _hard_domestic_summary(tokens: frozenset[str], title: str) -> bool:
    if tokens & _ROMANIAN_INSTITUTION_TOKENS:
        return True
    return any(
        phrase in title
        for phrase in (
            "premierul romaniei",
            "presedintele romaniei",
            "prim ministrul romaniei",
            "armata romana",
            "spatiul aerian al romaniei",
            "spatiul aerian romanesc",
            "spatiului aerian al romaniei",
            "spatiului aerian romanesc",
        )
    )


def _foreign_in_romanian(tokens: frozenset[str], title: str = "") -> bool:
    return (
        bool(tokens & _FOREIGN_EXACT_TOKENS)
        or _has_stem(tokens, _FOREIGN_STEMS)
        or any(phrase in title for phrase in _FOREIGN_PHRASES)
    )


def _contextual_category(
    title_tokens: frozenset[str],
    title: str,
    summary_tokens: frozenset[str],
    summary: str,
    domestic: frozenset[str],
    *,
    cancan_source_prior: bool,
) -> str | None:
    """Resolve narrow role/action cases without turning summary into a classifier."""

    evidence = _context_evidence(title_tokens, title, summary_tokens, summary)
    serious_social = _has_stem(title_tokens | summary_tokens, _SERIOUS_SOCIAL_STEMS)
    if serious_social and "Social" in domestic:
        if evidence.foreign_strength > evidence.domestic_strength:
            return "Externe"
        return "Social"
    if evidence.action_family == "sports" and "Diverse" in domestic:
        return "Diverse"
    if evidence.role_family == "political" and _has_stem(
        title_tokens | summary_tokens, _LIFESTYLE_STEMS
    ):
        return "Diverse" if "Diverse" in domestic else None
    if evidence.foreign_strength > evidence.domestic_strength and any(
        phrase in title or phrase in summary for phrase in _FOREIGN_INSTITUTION_PHRASES
    ):
        return "Externe"
    if (
        evidence.role_family == "emergency"
        and evidence.action_family == "social"
        and _family_score(title_tokens | summary_tokens, f"{title} {summary}", "CanCan")
        == 0
        and "Social" in domestic
    ):
        return "Social"

    # A clear title family remains primary; context is only a recovery mechanism.
    title_scores = {
        category: _family_score(title_tokens, title, category)
        for category in _DOMESTIC_TOKEN_STEMS
        if category in domestic
    }
    if max(title_scores.values(), default=0) > 0:
        return None

    if evidence.role_family == "political" and evidence.action_family == "political":
        if evidence.foreign_strength > evidence.domestic_strength:
            return "Externe"
        if "Politica" in domestic:
            return "Politica"
    if evidence.action_family == "social":
        if evidence.foreign_strength > evidence.domestic_strength:
            return "Externe"
        if "Social" in domestic:
            return "Social"
    if (
        evidence.role_family == "celebrity"
        and (
            evidence.action_family == "entertainment"
            or evidence.action_family == "lifestyle"
            or cancan_source_prior
            and evidence.action_family is None
        )
        and "CanCan" in domestic
    ):
        return "CanCan"
    if evidence.role_family in {"athlete", "business"} and "Diverse" in domestic:
        return "Diverse"
    return None


def _context_evidence(
    title_tokens: frozenset[str],
    title: str,
    summary_tokens: frozenset[str],
    summary: str,
) -> _ContextEvidence:
    all_tokens = title_tokens | summary_tokens
    domestic_strength = 3 if _hard_domestic_primary(title_tokens, title) else 0
    domestic_strength += int(_domestic_primary(title_tokens, title))
    domestic_strength += 2 * int(_hard_domestic_summary(summary_tokens, summary))
    foreign_strength = 3 * int(_foreign_in_romanian(title_tokens, title))
    foreign_strength += int(_foreign_in_romanian(summary_tokens, summary))
    foreign_strength += 2 * int(
        any(
            phrase in title or phrase in summary
            for phrase in _FOREIGN_INSTITUTION_PHRASES
        )
        and not _hard_domestic_summary(summary_tokens, summary)
    )
    return _ContextEvidence(
        role_family=_role_family(all_tokens),
        action_family=_action_family(all_tokens),
        domestic_strength=domestic_strength,
        foreign_strength=foreign_strength,
    )


def _role_family(tokens: frozenset[str]) -> str | None:
    families = (
        ("political", _POLITICAL_ROLE_STEMS),
        ("emergency", _EMERGENCY_ROLE_STEMS),
        ("celebrity", _CELEBRITY_ROLE_STEMS),
        ("athlete", _ATHLETE_ROLE_STEMS),
        ("business", _BUSINESS_ROLE_STEMS),
    )
    matches = [family for family, stems in families if _has_stem(tokens, stems)]
    return matches[0] if len(matches) == 1 else None


def _action_family(tokens: frozenset[str]) -> str | None:
    if tokens & _SPORTS_TOKENS or _has_stem(tokens, _ATHLETE_ROLE_STEMS):
        return "sports"
    families = (
        ("political", _POLITICAL_ACTION_STEMS),
        ("social", _SOCIAL_ACTION_STEMS),
        ("entertainment", _ENTERTAINMENT_ACTION_STEMS),
        ("lifestyle", _LIFESTYLE_STEMS),
    )
    matches = [family for family, stems in families if _has_stem(tokens, stems)]
    return matches[0] if len(matches) == 1 else None


def _english_word_shape(value: str) -> bool:
    return (
        len(value) >= 5
        and value.endswith(("ed", "ing"))
        or "'" in value
        or "’" in value
    )
