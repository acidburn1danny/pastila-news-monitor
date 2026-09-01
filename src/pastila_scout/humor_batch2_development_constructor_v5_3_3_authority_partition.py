"""Authority-partitioned provider boundary: A derived, B observed, C creative."""
from __future__ import annotations
from dataclasses import dataclass

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_1_runtime import AlignedSemanticNodeLexicalization
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import EdgeNecessityWitness, OperandSemanticSpec

@dataclass(frozen=True,slots=True)
class ProviderCreativeRealization:
    """The complete Class C schema; it contains no authoritative IDs or claims."""
    clause: str
    actor_surface: str
    predicate_surface: str
    patient_surface: str
    produced_operand_surfaces: tuple[str,...]

def derive_authority_bound_lexicalizations(*,typed_plan:tuple[TypedPlanNode,...],operand_specs:tuple[OperandSemanticSpec,...],
        edge_witnesses:tuple[EdgeNecessityWitness,...],creative:tuple[ProviderCreativeRealization,...]
        )->tuple[AlignedSemanticNodeLexicalization,...]:
    """Build the mixed runtime structure at the trusted boundary, never in provider space."""
    if len(creative)!=len(typed_plan): raise ValueError("creative realization coverage must equal frozen plan N/N")
    specs={item.operand_id:item for item in operand_specs}
    edge_rules={(edge.predecessor_node_id,edge.successor_node_id):edge.explicit_licensing_rule for edge in edge_witnesses}
    result=[]
    for index,(node,item) in enumerate(zip(typed_plan,creative,strict=True)):
        if not all(value and value.strip() for value in (item.clause,item.actor_surface,item.predicate_surface,item.patient_surface)):
            raise ValueError("empty creative surface field")
        if len(item.produced_operand_surfaces)!=len(node.introduces_ids):
            raise ValueError("produced surface count differs from frozen plan")
        actor,patient=specs[node.bound_actor_id],specs[node.bound_patient_id]
        rules=tuple(edge_rules[(parent,node.node_id)] for parent in node.predecessor_node_ids)
        result.append(AlignedSemanticNodeLexicalization(
            node.node_id,item.clause,item.actor_surface,item.actor_surface,"EXACT_NFKC_CASEFOLD",
            item.predicate_surface,item.predicate_surface,"EXACT_NFKC_CASEFOLD",
            item.patient_surface,item.patient_surface,"EXACT_NFKC_CASEFOLD",
            tuple(zip(node.introduces_ids,item.produced_operand_surfaces,strict=True)),index==len(typed_plan)-1,
            actor.semantic_roles,actor.affordances,patient.semantic_roles,patient.affordances,rules))
    return tuple(result)

__all__=["ProviderCreativeRealization","derive_authority_bound_lexicalizations"]
