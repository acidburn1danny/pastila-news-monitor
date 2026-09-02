from copy import deepcopy

import pytest

from pastila_scout.post_freeze_coverage_qualifier_v1 import CoverageTargets, qualify_frozen_rules


def rule(identity: str, family: str, cell: str, result: str, consumes=(), *, anchor=False, intermediate=False, terminal=False):
    return {
        "rule_identity": identity * 64, "predicate_family": family, "curriculum_cell": cell,
        "actor_classes": ["INPUT", *consumes], "patient_classes": ["PATIENT"],
        "actor_roles": ["VALUE"], "patient_roles": ["OBJECT"],
        "required_affordances": {"actor": ["USE"], "patient": []},
        "preconditions": ["READY"], "transition": {"direction": "FORWARD"},
        "result": {"class": result, "roles": ["VALUE"], "affordances": ["USE"]},
        "composition": {"anchor": anchor, "intermediate": intermediate, "terminal": terminal,
                        "consumable_result_classes": list(consumes)},
    }


def permissive_targets():
    return CoverageTargets(family_minimum=1, family_total=3, anchor_family_minimum=1,
                           result_family_minimum=1, terminal_family_minimum=1,
                           distinct_family_two_edge_minimum=2, three_stage_minimum=1,
                           island_fraction_maximum=0.0, priority_families=())


def test_freeze_is_a_hard_precondition():
    with pytest.raises(ValueError, match="RULE_CONTENT_FREEZE"):
        qualify_frozen_rules([], rule_content_freeze_identity="")


def test_measures_compatible_graph_and_qualifies_without_mutation():
    rules = [
        rule("a", "A", "A1", "MID", anchor=True),
        rule("b", "B", "B1", "END", ("MID",), intermediate=True),
        rule("c", "C", "C1", "DONE", ("END",), terminal=True),
    ]
    before = deepcopy(rules)
    report = qualify_frozen_rules(rules, rule_content_freeze_identity="freeze-1", targets=permissive_targets())
    assert report.qualified
    assert report.distinct_family_two_edge_compositions == (("a" * 64, "b" * 64), ("b" * 64, "c" * 64))
    assert report.anchor_intermediate_terminal_compositions == (("a" * 64, "b" * 64, "c" * 64),)
    assert report.disconnected_rule_island_fraction == 0
    assert rules == before


def test_exact_roles_and_affordances_prevent_hidden_inheritance():
    left = rule("a", "A", "A1", "MID", anchor=True)
    right = rule("b", "B", "B1", "END", ("MID",), terminal=True)
    right["actor_roles"] = ["VALUE", "EXTRA"]
    report = qualify_frozen_rules([left, right], rule_content_freeze_identity="freeze")
    assert report.compatible_edges == ()
    assert report.disconnected_rule_island_fraction == 0.5


def test_reports_ambiguity_privilege_duplicates_contradictions_and_overlap():
    first = rule("a", "A", "CELL", "ONE", terminal=True)
    second = rule("b", "A", "CELL", "TWO", terminal=True)
    duplicate = deepcopy(first)
    duplicate["curriculum_cell"] = "OTHER"
    report = qualify_frozen_rules(
        [first, second, duplicate], rule_content_freeze_identity="freeze",
        privileged_affordances={"USE"}, privileged_review_receipts={"a" * 64: "reviewed"},
    )
    assert report.ambiguous_rule_cells == ("CELL",)
    assert report.unreviewed_privileged_affordance_rules == ("b" * 64,)
    assert report.duplicate_rule_identities == ("a" * 64,)
    assert report.duplicate_semantic_rules == (("a" * 64, "a" * 64),)
    assert ("a" * 64, "b" * 64) in report.incompatible_outcome_overlaps
    assert any(set(group) == {"a" * 64, "b" * 64} for group in report.contradictions)
    assert not report.qualified


def test_detects_causal_cycles_and_islands():
    one = rule("a", "A", "A1", "Y", ("X",), anchor=True)
    two = rule("b", "B", "B1", "X", ("Y",), terminal=True)
    island = rule("c", "C", "C1", "Z")
    report = qualify_frozen_rules([one, two, island], rule_content_freeze_identity="freeze")
    assert report.cycles == (("a" * 64, "b" * 64),)
    assert report.disconnected_island_count == 1
    assert report.disconnected_rule_island_fraction == pytest.approx(1 / 3)
