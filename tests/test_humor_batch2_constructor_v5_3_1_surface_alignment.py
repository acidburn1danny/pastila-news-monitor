import pytest

from pastila_scout.humor_batch2_development_constructor_v5_3_1_surface_alignment import (
    CoordinateBoundRoleWitness, validate_coordinate_bound_role_witness,
)


def witness(surface, canonical, rule):
    start = surface.index("ambelor verificări conforme")
    form = "ambelor verificări conforme"
    byte_start = len(surface[:start].encode("utf-8"))
    return CoordinateBoundRoleWitness("L1", "PATIENT", "FACT_QUALIFICATION", start, start + len(form),
                                      byte_start, byte_start + len(form.encode("utf-8")), form, canonical, rule)


def test_legitimate_romanian_case_inflection_is_coordinate_bound_and_recognized():
    surface = "numai datorită ambelor verificări conforme, pornește ecoul"
    validate_coordinate_bound_role_witness(
        surface, witness(surface, "ambele verificări conforme", "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION"))


def test_genuinely_missing_role_fails_closed():
    surface = "numai datorită rezultatului, pornește ecoul"
    item = CoordinateBoundRoleWitness("L1", "PATIENT", "FACT_QUALIFICATION", 0, 9, 0, 9,
                                      "ambelor verificări conforme", "ambele verificări conforme",
                                      "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION")
    with pytest.raises(ValueError, match="genuinely missing"):
        validate_coordinate_bound_role_witness(surface, item)


def test_unlicensed_synonym_or_claimed_equivalence_fails_closed():
    surface = "numai datorită controalelor reușite, pornește ecoul"
    form = "controalelor reușite"
    start = surface.index(form); byte_start = len(surface[:start].encode("utf-8"))
    item = CoordinateBoundRoleWitness("L1", "PATIENT", "FACT_QUALIFICATION", start, start + len(form),
                                      byte_start, byte_start + len(form.encode()), form,
                                      "ambele verificări conforme", "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION")
    with pytest.raises(ValueError, match="not deterministically licensed"):
        validate_coordinate_bound_role_witness(surface, item)
