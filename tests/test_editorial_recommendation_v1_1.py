from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from pastila_scout.editorial_recommendation_v1_1 import (
    ContinuityContextV1_1,
    EditorialCandidateV1_1,
    recommend_episode_v1_1,
)

NOW = datetime(2026, 8, 14, 12, tzinfo=UTC)


def candidate(
    event_id: int,
    text: str,
    *,
    category: str = "Diverse",
    sources: int = 1,
    age: int = 0,
) -> EditorialCandidateV1_1:
    return EditorialCandidateV1_1(
        event_id,
        text,
        "Context editorial disponibil.",
        category,
        sources,
        NOW - timedelta(minutes=age),
    )


def evidence(text: str, **kwargs):
    return recommend_episode_v1_1((candidate(1, text, **kwargs),)).evaluations[0]


def test_consequence_requires_effect_not_institution_or_category() -> None:
    institution = evidence("Ministrul a participat la o sedinta", category="Politica")
    safety = evidence("Ambulanta a fost atacata si un pacient a fost ranit")
    consumer = evidence("Frauda a produs pierderi consumatorilor de milioane de lei")

    assert institution.consequence == 0
    assert institution.eligible is False
    assert safety.consequence == 1
    assert consumer.consequence >= 1


def test_contradiction_is_not_generic_criticism_scandal_or_disagreement() -> None:
    generic = evidence("Scandal politic dupa critici si dezacord public")
    role = evidence("Politistul a amanetat laptopul de serviciu pentru jocuri de noroc")
    gap = evidence("Programul exista numai pe hartie si nu functioneaza")

    assert generic.contradiction == 0
    assert role.contradiction == 2
    assert gap.contradiction == 1


def test_human_value_requires_harm_lesson_or_injustice_not_person_mention() -> None:
    mention = evidence("Un copil si familia sa au participat la eveniment")
    harm = evidence("Un elev a murit, iar scolile cer cursuri de prim ajutor")
    routine = evidence("Un pacient a ajuns la o consultatie obisnuita")

    assert mention.human_value == 0
    assert harm.human_value == 2
    assert harm.comic_visual == 0
    assert routine.human_value == 0


def test_intimate_partner_assault_has_human_value_without_person_inflation() -> None:
    assault = evidence("A intrat in locuinta fostei iubite si a agresat-o")
    ordinary = evidence("Fosta iubita a participat la un eveniment")
    assert assault.human_value == 2
    assert ordinary.human_value == 0


def test_explicit_no_current_victims_suppresses_historical_harm_context() -> None:
    item = evidence(
        "Explozie la fabrica; un accident similar a ranit muncitori in 2007, "
        "dar incidentul actual nu a cauzat victime"
    )
    assert item.human_value == 0


def test_comic_visual_requires_concrete_premise_not_novelty_adjective() -> None:
    adjective = evidence("Incident bizar si incredibil relatat local")
    object_story = evidence("Politistul a amanetat un laptop amanetat")
    animal = evidence("Un cerb beat a blocat strada")

    assert adjective.comic_visual == 0
    assert object_story.comic_visual == 1
    assert object_story.comic_type == "contextual"
    assert animal.comic_visual == 2


def test_concrete_physical_hazard_is_visual_but_generic_object_is_not() -> None:
    hazard = evidence("Obiecte metalice ascutite au fost puse pe autostrada")
    generic = evidence("Mai multe obiecte au fost inventariate intr-un depozit")
    assert hazard.comic_visual == 2
    assert generic.comic_visual == 0


def test_cultural_discourse_requires_behavior_or_debate_not_virality() -> None:
    viral = evidence("Clipul viral al unei vedete populare este in trending")
    misinformation = evidence(
        "Un zvon fals pe TikTok a provocat panica online si atacarea ambulantei"
    )
    culture = evidence("Filmul controversat a declansat un razboi cultural")

    assert viral.cultural_discourse == 0
    assert misinformation.cultural_discourse == 2
    assert culture.cultural_discourse == 2


def test_family_aggregation_prevents_single_fact_from_automatic_double_counting() -> (
    None
):
    institutional = evidence(
        "Politistul a amanetat echipamentul pentru jocuri de noroc"
    )
    human = evidence("Un copil a fost ranit intr-un accident")
    viral = evidence("Un scandal viral despre o vedeta")
    bizarre = evidence("O femeie a ascuns o narghilea intr-un cozonac")

    assert (institutional.contradiction, institutional.human_value) == (2, 0)
    assert (human.human_value, human.contradiction) == (2, 0)
    assert (viral.contradiction, viral.cultural_discourse, viral.comic_visual) == (
        0,
        0,
        0,
    )
    assert (bizarre.comic_visual, bizarre.consequence) == (2, 0)


def test_distinct_public_safety_and_human_evidence_can_both_score() -> None:
    item = evidence(
        "Ambulanta a fost atacata, un pacient a fost ranit si lipsit de ingrijire"
    )
    assert item.consequence == 1
    assert item.human_value == 2
    assert item.story_value == sum(
        (
            item.consequence,
            item.contradiction,
            item.human_value,
            item.comic_visual,
            item.continuity,
            item.cultural_discourse,
        )
    )


def test_local_visual_attack_is_not_inflated_to_strong_consequence() -> None:
    item = evidence("Un pescar a fost atacat de o caracatita si a scapat")
    assert item.consequence == 1
    assert item.comic_visual == 1
    assert item.story_value == 2


def test_fatal_or_direct_security_consequence_is_strong() -> None:
    fatal = evidence("Doi pasageri au murit intr-un incendiu la tren")
    direct_security = evidence("Dronele au incalcat spatiul aerian national")
    generic_security = evidence("Oficialii au discutat despre securitate nationala")
    assert fatal.consequence == 2
    assert direct_security.consequence == 2
    assert generic_security.consequence == 1


def test_system_dependency_irony_is_generalized_contradiction() -> None:
    ironic = evidence(
        "Pensionarii au fost chemati de acasa sa reporneasca serviciul esential"
    )
    ordinary = evidence("Pensionarii au fost invitati la o ceremonie")
    assert ironic.contradiction == 1
    assert ordinary.contradiction == 0


def test_cultural_institution_naming_dispute_is_not_generic_name_mention() -> None:
    dispute = evidence(
        "Cultural center board votes again to inscribe a name after a judge blocked it"
    )
    ordinary = evidence("Cultural center announces the name of its new director")
    assert dispute.cultural_discourse == 2
    assert dispute.contradiction == 1
    assert ordinary.cultural_discourse == 0


def test_story_value_excludes_sources_category_and_recency() -> None:
    text = "Ambulanta a fost atacata si un pacient a fost ranit"
    items = (
        candidate(1, text, category="Social", sources=1, age=30),
        candidate(2, text, category="Externe", sources=9),
    )
    result = recommend_episode_v1_1(items)
    assert result.evaluations[0].story_value == result.evaluations[1].story_value
    assert result.recommendations[0].event_id == 2


def test_lexicographic_story_value_beats_source_count() -> None:
    exceptional = candidate(1, "Un elev a murit si scolile cer cursuri de prim ajutor")
    weaker = candidate(2, "O frauda de pret afecteaza consumatorii", sources=10)
    result = recommend_episode_v1_1((weaker, exceptional))
    assert result.recommendations[0].event_id == 1
    assert result.evaluations[0].corroboration_contribution == 2
    assert result.evaluations[1].corroboration_contribution == 20


@pytest.mark.parametrize(
    ("higher", "lower"),
    (
        (
            "Un elev a murit si scolile cer cursuri de prim ajutor",
            "Un urs beat a fost trezit si amendat cu mii de euro",
        ),
        (
            "Un urs beat a fost trezit si amendat cu mii de euro",
            "Fosta iubita a fost agresata in locuinta",
        ),
        (
            "Fosta iubita a fost agresata in locuinta",
            "Frauda afecteaza consumatorii",
        ),
    ),
)
def test_each_adjacent_story_value_outranks_eight_source_lower_value(
    higher, lower
) -> None:
    result = recommend_episode_v1_1(
        (candidate(1, higher), candidate(2, lower, sources=8))
    )
    by_id = {item.event_id: item for item in result.evaluations}
    assert by_id[1].story_value > by_id[2].story_value
    assert result.recommendations[0].event_id == 1


@pytest.mark.parametrize(
    ("text", "reason"),
    (
        ("Loto: numerele extrase si premiul jackpot", "routine_loto"),
        ("Fotbal: rezultat meci si clasament in liga", "routine_sport"),
        (
            "Vedeta a postat fotografii si imagini adorabile",
            "generic_celebrity_promotion",
        ),
        ("Horoscopul zilei cu informatii generale", "insufficient_editorial_evidence"),
    ),
)
def test_hard_and_semantic_exclusions_ignore_high_source_count(text, reason) -> None:
    item = evidence(text, sources=10)
    assert item.eligible is False
    assert item.exclusion_reason == reason


def test_inflected_loto_result_is_still_routine_and_ineligible() -> None:
    item = evidence(
        "Rezultatele loto de azi. Numerele castigatoare de la noile trageri",
        sources=8,
    )
    assert item.exclusion_reason == "routine_loto"


@pytest.mark.parametrize(
    "text",
    (
        "Dronele au incalcat spatiul aerian si pun frontiera in pericol",
        "Regulamentul reduce varsta raspunderii penale",
        "Russian plot to kill a citizen was thwarted in a NATO country",
    ),
)
def test_inflected_romanian_and_equivalent_english_consequence(text) -> None:
    item = evidence(text)
    assert item.consequence > 0
    assert item.eligible is True


def test_sport_with_independent_public_consequence_remains_eligible() -> None:
    item = evidence(
        "Frauda cu bani publici in liga de fotbal este ancheta penala",
        sources=4,
    )
    assert item.eligible is True
    assert item.exclusion_reason is None


def test_continuity_is_explicit_bounded_and_never_inferred() -> None:
    story = candidate(2, "Noi detalii despre sabotajul caii ferate")
    absent = recommend_episode_v1_1((story,)).evaluations[0]
    duplicate = recommend_episode_v1_1(
        (story,),
        continuity_context=(ContinuityContextV1_1(1, 2, "sabotaj feroviar", False),),
    ).evaluations[0]
    update = recommend_episode_v1_1(
        (story,),
        continuity_context=(ContinuityContextV1_1(1, 2, "sabotaj feroviar", True),),
    ).evaluations[0]

    assert absent.continuity == duplicate.continuity == 0
    assert update.continuity == 2
    assert update.continuity_identity == "sabotaj feroviar"


def test_lexical_overlap_does_not_create_continuity() -> None:
    items = (
        candidate(2, "Atac asupra unei retele de apa"),
        candidate(3, "Atac asupra unui film in presa"),
    )
    result = recommend_episode_v1_1(
        items,
        continuity_context=(ContinuityContextV1_1(1, 2, "retea de apa", True),),
    )
    by_id = {item.event_id: item for item in result.evaluations}
    assert by_id[2].continuity == 2
    assert by_id[3].continuity == 0


def test_caps_are_maximum_only_after_global_rank() -> None:
    categories = (
        *(["Politica"] * 4),
        *(["Social"] * 5),
        *(["CanCan"] * 3),
        *(["Diverse"] * 5),
        *(["Externe"] * 4),
    )
    items = tuple(
        candidate(
            index,
            "Frauda de milioane de lei afecteaza consumatorii",
            category=category,
            sources=30 - index,
        )
        for index, category in enumerate(categories, 1)
    )
    result = recommend_episode_v1_1(items)
    counts = Counter(item.category for item in result.recommendations)
    assert len(result.recommendations) == 10
    assert counts <= Counter(
        {"Politica": 2, "Social": 3, "CanCan": 1, "Diverse": 3, "Externe": 2}
    )


def test_caps_do_not_reserve_categories_or_fill_to_ten() -> None:
    items = tuple(
        candidate(index, "Frauda afecteaza consumatorii", category="Politica")
        for index in range(1, 5)
    )
    result = recommend_episode_v1_1(items)
    assert len(result.recommendations) == 2
    assert result.available_slots == 8


def test_quality_floor_is_metadata_only_and_disabled() -> None:
    item = evidence("O frauda de pret afecteaza consumatorii")
    assert item.quality_tier_metadata == "uncalibrated"
    assert item.quality_floor_applied is False
    assert item.disposition == "recommended"


def test_explanations_derive_from_families_and_are_ascii() -> None:
    item = evidence("Un elev a murit si scolile cer cursuri de prim ajutor", sources=4)
    assert "miza umana" in item.explanation
    assert "4 surse independente" in item.explanation
    assert "elev" not in item.explanation
    assert item.explanation.isascii()


def test_determinism_is_independent_of_input_and_context_order() -> None:
    items = (
        candidate(1, "Frauda afecteaza consumatorii", sources=3),
        candidate(2, "Un elev a murit si scolile cer prim ajutor", category="Social"),
        candidate(3, "Un cerb beat a blocat drumul", category="Externe"),
    )
    context = (
        ContinuityContextV1_1(20, 2, "prim ajutor", True),
        ContinuityContextV1_1(30, 3, "animal", False),
    )
    forward = recommend_episode_v1_1(items, continuity_context=context)
    reverse = recommend_episode_v1_1(
        tuple(reversed(items)), continuity_context=tuple(reversed(context))
    )
    assert (
        forward == reverse == recommend_episode_v1_1(items, continuity_context=context)
    )


@pytest.mark.parametrize(
    ("text", "family"),
    (
        ("Taxiul a oprit langa o institutie", None),
        ("Publicul a vizitat un muzeu", None),
        ("Scandal viral despre o persoana populara", None),
        ("Meci in Mongolia despre un taxi", None),
        ("Atac cibernetic asupra retelei de apa", "consequence"),
    ),
)
def test_lexical_collision_boundaries(text, family) -> None:
    item = evidence(text)
    active = {
        name
        for name in (
            "consequence",
            "contradiction",
            "human_value",
            "comic_visual",
            "cultural_discourse",
        )
        if getattr(item, name)
    }
    assert active == (set() if family is None else {family})


CALIBRATION_STORIES = (
    (29, "Drona pune in pericol populatia; alertele publice se schimba"),
    (29, "Legea permite armatei interventie militara si afecteaza drepturi"),
    (29, "Specialist nuclear expulzat pentru risc de securitate nationala"),
    (29, "Taxa rutiera afecteaza consumatorii in functie de norma"),
    (29, "Facturile la energie intarzie si afecteaza consumatorii"),
    (29, "Procuror acuzat de mita si coruptie"),
    (29, "Programul scolii alege mango in loc sa rezolve nevoia de baza"),
    (29, "Promotiile pentru consumatori isi schimba regulile si preturile"),
    (29, "Romania obtine locul trei intr-o competitie culturala cu reactii online"),
    (29, "Un zvon fals provoaca panica online pe o croaziera"),
    (30, "Drona a fost lovit un apartament si a pus oameni in pericol"),
    (30, "Ministrul foloseste telefonul in timpul discursului despre telefoane"),
    (30, "Un elev a murit; scolile cer cursuri de prim ajutor"),
    (30, "Concediul medical intra in vigoare pentru bolnavi"),
    (30, "Medicul foloseste droguri la serviciu si pune pacientul in pericol"),
    (30, "Centru national de inteligenta artificiala cu impact public"),
    (30, "Primaria plateste mii de euro pentru un cotet"),
    (30, "Femeie a ascuns narghilea intr-un cozonac"),
    (30, "Descoperire medicala explica dependenta si ajuta preventia"),
    (30, "Muzeul a confundat un mamut cu o balena"),
    (31, "Drona maritima pune in pericol portul si securitatea nationala"),
    (31, "Numirea de prim-ministru schimba administratia publica"),
    (31, "Politician vorbeste la un forum rusesc in timp ce pretinde reprezentare"),
    (31, "Un pacient diabetic este agresat si privat de drepturi"),
    (31, "Frauda auto produce pierderi de milioane de lei"),
    (31, "Platforma misterioasa este o situatie neobisnuita pe mare"),
    (31, "Un cerb beat blocheaza drumul"),
    (31, "Consumul de alcool afecteaza sanatatea publica"),
    (32, "Politistul a amanetat laptopul pentru jocuri de noroc"),
    (32, "Hotii au furat sine de cale ferata si afecteaza infrastructura"),
    (32, "Cladirile cu risc sunt verificate doar vizual"),
    (32, "Bere pe stadion devine subiect de dezbatere culturala"),
    (32, "Sabotajul caii ferate pune in pericol calatorii"),
    (32, "Aeroportul este redenumit desi costa bani publici"),
    (32, "Atacul asupra combustibilului are efect de securitate nationala"),
    (32, "Varstnic abuzat intr-un centru si lipsit de ingrijire"),
)


@pytest.mark.parametrize(("episode", "text"), CALIBRATION_STORIES)
def test_calibration_selected_story_has_positive_explainable_family(
    episode, text
) -> None:
    del episode
    item = evidence(text)
    assert item.story_value > 0
    assert item.exclusion_reason is None
    assert item.primary_families


HOLDOUT_STORIES = (
    "Zvon fals pe TikTok provoaca panica online si ambulanta a fost atacata",
    "Teorie falsa despre limba provoaca dezbatere online",
    "Festival controversat provoaca o dezbatere culturala",
    "Acuzatie de spionaj cu efect de securitate nationala",
    "Atac cibernetic pune in pericol reteaua de apa",
    "Dirty Soda devine un trend social",
    "Obiecte ascutite pe autostrada pun soferii in pericol",
    "Filmul controversat provoaca razboi cultural online",
)


@pytest.mark.parametrize("text", HOLDOUT_STORIES)
def test_frozen_holdout_has_positive_generalized_family_coverage(text) -> None:
    item = evidence(text)
    assert item.story_value > 0
    assert item.eligible is True
