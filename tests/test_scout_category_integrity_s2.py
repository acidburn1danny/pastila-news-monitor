from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from pastila_scout.active_project_v1 import (
    NORMAL_SCOUT_RESULT_LIMIT,
    ActiveProjectStoreV1,
)
from pastila_scout.category_integrity import (
    CATEGORY_ORDER,
    is_clearly_english_title,
    normalize_category,
)
from pastila_scout.core.event_canonicalization import (
    canonicalize_event,
    derive_categories,
)
from pastila_scout.database import initialize_database
from pastila_scout.models import ArticleProvenance, ExistingEventMetadata


@pytest.mark.parametrize(
    "title",
    (
        "Trump announces new tariffs after talks with allies",
        "Lance Bass reveals why he kept the secret for years",
        "How this family found hope after the devastating storm",
        "Biden says new plan will help 10 million families",
        "Instagram introduces a redesigned wordmark",
        "Who really needs a cocktail robot?",
        "Taylor Swift Debuts Chic Haircut After Travis Kelce Wedding",
        "Romanian prime minister says Călin Georgescu will face inquiry",
        "Trump's plan isn't working as voters turn against him",
        'APPLE WILL OPEN A NEW FACTORY AFTER TALKS WITH "EU OFFICIALS"',
        'Trump says "new plan will help voters after election',
        "Rivian's 2027 changes include its No. 1 most-requested feature",
        "Terabytes of credentials leaked in massive supply-chain attack",
        "US boosts drone surveillance as flesh-eating screwworms spread in Texas",
        "Researchers found a way to hijack devices through Zoom screen sharing",
        "DEF CON crowd suspected in fake-hotspot attack on Delta flight",
        "Trump wants Big Pharma to split MMR vaccine; Big Pharma thinks it's idiotic",
        "Ukrainian drones wipe out entire US tank brigade in live war game",
        "Pet owners say smart pet feeder outage led to furry ones going unfed",
        'Kourtney Kardashian, Travis Barker Detail Rocky\'s "Terrifying" Surgery',
        "Netflix cancels popular series after three seasons",
        "Netflix cancels beloved show",
        "Pizza, pasta, potatoes, protein - how Italian children became so overweight",
        "Trump orders Smithsonian to post warnings about inaccurate US history",
        "Nigeria's president approves largest military expansion in recent times",
        "Romania blames Russia as military shoots down third drone",
        "Romanian airspace violated by drones twice in 2 days",
        "Trump orders content warnings installed outside Smithsonian museum",
        "They Gave MAGA a Safe Haven. Now They're in Retreat.",
    ),
)
def test_clearly_english_news_titles_are_detected(title: str) -> None:
    assert is_clearly_english_title(title)


@pytest.mark.parametrize(
    "title",
    (
        'Filmul "The Odyssey" al lui Christopher Nolan ajunge in cinematografe',
        "Donald Trump vine la Bucuresti pentru summitul NATO",
        "Netflix lanseaza un nou serial produs in Romania",
        "Netflix lanseaza un show nou in Romania",
        "Donald Trump spune ca noul plan va fi prezentat maine",
        'Artistul a cantat piesa "Love Me Again" la festival',
        "CEO-ul IBM anunta investitii noi in Romania",
        "Breaking news",
        "The Odyssey",
        "Șoc total la Hollywood: Star is dead",
        "OpenAI are un new model pentru Europa",
        'Filmul "The Best New Story Of Our Time" ajunge la cinema',
        "TRUMP VINE LA BUCURESTI PENTRU SUMMITUL NATO",
        "AI GPT-5.6 MSFT Q3",
    ),
)
def test_romanian_or_ambiguous_titles_are_not_forced_to_externe(title: str) -> None:
    assert not is_clearly_english_title(title)


def _article(
    article_id: int, title: str, categories: tuple[str, ...]
) -> ArticleProvenance:
    return ArticleProvenance(
        id=article_id,
        event_id=1,
        source_id=f"source-{article_id}",
        source_name=f"Source {article_id}",
        url=f"https://example.test/{article_id}",
        normalized_url=f"https://example.test/{article_id}",
        title=title,
        normalized_title=title.casefold(),
        summary="Summary",
        published_at="2026-08-14T10:00:00+00:00",
        discovered_at="2026-08-14T10:01:00+00:00",
        source_categories=categories,
    )


def test_english_domestic_article_is_authoritatively_externe() -> None:
    article = _article(
        1,
        "Lance Bass reveals why he kept the secret for years",
        ("CanCan", "Social"),
    )

    assert derive_categories((article,)) == ("Externe",)


@pytest.mark.parametrize("fallback", ("CanCan", "Diverse", "Economie"))
def test_english_article_ignores_domestic_fallback(fallback: str) -> None:
    article = _article(
        1,
        "Researchers found a way to hijack devices through screen sharing",
        (fallback,),
    )

    assert derive_categories((article,)) == ("Externe",)


@pytest.mark.parametrize(
    "title",
    (
        "Guvernul Romaniei anunta masuri noi pentru elevi",
        "Breaking news",
        "Recipe: Amish Peanut Butter Pie",
    ),
)
def test_externe_source_authority_is_independent_of_title_language(title: str) -> None:
    article = _article(1, title, ("Externe", "Diverse"))

    assert derive_categories((article,)) == ("Externe",)


@pytest.mark.parametrize(
    ("source_id", "categories", "title", "expected"),
    (
        (
            "cancan",
            ("CanCan", "Social", "Diverse"),
            "O vedeta din Romania vorbeste despre familie",
            "CanCan",
        ),
        (
            "cancan",
            ("CanCan", "Social", "Diverse"),
            "Celebrity reveals new relationship after wedding",
            "Externe",
        ),
    ),
)
def test_cancan_source_prior_preserves_supported_semantics(
    source_id: str,
    categories: tuple[str, ...],
    title: str,
    expected: str,
) -> None:
    article = _article(1, title, categories).model_copy(update={"source_id": source_id})

    assert derive_categories((article,)) == (expected,)


def test_final_five_category_contract_and_legacy_mapping() -> None:
    assert CATEGORY_ORDER == ("Politica", "Social", "CanCan", "Diverse", "Externe")
    assert normalize_category("Economie") == "Diverse"
    assert normalize_category("Conspiratii") == "CanCan"
    assert normalize_category("Toate") is None
    assert normalize_category("all") is None


def test_click_prior_alone_is_insufficient_but_english_still_wins() -> None:
    romanian = _article(
        1, "Subiect local fara semnal semantic", ("CanCan", "Social", "Diverse")
    ).model_copy(update={"source_id": "click"})
    english = romanian.model_copy(
        update={"title": "Celebrity reveals new relationship after wedding"}
    )

    assert derive_categories((romanian,)) == ("Diverse",)
    assert derive_categories((english,)) == ("Externe",)


@pytest.mark.parametrize(
    ("source_id", "title", "summary", "expected"),
    (
        (
            "cancan",
            "Accident mortal pe un drum national",
            "Politistii cerceteaza circumstantele tragediei.",
            "Social",
        ),
        (
            "click",
            "Rusia ataca din nou Ucraina cu drone",
            "Atacul a vizat infrastructura civila.",
            "Externe",
        ),
        (
            "cancan",
            "FCSB castiga meciul si urca in clasament",
            "Echipa s-a calificat in finala campionatului.",
            "Diverse",
        ),
        (
            "click",
            "Guvernul aproba reforma fiscala",
            "Ministrul a prezentat noua politica publica.",
            "Politica",
        ),
        (
            "cancan",
            "Bianca reactioneaza dupa veste",
            "Vedeta a vorbit despre relatia si nunta sa.",
            "CanCan",
        ),
        (
            "click",
            "Sfaturi simple pentru o vacanta reusita",
            "Ghidul prezinta destinatii si costuri orientative.",
            "Diverse",
        ),
    ),
)
def test_s23_cancan_click_are_bounded_supporting_priors(
    source_id: str, title: str, summary: str, expected: str
) -> None:
    article = _article(1, title, ("CanCan",)).model_copy(
        update={"source_id": source_id, "summary": summary}
    )

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Artista anunta o noua performanta muzicala", "CanCan"),
        ("Filmari Asia Express pe Drumul Matasii", "CanCan"),
        ("Insula Iubirii: concurentii formeaza un cuplu", "CanCan"),
        ("Tenorul publica imagini alaturi de familie", "CanCan"),
        ("Filme si seriale noi pe platformele de streaming", "CanCan"),
        ("Celebrele incaltari produse intr-un oras vechi", "Diverse"),
    ),
)
def test_s23_entertainment_context_requires_real_semantic_support(
    title: str, expected: str
) -> None:
    article = _article(1, title, ("Politica", "Social", "CanCan", "Diverse"))

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Sfaturi despre alimentatia copiilor oferite de un medic", "Diverse"),
        ("Un sofer explica de ce prefera masinile electrice", "Diverse"),
        ("Copil internat de urgenta la Spitalul Marie Curie", "Social"),
        ("Accident feroviar langa Brighton", "Externe"),
        ("Explozie intr-o rafinarie din portul Rotterdam", "Externe"),
        ("Guvernul Suediei adopta o lege noua", "Externe"),
        ("Rebelii Houthi din Yemen ataca o rafinarie", "Externe"),
        ("Hackeri chinezi ataca infrastructura din Taiwan", "Externe"),
        ("Urs impuscat dupa ce a intrat intr-un hotel din Brasov", "Social"),
        ("OCPI prelungeste programul dupa blocarea serviciului", "Social"),
        ("Centrala nucleara de la Cernavoda a fost oprita", "Politica"),
    ),
)
def test_s23_public_interest_and_foreign_context_require_strong_evidence(
    title: str, expected: str
) -> None:
    article = _article(1, title, ("Politica", "Social", "CanCan", "Diverse"))

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("source_id", "source_is_externe", "title", "summary", "expected"),
    (
        (
            "click",
            False,
            "Guvernul aproba bugetul si noua politica fiscala",
            "O vedeta a comentat decizia intr-un interviu.",
            "Politica",
        ),
        (
            "cancan",
            False,
            "Sportiv retinut dupa un accident mortal",
            "Atletul este cercetat de politie.",
            "Social",
        ),
        (
            "click",
            False,
            "Compania lanseaza un telefon nou",
            "Un medic si un copil apar in reclama produsului.",
            "Diverse",
        ),
        (
            "domestic",
            False,
            "MApN raporteaza o drona in spatiul aerian al Romaniei",
            "Incidentul este analizat impreuna cu aliatii straini.",
            "Politica",
        ),
        (
            "domestic",
            False,
            "Primarul povesteste despre dieta si vacanta sa",
            "Interviul nu priveste activitatea institutiei.",
            "Diverse",
        ),
        (
            "cancan",
            True,
            "Vedeta confirma nunta si noua relatie",
            "Material de divertisment.",
            "Externe",
        ),
        (
            "domestic",
            False,
            "Government announces a new policy after the election",
            "Guvernul Romaniei a comentat stirea.",
            "Externe",
        ),
    ),
)
def test_final_review_authority_context_and_summary_adversaries(
    source_id: str,
    source_is_externe: bool,
    title: str,
    summary: str,
    expected: str,
) -> None:
    categories = (
        ("Externe",)
        if source_is_externe
        else ("CanCan",)
        if source_id in {"cancan", "click"}
        else ("Politica", "Social", "CanCan", "Diverse")
    )
    article = _article(1, title, categories).model_copy(
        update={"source_id": source_id, "summary": summary}
    )

    assert derive_categories((article,)) == (expected,)


def test_feed_tag_does_not_impersonate_externe_source_authority() -> None:
    article = _article(
        1,
        "Guvernul Romaniei anunta masuri noi pentru elevi",
        ("Social",),
    ).model_copy(update={"raw_payload": '{"category": "Externe"}'})

    assert derive_categories((article,)) == ("Social",)


def test_romanian_and_unknown_articles_resolve_one_category() -> None:
    romanian = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Social", "Politica"),
    )
    unknown = _article(2, "Titlu local ambiguu", ("CategorieViitoare",))

    assert derive_categories((romanian,)) == ("Politica",)
    assert derive_categories((unknown,)) == ()


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Guvernul aproba o decizie propusa de ministru", "Politica"),
        ("Candidatul partidului intra in alegeri", "Politica"),
        ("Report urias la Loto 6 din 49", "Social"),
        ("Angajat concediat primeste despagubiri", "Social"),
        ("Festivalul aduce un flux mare de vizitatori", "Social"),
        ("Elev ranit intr-un accident langa scoala", "Social"),
        ("Compania raporteaza profit dupa o investitie", "Diverse"),
        ("Vedeta confirma o noua relatie", "CanCan"),
        ("Dezinformare si conspiratie distribuite online", "CanCan"),
        ("Material local incategorizabil", "Diverse"),
    ),
)
def test_broad_domestic_scope_uses_title_semantics(title: str, expected: str) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "Economie", "Conspiratii", "CanCan", "Diverse"),
    )

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        (
            "18 drone au intrat in spatiul aerian al Romaniei. Bilantul MApN",
            "Politica",
        ),
        ("Ambasadorul Rusiei, convocat la Ministerul Afacerilor Externe", "Politica"),
        ("Ministrul roman informeaza aliatii dupa incident", "Politica"),
        ("Liderii PSD, PNL, USR si AUR negociaza noua coalitie", "Politica"),
        ("Oana Gheorghiu analizeaza companiile de stat", "Politica"),
        ("Nicusor Dan anunta un protest diplomatic", "Politica"),
        ("Eurodeputatul cere Comisiei Europene un raspuns pentru Romania", "Politica"),
        ("Instantele romanesti aplica decizia CJUE", "Politica"),
        ("Un nou mesaj RO-Alert in nordul judetului Tulcea", "Social"),
        ("Record de inscrieri la universitate pentru examenul de admitere", "Social"),
        ("ANM anunta Cod galben de vijelii", "Social"),
        ("Salvamont intervine pentru salvarea a doi turisti", "Social"),
        ("Pompierii cauta doi marinari disparuti pe mare", "Social"),
        ("Politistii intervin dupa un accident grav", "Social"),
        ("Cum se calculeaza pensia si contributia CASS", "Social"),
        ("Furnizorul de electricitate a inselat consumatorii", "Social"),
        ("Pacientii primesc un tratament nou in spital", "Social"),
        ("CFR repara linia de cale ferata dupa accident", "Social"),
        ("Actrita Ioana Blaj revine dupa o pauza", "CanCan"),
        ("Prezentatoarea TV Adina Halas povesteste despre vacanta", "CanCan"),
        ("Cerere in casatorie inedita in centrul orasului", "CanCan"),
        ("Vedeta confirma relatia si vacanta de lux", "CanCan"),
        ("Rusia a atacat din nou Ucraina cu drone si rachete", "Externe"),
        ("Evacuari din cauza incendiilor din Franta si Spania", "Externe"),
        ("Iranul raspunde dupa atacul ucrainean asupra unei nave", "Externe"),
        ("Noul premier al Marii Britanii il critica pe Trump", "Externe"),
        ("MAE il convoaca pe ambasadorul Rusiei", "Politica"),
        ("MApN raporteaza o drona in spatiul aerian al Romaniei", "Politica"),
        ("Guvernul Romaniei reactioneaza la atacul din Ucraina", "Politica"),
        ("BVB creste dupa rezultatele raportate de companii", "Diverse"),
        ("Horoscop saptamanal pentru toate zodiile", "Diverse"),
        ("Echipa castiga meciul si urca in clasament", "Diverse"),
        ("Compania lanseaza un produs software pentru firme", "Diverse"),
    ),
)
def test_s21_real_semantic_families(title: str, expected: str) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    )

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Ministerul anunta reforma administratiei publice", "Politica"),
        ("Parlamentarii si senatorii voteaza proiectul de lege", "Politica"),
        ("Primaria modifica taxele locale", "Politica"),
        ("Pompierii intervin la incendiul unei case", "Social"),
        ("Pacientii din spitale primesc tratamente noi", "Social"),
        ("Politistii cerceteaza disparitia unui elev", "Social"),
        ("Actrita si cantareata confirma logodna", "CanCan"),
    ),
)
def test_s21_bounded_romanian_morphology(title: str, expected: str) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    )

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    "title",
    (
        "Romania participa la un festival de film",
        "Compania Romania Software raporteaza profit",
        "Actorul depune marturie intr-un proces penal",
        "Ministrul britanic viziteaza Romania pentru un concert",
    ),
)
def test_s21_context_tokens_do_not_create_automatic_categories(title: str) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    )

    assert len(derive_categories((article,))) == 1


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Prima tara care lanseaza un serviciu de taxi aerian", "Diverse"),
        ("Iubitorii de literatura descopera o librarie veche", "Diverse"),
        ("Buget de vacante pentru o iesire la gratar", "Diverse"),
        ("FCSB si CFR Cluj joaca in cupele europene", "Diverse"),
        ("Noul premier al Braziliei anunta alegeri", "Externe"),
        ("Accident grav la Berlin, anchetat de politie", "Externe"),
        ("Grecia inscrie Muntele Olimp in patrimoniul UNESCO", "Externe"),
        ("Jandarmii au ajutat un tanar care a cerut-o de sotie", "CanCan"),
        ("Salvamont Maramures salveaza doi ucraineni epuizati", "Social"),
        ("Mesajul sefului Statului Major despre drona doborata", "Politica"),
        ("Industria militara schimba viitorul apararii Romaniei", "Politica"),
        ("Copii asteapta un pat la spitalul Marie Curie", "Social"),
        ("Patru cutremure in Romania in mai putin de 24 de ore", "Social"),
        ("Medalie de aur pentru Romania la campionatul mondial", "Diverse"),
        ("Oamenii pot folosi noul serviciu de transport", "Diverse"),
        ("Partidul AUR anunta un candidat la alegeri", "Politica"),
        ("Copiii unei familii au fugit din Coreea de Nord", "Externe"),
        ("Antrenorul Universitatii Craiova va interveni dupa meci", "Diverse"),
        ("Deficitul bugetar al Romaniei a scazut in primul semestru", "Politica"),
        ("Politistii au retinut suspectii dupa un jaf", "Social"),
        ("Peste 300000 de varstnici sunt izolati in orase", "Social"),
        ("Imagini de la nunta artistei", "CanCan"),
        ("Incendiile afecteaza sudul Europei", "Externe"),
    ),
)
def test_s21_collision_and_foreign_precision_regressions(
    title: str, expected: str
) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    )

    assert derive_categories((article,)) == (expected,)


def test_s21_summary_is_bounded_secondary_evidence() -> None:
    political = _article(
        1,
        "Oana Gheorghiu prezinta concluziile analizei",
        ("Politica", "Social", "CanCan", "Diverse"),
    ).model_copy(
        update={
            "summary": "Vicepremierul explica reforma companiilor de stat si modificarile legislative."
        }
    )
    generic = _article(
        2,
        "Un produs nou ajunge pe piata",
        ("Politica", "Social", "CanCan", "Diverse"),
    ).model_copy(update={"summary": "Compania prezinta produsul intr-un comunicat."})

    assert derive_categories((political,)) == ("Politica",)
    assert derive_categories((generic,)) == ("Diverse",)


@pytest.mark.parametrize(
    ("title", "summary", "expected"),
    (
        (
            "Andrei Popescu reactioneaza dupa sedinta",
            "Vicepremierul Romaniei a explicat reforma pregatita de Guvern.",
            "Politica",
        ),
        (
            "Nadia Kovar face un anunt important",
            "Presedintele statului Nembala a anuntat noua politica a guvernului.",
            "Externe",
        ),
        (
            "Ioana Popa revine cu o declaratie",
            "Actrita a vorbit intr-un interviu despre noul film.",
            "CanCan",
        ),
        (
            "Mihai Ionescu se pregateste pentru ziua decisiva",
            "Sportivul roman va concura in finala campionatului.",
            "Diverse",
        ),
        (
            "Autoritatile au intervenit in cursul noptii",
            "Salvamont Maramures a salvat doi cetateni ucraineni.",
            "Social",
        ),
        (
            "Un anunt venit de la Orania",
            "Guvernul de la Orania a aprobat o noua politica externa.",
            "Externe",
        ),
        (
            "Ion Popescu este mentionat in comunicat",
            "Ministerul de externe de la Teheran a anuntat decizia.",
            "Externe",
        ),
        (
            "Radu Matei prezinta concluziile",
            "Directorul companiei a explicat rezultatele trimestriale.",
            "Diverse",
        ),
    ),
)
def test_s22_contextual_role_and_subject_resolution(
    title: str, summary: str, expected: str
) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    ).model_copy(update={"summary": summary})

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "summary", "expected"),
    (
        (
            "Actor cunoscut, retinut dupa o agresiune",
            "Politistii cerceteaza cazul penal.",
            "Social",
        ),
        (
            "Ministrul povesteste despre vacanta si dieta sa",
            "Interviul descrie exclusiv obiceiurile sale personale.",
            "Diverse",
        ),
        (
            "Alex Pop castiga finala",
            "Atletul a obtinut primul loc in campionat.",
            "Diverse",
        ),
        (
            "MApN raporteaza un incident la Teheran",
            "Institutia romana monitorizeaza situatia.",
            "Politica",
        ),
        (
            "Ministerul de Externe de la Teheran anunta masuri",
            "Un cetatean roman este mentionat in comunicat.",
            "Externe",
        ),
    ),
)
def test_s22_contextual_collision_and_precedence(
    title: str, summary: str, expected: str
) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    ).model_copy(update={"summary": summary})

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    ("title", "summary", "expected"),
    (
        (
            "Romania va informa aliatii dupa dronele doborate",
            "Ministrul Afacerilor Externe transmite concluziile anchetei privind spatiul aerian national.",
            "Politica",
        ),
        (
            "Seful Armatei Romane avertizeaza asupra incidentelor din Marea Neagra",
            "Seful Statului Major al Apararii explica riscurile pentru Romania.",
            "Politica",
        ),
        (
            "Doua drone au fost doborate intr-un timp record",
            "Ministrul spune ca Armata Romaniei face maximul posibil.",
            "Politica",
        ),
        (
            "O drona a fost doborata pe teritoriul Romaniei",
            "MApN a anuntat masura luata de avioanele F-16 romanesti.",
            "Politica",
        ),
        (
            "Patru fosti judecatori ai instantei supreme au fost numiti notari",
            "Ministerul Justitiei anunta decizia dupa votul Camerei Deputatilor.",
            "Politica",
        ),
        (
            "Acciza la motorina va fi redusa temporar",
            "Ministerul Finantelor a anuntat si aprobat masura fiscala.",
            "Politica",
        ),
        (
            "Autoritatile din sanatate anunta cazuri de virus cu nume strain",
            "Institutul National de Sanatate Publica a raportat cazurile din Romania.",
            "Social",
        ),
        (
            "Salvamontistii romani cauta un tanar britanic disparut in Carpati",
            "Echipele reiau cautarea in muntii din Romania.",
            "Social",
        ),
        (
            "Turistii au fost evacuati de pe plaja din Costinesti din cauza unei drone",
            "Autoritatile din Romania au evacuat plaja si au intervenit la fata locului.",
            "Social",
        ),
        (
            "Panica la Costinesti. Turistii spun: Plecam in Bulgaria",
            "Autoritatile au evacuat plaja, iar Garda de Coasta a intervenit.",
            "Social",
        ),
        (
            "Turisti evacuati de pe o plaja din Bulgaria din cauza unei drone",
            "Autoritatile bulgare si Garda de Coasta din Varna au intervenit.",
            "Externe",
        ),
        (
            "Garda de Coasta recupereaza o drona pe litoralul Romaniei",
            "Autoritatile au intervenit si au evacuat turistii de pe plaja.",
            "Social",
        ),
        (
            "Garda de Coasta bulgara intervine la Varna",
            "Autoritatile bulgare au evacuat turistii de pe plaja.",
            "Externe",
        ),
        (
            "Ministerul bulgar anunta evacuari in apropiere de Sofia",
            "Guvernul Bulgariei coordoneaza operatiunea.",
            "Externe",
        ),
        (
            "Un oficial din Ministerul Energiei infirma informatii despre Ucraina",
            "Secretarul de stat a explicat masura luata de Romania.",
            "Politica",
        ),
        (
            "Ministerul de Externe de la Teheran anunta masuri pentru Romania",
            "Guvernul iranian a aprobat decizia la Teheran.",
            "Externe",
        ),
        (
            "Fregatele Rusiei au fost avariate de un atac ucrainean",
            "Statul Major de la Kiev a confirmat loviturile.",
            "Externe",
        ),
        (
            "Romania analizeaza declaratia Ministerului Apararii din Ucraina",
            "Ministerul de la Kiev a anuntat masura.",
            "Externe",
        ),
        (
            "Pompierii romani au ajuns in Franta pentru incendiile de vegetatie",
            "Presedintele francez le-a multumit salvatorilor trimisi de Romania.",
            "Externe",
        ),
        (
            "O femeie explica operatiile estetice facute recent",
            (
                "Medicul estetician a oferit detalii despre operatii. "
                "Articolul apare prima data in Romania TV."
            ),
            "Diverse",
        ),
        (
            "Ministrul povesteste despre dieta si vacanta sa",
            "Interviul nu priveste activitatea institutiei.",
            "Diverse",
        ),
    ),
)
def test_s24_romanian_institution_and_public_system_precedence(
    title: str, summary: str, expected: str
) -> None:
    article = _article(
        1,
        title,
        ("Politica", "Social", "CanCan", "Diverse"),
    ).model_copy(update={"summary": summary})

    assert derive_categories((article,)) == (expected,)


@pytest.mark.parametrize(
    "titles",
    (
        (
            "Loto 6 din 49 are un report de milioane de euro",
            "Loteria anunta reportul pentru extragerea de duminica",
            "Report mare la Loto",
        ),
        (
            "Angajat concediat pentru trei cafele primeste despagubiri",
            "Compania plateste despagubiri unui angajat concediat",
        ),
        (
            "Festivalul UNTOLD aduce un flux mare de vizitatori",
            "Flux de vizitatori in oras in saptamana festivalului",
        ),
    ),
)
def test_real_defect_families_resolve_social(titles: tuple[str, ...]) -> None:
    broad = ("Politica", "Social", "Economie", "CanCan", "Diverse")
    articles = tuple(
        _article(article_id, title, broad)
        for article_id, title in enumerate(titles, start=1)
    )

    assert derive_categories(articles) == ("Social",)


def test_domestic_event_tie_does_not_use_presentation_order() -> None:
    political = _article(1, "Guvernul aproba o decizie", ("Politica", "Social"))
    social = _article(
        2, "Angajat concediat primeste despagubiri", ("Politica", "Social")
    )

    assert derive_categories((political, social)) == ("Diverse",)
    assert derive_categories((social, political)) == ("Diverse",)


def test_externe_half_threshold_and_domestic_majority_are_order_independent() -> None:
    domestic = (
        _article(1, "Guvernul aproba o decizie", ("Politica",)),
        _article(2, "Parlamentul voteaza decizia", ("Politica",)),
    )
    external = (
        _article(3, "Government approves a major decision after talks", ("Externe",)),
        _article(4, "Parliament votes on the decision after debate", ("Externe",)),
    )

    assert derive_categories((*domestic, *external)) == ("Externe",)
    assert derive_categories((external[1], domestic[0], external[0], domestic[1])) == (
        "Externe",
    )
    assert derive_categories((*domestic, external[0])) == ("Politica",)
    assert derive_categories((external[0], *reversed(domestic))) == ("Politica",)


def test_specialized_source_tie_yields_to_unanimous_event_semantics() -> None:
    click = _article(
        1,
        "Angajat concediat primeste despagubiri",
        ("CanCan", "Social", "Diverse"),
    ).model_copy(update={"source_id": "click"})
    generalist = _article(
        2,
        "Compania plateste despagubiri angajatului concediat",
        ("Politica", "Social", "Diverse"),
    )

    assert derive_categories((click, generalist)) == ("Social",)
    assert derive_categories((generalist, click)) == ("Social",)


def test_mixed_domestic_event_remains_domestic_independent_of_arrival_order() -> None:
    romanian = _article(
        1,
        "Guvernul Romaniei anunta un nou program pentru elevi",
        ("Politica", "Social"),
    )
    english = _article(
        2,
        "Government announces new program for Romanian students",
        ("Externe",),
    )

    assert derive_categories((romanian, english)) == ("Externe",)
    assert derive_categories((english, romanian)) == ("Externe",)


def test_cross_source_category_vote_tracks_corroboration_not_arrival_order() -> None:
    romanian = tuple(
        _article(
            article_id,
            f"Guvernul anunta masuri noi pentru orasul {article_id}",
            ("Politica",),
        )
        for article_id in (1, 2, 3)
    )
    english = tuple(
        _article(
            article_id,
            f"Government announces new measures for city {article_id}",
            ("CanCan",),
        )
        for article_id in (4, 5, 6)
    )

    assert derive_categories((*romanian, english[0])) == ("Politica",)
    assert derive_categories((english[0], *reversed(romanian))) == ("Politica",)
    assert derive_categories((romanian[0], *english)) == ("Externe",)
    assert derive_categories((*reversed(english), romanian[0])) == ("Externe",)
    assert derive_categories((romanian[0], english[0])) == ("Externe",)


def test_english_canonical_title_requires_strict_domestic_majority() -> None:
    domestic = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Politica",),
    )
    english = _article(
        2,
        "Government announces comprehensive new measures for Romanian students",
        ("Externe",),
    )
    broad_domestic = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        ("Politica", "Social", "Economie", "Diverse"),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title="Anterior",
        summary="Rezumat",
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    equal = canonicalize_event(existing, (broad_domestic, english))
    domestic_majority = canonicalize_event(
        existing,
        (
            domestic,
            english,
            _article(
                3,
                "Parlamentul discuta masurile pentru elevii din Romania",
                ("Politica",),
            ),
        ),
    )

    assert equal.canonical_article_id == 2
    assert equal.categories == ("Externe",)
    assert domestic_majority.categories == ("Politica",)


def test_legacy_multi_category_state_does_not_override_diverse_fallback() -> None:
    article = _article(1, "Titlu local ambiguu", ())
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=("Social", "Politica", "Diverse"),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    projected = canonicalize_event(existing, (article,))

    assert projected.categories == ("Diverse",)


@pytest.mark.parametrize(
    ("persisted", "current", "expected"),
    (
        ("Politica", "Social", "Social"),
        ("Social", "Economie", "Diverse"),
        ("Externe", "Social", "Social"),
    ),
)
def test_current_unanimous_evidence_overrides_legacy_category(
    persisted: str, current: str, expected: str
) -> None:
    article = _article(
        1,
        "Guvernul anunta masuri noi pentru elevii din Romania",
        (current,),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=(persisted,),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    assert canonicalize_event(existing, (article,)).categories == (expected,)


def test_english_evidence_overrides_legacy_cancan_category() -> None:
    article = _article(
        1,
        "Trump announces new tariffs after talks with allies",
        ("CanCan",),
    )
    existing = ExistingEventMetadata(
        id=1,
        canonical_title=article.title,
        summary="Rezumat",
        categories=("CanCan",),
        first_seen_at="2026-08-14T10:00:00+00:00",
        last_seen_at="2026-08-14T11:00:00+00:00",
    )

    assert canonicalize_event(existing, (article,)).categories == ("Externe",)


def _candidate_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        rows = (
            (91, "Titlu duplicat", "Politica", 2, "2026-08-14T09:00:00+00:00"),
            (3, "Social 8", "Social", 8, "2026-08-14T08:00:00+00:00"),
            (8, "Politic 5", "Politica", 5, "2026-08-14T07:00:00+00:00"),
            (2, "Titlu duplicat", "Politica", 8, "2026-08-14T06:00:00+00:00"),
            (7, "Externe 9", "Externe", 9, "2026-08-14T10:00:00+00:00"),
            (6, "Necunoscut", "Viitor", 99, "2026-08-14T11:00:00+00:00"),
            (10, "Necunoscut doi", "Alta", 99, "2026-08-14T11:00:00+00:00"),
            (4, "Politic tie recent", "Politica", 5, "2026-08-14T08:00:00+00:00"),
            (5, "Politic tie same", "Politica", 5, "2026-08-14T08:00:00+00:00"),
        )
        connection.executemany(
            """INSERT INTO events
               (id, canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at)
               VALUES (?, ?, LOWER(?), 'Rezumat', ?, ?, ?, ?, ?, ?, ?)""",
            (
                (
                    event_id,
                    title,
                    title,
                    category,
                    seen,
                    seen,
                    source_count,
                    source_count,
                    seen,
                    seen,
                )
                for event_id, title, category, source_count, seen in rows
            ),
        )


def test_normal_candidates_group_by_category_then_sources_and_stable_ties(
    tmp_path: Path,
) -> None:
    database = tmp_path / "scout.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates()
    repeated = store.list_candidates()

    assert [item.event_id for item in candidates] == [2, 4, 5, 8, 91, 3, 7]
    assert [item.source_count for item in candidates[:5]] == [8, 5, 5, 5, 2]
    assert repeated == candidates

    limited = store.list_candidates(limit=2)
    assert [item.event_id for item in limited] == [2, 4]

    social = store.list_candidates(category="Social")
    externe = store.list_candidates(category="Externe")
    assert [item.event_id for item in social] == [3]
    assert [item.event_id for item in externe] == [7]


def test_competitive_fill_uses_global_rank_and_scarcity_does_not_fabricate(
    tmp_path: Path,
) -> None:
    database = tmp_path / "competitive.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates(limit=6)
    scarce = store.list_candidates()

    assert [item.event_id for item in candidates] == [2, 4, 5, 8, 91, 7]
    assert [item.event_id for item in scarce] == [2, 4, 5, 8, 91, 3, 7]
    assert len(scarce) == len({item.event_id for item in scarce}) == 7


def _episode_pool_database(path: Path, *, politica: int = 60, cancan: int = 8) -> None:
    categories = (
        ("Politica", politica),
        ("Social", 20),
        ("CanCan", cancan),
        ("Diverse", 20),
        ("Externe", 20),
    )
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        rows = []
        event_id = 1
        for category, count in categories:
            for index in range(count):
                source_count = 9 - index % 9
                seen = f"2026-08-{14 - index % 7:02d}T{23 - index % 12:02d}:00:00+00:00"
                rows.append(
                    (
                        event_id,
                        "Titlu duplicat" if index < 2 else f"{category} {index}",
                        category,
                        source_count,
                        seen,
                    )
                )
                event_id += 1
        connection.executemany(
            """INSERT INTO events
               (id, canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at)
               VALUES (?, ?, LOWER(?), 'Rezumat', ?, ?, ?, ?, ?, ?, ?)""",
            (
                (
                    event_id,
                    title,
                    title,
                    category,
                    seen,
                    seen,
                    source_count,
                    source_count,
                    seen,
                    seen,
                )
                for event_id, title, category, source_count, seen in rows
            ),
        )


def test_episode_equivalent_pool_prevents_starvation_and_respects_caps(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pool.db"
    _episode_pool_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates()
    counts = Counter(item.category for item in candidates)

    assert (
        len(candidates)
        == len({item.event_id for item in candidates})
        == NORMAL_SCOUT_RESULT_LIMIT
    )
    assert counts["Politica"] == 10
    assert counts["CanCan"] == 5
    assert counts["Social"] <= 15
    assert counts["Diverse"] <= 15
    assert counts["Externe"] <= 20
    assert all(counts[category] for category in CATEGORY_ORDER)
    assert [item.category for item in candidates] == sorted(
        (item.category for item in candidates), key=CATEGORY_ORDER.index
    )
    for category in CATEGORY_ORDER:
        source_counts = [
            item.source_count for item in candidates if item.category == category
        ]
        assert source_counts == sorted(source_counts, reverse=True)


@pytest.mark.parametrize("limit", (49, 50, 51, 59, 60, 61))
def test_normal_scout_projection_has_deterministic_sixty_event_boundary(
    tmp_path: Path, limit: int
) -> None:
    database = tmp_path / f"pool-{limit}.db"
    _episode_pool_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    projected = store.list_candidates(limit=limit)
    repeated = store.list_candidates(limit=limit)

    assert len(projected) == min(limit, NORMAL_SCOUT_RESULT_LIMIT)
    assert projected == repeated
    assert len({item.event_id for item in projected}) == len(projected)
    assert [item.category for item in projected] == sorted(
        (item.category for item in projected), key=CATEGORY_ORDER.index
    )


def test_sixty_event_extension_preserves_the_established_first_fifty_projection(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pool-preservation.db"
    _episode_pool_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    established = store.list_candidates(limit=50)
    expanded = store.list_candidates(limit=60)
    established_ids = {item.event_id for item in established}

    assert (
        tuple(item for item in expanded if item.event_id in established_ids)
        == established
    )
    assert len(expanded) - len(established) == 10


def test_explicit_category_projection_is_not_limited_by_pool_allocation(
    tmp_path: Path,
) -> None:
    database = tmp_path / "filtered.db"
    _episode_pool_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    expected = {
        "Politica": 60,
        "Social": 20,
        "CanCan": 8,
        "Diverse": 20,
        "Externe": 20,
    }
    for category, count in expected.items():
        candidates = store.list_candidates(category=category)
        assert len(candidates) == count
        assert {item.category for item in candidates} == {category}


@pytest.mark.parametrize("available", (0, 1, 9, 10, 14))
def test_politica_protected_intake_respects_supply_and_cap(
    tmp_path: Path, available: int
) -> None:
    database = tmp_path / f"politica-{available}.db"
    _episode_pool_database(database, politica=available)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates()

    assert Counter(item.category for item in candidates)["Politica"] == min(
        available, 10
    )


@pytest.mark.parametrize("available", (0, 1, 4, 5, 9))
def test_cancan_protected_intake_respects_supply_and_cap(
    tmp_path: Path, available: int
) -> None:
    database = tmp_path / f"cancan-{available}.db"
    _episode_pool_database(database, cancan=available)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates()

    assert Counter(item.category for item in candidates)["CanCan"] == min(available, 5)


def test_targeted_candidate_ids_preserve_relevance_order(tmp_path: Path) -> None:
    database = tmp_path / "scout.db"
    _candidate_database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )

    candidates = store.list_candidates_by_ids(event_ids=(7, 3, 2))

    assert [item.event_id for item in candidates] == [7, 3, 2]
    assert [item.source_count for item in candidates] == [9, 8, 8]
