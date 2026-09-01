"""Mechanism-neutral semantic role and causal-edge enforcement for Constructor V5.3.

This module does not construct text. It validates semantic plan annotations
before realization and validates matching role/necessity witnesses before an
emitter may persist candidate bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode


_PRIVILEGED_ROLES = frozenset({
    "AGENT", "AUTHORITY_HOLDER", "CAPABILITY_BEARER", "OWNER",
    "PERMISSION_GRANTER", "PROCEDURE_APPLIER",
})
_PRIVILEGED_AFFORDANCES = frozenset({
    "APPLY_PROCEDURE", "AUTHORIZE", "CONTROL", "DECIDE", "GRANT_PERMISSION",
    "MOVE_OTHER_ENTITY", "OWN",
})


@dataclass(frozen=True, slots=True)
class OperandSemanticSpec:
    operand_id: str
    entity_identity: str
    semantic_roles: tuple[str, ...]
    affordances: tuple[str, ...]
    provenance_operand_ids: tuple[str, ...]
    reclassification_only: bool


@dataclass(frozen=True, slots=True)
class PredicateSemanticSignature:
    predicate_id: str
    required_actor_roles: tuple[str, ...]
    required_patient_roles: tuple[str, ...]
    required_actor_affordances: tuple[str, ...]
    required_patient_affordances: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EdgeNecessityWitness:
    predecessor_node_id: str
    successor_node_id: str
    produced_operand_id: str
    consumed_position: str
    explicit_licensing_rule: str
    counterfactual_dependency: bool
    non_arbitrary: bool


@dataclass(frozen=True, slots=True)
class SurfaceSemanticWitness:
    node_id: str
    actor_operand_id: str
    actor_semantic_roles: tuple[str, ...]
    actor_affordances: tuple[str, ...]
    predicate_id: str
    patient_operand_id: str
    patient_semantic_roles: tuple[str, ...]
    patient_affordances: tuple[str, ...]
    predecessor_causal_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticCoverage:
    nodes_validated: int
    edges_validated: int
    terminal_edge_validated: bool


def _require_subset(required: tuple[str, ...], actual: tuple[str, ...], message: str) -> None:
    if not set(required).issubset(actual):
        raise ValueError(message)


def validate_semantic_plan(
    *,
    typed_plan: tuple[TypedPlanNode, ...],
    operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...],
    edge_witnesses: tuple[EdgeNecessityWitness, ...],
) -> SemanticCoverage:
    """Reject role-incompatible or arbitrary edges before realization."""
    if not typed_plan:
        raise ValueError("missing typed plan")
    specs = {item.operand_id: item for item in operand_specs}
    signatures = {item.predicate_id: item for item in predicate_signatures}
    edges = {(item.predecessor_node_id, item.successor_node_id): item for item in edge_witnesses}
    if len(specs) != len(operand_specs) or len(signatures) != len(predicate_signatures) or len(edges) != len(edge_witnesses):
        raise ValueError("duplicate semantic specification")
    planned_edges = {(parent, node.node_id) for node in typed_plan for parent in node.predecessor_node_ids}
    if set(edges) != planned_edges:
        raise ValueError("semantic edge coverage must equal typed plan E/E")

    for produced in operand_specs:
        if not produced.reclassification_only:
            continue
        if not produced.provenance_operand_ids:
            raise ValueError("reclassified operand lacks semantic provenance")
        inherited_roles: set[str] = set()
        inherited_affordances: set[str] = set()
        inherited_identities = set()
        for source_id in produced.provenance_operand_ids:
            source = specs.get(source_id)
            if source is None:
                raise ValueError("reclassification source operand unavailable")
            inherited_roles.update(source.semantic_roles)
            inherited_affordances.update(source.affordances)
            inherited_identities.add(source.entity_identity)
        if produced.entity_identity not in inherited_identities:
            raise ValueError("reclassification changed entity identity")
        if set(produced.semantic_roles).intersection(_PRIVILEGED_ROLES - inherited_roles):
            raise ValueError("reclassification cannot create agency authority capability ownership or procedural power")
        if set(produced.affordances).intersection(_PRIVILEGED_AFFORDANCES - inherited_affordances):
            raise ValueError("reclassification cannot create a privileged affordance")

    validated_edges = 0
    for node in typed_plan:
        actor = specs.get(node.bound_actor_id)
        patient = specs.get(node.bound_patient_id)
        signature = signatures.get(node.predicate_id)
        if actor is None or patient is None or signature is None:
            raise ValueError("missing operand semantic spec or predicate role signature")
        _require_subset(signature.required_actor_roles, actor.semantic_roles,
                        "actor semantic role is incompatible with predicate")
        _require_subset(signature.required_patient_roles, patient.semantic_roles,
                        "patient semantic role is incompatible with predicate")
        _require_subset(signature.required_actor_affordances, actor.affordances,
                        "actor lacks predicate-required agency authority capability or affordance")
        _require_subset(signature.required_patient_affordances, patient.affordances,
                        "patient lacks predicate-required affordance")
        for operand_id in node.introduces_ids:
            produced = specs.get(operand_id)
            if produced is None or not produced.provenance_operand_ids:
                raise ValueError("produced operand lacks semantic provenance")
        for parent in node.predecessor_node_ids:
            edge = edges[(parent, node.node_id)]
            if edge.consumed_position not in {"ACTOR", "PATIENT"}:
                raise ValueError("edge consumed position")
            consumed = node.bound_actor_id if edge.consumed_position == "ACTOR" else node.bound_patient_id
            if edge.produced_operand_id != consumed:
                raise ValueError("edge does not bind predecessor output to successor argument")
            if not edge.explicit_licensing_rule.strip() or not edge.counterfactual_dependency or not edge.non_arbitrary:
                raise ValueError("edge lacks explicit causal necessity and non-arbitrariness witness")
            validated_edges += 1
    return SemanticCoverage(len(typed_plan), validated_edges, bool(typed_plan[-1].predecessor_node_ids))


def validate_surface_semantics(
    *,
    typed_plan: tuple[TypedPlanNode, ...],
    operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...],
    edge_witnesses: tuple[EdgeNecessityWitness, ...],
    surface_witnesses: tuple[SurfaceSemanticWitness, ...],
) -> SemanticCoverage:
    """Require realized role/affordance witnesses to match the validated plan."""
    coverage = validate_semantic_plan(typed_plan=typed_plan, operand_specs=operand_specs,
                                      predicate_signatures=predicate_signatures, edge_witnesses=edge_witnesses)
    specs = {item.operand_id: item for item in operand_specs}
    witnessed = {item.node_id: item for item in surface_witnesses}
    if len(witnessed) != len(surface_witnesses) or set(witnessed) != {node.node_id for node in typed_plan}:
        raise ValueError("surface semantic witness coverage must equal plan N/N")
    edge_rules = {(edge.predecessor_node_id, edge.successor_node_id): edge.explicit_licensing_rule
                  for edge in edge_witnesses}
    for node in typed_plan:
        witness = witnessed[node.node_id]
        actor, patient = specs[node.bound_actor_id], specs[node.bound_patient_id]
        expected_rules = tuple(edge_rules[(parent, node.node_id)] for parent in node.predecessor_node_ids)
        if (witness.actor_operand_id != node.bound_actor_id or witness.predicate_id != node.predicate_id
                or witness.patient_operand_id != node.bound_patient_id
                or witness.actor_semantic_roles != actor.semantic_roles
                or witness.actor_affordances != actor.affordances
                or witness.patient_semantic_roles != patient.semantic_roles
                or witness.patient_affordances != patient.affordances
                or witness.predecessor_causal_rule_ids != expected_rules):
            raise ValueError("realized semantic roles affordances or causal rule differ from validated plan")
    return coverage


__all__ = ["OperandSemanticSpec", "PredicateSemanticSignature", "EdgeNecessityWitness",
           "SurfaceSemanticWitness", "SemanticCoverage", "validate_semantic_plan", "validate_surface_semantics"]
