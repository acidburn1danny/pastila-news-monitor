"""Mechanism-neutral plan-to-surface enforcement for Constructor V5.2.

This module does not realize or emit candidate text.  It validates a proposed
realization draft against a previously validated typed plan and fails closed
before candidate emission when any node, edge, operand, or terminal witness is
missing, collapsed, merely asserted, or expressed as governance meta-language.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode


@dataclass(frozen=True, slots=True)
class SurfaceNodeWitness:
    node_id: str
    character_start: int
    character_end: int
    actor_operand_id: str
    actor_surface: str
    predicate_id: str
    predicate_surface: str
    patient_operand_id: str
    patient_surface: str
    predecessor_node_ids: tuple[str, ...]
    produced_operand_surfaces: tuple[tuple[str, str], ...]
    terminal_result: bool


@dataclass(frozen=True, slots=True)
class RealizationDraft:
    surface: str
    node_witnesses: tuple[SurfaceNodeWitness, ...]


@dataclass(frozen=True, slots=True)
class RealizationCoverage:
    nodes_realized: int
    nodes_required: int
    edges_realized: int
    edges_required: int
    terminal_result_realized: bool


_META_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:dou[aă]|[0-9]+)\s+(?:consecin(?:țe|te)|legături|relații)\b",
        r"\b(?:traseu|lanț|structur[ăa])\s+(?:inventat|cauzal|complet)\b",
        r"\brelația\s+continuă\b",
        r"\b(?:consecința|rezultatul)\s+depinde\s+de\s+(?:întregul|tot)\b",
        r"\b(?:nod|operand|predecesor|witness|plan)\b",
    )
)


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def validate_realization_draft(
    plan: tuple[TypedPlanNode, ...],
    draft: RealizationDraft,
) -> RealizationCoverage:
    """Require complete, explicit plan witnesses before candidate emission."""
    if not plan or not draft.surface:
        raise ValueError("missing plan or surface")
    if any(pattern.search(draft.surface) for pattern in _META_PATTERNS):
        raise ValueError("instruction or plan meta-language substitutes for realization")
    if not draft.node_witnesses:
        raise ValueError("missing plan or surface witnesses")

    planned = {node.node_id: node for node in plan}
    witnessed = {witness.node_id: witness for witness in draft.node_witnesses}
    if len(witnessed) != len(draft.node_witnesses) or set(witnessed) != set(planned):
        raise ValueError("incomplete or duplicate N/N node realization coverage")

    produced_surface: dict[str, str] = {}
    realized_edges: set[tuple[str, str]] = set()
    required_edges = {
        (parent, node.node_id)
        for node in plan
        for parent in node.predecessor_node_ids
    }
    for node in plan:
        witness = witnessed[node.node_id]
        if not (0 <= witness.character_start < witness.character_end <= len(draft.surface)):
            raise ValueError("invalid surface witness coordinates")
        fragment = draft.surface[witness.character_start:witness.character_end]
        if not all(_norm(value) in _norm(fragment) for value in (
            witness.actor_surface, witness.predicate_surface, witness.patient_surface
        )):
            raise ValueError("typed actor predicate or patient lacks an explicit surface witness")
        if (
            witness.actor_operand_id != node.bound_actor_id
            or witness.patient_operand_id != node.bound_patient_id
            or witness.predicate_id != node.predicate_id
            or witness.predecessor_node_ids != node.predecessor_node_ids
        ):
            raise ValueError("surface witness disagrees with typed plan")
        for predecessor in witness.predecessor_node_ids:
            realized_edges.add((predecessor, witness.node_id))
        for operand_id, surface_form in witness.produced_operand_surfaces:
            if operand_id not in node.introduces_ids or not surface_form.strip() or _norm(surface_form) not in _norm(fragment):
                raise ValueError("produced operand lacks an explicit local witness")
            if operand_id in produced_surface:
                raise ValueError("produced operand has multiple surface producers")
            produced_surface[operand_id] = surface_form
        if node.bound_actor_id.startswith("INVENTED_"):
            prior = produced_surface.get(node.bound_actor_id)
            if prior is None or _norm(prior) != _norm(witness.actor_surface):
                raise ValueError("typed invented actor continuity is not explicit")
        if node.bound_patient_id.startswith("INVENTED_"):
            prior = produced_surface.get(node.bound_patient_id)
            if prior is None or _norm(prior) != _norm(witness.patient_surface):
                raise ValueError("typed invented patient continuity is not explicit")

    if realized_edges != required_edges:
        raise ValueError("incomplete E/E causal-edge realization coverage")
    terminals = [w for w in draft.node_witnesses if w.terminal_result]
    if len(terminals) != 1 or terminals[0].node_id != plan[-1].node_id:
        raise ValueError("terminal result lacks a unique explicit surface witness")
    if len(plan) < 3 or len(required_edges) < 2:
        raise ValueError("multi-link causal spine is incomplete")
    return RealizationCoverage(len(witnessed), len(planned), len(realized_edges), len(required_edges), True)


__all__ = ["SurfaceNodeWitness", "RealizationDraft", "RealizationCoverage", "validate_realization_draft"]
