"""V5.3.2 guard: bind realized predecessor rules to frozen edge witnesses."""
from __future__ import annotations

from dataclasses import replace

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_1_runtime import (
    AlignedSemanticNodeLexicalization, AlignedSemanticRealizationDraft,
    emit_aligned_semantic_candidate_utf8, realize_aligned_semantic_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature,
)

def bind_frozen_causal_rules(
    *, typed_plan: tuple[TypedPlanNode, ...], edge_witnesses: tuple[EdgeNecessityWitness, ...],
    lexicalizations: tuple[AlignedSemanticNodeLexicalization, ...],
) -> tuple[AlignedSemanticNodeLexicalization, ...]:
    """Derive rule IDs from the validated edge set; never trust provider aliases."""
    edge_rules={(edge.predecessor_node_id,edge.successor_node_id):edge.explicit_licensing_rule for edge in edge_witnesses}
    by_node={item.node_id:item for item in lexicalizations}
    if len(by_node)!=len(lexicalizations) or set(by_node)!={node.node_id for node in typed_plan}:
        raise ValueError("provider lexicalization coverage differs from frozen plan")
    bound=[]
    for node in typed_plan:
        expected=tuple(edge_rules[(parent,node.node_id)] for parent in node.predecessor_node_ids)
        supplied=by_node[node.node_id].predecessor_causal_rule_ids
        if supplied and supplied!=expected:
            raise ValueError("provider causal-rule witness differs from frozen edge identity")
        bound.append(replace(by_node[node.node_id],predecessor_causal_rule_ids=expected))
    return tuple(bound)

def realize_frozen_rule_aligned_plan(
    *, exact_source: str, typed_plan: tuple[TypedPlanNode, ...], operand_specs: tuple[OperandSemanticSpec,...],
    predicate_signatures: tuple[PredicateSemanticSignature,...], edge_witnesses: tuple[EdgeNecessityWitness,...],
    lexicalizations: tuple[AlignedSemanticNodeLexicalization,...],
) -> AlignedSemanticRealizationDraft:
    bound=bind_frozen_causal_rules(typed_plan=typed_plan,edge_witnesses=edge_witnesses,lexicalizations=lexicalizations)
    return realize_aligned_semantic_typed_plan(exact_source=exact_source,typed_plan=typed_plan,
        operand_specs=operand_specs,predicate_signatures=predicate_signatures,edge_witnesses=edge_witnesses,
        lexicalizations=bound)

__all__=["bind_frozen_causal_rules","realize_frozen_rule_aligned_plan","emit_aligned_semantic_candidate_utf8"]
