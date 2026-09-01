from dataclasses import replace
import pytest

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_1_runtime import AlignedSemanticNodeLexicalization
from pastila_scout.humor_batch2_development_constructor_v5_3_2_runtime import bind_frozen_causal_rules
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import EdgeNecessityWitness

def fixture():
    plan=(TypedPlanNode("L1","A","RELATION_HEAD","P1","B",(),("X",),"P5",True),
          TypedPlanNode("RESULT","X","RELATION_HEAD","P2","A",("L1",),(),"L1",True))
    edge=(EdgeNecessityWitness("L1","RESULT","X","ACTOR","RULE_EXACT",True,True),)
    base=AlignedSemanticNodeLexicalization("L1","a p b","a","a","EXACT_NFKC_CASEFOLD","p","p","EXACT_NFKC_CASEFOLD","b","b","EXACT_NFKC_CASEFOLD",(("X","x"),),False,(),(),(),(),())
    result=AlignedSemanticNodeLexicalization("RESULT","x q a","x","x","EXACT_NFKC_CASEFOLD","q","q","EXACT_NFKC_CASEFOLD","a","a","EXACT_NFKC_CASEFOLD",(),True,(),(),(),(),())
    return plan,edge,(base,result)

def test_rule_is_derived_from_frozen_edge_when_provider_omits_it():
    plan,edge,items=fixture()
    assert bind_frozen_causal_rules(typed_plan=plan,edge_witnesses=edge,lexicalizations=items)[1].predecessor_causal_rule_ids==("RULE_EXACT",)

def test_pilot12_wrong_rule_alias_fails_before_realization():
    plan,edge,items=fixture(); bad=items[:-1]+(replace(items[-1],predecessor_causal_rule_ids=("RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",)),)
    with pytest.raises(ValueError,match="causal-rule witness differs"):
        bind_frozen_causal_rules(typed_plan=plan,edge_witnesses=edge,lexicalizations=bad)
