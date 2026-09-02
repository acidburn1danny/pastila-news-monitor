import json
from copy import deepcopy
import pytest
from pastila_scout.relation_contract_v2 import SPECS,adjudicate,candidate_identity,evidence_identity,validate_composition
from pastila_scout.relation_contract_v2_qualification import candidate,evidence,reviews,qualify

def test_positive_17_of_17_and_negative_7_of_7():
 q=qualify(); assert all(x["verdict"]=="PASS_ZERO_FAMILY_DIAGNOSTIC" for x in q["positives"].values()); assert all(x["verdict"]=="FAIL_CLOSED" for x in q["negatives"].values())

@pytest.mark.parametrize("rc",SPECS)
def test_evidence_free_pass_impossible(rc):
 c=candidate(rc); assert adjudicate(c,[],reviews(c,[]))["verdict"]=="FAIL_CLOSED"

@pytest.mark.parametrize("rc",SPECS)
def test_identity_and_relation_switch_invalidate_evidence(rc):
 c=candidate(rc);es=evidence(c); switched=deepcopy(c); switched["relation_class"]=next(k for k in SPECS if k!=rc); switched["candidate_identity"]=candidate_identity(switched)
 assert adjudicate(switched,es,reviews(c,es))["verdict"]=="FAIL_CLOSED"

def test_canonical_identity_ignores_mapping_order_only():
 c=candidate("CAUSAL"); assert candidate_identity(c)==candidate_identity(dict(reversed(list(c.items()))))

def test_unrelated_evidence_cannot_authorize_candidate():
 a=candidate("CAUSAL");b=candidate("TRIGGER");es=evidence(a);assert adjudicate(b,es,reviews(b,es))["verdict"]=="FAIL_CLOSED"

def test_legitimate_alternative_allowed_arbitrary_rejected():
 c=candidate("PHYSICAL_ACTION");es=evidence(c);assert adjudicate(c,es,reviews(c,es))["verdict"].startswith("PASS")
 c["arbitrary_substitution_rejected"]=False;c["candidate_identity"]=candidate_identity(c);assert adjudicate(c,es,reviews(c,es))["verdict"]=="FAIL_CLOSED"

def test_cross_class_boundary_is_typed_and_never_inherits_affordance():
 a=candidate("MEASUREMENT");b=candidate("RECORDING_EVIDENTIARY");boundary={"from_candidate":candidate_identity(a),"to_candidate":candidate_identity(b),"from_class":a["relation_class"],"to_class":b["relation_class"],"continuity":SPECS[b["relation_class"]].continuity,"authority_identity":"BOUNDARY","inherits_affordances":False}; assert not validate_composition(a,b,boundary)
 boundary["inherits_affordances"]=True;assert "HIDDEN_AFFORDANCE_INHERITANCE" in validate_composition(a,b,boundary)

def test_pass_reviews_without_substantive_evidence_fail():
 c=candidate("LOGICAL_INFERENCE"); assert adjudicate(c,[],reviews(c,[]))["evidence_path"]==[]

def test_unconditional_universal_rejection_absent():
    q=qualify();assert len({tuple(x["blockers"]) for x in q["positives"].values()})==1 and next(iter(q["positives"].values()))["blockers"]==()

@pytest.mark.parametrize("rc",["NORMATIVE_AUTHORIZATION","LOGICAL_INFERENCE","REPRESENTATIONAL","MEASUREMENT","TEMPORAL","INFORMATION_TRANSFER"])
def test_class_specific_evidence_kind_mismatch_fails(rc):
    c=candidate(rc);es=evidence(c);es[0]["kind"]="wrong_kind";es[0]["evidence_identity"]=evidence_identity(es[0])
    assert adjudicate(c,es,reviews(c,es))["verdict"]=="FAIL_CLOSED"

@pytest.mark.parametrize("field,value",[("actor_class","STATE"),("patient_class","TIME_REFERENCE")])
def test_actor_patient_mismatch(field,value):
    c=candidate("PHYSICAL_ACTION");c[field]=value;c["candidate_identity"]=candidate_identity(c);es=evidence(c)
    assert adjudicate(c,es,reviews(c,es))["verdict"]=="FAIL_CLOSED"

def test_affordance_and_continuity_removal_fail():
    c=candidate("MOVEMENT_LOCATION");c["affordances"]=[];c["continuity"]={};c["candidate_identity"]=candidate_identity(c);es=evidence(c)
    result=adjudicate(c,es,reviews(c,es));assert {"AFFORDANCE_MISMATCH","CONTINUITY_MISMATCH"}<=set(result["blockers"])
