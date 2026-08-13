"""Realistic conservative clustering regressions for Scout event matching."""

from pastila_scout.event_matcher import match_event, title_similarity


def _matches(left: str, right: str) -> bool:
    return title_similarity(left, right) >= 0.72


def test_real_cross_publication_paraphrases_cluster() -> None:
    positives = (
        (
            (
                "Konstantinos Passaris ramane in inchisoare. Cererea de eliberare "
                "conditionata a fost respinsa"
            ),
            (
                "Fiara din Balcani ramane in inchisoare. Tribunalul Dolj a respins "
                "cererea lui Passaris de eliberare conditionata"
            ),
        ),
        (
            (
                "David Popovici s-a calificat in finala probei de 200 metri liber "
                "la Europene cu cel mai bun timp"
            ),
            "David Popovici, calificat cu cel mai bun timp in finala la 200 m",
        ),
        (
            "Romania ridica avioane dupa patrunderea unei drone in spatiul aerian",
            "RO-Alert in Tulcea dupa detectarea unei drone aproape de granita",
        ),
        (
            (
                "Cel mai mare premiu din istorie la Loto 6/49, castigat cu o "
                "combinatie rar intalnita: sase numere, trei perechi consecutive"
            ),
            (
                "A fost castigat cel mai mare premiu din istoria Loto 6/49. Unde "
                "s-a jucat biletul de 8,50 lei care aduce peste 10 milioane de euro"
            ),
        ),
        (
            "Drona a patruns in spatiul aerian al Romaniei",
            "O drona detectata in spatiul aerian al Romaniei",
        ),
    )
    assert all(_matches(left, right) for left, right in positives)


def test_related_but_distinct_events_remain_separate() -> None:
    negatives = (
        (
            "Romania ridica avioane dupa patrunderea unei drone in spatiul aerian",
            "Atac cu drona asupra unui oras din Ucraina",
        ),
        (
            "Romania ridica avioane dupa patrunderea unei drone in spatiul aerian",
            "Noua drona comerciala este lansata in Romania",
        ),
        (
            "RO-Alert in Tulcea dupa detectarea unei drone aproape de granita",
            "Avion militar aterizeaza de urgenta la baza din Tulcea",
        ),
        (
            "Trump anunta noi taxe vamale pentru Europa",
            "Trump comenteaza alegerile pentru primaria New York",
        ),
        (
            "Rezultate Loto 6/49 de joi, 13 august 2026",
            "Rezultate Loto 6/49 de joi, 20 august 2026",
        ),
        (
            "David Popovici s-a calificat in finala probei de 200 metri liber",
            "David Popovici semneaza un nou contract de sponsorizare",
        ),
        (
            "David Popovici s-a calificat in finala probei de 200 metri liber",
            "David Popovici vorbeste intr-un interviu despre antrenamente",
        ),
        (
            (
                "Kourtney Kardashian si Travis Barker vorbesc despre operatia "
                "copilului lor"
            ),
            "Travis Barker explica regula casniciei sale cu Kourtney Kardashian",
        ),
        (
            "Care este diferenta dintre empatie si simpatie",
            "Miruta explica diferenta dintre inactiunea lui Grindeanu si Cernavoda",
        ),
        (
            "Cand inoata David Popovici in semifinala de 200 metri si cine transmite",
            "David Popovici a terminat primul semifinala de 200 metri liber",
        ),
        (
            "Cu cine va juca Universitatea Craiova in play-off-ul Europa League",
            "Universitatea Craiova a castigat cu KuPS si s-a calificat in play-off",
        ),
        (
            (
                "Cine transmite Tromso - CFR Cluj la TV. La ce ora incepe meciul "
                "din preliminariile Conference League"
            ),
            (
                "Cine transmite Universitatea Craiova - KuPS la TV. La ce ora "
                "incepe meciul din preliminariile Europa League"
            ),
        ),
        (
            "Aristotel Cancescu, eliberat dupa un prejudiciu de 47.000.000 de lei",
            "O mama spune ca fiul ei a cerut 500 de lei, iar alt copil 1.000 de lei",
        ),
    )
    assert not any(_matches(left, right) for left, right in negatives)


def test_follow_up_angles_do_not_bridge_weakly_related_clusters() -> None:
    assert not _matches(
        "Cel mai mare premiu din istorie la Loto 6/49 a fost castigat cu o "
        "combinatie rara",
        "Cel mai mare premiu din istorie la Loto 6/49. Cati bani intra efectiv "
        "in contul castigatorului",
    )
    assert not _matches(
        "David Popovici s-a calificat in finala probei de 200 metri liber la "
        "Europene cu cel mai bun timp",
        "David Popovici, primul mesaj dupa calificarea in finala: suntem in grafic",
    )


def test_explicit_dates_are_bounded_without_treating_ordinary_mai_as_month() -> None:
    assert _matches(
        "David Popovici obtine cel mai bun timp in finala de 200 metri",
        "David Popovici, calificat in finala de 200 m cu timpul cel mai bun",
    )
    assert not _matches(
        "Rezultate Loto din 12 mai, 2026: premiul cel mare",
        "Rezultate Loto din 13 mai 2026: premiul cel mare",
    )
    assert not _matches(
        "Raportul economic pentru mai 2026 a fost publicat",
        "Raportul economic pentru mai 2025 a fost publicat",
    )


def test_direct_match_does_not_bridge_to_same_person_follow_up() -> None:
    qualification = "David Popovici s-a calificat in finala de 200 metri liber"
    direct = "David Popovici ajunge in finala probei de 200 m liber"
    follow_up = "David Popovici da primul interviu despre viitoarele antrenamente"
    assert _matches(qualification, direct)
    assert not _matches(qualification, follow_up)
    assert not _matches(direct, follow_up)


def test_equal_matches_choose_lowest_event_id_deterministically() -> None:
    incoming = "Passaris ramane in inchisoare dupa respingerea eliberarii"
    events = [
        {
            "id": 9,
            "canonical_title": incoming,
        },
        {
            "id": 3,
            "canonical_title": incoming,
        },
    ]
    result = match_event(incoming, events, threshold=0.72)  # type: ignore[arg-type]
    assert result is not None
    assert result.event_id == 3
