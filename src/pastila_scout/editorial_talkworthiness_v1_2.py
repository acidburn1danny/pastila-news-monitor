"""Deterministic talkworthiness-first Scout recommendation V1.2.

V1.2 is intentionally isolated from the frozen V1/V1.1 recommenders.  News
significance is descriptive; only explicit editorial leverage can make a story
recommendation-eligible.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from enum import IntEnum

_CAPS = {"Politica": 2, "Social": 3, "CanCan": 1, "Diverse": 3, "Externe": 2}
_LEVERAGE_FAMILIES = (
    "accountability_system",
    "contradiction",
    "comic_roast",
    "unusual_pattern",
    "discussion_bridge",
    "cultural_discourse",
    "material_continuity",
)


class TalkworthinessTierV1_2(IntEnum):
    NONE = 0
    BOUNDED = 1
    STRONG = 2


@dataclass(frozen=True, slots=True)
class EditorialCandidateV1_2:
    event_id: int
    title: str
    summary: str
    category: str
    source_count: int
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class DiscussionBridgeContextV1_2:
    event_id: int
    romanian_question: str
    concrete_foreign_practice: str

    def __post_init__(self) -> None:
        if (
            type(self.event_id) is not int
            or self.event_id <= 0
            or not self.romanian_question.strip()
            or not self.concrete_foreign_practice.strip()
        ):
            raise ValueError("Invalid discussion bridge context")


@dataclass(frozen=True, slots=True)
class MaterialContinuityContextV1_2:
    event_id: int
    previous_event_id: int
    canonical_subject: str
    material_development: bool

    def __post_init__(self) -> None:
        if (
            type(self.event_id) is not int
            or self.event_id <= 0
            or type(self.previous_event_id) is not int
            or self.previous_event_id <= 0
            or self.event_id == self.previous_event_id
            or not self.canonical_subject.strip()
            or type(self.material_development) is not bool
        ):
            raise ValueError("Invalid material continuity context")


@dataclass(frozen=True, slots=True)
class EditorialEvidenceV1_2:
    event_id: int
    category: str
    source_count: int
    last_seen_at: datetime
    consequence: int
    human_stakes: int
    accountability_system: int
    contradiction: int
    comic_roast: int
    unusual_pattern: int
    discussion_bridge: int
    cultural_discourse: int
    material_continuity: int
    reason_codes: tuple[tuple[str, tuple[str, ...]], ...]
    talkworthiness: TalkworthinessTierV1_2
    leverage_strength: int
    significance_strength: int
    eligible: bool
    recommendation_rank: int | None = None
    disposition: str = "eligible"

    def __post_init__(self) -> None:
        leverage = tuple(getattr(self, name) for name in _LEVERAGE_FAMILIES)
        if any(type(value) is not int or value not in (0, 1, 2) for value in leverage):
            raise ValueError("Invalid Editorial Leverage")
        if self.consequence not in (0, 1, 2) or self.human_stakes not in (0, 1, 2):
            raise ValueError("Invalid Significance")
        if self.leverage_strength != sum(leverage):
            raise ValueError("Invalid leverage aggregate")
        if self.significance_strength != self.consequence + self.human_stakes:
            raise ValueError("Invalid significance aggregate")
        if self.eligible != (self.talkworthiness >= TalkworthinessTierV1_2.BOUNDED):
            raise ValueError("Talkworthiness eligibility mismatch")


@dataclass(frozen=True, slots=True)
class EpisodeRecommendationV1_2:
    recommendations: tuple[EditorialEvidenceV1_2, ...]
    evaluations: tuple[EditorialEvidenceV1_2, ...]
    available_slots: int


@dataclass(frozen=True, slots=True)
class PoolUtilityDecisionV1_2:
    useful: bool
    exclusion_reason: str | None = None


def recommend_episode_v1_2(
    candidates: tuple[EditorialCandidateV1_2, ...],
    *,
    discussion_bridges: tuple[DiscussionBridgeContextV1_2, ...] = (),
    continuity_context: tuple[MaterialContinuityContextV1_2, ...] = (),
) -> EpisodeRecommendationV1_2:
    if type(candidates) is not tuple or len(
        {item.event_id for item in candidates}
    ) != len(candidates):
        raise ValueError("Duplicate or invalid V1.2 candidates")
    bridges = _context_by_event(discussion_bridges)
    continuity = _context_by_event(continuity_context)
    evaluated = tuple(
        _evaluate(
            candidate,
            bridges.get(candidate.event_id),
            continuity.get(candidate.event_id),
        )
        for candidate in candidates
    )
    ranked = sorted((item for item in evaluated if item.eligible), key=_rank_key)
    selected: list[EditorialEvidenceV1_2] = []
    counts = {category: 0 for category in _CAPS}
    for item in ranked:
        if len(selected) == 10:
            break
        if counts[item.category] < _CAPS[item.category]:
            selected.append(item)
            counts[item.category] += 1
    ranks = {item.event_id: index for index, item in enumerate(selected, 1)}
    final = tuple(
        replace(
            item,
            recommendation_rank=ranks.get(item.event_id),
            disposition=(
                "recommended"
                if item.event_id in ranks
                else "retellable_only"
                if not item.eligible
                else "eligible_but_category_cap_reached"
                if counts[item.category] >= _CAPS[item.category]
                else "eligible_but_below_episode_cutoff"
            ),
        )
        for item in evaluated
    )
    by_id = {item.event_id: item for item in final}
    return EpisodeRecommendationV1_2(
        tuple(by_id[item.event_id] for item in selected),
        tuple(sorted(final, key=lambda item: item.event_id)),
        10 - len(selected),
    )


def pool_utility_v1_2(candidate: EditorialCandidateV1_2) -> PoolUtilityDecisionV1_2:
    _validate_candidate(candidate)
    text = _plain(f"{candidate.title} {candidate.summary}")
    if _has(text, ("loto", "loteria", "joker")) and _has_stem(
        text, ("extrag", "numere", "report", "jackpot", "castig", "premi")
    ):
        return PoolUtilityDecisionV1_2(False, "routine_loto")
    sport = _has_stem(
        text, ("fotbal", "sportiv", "meci", "campionat", "liga", "turneu")
    )
    routine_sport = _has_stem(
        text,
        ("scor", "rezultat", "clasament", "calific", "transfer", "victori", "finala"),
    )
    useful_override = _has_stem(
        text,
        ("corupt", "fraud", "abuz", "discrimin", "siguranta", "ancheta", "dreptur"),
    )
    if sport and routine_sport and not useful_override:
        return PoolUtilityDecisionV1_2(False, "routine_sport")
    if _has_stem(text, ("calendar", "programul", "orar")) and _has_stem(
        text, ("sarbator", "vacant", "examen", "meci", "eveniment", "ceremoni", "parad")
    ):
        return PoolUtilityDecisionV1_2(False, "routine_calendar")
    if _has_stem(
        text, ("traditi", "superstiti", "semnificatia sarbator")
    ) and not _has_stem(text, ("interzis", "controvers", "abuz", "conflict")):
        return PoolUtilityDecisionV1_2(False, "generic_tradition_explainer")
    if _has(
        text,
        (
            "a postat fotografii",
            "a publicat imagini",
            "imagini adorabile",
            "isi promoveaza",
            "revine in emisiune",
        ),
    ) and not _has_stem(text, ("controvers", "dezinform", "abuz", "fraud")):
        return PoolUtilityDecisionV1_2(False, "generic_celebrity_promotion")
    entertainment_promotion = _has_stem(
        text, ("reality show", "emisiun", "concurent", "pro tv", "voyo")
    ) and _has_stem(
        text, ("debuteaz", "afla cine", "noi concurent", "intra in competitie")
    )
    if entertainment_promotion:
        return PoolUtilityDecisionV1_2(False, "generic_celebrity_promotion")
    routine_media_departure = _has_stem(
        text, ("vedeta", "prezentator", "emisiun", "televiziun", "micul ecran")
    ) and _has_stem(text, ("demisi", "paraseste postul", "nu va mai aparea"))
    if routine_media_departure and not _has_stem(
        text, ("controvers", "abuz", "fraud", "anchet", "discrimin")
    ):
        return PoolUtilityDecisionV1_2(False, "generic_celebrity_promotion")
    if _has(text, ("te invata cum sa faci", "reteta pentru")) and _has_stem(
        text, ("inghetat", "prajitur", "mancare", "cafea", "desert")
    ):
        return PoolUtilityDecisionV1_2(False, "generic_lifestyle_howto")
    return PoolUtilityDecisionV1_2(True)


def _evaluate(candidate, bridge, continuity) -> EditorialEvidenceV1_2:
    _validate_candidate(candidate)
    text = _plain(f"{candidate.title} {candidate.summary}")
    consequence, human = _significance(text)
    reasons = {
        "accountability_system": _accountability(text),
        "contradiction": _contradiction(text),
        "comic_roast": _comic_roast(text),
        "unusual_pattern": _unusual_pattern(text),
        "discussion_bridge": ("explicit_romanian_discussion_bridge",) if bridge else (),
        "cultural_discourse": _cultural_discourse(text),
        "material_continuity": (
            ("explicit_material_development",)
            if continuity is not None and continuity.material_development
            else ()
        ),
    }
    strong_codes = {
        "preventable_system_failure",
        "institutional_accountability",
        "opaque_public_contracting",
        "critical_system_emergency_workaround",
        "explicit_two_sided_contradiction",
        "high_benefit_low_uptake",
        "official_claim_reversal",
        "prestige_immediate_failure",
        "security_everyday_collision",
        "age_context_mismatch",
        "high_value_discovery_uncertain_ownership",
        "heritage_emergency_relocation",
        "expanding_victim_pattern",
        "explicit_romanian_discussion_bridge",
        "meaningful_public_discourse",
        "contested_youth_digital_policy",
        "explicit_material_development",
    }
    strengths = {
        family: 2 if any(code in strong_codes for code in codes) else 1 if codes else 0
        for family, codes in reasons.items()
    }
    positives = sum(value > 0 for value in strengths.values())
    if any(value == 2 for value in strengths.values()) or positives >= 2:
        tier = TalkworthinessTierV1_2.STRONG
    elif positives == 1:
        tier = TalkworthinessTierV1_2.BOUNDED
    else:
        tier = TalkworthinessTierV1_2.NONE
    return EditorialEvidenceV1_2(
        event_id=candidate.event_id,
        category=candidate.category,
        source_count=candidate.source_count,
        last_seen_at=candidate.last_seen_at,
        consequence=consequence,
        human_stakes=human,
        accountability_system=strengths["accountability_system"],
        contradiction=strengths["contradiction"],
        comic_roast=strengths["comic_roast"],
        unusual_pattern=strengths["unusual_pattern"],
        discussion_bridge=strengths["discussion_bridge"],
        cultural_discourse=strengths["cultural_discourse"],
        material_continuity=strengths["material_continuity"],
        reason_codes=tuple((family, reasons[family]) for family in _LEVERAGE_FAMILIES),
        talkworthiness=tier,
        leverage_strength=sum(strengths.values()),
        significance_strength=consequence + human,
        eligible=tier >= TalkworthinessTierV1_2.BOUNDED,
        disposition="retellable_only"
        if tier == TalkworthinessTierV1_2.NONE
        else "eligible",
    )


def _significance(text: str) -> tuple[int, int]:
    severe = _has_stem(text, ("murit", "morti", "ucis", "fatal", "deced"))
    public = _has_stem(
        text,
        (
            "accident",
            "ranit",
            "evacuat",
            "drona",
            "securitat",
            "lege",
            "energie",
            "spital",
        ),
    )
    consequence = 2 if severe else 1 if public else 0
    vulnerable = _has_stem(
        text, ("copil", "copii", "famil", "victim", "pacient", "varstnic")
    )
    human = 2 if severe and vulnerable else 1 if severe or vulnerable else 0
    return consequence, human


def _accountability(text: str) -> tuple[str, ...]:
    if _has(
        text,
        (
            "prim ajutor",
            "cum poate fi prevenit",
            "protectia pacientului",
            "protectia consumatorului",
            "semne de avertizare",
        ),
    ):
        return ("practical_protection_lesson",)
    actor = _has_stem(
        text,
        (
            "autoritat",
            "institut",
            "ministr",
            "mapn",
            "sistem",
            "spital",
            "scoal",
        ),
    )
    failure = _has_stem(
        text,
        (
            "nu a detect",
            "nu au detect",
            "nu function",
            "esec",
            "vulnerabil",
            "neglijen",
            "prevent",
            "defect",
            "fragil",
        ),
    )
    responsibility = _has_stem(text, ("raspund", "responsab", "anchet")) or _has(
        text, ("explica", "a explicat", "cer explicatii", "sa explice")
    )
    public_actor = actor or _has_stem(
        text, ("regia", "regie", "companie public", "administratie public")
    )
    public_contract = _has_stem(text, ("contract", "achizit"))
    opacity = _has(
        text,
        (
            "fara publicare",
            "fara licitatie",
            "procedura netransparenta",
            "proceduri netransparente",
        ),
    )
    critical_system = _has_stem(
        text,
        (
            "centrala electr",
            "centrala nuclear",
            "reactor",
            "grup energetic",
            "grupul energetic",
            "retea electr",
            "sistem energetic",
        ),
    ) or bool(re.search(r"(?<!\w)grupul?\s+\d+(?!\w)", text))
    recalled_experts = _has_stem(text, ("pensionar", "specialist")) and _has_stem(
        text, ("chemat", "rechemat", "reven", "reporn")
    )
    physical_workaround = _has_stem(text, ("scufund", "barj")) and _has_stem(
        text, ("mentin", "evit", "function", "opr")
    )
    if public_actor and public_contract and opacity:
        return ("opaque_public_contracting",)
    if critical_system and (recalled_experts or physical_workaround):
        return ("critical_system_emergency_workaround",)
    if actor and failure:
        return ("preventable_system_failure",)
    if actor and responsibility:
        return ("institutional_accountability",)
    return ()


def _contradiction(text: str) -> tuple[str, ...]:
    material_benefit = _has_stem(
        text,
        ("salari", "bonus", "cazare", "transport plat", "masa", "prime"),
    )
    low_uptake = _has(
        text,
        (
            "nimeni nu vrea",
            "nimeni nu mai vrea",
            "nu se inghesuie",
            "nu-l vrea nimeni",
            "nu o vrea nimeni",
        ),
    ) or (
        _has_stem(text, ("numarul", "candidat", "angajat"))
        and _has_stem(text, ("scade", "putin", "lips"))
    )
    official_claim = _has_stem(
        text, ("presedinte", "premier", "ministr", "autoritat")
    ) and _has_stem(text, ("declar", "anunt", "sustin"))
    reversal = _has_stem(text, ("glum", "retract", "revenit asupra", "a negat apoi"))
    if material_benefit and low_uptake:
        return ("high_benefit_low_uptake",)
    if official_claim and reversal:
        return ("official_claim_reversal",)
    direct_inversion = _has(text, ("dar in realitate", "in loc sa"))
    two_sided_marker = _has(text, ("desi", "in timp ce"))
    mismatched_outcome = _has_stem(
        text,
        (
            "nimeni",
            "lipsa",
            "nu vrea",
            "nu poate",
            "fara",
            "scump",
            "surplus",
            "deficit",
            "esec",
        ),
    )
    if direct_inversion or (two_sided_marker and mismatched_outcome):
        return ("explicit_two_sided_contradiction",)
    if _has_stem(text, ("promis",)) and _has_stem(text, ("esec", "nu a", "incalcat")):
        return ("promise_outcome_inversion",)
    return ()


def _comic_roast(text: str) -> tuple[str, ...]:
    explicit_no_harm = _has(
        text,
        (
            "nu s-au inregistrat raniti",
            "nu au fost victime",
            "fara victime",
            "fara raniti",
            "no casualties",
            "no injuries",
        ),
    )
    harm = (
        _has_stem(text, ("murit", "ucis", "ranit", "victim")) and not explicit_no_harm
    )
    prestige = _has_stem(text, ("lux", "prestig", "exclusiv"))
    expensive = bool(
        re.search(r"\b[1-9][\d.]{3,}\s+(?:de\s+)?(?:euro|lei|dolari)\b", text)
    )
    failure = _has_stem(
        text, ("scufund", "defect", "prabus", "cedat", "esec", "distrus")
    )
    immediate = bool(
        re.search(r"\b(?:la\s+)?(?:doar|numai)?\s*\d+\s+(?:zile|ore)\b", text)
    )
    if not harm and (prestige or expensive) and failure and immediate:
        return ("prestige_immediate_failure",)
    if not harm and (prestige or expensive) and failure:
        return ("status_failure",)
    if not harm and _has_stem(text, ("a confundat", "a trezit", "a amanetat")):
        return ("concrete_bizarre_premise",)
    return ()


def _unusual_pattern(text: str) -> tuple[str, ...]:
    security_object = _has_stem(text, ("drona", "racheta", "munitie"))
    everyday_place = _has_stem(
        text, ("plaja", "turist", "scoala", "loc de joaca", "piata")
    )
    public_disruption = _has_stem(text, ("evacuat", "inchis", "izolat", "alert"))
    advanced_age = bool(
        re.search(r"(?<!\d)(?:6[5-9]|[7-9]\d|1\d{2})\s+(?:de\s+)?ani(?!\w)", text)
    )
    examination = _has_stem(text, ("examen", "bacalaureat", "proba", "permis"))
    delayed_step = _has_stem(
        text, ("anul viitor", "aman", "pregat", "mai tarziu", "urmatoarea sesiune")
    )
    valuable_find = _has_stem(text, ("gasit", "descoper")) and _has_stem(
        text, ("aur", "lingou", "comoara", "tezaur")
    )
    ownership_question = _has_stem(
        text, ("recompens", "proprietar", "apartine", "revendic")
    )
    heritage_remains = _has_stem(
        text, ("ramasite", "oseminte", "mormant", "sarcofag")
    ) and _has_stem(text, ("regi", "domnitor", "istoric", "medieval"))
    emergency_move = _has_stem(
        text, ("evacuat", "mutat", "relocat", "salvat")
    ) and _has_stem(text, ("incend", "inund", "cutremur", "prabus"))
    celestial_event = _has_stem(text, ("eclips", "luna plina", "mercur retrograd"))
    personal_effect = _has_stem(text, ("afectat", "provocat", "influentat"))
    if security_object and everyday_place and public_disruption:
        return ("security_everyday_collision",)
    if advanced_age and examination and delayed_step:
        return ("age_context_mismatch",)
    if valuable_find and ownership_question:
        return ("high_value_discovery_uncertain_ownership",)
    if heritage_remains and emergency_move:
        return ("heritage_emergency_relocation",)
    if celestial_event and personal_effect:
        return ("celestial_personal_causation",)
    unusual_method = _has_stem(text, ("otrav", "metoda neobisn", "mecanism rar"))
    multiple = _has_stem(text, ("doi", "doua", "mai multi", "multiple")) and _has_stem(
        text, ("victim", "barbat", "femei", "oameni")
    )
    more = _has(text, ("alte victime", "mai multe victime", "si alte victime"))
    if unusual_method and multiple and more:
        return ("expanding_victim_pattern",)
    if _has_stem(text, ("serie de incidente", "incidente repetate")):
        return ("explicit_repeated_anomaly",)
    unusual = _has_stem(text, ("fenomen neobisnuit", "mecanism neobisnuit"))
    persistent = _has_stem(text, ("continua", "persista", "repetat", "inca din"))
    grounded_context = _has_stem(
        text, ("ranger", "parc natural", "autoritat", "cercetator", "specialist")
    )
    if unusual and persistent and grounded_context:
        return ("persistent_anomalous_phenomenon",)
    return ()


def _cultural_discourse(text: str) -> tuple[str, ...]:
    youth = _has_stem(text, ("minor", "copil", "adolescent", "sub 15 ani"))
    digital_medium = (
        _has_stem(text, ("retea", "retel", "platform"))
        and _has_stem(text, ("socializare",))
    ) or _has(text, ("social media",))
    digital_policy = digital_medium and _has_stem(
        text, ("lege", "interzic", "reglement", "limit")
    )
    contested = _has_stem(text, ("respins", "anulat", "neconstitutional", "contestat"))
    neurodiversity = _has_stem(text, ("autism", "adhd", "tourette"))
    public_disclosure = _has_stem(
        text, ("diagnostic", "dezvaluit", "vorbit", "explica")
    )
    regional_infrastructure = _has_stem(
        text, ("autostrada", "coridor", "cale ferata", "interconect")
    ) and _has_stem(text, ("transfrontalier", "regional", "romania"))
    connection = _has_stem(text, ("conect", "lega", "construct", "traseu"))
    if youth and digital_policy and contested:
        return ("contested_youth_digital_policy",)
    if neurodiversity and public_disclosure:
        return ("public_neurodiversity_disclosure",)
    if regional_infrastructure and connection:
        return ("cross_border_infrastructure_discussion",)
    topic = _has_stem(
        text, ("dezinform", "propaganda", "controvers", "dezbatere", "reactii online")
    )
    public = _has_stem(text, ("public", "social", "cultural", "online", "identitat"))
    return ("meaningful_public_discourse",) if topic and public else ()


def _context_by_event(items: tuple) -> dict[int, object]:
    if type(items) is not tuple:
        raise ValueError("Invalid V1.2 context collection")
    result = {}
    for item in items:
        if item.event_id in result:
            raise ValueError("Duplicate V1.2 context")
        result[item.event_id] = item
    return result


def _validate_candidate(candidate: EditorialCandidateV1_2) -> None:
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
        raise ValueError("Invalid V1.2 candidate")


def _rank_key(item: EditorialEvidenceV1_2) -> tuple[int, int, int, int, float, int]:
    return (
        -int(item.talkworthiness),
        -item.leverage_strength,
        -item.significance_strength,
        -item.source_count,
        -item.last_seen_at.timestamp(),
        item.event_id,
    )


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(
        r"\s+", " ", "".join(c for c in normalized if not unicodedata.combining(c))
    )


def _has(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _has_stem(text: str, stems: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(stem)}\w*(?!\w)", text) for stem in stems)


__all__ = [
    "DiscussionBridgeContextV1_2",
    "EditorialCandidateV1_2",
    "EditorialEvidenceV1_2",
    "EpisodeRecommendationV1_2",
    "MaterialContinuityContextV1_2",
    "PoolUtilityDecisionV1_2",
    "TalkworthinessTierV1_2",
    "pool_utility_v1_2",
    "recommend_episode_v1_2",
]
