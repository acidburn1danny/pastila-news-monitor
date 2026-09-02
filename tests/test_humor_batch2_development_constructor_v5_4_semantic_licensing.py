from __future__ import annotations

import pytest

from pastila_scout.humor_batch2_development_constructor_v5_4_semantic_licensing import (
    ProposedRelation, RuleOrigin, SemanticOperand, TrustedRuleRegistry,
    TrustedSemanticRule, assert_registry_is_external, validate_and_license_plan,
    verify_rule_registry_partition,
)


def operand(identifier: str, kind: str, roles: set[str], affordances: set[str], authority: set[str] = {"P"}):
    return SemanticOperand(identifier, kind, frozenset(roles), frozenset(affordances), frozenset(authority))


def rule(identifier: str, predicate: str, actor: str, patient: str, *,
         actor_role: str, patient_role: str, actor_affordance: str,
         patient_affordance: str, result: str = "EVENT"):
    return TrustedSemanticRule(identifier, RuleOrigin.FROZEN_GENERIC_ONTOLOGY, predicate,
        frozenset({actor}), frozenset({patient}), frozenset({actor_role}),
        frozenset({patient_role}), frozenset({actor_affordance}),
        frozenset({patient_affordance}), result, frozenset({"RESULT"}),
        frozenset({"CONTINUE"}), frozenset())


def test_trusted_rule_positive_control_and_anchor_edge_coverage():
    registry = TrustedRuleRegistry((rule("timer-fires", "TRIGGER", "TIMER_EVENT", "ALARM",
        actor_role="TRIGGER", patient_role="TRIGGERABLE", actor_affordance="FIRE",
        patient_affordance="BE_TRIGGERED"),))
    plan = validate_and_license_plan(authority_operands=(
        operand("timer", "TIMER_EVENT", {"TRIGGER"}, {"FIRE"}),
        operand("alarm", "ALARM", {"TRIGGERABLE"}, {"BE_TRIGGERED"}),
    ), proposed_relations=(ProposedRelation("anchor-to-terminal", None, "TRIGGER", "timer", "alarm",
        "ringing", "timer-fires", True),), registry=registry)
    assert plan.derived_operands[0].entity_class == "EVENT"


@pytest.mark.parametrize(("actor_kind", "patient_kind", "predicate"), [
    ("PROPOSITION", "TEMPORAL_MOMENT", "ACTIVATE"),
    ("STATUS", "LOG", "PROPAGATE"),
    ("ABSTRACT_STATE", "RELATION", "RESOLVE"),
    ("RECORD", "PERSON", "OBLIGATE"),
])
def test_pilot13_failure_classes_cannot_self_license(actor_kind, patient_kind, predicate):
    registry = TrustedRuleRegistry((rule("unrelated", "TRIGGER", "TIMER_EVENT", "ALARM",
        actor_role="TRIGGER", patient_role="TRIGGERABLE", actor_affordance="FIRE",
        patient_affordance="BE_TRIGGERED"),))
    with pytest.raises(ValueError, match="untrusted semantic rule"):
        validate_and_license_plan(authority_operands=(
            operand("a", actor_kind, {"PLANNER_ROLE"}, {"PLANNER_AFFORDANCE"}),
            operand("p", patient_kind, {"PLANNER_ROLE"}, {"PLANNER_AFFORDANCE"}),
        ), proposed_relations=(ProposedRelation("r", None, predicate, "a", "p", "x",
            "planner-created-rule", True),), registry=registry)


@pytest.mark.parametrize("key", ["rules", "ontology", "roles", "affordances", "predicate_signatures", "necessity"])
def test_planner_cannot_supply_validation_authority(key):
    trusted = rule("timer-fires", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED")
    with pytest.raises(ValueError, match="attempts to author"):
        assert_registry_is_external(registry_rules={trusted.rule_id: trusted}, planner_payload_keys=frozenset({key}))


def test_reclassification_or_grammatical_position_does_not_create_affordance():
    trusted = rule("timer-fires", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED")
    with pytest.raises(ValueError, match="entity class"):
        validate_and_license_plan(authority_operands=(
            operand("subject", "PROPOSITION", {"TRIGGER"}, {"FIRE"}),
            operand("object", "ALARM", {"TRIGGERABLE"}, {"BE_TRIGGERED"}),
        ), proposed_relations=(ProposedRelation("r", None, "TRIGGER", "subject", "object", "x",
            trusted.rule_id, True),), registry=TrustedRuleRegistry((trusted,)))


def test_predecessor_label_without_produced_operand_consumption_fails():
    first = rule("first", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED")
    second = rule("second", "OTHER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED")
    with pytest.raises(ValueError, match="does not consume"):
        validate_and_license_plan(authority_operands=(
            operand("timer", "TIMER_EVENT", {"TRIGGER"}, {"FIRE"}),
            operand("alarm", "ALARM", {"TRIGGERABLE"}, {"BE_TRIGGERED"}),
        ), proposed_relations=(
            ProposedRelation("r1", None, "TRIGGER", "timer", "alarm", "derived", "first"),
            ProposedRelation("r2", "r1", "OTHER", "timer", "alarm", "terminal", "second", True),
        ), registry=TrustedRuleRegistry((first, second)))


def test_compatible_alternative_consequence_fails_substitutability():
    one = rule("one", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED",
        result="RINGING")
    two = rule("two", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
        patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED",
        result="FLASHING")
    with pytest.raises(ValueError, match="freely substitutable"):
        validate_and_license_plan(authority_operands=(
            operand("timer", "TIMER_EVENT", {"TRIGGER"}, {"FIRE"}),
            operand("alarm", "ALARM", {"TRIGGERABLE"}, {"BE_TRIGGERED"}),
        ), proposed_relations=(ProposedRelation("r", None, "TRIGGER", "timer", "alarm", "x", "one", True),),
        registry=TrustedRuleRegistry((one, two)))


def test_counterfactual_is_validator_derived_for_each_chained_edge():
    first = TrustedSemanticRule("timer-fires", RuleOrigin.FROZEN_GENERIC_ONTOLOGY, "TRIGGER",
        frozenset({"TIMER_EVENT"}), frozenset({"ALARM"}), frozenset({"TRIGGER"}),
        frozenset({"TRIGGERABLE"}), frozenset({"FIRE"}), frozenset({"BE_TRIGGERED"}),
        "RINGING", frozenset({"SIGNAL"}), frozenset({"NOTIFY"}), frozenset())
    second = TrustedSemanticRule("ringing-notifies", RuleOrigin.FROZEN_GENERIC_ONTOLOGY, "NOTIFY",
        frozenset({"RINGING"}), frozenset({"OPERATOR"}), frozenset({"SIGNAL"}),
        frozenset({"RECIPIENT"}), frozenset({"NOTIFY"}), frozenset({"RECEIVE"}),
        "NOTICE", frozenset({"RESULT"}), frozenset(), frozenset())
    plan = validate_and_license_plan(authority_operands=(
        operand("timer", "TIMER_EVENT", {"TRIGGER"}, {"FIRE"}),
        operand("alarm", "ALARM", {"TRIGGERABLE"}, {"BE_TRIGGERED"}),
        operand("operator", "OPERATOR", {"RECIPIENT"}, {"RECEIVE"}),
    ), proposed_relations=(
        ProposedRelation("r1", None, "TRIGGER", "timer", "alarm", "ringing", "timer-fires"),
        ProposedRelation("r2", "r1", "NOTIFY", "ringing", "operator", "notice", "ringing-notifies", True),
    ), registry=TrustedRuleRegistry((first, second)))
    assert plan.counterfactual_edges[0].removal_breaks_successor is True
    assert plan.counterfactual_edges[0].alternative_rule_count == 0


def test_source_derived_rule_needs_independent_rule_identity_authority():
    source_rule = TrustedSemanticRule("source-rule", RuleOrigin.SOURCE_DERIVED, "REPORT",
        frozenset({"SENSOR"}), frozenset({"LOG"}), frozenset({"REPORTER"}),
        frozenset({"RECORD"}), frozenset({"REPORT"}), frozenset({"RECEIVE"}),
        "ENTRY", frozenset({"RESULT"}), frozenset(), frozenset({"P"}))
    args = dict(authority_operands=(
        operand("sensor", "SENSOR", {"REPORTER"}, {"REPORT"}),
        operand("log", "LOG", {"RECORD"}, {"RECEIVE"}),
    ), proposed_relations=(ProposedRelation("r", None, "REPORT", "sensor", "log", "entry",
        "source-rule", True),), registry=TrustedRuleRegistry((source_rule,)))
    with pytest.raises(ValueError, match="not independently authorized"):
        validate_and_license_plan(**args)
    assert validate_and_license_plan(**args, authorized_source_rule_ids=frozenset({"source-rule"}))


@pytest.mark.parametrize("origin", [RuleOrigin.SOURCE_DERIVED, RuleOrigin.FROZEN_GENERIC_ONTOLOGY])
def test_rule_cannot_claim_a_trust_domain_by_label_alone(origin):
    candidate = TrustedSemanticRule("candidate", origin, "X", frozenset({"A"}), frozenset({"B"}),
        frozenset(), frozenset(), frozenset(), frozenset(), "C", frozenset(), frozenset(),
        frozenset({"P"}) if origin is RuleOrigin.SOURCE_DERIVED else frozenset())
    with pytest.raises(ValueError, match="not in"):
        verify_rule_registry_partition(rules=(candidate,), frozen_generic_rule_ids=frozenset(),
                                       authorized_source_rule_ids=frozenset())


@pytest.mark.parametrize("entity_class", [
    "PROPOSITION", "TEMPORAL_MOMENT", "STATUS", "ELIGIBILITY", "RECORD", "LOG", "LABEL",
    "ABSTRACT_STATE", "EVENT", "INFORMATION_OBJECT",
])
@pytest.mark.parametrize("predicate", ["ACTIVATE", "PROPAGATE", "RESOLVE", "OBLIGATE", "AUTHORIZE"])
def test_unrelated_vocabulary_and_predicate_permutations_never_create_a_rule(entity_class, predicate):
    with pytest.raises(ValueError, match="untrusted semantic rule"):
        validate_and_license_plan(authority_operands=(
            operand("x", entity_class, {"GRAMMATICAL_SUBJECT"}, {"PREDECESSOR"}),
            operand("y", "OBJECT", {"GRAMMATICAL_OBJECT"}, {"TERMINAL_PATIENT"}),
        ), proposed_relations=(ProposedRelation("relation", None, predicate, "x", "y", "z",
            f"local-{entity_class.lower()}-{predicate.lower()}", True),), registry=TrustedRuleRegistry((
                rule("control", "TRIGGER", "TIMER_EVENT", "ALARM", actor_role="TRIGGER",
                     patient_role="TRIGGERABLE", actor_affordance="FIRE", patient_affordance="BE_TRIGGERED"),
            )))
