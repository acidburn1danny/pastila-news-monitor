"""Part 5D endpoint-level diagnostics for the frozen required-time predicate."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from pastila_scout.editor.generation.models import EpisodeDraft, derive_assembled_text
from scripts.openai_controlled_revision_acceptance import (
    AcceptanceStatus,
    evaluate_editorial_acceptance,
)
from scripts.validate_openai_controlled_revision_e2e import (
    SCENARIOS,
    acceptance_specification,
)

SOURCE = SCENARIOS[0].source
SPECIFICATION = acceptance_specification(SCENARIOS[0])
PREFIX = (
    "Clar și firesc: la Brașov, biblioteca municipală va deschide la 15 "
    "septembrie o sală cu 120 de locuri, 30 de mese și 18 calculatoare. Program: "
)


def _revision(rendering: str) -> EpisodeDraft:
    values = SOURCE.model_dump(mode="python")
    values["opening"] = PREFIX + rendering
    assembled = derive_assembled_text(
        opening=values["opening"],
        stories=values["stories"],
        transitions=values["transitions"],
        closing=values["closing"],
        cta=values["cta"],
    )
    values["assembled_text"] = assembled
    values["teleprompter_text"] = assembled
    return EpisodeDraft.model_validate(values)


def _time(rendering: str, *, specification=SPECIFICATION, overrides=None):
    result = evaluate_editorial_acceptance(
        SOURCE,
        _revision(rendering),
        specification,
        predicate_overrides=overrides,
    )
    return next(
        item
        for item in result.predicates
        if item.predicate == "editorial.required_times"
    )


@pytest.mark.parametrize(
    "rendering",
    (
        "09:00–20:00",
        "09:00-20:00",
        "09:00—20:00",
        "09:00 – 20:00",
        "09:00\u00a0–\u00a020:00",
    ),
)
def test_t01_t04_and_t15_canonical_typography_passes(rendering: str) -> None:
    item = _time(rendering)
    assert item.status is AcceptanceStatus.PASS
    assert item.start_endpoint_matched_count == 1
    assert item.end_endpoint_matched_count == 1
    assert item.canonical_range_match_count == 1
    assert item.alternate_range_match_count == 0


@pytest.mark.parametrize("rendering", ("între 09:00 și 20:00", "de la 09:00 la 20:00"))
def test_t05_t06_approved_connectives_are_accepted(
    rendering: str,
) -> None:
    item = _time(rendering)
    assert item.status is AcceptanceStatus.PASS
    assert item.failure_category is None
    assert item.start_endpoint_matched_count == 1
    assert item.end_endpoint_matched_count == 1
    assert item.canonical_range_match_count == 0
    assert item.alternate_range_match_count == 1


def test_t07_reversed_endpoints_do_not_pass() -> None:
    item = _time("20:00–09:00")
    assert item.status is AcceptanceStatus.FAIL
    assert item.canonical_range_match_count == 0
    assert item.failure_category == "required_time_order_reversed"


def test_t08_start_endpoint_only() -> None:
    item = _time("09:00")
    assert item.start_endpoint_matched_count == 1
    assert item.end_endpoint_matched_count == 0
    assert item.failure_category == "required_time_end_missing"


def test_t09_end_endpoint_only() -> None:
    item = _time("20:00")
    assert item.start_endpoint_matched_count == 0
    assert item.end_endpoint_matched_count == 1
    assert item.failure_category == "required_time_start_missing"


def test_t10_unrelated_sentences_leave_endpoints_unpaired() -> None:
    item = _time("09:00 este ora de început. Altă propoziție menționează 20:00.")
    assert item.status is AcceptanceStatus.FAIL
    assert item.unpaired_endpoint_count == 1
    assert item.failure_category == "required_time_endpoints_present_but_unpaired"


@pytest.mark.parametrize(
    ("rendering", "category"),
    (
        ("10:00–20:00", "required_time_start_missing"),
        ("09:00–21:00", "required_time_end_missing"),
    ),
)
def test_t11_t12_changed_endpoint_fails(rendering: str, category: str) -> None:
    item = _time(rendering)
    assert item.status is AcceptanceStatus.FAIL
    assert item.failure_category == category


def test_t13_leading_zero_variation_remains_distinct_under_current_contract() -> None:
    item = _time("9:00–20:00")
    assert item.status is AcceptanceStatus.FAIL
    assert item.failure_category == "required_time_start_missing"


def test_t14_dot_separator_remains_distinct_under_current_contract() -> None:
    item = _time("09.00–20.00")
    assert item.status is AcceptanceStatus.FAIL
    assert item.start_endpoint_matched_count == 0
    assert item.end_endpoint_matched_count == 0


def test_t16_expected_range_and_unauthorized_time_remain_independent() -> None:
    specification = replace(SPECIFICATION, known_unauthorized_times=("21:00",))
    result = evaluate_editorial_acceptance(
        SOURCE, _revision("09:00–20:00. Este menționată și ora 21:00."), specification
    )
    statuses = {item.predicate: item.status for item in result.predicates}
    assert statuses["editorial.required_times"] is AcceptanceStatus.PASS
    assert statuses["editorial.unauthorized_times"] is AcceptanceStatus.FAIL


def test_t17_no_time_reports_both_endpoints_missing() -> None:
    item = _time("zilnic")
    assert item.status is AcceptanceStatus.FAIL
    assert item.start_endpoint_matched_count == 0
    assert item.end_endpoint_matched_count == 0
    assert item.failure_category == "required_time_range_missing"


def test_t18_extraction_error_is_content_free_not_run() -> None:
    def explode() -> bool:
        raise RuntimeError("TIME-RAW-LEAK-MARKER")

    item = _time(
        "09:00–20:00",
        overrides={"editorial.required_times": explode},
    )
    serialized = json.dumps(item.safe_dict())
    assert item.status is AcceptanceStatus.NOT_RUN
    assert item.failure_category == "time_predicate_execution_error"
    assert "TIME-RAW-LEAK-MARKER" not in serialized


def test_endpoint_diagnostic_serialization_never_contains_time_values() -> None:
    serialized = json.dumps(_time("între 09:00 și 20:00").safe_dict())
    assert "09:00" not in serialized
    assert "20:00" not in serialized
    assert "între" not in serialized
    assert "expected_range_count" in serialized
    assert "alternate_range_match_count" in serialized


def test_t19_duplicate_canonical_and_alternate_ranges_fail_count() -> None:
    item = _time("09:00–20:00 și între 09:00 și 20:00")
    assert item.status is AcceptanceStatus.FAIL
    assert item.matched_range_count == 2
    assert item.failure_category == "required_time_range_count_mismatch"


def test_t20_two_expected_ranges_match_independently_without_cross_pairing() -> None:
    specification = replace(
        SPECIFICATION,
        required_times=("09:00-12:00", "14:00-20:00"),
    )
    result = evaluate_editorial_acceptance(
        SOURCE,
        _revision("între 09:00 și 12:00, apoi de la 14:00 la 20:00"),
        specification,
    )
    item = next(
        value
        for value in result.predicates
        if value.predicate == "editorial.required_times"
    )
    assert item.status is AcceptanceStatus.PASS
    assert item.alternate_range_match_count == 2
    assert item.matched_range_count == 2


def test_t21_cross_component_endpoints_do_not_pair() -> None:
    values = SOURCE.model_dump(mode="python")
    values["opening"] = PREFIX + "de la 09:00"
    values["closing"] = "Încheiere protejată la 20:00."
    values["assembled_text"] = derive_assembled_text(
        opening=values["opening"],
        stories=values["stories"],
        transitions=values["transitions"],
        closing=values["closing"],
        cta=values["cta"],
    )
    values["teleprompter_text"] = values["assembled_text"]
    revised = EpisodeDraft.model_validate(values)
    result = evaluate_editorial_acceptance(SOURCE, revised, SPECIFICATION)
    item = next(
        value
        for value in result.predicates
        if value.predicate == "editorial.required_times"
    )
    assert item.status is AcceptanceStatus.FAIL
    assert item.failure_category == "required_time_end_missing"


def test_t22_adjacent_unrelated_times_do_not_pair() -> None:
    item = _time("09:00 este începutul. O ședință separată apare la 20:00.")
    assert item.status is AcceptanceStatus.FAIL
    assert item.failure_category == "required_time_endpoints_present_but_unpaired"


def test_t23_casefolded_romanian_connective_passes() -> None:
    item = _time("ÎNTRE 09:00 ȘI 20:00")
    assert item.status is AcceptanceStatus.PASS
    assert item.alternate_range_match_count == 1


@pytest.mark.parametrize(
    "rendering",
    ("între: 09:00, și 20:00", "de la 09:00, la 20:00"),
)
def test_t24_harmless_connective_punctuation_passes(rendering: str) -> None:
    item = _time(rendering)
    assert item.status is AcceptanceStatus.PASS
    assert item.alternate_range_match_count == 1


def test_t25_unsupported_connective_remains_unpaired() -> None:
    item = _time("programul pornește 09:00 iar ulterior apare 20:00")
    assert item.status is AcceptanceStatus.FAIL
    assert item.failure_category == "required_time_endpoints_present_but_unpaired"
