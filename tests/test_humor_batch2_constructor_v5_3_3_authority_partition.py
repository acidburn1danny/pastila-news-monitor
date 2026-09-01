from dataclasses import fields
import pytest
from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_3_authority_partition import ProviderCreativeRealization,derive_authority_bound_lexicalizations
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import EdgeNecessityWitness,OperandSemanticSpec

def test_provider_schema_contains_only_genuinely_creative_fields():
    assert {f.name for f in fields(ProviderCreativeRealization)}=={"clause","actor_surface","predicate_surface","patient_surface","produced_operand_surfaces"}

def test_all_authoritative_metadata_is_derived_from_frozen_state():
    plan=(TypedPlanNode("L1","A","RELATION_HEAD","P1","B",(),("X",),"P5",True),TypedPlanNode("RESULT","X","RELATION_HEAD","P2","A",("L1",),(),"L1",True))
    specs=(OperandSemanticSpec("A","EA",("RA",),("AA",),(),False),OperandSemanticSpec("B","EB",("RB",),("AB",),(),False),OperandSemanticSpec("X","EX",("RX",),("AX",),("A","B"),False))
    edges=(EdgeNecessityWitness("L1","RESULT","X","ACTOR","RULE_EXACT",True,True),)
    creative=(ProviderCreativeRealization("a p b x","a","p","b",("x",)),ProviderCreativeRealization("x q a","x","q","a",()))
    result=derive_authority_bound_lexicalizations(typed_plan=plan,operand_specs=specs,edge_witnesses=edges,creative=creative)
    assert result[0].node_id=="L1" and result[0].actor_semantic_roles==("RA",) and not result[0].terminal_result
    assert result[1].predecessor_causal_rule_ids==("RULE_EXACT",) and result[1].terminal_result

def test_impossible_produced_operand_shape_fails_pre_invocation():
    plan=(TypedPlanNode("L1","A","RELATION_HEAD","P1","B",(),("X",),"P5",True),)
    specs=(OperandSemanticSpec("A","EA",(),(),(),False),OperandSemanticSpec("B","EB",(),(),(),False))
    with pytest.raises(ValueError,match="produced surface count"):
        derive_authority_bound_lexicalizations(typed_plan=plan,operand_specs=specs,edge_witnesses=(),creative=(ProviderCreativeRealization("a p b","a","p","b",()),))
