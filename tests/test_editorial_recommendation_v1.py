from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from pastila_scout.editorial_recommendation_v1 import (
    EditorialCandidateV1,
    recommend_episode_v1,
)

NOW = datetime(2026, 8, 14, 12, tzinfo=UTC)


def candidate(
    event_id: int,
    category: str,
    title: str = "Ancheta publica provoaca o controversa",
    *,
    sources: int = 3,
    age: int = 0,
) -> EditorialCandidateV1:
    return EditorialCandidateV1(
        event_id,
        title,
        "Autoritatile sunt criticate pentru impactul social al deciziei.",
        category,
        sources,
        NOW - timedelta(minutes=age),
    )


def recommended_ids(*items: EditorialCandidateV1) -> tuple[int, ...]:
    return tuple(x.event_id for x in recommend_episode_v1(tuple(items)).recommendations)


def test_routine_loto_and_sport_lose_to_editorial_material() -> None:
    loto = EditorialCandidateV1(
        1,
        "LOTO: numerele extrase si premiul jackpot",
        "Rezultatul extragerii de astazi.",
        "Social",
        8,
        NOW,
    )
    sport = EditorialCandidateV1(
        2,
        "David Popovici s-a calificat in finala",
        "Rezultatul competitiei sportive.",
        "Diverse",
        7,
        NOW,
    )
    strong = candidate(3, "Politica", sources=4)
    result = recommend_episode_v1((loto, sport, strong))

    assert tuple(x.event_id for x in result.recommendations) == (3,)
    excluded = {x.event_id: x.exclusion_reason for x in result.evaluations}
    assert excluded == {1: "routine_loto", 2: "routine_sport", 3: None}


def test_sport_scandal_is_not_excluded_merely_for_sport_terms() -> None:
    item = candidate(1, "Social", "Scandal de coruptie la clubul de fotbal")
    evidence = recommend_episode_v1((item,)).evaluations[0]
    assert evidence.eligible is True
    assert evidence.routine_sport is False

    routine_children = EditorialCandidateV1(
        2,
        "Echipa de copii a castigat meciul final",
        "Rezultatul competitiei a fost anuntat.",
        "Social",
        6,
        NOW,
    )
    assert (
        recommend_episode_v1((routine_children,)).evaluations[0].exclusion_reason
        == "routine_sport"
    )


def test_lottery_context_does_not_confuse_joker_film_award() -> None:
    film = EditorialCandidateV1(
        1,
        "Filmul Joker castiga un premiu international",
        "Ceremonia a avut loc aseara.",
        "Externe",
        2,
        NOW,
    )
    evidence = recommend_episode_v1((film,)).evaluations[0]
    assert evidence.routine_loto is False
    assert evidence.eligible is True

    scandal = EditorialCandidateV1(
        2,
        "Scandal de coruptie la Loteria nationala",
        "Autoritatile ancheteaza extragerile si premiile.",
        "Social",
        5,
        NOW,
    )
    scandal_evidence = recommend_episode_v1((scandal,)).evaluations[0]
    assert scandal_evidence.routine_loto is False
    assert scandal_evidence.eligible is True


def test_protected_politica_and_cancan_targets_are_bounded_by_eligibility() -> None:
    items = tuple(
        candidate(i, "Politica", sources=10 - i) for i in range(1, 5)
    ) + tuple(
        candidate(i, "CanCan", "Vedeta provoaca un scandal bizar", sources=10 - i)
        for i in range(5, 8)
    )
    result = recommend_episode_v1(items)
    counts = Counter(x.category for x in result.recommendations)
    assert counts == {"Politica": 2, "CanCan": 1}

    weak = EditorialCandidateV1(
        20, "Horoscop pentru toate zodiile", "Previziuni astrale.", "CanCan", 3, NOW
    )
    assert recommended_ids(weak) == ()

    promotion = EditorialCandidateV1(
        21,
        "Record pentru artista: performanta uriasa",
        "Artista a anuntat rezultatul.",
        "CanCan",
        1,
        NOW,
    )
    evidence = recommend_episode_v1((promotion,)).evaluations[0]
    assert evidence.exclusion_reason == "generic_celebrity_promotion"

    published = EditorialCandidateV1(
        22,
        "Vedeta a publicat imagini cu familia",
        "Fotografiile au fost publicate online.",
        "CanCan",
        1,
        NOW,
    )
    assert (
        recommend_episode_v1((published,)).evaluations[0].exclusion_reason
        == "generic_celebrity_promotion"
    )

    corroborated_promotion = EditorialCandidateV1(
        23,
        "Vedeta a publicat imagini adorabile",
        "Fotografiile au fost preluate de mai multe publicatii.",
        "CanCan",
        4,
        NOW,
    )
    assert (
        recommend_episode_v1((corroborated_promotion,)).evaluations[0].exclusion_reason
        == "generic_celebrity_promotion"
    )

    wedding = EditorialCandidateV1(
        24,
        "Nunta surpriza a unei vedete provoaca un scandal",
        "Invitatii acuza organizatorii.",
        "CanCan",
        1,
        NOW,
    )
    assert recommend_episode_v1((wedding,)).evaluations[0].eligible is True


def test_zero_one_two_and_more_externe_are_not_forced_and_never_exceed_two() -> None:
    for count, expected in ((0, 0), (1, 1), (2, 2), (4, 2)):
        foreign = tuple(
            candidate(100 + i, "Externe", sources=5 - i) for i in range(count)
        )
        domestic = tuple(candidate(200 + i, "Social") for i in range(4))
        result = recommend_episode_v1(foreign + domestic)
        assert sum(x.category == "Externe" for x in result.recommendations) == expected
    weak = EditorialCandidateV1(
        300, "Prognoza meteo pentru weekend", "Temperaturi normale.", "Externe", 3, NOW
    )
    assert recommended_ids(weak) == ()


@pytest.mark.parametrize("category,cap", (("Politica", 2), ("CanCan", 1)))
@pytest.mark.parametrize("available", (0, 1, 2, 4))
def test_protected_targets_select_only_available_eligible_items(
    category: str, cap: int, available: int
) -> None:
    items = tuple(candidate(i + 1, category, sources=5 - i) for i in range(available))
    result = recommend_episode_v1(items)
    assert len(result.recommendations) == min(available, cap)


def test_all_caps_and_total_are_enforced_by_competitive_rank() -> None:
    categories = (
        *("Politica" for _ in range(4)),
        *("Social" for _ in range(5)),
        *("CanCan" for _ in range(3)),
        *("Diverse" for _ in range(5)),
        *("Externe" for _ in range(4)),
    )
    items = tuple(
        candidate(i + 1, category, sources=10 - i % 8)
        for i, category in enumerate(categories)
    )
    result = recommend_episode_v1(items)
    counts = Counter(x.category for x in result.recommendations)
    assert len(result.recommendations) == 10
    assert counts["Politica"] <= 2
    assert counts["Social"] <= 3
    assert counts["CanCan"] <= 1
    assert counts["Diverse"] <= 3
    assert counts["Externe"] <= 2


def test_competitive_eleventh_candidate_loses_by_rank_not_category_order() -> None:
    items = (
        *(candidate(i, "Politica") for i in range(1, 3)),
        candidate(3, "CanCan", "Vedeta intr-un scandal bizar"),
        *(candidate(i, "Social", sources=6) for i in range(4, 7)),
        *(candidate(i, "Diverse", sources=5) for i in range(7, 10)),
        *(candidate(i, "Externe", sources=4) for i in range(10, 12)),
    )
    result = recommend_episode_v1(tuple(items))
    assert len(result.recommendations) == 10
    assert 11 not in recommended_ids(*items)
    assert (
        next(x for x in result.evaluations if x.event_id == 11).disposition
        == "eligible_but_below_episode_cutoff"
    )


def test_editorial_fit_beats_raw_source_count_and_sport_substrings_do_not_exclude() -> (
    None
):
    generic = EditorialCandidateV1(
        1, "Anunt general despre un serviciu", "Detalii disponibile.", "Diverse", 8, NOW
    )
    strong = EditorialCandidateV1(
        2,
        "Primarul acuzat de abuz intr-un scandal bizar",
        "Ancheta continua.",
        "Diverse",
        4,
        NOW,
    )
    mongolia = EditorialCandidateV1(
        3,
        "Mongolia schimba o lege publica",
        "Decizia a fost anuntata.",
        "Externe",
        2,
        NOW,
    )
    result = recommend_episode_v1((generic, strong, mongolia))
    assert result.recommendations[0].event_id == 2
    assert next(x for x in result.evaluations if x.event_id == 3).routine_sport is False


def test_corroboration_then_recency_then_event_id_are_deterministic() -> None:
    more_sources = candidate(9, "Social", sources=5, age=20)
    fewer_sources = candidate(1, "Social", sources=4)
    recent = candidate(7, "Diverse", sources=3)
    old = candidate(6, "Diverse", sources=3, age=1)
    same_recent_high_id = candidate(5, "Externe", sources=2)
    same_recent_low_id = candidate(4, "Externe", sources=2)
    result = recommend_episode_v1(
        (
            fewer_sources,
            more_sources,
            old,
            recent,
            same_recent_high_id,
            same_recent_low_id,
        )
    )
    assert tuple(x.event_id for x in result.recommendations) == (9, 1, 7, 6, 4, 5)


def test_similar_editorial_fit_scales_with_one_two_four_and_eight_sources() -> None:
    items = tuple(
        candidate(i, "Diverse", sources=sources)
        for i, sources in enumerate((1, 2, 4, 8), 1)
    )
    result = recommend_episode_v1(items)
    scores = {item.source_count: item.editorial_score for item in result.evaluations}
    assert scores[1] < scores[2] < scores[4] < scores[8]


def test_recommendation_is_independent_of_input_order_and_signals_are_not_double_counted() -> (
    None
):
    items = tuple(candidate(i, "Diverse", sources=5 - i) for i in range(1, 4))
    forward = recommend_episode_v1(items)
    reverse = recommend_episode_v1(tuple(reversed(items)))
    assert forward == reverse

    controversy_only = EditorialCandidateV1(
        20,
        "Scandal local",
        "Detalii noi.",
        "Diverse",
        1,
        NOW,
    )
    evidence = recommend_episode_v1((controversy_only,)).evaluations[0]
    assert evidence.satire_roast is True
    assert evidence.controversy is True
    assert evidence.editorial_score == 8


def test_short_complete_words_do_not_match_unrelated_prefixes() -> None:
    item = EditorialCandidateV1(
        1,
        "Warning about a courtyard near a golf course and a legendary taxi",
        "A familiar mortgage notice was issued.",
        "Externe",
        2,
        NOW,
    )
    evidence = recommend_episode_v1((item,)).evaluations[0]
    assert evidence.controversy is False
    assert evidence.public_interest is False
    assert evidence.routine_sport is False


def test_bounded_eu_regulatory_change_is_public_interest() -> None:
    item = EditorialCandidateV1(
        1,
        "Se schimba regulile pentru masinile noi din UE",
        "Automobilele trebuie sa contina plastic reciclat.",
        "Diverse",
        1,
        NOW,
    )
    evidence = recommend_episode_v1((item,)).evaluations[0]
    assert evidence.public_interest is True
    assert evidence.eligible is True


def test_input_pool_is_not_mutated_and_nonrecommended_identity_remains_available() -> (
    None
):
    pool = tuple(candidate(i, "Social", sources=20 - i) for i in range(1, 6))
    before = tuple((x.event_id, x.title) for x in pool)
    result = recommend_episode_v1(pool)
    assert tuple((x.event_id, x.title) for x in pool) == before
    assert len(result.recommendations) == 3
    assert {x.event_id for x in pool} - {x.event_id for x in result.recommendations}


def test_explanations_and_dispositions_are_explicit() -> None:
    items = tuple(candidate(i, "Politica", sources=10 - i) for i in range(1, 4))
    result = recommend_episode_v1(items)
    assert all("surse" in x.explanation for x in result.evaluations)
    assert result.evaluations[2].disposition == "eligible_but_category_cap_reached"
