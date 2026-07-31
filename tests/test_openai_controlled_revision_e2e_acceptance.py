"""Focused tests for content-free Part 5C acceptance diagnostics."""

from __future__ import annotations

import json

import pytest

from pastila_scout.editor.generation.models import EpisodeDraft, derive_assembled_text
from scripts.openai_controlled_revision_acceptance import (
    AcceptanceStatus,
    evaluate_editorial_acceptance,
    normalize_editorial_text,
)
from scripts.validate_openai_controlled_revision_e2e import (
    SCENARIOS,
    acceptance_specification,
)

SOURCE = SCENARIOS[0].source
SPECIFICATION = acceptance_specification(SCENARIOS[0])
VALID_OPENING = (
    "Clar și firesc: la Brașov, biblioteca municipală va deschide la 15 "
    "septembrie o sală cu 120 de locuri, 30 de mese și 18 calculatoare. "
    "Program: 09:00 - 20:00."
)


def _revision(
    opening: str = VALID_OPENING, *, closing: str | None = None
) -> EpisodeDraft:
    values = SOURCE.model_dump(mode="python")
    values["opening"] = opening
    if closing is not None:
        values["closing"] = closing
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


def _statuses(result) -> dict[str, AcceptanceStatus]:
    return {item.predicate: item.status for item in result.predicates}


def _evaluate(opening: str = VALID_OPENING, *, closing: str | None = None):
    return evaluate_editorial_acceptance(
        SOURCE, _revision(opening, closing=closing), SPECIFICATION
    )


def test_d01_fully_valid_revision_passes() -> None:
    result = _evaluate()
    assert result.passed
    assert all(
        item.status in {AcceptanceStatus.PASS, AcceptanceStatus.NOT_APPLICABLE}
        for item in result.predicates
    )


@pytest.mark.parametrize(
    ("case", "opening", "predicate"),
    (
        (
            "D02",
            VALID_OPENING.replace("120 de ", ""),
            "editorial.required_numeric_values",
        ),
        (
            "D03",
            VALID_OPENING.replace("15 septembrie", "septembrie"),
            "editorial.required_dates",
        ),
        (
            "D04",
            VALID_OPENING.replace("09:00 - 20:00", "toată ziua"),
            "editorial.required_times",
        ),
        ("D05", VALID_OPENING.replace("Brașov", "oraș"), "editorial.required_entities"),
        (
            "D06",
            VALID_OPENING + " Sunt 777 voluntari.",
            "editorial.unauthorized_numbers",
        ),
        (
            "D07",
            VALID_OPENING + " Revine la 16 septembrie.",
            "editorial.unauthorized_dates",
        ),
        (
            "D08",
            VALID_OPENING + " Revine la 10:00-20:00.",
            "editorial.unauthorized_times",
        ),
        (
            "D09",
            VALID_OPENING + " Proiectul ajunge în București.",
            "editorial.unauthorized_entities",
        ),
    ),
)
def test_d02_to_d09_isolate_fact_failures(
    case: str, opening: str, predicate: str
) -> None:
    del case
    result = _evaluate(opening)
    assert not result.passed
    assert _statuses(result)[predicate] is AcceptanceStatus.FAIL


def test_d10_language_failure_does_not_hide_fact_results() -> None:
    opening = (
        "Brașov biblioteca municipală 15 septembrie. 120 locuri, 30 mese, "
        "18 calculatoare. Program 09:00-20:00."
    )
    result = _evaluate(opening)
    statuses = _statuses(result)
    assert statuses["language.romanian_preservation"] is AcceptanceStatus.FAIL
    assert statuses["editorial.required_numeric_values"] is AcceptanceStatus.PASS
    assert statuses["editorial.required_dates"] is AcceptanceStatus.PASS
    assert statuses["editorial.required_times"] is AcceptanceStatus.PASS
    assert statuses["editorial.required_entities"] is AcceptanceStatus.PASS


def test_d11_source_identical_opening_fails_distinct_revision() -> None:
    result = _evaluate(SOURCE.opening)
    assert _statuses(result)["editorial.distinct_revision"] is AcceptanceStatus.FAIL


def test_d12_protected_component_change_is_independent() -> None:
    result = _evaluate(closing="Încheiere protejată schimbată.")
    assert _statuses(result)["structure.protected_components"] is AcceptanceStatus.FAIL


def test_d13_predicate_execution_error_is_not_run() -> None:
    def explode() -> bool:
        raise RuntimeError("RAW-SECRET-VALUE")

    result = evaluate_editorial_acceptance(
        SOURCE,
        _revision(),
        SPECIFICATION,
        predicate_overrides={"editorial.required_dates": explode},
    )
    item = next(
        item
        for item in result.predicates
        if item.predicate == "editorial.required_dates"
    )
    assert item.status is AcceptanceStatus.NOT_RUN
    assert item.failure_category == "predicate_execution_error"
    assert "RAW-SECRET-VALUE" not in json.dumps(result.safe_dict())
    assert not result.passed


def test_d14_multiple_failures_are_all_reported() -> None:
    result = _evaluate(
        "English output 777 on 16 septembrie at 10:00-20:00 in București."
    )
    statuses = _statuses(result)
    failed = {key for key, value in statuses.items() if value is AcceptanceStatus.FAIL}
    assert {
        "editorial.required_numeric_values",
        "editorial.required_dates",
        "editorial.required_times",
        "editorial.required_entities",
        "editorial.unauthorized_numbers",
        "editorial.unauthorized_dates",
        "editorial.unauthorized_times",
        "editorial.unauthorized_entities",
        "language.romanian_preservation",
    } <= failed


def test_d15_source_authority_predicates_are_not_applicable() -> None:
    statuses = _statuses(_evaluate())
    assert (
        statuses["authority.embedded_instruction_not_followed"]
        is AcceptanceStatus.NOT_APPLICABLE
    )
    assert (
        statuses["authority.malicious_value_not_adopted"]
        is AcceptanceStatus.NOT_APPLICABLE
    )
    assert statuses["authority.source_data_boundary"] is AcceptanceStatus.NOT_APPLICABLE


def test_normalization_accepts_typography_but_preserves_factual_differences() -> None:
    assert normalize_editorial_text("09:00\u00a0–\u00a020:00") == "09:00-20:00"
    assert normalize_editorial_text("BRAȘOV") == normalize_editorial_text("Brașov")
    assert normalize_editorial_text("120") != normalize_editorial_text("12")
    assert normalize_editorial_text("15 septembrie") != normalize_editorial_text(
        "16 septembrie"
    )


def test_safe_json_contains_only_identifiers_statuses_and_counts() -> None:
    markers = (
        "SOURCE-LEAK-MARKER",
        "REVISED-LEAK-MARKER",
        "PROMPT-LEAK-MARKER",
        "RAW-RESPONSE-MARKER",
        "VALIDATION-VALUE-MARKER",
        "CREDENTIAL-MARKER",
        "REQUEST-ID-MARKER",
    )
    serialized = json.dumps(_evaluate().safe_dict(), ensure_ascii=False)
    assert all(marker not in serialized for marker in markers)
    assert "editorial.required_numeric_values" in serialized
    assert "expected_count" in serialized
