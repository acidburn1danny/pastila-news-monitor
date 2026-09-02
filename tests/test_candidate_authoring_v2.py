from copy import deepcopy
import pytest
from pastila_scout.candidate_authoring_v2 import authority_identity,author_from_basis,duplicate_report,evidence_basis_identity,paths_conform,semantic_primitive_identity
from pastila_scout.semantic_authority_bootstrap_v2 import canonical_identity
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

def authorities(b):
 s=SPECS[b["relation_class"]];bid=evidence_basis_identity(b);out=[]
 for kind in sorted({s.evidence_kind,"contrast_alternatives","semantic_authority"}):
  owner="INDEPENDENT_AUTHORITY:"+kind
  source={"origin":"EXTERNAL_GOVERNED_GENERAL_SEMANTIC_SOURCE","provenance_identity":b["authority_provenance"],"source_owner":owner,"synthetic_qualification_fixture":False,"source_commitment":f"commitment:{kind}:{bid}","source_identity":""};source["source_identity"]=canonical_identity(source,"source_identity")
  a={"kind":kind,"basis_identity":bid,"relation_class":b["relation_class"],"source_provenance_identity":b["authority_provenance"],"trust_domain_owner":owner,"independent":True,"source_manifest":source,"admission_receipt":{},"canonical_semantic_content":{"basis":b["semantic_basis"],"kind":kind},"authority_identity":""}
  admission={"source_identity":source["source_identity"],"authority_identity":"","basis_identity":bid,"relation_class":b["relation_class"],"kind":kind,"verdict":"ADMITTED","fail_closed":True,"candidate_identity":None,"verifier_identity":"INDEPENDENT_VERIFIER:"+kind,"admission_identity":""}
  a["admission_receipt"]=admission;a["authority_identity"]=authority_identity(a);admission["authority_identity"]=a["authority_identity"];admission["admission_identity"]=canonical_identity(admission,"admission_identity");out.append(a)
 return out
def author(b,meta=None):return author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=authorities(b),metadata=meta)

def test_replay_16_are_substantively_distinct_and_adjudicable():
 packages=[author(b) for b in bases()];cs=[p[0] for p in packages];assert duplicate_report(cs)["duplicate_rate"]==0
 results=[adjudicate(c,e,reviews(c,e)) for c,e,_ in packages];assert all(x["verdict"].startswith("PASS") for x in results)

@pytest.mark.parametrize("field",["sequence","nonce","timestamp","label","filename","batch"])
def test_ephemeral_metadata_cannot_create_semantic_novelty(field):
 b=bases()[0];a=author(b,{field:"A"})[0];z=author(b,{field:"Z"})[0];assert semantic_primitive_identity(a)==semantic_primitive_identity(z)

def test_four_identifier_only_variants_trigger_duplicate_stop():
 b=bases()[0];cs=[author(b,{"sequence":i,"nonce":str(i)})[0] for i in range(4)];assert duplicate_report(cs)["duplicate_rate"]==0.75

def test_evidence_changes_with_substantive_basis():
 packages=[author(b) for b in bases()[:4]];assert len({p[2]["basis"]["basis_identity"] for p in packages})==4;assert len({p[1][0]["provenance_identity"] for p in packages})==4

def test_dry_and_execution_are_same_canonical_path():
 f=lambda b:author(b);assert paths_conform(f,f,bases())

def test_chain_slot_generic_state_and_reverse_order_fail():
 b=bases()[0]
 for key,value in [("chain_slot","anchor"),("generic_produced_state",True),("origin_order","RULE_BEFORE_EVIDENCE")]:
  x=deepcopy(b);x[key]=value
  with pytest.raises(ValueError):author(x)

def test_cross_class_templates_do_not_collapse():
    cs=[author(next(b for b in bases() if b["relation_class"]==rc))[0] for rc in BATCHES[1]];assert len(set(duplicate_report(cs)["identities"]))==4

def test_author_cannot_synthesize_or_own_authority():
 b=bases()[0];auth=authorities(b);auth[0]["trust_domain_owner"]=AUTHOR;auth[0]["authority_identity"]=authority_identity(auth[0])
 with pytest.raises(ValueError):author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=auth)

def test_nested_substantive_label_and_time_are_not_stripped():
 b=bases()[0];c=author(b)[0];z=deepcopy(c);z["scope"]={"label":"different-semantic-label","timestamp":"event-time"}
 assert semantic_primitive_identity(c)!=semantic_primitive_identity(z)

def test_evidence_order_is_deterministic():
 b=bases()[0];first=author(b)[1];second=author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=reversed(authorities(b)))[1]
 assert [e["evidence_identity"] for e in first]==[e["evidence_identity"] for e in second]

def all_five_batch_bases():
 out=[]
 for batch,classes in BATCHES.items():
  for rc in classes:
   s=SPECS[rc]
   for ordinal,aspect in enumerate(("initiation","transformation","verification","bounded-result"),1):
    out.append({"relation_class":rc,"semantic_basis":f"{rc.lower()}:{aspect}","actor_class":s.actor_classes[0],"patient_class":s.patient_classes[(ordinal-1)%len(s.patient_classes)],"operands":[f"{rc}:{aspect}:actor",f"{rc}:{aspect}:patient"],"claimed_result":f"{rc}:{aspect}:result","scope":{"domain":rc.lower(),"aspect":aspect},"authority_provenance":f"independent:{rc}:{aspect}","continuity_binding":f"{rc}:{aspect}:continuity","origin_order":"INDEPENDENT_BASIS_BEFORE_EVIDENCE_BEFORE_CANDIDATE","batch":batch})
 return out

def test_all_five_batches_share_one_path_and_have_zero_false_duplicates():
 bs=all_five_batch_bases();assert len(bs)==68
 assert paths_conform(lambda b:author(b),lambda b:author(b,{"sequence":"execution"}),bs)
 packages=[author(b) for b in bs];assert duplicate_report([p[0] for p in packages])["duplicate_rate"]==0
 assert all(adjudicate(c,e,reviews(c,e))["verdict"].startswith("PASS") for c,e,_ in packages)

def test_duplicate_authority_kind_and_provenance_skew_fail():
 b=bases()[0];auth=authorities(b)
 with pytest.raises(ValueError,match="duplicate authority"):author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=auth+[auth[0]])
 auth=authorities(b);auth[0]["source_provenance_identity"]="wrong";auth[0]["authority_identity"]=authority_identity(auth[0])
 with pytest.raises(ValueError,match="authority binding"):author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=auth)

def test_evidence_roles_are_explicit_and_skew_fails():
 c,e,_=author(bases()[0]);assert all(x["roles"]==c["roles"] for x in e)
 e[0]["roles"]={"actor":"PATIENT","patient":"ACTOR"};e[0]["evidence_identity"]=__import__('pastila_scout.relation_contract_v2',fromlist=['evidence_identity']).evidence_identity(e[0])
 assert "EVIDENCE_ROLE_SKEW" in adjudicate(c,e,reviews(c,e))["blockers"]

@pytest.mark.parametrize("mutation",[
 lambda a:a.pop("admission_receipt"),
 lambda a:a["source_manifest"].update(synthetic_qualification_fixture=True),
 lambda a:a["admission_receipt"].update(candidate_identity="candidate"),
 lambda a:a["admission_receipt"].update(verifier_identity=AUTHOR),
])
def test_asserted_independence_and_mutated_admission_fail_closed(mutation):
 b=bases()[0];auth=authorities(b);mutation(auth[0])
 with pytest.raises(ValueError):author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=auth)

def test_resealed_synthetic_source_and_candidate_dependent_admission_still_fail():
 b=bases()[0]
 for mode in ("synthetic","candidate-dependent","trust-collision"):
  auth=authorities(b);a=auth[0]
  if mode=="synthetic":
   a["source_manifest"]["synthetic_qualification_fixture"]=True
   a["source_manifest"]["source_identity"]=canonical_identity(a["source_manifest"],"source_identity")
  elif mode=="candidate-dependent":a["admission_receipt"]["candidate_identity"]="future-candidate"
  else:a["admission_receipt"]["verifier_identity"]=AUTHOR
  a["authority_identity"]=authority_identity(a)
  a["admission_receipt"]["source_identity"]=a["source_manifest"]["source_identity"]
  a["admission_receipt"]["authority_identity"]=a["authority_identity"]
  a["admission_receipt"]["admission_identity"]=canonical_identity(a["admission_receipt"],"admission_identity")
  with pytest.raises(ValueError):author_from_basis(b,author_identity=AUTHOR,adjudicator_identity=ADJ,authorities=auth)
