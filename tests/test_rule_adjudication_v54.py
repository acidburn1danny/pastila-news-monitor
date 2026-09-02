from copy import deepcopy

from pastila_scout.rule_adjudication_v54 import (
    ADJUDICATOR_IDENTITY,
    REVIEW_DIMENSIONS,
    ReviewEvidence,
    adjudicate_candidate,
    canonical_rule_identity,
    validate_composition_chain,
)


ONTOLOGY = {
    "entity_classes": {
        "PERSON_AGENT": {"roles": ["ACTOR"]},
        "PHYSICAL_ENTITY": {"roles": ["PATIENT"]},
        "STATE": {"roles": ["RESULT"]},
    }
}
TAXONOMY = {
    "families": [{
        "family": "PHYSICAL_ACTION",
        "actors": ["PERSON_AGENT"],
        "patients": ["PHYSICAL_ENTITY"],
        "requires": ["ACTION_CAPABILITY"],
        "positions": ["ANCHOR", "INTERMEDIATE", "TERMINAL"],
    }]
}
CURRICULUM = {"ordering": [{"batch": 1, "domains": ["PHYSICAL_ACTION"]}]}


def candidate():
    value = {
        "schema_version": "1.0.0",
        "curriculum_cell": "B1-CELL-01",
        "origin": "FROZEN_GENERIC_ONTOLOGY",
        "provenance": {"design_basis": ["GENERAL_SEMANTICS"], "created_before_family_access": True, "blind_access": False},
        "predicate_family": "PHYSICAL_ACTION",
        "actor_classes": ["PERSON_AGENT"],
        "patient_classes": ["PHYSICAL_ENTITY"],
        "actor_roles": ["ACTOR"],
        "patient_roles": ["PATIENT"],
        "required_affordances": {"actor": ["ACTION_CAPABILITY"], "patient": []},
        "preconditions": ["actor capability is independently established"],
        "transition": {"direction": "precondition to state", "predecessor_consumption": "NOT_APPLICABLE_ANCHOR"},
        "result": {"class": "STATE", "roles": ["RESULT"], "affordances": []},
        "counterfactual": {"test": "remove capability", "expected": "SUCCESSOR_RELATION_BREAKS"},
        "non_substitutability": {"comparison_domain": "same typed operands", "maximum_compatible_rules": 1},
        "composition": {"anchor": True, "intermediate": False, "terminal": False, "consumable_result_classes": []},
        "scope": {"domains": ["physical action"], "exclusions": ["untyped actors"], "version": "1"},
        "author_identity": "RULE_AUTHOR_V54_01",
        "adjudication_receipt": "PENDING",
        "rule_identity": "0" * 64,
    }
    value["rule_identity"] = canonical_rule_identity(value)
    return value


def reviews():
    result = []
    for dimension in REVIEW_DIMENSIONS:
        reviewer = "RULE_ADJUDICATOR_V54_01"
        if dimension in {"CAUSAL_NECESSITY", "COUNTERFACTUAL_DEPENDENCY", "CONSEQUENCE_NON_SUBSTITUTABILITY"}:
            reviewer = "CAUSAL_REVIEWER_V54_01"
        elif dimension == "ADVERSARIAL_OVERBREADTH":
            reviewer = "ADVERSARIAL_REVIEWER_V54_01"
        result.append(ReviewEvidence(dimension, "PASS", "specific evidence recorded", reviewer))
    return result


def test_complete_independently_reviewed_candidate_passes_advisory_review():
    result = adjudicate_candidate(candidate(), reviews(), ontology=ONTOLOGY, taxonomy=TAXONOMY, curriculum=CURRICULUM)
    assert result.passed
    assert result.adjudicator_identity == ADJUDICATOR_IDENTITY


def test_identity_collision_and_missing_review_fail_closed():
    value = candidate()
    value["author_identity"] = ADJUDICATOR_IDENTITY
    value["rule_identity"] = canonical_rule_identity(value)
    result = adjudicate_candidate(value, reviews()[:-1], ontology=ONTOLOGY, taxonomy=TAXONOMY, curriculum=CURRICULUM)
    assert not result.passed
    assert "AUTHOR_ADJUDICATOR_IDENTITY_COLLISION" in result.blockers
    assert "REVIEW_CARDINALITY:ADVERSARIAL_OVERBREADTH" in result.blockers


def test_unlicensed_affordance_shape_and_tampered_identity_fail():
    value = candidate()
    value["required_affordances"]["actor"] = []
    result = adjudicate_candidate(value, reviews(), ontology=ONTOLOGY, taxonomy=TAXONOMY, curriculum=CURRICULUM)
    assert "FAMILY_REQUIRED_AFFORDANCE_MISSING" in result.blockers
    assert "CANONICAL_IDENTITY_MISMATCH" in result.blockers


def test_composition_requires_exact_result_consumption_and_unique_endpoints():
    first = candidate()
    second = deepcopy(first)
    second["rule_identity"] = "1" * 64
    second["composition"] = {"anchor": False, "intermediate": False, "terminal": True, "consumable_result_classes": ["STATE"]}
    second["transition"]["predecessor_consumption"] = "REQUIRED"
    assert validate_composition_chain([first, second]) == ()
    second["composition"]["consumable_result_classes"] = []
    assert "RESULT_CLASS_MISMATCH" in validate_composition_chain([first, second])
