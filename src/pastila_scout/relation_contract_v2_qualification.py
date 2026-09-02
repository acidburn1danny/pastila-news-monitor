"""Synthetic zero-family qualification harness for Contract V2."""
from __future__ import annotations
from copy import deepcopy
from .relation_contract_v2 import SPECS,adjudicate,candidate_identity,evidence_identity,validate_composition

def candidate(rc):
 s=SPECS[rc]; c={"relation_class":rc,"actor_class":s.actor_classes[0],"patient_class":s.patient_classes[0],"roles":{"actor":"ACTOR","patient":"PATIENT"},"operands":["ACTOR_1","PATIENT_1"],"affordances":list(s.required_affordances),"continuity":{"kind":s.continuity},"dependency_test":s.dependency,"claimed_result_licensed":True,"arbitrary_substitution_rejected":True,"alternative_results_allowed":s.alternatives_allowed,"terminal":{"enabled":True,"authority":True,"continuity":True,"licensed_result":True,"non_arbitrary":True},"author_identity":"AUTHOR_A","adjudicator_identity":"ADJUDICATOR_B","candidate_identity":""}; c["candidate_identity"]=candidate_identity(c); return c

def evidence(c):
 kinds={SPECS[c["relation_class"]].evidence_kind,"contrast_alternatives","semantic_authority"}; out=[]
 for kind in kinds:
  e={"kind":kind,"relation_class":c["relation_class"],"candidate_identity":c["candidate_identity"],"provenance_identity":"PROVENANCE_"+kind,"trust_domain_owner":"INDEPENDENT_"+kind,"independent":True,"operands":c["operands"],"roles":c["roles"],"canonical_content":{"predicate":kind},"evidence_identity":""};e["evidence_identity"]=evidence_identity(e);out.append(e)
 return out

def reviews(c,ev):
 ids=[x.get("evidence_identity") for x in ev if x.get("evidence_identity")]
 return [{"dimension":d,"candidate_identity":c["candidate_identity"],"relation_class":c["relation_class"],"evidence_identities":ids,"reviewer_identity":"REVIEWER_"+d,"verdict":"PASS","evaluated_predicates":[d]} for d in ("SEMANTIC","LICENSING","ADVERSARIAL")]

def qualify():
 positives={}
 for rc in SPECS:
  c=candidate(rc);ev=evidence(c);positives[rc]=adjudicate(c,ev,reviews(c,ev))
 negatives={}
 base=candidate("TEMPORAL");ev=evidence(base);rv=reviews(base,ev);bad=deepcopy(base);bad["actor_class"]="PROPOSITION_CONTENT";bad["candidate_identity"]=candidate_identity(bad);negatives["PROPOSITION_ACTIVATES_TIME"]=adjudicate(bad,ev,rv)
 for name,rc,mutation in [
  ("ELIGIBILITY_WITHOUT_AUTHORITY","NORMATIVE_AUTHORIZATION",lambda e:e.clear()),
  ("RECORD_CREATES_OBLIGATION","NORMATIVE_OBLIGATION",lambda e:e.clear()),
  ("LEXICAL_CONTINUITY_AS_CAUSALITY","CAUSAL",lambda e:e.clear()),
  ("PLANNER_AUTHORED_LICENSE","PHYSICAL_ACTION",lambda e:e.update(trust_domain_owner="PLANNER")),
  ("SELF_VALIDATING_NECESSITY","TRIGGER",lambda e:e.update(independent=False)),]:
  c=candidate(rc);es=evidence(c); mutation(es[0]); negatives[name]=adjudicate(c,es,reviews(c,es))
 c=candidate("REPRESENTATIONAL");es=evidence(c);c["terminal"]["authority"]=False;c["candidate_identity"]=candidate_identity(c);negatives["ARBITRARY_TERMINAL"]=adjudicate(c,es,reviews(c,es))
 return {"positives":positives,"negatives":negatives}
