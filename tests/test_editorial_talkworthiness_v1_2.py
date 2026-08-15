from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.database import initialize_database
from pastila_scout.desktop_v1.entrypoint import _publish_candidates
from pastila_scout.editorial_talkworthiness_v1_2 import (
    DiscussionBridgeContextV1_2,
    EditorialCandidateV1_2,
    MaterialContinuityContextV1_2,
    TalkworthinessTierV1_2,
    pool_utility_v1_2,
    recommend_episode_v1_2,
)

NOW = datetime(2026, 8, 14, tzinfo=UTC)


def candidate(
    event_id: int,
    text: str,
    *,
    category: str = "Social",
    sources: int = 1,
    minutes: int = 0,
) -> EditorialCandidateV1_2:
    return EditorialCandidateV1_2(
        event_id,
        text,
        text,
        category,
        sources,
        NOW + timedelta(minutes=minutes),
    )


def evaluation(item: EditorialCandidateV1_2, **kwargs):
    return recommend_episode_v1_2((item,), **kwargs).evaluations[0]


def test_severity_and_human_stakes_cannot_create_talkworthiness():
    item = candidate(
        1,
        "Accident rutier grav: doi soti au murit si trei copii au fost raniti.",
        sources=9,
    )

    result = evaluation(item)

    assert (result.consequence, result.human_stakes) == (2, 2)
    assert result.significance_strength == 4
    assert result.leverage_strength == 0
    assert result.talkworthiness is TalkworthinessTierV1_2.NONE
    assert result.eligible is False
    assert result.disposition == "retellable_only"


def test_serious_system_failure_is_talkworthy_without_humor():
    item = candidate(
        2,
        "Accident cu morti dupa ce sistemul public defect nu a functionat; "
        "autoritatile explica vulnerabilitatea prevenibila.",
    )

    result = evaluation(item)

    assert result.accountability_system == 2
    assert result.comic_roast == 0
    assert result.talkworthiness is TalkworthinessTierV1_2.STRONG


def test_practical_protection_lesson_makes_serious_story_discussable():
    result = evaluation(
        candidate(
            25,
            "Dupa incidentul din scoala, medicii explica semne de avertizare si prim ajutor.",
        )
    )

    assert result.accountability_system == 1
    assert result.talkworthiness is TalkworthinessTierV1_2.BOUNDED


def test_plural_detection_failure_is_accountability_evidence():
    result = evaluation(
        candidate(22, "Radarele MApN nu au detectat drona care a explodat.")
    )

    assert result.accountability_system == 2


def test_institution_mention_without_failure_is_not_accountability():
    result = evaluation(candidate(3, "Ministerul a publicat un anunt despre sedinta."))

    assert result.accountability_system == 0
    assert result.talkworthiness is TalkworthinessTierV1_2.NONE


def test_explicit_word_and_routine_official_dispute_do_not_fake_accountability():
    result = evaluation(
        candidate(
            26,
            "Primarul il contrazice pe ministru despre sporul de 20%; autoritatile "
            "locale au cerut explicit mentinerea lui.",
            category="Politica",
        )
    )

    assert result.accountability_system == 0
    assert result.talkworthiness is TalkworthinessTierV1_2.NONE


def test_explicit_contradiction_is_editorial_leverage():
    result = evaluation(
        candidate(4, "Romania importa energie scumpa seara, desi la pranz are surplus.")
    )

    assert result.contradiction == 2
    assert result.talkworthiness is TalkworthinessTierV1_2.STRONG


def test_temporal_desi_clause_is_not_automatically_a_contradiction():
    result = evaluation(
        candidate(27, "Fenomenul continua, desi primele focare au aparut anul trecut.")
    )

    assert result.contradiction == 0


def test_persistent_grounded_anomaly_is_pattern_but_novelty_alone_is_not():
    persistent = evaluation(
        candidate(
            28,
            "Fenomen neobisnuit in parcul natural: continua de anul trecut si le da "
            "de cap rangerilor.",
        )
    )
    novelty = evaluation(
        candidate(29, "Fenomen neobisnuit: un copac arde din interior.")
    )

    assert persistent.unusual_pattern == 1
    assert persistent.talkworthiness is TalkworthinessTierV1_2.BOUNDED
    assert novelty.unusual_pattern == 0
    assert novelty.talkworthiness is TalkworthinessTierV1_2.NONE


def test_prestige_object_immediate_failure_is_strong_roast_premise():
    result = evaluation(
        candidate(
            5,
            "Un iaht de lux de 8.000.000 de euro s-a scufundat la doar 4 zile de la livrare.",
            category="Diverse",
        )
    )

    assert result.comic_roast == 2
    assert result.talkworthiness is TalkworthinessTierV1_2.STRONG


def test_explicit_no_injuries_does_not_suppress_verified_prestige_failure():
    result = evaluation(
        candidate(
            24,
            "Un iaht de lux de 8.000.000 de euro s-a scufundat la doar 4 zile; "
            "pasagerii au fost evacuati si nu s-au inregistrat raniti.",
            category="Diverse",
        )
    )

    assert result.comic_roast == 2


def test_price_alone_and_expensive_tragedy_do_not_create_roast():
    expensive = evaluation(candidate(6, "Un iaht de lux costa 8.000.000 de euro."))
    tragedy = evaluation(
        candidate(
            7, "Masina de lux de 200.000 de euro s-a prabusit; doi oameni au murit."
        )
    )

    assert expensive.comic_roast == tragedy.comic_roast == 0


def test_ordinary_company_product_failure_is_not_strong_accountability_or_roast():
    result = evaluation(
        candidate(16, "Un produs obisnuit al companiei s-a defectat dupa un an.")
    )

    assert result.accountability_system == 0
    assert result.comic_roast == 0
    assert result.talkworthiness is TalkworthinessTierV1_2.NONE


def test_explicit_expanding_poisoning_pattern_is_leverage_but_generic_murder_is_not():
    pattern = evaluation(
        candidate(
            8,
            "Au otravit si ucis doi barbati; autoritatile cred ca exista si alte victime.",
            category="Externe",
        )
    )
    generic = evaluation(candidate(9, "Un barbat a fost ucis intr-un atac violent."))

    assert pattern.unusual_pattern == 2
    assert pattern.talkworthiness is TalkworthinessTierV1_2.STRONG
    assert generic.unusual_pattern == 0
    assert generic.talkworthiness is TalkworthinessTierV1_2.NONE


def test_discussion_bridge_requires_explicit_context():
    item = candidate(
        10,
        "Suedia a redus varsta raspunderii penale de la 15 la 14 ani.",
        category="Externe",
    )
    absent = evaluation(item)
    present = evaluation(
        item,
        discussion_bridges=(
            DiscussionBridgeContextV1_2(
                10,
                "Ar trebui Romania sa compare varsta raspunderii penale?",
                "Suedia a redus pragul legal la 14 ani.",
            ),
        ),
    )

    assert absent.discussion_bridge == 0
    assert absent.talkworthiness is TalkworthinessTierV1_2.NONE
    assert present.discussion_bridge == 2
    assert present.talkworthiness is TalkworthinessTierV1_2.STRONG


def test_cultural_discourse_requires_more_than_popularity():
    discourse = evaluation(
        candidate(11, "Controversa online a deschis o dezbatere culturala publica.")
    )
    viral = evaluation(candidate(12, "Clipul unei vedete a devenit viral."))

    assert discourse.cultural_discourse == 2
    assert viral.cultural_discourse == 0


def test_historical_style_leverage_families_and_holdout_remain_individual_evidence():
    examples = (
        candidate(30, "Ministerul explica vulnerabilitatea sistemului defect."),
        candidate(31, "Un obiect de lux de 90.000 euro s-a defectat la doar 2 ore."),
        candidate(32, "Dezinformarea online a creat o dezbatere culturala publica."),
        candidate(33, "Un fenomen neobisnuit arata o serie de incidente repetate."),
    )

    results = recommend_episode_v1_2(examples).evaluations

    assert all(
        item.talkworthiness >= TalkworthinessTierV1_2.BOUNDED for item in results
    )
    assert (
        evaluation(
            candidate(34, "O vedeta a publicat un clip foarte viral.")
        ).talkworthiness
        is TalkworthinessTierV1_2.NONE
    )


@pytest.mark.parametrize(
    ("family", "text", "expected"),
    (
        (
            "accountability_system",
            "Regia judeteana a acordat contracte fara licitatie, iar conducerea da explicatii.",
            True,
        ),
        (
            "accountability_system",
            "Centrala electrica a rechemat pensionari ca sa reporneasca grupul 2.",
            True,
        ),
        (
            "accountability_system",
            "Regia a publicat lista contractelor atribuite prin licitatie.",
            False,
        ),
        (
            "accountability_system",
            "Pensionarii au vizitat centrala electrica la aniversare.",
            False,
        ),
        (
            "contradiction",
            "Fabrica ofera salariu mare, transport si cazare, dar nu se inghesuie candidatii.",
            True,
        ),
        (
            "contradiction",
            "Ministrul a anuntat interdictia, apoi a spus ca glumea.",
            True,
        ),
        (
            "contradiction",
            "Fabrica ofera salarii bune si a angajat cincizeci de candidati.",
            False,
        ),
        (
            "contradiction",
            "Un actor a glumit despre o interdictie imaginara.",
            False,
        ),
        (
            "unusual_pattern",
            "La 72 de ani, candidatul a amanat ultima proba a examenului pentru sesiunea urmatoare.",
            True,
        ),
        (
            "unusual_pattern",
            "Zidarii au descoperit un tezaur, dar proprietarul si recompensa sunt incerte.",
            True,
        ),
        (
            "unusual_pattern",
            "La 72 de ani, absolventul a primit diploma dupa examen.",
            False,
        ),
        (
            "unusual_pattern",
            "Muzeul a expus tezaurul al carui proprietar este cunoscut.",
            False,
        ),
        (
            "cultural_discourse",
            "Curtea a anulat legea care limita platformele de socializare pentru adolescenti.",
            True,
        ),
        (
            "cultural_discourse",
            "O profesoara a dezvaluit diagnosticul de ADHD si a explicat experienta public.",
            True,
        ),
        (
            "cultural_discourse",
            "Parlamentul a adoptat legea raportarii fiscale online.",
            False,
        ),
        (
            "cultural_discourse",
            "Actrita a dezvaluit ca s-a operat la genunchi.",
            False,
        ),
    ),
)
def test_romanian_leverage_recognizers_generalize_without_single_word_triggers(
    family, text, expected
):
    result = evaluation(candidate(100, text))

    assert (getattr(result, family) > 0) is expected


def test_continuity_requires_explicit_material_development():
    item = candidate(13, "A aparut o informatie noua despre cazul urmarit.")
    duplicate = evaluation(
        item,
        continuity_context=(MaterialContinuityContextV1_2(13, 12, "caz", False),),
    )
    material = evaluation(
        item,
        continuity_context=(MaterialContinuityContextV1_2(13, 12, "caz", True),),
    )

    assert duplicate.material_continuity == 0
    assert material.material_continuity == 2


def test_source_count_cannot_rescue_filler_or_retellable_story():
    loto = candidate(14, "Rezultate LOTO: numerele extrase si jackpotul", sources=8)
    tragedy = candidate(15, "Accident fatal: doi oameni au murit.", sources=20)

    assert pool_utility_v1_2(loto).exclusion_reason == "routine_loto"
    assert evaluation(tragedy).eligible is False


def test_pool_filter_high_precision_classes_and_overrides():
    cases = (
        ("routine_sport", "Meci de fotbal: rezultat si calificare in finala"),
        (
            "generic_celebrity_promotion",
            "Vedeta a postat fotografii si isi promoveaza emisiunea",
        ),
        ("routine_calendar", "Calendarul examenelor si programul vacantei"),
        (
            "generic_tradition_explainer",
            "Traditii si superstitii: semnificatia sarbatorii",
        ),
        (
            "generic_lifestyle_howto",
            "O vedeta te invata cum sa faci inghetata cu cafea",
        ),
        (
            "generic_celebrity_promotion",
            "Afla cine sunt noii concurenti din reality show-ul care debuteaza la PRO TV",
        ),
    )
    for reason, text in cases:
        assert pool_utility_v1_2(candidate(20, text)).exclusion_reason == reason
    useful_sport = candidate(
        21, "Frauda si coruptie in liga de fotbal, ancheta penala deschisa"
    )
    assert pool_utility_v1_2(useful_sport).useful is True

    event_program = candidate(23, "Programul evenimentelor: ceremonii si parade")
    assert pool_utility_v1_2(event_program).exclusion_reason == "routine_calendar"
    media_departure = candidate(
        35, "Demisie la televiziune: vedeta si prezentatorul paraseste postul"
    )
    assert (
        pool_utility_v1_2(media_departure).exclusion_reason
        == "generic_celebrity_promotion"
    )


def test_ranking_is_deterministic_and_caps_are_maximum_only():
    items = tuple(
        candidate(
            event_id,
            "Autoritatile explica vulnerabilitatea sistemului defect care nu a functionat.",
            category="Politica" if event_id < 6 else "Social",
            sources=event_id,
            minutes=event_id,
        )
        for event_id in range(1, 10)
    )

    forward = recommend_episode_v1_2(items)
    reverse = recommend_episode_v1_2(tuple(reversed(items)))

    assert tuple(item.event_id for item in forward.recommendations) == tuple(
        item.event_id for item in reverse.recommendations
    )
    assert sum(item.category == "Politica" for item in forward.recommendations) == 2
    assert sum(item.category == "Social" for item in forward.recommendations) == 3
    assert forward.available_slots == 5


def _database(path: Path, rows: list[tuple[int, str, str, str, int]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        for event_id, title, summary, category, sources in rows:
            connection.execute(
                """INSERT INTO events
                   (id, canonical_title, normalized_title, summary, category,
                    first_seen_at, last_seen_at, article_count, source_count,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                (
                    event_id,
                    title,
                    title.casefold(),
                    summary,
                    category,
                    NOW.isoformat(),
                    (NOW + timedelta(minutes=event_id)).isoformat(),
                    sources,
                    NOW.isoformat(),
                    NOW.isoformat(),
                ),
            )


def test_active_project_v1_2_filters_before_intake_and_does_not_pad(tmp_path):
    database = tmp_path / "scout.db"
    rows = [
        (1, "Rezultate LOTO", "Numere extrase si jackpot", "Social", 8),
        (2, "Fotbal", "Rezultat meci si calificare in finala", "Diverse", 7),
        (
            3,
            "Sistem fragil",
            "Autoritatile explica vulnerabilitatea sistemului defect care nu a functionat.",
            "Social",
            1,
        ),
    ]
    _database(database, rows)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    useful = store.list_useful_candidates_v1_2()
    recommendation = store.recommend_episode_v1_2()

    assert tuple(item.event_id for item in useful) == (3,)
    assert tuple(item.event_id for item in recommendation.recommendations) == (3,)
    assert store.list_candidates(category="Social")[0].event_id == 1
    assert len(useful) < 50
    assert not (tmp_path / "project.json").exists()


def test_v1_2_api_does_not_redirect_frozen_v1_1(tmp_path):
    database = tmp_path / "scout.db"
    _database(
        database,
        [
            (
                1,
                "Accident fatal",
                "Doi soti au murit si trei copii au fost raniti.",
                "Social",
                9,
            )
        ],
    )
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    v1_1 = store.recommend_episode_v1_1()
    v1_2 = store.recommend_episode_v1_2()

    assert tuple(item.event_id for item in v1_1.recommendations) == (1,)
    assert v1_2.recommendations == ()


def test_desktop_toate_uses_useful_pool_but_explicit_category_remains_pure():
    class Store:
        def __init__(self):
            self.calls = []

        def list_useful_candidates_v1_2(self):
            self.calls.append(("useful", None))
            return ()

        def list_candidates(self, *, category=None):
            self.calls.append(("frozen", category))
            return ()

    class View:
        def publish_candidates(self, *, candidates):
            assert candidates == ()

    store = Store()
    view = View()

    _publish_candidates(view, store)
    _publish_candidates(view, store, "Externe")

    assert store.calls == [("useful", None), ("frozen", "Externe")]
