"""Pathless V5.3.1 provider/emitter integration with coordinate-bound alignment."""

from __future__ import annotations

from dataclasses import dataclass
import re

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_2 import RealizationDraft
from pastila_scout.humor_batch2_development_constructor_v5_2_runtime import NodeLexicalization, realize_typed_plan
from pastila_scout.humor_batch2_development_constructor_v5_3_1_surface_alignment import (
    CoordinateBoundRoleWitness, validate_node_role_alignment,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature,
    SurfaceSemanticWitness, validate_semantic_plan, validate_surface_semantics,
)


@dataclass(frozen=True, slots=True)
class AlignedSemanticNodeLexicalization:
    node_id: str
    clause: str
    actor_surface: str
    actor_canonical_form: str
    actor_alignment_rule: str
    predicate_surface: str
    predicate_canonical_form: str
    predicate_alignment_rule: str
    patient_surface: str
    patient_canonical_form: str
    patient_alignment_rule: str
    produced_operand_surfaces: tuple[tuple[str, str], ...]
    terminal_result: bool
    actor_semantic_roles: tuple[str, ...]
    actor_affordances: tuple[str, ...]
    patient_semantic_roles: tuple[str, ...]
    patient_affordances: tuple[str, ...]
    predecessor_causal_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlignedSemanticRealizationDraft:
    structural_draft: RealizationDraft
    semantic_witnesses: tuple[SurfaceSemanticWitness, ...]
    coordinate_role_witnesses: tuple[CoordinateBoundRoleWitness, ...]


_META = re.compile(r"\b(?:nod|operand|predecesor|witness|plan|guvernan[țţ]|conforman[țţ])\b", re.IGNORECASE)


def _unique_local_span(clause: str, surface_form: str) -> tuple[int, int]:
    start = clause.find(surface_form)
    if start < 0 or clause.find(surface_form, start + 1) >= 0:
        raise ValueError("semantic role genuinely missing or ambiguous in realized clause")
    return start, start + len(surface_form)


def _coordinate_witness(*, complete_surface: str, clause_start: int, lexical: AlignedSemanticNodeLexicalization,
                        role: str, identity: str, surface_form: str, canonical_form: str,
                        alignment_rule: str) -> CoordinateBoundRoleWitness:
    local_start, local_end = _unique_local_span(lexical.clause.strip(), surface_form)
    start, end = clause_start + local_start, clause_start + local_end
    byte_start = len(complete_surface[:start].encode("utf-8"))
    byte_end = len(complete_surface[:end].encode("utf-8"))
    return CoordinateBoundRoleWitness(lexical.node_id, role, identity, start, end, byte_start, byte_end,
                                      surface_form, canonical_form, alignment_rule)


def _validate_aligned_structure(*, typed_plan: tuple[TypedPlanNode, ...], draft: AlignedSemanticRealizationDraft) -> None:
    surface, witnesses = draft.structural_draft.surface, draft.structural_draft.node_witnesses
    if not surface or _META.search(surface):
        raise ValueError("missing surface or prohibited instruction/governance/plan language")
    planned, observed = {node.node_id: node for node in typed_plan}, {item.node_id: item for item in witnesses}
    if len(observed) != len(witnesses) or set(observed) != set(planned):
        raise ValueError("incomplete N/N node coverage")
    produced, realized_edges = {}, set()
    for node in typed_plan:
        item = observed[node.node_id]
        if (item.actor_operand_id != node.bound_actor_id or item.predicate_id != node.predicate_id
                or item.patient_operand_id != node.bound_patient_id or item.predecessor_node_ids != node.predecessor_node_ids):
            raise ValueError("typed node identity mismatch")
        for parent in item.predecessor_node_ids:
            realized_edges.add((parent, item.node_id))
        fragment = surface[item.character_start:item.character_end].casefold()
        for operand_id, surface_form in item.produced_operand_surfaces:
            if operand_id not in node.introduces_ids or surface_form.casefold() not in fragment or operand_id in produced:
                raise ValueError("produced operand lacks unique explicit surface evidence")
            produced[operand_id] = surface_form.casefold()
        if node.bound_actor_id.startswith("INVENTED_") and produced.get(node.bound_actor_id) != item.actor_surface.casefold():
            raise ValueError("invented actor continuity missing")
        if node.bound_patient_id.startswith("INVENTED_") and produced.get(node.bound_patient_id) != item.patient_surface.casefold():
            raise ValueError("invented patient continuity missing")
    required_edges = {(parent, node.node_id) for node in typed_plan for parent in node.predecessor_node_ids}
    if realized_edges != required_edges:
        raise ValueError("incomplete E/E edge coverage")
    terminals = [item for item in witnesses if item.terminal_result]
    if len(terminals) != 1 or terminals[0].node_id != typed_plan[-1].node_id:
        raise ValueError("terminal result witness")
    validate_node_role_alignment(surface=surface, typed_plan=typed_plan, witnesses=draft.coordinate_role_witnesses)


def realize_aligned_semantic_typed_plan(
    *, exact_source: str, typed_plan: tuple[TypedPlanNode, ...], operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...], edge_witnesses: tuple[EdgeNecessityWitness, ...],
    lexicalizations: tuple[AlignedSemanticNodeLexicalization, ...],
) -> AlignedSemanticRealizationDraft:
    validate_semantic_plan(typed_plan=typed_plan, operand_specs=operand_specs,
                           predicate_signatures=predicate_signatures, edge_witnesses=edge_witnesses)
    structural = tuple(NodeLexicalization(item.node_id, item.clause, item.actor_surface, item.predicate_surface,
                                          item.patient_surface, item.produced_operand_surfaces, item.terminal_result)
                       for item in lexicalizations)
    structural_draft = realize_typed_plan(exact_source=exact_source, typed_plan=typed_plan, lexicalizations=structural)
    by_node = {item.node_id: item for item in lexicalizations}
    structural_by_node = {item.node_id: item for item in structural_draft.node_witnesses}
    semantic, coordinates = [], []
    for node in typed_plan:
        item, structural_item = by_node[node.node_id], structural_by_node[node.node_id]
        semantic.append(SurfaceSemanticWitness(node.node_id, node.bound_actor_id, item.actor_semantic_roles,
                        item.actor_affordances, node.predicate_id, node.bound_patient_id,
                        item.patient_semantic_roles, item.patient_affordances, item.predecessor_causal_rule_ids))
        for role, identity, surface_form, canonical_form, rule in (
            ("ACTOR", node.bound_actor_id, item.actor_surface, item.actor_canonical_form, item.actor_alignment_rule),
            ("PREDICATE", node.predicate_id, item.predicate_surface, item.predicate_canonical_form, item.predicate_alignment_rule),
            ("PATIENT", node.bound_patient_id, item.patient_surface, item.patient_canonical_form, item.patient_alignment_rule),
        ):
            coordinates.append(_coordinate_witness(complete_surface=structural_draft.surface,
                               clause_start=structural_item.character_start, lexical=item, role=role, identity=identity,
                               surface_form=surface_form, canonical_form=canonical_form, alignment_rule=rule))
    result = AlignedSemanticRealizationDraft(structural_draft, tuple(semantic), tuple(coordinates))
    validate_surface_semantics(typed_plan=typed_plan, operand_specs=operand_specs,
                               predicate_signatures=predicate_signatures, edge_witnesses=edge_witnesses,
                               surface_witnesses=result.semantic_witnesses)
    _validate_aligned_structure(typed_plan=typed_plan, draft=result)
    return result


def emit_aligned_semantic_candidate_utf8(
    *, typed_plan: tuple[TypedPlanNode, ...], operand_specs: tuple[OperandSemanticSpec, ...],
    predicate_signatures: tuple[PredicateSemanticSignature, ...], edge_witnesses: tuple[EdgeNecessityWitness, ...],
    draft: AlignedSemanticRealizationDraft,
) -> bytes:
    validate_surface_semantics(typed_plan=typed_plan, operand_specs=operand_specs,
                               predicate_signatures=predicate_signatures, edge_witnesses=edge_witnesses,
                               surface_witnesses=draft.semantic_witnesses)
    _validate_aligned_structure(typed_plan=typed_plan, draft=draft)
    return (draft.structural_draft.surface.rstrip("\n") + "\n").encode("utf-8")


__all__ = ["AlignedSemanticNodeLexicalization", "AlignedSemanticRealizationDraft",
           "realize_aligned_semantic_typed_plan", "emit_aligned_semantic_candidate_utf8"]
