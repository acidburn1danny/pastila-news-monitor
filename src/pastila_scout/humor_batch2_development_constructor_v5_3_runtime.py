"""Pathless V5.3 semantic provider/emitter integration.

This wrapper adds semantic edge and operand-role enforcement around the frozen
V5.2 structural realization path.  It carries no release authority and does
not perform filesystem, process, network, or model access.
"""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_2 import RealizationDraft
from pastila_scout.humor_batch2_development_constructor_v5_2_runtime import (
    NodeLexicalization,
    emit_candidate_utf8,
    realize_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness,
    OperandSemanticSpec,
    PredicateSemanticSignature,
    SurfaceSemanticWitness,
    validate_semantic_plan,
    validate_surface_semantics,
)


@dataclass(frozen=True, slots=True)
class SemanticNodeLexicalization:
    node_id: str
    clause: str
    actor_surface: str
    predicate_surface: str
    patient_surface: str
    produced_operand_surfaces: tuple[tuple[str, str], ...]
    terminal_result: bool
    actor_semantic_roles: tuple[str, ...]
    actor_affordances: tuple[str, ...]
    patient_semantic_roles: tuple[str, ...]
    patient_affordances: tuple[str, ...]
    predecessor_causal_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticRealizationDraft:
    structural_draft: RealizationDraft
    semantic_witnesses: tuple[SurfaceSemanticWitness, ...]


def realize_semantic_typed_plan(
    *,
    exact_source: str,
    typed_plan: tuple[TypedPlanNode, ...],
    operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...],
    edge_witnesses: tuple[EdgeNecessityWitness, ...],
    lexicalizations: tuple[SemanticNodeLexicalization, ...],
) -> SemanticRealizationDraft:
    """Validate semantics, realize structurally, then bind surface semantics."""
    validate_semantic_plan(
        typed_plan=typed_plan,
        operand_specs=operand_specs,
        predicate_signatures=predicate_signatures,
        edge_witnesses=edge_witnesses,
    )
    structural_lexicalizations = tuple(NodeLexicalization(
        node_id=item.node_id,
        clause=item.clause,
        actor_surface=item.actor_surface,
        predicate_surface=item.predicate_surface,
        patient_surface=item.patient_surface,
        produced_operand_surfaces=item.produced_operand_surfaces,
        terminal_result=item.terminal_result,
    ) for item in lexicalizations)
    structural_draft = realize_typed_plan(
        exact_source=exact_source,
        typed_plan=typed_plan,
        lexicalizations=structural_lexicalizations,
    )
    by_node = {item.node_id: item for item in lexicalizations}
    if len(by_node) != len(lexicalizations) or set(by_node) != {node.node_id for node in typed_plan}:
        raise ValueError("semantic lexicalization coverage must equal plan N/N")
    semantic_witnesses = tuple(SurfaceSemanticWitness(
        node_id=node.node_id,
        actor_operand_id=node.bound_actor_id,
        actor_semantic_roles=by_node[node.node_id].actor_semantic_roles,
        actor_affordances=by_node[node.node_id].actor_affordances,
        predicate_id=node.predicate_id,
        patient_operand_id=node.bound_patient_id,
        patient_semantic_roles=by_node[node.node_id].patient_semantic_roles,
        patient_affordances=by_node[node.node_id].patient_affordances,
        predecessor_causal_rule_ids=by_node[node.node_id].predecessor_causal_rule_ids,
    ) for node in typed_plan)
    validate_surface_semantics(
        typed_plan=typed_plan,
        operand_specs=operand_specs,
        predicate_signatures=predicate_signatures,
        edge_witnesses=edge_witnesses,
        surface_witnesses=semantic_witnesses,
    )
    return SemanticRealizationDraft(structural_draft, semantic_witnesses)


def emit_semantic_candidate_utf8(
    *,
    typed_plan: tuple[TypedPlanNode, ...],
    operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...],
    edge_witnesses: tuple[EdgeNecessityWitness, ...],
    draft: SemanticRealizationDraft,
) -> bytes:
    """Revalidate semantic witnesses before delegating to byte emission."""
    validate_surface_semantics(
        typed_plan=typed_plan,
        operand_specs=operand_specs,
        predicate_signatures=predicate_signatures,
        edge_witnesses=edge_witnesses,
        surface_witnesses=draft.semantic_witnesses,
    )
    return emit_candidate_utf8(typed_plan=typed_plan, draft=draft.structural_draft)


__all__ = ["SemanticNodeLexicalization", "SemanticRealizationDraft",
           "realize_semantic_typed_plan", "emit_semantic_candidate_utf8"]
