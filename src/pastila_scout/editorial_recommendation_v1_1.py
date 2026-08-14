"""Deterministic corpus-grounded V1.1 editorial recommendation.

V1.1 deliberately remains separate from the frozen V1 implementation.  It scores
individual story value only; corroboration, recency, category caps, and future
episode-slate concerns are separate ranking or selection concerns.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime

_CAPS = {"Politica": 2, "Social": 3, "CanCan": 1, "Diverse": 3, "Externe": 2}
_FAMILY_NAMES = (
    "consequence",
    "contradiction",
    "human_value",
    "comic_visual",
    "continuity",
    "cultural_discourse",
)

_ROUTINE_SPORT = (
    "scor",
    "rezultat",
    "clasament",
    "etapa",
    "meci",
    "transfer",
    "calificat",
    "calificare",
    "victorie",
    "infrangere",
    "gol",
    "finala",
    "semifinala",
)
_SPORT_CONTEXT = (
    "fotbal",
    "sport",
    "sportiv",
    "liga",
    "campionat",
    "turneu",
    "echipa",
    "tenis",
    "atlet",
)
_SPORT_OVERRIDE = (
    "coruptie",
    "frauda",
    "bani publici",
    "siguranta publica",
    "abuz",
    "discriminare",
    "drepturi",
    "ancheta penala",
)
_LOTO_CONTEXT = ("loto", "loteria", "joker")
_LOTO_ROUTINE = ("numere", "extragere", "report", "jackpot", "premiu", "castig")
_LOTO_ROUTINE_STEMS = ("extrag", "rezultat", "numere", "castig", "premi")
_PROMOTION = (
    "a postat fotografii",
    "a publicat imagini",
    "imagini adorabile",
    "topit dupa",
    "isi promoveaza",
    "revine in emisiune",
)

_SAFETY = (
    "siguranta",
    "pericol",
    "atac",
    "incendiu",
    "accident",
    "ranit",
    "mort",
    "ucis",
    "ambulanta",
    "urgenta",
    "drona",
    "sabotaj",
    "explozie",
    "evacuati",
    "evacuare",
    "attack",
    "killed",
    "fire",
    "explosion",
)
_MONEY = (
    "frauda",
    "mita",
    "coruptie",
    "bani publici",
    "buget",
    "taxa",
    "impozit",
    "factura",
    "pret",
    "euro",
    "lei",
    "consumator",
    "acciza",
    "salarii",
    "prejudiciu",
)
_RIGHTS_LAW = (
    "drepturi",
    "lege",
    "instanta",
    "justitie",
    "condamnat",
    "inchisoare",
    "interzis",
    "concediu medical",
    "raspundere penala",
    "regulament",
    "international law",
)
_INFRASTRUCTURE = (
    "spital",
    "scoala",
    "cale ferata",
    "autostrada",
    "drum",
    "apa potabila",
    "retea de apa",
    "electricitate",
    "energie",
    "infrastructura",
    "serviciu public",
    "transport feroviar",
    "transport public",
)
_SECURITY = (
    "securitate nationala",
    "spionaj",
    "razboi",
    "militar",
    "nuclear",
    "atac cibernetic",
    "cyberattack",
    "armata",
    "frontiera",
    "spatiu aerian",
    "nato",
    "territorial",
    "russian plot",
    "ukrainian",
)
_DIRECT_EFFECT = (
    "afecteaza",
    "pune in pericol",
    "raman fara",
    "a fost atacat",
    "a fost lovit",
    "a murit",
    "au murit",
    "pagube",
    "pierderi",
    "obligatoriu",
    "intra in vigoare",
    "schimba administratia",
    "impact public",
    "ar putea perturba",
    "risca sa nu",
    "reduced the age",
    "thwarted",
)
_SEVERE_HARM = ("a murit", "au murit", "morti", "decedat", "killed", "fatal")
_DIRECT_SECURITY_ACTION = (
    "incalcat spatiul aerian",
    "doborate",
    "explozia dronei",
    "atac cibernetic",
    "plot to kill",
    "complot pentru asasinare",
    "sabotaj",
)
_DIRECT_REMEDY = (
    "trebuie sa-i plateasca",
    "trebuie sa plateasca",
    "a castigat in instanta",
    "despagubiri",
)

_ROLE_ACTORS = (
    "ministru",
    "politist",
    "procuror",
    "medic",
    "profesor",
    "primar",
    "judecator",
    "autoritate",
    "institutie",
)
_ROLE_ACTOR_STEMS = (
    "ministr",
    "politist",
    "procuror",
    "medic",
    "profesor",
    "primar",
    "judecator",
    "autoritat",
    "institut",
)
_ROLE_VIOLATIONS = (
    "mita",
    "coruptie",
    "abuz",
    "amanetat",
    "jocuri de noroc",
    "droguri la serviciu",
    "in timpul discursului",
    "a incalcat chiar",
)
_EXPLICIT_TENSION = (
    "desi",
    "in timp ce",
    "chiar daca",
    "contrar",
    "dar in realitate",
    "in loc sa",
    "promite dar",
    "spune ca dar",
)
_IMPLEMENTATION_GAP = (
    "doar vizual",
    "numai pe hartie",
    "nu este aplicat",
    "nu functioneaza",
    "fara sa rezolve",
    "prioritate gresita",
)
_VULNERABLE = (
    "copil",
    "elev",
    "pacient",
    "bolnav",
    "victima",
    "varstnic",
    "persoana cu dizabilitati",
    "familie",
)
_HARM = (
    "a murit",
    "au murit",
    "ranit",
    "abuzat",
    "agresat",
    "discriminat",
    "lipsit de ingrijire",
    "fara tratament",
    "pune in pericol",
    "prejudiciu",
)
_NO_CURRENT_HARM = (
    "nu a cauzat victime",
    "fara victime",
    "no casualties",
    "no injuries",
)
_PRACTICAL_LESSON = (
    "prim ajutor",
    "preventie",
    "cum poate fi prevenit",
    "semne de avertizare",
    "protectia pacientului",
    "protectia consumatorului",
    "preventia",
)
_INJUSTICE = (
    "nedreptate",
    "abuz",
    "violenta politiei",
    "privat de drepturi",
    "exploatat",
    "inselat",
)
_HUMAN_ROLES = (
    "muncitor",
    "pasager",
    "mecanic",
    "angajat",
    "sofer",
    "pescar",
    "turist",
    "worker",
    "passenger",
    "crew",
)

_ANIMALS = (
    "urs",
    "caracatita",
    "cerb",
    "caprioara",
    "balena",
    "animal",
    "octopus",
    "bear",
    "deer",
)
_VISUAL_ACTIONS = (
    "a ascuns",
    "a furat",
    "a amanetat",
    "a confundat",
    "a intrat cu",
    "a aruncat",
    "a trezit",
    "a atacat",
    "atacat",
    "s-a prins de fata",
    "impuscat",
)
_ABSURD_ACTIONS = (
    "a amanetat",
    "a ascuns",
    "a confundat",
    "a trezit",
    "beat",
    "beata",
    "furat",
)
_CONCRETE_ODDITY_PATTERNS = (
    r"\ba ascuns\b.+\bintr-un\b",
    r"\ba confundat\b.+\bcu\b",
    r"\b(?:mii|milioane|\d[\d.]*) de euro pentru (?:un|o)\b",
    r"\b(?:obiect|structura|platforma) misterioas\w*\b",
    r"\bla \d{2,3} de ani\b.+\b(?:examen|bacalaureat)\w*\b",
    r"\b(?:examen|bacalaureat)\w*\b.+\bla \d{2,3} de ani\b",
    r"\b(?:obiect|obstacol)\w* (?:ascutit|metalic|periculos)\w*\b",
)
_MISINFORMATION = (
    "dezinformare",
    "informatie falsa",
    "zvon fals",
    "teorie falsa",
    "fake news",
    "conspiratie",
    "propaganda falsa",
    "false propaganda",
    "falsa propaganda",
)
_ONLINE_REACTION = (
    "reactii online",
    "isterie online",
    "panica online",
    "controversa online",
    "dezbatere online",
    "razboi cultural",
    "pe tiktok",
    "pe retelele sociale",
)
_CULTURAL_DEBATE = (
    "dezbatere culturala",
    "controversa culturala",
    "film controversat",
    "festival controversat",
    "reactie colectiva",
    "trend social",
    "fenomen social",
    "institutie culturala",
    "centru cultural",
    "renaming controversy",
    "name change dispute",
    "identitate nationala",
    "retorica nationalista",
    "simbol istoric",
)

_EXPLANATIONS = {
    "consequence": "impact public",
    "contradiction": "contradictie institutionala",
    "human_value": "miza umana",
    "comic_visual": "premisa vizuala/comica",
    "continuity": "continuare a unui caz urmarit",
    "cultural_discourse": "dezbatere culturala / reactie online",
}


@dataclass(frozen=True, slots=True)
class EditorialCandidateV1_1:
    event_id: int
    title: str
    summary: str
    category: str
    source_count: int
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class ContinuityContextV1_1:
    """Explicit caller assertion linking a material update to a prior story."""

    previous_event_id: int
    current_event_id: int
    canonical_subject: str
    material_development: bool

    def __post_init__(self) -> None:
        if (
            type(self.previous_event_id) is not int
            or self.previous_event_id <= 0
            or type(self.current_event_id) is not int
            or self.current_event_id <= 0
            or self.previous_event_id == self.current_event_id
            or not self.canonical_subject.strip()
            or type(self.material_development) is not bool
        ):
            raise ValueError("Invalid continuity context")


@dataclass(frozen=True, slots=True)
class EditorialEvidenceV1_1:
    event_id: int
    category: str
    source_count: int
    last_seen_at: datetime
    eligible: bool
    exclusion_reason: str | None
    consequence: int
    contradiction: int
    human_value: int
    comic_visual: int
    continuity: int
    cultural_discourse: int
    family_reason_codes: tuple[tuple[str, tuple[str, ...]], ...]
    story_value: int
    corroboration_contribution: int
    quality_tier_metadata: str
    quality_floor_applied: bool
    primary_families: tuple[str, ...]
    comic_type: str | None
    continuity_identity: str | None
    explanation: str
    recommendation_rank: int | None = None
    disposition: str = "eligible"

    def __post_init__(self) -> None:
        strengths = tuple(getattr(self, name) for name in _FAMILY_NAMES)
        if any(type(value) is not int or value not in (0, 1, 2) for value in strengths):
            raise ValueError("Invalid editorial family strength")
        if self.story_value != sum(strengths) or not 0 <= self.story_value <= 12:
            raise ValueError("Invalid Story Value")
        if self.quality_floor_applied:
            raise ValueError("V1.1 quality floor must remain disabled")


@dataclass(frozen=True, slots=True)
class EpisodeRecommendationV1_1:
    recommendations: tuple[EditorialEvidenceV1_1, ...]
    evaluations: tuple[EditorialEvidenceV1_1, ...]
    available_slots: int


def recommend_episode_v1_1(
    candidates: tuple[EditorialCandidateV1_1, ...],
    *,
    continuity_context: tuple[ContinuityContextV1_1, ...] = (),
) -> EpisodeRecommendationV1_1:
    """Return a transient V1.1 recommendation over an immutable candidate pool."""
    if type(candidates) is not tuple or len(
        {item.event_id for item in candidates}
    ) != len(candidates):
        raise ValueError("Duplicate or invalid editorial candidate collection")
    if type(continuity_context) is not tuple:
        raise ValueError("Invalid continuity context collection")
    context_by_current: dict[int, ContinuityContextV1_1] = {}
    for item in continuity_context:
        if item.current_event_id in context_by_current:
            raise ValueError("Duplicate continuity context")
        context_by_current[item.current_event_id] = item

    evaluated = tuple(
        _evaluate(candidate, continuity=context_by_current.get(candidate.event_id))
        for candidate in candidates
    )
    ranked = sorted((item for item in evaluated if item.eligible), key=_rank_key)
    selected: list[EditorialEvidenceV1_1] = []
    counts = {category: 0 for category in _CAPS}
    for item in ranked:
        if len(selected) == 10:
            break
        if counts[item.category] < _CAPS[item.category]:
            selected.append(item)
            counts[item.category] += 1

    rank_by_id = {item.event_id: rank for rank, item in enumerate(selected, 1)}
    final: list[EditorialEvidenceV1_1] = []
    for item in evaluated:
        if item.event_id in rank_by_id:
            final.append(
                replace(
                    item,
                    recommendation_rank=rank_by_id[item.event_id],
                    disposition="recommended",
                )
            )
        elif not item.eligible:
            final.append(item)
        elif counts[item.category] >= _CAPS[item.category]:
            final.append(replace(item, disposition="eligible_but_category_cap_reached"))
        else:
            final.append(replace(item, disposition="eligible_but_below_episode_cutoff"))
    by_id = {item.event_id: item for item in final}
    recommendations = tuple(by_id[item.event_id] for item in selected)
    return EpisodeRecommendationV1_1(
        recommendations,
        tuple(sorted(final, key=lambda item: item.event_id)),
        10 - len(selected),
    )


def _evaluate(
    candidate: EditorialCandidateV1_1,
    *,
    continuity: ContinuityContextV1_1 | None,
) -> EditorialEvidenceV1_1:
    _validate_candidate(candidate)
    text = _plain(f"{candidate.title} {candidate.summary}")

    consequence_reasons = _consequence_reasons(text)
    consequence = _domain_strength(
        consequence_reasons,
        strong={
            "severe_public_safety",
            "direct_national_security",
            "direct_legal_or_financial_remedy",
        },
    )
    contradiction_reasons = _contradiction_reasons(text)
    contradiction = _domain_strength(
        contradiction_reasons,
        strong={"explicit_two_sided_tension", "role_violation"},
    )
    human_reasons = _human_reasons(text)
    human_value = _domain_strength(
        human_reasons,
        strong={"preventable_harm", "practical_public_lesson"},
    )
    comic_reasons, comic_type = _comic_reasons(text)
    comic_visual = _domain_strength(
        comic_reasons,
        strong={"concrete_bizarre_premise", "intrinsic_absurdity"},
    )
    cultural_reasons = _cultural_reasons(text)
    cultural_discourse = _domain_strength(
        cultural_reasons,
        strong={
            "misinformation_with_reaction",
            "meaningful_public_discourse",
            "institutional_cultural_dispute",
        },
    )
    continuity_reasons: tuple[str, ...] = ()
    continuity_identity = None
    continuity_strength = 0
    if continuity is not None and continuity.material_development:
        continuity_reasons = ("explicit_material_update",)
        continuity_identity = continuity.canonical_subject.strip()
        continuity_strength = 2

    strengths = {
        "consequence": consequence,
        "contradiction": contradiction,
        "human_value": human_value,
        "comic_visual": comic_visual,
        "continuity": continuity_strength,
        "cultural_discourse": cultural_discourse,
    }
    reasons = {
        "consequence": consequence_reasons,
        "contradiction": contradiction_reasons,
        "human_value": human_reasons,
        "comic_visual": comic_reasons,
        "continuity": continuity_reasons,
        "cultural_discourse": cultural_reasons,
    }
    story_value = sum(strengths.values())
    exclusion_reason = _exclusion_reason(text, story_value=story_value)
    eligible = exclusion_reason is None
    primary_strength = max(strengths.values(), default=0)
    primary = tuple(
        name
        for name in _FAMILY_NAMES
        if primary_strength > 0 and strengths[name] == primary_strength
    )
    explanation = _explanation(
        strengths,
        source_count=candidate.source_count,
        exclusion_reason=exclusion_reason,
    )
    return EditorialEvidenceV1_1(
        event_id=candidate.event_id,
        category=candidate.category,
        source_count=candidate.source_count,
        last_seen_at=candidate.last_seen_at,
        eligible=eligible,
        exclusion_reason=exclusion_reason,
        consequence=consequence,
        contradiction=contradiction,
        human_value=human_value,
        comic_visual=comic_visual,
        continuity=continuity_strength,
        cultural_discourse=cultural_discourse,
        family_reason_codes=tuple((name, reasons[name]) for name in _FAMILY_NAMES),
        story_value=story_value,
        corroboration_contribution=min(candidate.source_count, 10) * 2,
        quality_tier_metadata="uncalibrated",
        quality_floor_applied=False,
        primary_families=primary,
        comic_type=comic_type,
        continuity_identity=continuity_identity,
        explanation=explanation,
        disposition="excluded" if exclusion_reason else "eligible",
    )


def _validate_candidate(candidate: EditorialCandidateV1_1) -> None:
    if (
        type(candidate.event_id) is not int
        or candidate.event_id <= 0
        or not candidate.title.strip()
        or not candidate.summary.strip()
        or candidate.category not in _CAPS
        or type(candidate.source_count) is not int
        or candidate.source_count <= 0
        or type(candidate.last_seen_at) is not datetime
        or candidate.last_seen_at.utcoffset() is None
    ):
        raise ValueError("Invalid editorial candidate")


def _consequence_reasons(text: str) -> tuple[str, ...]:
    reasons: list[str] = []
    safety = _has(text, _SAFETY) or _has_stem(
        text, ("ranit", "muri", "atac", "incendi", "explod", "ucis", "omor")
    )
    if safety and _has(text, _SEVERE_HARM):
        reasons.append("severe_public_safety")
    elif safety:
        reasons.append("bounded_public_safety")
    consumer_change = _has_stem(text, ("promoti", "regul")) and _has_stem(
        text, ("consumator",)
    )
    if (
        _has(text, _MONEY)
        or _has_stem(text, ("consumator", "factur"))
        or consumer_change
        or (
            _has_stem(text, ("motorin", "combustibil"))
            and _has_stem(text, ("pret", "deficit", "scump"))
        )
    ):
        reasons.append("money_or_consumer_effect")
    if _has(text, _RIGHTS_LAW) or _has_stem(
        text, ("concedi", "regulament", "raspunder", "dreptur")
    ):
        reasons.append("rights_or_legal_effect")
    if (_has(text, _INFRASTRUCTURE) or _has_stem(text, ("salari",))) and (
        _has(text, _DIRECT_EFFECT)
        or _has_stem(text, ("furat", "atac", "sabot", "risc", "perturb", "oprire"))
    ):
        reasons.append("infrastructure_or_service_effect")
    security = _has(text, _SECURITY) or _has_stem(
        text, ("dron", "spion", "militar", "nuclear")
    )
    if security:
        reasons.append("national_security")
    if security and (
        _has(text, _DIRECT_SECURITY_ACTION)
        or _has_stem(text, ("explod", "sabot", "asasin"))
    ):
        reasons.append("direct_national_security")
    constructive = (
        _has_stem(text, ("descoper", "progres"))
        and _has_stem(text, ("medical", "stiint", "tehnolog"))
    ) or (
        _has_stem(text, ("inteligent", "tehnolog"))
        and _has(text, ("impact public", "interes public", "centru national"))
    )
    if constructive or _has(text, ("sanatatea publica",)):
        reasons.append("constructive_public_value")
    if (_has_stem(text, ("numir",)) and _has(text, ("prim-ministru",))) or _has(
        text, ("schimba administratia",)
    ):
        reasons.append("governance_effect")
    if _has(text, _DIRECT_REMEDY):
        reasons.append("direct_legal_or_financial_remedy")
    if _has(text, ("disputed", "teritoriu disputat", "insule disputate")):
        reasons.append("geopolitical_effect")
    return tuple(dict.fromkeys(reasons))


def _contradiction_reasons(text: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if (_has(text, _ROLE_ACTORS) or _has_stem(text, _ROLE_ACTOR_STEMS)) and _has(
        text, _ROLE_VIOLATIONS
    ):
        reasons.append("role_violation")
    if _has(text, _EXPLICIT_TENSION):
        reasons.append("explicit_two_sided_tension")
    if _has(text, _IMPLEMENTATION_GAP):
        reasons.append("policy_implementation_gap")
    if (
        _has_stem(text, ("pensionar",))
        and _has_stem(text, ("chemat",))
        and _has_stem(text, ("porn", "reporn"))
    ):
        reasons.append("system_dependency_irony")
    if (
        _has(text, ("votes again", "voteaza din nou"))
        and _has_stem(text, ("judec", "instant", "judg"))
        and _has_stem(text, ("block", "bloca"))
    ):
        reasons.append("authority_defiance")
    return tuple(reasons)


def _human_reasons(text: str) -> tuple[str, ...]:
    reasons: list[str] = []
    vulnerable = (
        _has(text, _VULNERABLE)
        or _has(
            text, ("fosta iubita", "fostul iubit", "partener intim", "sotie", "sot")
        )
        or _has_stem(text, ("iubit", "partener", "sot"))
    )
    harm = _has(text, _HARM) or _has_stem(
        text, ("agres", "ranit", "abuz", "discrimin", "insel")
    )
    if _has(text, _NO_CURRENT_HARM):
        harm = False
    if vulnerable and harm:
        reasons.append("preventable_harm")
    elif harm and (_has(text, _HUMAN_ROLES) or _has_stem(text, _HUMAN_ROLES)):
        reasons.append("human_harm")
    if _has(text, _PRACTICAL_LESSON):
        reasons.append("practical_public_lesson")
    if vulnerable and _has(text, _INJUSTICE):
        reasons.append("vulnerability_or_injustice")
    return tuple(dict.fromkeys(reasons))


def _comic_reasons(text: str) -> tuple[tuple[str, ...], str | None]:
    has_action = _has(text, _VISUAL_ACTIONS)
    absurd_action = _has(text, _ABSURD_ACTIONS)
    unusual_animal = _has(text, _ANIMALS) and (has_action or absurd_action)
    patterned_oddity = any(
        re.search(pattern, text) for pattern in _CONCRETE_ODDITY_PATTERNS
    )
    if unusual_animal and absurd_action:
        return ("intrinsic_absurdity", "concrete_bizarre_premise"), "intrinsic"
    if patterned_oddity:
        return ("concrete_bizarre_premise",), "intrinsic"
    if absurd_action and (
        _has(text, _ROLE_ACTORS) or _has_stem(text, _ROLE_ACTOR_STEMS)
    ):
        return ("contextual_absurdity",), "contextual"
    if unusual_animal or has_action:
        return ("concrete_visual_premise",), "intrinsic"
    return (), None


def _cultural_reasons(text: str) -> tuple[str, ...]:
    misinformation = _has(text, _MISINFORMATION)
    reaction = _has(text, _ONLINE_REACTION)
    debate = _has(text, _CULTURAL_DEBATE)
    identity_discourse = _has(text, ("neam de", "national identity"))
    naming_dispute = (
        _has_stem(text, ("nume", "name", "inscrib"))
        and _has_stem(text, ("judec", "block", "bloca"))
        and _has(text, ("center", "centru", "board", "consiliu"))
    )
    if misinformation and reaction:
        return ("misinformation_with_reaction", "meaningful_public_discourse")
    if misinformation:
        return ("misinformation_behavior",)
    if reaction or debate:
        return ("meaningful_public_discourse",)
    if naming_dispute:
        return ("institutional_cultural_dispute",)
    if identity_discourse:
        return ("cultural_identity_discourse",)
    return ()


def _domain_strength(reasons: tuple[str, ...], *, strong: set[str]) -> int:
    if not reasons:
        return 0
    if any(reason in strong for reason in reasons):
        return 2
    return 1


def _exclusion_reason(text: str, *, story_value: int) -> str | None:
    routine_sport = (
        _has(text, _SPORT_CONTEXT)
        and _has(text, _ROUTINE_SPORT)
        and not _has(text, _SPORT_OVERRIDE)
    )
    routine_loto = _has(text, _LOTO_CONTEXT) and (
        _has(text, _LOTO_ROUTINE) or _has_stem(text, _LOTO_ROUTINE_STEMS)
    )
    weak_promotion = _has(text, _PROMOTION) and story_value == 0
    if routine_loto:
        return "routine_loto"
    if routine_sport:
        return "routine_sport"
    if weak_promotion:
        return "generic_celebrity_promotion"
    if story_value == 0:
        return "insufficient_editorial_evidence"
    return None


def _explanation(
    strengths: dict[str, int],
    *,
    source_count: int,
    exclusion_reason: str | None,
) -> str:
    parts = [
        _EXPLANATIONS[name] + (" puternic" if strengths[name] == 2 else "")
        for name in _FAMILY_NAMES
        if strengths[name] > 0
    ]
    parts.append(f"{source_count} surse independente")
    if exclusion_reason is not None:
        parts.append(f"exclus: {exclusion_reason}")
    return " + ".join(parts)


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(
        r"\s+", " ", "".join(c for c in normalized if not unicodedata.combining(c))
    )


def _has(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _has_stem(text: str, stems: tuple[str, ...]) -> bool:
    """Match bounded inflected words; callers provide only unambiguous long stems."""
    return any(re.search(rf"(?<!\w){re.escape(stem)}\w*(?!\w)", text) for stem in stems)


def _rank_key(item: EditorialEvidenceV1_1) -> tuple[int, int, float, int]:
    return (
        -item.story_value,
        -item.corroboration_contribution,
        -item.last_seen_at.timestamp(),
        item.event_id,
    )


__all__ = [
    "ContinuityContextV1_1",
    "EditorialCandidateV1_1",
    "EditorialEvidenceV1_1",
    "EpisodeRecommendationV1_1",
    "recommend_episode_v1_1",
]
