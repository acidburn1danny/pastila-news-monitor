"""Zero-release integration of V5.4 licensing with the V5.3.3 byte path."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import (
    FrozenExecutableAuthorityV533, FrozenNodeRelationRule, FrozenSurfaceRoleRule,
    TrustedConformanceReceiptV533, conditional_emit, invoke_clause_only_provider,
    observe_and_conform_surface,
)
from pastila_scout.humor_batch2_development_constructor_v5_4_semantic_licensing import (
    LicensedPlan, ProposedRelation, SemanticOperand, TrustedRuleRegistry,
    TrustedSemanticRule, assert_registry_is_external, validate_and_license_plan,
    verify_rule_registry_partition,
)


@dataclass(frozen=True, slots=True)
class FrozenIntegratedAuthorityV54:
    authority_identity: str
    implementation_identity: str
    release_binding_identity: str
    proposition_span_identity: str
    denyset_identity: str
    alignment_policy_identity: str
    contract_identity: str
    provider_identity: str
    observer_identity: str
    emitter_identity: str
    authority_operands: tuple[SemanticOperand, ...]
    proposed_relations: tuple[ProposedRelation, ...]
    trusted_rules: tuple[TrustedSemanticRule, ...]
    frozen_generic_rule_ids: frozenset[str]
    authorized_source_rule_ids: frozenset[str]
    planner_payload_keys: frozenset[str]
    role_rules: tuple[FrozenSurfaceRoleRule, ...]


@dataclass(frozen=True, slots=True)
class QualifiedRuntimeBindingsV54:
    implementation_identity: str
    provider_identity: str
    observer_identity: str
    emitter_identity: str
    contract_identity: str


@dataclass(frozen=True, slots=True)
class ClosedIntegratedAuthorityV54:
    authority: FrozenIntegratedAuthorityV54
    licensed_plan: LicensedPlan
    byte_authority: FrozenExecutableAuthorityV533
    closure_identity: str


@dataclass(frozen=True, slots=True)
class TrustedIntegratedReceiptV54:
    closure_identity: str
    component_binding_identity: str
    byte_receipt: TrustedConformanceReceiptV533
    receipt_identity: str


def close_integrated_authority(authority: FrozenIntegratedAuthorityV54, *,
                               bindings: QualifiedRuntimeBindingsV54) -> ClosedIntegratedAuthorityV54:
    values = (authority.authority_identity, authority.implementation_identity,
              authority.release_binding_identity, authority.proposition_span_identity,
              authority.denyset_identity, authority.alignment_policy_identity)
    if not all(values):
        raise ValueError("incomplete integrated Class A authority")
    if authority.implementation_identity != bindings.implementation_identity:
        raise ValueError("integrated implementation identity skew")
    actual_components = (authority.provider_identity, authority.observer_identity,
                         authority.emitter_identity, authority.contract_identity)
    expected_components = (bindings.provider_identity, bindings.observer_identity,
                           bindings.emitter_identity, bindings.contract_identity)
    if not all(expected_components) or actual_components != expected_components:
        raise ValueError("provider observer emitter or contract identity skew")
    rules = {rule.rule_id: rule for rule in authority.trusted_rules}
    assert_registry_is_external(registry_rules=rules, planner_payload_keys=authority.planner_payload_keys)
    verify_rule_registry_partition(rules=authority.trusted_rules,
        frozen_generic_rule_ids=authority.frozen_generic_rule_ids,
        authorized_source_rule_ids=authority.authorized_source_rule_ids)
    licensed = validate_and_license_plan(authority_operands=authority.authority_operands,
        proposed_relations=authority.proposed_relations, registry=TrustedRuleRegistry(authority.trusted_rules),
        authorized_source_rule_ids=authority.authorized_source_rule_ids)

    node_rules = tuple(FrozenNodeRelationRule(
        node_id=relation.relation_id,
        actor_identity=relation.actor_id,
        predicate_identity=relation.predicate_class,
        patient_identity=relation.patient_id,
        produced_identity=relation.result_id,
        terminal=relation.terminal,
        predecessor_node_id=relation.predecessor_relation_id,
    ) for relation in authority.proposed_relations)
    role_index = {(item.node_id, item.role): item for item in authority.role_rules}
    for node in node_rules:
        expected = {("ACTOR", node.actor_identity), ("PREDICATE", node.predicate_identity),
                    ("PATIENT", node.patient_identity), ("PRODUCED", node.produced_identity)}
        actual = {(role, role_index[(node.node_id, role)].semantic_identity)
                  for role in ("ACTOR", "PREDICATE", "PATIENT", "PRODUCED")
                  if (node.node_id, role) in role_index}
        if actual != expected:
            raise ValueError("byte-observation rules drift from licensed semantic plan")
    byte_authority = FrozenExecutableAuthorityV533(*values, authority.role_rules, node_rules)
    material = repr((authority, licensed, node_rules)).encode("utf-8")
    return ClosedIntegratedAuthorityV54(authority, licensed, byte_authority,
                                        hashlib.sha256(material).hexdigest())


def _component_binding(authority: FrozenIntegratedAuthorityV54) -> str:
    material = "|".join((authority.implementation_identity, authority.contract_identity,
                         authority.provider_identity, authority.observer_identity, authority.emitter_identity))
    return hashlib.sha256(material.encode()).hexdigest()


def conditional_integrated_emit(*, closed: ClosedIntegratedAuthorityV54, surface_bytes: bytes,
                                receipt: TrustedIntegratedReceiptV54) -> bytes:
    expected_component = _component_binding(closed.authority)
    if receipt.closure_identity != closed.closure_identity or receipt.component_binding_identity != expected_component:
        raise ValueError("emitter receipt does not bind the licensed closure and exact components")
    core = "|".join((receipt.closure_identity, receipt.component_binding_identity,
                     receipt.byte_receipt.receipt_identity))
    if receipt.receipt_identity != hashlib.sha256(core.encode()).hexdigest():
        raise ValueError("integrated receipt identity mismatch")
    return conditional_emit(authority=closed.byte_authority, surface_bytes=surface_bytes,
                            receipt=receipt.byte_receipt)


def execute_zero_family_path(*, closed: ClosedIntegratedAuthorityV54,
                             provider_payload: Mapping[str, Any]) -> tuple[bytes, TrustedIntegratedReceiptV54]:
    """Synthetic qualification entry point; it represents no family capability."""
    surface = invoke_clause_only_provider(provider_payload)
    byte_receipt = observe_and_conform_surface(authority=closed.byte_authority, surface_bytes=surface)
    component = _component_binding(closed.authority)
    core = "|".join((closed.closure_identity, component, byte_receipt.receipt_identity))
    receipt = TrustedIntegratedReceiptV54(closed.closure_identity, component, byte_receipt,
                                          hashlib.sha256(core.encode()).hexdigest())
    return conditional_integrated_emit(closed=closed, surface_bytes=surface, receipt=receipt), receipt


__all__ = ["ClosedIntegratedAuthorityV54", "FrozenIntegratedAuthorityV54", "QualifiedRuntimeBindingsV54",
           "TrustedIntegratedReceiptV54", "close_integrated_authority", "conditional_integrated_emit",
           "execute_zero_family_path"]
