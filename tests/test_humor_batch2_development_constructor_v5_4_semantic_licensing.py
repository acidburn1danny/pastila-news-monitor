from __future__ import annotations

import pytest

from pastila_scout.humor_batch2_development_constructor_v5_4_semantic_licensing import (
    ProposedRelation, RuleOrigin, SemanticOperand, TrustedRuleRegistry,
    TrustedSemanticRule, assert_registry_is_external, validate_and_license_plan,
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
