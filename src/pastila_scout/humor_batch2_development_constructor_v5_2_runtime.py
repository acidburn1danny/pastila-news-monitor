"""Pathless realization-provider and candidate-emitter implementation for V5.2.

No release authority is embedded here.  A caller must supply one concrete,
plan-bound lexicalization per typed node.  The provider constructs exact surface
witnesses; the emitter validates the complete draft before returning UTF-8.
"""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_2 import (
    RealizationDraft,
    SurfaceNodeWitness,
    validate_realization_draft,
)


@dataclass(frozen=True, slots=True)
class NodeLexicalization:
    node_id: str
    clause: str
    actor_surface: str
    predicate_surface: str
    patient_surface: str
    produced_operand_surfaces: tuple[tuple[str, str], ...]
    terminal_result: bool


def realize_typed_plan(
    *,
    exact_source: str,
    typed_plan: tuple[TypedPlanNode, ...],
    lexicalizations: tuple[NodeLexicalization, ...],
) -> RealizationDraft:
    """Materialize all typed plan nodes into explicit, coordinate-bound clauses."""
    if not exact_source or not exact_source.strip():
        raise ValueError("exact source is required")
    by_node = {item.node_id: item for item in lexicalizations}
    if len(by_node) != len(lexicalizations) or set(by_node) != {node.node_id for node in typed_plan}:
        raise ValueError("lexicalization coverage must equal typed plan N/N")

    surface = exact_source.rstrip("\n")
    witnesses: list[SurfaceNodeWitness] = []
    for node in typed_plan:
        lexical = by_node[node.node_id]
        clause = lexical.clause.strip()
        if not clause:
            raise ValueError("empty node lexicalization")
        separator = " " if surface else ""
        start = len(surface) + len(separator)
        surface += separator + clause
        end = len(surface)
        witnesses.append(SurfaceNodeWitness(
            node_id=node.node_id,
            character_start=start,
            character_end=end,
            actor_operand_id=node.bound_actor_id,
            actor_surface=lexical.actor_surface,
            predicate_id=node.predicate_id,
            predicate_surface=lexical.predicate_surface,
            patient_operand_id=node.bound_patient_id,
            patient_surface=lexical.patient_surface,
            predecessor_node_ids=node.predecessor_node_ids,
            produced_operand_surfaces=lexical.produced_operand_surfaces,
            terminal_result=lexical.terminal_result,
        ))
    return RealizationDraft(surface=surface, node_witnesses=tuple(witnesses))


def emit_candidate_utf8(
    *,
    typed_plan: tuple[TypedPlanNode, ...],
    draft: RealizationDraft,
) -> bytes:
    """Fail closed on realization conformance before emitting candidate bytes."""
    coverage = validate_realization_draft(typed_plan, draft)
    required_edges = sum(len(node.predecessor_node_ids) for node in typed_plan)
    if (
        coverage.nodes_realized != coverage.nodes_required
        or coverage.nodes_required != len(typed_plan)
        or coverage.edges_realized != coverage.edges_required
        or coverage.edges_required != required_edges
        or not coverage.terminal_result_realized
    ):
        raise ValueError("realization coverage disagrees with typed plan")
    return (draft.surface.rstrip("\n") + "\n").encode("utf-8")


__all__ = ["NodeLexicalization", "realize_typed_plan", "emit_candidate_utf8"]
