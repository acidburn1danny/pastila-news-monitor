"""Independent semantic licensing for successor DEVELOPMENT constructors.

The planner may select operands and request rules.  It may not create the
ontology, affordances, rule truth, or counterfactual result used to validate
its own plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Iterable, Mapping


class RuleOrigin(StrEnum):
    SOURCE_DERIVED = "SOURCE_DERIVED"
    FROZEN_GENERIC_ONTOLOGY = "FROZEN_GENERIC_ONTOLOGY"


@dataclass(frozen=True, slots=True)
class SemanticOperand:
    operand_id: str
    entity_class: str
    roles: frozenset[str]
    affordances: frozenset[str]
    authority_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class TrustedSemanticRule:
    rule_id: str
    origin: RuleOrigin
    predicate_class: str
    actor_classes: frozenset[str]
    patient_classes: frozenset[str]
    actor_roles: frozenset[str]
    patient_roles: frozenset[str]
    actor_affordances: frozenset[str]
    patient_affordances: frozenset[str]
    result_class: str
    result_roles: frozenset[str]
    result_affordances: frozenset[str]
    source_authority_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProposedRelation:
    relation_id: str
    predecessor_relation_id: str | None
    predicate_class: str
    actor_id: str
    patient_id: str
    result_id: str
    requested_rule_id: str
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class LicensedPlan:
    relations: tuple[ProposedRelation, ...]
    derived_operands: tuple[SemanticOperand, ...]
    rule_ids: tuple[str, ...]
    counterfactual_edges: tuple["CounterfactualEdgeResult", ...]


@dataclass(frozen=True, slots=True)
class CounterfactualEdgeResult:
    predecessor_relation_id: str
    successor_relation_id: str
    produced_operand_id: str
    removal_breaks_successor: bool
    alternative_rule_count: int


class TrustedRuleRegistry:
    """Immutable registry constructed outside the planner invocation."""

    def __init__(self, rules: Iterable[TrustedSemanticRule]) -> None:
        materialized = tuple(rules)
        by_id = {rule.rule_id: rule for rule in materialized}
        if len(by_id) != len(materialized):
            raise ValueError("duplicate trusted rule")
        self._rules = by_id

    def get(self, rule_id: str) -> TrustedSemanticRule:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise ValueError("relation requests an untrusted semantic rule") from exc

    def compatible_rules(self, predicate: str, actor: SemanticOperand, patient: SemanticOperand) -> tuple[TrustedSemanticRule, ...]:
        return tuple(rule for rule in self._rules.values()
                     if rule.predicate_class == predicate
                     and actor.entity_class in rule.actor_classes
                     and patient.entity_class in rule.patient_classes
                     and rule.actor_roles.issubset(actor.roles)
                     and rule.patient_roles.issubset(patient.roles)
                     and rule.actor_affordances.issubset(actor.affordances)
                     and rule.patient_affordances.issubset(patient.affordances))


def semantic_rule_identity(rule: TrustedSemanticRule) -> str:
    payload = {
        "rule_id": rule.rule_id, "origin": rule.origin.value, "predicate_class": rule.predicate_class,
        "actor_classes": sorted(rule.actor_classes), "patient_classes": sorted(rule.patient_classes),
        "actor_roles": sorted(rule.actor_roles), "patient_roles": sorted(rule.patient_roles),
        "actor_affordances": sorted(rule.actor_affordances),
        "patient_affordances": sorted(rule.patient_affordances), "result_class": rule.result_class,
        "result_roles": sorted(rule.result_roles), "result_affordances": sorted(rule.result_affordances),
        "source_authority_ids": sorted(rule.source_authority_ids),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _contains(required: frozenset[str], actual: frozenset[str], label: str) -> None:
    if not required.issubset(actual):
        raise ValueError(f"{label} incompatible with trusted rule")


def validate_and_license_plan(
    *,
    authority_operands: tuple[SemanticOperand, ...],
    proposed_relations: tuple[ProposedRelation, ...],
    registry: TrustedRuleRegistry,
    authorized_source_rule_ids: frozenset[str] = frozenset(),
) -> LicensedPlan:
    """Validate every relation, including the anchor and terminal relations.

    Produced operands are derived exclusively from the selected trusted rule;
    planner-supplied result roles or affordances are not accepted.
    """
    if not proposed_relations:
        raise ValueError("empty semantic plan")
    operands: dict[str, SemanticOperand] = {item.operand_id: item for item in authority_operands}
    if len(operands) != len(authority_operands):
        raise ValueError("duplicate authority operand")
    seen_relations: set[str] = set()
    derived: list[SemanticOperand] = []
    terminal_count = 0
    previous: str | None = None
    produced_by_relation: dict[str, str] = {}
    counterfactuals: list[CounterfactualEdgeResult] = []
    derived_classes: set[str] = set()

    for index, relation in enumerate(proposed_relations):
        if relation.relation_id in seen_relations:
            raise ValueError("duplicate relation")
        if relation.predecessor_relation_id != previous:
            raise ValueError("plan relation is disconnected or directionally invalid")
        if relation.result_id in operands:
            raise ValueError("relation result overwrites an existing operand")
        actor = operands.get(relation.actor_id)
        patient = operands.get(relation.patient_id)
        if actor is None or patient is None:
            raise ValueError("relation has an unbound operand")
        rule = registry.get(relation.requested_rule_id)
        if rule.predicate_class != relation.predicate_class:
            raise ValueError("predicate is not licensed by requested rule")
        if actor.entity_class not in rule.actor_classes or patient.entity_class not in rule.patient_classes:
            raise ValueError("predicate argument entity class is incompatible")
        _contains(rule.actor_roles, actor.roles, "actor role")
        _contains(rule.patient_roles, patient.roles, "patient role")
        _contains(rule.actor_affordances, actor.affordances, "actor affordance")
        _contains(rule.patient_affordances, patient.affordances, "patient affordance")
        compatible = registry.compatible_rules(relation.predicate_class, actor, patient)
        if len(compatible) != 1 or compatible[0].rule_id != rule.rule_id:
            raise ValueError("semantic consequence is absent or freely substitutable")
        if rule.origin is RuleOrigin.SOURCE_DERIVED:
            if semantic_rule_identity(rule) not in authorized_source_rule_ids:
                raise ValueError("source-derived rule identity is not independently authorized")
            if not rule.source_authority_ids or not rule.source_authority_ids.issubset(
                actor.authority_ids | patient.authority_ids
            ):
                raise ValueError("source-derived rule lacks exact authority support")
        elif rule.source_authority_ids:
            raise ValueError("generic ontology rule cannot claim source authority")

        if previous is not None:
            predecessor_result = produced_by_relation[previous]
            consumed = relation.actor_id == predecessor_result or relation.patient_id == predecessor_result
            if not consumed:
                raise ValueError("successor does not consume the immediate predecessor result")
        result = SemanticOperand(
            relation.result_id,
            rule.result_class,
            rule.result_roles,
            rule.result_affordances,
            actor.authority_ids | patient.authority_ids | rule.source_authority_ids,
        )
        actor_signature = (actor.entity_class, actor.roles, actor.affordances)
        patient_signature = (patient.entity_class, patient.roles, patient.affordances)
        result_signature = (result.entity_class, result.roles, result.affordances)
        if result_signature in {actor_signature, patient_signature}:
            raise ValueError("semantic edge merely restates an input operand")
        if result.entity_class in derived_classes:
            raise ValueError("semantic plan contains a derived-class cycle")
        operands[result.operand_id] = result
        derived_classes.add(result.entity_class)
        if previous is not None:
            # This evidence is validator-derived: remove the predecessor result and
            # the successor necessarily loses a required bound argument.
            counterfactuals.append(CounterfactualEdgeResult(
                previous, relation.relation_id, predecessor_result, consumed, len(compatible) - 1,
            ))
        produced_by_relation[relation.relation_id] = result.operand_id
        derived.append(result)
        seen_relations.add(relation.relation_id)
        previous = relation.relation_id
        terminal_count += int(relation.terminal)
        if relation.terminal != (index == len(proposed_relations) - 1):
            raise ValueError("terminal marker must identify only the final relation")

    if terminal_count != 1:
        raise ValueError("plan must contain exactly one terminal relation")
    return LicensedPlan(proposed_relations, tuple(derived),
                        tuple(r.requested_rule_id for r in proposed_relations), tuple(counterfactuals))


def assert_registry_is_external(
    *, registry_rules: Mapping[str, TrustedSemanticRule], planner_payload_keys: frozenset[str]
) -> None:
    """Reject planner payloads capable of extending semantic authority."""
    forbidden = {"rules", "ontology", "roles", "affordances", "predicate_signatures", "necessity"}
    if planner_payload_keys & forbidden:
        raise ValueError("planner payload attempts to author semantic validation evidence")
    if not registry_rules:
        raise ValueError("trusted semantic rule registry is empty")


def verify_rule_registry_partition(
    *,
    rules: tuple[TrustedSemanticRule, ...],
    frozen_generic_rule_ids: frozenset[str],
    authorized_source_rule_ids: frozenset[str],
) -> None:
    """Require every rule to belong to exactly one independently frozen trust domain."""
    ids = {rule.rule_id for rule in rules}
    if len(ids) != len(rules):
        raise ValueError("duplicate rule identity")
    if frozen_generic_rule_ids & authorized_source_rule_ids:
        raise ValueError("semantic rule trust domains overlap")
    for rule in rules:
        if rule.origin is RuleOrigin.FROZEN_GENERIC_ONTOLOGY:
            if semantic_rule_identity(rule) not in frozen_generic_rule_ids:
                raise ValueError("generic rule is not in the frozen ontology")
        elif semantic_rule_identity(rule) not in authorized_source_rule_ids:
            raise ValueError("source-derived rule is not in the authority envelope")


__all__ = [
    "CounterfactualEdgeResult", "LicensedPlan", "ProposedRelation", "RuleOrigin", "SemanticOperand",
    "TrustedRuleRegistry", "TrustedSemanticRule", "assert_registry_is_external",
    "semantic_rule_identity", "validate_and_license_plan", "verify_rule_registry_partition",
]
