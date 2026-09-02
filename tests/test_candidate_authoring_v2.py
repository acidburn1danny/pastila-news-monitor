from copy import deepcopy
import pytest
from pastila_scout.candidate_authoring_v2 import author_from_basis,duplicate_report,evidence_basis_identity,paths_conform,semantic_primitive_identity
from pastila_scout.curriculum_v2_design import BATCHES
from pastila_scout.relation_contract_v2 import adjudicate,SPECS
from pastila_scout.relation_contract_v2_qualification import reviews

AUTHOR="RULE_AUTHOR_V2_01";ADJ="RULE_ADJUDICATOR_V2_01"
SUBDOMAINS={
"PHYSICAL_ACTION":[("contact","PHYSICAL_ENTITY","contact-event"),("support","PHYSICAL_ENTITY","supported-state"),("separation","PHYSICAL_ENTITY","separation-event"),("rotation","PHYSICAL_ENTITY","orientation-state")],
"MOVEMENT_LOCATION":[("translation","LOCATION","arrival-state"),("departure","LOCATION","departure-event"),("path-traversal","LOCATION","traversal-event"),("containment-entry","LOCATION","contained-state")],
"OBSERVATION_PERCEPTION":[("visual","OBSERVED_EVENT","visual-observation"),("auditory","OBSERVED_EVENT","auditory-observation"),("sensor-state","OBSERVED_STATE","state-observation"),("change-detection","OBSERVED_STATE","change-observation")],
"MEASUREMENT":[("length","MEASURED_PROPERTY","length-quantity"),("duration","MEASURED_PROPERTY","duration-quantity"),("mass","MEASURED_PROPERTY","mass-quantity"),("temperature","MEASURED_PROPERTY","temperature-quantity")],}

def bases():
 out=[]
 for rc in BATCHES[1]:
  for i,(sub,patient,result) in enumerate(SUBDOMAINS[rc],1):
   s=SPECS[rc];out.append({"relation_class":rc,"semantic_basis":sub,"actor_class":s.actor_classes[0],"patient_class":patient,"operands":[f"{sub}-actor",f"{sub}-patient"],"claimed_result":result,"scope":{"domain":sub},"authority_provenance":f"general-semantic-authority:{rc}:{sub}","continuity_binding":f"{sub}-continuity","origin_order":"INDEPENDENT_BASIS_BEFORE_EVIDENCE_BEFORE_CANDIDATE"})
 return out

def author(b,meta=None):return author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,metadata=meta)

def test_replay_16_are_substantively_distinct_and_adjudicable():
 packages=[author(b) for b in bases()];cs=[p[0] for p in packages];assert duplicate_report(cs)["duplicate_rate"]==0
 results=[adjudicate(c,e,reviews(c,e)) for c,e,_ in packages];assert all(x["verdict"].startswith("PASS") for x in results)

@pytest.mark.parametrize("field",["sequence","nonce","timestamp","label","filename","batch"])
def test_ephemeral_metadata_cannot_create_semantic_novelty(field):
 b=bases()[0];a=author(b,{field:"A"})[0];z=author(b,{field:"Z"})[0];assert semantic_primitive_identity(a)==semantic_primitive_identity(z)

def test_four_identifier_only_variants_trigger_duplicate_stop():
 b=bases()[0];cs=[author(b,{"sequence":i,"nonce":str(i)})[0] for i in range(4)];assert duplicate_report(cs)["duplicate_rate"]==0.75

def test_evidence_changes_with_substantive_basis():
 packages=[author(b) for b in bases()[:4]];assert len({p[2]["basis_identity"] for p in packages})==4;assert len({p[1][0]["canonical_content"]["basis_identity"] for p in packages})==4

def test_dry_and_execution_are_same_canonical_path():
 f=lambda b:author(b);assert paths_conform(f,f,bases())

def test_chain_slot_generic_state_and_reverse_order_fail():
 b=bases()[0]
 for key,value in [("chain_slot","anchor"),("generic_produced_state",True),("origin_order","RULE_BEFORE_EVIDENCE")]:
  x=deepcopy(b);x[key]=value
  with pytest.raises(ValueError):author(x)

def test_cross_class_templates_do_not_collapse():
 cs=[author(next(b for b in bases() if b["relation_class"]==rc))[0] for rc in BATCHES[1]];assert len(set(duplicate_report(cs)["identities"]))==4
